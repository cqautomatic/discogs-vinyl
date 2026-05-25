import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

// Based on COLLECTION_SEARCH_QUERY from data/queries.py.
// Uses a single $1 parameter for both title and artist matching to avoid
// passing the same value twice (safe because $N can be reused in pg).
const SEARCH_QUERY = `
SELECT
  r.release_id, r.discogs_id, r.title, r.artist, r.year,
  r.label, r.catno, r.format, r.genres, r.styles, r.producers,
  r.country, r.rating, r.condition, r.sleeve_condition, r.date_added,
  r.copies_count, r.instance_ids,
  r.community_have_count, r.community_want_count,
  r.community_average_rating, r.community_rating_count,
  COALESCE(
    JSON_AGG(
      JSON_BUILD_OBJECT(
        'artwork_id',          a.artwork_id,
        'image_type',          a.image_type,
        'local_file_path',     a.local_file_path,
        'thumbnail_file_path', a.thumbnail_file_path,
        'original_url',        a.original_url,
        'file_size',           a.file_size,
        'image_width',         a.image_width,
        'image_height',        a.image_height
      ) ORDER BY CASE a.image_type WHEN 'primary' THEN 0 ELSE 1 END, a.artwork_id
    ) FILTER (WHERE a.artwork_id IS NOT NULL),
    '[]'::json
  ) AS artwork_files
FROM   releases r
LEFT JOIN artwork a ON r.release_id = a.release_id
WHERE  UPPER(r.title)  LIKE UPPER($1)
    OR UPPER(r.artist) LIKE UPPER($1)
GROUP BY
  r.release_id, r.discogs_id, r.title, r.artist, r.year,
  r.label, r.catno, r.format, r.genres, r.styles, r.producers,
  r.country, r.rating, r.condition, r.sleeve_condition, r.date_added,
  r.copies_count, r.instance_ids,
  r.community_have_count, r.community_want_count,
  r.community_average_rating, r.community_rating_count
ORDER BY r.artist, r.year
LIMIT  $2 OFFSET $3
`;

interface SearchQuery {
  q: string;
  limit?: number;
  offset?: number;
}

const search: FastifyPluginAsync = async (fastify) => {
  fastify.get<{ Querystring: SearchQuery }>('/search', {
    schema: {
      querystring: {
        type: 'object',
        required: ['q'],
        properties: {
          q:      { type: 'string', minLength: 1, maxLength: 200 },
          limit:  { type: 'integer', minimum: 1, maximum: 100, default: 20 },
          offset: { type: 'integer', minimum: 0, default: 0 },
        },
      },
    },
  }, async (request, reply) => {
    const { q, limit = 20, offset = 0 } = request.query;

    // Trim and wrap with wildcards for LIKE matching.
    const term = `%${q.trim()}%`;

    const result = await pool.query(SEARCH_QUERY, [term, limit, offset]);
    return reply.send({ releases: result.rows, count: result.rowCount });
  });
};

export default search;
