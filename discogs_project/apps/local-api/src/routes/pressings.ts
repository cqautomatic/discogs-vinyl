import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';
import { discogsGet, delay } from '../lib/discogs';

// Keep only vinyl pressings — Discogs format strings are messy, so filter twice:
// 1) request format=Vinyl from the API; 2) defensively post-filter here.
const VINYL_INCLUDE = /vinyl|LP|12"|10"|7"/i;
const NON_VINYL     = /\b(CD|CDr|Cassette|File|SACD|DVD)\b/i;

function isVinyl(format: string): boolean {
  return VINYL_INCLUDE.test(format) && !NON_VINYL.test(format);
}

// TTLs in milliseconds
const TTL_VERSIONS_MS  = 7  * 24 * 60 * 60 * 1000;
const TTL_STATS_MS     = 24 * 60 * 60 * 1000;

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

interface VersionRow {
  id: number;
  title: string;
  major_formats: string[];
  format: string;
  label: string;
  catno: string;
  country: string;
  released: string;
  stats?: { community?: { in_wantlist?: number; in_collection?: number } };
}

interface StatsPayload {
  lowest_price: { value: number; currency: string } | null;
  num_for_sale: number;
}

const pressingsRoutes: FastifyPluginAsync = async (fastify) => {
  fastify.get<{ Params: { masterId: string }; Querystring: { exclude_release_id?: string } }>(
    '/pressings/:masterId',
    async (req, reply) => {
      const masterId = parseInt(req.params.masterId, 10);
      if (isNaN(masterId) || masterId <= 0) {
        return reply.code(400).send({ error: 'Invalid master_id' });
      }
      const excludeId = req.query.exclude_release_id ? parseInt(req.query.exclude_release_id, 10) : null;

      // ── Cache check for versions list ────────────────────────────────────────
      const vKey = String(masterId);
      const cached = await cacheGet('master_versions', vKey);
      const now = Date.now();
      let versions: VersionRow[] = [];
      let fromCache = false;
      let fetchedAt: string | null = null;

      if (cached && (now - cached.fetchedAt.getTime()) < TTL_VERSIONS_MS) {
        versions = cached.payload as VersionRow[];
        fromCache = true;
        fetchedAt = cached.fetchedAt.toISOString();
      } else {
        // Fetch all vinyl versions (paginate, cap at 200)
        const allVersions: VersionRow[] = [];
        let page = 1;
        while (allVersions.length < 200) {
          const url = `https://api.discogs.com/masters/${masterId}/versions?format=Vinyl&per_page=100&page=${page}`;
          let data: { versions: VersionRow[]; pagination: { pages: number } };
          try {
            data = await discogsGet(url) as typeof data;
          } catch {
            break;
          }
          if (!data.versions?.length) break;
          allVersions.push(...data.versions);
          if (page >= data.pagination.pages) break;
          page++;
          await delay(1100);
        }
        versions = allVersions.filter((v) => {
          const fmt = [v.format, ...(v.major_formats ?? [])].join(', ');
          return isVinyl(fmt);
        });
        await cacheSet('master_versions', vKey, versions);
        fetchedAt = new Date().toISOString();
      }

      // ── Get owned release IDs ─────────────────────────────────────────────────
      const ownedRes = await pool.query<{ discogs_id: number }>(
        'SELECT discogs_id FROM collection_data.releases WHERE discogs_id IS NOT NULL'
      );
      const ownedSet = new Set(ownedRes.rows.map((r) => r.discogs_id));

      // ── Fetch prices for up to 40 versions ───────────────────────────────────
      const toPrice = versions.slice(0, 40);
      const priceMap = new Map<number, StatsPayload>();

      // Cache-or-fetch for every version regardless of where the versions list
      // came from — a warm versions cache must not pin expired prices.
      for (const v of toPrice) {
        const sKey = String(v.id);
        const sc = await cacheGet('release_stats', sKey);
        if (sc && (now - sc.fetchedAt.getTime()) < TTL_STATS_MS) {
          priceMap.set(v.id, sc.payload as StatsPayload);
        } else {
          try {
            const sd = await discogsGet(
              `https://api.discogs.com/marketplace/stats/${v.id}?curr_abbr=USD`
            ) as StatsPayload;
            priceMap.set(v.id, sd);
            await cacheSet('release_stats', sKey, sd);
          } catch {
            // Live fetch failed — serve the stale cached payload over nothing
            if (sc) priceMap.set(v.id, sc.payload as StatsPayload);
          }
          await delay(1100);
        }
      }

      // ── Build response ────────────────────────────────────────────────────────
      const out = versions.map((v) => {
        const stats = priceMap.get(v.id);
        const fmt = [v.format, ...(v.major_formats ?? [])].join(', ');
        return {
          discogs_release_id: v.id,
          title:   v.title,
          label:   v.label   ?? null,
          catno:   v.catno   ?? null,
          country: v.country ?? null,
          year:    v.released ? parseInt(v.released, 10) : null,
          format:  fmt,
          lowest_price:  stats?.lowest_price?.value  ?? null,
          currency:      stats?.lowest_price?.currency ?? null,
          num_for_sale:  stats?.num_for_sale          ?? null,
          is_wantlist_pressing: excludeId !== null && v.id === excludeId,
          owned: ownedSet.has(v.id),
        };
      });

      // Sort: priced first (ascending), then unpriced
      out.sort((a, b) => {
        if (a.lowest_price !== null && b.lowest_price !== null) return a.lowest_price - b.lowest_price;
        if (a.lowest_price !== null) return -1;
        if (b.lowest_price !== null) return  1;
        return 0;
      });

      return { master_id: masterId, versions: out, cached: fromCache, fetched_at: fetchedAt };
    }
  );
};

export default pressingsRoutes;
