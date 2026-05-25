import { Pool } from 'pg';

const schema = process.env.POSTGRES_SCHEMA ?? 'collection_data';

export const pool = new Pool({
  host: process.env.POSTGRES_HOST ?? 'localhost',
  port: parseInt(process.env.POSTGRES_PORT ?? '5432', 10),
  user: process.env.POSTGRES_USER ?? 'discogs_user',
  password: process.env.POSTGRES_PASSWORD,
  database: process.env.POSTGRES_DATABASE ?? 'discogs_collection',
});

// Set search_path on every new connection so queries can omit the schema prefix.
// Using double-quoted identifier to handle names with uppercase or special chars.
pool.on('connect', (client) => {
  client.query(`SET search_path TO "${schema}", public`).catch(() => {});
});
