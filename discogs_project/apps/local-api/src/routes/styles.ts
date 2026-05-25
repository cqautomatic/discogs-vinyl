import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

// Matches STYLE_ANALYSIS_QUERY from data/queries.py.
const STYLE_QUERY = `
SELECT
  style,
  COUNT(*)                                      AS release_count,
  COUNT(DISTINCT artist)                        AS artist_count,
  AVG(CASE WHEN rating > 0 THEN rating END)     AS avg_rating
FROM   releases r,
       LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS style
WHERE  style IS NOT NULL AND style != ''
GROUP  BY style
ORDER  BY release_count DESC
LIMIT  20
`;

const styles: FastifyPluginAsync = async (fastify) => {
  fastify.get('/styles', async (_request, reply) => {
    // Try the materialized view first; fall back to live query.
    try {
      const mv = await pool.query('SELECT * FROM style_analysis_mv LIMIT 20');
      if (mv.rows.length > 0) {
        return reply.send({ styles: mv.rows });
      }
    } catch (_err) {
      // materialized view not yet populated or doesn't exist — fall through
    }

    const result = await pool.query(STYLE_QUERY);
    return reply.send({ styles: result.rows });
  });
};

export default styles;
