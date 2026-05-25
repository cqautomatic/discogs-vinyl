import 'dotenv/config';
import { Client } from 'pg';
import * as fs from 'fs';
import * as path from 'path';

const migrationsDir = path.resolve(__dirname, '../../../db/migrations');

async function main(): Promise<void> {
  const client = new Client({
    host:     process.env.POSTGRES_HOST     ?? 'localhost',
    port:     parseInt(process.env.POSTGRES_PORT ?? '5432', 10),
    user:     process.env.POSTGRES_USER     ?? 'discogs_user',
    password: process.env.POSTGRES_PASSWORD,
    database: process.env.POSTGRES_DATABASE ?? 'discogs_collection',
  });

  await client.connect();

  try {
    // Ensure schema exists
    await client.query('CREATE SCHEMA IF NOT EXISTS collection_data');

    // Ensure tracking table exists
    await client.query(`
      CREATE TABLE IF NOT EXISTS collection_data.schema_migrations (
        name       TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ DEFAULT NOW()
      )
    `);

    // Read and sort migration files
    const files = fs.readdirSync(migrationsDir)
      .filter(f => f.endsWith('.sql'))
      .sort();

    let applied = 0;
    let skipped = 0;

    for (const file of files) {
      // Check if already applied
      const { rows } = await client.query(
        'SELECT 1 FROM collection_data.schema_migrations WHERE name = $1',
        [file]
      );

      if (rows.length > 0) {
        console.log(`[SKIP] ${file}`);
        skipped++;
        continue;
      }

      console.log(`[APPLY] ${file}`);
      const sql = fs.readFileSync(path.join(migrationsDir, file), 'utf8');

      try {
        await client.query('BEGIN');
        await client.query(sql);
        await client.query(
          'INSERT INTO collection_data.schema_migrations (name) VALUES ($1)',
          [file]
        );
        await client.query('COMMIT');
        applied++;
      } catch (err) {
        await client.query('ROLLBACK');
        const message = err instanceof Error ? err.message : String(err);
        console.error(`[ERROR] ${file}: ${message}`);
        process.exit(1);
      }
    }

    console.log(`Migration complete. ${applied} applied, ${skipped} skipped.`);
  } finally {
    await client.end();
  }
}

main().catch(err => {
  console.error('Unexpected error:', err);
  process.exit(1);
});
