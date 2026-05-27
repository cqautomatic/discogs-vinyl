import 'dotenv/config';
import Fastify from 'fastify';
import cors from '@fastify/cors';
import healthRoutes from './routes/health';
import statsRoutes from './routes/stats';
import releasesRoutes from './routes/releases';
import artworkRoutes from './routes/artwork';
import genresRoutes from './routes/genres';
import stylesRoutes from './routes/styles';
import searchRoutes from './routes/search';
import recommendationsRoutes from './routes/recommendations';
import artistRoutes from './routes/artist';
import newReleasesRoutes from './routes/new-releases';
import discoverRoutes from './routes/discover';
import syncRoutes from './routes/sync';

const PORT = parseInt(process.env.PORT ?? '3001', 10);
const CORS_ORIGIN = process.env.CORS_ORIGIN ?? 'http://localhost:5173';

const fastify = Fastify({ logger: true });

async function start(): Promise<void> {
  await fastify.register(cors, { origin: CORS_ORIGIN });

  await fastify.register(healthRoutes);
  await fastify.register(artworkRoutes);
  await fastify.register(statsRoutes, { prefix: '/api' });
  await fastify.register(releasesRoutes, { prefix: '/api' });
  await fastify.register(genresRoutes, { prefix: '/api' });
  await fastify.register(stylesRoutes, { prefix: '/api' });
  await fastify.register(searchRoutes, { prefix: '/api' });
  await fastify.register(recommendationsRoutes, { prefix: '/api' });
  await fastify.register(artistRoutes, { prefix: '/api' });
  await fastify.register(newReleasesRoutes, { prefix: '/api' });
  await fastify.register(discoverRoutes,   { prefix: '/api' });
  await fastify.register(syncRoutes,       { prefix: '/api' });

  await fastify.listen({ port: PORT, host: '0.0.0.0' });
}

start().catch((err: unknown) => {
  fastify.log.error(err);
  process.exit(1);
});
