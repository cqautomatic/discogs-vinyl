/**
 * GET /api/sync/snapshot
 * Returns the full collection, wantlist, and prices as a single JSON payload
 * for caching into the iPhone PWA's IndexedDB.
 */

import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

const syncRoutes: FastifyPluginAsync = async (fastify) => {
  fastify.get('/sync/snapshot', async (_request, reply) => {
    try {
      const [collectionRes, wantlistRes, pricesRes] = await Promise.all([
        pool.query(`
          SELECT
            discogs_id,
            title,
            artist,
            year,
            label,
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
        pool.query(`
          SELECT
            discogs_release_id,
            title,
            artist,
            year,
            label,
            format,
            COALESCE(genres, '[]'::jsonb) AS genres,
            COALESCE(styles, '[]'::jsonb) AS styles
          FROM collection_data.wantlist
          ORDER BY artist, year
        `),
        pool.query(`
          SELECT
            discogs_release_id,
            lowest_price,
            currency,
            COALESCE(num_for_sale, 0)    AS num_for_sale,
            COALESCE(availability, false) AS availability
          FROM collection_data.release_prices
        `),
      ]);

      return reply.send({
        collection:  collectionRes.rows,
        wantlist:    wantlistRes.rows,
        prices:      pricesRes.rows,
        synced_at:   new Date().toISOString(),
        stats: {
          collection_count: collectionRes.rowCount ?? 0,
          wantlist_count:   wantlistRes.rowCount   ?? 0,
          prices_count:     pricesRes.rowCount     ?? 0,
        },
      });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Snapshot failed' });
    }
  });
};

export default syncRoutes;
