import { FastifyPluginAsync } from 'fastify';
import { pool } from '../db';

// ── Query strings ─────────────────────────────────────────────────────────────

const WANTLIST_QUERY = `
SELECT
  w.discogs_release_id, w.title, w.artist, w.year, w.label, w.format,
  w.genres, w.styles, w.notes, w.rating, w.added,
  rp.lowest_price, rp.currency, rp.num_for_sale, rp.availability,
  rp.last_seen AS price_last_seen
FROM wantlist w
LEFT JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
ORDER BY
  CASE WHEN rp.availability = true THEN 0 ELSE 1 END,
  rp.lowest_price ASC NULLS LAST,
  w.added DESC
LIMIT $1
`;

const BUDGET_QUERY = `
SELECT
  w.discogs_release_id, w.title, w.artist, w.year, w.label, w.format,
  w.genres, w.styles,
  rp.lowest_price, rp.currency, rp.num_for_sale,
  'wantlist' AS source
FROM wantlist w
INNER JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
WHERE rp.lowest_price <= $1
  AND rp.availability = true
  AND rp.lowest_price IS NOT NULL
ORDER BY rp.lowest_price ASC
LIMIT $2
`;

const HIGH_DEMAND_QUERY = `
SELECT
  release_id, title, artist, year, label,
  community_want_count, community_have_count,
  ROUND(
    (community_want_count::decimal / NULLIF(community_have_count, 0))::numeric, 2
  ) AS want_have_ratio
FROM releases
WHERE community_want_count > 0
  AND community_have_count > 0
ORDER BY
  (community_want_count::decimal / NULLIF(community_have_count, 0)) DESC NULLS LAST,
  community_want_count DESC
LIMIT $1
`;

const LABEL_GAPS_QUERY = `
SELECT
  label,
  COUNT(*) AS owned_releases,
  COUNT(DISTINCT artist) AS unique_artists,
  ROUND(AVG(CASE WHEN rating > 0 THEN rating END)::numeric, 1) AS avg_rating
FROM releases
WHERE label IS NOT NULL AND label != ''
GROUP BY label
HAVING COUNT(*) >= 2
ORDER BY avg_rating DESC NULLS LAST, owned_releases DESC
LIMIT $1
`;

const DECADE_GAPS_QUERY = `
SELECT
  (year / 10) * 10 AS decade_start,
  ((year / 10) * 10)::text || 's' AS decade_label,
  COUNT(*) AS releases_owned,
  MIN(year) AS earliest_year,
  MAX(year) AS latest_year,
  COUNT(DISTINCT year) AS unique_years,
  ROUND(
    COUNT(DISTINCT year)::decimal /
    NULLIF(MAX(year) - MIN(year) + 1, 0) * 100, 1
  ) AS coverage_pct
FROM releases
WHERE year IS NOT NULL AND year >= 1920
GROUP BY (year / 10) * 10
ORDER BY decade_start DESC
`;

const SIMILAR_ARTISTS_QUERY = `
WITH my_labels AS (
  SELECT DISTINCT label FROM releases WHERE label IS NOT NULL AND label != ''
),
my_genres AS (
  SELECT DISTINCT jsonb_array_elements_text(COALESCE(genres, '[]'::jsonb)) AS genre
  FROM releases
),
my_artists AS (
  SELECT DISTINCT LOWER(TRIM(artist)) AS artist FROM releases WHERE artist IS NOT NULL
)
SELECT
  w.artist,
  COUNT(DISTINCT w.discogs_release_id) AS wantlist_count,
  ARRAY_AGG(DISTINCT w.label) FILTER (WHERE w.label IN (SELECT label FROM my_labels)) AS shared_labels
FROM wantlist w
WHERE LOWER(TRIM(w.artist)) NOT IN (SELECT artist FROM my_artists)
  AND w.artist IS NOT NULL AND w.artist != ''
  AND (
    w.label IN (SELECT label FROM my_labels)
    OR EXISTS (
      SELECT 1 FROM jsonb_array_elements_text(COALESCE(w.genres, '[]'::jsonb)) g
      WHERE g IN (SELECT genre FROM my_genres)
    )
  )
GROUP BY w.artist
ORDER BY wantlist_count DESC
LIMIT $1
`;

const ARTIST_GAPS_QUERY = `
SELECT
  artist,
  COUNT(*) AS owned_releases,
  ROUND(AVG(CASE WHEN rating > 0 THEN rating END)::numeric, 1) AS avg_rating
FROM releases
WHERE artist IS NOT NULL AND artist != ''
GROUP BY artist
HAVING COUNT(*) >= 2
ORDER BY COUNT(*) ASC, owned_releases ASC
LIMIT $1
`;

const AFFORDABLE_GRAILS_QUERY = `
SELECT
  w.discogs_release_id, w.title, w.artist, w.year, w.label, w.format,
  w.genres, w.styles,
  rp.lowest_price, rp.currency, rp.num_for_sale,
  r.community_want_count, r.community_have_count,
  ROUND(
    (r.community_want_count::decimal / NULLIF(r.community_have_count, 0))::numeric, 2
  ) AS want_have_ratio
FROM wantlist w
LEFT JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
LEFT JOIN releases r ON r.discogs_id = w.discogs_release_id
WHERE rp.lowest_price IS NOT NULL
  AND rp.lowest_price <= $1
  AND rp.availability = true
  AND r.community_have_count > 0
  AND (r.community_want_count::decimal / NULLIF(r.community_have_count, 0)) >= $2
ORDER BY want_have_ratio DESC, rp.lowest_price ASC
LIMIT $3
`;

const HEALTH_QUERY = `
SELECT
  COUNT(*) AS total_wantlist,
  COUNT(CASE WHEN rp.availability = true THEN 1 END) AS available_now,
  ROUND(
    COALESCE(SUM(CASE WHEN rp.availability = true THEN rp.lowest_price END), 0)::numeric, 2
  ) AS total_available_value,
  COUNT(CASE WHEN rp.lowest_price <= 20 AND rp.availability = true THEN 1 END) AS items_under_20,
  ROUND(
    COALESCE(AVG(CASE WHEN rp.availability = true THEN rp.lowest_price END), 0)::numeric, 2
  ) AS avg_available_price
FROM wantlist w
LEFT JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
`;

const COMPLETE_DECADE_QUERY = `
WITH decade_coverage AS (
  SELECT
    (year / 10) * 10 AS decade_start,
    COUNT(*) AS releases_owned
  FROM releases
  WHERE year IS NOT NULL
  GROUP BY (year / 10) * 10
  ORDER BY releases_owned ASC
  LIMIT 2
)
SELECT
  w.discogs_release_id, w.title, w.artist, w.year, w.label, w.format,
  w.genres, w.styles,
  rp.lowest_price, rp.currency, rp.num_for_sale, rp.availability,
  dc.decade_start,
  dc.decade_start::text || 's' AS decade_label,
  dc.releases_owned
FROM wantlist w
LEFT JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
INNER JOIN decade_coverage dc ON (w.year / 10) * 10 = dc.decade_start
WHERE w.year IS NOT NULL
ORDER BY rp.lowest_price ASC NULLS LAST, w.year ASC
LIMIT $1
`;

const GENRE_VALUE_MAP_QUERY = `
WITH wantlist_genres AS (
  SELECT
    w.discogs_release_id,
    g.genre,
    rp.lowest_price
  FROM wantlist w
  CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(w.genres, '[]'::jsonb)) AS g(genre)
  LEFT JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
  WHERE g.genre IS NOT NULL AND g.genre != ''
),
release_ratings AS (
  SELECT
    g.genre,
    r.community_average_rating
  FROM releases r
  CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS g(genre)
  WHERE r.community_average_rating IS NOT NULL
    AND r.community_average_rating > 0
    AND g.genre IS NOT NULL AND g.genre != ''
)
SELECT
  wg.genre,
  COUNT(*) AS wantlist_count,
  ROUND(AVG(wg.lowest_price)::numeric, 2) AS avg_price,
  ROUND(AVG(rr.community_average_rating)::numeric, 2) AS avg_rating
FROM wantlist_genres wg
LEFT JOIN release_ratings rr ON wg.genre = rr.genre
WHERE wg.genre IS NOT NULL AND wg.genre != ''
GROUP BY wg.genre
HAVING COUNT(*) >= 1
ORDER BY avg_rating DESC NULLS LAST, avg_price ASC NULLS LAST
`;

// ── Types ─────────────────────────────────────────────────────────────────────

interface LimitQuery {
  limit?: number;
}

interface BudgetQuery {
  max_price?: number;
  limit?: number;
}

interface AffordableGrailsQuery {
  max_price?: number;
  min_ratio?: number;
  limit?: number;
}

// ── Plugin ────────────────────────────────────────────────────────────────────

const recommendations: FastifyPluginAsync = async (fastify) => {

  // GET /api/recommendations/wantlist
  fastify.get<{ Querystring: LimitQuery }>('/recommendations/wantlist', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          limit: { type: 'integer', minimum: 1, maximum: 200, default: 50 },
        },
      },
    },
  }, async (request, reply) => {
    const { limit = 50 } = request.query;
    try {
      const result = await pool.query(WANTLIST_QUERY, [limit]);
      return reply.send({ items: result.rows, count: result.rowCount });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // GET /api/recommendations/budget
  fastify.get<{ Querystring: BudgetQuery }>('/recommendations/budget', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          max_price: { type: 'number', minimum: 0, default: 50 },
          limit: { type: 'integer', minimum: 1, maximum: 200, default: 20 },
        },
      },
    },
  }, async (request, reply) => {
    const { max_price = 50, limit = 20 } = request.query;
    try {
      const result = await pool.query(BUDGET_QUERY, [max_price, limit]);
      return reply.send({ items: result.rows, count: result.rowCount });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // GET /api/recommendations/high-demand
  fastify.get<{ Querystring: LimitQuery }>('/recommendations/high-demand', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          limit: { type: 'integer', minimum: 1, maximum: 200, default: 20 },
        },
      },
    },
  }, async (request, reply) => {
    const { limit = 20 } = request.query;
    try {
      const result = await pool.query(HIGH_DEMAND_QUERY, [limit]);
      return reply.send({ items: result.rows, count: result.rowCount });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // GET /api/recommendations/label-gaps
  fastify.get<{ Querystring: LimitQuery }>('/recommendations/label-gaps', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          limit: { type: 'integer', minimum: 1, maximum: 200, default: 15 },
        },
      },
    },
  }, async (request, reply) => {
    const { limit = 15 } = request.query;
    try {
      const result = await pool.query(LABEL_GAPS_QUERY, [limit]);
      return reply.send({ labels: result.rows, count: result.rowCount });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // GET /api/recommendations/decade-gaps
  fastify.get('/recommendations/decade-gaps', async (_request, reply) => {
    try {
      const result = await pool.query(DECADE_GAPS_QUERY);
      return reply.send({ decades: result.rows });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // GET /api/recommendations/similar-artists
  fastify.get<{ Querystring: LimitQuery }>('/recommendations/similar-artists', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          limit: { type: 'integer', minimum: 1, maximum: 200, default: 20 },
        },
      },
    },
  }, async (request, reply) => {
    const { limit = 20 } = request.query;
    try {
      const result = await pool.query(SIMILAR_ARTISTS_QUERY, [limit]);
      return reply.send({ artists: result.rows, count: result.rowCount });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // GET /api/recommendations/artist-gaps
  fastify.get<{ Querystring: LimitQuery }>('/recommendations/artist-gaps', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          limit: { type: 'integer', minimum: 1, maximum: 200, default: 20 },
        },
      },
    },
  }, async (request, reply) => {
    const { limit = 20 } = request.query;
    try {
      const result = await pool.query(ARTIST_GAPS_QUERY, [limit]);
      return reply.send({ artists: result.rows, count: result.rowCount });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // GET /api/recommendations/affordable-grails
  fastify.get<{ Querystring: AffordableGrailsQuery }>('/recommendations/affordable-grails', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          max_price: { type: 'number', minimum: 0, default: 25 },
          min_ratio: { type: 'number', minimum: 0, default: 2.0 },
          limit: { type: 'integer', minimum: 1, maximum: 200, default: 20 },
        },
      },
    },
  }, async (request, reply) => {
    const { max_price = 25, min_ratio = 2.0, limit = 20 } = request.query;
    try {
      const result = await pool.query(AFFORDABLE_GRAILS_QUERY, [max_price, min_ratio, limit]);
      return reply.send({ items: result.rows, count: result.rowCount });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // GET /api/recommendations/health
  fastify.get('/recommendations/health', async (_request, reply) => {
    try {
      const result = await pool.query(HEALTH_QUERY);
      return reply.send({ health: result.rows[0] ?? {} });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // GET /api/recommendations/complete-decade
  fastify.get<{ Querystring: LimitQuery }>('/recommendations/complete-decade', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          limit: { type: 'integer', minimum: 1, maximum: 200, default: 20 },
        },
      },
    },
  }, async (request, reply) => {
    const { limit = 20 } = request.query;
    try {
      const result = await pool.query(COMPLETE_DECADE_QUERY, [limit]);
      return reply.send({ items: result.rows, count: result.rowCount });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // GET /api/recommendations/genre-value-map
  fastify.get('/recommendations/genre-value-map', async (_request, reply) => {
    try {
      const result = await pool.query(GENRE_VALUE_MAP_QUERY);
      return reply.send({ genres: result.rows });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });
};

export default recommendations;
