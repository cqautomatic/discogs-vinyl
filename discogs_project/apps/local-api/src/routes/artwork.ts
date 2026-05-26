import * as path from 'path';
import * as fs from 'fs';
import { FastifyPluginAsync } from 'fastify';

const artwork: FastifyPluginAsync = async (fastify) => {
  fastify.get('/artwork/:filename', async (request, reply) => {
    const { filename } = request.params as { filename: string };

    // Prevent directory traversal
    if (filename.includes('..') || filename.includes('/')) {
      return reply.status(400).send({ error: 'Invalid filename' });
    }

    // Artwork is in the project root (relative to src being in src/)
    const artworkDir = path.resolve(__dirname, '../../../../artwork');
    const filepath = path.join(artworkDir, filename);

    if (!fs.existsSync(filepath)) {
      return reply.status(404).send({ error: 'Not found' });
    }

    // Verify file is in artwork dir (prevent traversal)
    const realpath = fs.realpathSync(filepath);
    const artworkDirReal = fs.realpathSync(artworkDir);
    if (!realpath.startsWith(artworkDirReal)) {
      return reply.status(403).send({ error: 'Forbidden' });
    }

    const buffer = fs.readFileSync(filepath);
    reply.type('image/jpeg');
    return reply.send(buffer);
  });
};

export default artwork;
