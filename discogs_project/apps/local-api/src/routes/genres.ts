import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

// Matches GENRE_ANALYSIS_QUERY from data/queries.py.
// Falls back gracefully if the genre_analysis_mv materialized view does not exist.
const GENRE_QUERY = `
SELECT
  genre,
  COUNT(*)                                      AS release_count,
  COUNT(DISTINCT artist)                        AS artist_count,
  AVG(CASE WHEN rating > 0 THEN rating END)     AS avg_rating
FROM   releases r,
       LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre
WHERE  genre IS NOT NULL AND genre != ''
GROUP  BY genre
ORDER  BY release_count DESC
LIMIT  20
`;

const genres: FastifyPluginAsync = async (fastify) => {
  fastify.get('/genres', async (_request, reply) => {
    // Try the materialized view first (faster); fall back to live query.
    try {
      const mv = await pool.query('SELECT * FROM genre_analysis_mv LIMIT 20');
      if (mv.rows.length > 0) {
        return reply.send({ genres: mv.rows });
      }
    } catch (_err) {
      // materialized view not yet populated or doesn't exist — fall through
    }

    const result = await pool.query(GENRE_QUERY);
    return reply.send({ genres: result.rows });
  });
};

export default genres;
