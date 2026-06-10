/**
 * GET /api/sync/snapshot
 * Returns the full collection, wantlist, prices, and new releases as a single
 * JSON payload for caching into the iPhone PWA's IndexedDB.
 */

import * as fs from 'fs';
import * as path from 'path';
import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

const STYLES_CONFIG = path.resolve(process.cwd(), '../../config/discovery-styles.json');
let DISCOVERY_STYLES: string[];
try {
  DISCOVERY_STYLES = (JSON.parse(fs.readFileSync(STYLES_CONFIG, 'utf8')) as { styles: string[] }).styles;
} catch (err) {
  throw new Error(`[sync] Could not load ${STYLES_CONFIG}: ${err}`);
}

const syncRoutes: FastifyPluginAsync = async (fastify) => {
  fastify.get('/sync/snapshot', async (_request, reply) => {
    try {
      const [collectionRes, wantlistRes, pricesRes, newReleasesRes] = await Promise.all([

        // Collection — adds catno
        pool.query(`
          SELECT
            discogs_id,
            title,
            artist,
            year,
            label,
            catno,
            format,
            country,
            COALESCE(genres, '[]'::jsonb)  AS genres,
            COALESCE(styles, '[]'::jsonb)  AS styles,
            basic_information->>'cover_image' AS thumb,
            COALESCE(community_have_count, 0) AS community_have,
            COALESCE(community_want_count, 0) AS community_want,
            rating
          FROM collection_data.releases
          WHERE discogs_id IS NOT NULL
          ORDER BY artist, year
        `),

        // Wantlist — adds catno, master_id, sold history, current price
        pool.query(`
          SELECT
            w.discogs_release_id,
            w.title, w.artist, w.year, w.label, w.format,
            COALESCE(w.genres, '[]'::jsonb) AS genres,
            COALESCE(w.styles, '[]'::jsonb) AS styles,
            w.basic_information->>'catno'              AS catno,
            (w.basic_information->>'master_id')::int   AS master_id,
            rp.lowest_price,
            rp.currency,
            COALESCE(rp.num_for_sale, 0)               AS num_for_sale,
            ms.low_sold_price,
            ms.high_sold_price,
            ms.last_sold_date
          FROM collection_data.wantlist w
          LEFT JOIN collection_data.release_prices rp
                 ON rp.discogs_release_id = w.discogs_release_id
          LEFT JOIN collection_data.marketplace_stats_dim ms
                 ON ms.discogs_release_id = w.discogs_release_id
          ORDER BY w.artist, w.year
        `),

        // Prices — adds sold history
        pool.query(`
          SELECT
            rp.discogs_release_id,
            rp.lowest_price,
            rp.currency,
            COALESCE(rp.num_for_sale, 0)      AS num_for_sale,
            COALESCE(rp.availability, false)  AS availability,
            ms.low_sold_price,
            ms.high_sold_price,
            ms.last_sold_date
          FROM collection_data.release_prices rp
          LEFT JOIN collection_data.marketplace_stats_dim ms
                 ON ms.discogs_release_id = rp.discogs_release_id
        `),

        // New releases feed — non-dismissed, matching curated styles, with cached prices
        pool.query(`
          SELECT * FROM (
            SELECT DISTINCT ON (nrf.artist, nrf.title)
              nrf.id,
              nrf.discogs_release_id,
              nrf.title,
              nrf.artist,
              nrf.year,
              nrf.label,
              nrf.format,
              nrf.genres,
              nrf.styles,
              nrf.country,
              nrf.source,
              nrf.discovered_at,
              nrf.thumb,
              (w.discogs_release_id IS NOT NULL)            AS in_wantlist,
              (dcc.payload->'lowest_price'->>'value')::float AS cached_lowest_price,
              dcc.payload->'lowest_price'->>'currency'       AS cached_currency,
              (dcc.payload->>'num_for_sale')::int            AS cached_num_for_sale
            FROM collection_data.new_releases_feed nrf
            LEFT JOIN collection_data.releases r_exact
                   ON r_exact.discogs_id = nrf.discogs_release_id
            LEFT JOIN collection_data.releases r_master
                   ON nrf.master_id IS NOT NULL
                  AND (r_master.basic_information->>'master_id')::int = nrf.master_id
            LEFT JOIN collection_data.wantlist w
                   ON w.discogs_release_id = nrf.discogs_release_id
            LEFT JOIN collection_data.discogs_catalog_cache dcc
                   ON dcc.kind = 'release_stats'
                  AND dcc.key  = nrf.discogs_release_id::text
            WHERE r_exact.release_id IS NULL
              AND r_master.release_id IS NULL
              AND nrf.dismissed_at IS NULL
              AND nrf.styles IS NOT NULL AND nrf.styles != '[]'::jsonb
              AND EXISTS (
                SELECT 1 FROM jsonb_array_elements_text(nrf.styles) AS s
                WHERE s = ANY($1::text[])
              )
            ORDER BY nrf.artist, nrf.title, nrf.discovered_at DESC
          ) d
          ORDER BY d.discovered_at DESC, d.artist ASC
        `, [DISCOVERY_STYLES]),
      ]);

      return reply.send({
        collection:   collectionRes.rows,
        wantlist:     wantlistRes.rows,
        prices:       pricesRes.rows,
        new_releases: newReleasesRes.rows,
        synced_at:    new Date().toISOString(),
        stats: {
          collection_count:   collectionRes.rowCount  ?? 0,
          wantlist_count:     wantlistRes.rowCount    ?? 0,
          prices_count:       pricesRes.rowCount      ?? 0,
          new_releases_count: newReleasesRes.rowCount ?? 0,
        },
      });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Snapshot failed' });
    }
  });
};

export default syncRoutes;
