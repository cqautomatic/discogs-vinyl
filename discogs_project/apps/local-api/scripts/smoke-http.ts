/**
 * Live HTTP smoke test — requires the local-api server to be running.
 * Usage: npm run smoke:http
 * Or:    API_BASE=http://localhost:3001 npm run smoke:http
 *
 * All endpoints are tested for HTTP 200 + correct response shape.
 * Exits 0 on full pass, 1 on any failure.
 */

const API_BASE = process.env.API_BASE ?? 'http://localhost:3001';

interface EndpointCheck {
  path: string;
  validate: (body: unknown) => boolean;
}

const ENDPOINTS: EndpointCheck[] = [
  {
    path: '/health',
    validate: (body) => typeof body === 'object' && body !== null && 'status' in body,
  },
  {
    path: '/api/stats',
    validate: (body) => typeof body === 'object' && body !== null && !Array.isArray(body),
  },
  {
    path: '/api/releases?limit=1',
    validate: (body) => typeof body === 'object' && body !== null && 'releases' in body && Array.isArray((body as Record<string, unknown>).releases),
  },
  {
    path: '/api/genres',
    validate: (body) => typeof body === 'object' && body !== null && 'genres' in body && Array.isArray((body as Record<string, unknown>).genres),
  },
  {
    path: '/api/styles',
    validate: (body) => typeof body === 'object' && body !== null && 'styles' in body && Array.isArray((body as Record<string, unknown>).styles),
  },
  {
    path: '/api/search?q=test',
    validate: (body) => typeof body === 'object' && body !== null && 'releases' in body && Array.isArray((body as Record<string, unknown>).releases),
  },
  {
    path: '/api/recommendations/wantlist?limit=1',
    validate: (body) => typeof body === 'object' && body !== null && 'items' in body && Array.isArray((body as Record<string, unknown>).items),
  },
  {
    path: '/api/recommendations/budget?max_price=100&limit=1',
    validate: (body) => typeof body === 'object' && body !== null && 'items' in body && Array.isArray((body as Record<string, unknown>).items),
  },
  {
    path: '/api/recommendations/high-demand?limit=1',
    validate: (body) => typeof body === 'object' && body !== null && 'items' in body && Array.isArray((body as Record<string, unknown>).items),
  },
  {
    path: '/api/recommendations/label-gaps?limit=5',
    validate: (body) => typeof body === 'object' && body !== null && 'labels' in body && Array.isArray((body as Record<string, unknown>).labels),
  },
  {
    path: '/api/recommendations/decade-gaps',
    validate: (body) => typeof body === 'object' && body !== null && 'decades' in body && Array.isArray((body as Record<string, unknown>).decades),
  },
  {
    path: '/api/recommendations/similar-artists?limit=5',
    validate: (body) => typeof body === 'object' && body !== null && 'artists' in body && Array.isArray((body as Record<string, unknown>).artists),
  },
  {
    path: '/api/recommendations/artist-gaps?limit=5',
    validate: (body) => typeof body === 'object' && body !== null && 'artists' in body && Array.isArray((body as Record<string, unknown>).artists),
  },
  {
    path: '/api/recommendations/affordable-grails?max_price=50&min_ratio=1.0&limit=5',
    validate: (body) => typeof body === 'object' && body !== null && 'items' in body && Array.isArray((body as Record<string, unknown>).items),
  },
  {
    path: '/api/recommendations/health',
    validate: (body) => typeof body === 'object' && body !== null && 'health' in body,
  },
  {
    path: '/api/recommendations/complete-decade?limit=5',
    validate: (body) => typeof body === 'object' && body !== null && 'items' in body && Array.isArray((body as Record<string, unknown>).items),
  },
  {
    path: '/api/recommendations/genre-value-map',
    validate: (body) => typeof body === 'object' && body !== null && 'genres' in body && Array.isArray((body as Record<string, unknown>).genres),
  },
  {
    path: '/api/artist/test',
    validate: (body) => typeof body === 'object' && body !== null && 'collection' in body && Array.isArray((body as Record<string, unknown>).collection) && 'wantlist' in body && Array.isArray((body as Record<string, unknown>).wantlist),
  },
  {
    path: '/api/new-releases?limit=1',
    validate: (body) => typeof body === 'object' && body !== null && 'items' in body && Array.isArray((body as Record<string, unknown>).items),
  },
];

(async () => {
  let passed = 0;
  let failedCount = 0;

  for (const { path, validate } of ENDPOINTS) {
    const url = `${API_BASE}${path}`;
    console.log(`CHECK: GET ${path}`);

    let res: Response;
    let body: unknown;

    try {
      res = await fetch(url);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error(`  ERROR ${path} — ${message}`);
      console.error(`\nAPI not reachable at ${API_BASE}. Is the server running?`);
      process.exit(1);
    }

    if (res.status !== 200) {
      console.error(`  FAIL ${path} — HTTP ${res.status}`);
      failedCount++;
      continue;
    }

    try {
      body = await res.json();
    } catch {
      console.error(`  FAIL ${path} — could not parse JSON response`);
      failedCount++;
      continue;
    }

    if (!validate(body)) {
      console.error(`  FAIL ${path} — unexpected shape: ${JSON.stringify(body)}`);
      failedCount++;
      continue;
    }

    console.log(`  OK   ${path}`);
    passed++;
  }

  console.log(`\n${passed} passed, ${failedCount} failed`);
  process.exit(failedCount > 0 ? 1 : 0);
})();
