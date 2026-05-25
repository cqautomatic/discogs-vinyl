import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

const COLLECTION_QUERY = `
SELECT
  r.release_id, r.discogs_id, r.title, r.artist, r.year,
  r.label, r.catno, r.format, r.genres, r.styles,
  r.rating, r.condition, r.date_added,
  r.community_have_count, r.community_want_count,
  r.community_average_rating, r.community_rating_count,
  r.copies_count, r.instance_ids, r.producers, r.country,
  r.sleeve_condition,
  COALESCE(
    JSON_AGG(
      JSON_BUILD_OBJECT(
        'artwork_id', a.artwork_id,
        'image_type', a.image_type,
        'local_file_path', a.local_file_path,
        'thumbnail_file_path', a.thumbnail_file_path,
        'original_url', a.original_url,
        'file_size', a.file_size,
        'image_width', a.image_width,
        'image_height', a.image_height
      ) ORDER BY CASE a.image_type WHEN 'primary' THEN 0 ELSE 1 END, a.artwork_id
    ) FILTER (WHERE a.artwork_id IS NOT NULL),
    '[]'::json
  ) AS artwork_files
FROM releases r
LEFT JOIN artwork a ON r.release_id = a.release_id
WHERE LOWER(r.artist) = LOWER($1)
GROUP BY r.release_id, r.discogs_id, r.title, r.artist, r.year,
  r.label, r.catno, r.format, r.genres, r.styles,
  r.rating, r.condition, r.date_added,
  r.community_have_count, r.community_want_count,
  r.community_average_rating, r.community_rating_count,
  r.copies_count, r.instance_ids, r.producers, r.country,
  r.sleeve_condition
ORDER BY r.year DESC NULLS LAST
`;

const WANTLIST_QUERY = `
SELECT
  w.discogs_release_id, w.title, w.artist, w.year, w.label,
  w.format, w.genres, w.styles, w.notes, w.rating, w.added,
  rp.lowest_price, rp.currency, rp.num_for_sale,
  rp.availability, rp.last_seen AS price_last_seen
FROM wantlist w
LEFT JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
WHERE LOWER(w.artist) = LOWER($1)
ORDER BY rp.lowest_price ASC NULLS LAST
`;

interface ArtistParams {
  name: string;
}

const artistRoutes: FastifyPluginAsync = async (fastify) => {
  fastify.get<{ Params: ArtistParams }>('/artist/:name', {
    schema: {
      params: {
        type: 'object',
        required: ['name'],
        properties: {
          name: { type: 'string', minLength: 1, maxLength: 200 },
        },
      },
    },
  }, async (request, reply) => {
    const { name } = request.params;
    try {
      const [collectionResult, wantlistResult] = await Promise.all([
        pool.query(COLLECTION_QUERY, [name]),
        pool.query(WANTLIST_QUERY, [name]),
      ]);
      return reply.send({
        artist: name,
        collection: collectionResult.rows,
        wantlist: wantlistResult.rows,
      });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });
};

export default artistRoutes;
