/**
 * Smoke test: validates that all route modules can be imported and each
 * exports a default function (FastifyPluginAsync).
 *
 * Does NOT start a server or make any network connections.
 * pg.Pool is lazy — no TCP connection is opened until the first query.
 *
 * Run with: npm run smoke
 */

const ROUTE_MODULES = [
  '../src/routes/health',
  '../src/routes/stats',
  '../src/routes/releases',
  '../src/routes/genres',
  '../src/routes/styles',
  '../src/routes/search',
  '../src/routes/recommendations',
  '../src/routes/artist',
  '../src/routes/new-releases',
];

(async () => {
  let failed = false;

  for (const route of ROUTE_MODULES) {
    try {
      const mod = await import(route);
      if (typeof mod.default !== 'function') {
        console.error(`FAIL: ${route} — default export is not a function (got ${typeof mod.default})`);
        failed = true;
      } else {
        console.log(`OK:   ${route}`);
      }
    } catch (err) {
      console.error(`FAIL: ${route} — import threw:`, err);
      failed = true;
    }
  }

  if (failed) {
    console.error('\nSmoke check FAILED.');
    process.exit(1);
  }

  console.log('\nAll route modules OK.');
})();
