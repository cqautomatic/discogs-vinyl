# discogs-frontend

Vite + React + TypeScript frontend for the local Discogs collection browser.

Consumes the Node API in `../local-api`. No direct database access from the browser.

## Quick start

See the full setup guide in [`docs/local-development.md`](../../docs/local-development.md),
section **6. React + Node API**.

```bash
# Install dependencies first (node_modules are not committed):
npm install

# Dev server (proxies /api and /health to local-api on :3001):
npm run dev

# Type-check without building:
npm run typecheck

# Validate API contract types statically (no network/docker required):
npm run smoke

# Production build:
npm run build
```

The dev server runs on `http://localhost:5173` and proxies API calls to
`http://localhost:3001`. Start the Node API before the frontend.
