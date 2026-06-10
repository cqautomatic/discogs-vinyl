import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';
import { discogsGet } from '../lib/discogs';

interface CacheRow { payload: unknown; fetched_at: Date }

async function cacheGet(kind: string, key: string): Promise<{ payload: unknown; fetchedAt: Date } | null> {
  const r = await pool.query<CacheRow>(
    'SELECT payload, fetched_at FROM collection_data.discogs_catalog_cache WHERE kind=$1 AND key=$2',
    [kind, key]
  );
  if (!r.rows.length) return null;
  return { payload: r.rows[0].payload, fetchedAt: r.rows[0].fetched_at };
}

async function cacheSet(kind: string, key: string, payload: unknown): Promise<void> {
  await pool.query(
    `INSERT INTO collection_data.discogs_catalog_cache (kind, key, payload)
     VALUES ($1,$2,$3)
     ON CONFLICT (kind,key) DO UPDATE SET payload=$3, fetched_at=now()`,
    [kind, key, JSON.stringify(payload)]
  );
}

const TTL_SEARCH_MS   = 24 * 60 * 60 * 1000;
const TTL_BANDCAMP_MS =  7 * 24 * 60 * 60 * 1000;

const storeCheckRoutes: FastifyPluginAsync = async (fastify) => {

  // ── GET /api/store-check?q= ───────────────────────────────────────────────
  fastify.get<{ Querystring: { q: string } }>('/store-check', async (req, reply) => {
    const q = (req.query.q ?? '').trim();
    if (!q) return reply.code(400).send({ error: 'q is required' });

    // Tokenized matching — every word must appear somewhere across the
    // combined fields, mirroring offlineStoreSearch in the frontend so the
    // same query gives the same verdict online and offline.
    const words = q.split(/\s+/).filter(Boolean).slice(0, 8);
    const wordParams = words.map(w => `%${w.replace(/[\\%_]/g, '\\$&')}%`);
    const tokenCond = (haystack: string) =>
      wordParams.map((_, i) => `${haystack} ILIKE $${i + 1} ESCAPE '\\'`).join(' AND ');

    const releasesHaystack = `(COALESCE(r.title,'') || ' ' || COALESCE(r.artist,'') || ' ' || COALESCE(r.catno,''))`;
    const wantlistHaystack = `(COALESCE(w.title,'') || ' ' || COALESCE(w.artist,'') || ' ' || COALESCE(w.basic_information->>'catno',''))`;

    // ── Local search: owned + wantlist ─────────────────────────────────────
    const localSql = `
      SELECT
        r.discogs_id           AS discogs_release_id,
        r.title, r.artist, r.year,
        r.label, r.catno, r.format,
        (r.basic_information->>'master_id')::int AS master_id,
        true                   AS owned,
        false                  AS owns_version,
        (EXISTS(
          SELECT 1 FROM collection_data.wantlist w2
          WHERE w2.discogs_release_id = r.discogs_id
        ))                     AS wantlist,
        rp.lowest_price, rp.currency, rp.num_for_sale,
        ms.low_sold_price, ms.high_sold_price, ms.last_sold_date,
        'local'::text          AS source
      FROM collection_data.releases r
      LEFT JOIN collection_data.release_prices rp
             ON r.discogs_id = rp.discogs_release_id
      LEFT JOIN collection_data.marketplace_stats_dim ms
             ON r.discogs_id = ms.discogs_release_id
      WHERE r.discogs_id IS NOT NULL
        AND ${tokenCond(releasesHaystack)}

      UNION ALL

      SELECT
        w.discogs_release_id,
        w.title, w.artist, w.year,
        w.label,
        (w.basic_information->>'catno')   AS catno,
        w.format,
        (w.basic_information->>'master_id')::int AS master_id,
        false                AS owned,
        (w.basic_information->>'master_id' IS NOT NULL AND EXISTS(
          SELECT 1 FROM collection_data.releases rm
          WHERE (rm.basic_information->>'master_id')::int
              = (w.basic_information->>'master_id')::int
        ))                   AS owns_version,
        true                 AS wantlist,
        rp.lowest_price, rp.currency, rp.num_for_sale,
        ms.low_sold_price, ms.high_sold_price, ms.last_sold_date,
        'local'::text        AS source
      FROM collection_data.wantlist w
      LEFT JOIN collection_data.release_prices rp
             ON w.discogs_release_id = rp.discogs_release_id
      LEFT JOIN collection_data.marketplace_stats_dim ms
             ON w.discogs_release_id = ms.discogs_release_id
      WHERE ${tokenCond(wantlistHaystack)}
        -- skip if already in owned results
        AND NOT EXISTS(
          SELECT 1 FROM collection_data.releases r2
          WHERE r2.discogs_id = w.discogs_release_id
        )

      ORDER BY owned DESC, owns_version DESC, wantlist DESC
      LIMIT 10
    `;

    const localRes = await pool.query(localSql, wordParams);
    const localRows = localRes.rows as Record<string, unknown>[];

    if (localRows.length > 0) {
      return { results: localRows, source: 'local' };
    }

    // ── Discogs fallback search ─────────────────────────────────────────────
    const cacheKey = q.toLowerCase().slice(0, 200);
    const cached = await cacheGet('search', cacheKey);
    const now = Date.now();

    let discogsRows: Record<string, unknown>[] = [];
    if (cached && (now - cached.fetchedAt.getTime()) < TTL_SEARCH_MS) {
      discogsRows = cached.payload as Record<string, unknown>[];
    } else {
      try {
        const params = new URLSearchParams({
          q,
          format: 'Vinyl',
          type:   'release',
          per_page: '10',
        });
        const data = await discogsGet(
          `https://api.discogs.com/database/search?${params}`
        ) as { results?: Array<{
          id: number;
          title: string;
          year?: string;
          label?: string[];
          catno?: string;
          format?: string[];
          master_id?: number;
          thumb?: string;
        }> };

        // Fetch owned/wantlist sets + owned master IDs for tagging
        const [ownedRes, wantRes, masterRes] = await Promise.all([
          pool.query<{ discogs_id: number }>('SELECT discogs_id FROM collection_data.releases WHERE discogs_id IS NOT NULL'),
          pool.query<{ discogs_release_id: number }>('SELECT discogs_release_id FROM collection_data.wantlist'),
          pool.query<{ master_id: number }>(`
            SELECT DISTINCT (basic_information->>'master_id')::int AS master_id
            FROM collection_data.releases
            WHERE basic_information->>'master_id' IS NOT NULL
          `),
        ]);
        const ownedSet      = new Set(ownedRes.rows.map((r) => r.discogs_id));
        const wantSet       = new Set(wantRes.rows.map((r) => r.discogs_release_id));
        const ownedMasterIds = new Set(masterRes.rows.map((r) => r.master_id));

        discogsRows = (data.results ?? []).slice(0, 10).map((item) => {
          const [artist = '', ...titleParts] = item.title.split(' - ');
          const exactOwned   = ownedSet.has(item.id);
          const masterOwned  = !exactOwned && item.master_id != null && ownedMasterIds.has(item.master_id);
          return {
            discogs_release_id: item.id,
            title:       titleParts.join(' - ') || item.title,
            artist:      titleParts.length ? artist : null,
            year:        item.year ? parseInt(item.year, 10) : null,
            label:       item.label?.[0] ?? null,
            catno:       item.catno ?? null,
            format:      item.format?.join(', ') ?? null,
            master_id:   item.master_id ?? null,
            owned:       exactOwned,
            owns_version: masterOwned,
            wantlist:    wantSet.has(item.id),
            lowest_price: null, currency: null, num_for_sale: null,
            low_sold_price: null, high_sold_price: null, last_sold_date: null,
            source: 'discogs',
          };
        });
        await cacheSet('search', cacheKey, discogsRows);
      } catch (err) {
        fastify.log.error(err, 'Discogs search failed');
        // Distinguish "lookup failed" from a genuine no-match so the UI
        // doesn't tell the user the record doesn't exist.
        return { results: [], source: 'discogs', error: 'Discogs lookup failed — rate limit or connection issue. Try again in a minute.' };
      }
    }

    return { results: discogsRows, source: 'discogs' };
  });

  // ── GET /api/store-check/bandcamp?artist=&title= ─────────────────────────
  fastify.get<{ Querystring: { artist?: string; title?: string } }>(
    '/store-check/bandcamp',
    async (req, reply) => {
      const artist = (req.query.artist ?? '').trim();
      const title  = (req.query.title  ?? '').trim();
      if (!artist && !title) return reply.code(400).send({ error: 'artist or title required' });

      const searchText = [artist, title].filter(Boolean).join(' ');
      const fallbackUrl = `https://bandcamp.com/search?q=${encodeURIComponent(searchText)}&item_type=a`;
      const cacheKey = searchText.toLowerCase().slice(0, 200);

      const cached = await cacheGet('bandcamp', cacheKey);
      const now = Date.now();
      if (cached && (now - cached.fetchedAt.getTime()) < TTL_BANDCAMP_MS) {
        return cached.payload;
      }

      try {
        const res = await fetch('https://bandcamp.com/api/bcsearch_public_api/1/autocomplete_elastic', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ search_text: searchText, search_filter: 'a', fan_id: null }),
          signal: AbortSignal.timeout(5000),
        });
        if (!res.ok) throw new Error(`Bandcamp ${res.status}`);

        const data = await res.json() as { auto?: { results?: Array<{ name: string; band_name: string; item_url_path: string }> } };
        const results = (data.auto?.results ?? []).slice(0, 3).map((r) => ({
          name:      r.name,
          band_name: r.band_name,
          url:       `https://bandcamp.com${r.item_url_path}`,
        }));
        const payload = { results, fallback_url: fallbackUrl };
        await cacheSet('bandcamp', cacheKey, payload);
        return payload;
      } catch {
        // Unofficial API — always succeed with fallback
        return { results: [], fallback_url: fallbackUrl };
      }
    }
  );
};

export default storeCheckRoutes;
