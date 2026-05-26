/**
 * /api/discover — three discovery tools:
 *   GET /api/discover/style    — live Discogs search by style/genre, tagged owned/wantlist/gap
 *   GET /api/discover/expand   — SQL-based expansion from your collection's DNA
 *   GET /api/discover/lists    — find Discogs community lists matching a query
 *   GET /api/discover/list/:id — load a specific list and tag each item
 */

import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

const DISCOGS_TOKEN = process.env.DISCOGS_TOKEN ?? '';
const DISCOGS_HEADERS: Record<string, string> = {
  Authorization: `Discogs token=${DISCOGS_TOKEN}`,
  'User-Agent': 'DiscogsCollectionApp/1.0',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

async function discogsGet(url: string): Promise<unknown> {
  const res = await fetch(url, { headers: DISCOGS_HEADERS });
  if (!res.ok) throw new Error(`Discogs API ${res.status} — ${url}`);
  return res.json();
}

async function getOwnedAndWanted(): Promise<{ ownedIds: Set<number>; wantIds: Set<number> }> {
  const [ownedRes, wantRes] = await Promise.all([
    pool.query('SELECT discogs_id FROM collection_data.releases WHERE discogs_id IS NOT NULL'),
    pool.query(
      'SELECT discogs_release_id FROM collection_data.wantlist WHERE discogs_release_id IS NOT NULL'
    ).catch(() => ({ rows: [] as { discogs_release_id: unknown }[] })),
  ]);
  return {
    ownedIds: new Set((ownedRes.rows as { discogs_id: unknown }[]).map((r) => Number(r.discogs_id))),
    wantIds:  new Set((wantRes.rows as { discogs_release_id: unknown }[]).map((r) => Number(r.discogs_release_id))),
  };
}

function tagStatus(
  id: number,
  ownedIds: Set<number>,
  wantIds: Set<number>,
): 'owned' | 'wantlist' | 'gap' {
  if (ownedIds.has(id)) return 'owned';
  if (wantIds.has(id))  return 'wantlist';
  return 'gap';
}

// Scrape Discogs list-search results page — returns list slugs/ids without auth
async function scrapeDiscogListSearch(
  query: string,
): Promise<Array<{ id: number; slug: string; name: string; url: string }>> {
  const searchUrl = `https://www.discogs.com/search/?type=list&q=${encodeURIComponent(query)}`;
  const res = await fetch(searchUrl, {
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ' +
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      Accept: 'text/html,application/xhtml+xml',
      'Accept-Language': 'en-US,en;q=0.9',
    },
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) return [];
  const html = await res.text();

  // Pattern: href="/lists/Some-Slug/1234567"
  const seen   = new Set<number>();
  const lists: Array<{ id: number; slug: string; name: string; url: string }> = [];

  // Grab all list hrefs
  const hrefRe = /href="\/lists\/([A-Za-z0-9_-]+)\/(\d+)"/g;
  // Grab anchor text for those hrefs (same line / nearby)
  const blockRe = /href="\/lists\/([A-Za-z0-9_-]+)\/(\d+)"[^>]*>([^<]{2,120})<\/a>/g;

  const nameMap = new Map<number, string>();
  let m: RegExpExecArray | null;
  while ((m = blockRe.exec(html)) !== null) {
    const id   = parseInt(m[2], 10);
    const text = m[3].trim();
    if (text) nameMap.set(id, text);
  }

  while ((m = hrefRe.exec(html)) !== null) {
    const slug = m[1];
    const id   = parseInt(m[2], 10);
    if (seen.has(id)) continue;
    seen.add(id);
    const name = nameMap.get(id) ?? slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    lists.push({ id, slug, name, url: `https://www.discogs.com/lists/${slug}/${id}` });
    if (lists.length >= 20) break;
  }

  return lists;
}

// ── Plugin ────────────────────────────────────────────────────────────────────

const discoverRoutes: FastifyPluginAsync = async (fastify) => {

  // ── 1. Style Explorer ───────────────────────────────────────────────────────
  // Live Discogs search filtered by vinyl, sorted by community have count.
  // Each result tagged owned / wantlist / gap against your collection.
  fastify.get<{ Querystring: { style?: string; genre?: string; limit?: number } }>(
    '/discover/style',
    {
      schema: {
        querystring: {
          type: 'object',
          properties: {
            style: { type: 'string', maxLength: 120 },
            genre: { type: 'string', maxLength: 120 },
            limit: { type: 'integer', minimum: 1, maximum: 100, default: 40 },
          },
        },
      },
    },
    async (request, reply) => {
      const { style, genre, limit = 40 } = request.query;
      if (!style && !genre) {
        return reply.status(400).send({ error: 'Provide style or genre' });
      }

      const params = new URLSearchParams({
        format:     'Vinyl',
        sort:       'have',
        sort_order: 'desc',
        per_page:   String(Math.min(limit, 100)),
        type:       'release',
      });
      if (style) params.set('style', style);
      if (genre) params.set('genre', genre);

      const [data, { ownedIds, wantIds }] = await Promise.all([
        discogsGet(`https://api.discogs.com/database/search?${params}`) as Promise<{
          results?: {
            id: number; title: string; year?: number;
            label?: string[]; format?: string[];
            genre?: string[]; style?: string[];
            country?: string; cover_image?: string; thumb?: string;
            community?: { have?: number; want?: number };
          }[];
          pagination?: { items: number };
        }>,
        getOwnedAndWanted(),
      ]);

      const results = (data.results ?? []).map((r) => ({
        id:            r.id,
        title:         r.title,
        year:          r.year ?? null,
        label:         (r.label ?? [])[0] ?? null,
        format:        (r.format ?? [])[0] ?? null,
        genres:        r.genre  ?? [],
        styles:        r.style  ?? [],
        country:       r.country ?? null,
        thumb:         r.cover_image ?? r.thumb ?? null,
        community_have: r.community?.have ?? null,
        community_want: r.community?.want ?? null,
        status:        tagStatus(r.id, ownedIds, wantIds),
      }));

      return reply.send({ results, total: data.pagination?.items ?? results.length });
    },
  );

  // ── 2. Collection DNA Expander ──────────────────────────────────────────────
  // Pure SQL: extracts top labels + artists for the given style from your
  // collection, then finds items in new_releases_feed you don't own yet that
  // match those labels / artists.
  fastify.get<{ Querystring: { style?: string; limit?: number } }>(
    '/discover/expand',
    {
      schema: {
        querystring: {
          type: 'object',
          properties: {
            style: { type: 'string', maxLength: 120 },
            limit: { type: 'integer', minimum: 1, maximum: 100, default: 40 },
          },
        },
      },
    },
    async (request, reply) => {
      const { style, limit = 40 } = request.query;

      const styleParam: string[] = style ? [style] : [];
      const styleClause = style ? 'AND style_val = $1' : '';

      // Parallel: top labels, top artists, owned count in style
      const [labelRes, artistRes, countRes] = await Promise.all([
        pool.query<{ label: string; cnt: string }>(
          `SELECT r.label, COUNT(*) AS cnt
           FROM collection_data.releases r,
                jsonb_array_elements_text(COALESCE(r.styles,'[]'::jsonb)) AS style_val
           WHERE r.label IS NOT NULL ${styleClause}
           GROUP BY r.label ORDER BY cnt DESC LIMIT 12`,
          styleParam,
        ),
        pool.query<{ artist: string; cnt: string }>(
          `SELECT r.artist, COUNT(*) AS cnt
           FROM collection_data.releases r,
                jsonb_array_elements_text(COALESCE(r.styles,'[]'::jsonb)) AS style_val
           WHERE r.artist IS NOT NULL AND r.artist NOT ILIKE '%various%' ${styleClause}
           GROUP BY r.artist ORDER BY cnt DESC LIMIT 20`,
          styleParam,
        ),
        pool.query<{ cnt: string }>(
          `SELECT COUNT(*) AS cnt
           FROM collection_data.releases r,
                jsonb_array_elements_text(COALESCE(r.styles,'[]'::jsonb)) AS style_val
           WHERE 1=1 ${styleClause}`,
          styleParam,
        ),
      ]);

      const topLabels  = labelRes.rows.map((r) => r.label);
      const topArtists = artistRes.rows.map((r) => r.artist);
      const ownedCount = Number(countRes.rows[0]?.cnt ?? 0);

      // Build feed query: label OR artist match, not yet owned
      const feedParams: (string | number)[] = [];
      const conditions: string[] = [];

      if (topLabels.length > 0) {
        const ph = topLabels.map((_, i) => `$${feedParams.length + i + 1}`).join(', ');
        feedParams.push(...topLabels);
        conditions.push(`nrf.label IN (${ph})`);
      }
      if (topArtists.length > 0) {
        const ph = topArtists.map((_, i) => `$${feedParams.length + i + 1}`).join(', ');
        feedParams.push(...topArtists);
        conditions.push(`nrf.artist IN (${ph})`);
      }
      // Also match style-sourced rows directly
      if (style) {
        feedParams.push(`style:${style}`);
        conditions.push(`nrf.source = $${feedParams.length}`);
      }

      let feedRows: unknown[] = [];
      if (conditions.length > 0) {
        feedParams.push(limit);
        const feedRes = await pool.query(
          `SELECT nrf.discogs_release_id, nrf.title, nrf.artist,
                  nrf.year, nrf.label, nrf.format, nrf.genres, nrf.country, nrf.source
           FROM   collection_data.new_releases_feed nrf
           LEFT JOIN collection_data.releases r ON r.discogs_id = nrf.discogs_release_id
           WHERE  r.release_id IS NULL
           AND    (${conditions.join(' OR ')})
           ORDER  BY nrf.discovered_at DESC
           LIMIT  $${feedParams.length}`,
          feedParams,
        );

        const { ownedIds, wantIds } = await getOwnedAndWanted();
        feedRows = (feedRes.rows as {
          discogs_release_id: number; title: string; artist: string;
          year: number | null; label: string | null; format: string | null;
          genres: unknown; country: string | null; source: string;
        }[]).map((r) => ({
          ...r,
          status: tagStatus(Number(r.discogs_release_id), ownedIds, wantIds),
        }));
      }

      return reply.send({
        style:       style ?? 'all',
        owned_count: ownedCount,
        topLabels,
        topArtists,
        results:     feedRows,
        feed_tip:    feedRows.length === 0
          ? 'Hit ↻ Sync in New Releases to populate the feed with style-based results, then try again.'
          : null,
      });
    },
  );

  // ── 3a. List Discovery ──────────────────────────────────────────────────────
  // Scrapes Discogs list-search results page for lists matching the query.
  fastify.get<{ Querystring: { query: string } }>(
    '/discover/lists',
    {
      schema: {
        querystring: {
          type: 'object',
          required: ['query'],
          properties: {
            query: { type: 'string', minLength: 1, maxLength: 200 },
          },
        },
      },
    },
    async (request, reply) => {
      const { query } = request.query;
      try {
        const lists = await scrapeDiscogListSearch(query);
        return reply.send({
          lists,
          query,
          discogs_search_url: `https://www.discogs.com/search/?type=list&q=${encodeURIComponent(query)}`,
        });
      } catch (err) {
        fastify.log.warn({ err }, 'List scrape failed');
        return reply.send({
          lists: [],
          query,
          discogs_search_url: `https://www.discogs.com/search/?type=list&q=${encodeURIComponent(query)}`,
          error: 'Could not reach Discogs — open the link below to search manually.',
        });
      }
    },
  );

  // ── 3b. Load a specific list ────────────────────────────────────────────────
  // Fetches the Discogs list by ID and tags each item against your collection.
  fastify.get<{ Params: { id: string } }>(
    '/discover/list/:id',
    async (request, reply) => {
      const listId = parseInt((request.params as { id: string }).id, 10);
      if (isNaN(listId) || listId < 1) {
        return reply.status(400).send({ error: 'Invalid list ID' });
      }

      const [listData, { ownedIds, wantIds }] = await Promise.all([
        discogsGet(`https://api.discogs.com/lists/${listId}`) as Promise<{
          id: number; name: string; description?: string;
          items?: {
            id: number; display_title?: string; title?: string;
            image_url?: string; uri?: string; type?: string; comment?: string;
          }[];
        }>,
        getOwnedAndWanted(),
      ]);

      const items = (listData.items ?? []).map((item) => ({
        id:      item.id,
        title:   item.display_title ?? item.title ?? '',
        thumb:   item.image_url ?? null,
        uri:     item.uri
               ? (item.uri.startsWith('http') ? item.uri : `https://www.discogs.com${item.uri}`)
               : null,
        type:    item.type ?? 'release',
        comment: item.comment ?? '',
        status:  tagStatus(item.id, ownedIds, wantIds),
      }));

      return reply.send({
        id:          listData.id,
        name:        listData.name,
        description: listData.description ?? '',
        item_count:  items.length,
        items,
        owned:   items.filter((i) => i.status === 'owned').length,
        wanted:  items.filter((i) => i.status === 'wantlist').length,
        gaps:    items.filter((i) => i.status === 'gap').length,
      });
    },
  );
};

export default discoverRoutes;
