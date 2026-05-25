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

    // Artwork is in the project root
    const artworkDir = path.join(process.cwd(), 'artwork');
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

    return reply.sendFile(filepath);
  });
};

export default artwork;
