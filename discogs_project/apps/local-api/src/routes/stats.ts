import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

// Matches COLLECTION_STATS_QUERY from the Python app (data/queries.py).
// No parameters — fully static aggregation across the collection.
const STATS_QUERY = `
SELECT
  COUNT(*) as total_items,
  COUNT(CASE WHEN discogs_id IS NOT NULL THEN 1 END) as downloaded_items,
  COUNT(DISTINCT artist) as unique_artists,
  COUNT(DISTINCT label) as unique_labels,
  COUNT(DISTINCT NULLIF(country, '')) as countries,
  MIN(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) as earliest_year,
  MAX(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) as latest_year,
  AVG(CASE WHEN community_average_rating > 0 THEN community_average_rating END) as avg_rating,
  COUNT(CASE WHEN community_average_rating > 0 THEN 1 END) as rated_items,
  (SELECT COUNT(*) FROM artwork) as artwork_count,
  (SELECT COALESCE(SUM(file_size), 0) FROM artwork) as total_artwork_size_bytes,
  (SELECT MIN(rp.lowest_price) FROM release_prices rp WHERE rp.lowest_price > 0) as min_price,
  (SELECT MAX(rp.lowest_price) FROM release_prices rp WHERE rp.lowest_price > 0) as max_price,
  (SELECT AVG(rp.lowest_price) FROM release_prices rp WHERE rp.lowest_price > 0) as avg_price,
  (SELECT SUM(rp.lowest_price)
   FROM release_prices rp
   JOIN releases r2 ON r2.discogs_id = rp.discogs_release_id
   WHERE rp.lowest_price > 0) as total_value,
  (SELECT COUNT(*) FROM release_prices rp WHERE rp.lowest_price > 0) as priced_items
FROM releases
`;

const stats: FastifyPluginAsync = async (fastify) => {
  fastify.get('/stats', async (_request, reply) => {
    const result = await pool.query(STATS_QUERY);
    return reply.send(result.rows[0] ?? {});
  });
};

export default stats;
