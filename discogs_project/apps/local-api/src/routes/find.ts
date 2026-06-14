/**
 * /api/find — actionable record-discovery endpoints
 *
 *   GET /api/find/buy-now?max_price=&condition=
 *     Wantlist items available for sale right now, ranked by want/have ratio.
 *
 *   GET /api/find/gaps/label?label=
 *     Discogs label catalogue minus owned records, filtered for desirability.
 *     Results cached 7 days in collection_data.discogs_catalog_cache.
 *
 *   GET /api/find/gaps/artist?artist=
 *     Discogs artist catalogue minus owned records, ranked by community_want.
 *     Same 7-day cache.
 */

import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

const DISCOGS_TOKEN = process.env.DISCOGS_TOKEN ?? '';
const DISCOGS_HEADERS: Record<string, string> = {
  Authorization: `Discogs token=${DISCOGS_TOKEN}`,
  'User-Agent': 'DiscogsCollectionApp/1.0',
};

const CACHE_TTL_DAYS = 7;

// ── Helpers ───────────────────────────────────────────────────────────────────

async function discogsGet(url: string): Promise<unknown> {
  const res = await fetch(url, { headers: DISCOGS_HEADERS });
  if (!res.ok) throw new Error(`Discogs API ${res.status} — ${url}`);
  return res.json();
}

/** Rate-limited Discogs fetch: waits 1 s between calls. */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Read from cache. Returns payload if fresh, null if missing/stale. */
async function cacheGet(kind: string, key: string): Promise<unknown | null> {
  const res = await pool.query(
    `SELECT payload FROM collection_data.discogs_catalog_cache
     WHERE kind = $1 AND key = $2
       AND fetched_at > now() - ($3 || ' days')::interval`,
    [kind, key, CACHE_TTL_DAYS],
  );
  return res.rows.length > 0 ? (res.rows[0] as { payload: unknown }).payload : null;
}

/** Write (upsert) into cache. */
async function cacheSet(kind: string, key: string, payload: unknown): Promise<void> {
  await pool.query(
    `INSERT INTO collection_data.discogs_catalog_cache (kind, key, payload, fetched_at)
     VALUES ($1, $2, $3, now())
     ON CONFLICT (kind, key) DO UPDATE
       SET payload = EXCLUDED.payload, fetched_at = EXCLUDED.fetched_at`,
    [kind, key, JSON.stringify(payload)],
  );
}

/** Fetch all pages from a paginated Discogs endpoint, 1 req/sec. */
async function fetchAllPages(firstUrl: string): Promise<unknown[]> {
  const items: unknown[] = [];
  let url: string | null = firstUrl;
  let page = 1;

  while (url) {
    if (page > 1) await sleep(1000);
    const data = await discogsGet(url) as Record<string, unknown>;

    // Handle both /releases and /versions shapes
    const rows = (
      (data.releases as unknown[] | undefined) ??
      (data.versions as unknown[] | undefined) ??
      []
    );
    items.push(...rows);

    const pagination = data.pagination as Record<string, unknown> | undefined;
    const urls = pagination?.urls as Record<string, string> | undefined;
    url = urls?.next ?? null;
    page++;
  }

  return items;
}

/** Get owned discogs_ids as a Set<number>. */
async function getOwnedIds(): Promise<Set<number>> {
  const res = await pool.query(
    'SELECT discogs_id FROM collection_data.releases WHERE discogs_id IS NOT NULL',
  );
  return new Set((res.rows as { discogs_id: unknown }[]).map((r) => Number(r.discogs_id)));
}

// ── Route plugin ──────────────────────────────────────────────────────────────

const findRoutes: FastifyPluginAsync = async (fastify) => {

  // ── POST /api/find/refresh-wantlist-community ─────────────────────────────
  // Fetches community want/have counts from Discogs for any wantlist item
  // that doesn't have them yet. One-time fix; safe to re-run (skips populated rows).
  fastify.post('/find/refresh-wantlist-community', async (_request, reply) => {
    const { rows } = await pool.query(
      `SELECT discogs_release_id FROM collection_data.wantlist
       WHERE community_want_count IS NULL AND discogs_release_id IS NOT NULL`,
    );

    let updated = 0;
    let failed = 0;

    for (const row of rows as { discogs_release_id: number }[]) {
      try {
        await sleep(1000);
        const data = await discogsGet(
          `https://api.discogs.com/releases/${row.discogs_release_id}`,
        ) as Record<string, unknown>;

        const community = data.community as Record<string, unknown> | undefined;
        const want = community?.want != null ? Number(community.want) : null;
        const have = community?.have != null ? Number(community.have) : null;

        await pool.query(
          `UPDATE collection_data.wantlist
           SET community_want_count = $1, community_have_count = $2
           WHERE discogs_release_id = $3`,
          [want, have, row.discogs_release_id],
        );
        updated++;
      } catch {
        failed++;
      }
    }

    return reply.send({ ok: true, updated, failed, total: rows.length });
  });

  // ── GET /api/find/buy-now ────────────────────────────────────────────────────
  fastify.get('/find/buy-now', async (request, reply) => {
    const { max_price } = request.query as { max_price?: string };

    const maxPrice = max_price ? parseFloat(max_price) : null;

    const { rows } = await pool.query(
      `SELECT
         w.discogs_release_id,
         w.title,
         w.artist,
         w.year,
         w.label,
         rp.lowest_price,
         rp.currency,
         rp.num_for_sale,
         w.community_want_count,
         w.community_have_count,
         w.basic_information->>'thumb' AS thumb,
         CASE
           WHEN w.community_have_count > 0
           THEN ROUND(w.community_want_count::numeric / w.community_have_count, 2)
           ELSE NULL
         END AS ratio
       FROM collection_data.wantlist w
       JOIN collection_data.release_prices rp
         ON rp.discogs_release_id = w.discogs_release_id
       WHERE rp.num_for_sale > 0
         AND ($1::numeric IS NULL OR rp.lowest_price <= $1::numeric)
         AND NOT EXISTS (
           SELECT 1 FROM collection_data.releases
           WHERE discogs_id = w.discogs_release_id
         )
       ORDER BY ratio DESC NULLS LAST`,
      [maxPrice],
    );

    return reply.send({ items: rows, count: rows.length });
  });

  // ── GET /api/find/gaps/label ─────────────────────────────────────────────────
  fastify.get('/find/gaps/label', async (request, reply) => {
    const { label } = request.query as { label?: string };
    if (!label?.trim()) {
      return reply.status(400).send({ error: 'label query param required' });
    }

    const cacheKey = label.toLowerCase().trim();

    // Check cache first
    const cached = await cacheGet('label', cacheKey);
    if (cached) {
      return reply.send({ items: cached, cached: true });
    }

    // Find label id via search
    const searchData = await discogsGet(
      `https://api.discogs.com/database/search?q=${encodeURIComponent(label)}&type=label&per_page=5`,
    ) as Record<string, unknown>;

    const searchResults = (searchData.results as Array<Record<string, unknown>>) ?? [];
    if (searchResults.length === 0) {
      return reply.send({ items: [], cached: false });
    }

    // Pick the best match (first result)
    const labelId = searchResults[0].id as number;

    // Fetch all label releases (paginated, 1 req/sec)
    await sleep(1000);
    const allReleases = await fetchAllPages(
      `https://api.discogs.com/labels/${labelId}/releases?per_page=100&sort=year&sort_order=desc`,
    );

    // Get owned ids
    const ownedIds = await getOwnedIds();

    // Filter and shape
    // Label releases use stats.community.in_wantlist/in_collection
    const gaps = (allReleases as Array<Record<string, unknown>>)
      .filter((rel) => {
        const id = Number(rel.id);
        if (ownedIds.has(id)) return false;
        const stats = rel.stats as Record<string, unknown> | undefined;
        const community = (stats?.community ?? rel.community) as Record<string, unknown> | undefined;
        const want = Number(community?.in_wantlist ?? community?.want ?? 0);
        const have = Number(community?.in_collection ?? community?.have ?? 0);
        return want > 0;
      })
      .map((rel) => {
        const stats = rel.stats as Record<string, unknown> | undefined;
        const community = (stats?.community ?? rel.community) as Record<string, unknown> | undefined;
        const want = Number(community?.in_wantlist ?? community?.want ?? 0);
        const have = Number(community?.in_collection ?? community?.have ?? 0);
        return {
          discogs_id: Number(rel.id),
          title: rel.title as string,
          artist: (rel.artist as string | undefined) ?? '',
          year: (rel.year as number | null) ?? null,
          thumb: (rel.thumb as string | null) ?? null,
          community_want: want,
          community_have: have,
          ratio: have > 0 ? Math.round((want / have) * 100) / 100 : null,
        };
      })
      .sort((a, b) => (b.ratio ?? 0) - (a.ratio ?? 0));

    // Cache the result
    await cacheSet('label', cacheKey, gaps);

    return reply.send({ items: gaps, cached: false });
  });

  // ── GET /api/find/gaps/artist ────────────────────────────────────────────────
  fastify.get('/find/gaps/artist', async (request, reply) => {
    const { artist } = request.query as { artist?: string };
    if (!artist?.trim()) {
      return reply.status(400).send({ error: 'artist query param required' });
    }

    const cacheKey = artist.toLowerCase().trim();

    // Check cache first
    const cached = await cacheGet('artist', cacheKey);
    if (cached) {
      return reply.send({ items: cached, cached: true });
    }

    // Find artist id via search
    const searchData = await discogsGet(
      `https://api.discogs.com/database/search?q=${encodeURIComponent(artist)}&type=artist&per_page=5`,
    ) as Record<string, unknown>;

    const searchResults = (searchData.results as Array<Record<string, unknown>>) ?? [];
    if (searchResults.length === 0) {
      return reply.send({ items: [], cached: false });
    }

    const artistId = searchResults[0].id as number;

    // Fetch all artist releases (paginated)
    await sleep(1000);
    const allReleases = await fetchAllPages(
      `https://api.discogs.com/artists/${artistId}/releases?per_page=100&sort=year&sort_order=desc`,
    );

    // Get owned ids
    const ownedIds = await getOwnedIds();

    // Filter: not owned, rank by community_want DESC
    const gaps = (allReleases as Array<Record<string, unknown>>)
      .filter((rel) => {
        const id = Number(rel.id);
        return !ownedIds.has(id);
      })
      .map((rel) => ({
        discogs_id: Number(rel.id),
        title: rel.title as string,
        year: (rel.year as number | null) ?? null,
        thumb: (rel.thumb as string | null) ?? null,
        role: (rel.role as string | null) ?? null,
        format: (rel.format as string | null) ?? null,
        community_want: Number((rel.stats as Record<string, unknown> | undefined)?.community != null ? ((rel.stats as Record<string, Record<string, unknown>>).community?.want ?? 0) : 0),
        community_have: Number((rel.stats as Record<string, unknown> | undefined)?.community != null ? ((rel.stats as Record<string, Record<string, unknown>>).community?.have ?? 0) : 0),
      }))
      .sort((a, b) => b.community_want - a.community_want);

    // Cache the result
    await cacheSet('artist', cacheKey, gaps);

    return reply.send({ items: gaps, cached: false });
  });
};

export default findRoutes;
