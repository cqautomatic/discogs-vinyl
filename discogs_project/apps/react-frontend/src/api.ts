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
  NewRelease,
} from './types';

// Default: direct to Node API (CORS is open to localhost:5173).
// Set VITE_API_BASE_URL='' in .env.local to use the Vite dev proxy instead.
const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:3001';

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText} — ${path}`);
  }
  return res.json() as Promise<T>;
}

export function getStats(): Promise<Stats> {
  return fetchJSON<Stats>('/api/stats');
}

export async function getReleases(params: {
  limit?: number;
  offset?: number;
  genre?: string;
  style?: string;
}): Promise<ReleasesResponse> {
  const p = new URLSearchParams();
  if (params.limit !== undefined) p.set('limit', String(params.limit));
  if (params.offset !== undefined) p.set('offset', String(params.offset));
  if (params.genre) p.set('genre', params.genre);
  if (params.style) p.set('style', params.style);
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

export function getNewReleases(limit = 20): Promise<{ items: NewRelease[]; count: number }> {
  return fetchJSON(`/api/new-releases?limit=${limit}`);
}
