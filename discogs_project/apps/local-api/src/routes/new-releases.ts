import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';
import { discogsGet, discogsPut, delay } from '../lib/discogs';

// ── Discovery styles — single source of truth loaded from config JSON ────────
const STYLES_CONFIG = path.resolve(process.cwd(), '../../config/discovery-styles.json');
let DISCOVERY_STYLES: string[];
try {
  DISCOVERY_STYLES = (JSON.parse(fs.readFileSync(STYLES_CONFIG, 'utf8')) as { styles: string[] }).styles;
} catch (err) {
  throw new Error(`[new-releases] Could not load ${STYLES_CONFIG}: ${err}`);
}
const DISCOVERY_STYLES_SET = new Set(DISCOVERY_STYLES);

// ── Cache helpers (same pattern as pressings.ts) ─────────────────────────────
const TTL_STATS_MS = 24 * 60 * 60 * 1000;

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

// ── Feed query — DISTINCT ON deduplicates artist+title, outer sorts by freshness
const FEED_SQL = `
SELECT * FROM (
  SELECT DISTINCT ON (nrf.artist, nrf.title)
    nrf.id, nrf.discogs_release_id, nrf.title, nrf.artist,
    nrf.year, nrf.label, nrf.format, nrf.genres, nrf.styles,
    nrf.country, nrf.source, nrf.discovered_at, nrf.thumb,
    (w.discogs_release_id IS NOT NULL) AS in_wantlist
  FROM new_releases_feed nrf
  LEFT JOIN releases r_exact
         ON r_exact.discogs_id = nrf.discogs_release_id
  LEFT JOIN releases r_master
         ON nrf.master_id IS NOT NULL
        AND (r_master.basic_information->>'master_id')::int = nrf.master_id
  LEFT JOIN wantlist w ON w.discogs_release_id = nrf.discogs_release_id
  WHERE r_exact.release_id IS NULL
    AND r_master.release_id IS NULL
    AND nrf.dismissed_at IS NULL
    AND nrf.styles IS NOT NULL AND nrf.styles != '[]'::jsonb
    AND EXISTS (
      SELECT 1 FROM jsonb_array_elements_text(nrf.styles) AS s
      WHERE s = ANY($2::text[])
    )
  ORDER BY nrf.artist, nrf.title, nrf.discovered_at DESC
) d
ORDER BY d.discovered_at DESC, d.artist ASC
LIMIT $1
`;

interface NewReleasesQuery {
  limit?: number;
  style?: string;
}

const newReleasesRoutes: FastifyPluginAsync = async (fastify) => {

  // GET /api/new-releases?limit=40&style=House,Deep+House
  fastify.get<{ Querystring: NewReleasesQuery }>('/new-releases', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          limit: { type: 'integer', minimum: 1, maximum: 100, default: 20 },
          style: { type: 'string' },
        },
      },
    },
  }, async (request, reply) => {
    const { limit = 20, style } = request.query;

    // Validate and resolve styles array for query
    let stylesFilter: string[];
    if (style) {
      const requested = style.split(',').map(s => s.trim()).filter(Boolean);
      const invalid = requested.filter(s => !DISCOVERY_STYLES_SET.has(s));
      if (invalid.length) {
        return reply.code(400).send({ error: `Unknown styles: ${invalid.join(', ')}` });
      }
      stylesFilter = requested;
    } else {
      stylesFilter = DISCOVERY_STYLES;
    }

    try {
      const result = await pool.query(FEED_SQL, [limit, stylesFilter]);
      const rows = result.rows as Array<{ discovered_at: string }>;
      const latest_sync = rows.length
        ? rows.reduce<string>((max, r) => r.discovered_at > max ? r.discovered_at : max, rows[0].discovered_at)
        : null;
      return reply.send({ items: rows, count: result.rowCount ?? 0, latest_sync });
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'code' in err && (err as { code: string }).code === '42P01') {
        return reply.send({ items: [], count: 0, latest_sync: null });
      }
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // POST /api/new-releases/prices — batch price lookup (cache-first, ≤15 live fetches)
  fastify.post<{ Body: { release_ids: number[] } }>('/new-releases/prices', {
    schema: {
      body: {
        type: 'object',
        required: ['release_ids'],
        properties: { release_ids: { type: 'array', items: { type: 'integer' }, maxItems: 60 } },
      },
    },
  }, async (request, reply) => {
    const { release_ids } = request.body;
    if (release_ids.length > 60) {
      return reply.code(400).send({ error: 'release_ids must contain at most 60 ids' });
    }

    const now = Date.now();
    const prices: Record<string, { lowest_price: number | null; currency: string | null; num_for_sale: number }> = {};
    const misses: number[] = [];

    // Single-query cache pass instead of N individual SELECTs
    const cacheRows = await pool.query<{ key: string; payload: unknown; fetched_at: Date }>(
      `SELECT key, payload, fetched_at FROM collection_data.discogs_catalog_cache
       WHERE kind = 'release_stats' AND key = ANY($1)`,
      [release_ids.map(String)]
    );
    const cacheMap = new Map(cacheRows.rows.map(r => [r.key, { payload: r.payload, fetchedAt: r.fetched_at }]));

    for (const id of release_ids) {
      const cached = cacheMap.get(String(id));
      if (cached && (now - cached.fetchedAt.getTime()) < TTL_STATS_MS) {
        const p = cached.payload as { lowest_price: { value: number; currency: string } | null; num_for_sale: number };
        prices[String(id)] = {
          lowest_price: p.lowest_price?.value ?? null,
          currency: p.lowest_price?.currency ?? null,
          num_for_sale: p.num_for_sale ?? 0,
        };
      } else {
        misses.push(id);
      }
    }

    // Live fetch up to 15 misses
    const toFetch = misses.slice(0, 15);
    for (let i = 0; i < toFetch.length; i++) {
      const id = toFetch[i];
      try {
        const sd = await discogsGet(
          `https://api.discogs.com/marketplace/stats/${id}?curr_abbr=USD`
        ) as { lowest_price: { value: number; currency: string } | null; num_for_sale: number };
        await cacheSet('release_stats', String(id), sd);
        prices[String(id)] = {
          lowest_price: sd.lowest_price?.value ?? null,
          currency: sd.lowest_price?.currency ?? null,
          num_for_sale: sd.num_for_sale ?? 0,
        };
      } catch { /* skip, leave absent from response */ }
      if (i < toFetch.length - 1) await delay(1100); // rate-limit between calls, not after the last
    }

    return reply.send({ prices });
  });

  // POST /api/new-releases/sync — runs sync_new_releases.py
  fastify.post('/new-releases/sync', async (_request, reply) => {
    const scriptDir = path.resolve(process.cwd(), '../../apps/postgres/discogs_collection_postgres_lab');
    const scriptPath = path.join(scriptDir, 'sync_new_releases.py');
    const pythonPath = process.env.PYTHON_PATH ?? 'python3';

    return new Promise((resolve) => {
      const proc = spawn(pythonPath, [scriptPath], {
        cwd: scriptDir,
        env: {
          ...process.env,
          DISCOGS_TOKEN: process.env.DISCOGS_TOKEN ?? '',
          DISCOGS_USERNAME: process.env.DISCOGS_USERNAME ?? '',
          POSTGRES_HOST: process.env.POSTGRES_HOST ?? 'localhost',
          POSTGRES_PORT: process.env.POSTGRES_PORT ?? '5432',
          POSTGRES_USER: process.env.POSTGRES_USER ?? 'discogs_user',
          POSTGRES_PASSWORD: process.env.POSTGRES_PASSWORD ?? '',
          POSTGRES_DATABASE: process.env.POSTGRES_DATABASE ?? 'discogs_collection',
          POSTGRES_SCHEMA: process.env.POSTGRES_SCHEMA ?? 'collection_data',
        },
      });

      let out = '';
      let err = '';
      proc.stdout.on('data', (d: Buffer) => { out += d.toString(); });
      proc.stderr.on('data', (d: Buffer) => { err += d.toString(); });

      proc.on('close', (code) => {
        if (code === 0) {
          resolve(reply.send({ ok: true, message: out.trim() }));
        } else {
          resolve(reply.status(500).send({ ok: false, message: err.trim() || out.trim() }));
        }
      });
    });
  });

  // POST /api/new-releases/:id/dismiss
  fastify.post<{ Params: { id: string } }>('/new-releases/:id/dismiss', async (request, reply) => {
    const id = parseInt(request.params.id, 10);
    if (isNaN(id)) return reply.code(400).send({ error: 'Invalid id' });
    const r = await pool.query(
      'UPDATE new_releases_feed SET dismissed_at = now() WHERE id = $1',
      [id]
    );
    if ((r.rowCount ?? 0) === 0) return reply.code(404).send({ error: 'Not found' });
    return reply.send({ ok: true });
  });

  // POST /api/new-releases/:id/undismiss
  fastify.post<{ Params: { id: string } }>('/new-releases/:id/undismiss', async (request, reply) => {
    const id = parseInt(request.params.id, 10);
    if (isNaN(id)) return reply.code(400).send({ error: 'Invalid id' });
    const r = await pool.query(
      'UPDATE new_releases_feed SET dismissed_at = NULL WHERE id = $1',
      [id]
    );
    if ((r.rowCount ?? 0) === 0) return reply.code(404).send({ error: 'Not found' });
    return reply.send({ ok: true });
  });

  // POST /api/new-releases/:id/want — add to Discogs wantlist + local upsert
  fastify.post<{ Params: { id: string } }>('/new-releases/:id/want', async (request, reply) => {
    const id = parseInt(request.params.id, 10);
    if (isNaN(id)) return reply.code(400).send({ error: 'Invalid id' });

    const username = process.env.DISCOGS_USERNAME;
    if (!username) return reply.code(500).send({ error: 'DISCOGS_USERNAME not configured' });

    // Look up the feed row
    const feedRes = await pool.query<{
      discogs_release_id: number; title: string; artist: string;
      year: number | null; label: string | null; format: string | null;
      genres: unknown; styles: unknown;
    }>(
      'SELECT discogs_release_id, title, artist, year, label, format, genres, styles FROM new_releases_feed WHERE id = $1',
      [id]
    );
    if (!feedRes.rows.length) return reply.code(404).send({ error: 'Feed item not found' });
    const feed = feedRes.rows[0];

    // Call Discogs API
    let wantResponse: unknown;
    try {
      wantResponse = await discogsPut(
        `https://api.discogs.com/users/${username}/wants/${feed.discogs_release_id}`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Discogs request failed';
      return reply.code(502).send({ ok: false, error: msg });
    }

    // Upsert local wantlist row so badge updates immediately
    const want = wantResponse as { id: number; basic_information: unknown };
    const wantId = String(want.id);
    await pool.query(
      `INSERT INTO wantlist (want_id, username, discogs_release_id, title, artist, year, label, format, genres, styles, basic_information)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
       ON CONFLICT (discogs_release_id) DO NOTHING`,
      [wantId, username, feed.discogs_release_id, feed.title, feed.artist,
       feed.year, feed.label, feed.format,
       JSON.stringify(feed.genres), JSON.stringify(feed.styles),
       JSON.stringify(want.basic_information)]
    );

    return reply.send({ ok: true, in_wantlist: true });
  });

};

export default newReleasesRoutes;
