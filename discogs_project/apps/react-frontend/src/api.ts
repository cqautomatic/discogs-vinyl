import type {
  Stats,
  Release,
  ReleasesResponse,
  GenreStat,
  StyleStat,
  SearchResponse,
  GenresResponse,
  StylesResponse,
  WantlistItem,
  BudgetItem,
  HighDemandItem,
  LabelGap,
  DecadeGap,
  SimilarArtist,
  ArtistGap,
  AffordableGrail,
  CollectionHealth,
  CompleteDecadeItem,
  GenreValueEntry,
  ArtistPageData,
  NewReleasesResponse,
  NewReleasePriceEntry,
  StyleResult,
  ExpandResult,
  DiscogsListMeta,
  DiscogsListDetail,
  PressingResponse,
  StoreCheckResult,
  BandcampResponse,
} from './types';
import { cacheSet, cacheGet } from './lib/api-cache';

// Default: same origin — the Fastify API serves the built frontend, so API
// calls are relative. This is what makes the HTTPS PWA work with zero config.
// Vite dev/preview ports (5173/4173) are the exception: they point at :3001.
// Set VITE_API_BASE_URL in .env.local to override entirely.
function resolveApiBase(): string {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
  const { hostname, port, protocol } = window.location;
  // Manual override from the sync panel — ignore http: URLs on an https page
  // (mixed content is blocked by the browser anyway)
  const saved = localStorage.getItem('vinyl-api-url');
  if (saved && !(protocol === 'https:' && saved.startsWith('http://'))) return saved;
  // Vite dev server / preview — API lives on a separate port (http only)
  if ((port === '5173' || port === '4173') && protocol === 'http:') {
    return `http://${hostname}:3001`;
  }
  return ''; // same origin
}
const API_BASE: string = resolveApiBase();

// ── Offline cache-hit state ───────────────────────────────────────────────────
// When fetchJSON falls back to IndexedDB cache it emits a hit so the UI can
// show a "cached · X ago" banner.  When a live response comes in it clears it.

export interface CacheHit { path: string; cachedAt: string }
let _lastCacheHit: CacheHit | null = null;
const _cacheListeners = new Set<(hit: CacheHit | null) => void>();

/** Subscribe to cache-hit changes.  Returns an unsubscribe function. */
export function onCacheHit(fn: (hit: CacheHit | null) => void): () => void {
  _cacheListeners.add(fn);
  fn(_lastCacheHit); // fire immediately with current state
  return () => _cacheListeners.delete(fn);
}

function _setCacheHit(hit: CacheHit | null) {
  _lastCacheHit = hit;
  _cacheListeners.forEach(fn => fn(hit));
}

// ── fetch helper ─────────────────────────────────────────────────────────────

export async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const isGet = !init?.method || init.method.toUpperCase() === 'GET';
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    // Network-level failure (Mac unreachable, Tailscale off, etc.)
    // For GET requests try the IndexedDB response cache before giving up.
    if (isGet) {
      const cached = await cacheGet<T>(path);
      if (cached) {
        _setCacheHit({ path, cachedAt: cached.cachedAt });
        return cached.data;
      }
    }
    throw new Error(`Failed to fetch — Mac unreachable`);
  }
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json() as { error?: string; message?: string };
      detail = body.error ?? body.message ?? '';
    } catch { /* ignore parse failure */ }
    throw new Error(detail || `API ${res.status}: ${res.statusText} — ${path}`);
  }
  const data = await res.json() as T;
  // Persist every successful GET response so we can serve it when offline later.
  if (isGet) void cacheSet(path, data);
  // Clear any stale-cache banner now that we have fresh data.
  if (_lastCacheHit) _setCacheHit(null);
  return data;
}

export function getStats(): Promise<Stats> {
  return fetchJSON<Stats>('/api/stats');
}

export type SortOption = 'artist_year' | 'date_added' | 'year' | 'title';

export async function getReleases(params: {
  limit?: number;
  offset?: number;
  genre?: string;
  style?: string;
  label?: string;
  year?: number;
  country?: string;
  artist?: string;
  sort?: SortOption;
}): Promise<ReleasesResponse> {
  const p = new URLSearchParams();
  if (params.limit !== undefined)  p.set('limit',   String(params.limit));
  if (params.offset !== undefined) p.set('offset',  String(params.offset));
  if (params.genre)   p.set('genre',   params.genre);
  if (params.style)   p.set('style',   params.style);
  if (params.label)   p.set('label',   params.label);
  if (params.year)    p.set('year',    String(params.year));
  if (params.country) p.set('country', params.country);
  if (params.artist)  p.set('artist',  params.artist);
  if (params.sort)    p.set('sort',    params.sort);
  const qs = p.toString();
  return fetchJSON<ReleasesResponse>(`/api/releases${qs ? `?${qs}` : ''}`);
}

export function getRelease(id: number): Promise<Release> {
  return fetchJSON<Release>(`/api/releases/${id}`);
}

export async function getGenres(): Promise<GenreStat[]> {
  const res = await fetchJSON<GenresResponse>('/api/genres');
  return res.genres;
}

export async function getStyles(): Promise<StyleStat[]> {
  const res = await fetchJSON<StylesResponse>('/api/styles');
  return res.styles;
}

export function searchReleases(query: string): Promise<SearchResponse> {
  const p = new URLSearchParams({ q: query });
  return fetchJSON<SearchResponse>(`/api/search?${p.toString()}`);
}

// ── Recommendations ────────────────────────────────────────────────────────────

export function getWantlist(limit = 50): Promise<{ items: WantlistItem[]; count: number }> {
  return fetchJSON(`/api/recommendations/wantlist?limit=${limit}`);
}

export function getBudgetRecs(maxPrice = 50, limit = 20): Promise<{ items: BudgetItem[]; count: number }> {
  return fetchJSON(`/api/recommendations/budget?max_price=${maxPrice}&limit=${limit}`);
}

export function getHighDemand(limit = 20): Promise<{ items: HighDemandItem[]; count: number }> {
  return fetchJSON(`/api/recommendations/high-demand?limit=${limit}`);
}

export function getLabelGaps(limit = 15): Promise<{ labels: LabelGap[]; count: number }> {
  return fetchJSON(`/api/recommendations/label-gaps?limit=${limit}`);
}

export function getDecadeGaps(): Promise<{ decades: DecadeGap[] }> {
  return fetchJSON('/api/recommendations/decade-gaps');
}

export function getSimilarArtists(limit = 20): Promise<{ artists: SimilarArtist[]; count: number }> {
  return fetchJSON(`/api/recommendations/similar-artists?limit=${limit}`);
}

export function getArtistGaps(limit = 20): Promise<{ artists: ArtistGap[]; count: number }> {
  return fetchJSON(`/api/recommendations/artist-gaps?limit=${limit}`);
}

export function getAffordableGrails(maxPrice = 25, minRatio = 2.0, limit = 20): Promise<{ items: AffordableGrail[]; count: number }> {
  return fetchJSON(`/api/recommendations/affordable-grails?max_price=${maxPrice}&min_ratio=${minRatio}&limit=${limit}`);
}

export function getCollectionHealth(): Promise<{ health: CollectionHealth }> {
  return fetchJSON('/api/recommendations/health');
}

export function getCompleteDecade(limit = 20): Promise<{ items: CompleteDecadeItem[]; count: number }> {
  return fetchJSON(`/api/recommendations/complete-decade?limit=${limit}`);
}

export function getGenreValueMap(): Promise<{ genres: GenreValueEntry[] }> {
  return fetchJSON('/api/recommendations/genre-value-map');
}

export function getArtist(name: string): Promise<ArtistPageData> {
  return fetchJSON(`/api/artist/${encodeURIComponent(name)}`);
}

/**
 * Fetch the New Releases feed.
 * @param style Comma-separated style filter, e.g. "House,Deep House,Garage House".
 *              Each value must be a valid DISCOVERY_STYLES entry (server validates).
 *              Omit for all styles.
 */
export function getNewReleases(limit = 20, style?: string): Promise<NewReleasesResponse> {
  const p = new URLSearchParams({ limit: String(limit) });
  if (style) p.set('style', style);
  return fetchJSON<NewReleasesResponse>(`/api/new-releases?${p}`);
}

/** Batch price lookup for feed cards. Returns a map keyed by discogs_release_id string. */
export function getNewReleasePrices(releaseIds: number[]): Promise<{ prices: Record<string, NewReleasePriceEntry> }> {
  return fetchJSON('/api/new-releases/prices', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ release_ids: releaseIds }),
  });
}

export function dismissNewRelease(id: number): Promise<{ ok: boolean }> {
  return fetchJSON(`/api/new-releases/${id}/dismiss`, { method: 'POST' });
}

export function undismissNewRelease(id: number): Promise<{ ok: boolean }> {
  return fetchJSON(`/api/new-releases/${id}/undismiss`, { method: 'POST' });
}

export function addToWantlistFromFeed(id: number): Promise<{ ok: boolean; in_wantlist: boolean }> {
  return fetchJSON(`/api/new-releases/${id}/want`, { method: 'POST' });
}

// Construct artwork URLs from local file paths
export function getArtworkUrl(localFilePath: string | null): string | null {
  if (!localFilePath) return null;
  const filename = localFilePath.split('/').pop();
  if (!filename) return null;
  return `${API_BASE}/artwork/${filename}`;
}

export function syncNewReleases(): Promise<{ ok: boolean; message: string }> {
  return fetchJSON('/api/new-releases/sync', { method: 'POST' });
}

// ── Discover ──────────────────────────────────────────────────────────────────

export function discoverStyle(params: { style?: string; genre?: string; limit?: number }): Promise<{ results: StyleResult[]; total: number }> {
  const p = new URLSearchParams();
  if (params.style)  p.set('style', params.style);
  if (params.genre)  p.set('genre', params.genre);
  if (params.limit)  p.set('limit', String(params.limit));
  return fetchJSON(`/api/discover/style?${p}`);
}

export function discoverExpand(style?: string, limit?: number): Promise<ExpandResult> {
  const p = new URLSearchParams();
  if (style)  p.set('style', style);
  if (limit)  p.set('limit', String(limit));
  return fetchJSON(`/api/discover/expand?${p}`);
}

export function searchDiscogsLists(query: string): Promise<{ lists: DiscogsListMeta[]; query: string; discogs_search_url: string; error?: string }> {
  return fetchJSON(`/api/discover/lists?query=${encodeURIComponent(query)}`);
}

export function loadDiscogsList(id: number): Promise<DiscogsListDetail> {
  return fetchJSON(`/api/discover/list/${id}`);
}

// ── Pressings ─────────────────────────────────────────────────────────────────

export function getPressings(masterId: number, excludeReleaseId?: number): Promise<PressingResponse> {
  const qs = excludeReleaseId ? `?exclude_release_id=${excludeReleaseId}` : '';
  return fetchJSON(`/api/pressings/${masterId}${qs}`);
}

// ── Store Check ───────────────────────────────────────────────────────────────

export function storeCheck(q: string): Promise<{ results: StoreCheckResult[]; source: string; error?: string }> {
  return fetchJSON(`/api/store-check?q=${encodeURIComponent(q)}`);
}

export function bandcampCheck(artist: string, title: string): Promise<BandcampResponse> {
  const p = new URLSearchParams();
  if (artist) p.set('artist', artist);
  if (title)  p.set('title',  title);
  return fetchJSON(`/api/store-check/bandcamp?${p}`);
}
