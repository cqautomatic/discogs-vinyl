import 'dotenv/config';
import * as fs from 'fs';
import * as path from 'path';
import Fastify from 'fastify';
import cors from '@fastify/cors';
import fastifyStatic from '@fastify/static';
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
import findRoutes from './routes/find';
import pressingsRoutes from './routes/pressings';
import storeCheckRoutes from './routes/store-check';
import coverScanRoutes from './routes/cover-scan';

const PORT = parseInt(process.env.PORT ?? '3001', 10);

// Allow localhost dev, the Vercel PWA, and any local-network origin (192.168.x.x / 10.x.x.x)
const CORS_ORIGINS = [
  /^http:\/\/localhost(:\d+)?$/,
  /^http:\/\/127\.0\.0\.1(:\d+)?$/,
  /^https?:\/\/.*\.vercel\.app$/,
  /^https?:\/\/192\.168\.\d+\.\d+(:\d+)?$/,
  /^https?:\/\/10\.\d+\.\d+\.\d+(:\d+)?$/,
  /^https?:\/\/100\.\d+\.\d+\.\d+(:\d+)?$/,  // Tailscale IP
  /^https:\/\/[\w-]+\.[\w-]+\.ts\.net$/,     // Tailscale Serve (MagicDNS)
];

// Built React frontend — served same-origin so the iPhone PWA needs no API URL config
const FRONTEND_DIST = path.resolve(process.cwd(), '../react-frontend/dist');

const fastify = Fastify({ logger: true });

async function start(): Promise<void> {
  await fastify.register(cors, { origin: CORS_ORIGINS });

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
  await fastify.register(findRoutes,       { prefix: '/api' });
  await fastify.register(pressingsRoutes,  { prefix: '/api' });
  await fastify.register(storeCheckRoutes, { prefix: '/api' });
  await fastify.register(coverScanRoutes,  { prefix: '/api' });

  if (fs.existsSync(FRONTEND_DIST)) {
    await fastify.register(fastifyStatic, { root: FRONTEND_DIST });
    // SPA fallback — unknown non-API GETs get index.html
    fastify.setNotFoundHandler((request, reply) => {
      if (request.method === 'GET' && !request.url.startsWith('/api') && !request.url.startsWith('/artwork')) {
        return reply.sendFile('index.html');
      }
      return reply.status(404).send({ error: 'Not found' });
    });
  } else {
    fastify.log.warn(`Frontend dist not found at ${FRONTEND_DIST} — serving API only`);
  }

  await fastify.listen({ port: PORT, host: '0.0.0.0' });
}

start().catch((err: unknown) => {
  fastify.log.error(err);
  process.exit(1);
});
