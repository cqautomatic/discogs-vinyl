import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

// Columns selected on every releases list/detail query.
// Must stay in sync with GROUP_BY_COLS below.
const RELEASE_COLS = [
  'r.release_id', 'r.discogs_id', 'r.title', 'r.artist', 'r.year',
  'r.label', 'r.catno', 'r.format', 'r.genres', 'r.styles', 'r.producers',
  'r.country', 'r.rating', 'r.condition', 'r.sleeve_condition', 'r.date_added',
  'r.copies_count', 'r.instance_ids',
  'r.community_have_count', 'r.community_want_count',
  'r.community_average_rating', 'r.community_rating_count',
].join(', ');

const GROUP_BY_COLS = [
  'r.release_id', 'r.discogs_id', 'r.title', 'r.artist', 'r.year',
  'r.label', 'r.catno', 'r.format', 'r.genres', 'r.styles', 'r.producers',
  'r.country', 'r.rating', 'r.condition', 'r.sleeve_condition', 'r.date_added',
  'r.copies_count', 'r.instance_ids',
  'r.community_have_count', 'r.community_want_count',
  'r.community_average_rating', 'r.community_rating_count',
].join(', ');

// Artwork aggregation fragment — produces a JSON array sorted primary-first.
const ARTWORK_AGG = `
  COALESCE(
    JSON_AGG(
      JSON_BUILD_OBJECT(
        'artwork_id',         a.artwork_id,
        'image_type',         a.image_type,
        'local_file_path',    a.local_file_path,
        'thumbnail_file_path', a.thumbnail_file_path,
        'original_url',       a.original_url,
        'file_size',          a.file_size,
        'image_width',        a.image_width,
        'image_height',       a.image_height
      ) ORDER BY CASE a.image_type WHEN 'primary' THEN 0 ELSE 1 END, a.artwork_id
    ) FILTER (WHERE a.artwork_id IS NOT NULL),
    '[]'::json
  ) AS artwork_files
`;

// ── Sort helpers ──────────────────────────────────────────────────────────────

type SortOption = 'artist_year' | 'date_added' | 'year' | 'title';

function orderByClause(sort?: SortOption): string {
  switch (sort) {
    case 'date_added': return 'r.date_added DESC NULLS LAST';
    case 'year':       return 'r.year DESC NULLS LAST, r.artist';
    case 'title':      return 'r.title, r.artist';
    default:           return 'r.artist, r.year';           // artist_year (default)
  }
}

// ── Query builders ────────────────────────────────────────────────────────────

function listAllQuery(sort?: SortOption): string {
  return `
    SELECT ${RELEASE_COLS}, ${ARTWORK_AGG}
    FROM   releases r
    LEFT JOIN artwork a ON r.release_id = a.release_id
    GROUP BY ${GROUP_BY_COLS}
    ORDER BY ${orderByClause(sort)}
    LIMIT $1 OFFSET $2
  `;
}

// Generic filtered query: builds WHERE clause dynamically from active filters
function listFilteredQuery(filters: {
  genre?: string; style?: string; label?: string; year?: number; country?: string; artist?: string;
}, sort?: SortOption): { sql: string; params: (string | number)[] } {
  const conditions: string[] = [];
  const params: (string | number)[] = [];
  const joins: string[] = [];

  if (filters.genre) {
    params.push(filters.genre);
    joins.push(`LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS g(val)`);
    conditions.push(`g.val = $${params.length}`);
  }
  if (filters.style) {
    params.push(filters.style);
    joins.push(`LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS s(val)`);
    conditions.push(`s.val = $${params.length}`);
  }
  if (filters.label) {
    params.push(filters.label);
    conditions.push(`r.label = $${params.length}`);
  }
  if (filters.year) {
    params.push(filters.year);
    conditions.push(`r.year = $${params.length}`);
  }
  if (filters.country) {
    params.push(filters.country);
    conditions.push(`r.country = $${params.length}`);
  }
  if (filters.artist) {
    params.push(filters.artist);
    conditions.push(`r.artist = $${params.length}`);
  }

  const limitIdx = params.length + 1;
  const offsetIdx = params.length + 2;

  const sql = `
    SELECT ${RELEASE_COLS}, ${ARTWORK_AGG}
    FROM   releases r
    LEFT JOIN artwork a ON r.release_id = a.release_id
    ${joins.map(j => `, ${j}`).join('\n')}
    ${conditions.length ? 'WHERE ' + conditions.join(' AND ') : ''}
    GROUP BY ${GROUP_BY_COLS}
    ORDER BY ${orderByClause(sort)}
    LIMIT $${limitIdx} OFFSET $${offsetIdx}
  `;
  return { sql, params };
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface ReleasesQuery {
  limit?: number;
  offset?: number;
  genre?: string;
  style?: string;
  label?: string;
  year?: number;
  country?: string;
  artist?: string;
  sort?: SortOption;
}

// ── Plugin ────────────────────────────────────────────────────────────────────

const releases: FastifyPluginAsync = async (fastify) => {

  // GET /api/releases
  fastify.get<{ Querystring: ReleasesQuery }>('/releases', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          limit:   { type: 'integer', minimum: 1, maximum: 100, default: 20 },
          offset:  { type: 'integer', minimum: 0, default: 0 },
          genre:   { type: 'string', maxLength: 100 },
          style:   { type: 'string', maxLength: 100 },
          label:   { type: 'string', maxLength: 200 },
          year:    { type: 'integer', minimum: 1900, maximum: 2100 },
          country: { type: 'string', maxLength: 100 },
          artist:  { type: 'string', maxLength: 300 },
          sort:    { type: 'string', enum: ['artist_year', 'date_added', 'year', 'title'] },
        },
      },
    },
  }, async (request, reply) => {
    const { limit = 20, offset = 0, genre, style, label, year, country, artist, sort } = request.query;

    let result;
    const hasFilter = genre || style || label || year || country || artist;
    if (hasFilter) {
      const { sql, params } = listFilteredQuery({ genre, style, label, year, country, artist }, sort);
      result = await pool.query(sql, [...params, limit, offset]);
    } else {
      result = await pool.query(listAllQuery(sort), [limit, offset]);
    }

    return reply.send({ releases: result.rows, count: result.rowCount });
  });

  // GET /api/releases/:id
  fastify.get('/releases/:id', async (request, reply) => {
    const rawId = (request.params as { id: string }).id;
    const id = parseInt(rawId, 10);
    if (isNaN(id) || id < 1) {
      return reply.status(400).send({ error: 'id must be a positive integer' });
    }

    const releaseResult = await pool.query(`
      SELECT ${RELEASE_COLS}, r.stats_last_updated, ${ARTWORK_AGG}
      FROM   releases r
      LEFT JOIN artwork a ON r.release_id = a.release_id
      WHERE  r.discogs_id = $1
      GROUP BY ${GROUP_BY_COLS}, r.stats_last_updated
    `, [id]);

    if (releaseResult.rows.length === 0) {
      return reply.status(404).send({ error: 'Release not found' });
    }

    // Fetch marketplace / pricing data separately (joined on discogs_id)
    let statsRow = {};
    try {
      const statsResult = await pool.query(`
        SELECT
          ms.last_sold_date,
          ms.low_sold_price,
          ms.high_sold_price,
          ms.currency      AS ms_currency,
          ms.as_of         AS marketplace_as_of,
          rp.num_for_sale,
          rp.lowest_price,
          rp.currency      AS rp_currency,
          rp.last_seen
        FROM   releases r
        LEFT JOIN marketplace_stats_dim ms ON ms.discogs_release_id = r.discogs_id
        LEFT JOIN release_prices        rp ON rp.discogs_release_id = r.discogs_id
        WHERE  r.discogs_id = $1
        LIMIT  1
      `, [id]);
      statsRow = statsResult.rows[0] ?? {};
    } catch (err) {
      fastify.log.warn({ err, id }, 'stats query failed — returning release without pricing');
    }

    return reply.send({
      ...releaseResult.rows[0],
      ...statsRow,
    });
  });
};

export default releases;
