# Code Review & Roadmap — Discogs Collection

## 1. Code Review Summary

### `apps/local-api/src/routes/artist.ts`

Clean, idiomatic Fastify plugin. The two DB queries run in parallel via `Promise.all`, Fastify schema validation covers the param with length bounds, and all queries use `$1` parameterization — no injection surface. The case-insensitive `LOWER()` matching is the right call given Discogs's inconsistent artist name casing. The `GROUP BY` clause is long because it lists every non-aggregated column individually, which is correct but fragile: adding a column to the `SELECT` means adding it to the `GROUP BY` or the query breaks silently at runtime. Artwork is aggregated with `JSON_AGG … ORDER BY … FILTER (WHERE … IS NOT NULL)` — a solid pattern that avoids nulls when no artwork rows exist. No caching at the API level: repeated artist opens hit Postgres every time.

---

### `apps/local-api/src/routes/new-releases.ts`

Compact and correct. The anti-join pattern (`LEFT JOIN releases … WHERE r.release_id IS NULL`) efficiently filters out already-owned records at the DB layer rather than in application code — good. The graceful degradation for error code `42P01` (undefined table) is a thoughtful touch that lets the app boot before migration 003 has run. The `err as { code: string }` double-cast is slightly awkward; a type guard or `instanceof` check would be cleaner. There is no `offset` parameter, so the endpoint only ever surfaces the latest `N` items — acceptable for now but will become a problem as the feed grows.

---

### `apps/react-frontend/src/components/ArtistView.tsx`

Straightforward controlled-component pattern with `useState` + `useEffect`. The `artistName` dependency in the effect is correct — switching artists triggers a fresh fetch. The Escape key handler is properly removed on cleanup. One wrinkle: `ReleaseDetail` is rendered *inside* the artist panel's `<div>`, which means clicking a release opens a layered modal-inside-modal — there is no z-index or backdrop conflict today but it is fragile if styles change. The `PgNum` cast on `lowest_price` exposes an implicit contract: Postgres `NUMERIC` columns arrive as strings in `node-postgres` and the component silently calls `Number()` on them. This works but is undocumented and will surprise anyone adding new price fields. No caching of any kind; every modal open fires a network round-trip.

---

### `apps/react-frontend/src/components/ExternalLinks.tsx`

A pure, stateless component — exactly right for this role. The link set reveals the app's buying orientation (Discogs marketplace, Disk Union, Recofan, Juno, Clone) and a Japan-centric shopping focus. A few gaps worth noting: Recofan's URL uses `artistQ` only, not the title, so a search for "Basic Channel – Quadrant Dub" will return all Basic Channel results rather than that specific release. The Discogs link points to the sell-listings page for the exact release ID, which is the most useful possible link. None of the generated URLs are validated against store availability — a link to Clone or Juno will appear even if the store has zero copies, which means dead-end clicks.

---

### `apps/react-frontend/src/components/NewReleasesView.tsx`

Minimal and purposeful. The empty state is unusually helpful — it tells the user exactly which command to run to populate the feed, which is the right UX for a developer-facing tool. There is no pagination or "load more" control, so the view is capped at whatever `getNewReleases()` defaults to (20 items). No refresh button: data is stale until the page reloads. The layout — title/artist/meta on the left, `ExternalLinks` on the right — is well-suited to the buying-guide use case.

---

### `apps/react-frontend/src/components/ReleaseDetail.tsx`

Good defensive coding throughout: null guards on every optional field, `fmtPrice` handles EUR/GBP/USD, and primary-image selection falls back to `artwork_files[0]`. The Escape key pattern is identical to `ArtistView` but not extracted into a shared hook — a small DRY violation that will multiply if more modal components are added. The component renders a standalone "Buy on Discogs" link *and* then renders `<ExternalLinks>`, which also includes a Discogs link — so Discogs appears twice in the output. The image URL comes directly from `original_url` (a Discogs CDN path), which may require authentication headers in some contexts or expire, though in practice Discogs release images are publicly accessible.

---

### `apps/react-frontend/src/App.tsx`

The top-level view router is clean and easy to extend — adding a new view is three lines. The header quick-search with 300ms debounce and 5-result cap is good UX. One real bug: `API_BASE` is defined here as `import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:3001'` and identically in `api.ts`. The two copies must be kept in sync manually; if one is changed the health-check fetch in `App.tsx` will diverge from the rest of the API calls. The `availableNow` badge on the Command Center nav button is a nice progressive disclosure detail. The `searchReleaseId` ReleaseDetail is rendered outside the `<main>` tag, which is fine but slightly inconsistent with how other modals are triggered.

---

### `apps/react-frontend/src/api.ts`

A clean typed wrapper around `fetch` with a single `fetchJSON<T>` helper — the right abstraction. All endpoints are centralized here, which makes auditing easy. The `API_BASE` duplication with `App.tsx` is the main issue (see above). There is no retry logic, no request deduplication (rapid navigation could fire duplicate in-flight requests), and no client-side caching layer. For a single-user local app these omissions are acceptable, but they are the first things to add if the app gets shared or hosted.

---

### `apps/postgres/discogs_collection_postgres_lab/sync_new_releases.py`

Functional script with reasonable error handling at the per-artist level (a failed request is logged and skipped, not a fatal crash). The `(result.get("label") or [None])[0]` pattern (and identically for `format`) is the correct defensive form: Discogs occasionally returns an empty list `[]` for these fields, not the absence of the key, so `result.get("label", [None])` would hand back `[]` and `[][0]` would raise an `IndexError` crashing the loop mid-sync. The `or [None]` short-circuit handles both the missing-key and empty-list cases. The `ON CONFLICT (discogs_release_id) DO NOTHING` upsert is correct for idempotent re-runs. Two cursor blocks (`with conn.cursor()`) are used sequentially where one would do; this is not a bug but adds ceremony. The key structural limitations: the Discogs search API is called with `per_page=10` and no page iteration, so only 10 results per artist are ever considered; there is no handling of HTTP 429 rate-limit responses beyond the fixed `time.sleep(1.0)` polite delay (which does not read the `Retry-After` header); and `autocommit = True` means each INSERT is committed immediately with no rollback on partial failure — fine here but worth noting. The feed does not cross-check the wantlist, so a release the user already wants will appear as a new discovery.

---

### `db/migrations/003_new_releases_feed.sql`

Correct and idempotent. The `IF NOT EXISTS` guards mean it can be replayed safely. Indexes on `artist` and `discovered_at DESC` match the access patterns used by the API query. One subtle point: `discogs_release_id` is `INTEGER UNIQUE` but not `NOT NULL`. In Postgres, a `UNIQUE` constraint on a nullable column permits multiple `NULL` values (NULLs are not considered equal), so rows with a null `discogs_release_id` won't conflict — and the `ON CONFLICT` in the Python script won't deduplicate them either. The `genres` column is correctly typed as `JSONB` for future querying. The `source TEXT DEFAULT 'discogs_api'` field is good forward-thinking: it leaves the door open for populating the feed from other sources (e.g., Bandcamp, label newsletters).

---

## 2. Known Issues & Caveats

- **`sync_new_releases.py` — no pagination:** The Discogs search call uses `per_page=10` with no loop over subsequent pages. For prolific artists, only the 10 most recent results are ever fetched.

- **`sync_new_releases.py` — no retry on HTTP 429:** Discogs enforces a rate limit of 60 requests/minute for authenticated users. The script sleeps a fixed 1 second between artists but does not inspect the `Retry-After` response header on a 429, so sustained runs against large collections will silently drop artists.

- **`new_releases_feed` — no deduplication against wantlist:** The API filters out releases already in the collection (`LEFT JOIN releases … WHERE r.release_id IS NULL`) but does not cross-check `new_releases_feed` against the `wantlist` table. A release the user has already flagged as wanted will appear in the New Releases feed as a new discovery.

- **`ArtistView` — no cache:** Every time the artist panel is opened, a full round-trip to Postgres fires. For artists with large collections and artwork joins this can be noticeably slow, and there is no stale-while-revalidate or TTL caching to soften repeat opens.

- **`ExternalLinks` — URLs are search patterns, not validated listings:** All generated links (Disk Union, Recofan, Juno, Clone) are search-result URLs. There is no check that the target store has inventory. Dead-end searches are presented identically to live ones.

- **`API_BASE` duplication:** Defined independently in both `api.ts` and `App.tsx`. A misconfigured `.env.local` that changes one but not the other will cause the health-check badge to query a different host than all other API calls.

- **`ReleaseDetail` — Discogs link appears twice:** The component renders a standalone "Buy on Discogs" anchor and then renders `<ExternalLinks>`, which also generates a Discogs marketplace link for the same `discogs_id`.

---

## 3. Future Roadmap

| # | Title | Description | Complexity |
|---|-------|-------------|------------|
| 1 | **New Releases pagination** | Add `offset` to the `/new-releases` API endpoint and a "Load more" button in `NewReleasesView` so the feed isn't artificially capped at 20 items. | Low |
| 2 | **Wantlist deduplication in feed** | Before inserting into `new_releases_feed`, cross-check against the `wantlist` table and either skip or flag those rows so the UI can distinguish "already wanted" from "new discovery". | Low |
| 3 | **Rate-limit-aware sync** | Update `sync_new_releases.py` to read the `Retry-After` or `X-Discogs-Ratelimit-Remaining` headers and back off dynamically instead of using a fixed sleep. | Low |
| 4 | **Multi-page Discogs sync** | Extend `sync_new_releases.py` to iterate through all pages of search results per artist (respecting `pagination.pages`), not just the first 10 results. | Low |
| 5 | **Shared `useEscapeClose` hook** | Extract the identical `window.addEventListener('keydown', …)` pattern from `ArtistView` and `ReleaseDetail` (and any future modals) into a single `useEscapeClose(onClose)` hook. | Low |
| 6 | **Artist-level caching** | Add a simple `Map<string, ArtistPageData>` cache (or use `react-query` / SWR) in `ArtistView` to serve repeat opens from memory and avoid redundant Postgres queries. | Low |
| 7 | **Label drill-down page** | Clicking a label name anywhere in the UI opens a view showing all owned releases on that label, wantlist items on that label, and optionally fetches the label's full catalog from the Discogs label API. | Medium |
| 8 | **Collection value estimate** | Sum `lowest_price` from `release_prices` across all owned records to generate a live estimated market value of the collection, displayed on the Overview or Command Center. | Medium |
| 9 | **Price history chart** | Store timestamped `release_prices` snapshots (currently only the latest is kept) and render a small sparkline on `ReleaseDetail` showing price trend over time. | Medium |
| 10 | **Wantlist price-drop alerts** | Add a `price_threshold` column to the `wantlist` table and a background job that sends a notification (email, ntfy, or webhook) when `lowest_price` drops below it. | Medium |
| 11 | **Record-fair buying list export** | Add a "Print / Export" button to the wantlist or New Releases view that generates a clean, printer-friendly or shareable list (PDF or plain text) of items to look for at a record fair. | Low |
| 12 | **Master release version browser** | When viewing a release, fetch the corresponding Discogs master release and show all known pressings (different countries, years, labels) so the user can identify cheaper or preferred variants to hunt for. | Medium |
| 13 | **Add to wantlist from UI** | Wire up the Discogs API `PUT /users/{username}/wants/{release_id}` endpoint so a user can add a recommended or new-release item directly to their Discogs wantlist without leaving the app. | Medium |
| 14 | **Bandcamp / label-store links in ExternalLinks** | Extend the `ExternalLinks` component with links to Bandcamp search and label-specific Bandcamp stores for electronic/indie labels, improving utility for new releases that won't appear on second-hand markets yet. | Low |
| 15 | **Artist image enrichment** | Fetch artist images from the Discogs artist API (or MusicBrainz as a fallback) and display a photo alongside the artist name in `ArtistView`, improving the browsing experience for large collections. | Medium |
| 16 | **Collection folder support** | Discogs supports named collection folders (e.g., "For Sale", "Favorites"). Expose folder metadata via the API and add a folder filter to the Browse view, mirroring how users organize their physical collection. | Medium |
| 17 | **Duplicate / multi-copy manager** | Surface records where `copies_count > 1` (already tracked in the `releases` table) in a dedicated view, with quick links to list the duplicates for sale on Discogs marketplace. | Low |
