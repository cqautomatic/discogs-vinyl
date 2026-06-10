/**
 * POST /api/cover-scan
 * Accepts a base64 JPEG of an album cover, uses Claude Vision to identify
 * the artist and title, then returns the identification so the caller can
 * run a store-check search.
 *
 * Requires ANTHROPIC_API_KEY in the environment.
 */

import { FastifyPluginAsync } from 'fastify';

interface AnthropicMessage {
  content: Array<{ type: string; text?: string }>;
}

async function identifyCover(base64Jpeg: string): Promise<{ artist: string; title: string; catno: string }> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error('ANTHROPIC_API_KEY not configured');

  const resp = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 150,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'image',
              source: { type: 'base64', media_type: 'image/jpeg', data: base64Jpeg },
            },
            {
              type: 'text',
              text: 'This is either a vinyl record label (the center of the record) or a record cover. Read every piece of text visible. Extract the artist name, album or release title, and catalog number (usually printed near the edge of the label or on the spine — looks like letters+numbers e.g. "ABCD-1234" or "CTI 6001"). Respond with JSON only, no other text: {"artist": "...", "title": "...", "catno": "..."}. Use empty string for any field you cannot find.',
            },
          ],
        },
      ],
    }),
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Anthropic API error ${resp.status}: ${body.slice(0, 200)}`);
  }

  const data = (await resp.json()) as AnthropicMessage;
  const text = data.content.find(c => c.type === 'text')?.text ?? '';

  // Parse the whole response first; fall back to the outermost brace span
  // (handles markdown fences and any nested objects the model adds).
  let parsed: { artist?: unknown; title?: unknown; catno?: unknown };
  try {
    parsed = JSON.parse(text) as typeof parsed;
  } catch {
    const start = text.indexOf('{');
    const end = text.lastIndexOf('}');
    if (start === -1 || end <= start) throw new Error(`Could not parse artist/title from: ${text}`);
    parsed = JSON.parse(text.slice(start, end + 1)) as typeof parsed;
  }
  return {
    artist: typeof parsed.artist === 'string' ? parsed.artist : '',
    title:  typeof parsed.title  === 'string' ? parsed.title  : '',
    catno:  typeof parsed.catno  === 'string' ? parsed.catno  : '',
  };
}

const coverScanRoutes: FastifyPluginAsync = async (fastify) => {
  fastify.post<{ Body: { image: string } }>('/cover-scan', {
    schema: {
      body: {
        type: 'object',
        required: ['image'],
        properties: {
          image: { type: 'string', minLength: 1 },
        },
      },
    },
  }, async (request, reply) => {
    if (!process.env.ANTHROPIC_API_KEY) {
      return reply.code(503).send({ error: 'Cover scan not configured — add ANTHROPIC_API_KEY to .env' });
    }

    try {
      const { artist, title, catno } = await identifyCover(request.body.image);
      if (!artist && !title && !catno) {
        return reply.code(422).send({ error: 'Could not identify an album in that photo' });
      }
      return reply.send({ artist, title, catno });
    } catch (err: unknown) {
      fastify.log.error(err);
      const msg = err instanceof Error ? err.message : 'Cover scan failed';
      return reply.code(500).send({ error: msg });
    }
  });
};

export default coverScanRoutes;
