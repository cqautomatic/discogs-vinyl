import * as path from 'path';
import * as fs from 'fs/promises';
import { FastifyPluginAsync } from 'fastify';

const MIME: Record<string, string> = {
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
};

const artwork: FastifyPluginAsync = async (fastify) => {
  fastify.get('/artwork/:filename', async (request, reply) => {
    const { filename } = request.params as { filename: string };

    if (filename.includes('..') || filename.includes('/')) {
      return reply.status(400).send({ error: 'Invalid filename' });
    }

    const artworkDir = path.resolve(process.cwd(), '../../artwork');
    const filepath = path.join(artworkDir, filename);

    try {
      await fs.access(filepath);
    } catch {
      return reply.status(404).send({ error: 'Not found' });
    }

    // Resolve symlinks and verify containment (with sep to prevent sibling-dir bypass)
    const [realFile, realDir] = await Promise.all([
      fs.realpath(filepath),
      fs.realpath(artworkDir),
    ]);
    if (!realFile.startsWith(realDir + path.sep)) {
      return reply.status(403).send({ error: 'Forbidden' });
    }

    const ext = path.extname(filename).toLowerCase();
    const mime = MIME[ext] ?? 'application/octet-stream';
    const buffer = await fs.readFile(realFile);
    reply.type(mime);
    return reply.send(buffer);
  });
};

export default artwork;
