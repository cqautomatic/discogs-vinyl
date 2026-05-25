import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

const health: FastifyPluginAsync = async (fastify) => {
  fastify.get('/health', async (_request, reply) => {
    try {
      await pool.query('SELECT 1');
      return reply.send({ status: 'ok', db: 'connected' });
    } catch (_err) {
      return reply.status(503).send({ status: 'error', db: 'disconnected' });
    }
  });
};

export default health;
