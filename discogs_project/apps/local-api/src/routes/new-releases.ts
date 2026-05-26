import { spawn } from 'child_process';
import * as path from 'path';
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

  // GET /api/new-releases
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
      if (err && typeof err === 'object' && 'code' in err && (err as { code: string }).code === '42P01') {
        return reply.send({ items: [], count: 0 });
      }
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // POST /api/new-releases/sync — runs sync_new_releases.py
  fastify.post('/new-releases/sync', async (_request, reply) => {
    const scriptDir = path.resolve(process.cwd(), '../../apps/postgres/discogs_collection_postgres_lab');
    const scriptPath = path.join(scriptDir, 'sync_new_releases.py');

    return new Promise((resolve) => {
      const proc = spawn('/Users/joeyfoley/cursor_1/discogs_project/.venv/bin/python3', [scriptPath], {
        cwd: scriptDir,
        env: { ...process.env, DISCOGS_TOKEN: process.env.DISCOGS_TOKEN ?? '', DISCOGS_USERNAME: process.env.DISCOGS_USERNAME ?? '', POSTGRES_HOST: process.env.POSTGRES_HOST ?? 'localhost', POSTGRES_PORT: process.env.POSTGRES_PORT ?? '5432', POSTGRES_USER: process.env.POSTGRES_USER ?? 'discogs_user', POSTGRES_PASSWORD: process.env.POSTGRES_PASSWORD ?? '', POSTGRES_DATABASE: process.env.POSTGRES_DATABASE ?? 'discogs_collection', POSTGRES_SCHEMA: process.env.POSTGRES_SCHEMA ?? 'collection_data' },
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

};

export default newReleasesRoutes;
