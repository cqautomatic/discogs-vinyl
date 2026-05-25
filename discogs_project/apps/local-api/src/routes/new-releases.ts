import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

const NEW_RELEASES_QUERY = `
SELECT
  nrf.id, nrf.discogs_release_id, nrf.title, nrf.artist,
  nrf.year, nrf.label, nrf.format, nrf.genres,
  nrf.country, nrf.source, nrf.discovered_at
FROM new_releases_feed nrf
LEFT JOIN releases r ON r.discogs_id = nrf.discogs_release_id
WHERE r.release_id IS NULL
ORDER BY nrf.discovered_at DESC
LIMIT $1
`;

interface NewReleasesQuery {
  limit?: number;
}

const newReleasesRoutes: FastifyPluginAsync = async (fastify) => {
  fastify.get<{ Querystring: NewReleasesQuery }>('/new-releases', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          limit: { type: 'integer', minimum: 1, maximum: 100, default: 20 },
        },
      },
    },
  }, async (request, reply) => {
    const { limit = 20 } = request.query;
    try {
      const result = await pool.query(NEW_RELEASES_QUERY, [limit]);
      return reply.send({ items: result.rows, count: result.rowCount ?? 0 });
    } catch (err: unknown) {
      // Gracefully handle missing table (before migration runs)
      if (
        err &&
        typeof err === 'object' &&
        'code' in err &&
        (err as { code: string }).code === '42P01'
      ) {
        return reply.send({ items: [], count: 0 });
      }
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });
};

export default newReleasesRoutes;
