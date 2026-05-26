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

      let data: {
        results?: {
          id: number; title: string; year?: number;
          label?: string[]; format?: string[];
          genre?: string[]; style?: string[];
          country?: string; cover_image?: string; thumb?: string;
          community?: { have?: number; want?: number };
        }[];
        pagination?: { items: number };
      };

      try {
        data = await discogsGet(`https://api.discogs.com/database/search?${params}`) as typeof data;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        fastify.log.warn({ err }, 'Discogs API error in /discover/style');
        const isRateLimit = msg.includes('429');
        return reply.status(503).send({
          error: isRateLimit
            ? 'Discogs rate limit hit — wait a few seconds and try again.'
            : 'Discogs API unavailable — try again in a moment.',
          detail: msg,
        });
      }

      const { ownedIds, wantIds } = await getOwnedAndWanted();

      const results = (data.results ?? []).map((r) => ({
        id:            r.id,
        title:         r.title,
        year:          r.year != null ? Number(r.year) : null,
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
  // 1. SQL: top labels + artists for the chosen style in your collection
  // 2. Discogs live search by style (stays 100% in-genre)
  // 3. Rank results: top-label matches first, then top-artist, then rest
  // 4. Tag each result owned / wantlist / gap
  fastify.get<{ Querystring: { style?: string; limit?: number } }>(
    '/discover/expand',
    {
      schema: {
        querystring: {
          type: 'object',
          properties: {
            style: { type: 'string', maxLength: 120 },
            limit: { type: 'integer', minimum: 1, maximum: 100, default: 50 },
          },
        },
      },
    },
    async (request, reply) => {
      const { style, limit = 50 } = request.query;

      if (!style) {
        return reply.status(400).send({ error: 'Provide a style' });
      }

      const styleParam = [style];

      // SQL: top labels, top artists, owned count — all for the exact style
      const [labelRes, artistRes, countRes] = await Promise.all([
        pool.query<{ label: string; cnt: string }>(
          `SELECT r.label, COUNT(*) AS cnt
           FROM collection_data.releases r,
                jsonb_array_elements_text(COALESCE(r.styles,'[]'::jsonb)) AS style_val
           WHERE r.label IS NOT NULL AND style_val = $1
           GROUP BY r.label ORDER BY cnt DESC LIMIT 12`,
          styleParam,
        ),
        pool.query<{ artist: string; cnt: string }>(
          `SELECT r.artist, COUNT(*) AS cnt
           FROM collection_data.releases r,
                jsonb_array_elements_text(COALESCE(r.styles,'[]'::jsonb)) AS style_val
           WHERE r.artist IS NOT NULL AND r.artist NOT ILIKE '%various%' AND style_val = $1
           GROUP BY r.artist ORDER BY cnt DESC LIMIT 20`,
          styleParam,
        ),
        pool.query<{ cnt: string }>(
          `SELECT COUNT(*) AS cnt
           FROM collection_data.releases r,
                jsonb_array_elements_text(COALESCE(r.styles,'[]'::jsonb)) AS style_val
           WHERE style_val = $1`,
          styleParam,
        ),
      ]);

      const topLabels  = labelRes.rows.map((r) => r.label);
      const topArtists = artistRes.rows.map((r) => r.artist);
      const ownedCount = Number(countRes.rows[0]?.cnt ?? 0);

      // Case-insensitive sets for fast matching
      const topLabelSet  = new Set(topLabels.map((l) => l.toLowerCase()));
      const topArtistSet = new Set(topArtists.map((a) => a.toLowerCase()));

      // Live Discogs search — locked to the exact style, vinyl only
      const searchParams = new URLSearchParams({
        style,
        format:     'Vinyl',
        sort:       'have',
        sort_order: 'desc',
        per_page:   '100',
        type:       'release',
      });

      let discogsData: {
        results?: {
          id: number; title: string; year?: string | number;
          label?: string[]; format?: string[];
          genre?: string[]; style?: string[];
          country?: string; cover_image?: string; thumb?: string;
          community?: { have?: number; want?: number };
        }[];
        pagination?: { items: number };
      };

      try {
        discogsData = await discogsGet(
          `https://api.discogs.com/database/search?${searchParams}`,
        ) as typeof discogsData;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        fastify.log.warn({ err }, 'Discogs API error in /discover/expand');
        const isRateLimit = msg.includes('429');
        return reply.status(503).send({
          error: isRateLimit
            ? 'Discogs rate limit hit — wait a few seconds and try again.'
            : 'Discogs API unavailable — try again in a moment.',
          detail: msg,
        });
      }

      const { ownedIds, wantIds } = await getOwnedAndWanted();

      type MatchType = 'top-label' | 'top-artist' | 'style';
      const RANK: Record<MatchType, number> = { 'top-label': 0, 'top-artist': 1, 'style': 2 };

      const mapped = (discogsData.results ?? []).map((r) => {
        // Discogs title format is "Artist - Title"
        const parts = r.title.split(' - ');
        const artist = parts.length > 1 ? parts[0] : '';
        const title  = parts.length > 1 ? parts.slice(1).join(' - ') : r.title;

        const label      = (r.label ?? [])[0] ?? null;
        const isTopLabel  = label  ? topLabelSet.has(label.toLowerCase())   : false;
        const isTopArtist = artist ? topArtistSet.has(artist.toLowerCase()) : false;
        const match: MatchType = isTopLabel ? 'top-label' : isTopArtist ? 'top-artist' : 'style';

        return {
          discogs_release_id: r.id,
          title,
          artist,
          year:    r.year != null ? Number(r.year) : null,
          label,
          format:  (r.format ?? [])[0] ?? null,
          genres:  r.genre  ?? [],
          country: r.country ?? null,
          thumb:   r.cover_image ?? r.thumb ?? null,
          match,
          status:  tagStatus(r.id, ownedIds, wantIds),
        };
      });

      // Sort: top-label → top-artist → rest; Discogs already sorted by have count within each tier
      const results = mapped
        .sort((a, b) => RANK[a.match as MatchType] - RANK[b.match as MatchType])
        .slice(0, limit);

      return reply.send({
        style,
        owned_count: ownedCount,
        topLabels,
        topArtists,
        results,
        feed_tip: null,
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

      type ListData = {
        id: number; name: string; description?: string;
        items?: {
          id: number; display_title?: string; title?: string;
          image_url?: string; uri?: string; type?: string; comment?: string;
        }[];
      };
      let listData: ListData;
      try {
        listData = await discogsGet(`https://api.discogs.com/lists/${listId}`) as ListData;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        fastify.log.warn({ err }, `Discogs API error loading list ${listId}`);
        if (msg.includes('404')) {
          return reply.status(404).send({ error: `List ${listId} not found on Discogs.` });
        }
        return reply.status(503).send({
          error: 'Discogs API unavailable — try again in a moment.',
          detail: msg,
        });
      }
      const { ownedIds, wantIds } = await getOwnedAndWanted();

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
