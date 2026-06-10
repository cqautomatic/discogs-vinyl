/**
 * Types aligned with the Node API response shapes in apps/local-api.
 *
 * pg returns bigint/numeric columns as strings; integer/float as numbers.
 * PgNum covers both so display helpers can use Number() without narrowing noise.
 */
export type PgNum = string | number | null;

// ── /api/stats ────────────────────────────────────────────────────────────────

export interface Stats {
  total_items: PgNum;
  downloaded_items: PgNum;
  unique_artists: PgNum;
  unique_labels: PgNum;
  countries: PgNum;
  earliest_year: PgNum;
  latest_year: PgNum;
  avg_rating: PgNum;
  rated_items: PgNum;
  artwork_count: PgNum;
  total_artwork_size_bytes: PgNum;
  min_price: PgNum;
  max_price: PgNum;
  avg_price: PgNum;
  total_value: PgNum;
  priced_items: PgNum;
}

// ── /api/releases, /api/releases/:id ─────────────────────────────────────────

export interface ArtworkFile {
  artwork_id: number;
  image_type: string;
  local_file_path: string | null;
  thumbnail_file_path: string | null;
  original_url: string | null;
  file_size: number | null;
  image_width: number | null;
  image_height: number | null;
}

export interface Release {
  release_id: number;
  discogs_id: number | null;
  title: string;
  artist: string;
  year: number | null;
  label: string | null;
  catno: string | null;
  format: string | null;
  genres: string[] | null;
  styles: string[] | null;
  producers: string | null;
  country: string | null;
  rating: number | null;
  condition: string | null;
  sleeve_condition: string | null;
  date_added: string | null;
  copies_count: number | null;
  instance_ids: number[] | null;
  community_have_count: number | null;
  community_want_count: number | null;
  community_average_rating: number | null;
  community_rating_count: number | null;
  artwork_files: ArtworkFile[];
  // Detail endpoint extras
  stats_last_updated?: string | null;
  last_sold_date?: string | null;
  low_sold_price?: PgNum;
  high_sold_price?: PgNum;
  ms_currency?: string | null;
  marketplace_as_of?: string | null;
  num_for_sale?: number | null;
  lowest_price?: PgNum;
  rp_currency?: string | null;
  last_seen?: string | null;
}

// GET /api/releases — note: "count" is rows returned (not total matching rows)
export interface ReleasesResponse {
  releases: Release[];
  count: PgNum;
}

// ── /api/genres ───────────────────────────────────────────────────────────────

export interface GenreStat {
  genre: string;
  release_count: PgNum;
  artist_count: PgNum;
  avg_rating: PgNum;
}

export interface GenresResponse {
  genres: GenreStat[];
}

// ── /api/styles ───────────────────────────────────────────────────────────────

export interface StyleStat {
  style: string;
  release_count: PgNum;
  artist_count: PgNum;
  avg_rating: PgNum;
}

export interface StylesResponse {
  styles: StyleStat[];
}

// ── /api/search ───────────────────────────────────────────────────────────────
// Shape matches local-api/src/routes/search.ts: { releases, count }
// (consistent with ReleasesResponse — count is rowCount, not total matching rows)

export interface SearchResponse {
  releases: Release[];
  count: PgNum;
}

// ── /api/recommendations ──────────────────────────────────────────────────────

export interface WantlistItem {
  discogs_release_id: number;
  title: string;
  artist: string;
  year: number | null;
  label: string | null;
  format: string | null;
  genres: string[] | null;
  styles: string[] | null;
  notes: string | null;
  rating: number | null;
  added: string | null;
  master_id: number | null;
  lowest_price: PgNum;
  currency: string | null;
  num_for_sale: number | null;
  availability: boolean | null;
  price_last_seen: string | null;
}

// ── /api/pressings/:masterId ──────────────────────────────────────────────────

export interface PressingVersion {
  discogs_release_id: number;
  title: string;
  label: string | null;
  catno: string | null;
  country: string | null;
  year: number | null;
  format: string;
  lowest_price: number | null;
  currency: string | null;
  num_for_sale: number | null;
  is_wantlist_pressing: boolean;
  owned: boolean;
}

export interface PressingResponse {
  master_id: number;
  versions: PressingVersion[];
  cached: boolean;
  fetched_at: string | null;
}

// ── /api/store-check ──────────────────────────────────────────────────────────

export interface StoreCheckResult {
  discogs_release_id: number;
  title: string;
  artist: string;
  year: number | null;
  label: string | null;
  catno: string | null;
  format: string | null;
  master_id: number | null;
  owned: boolean;
  owns_version: boolean;
  wantlist: boolean;
  lowest_price: PgNum;
  currency: string | null;
  num_for_sale: number | null;
  low_sold_price: PgNum;
  high_sold_price: PgNum;
  last_sold_date: string | null;
  source: 'local' | 'discogs';
}

export interface BandcampResult {
  name: string;
  band_name: string;
  url: string;
}

export interface BandcampResponse {
  results: BandcampResult[];
  fallback_url: string;
}

export interface BudgetItem {
  discogs_release_id: number;
  title: string;
  artist: string;
  year: number | null;
  label: string | null;
  format: string | null;
  genres: string[] | null;
  styles: string[] | null;
  lowest_price: PgNum;
  currency: string | null;
  num_for_sale: number | null;
  source: string;
}

export interface HighDemandItem {
  release_id: number;
  discogs_id: number;
  title: string;
  artist: string;
  year: number | null;
  label: string | null;
  community_want_count: number | null;
  community_have_count: number | null;
  want_have_ratio: PgNum;
}

export interface LabelGap {
  label: string;
  owned_releases: PgNum;
  unique_artists: PgNum;
  avg_rating: PgNum;
}

export interface DecadeGap {
  decade_start: number;
  decade_label: string;
  releases_owned: PgNum;
  unique_years: PgNum;
  coverage_pct: PgNum;
}

export interface SimilarArtist {
  artist: string;
  wantlist_count: PgNum;
  shared_labels: string[] | null;
  similar_to_artists: string[] | null;
  top_release_title: string | null;
  top_release_discogs_id: number | null;
  top_release_thumb: string | null;
}

export interface ArtistGap {
  artist: string;
  owned_releases: PgNum;
  avg_rating: PgNum;
}

export interface AffordableGrail {
  discogs_release_id: number;
  title: string;
  artist: string;
  year: number | null;
  label: string | null;
  format: string | null;
  thumb: string | null;
  lowest_price: PgNum;
  currency: string | null;
  num_for_sale: number | null;
  community_want_count: number | null;
  community_have_count: number | null;
  want_have_ratio: PgNum;
}

export interface CollectionHealth {
  total_wantlist: PgNum;
  available_now: PgNum;
  total_available_value: PgNum;
  items_under_20: PgNum;
  avg_available_price: PgNum;
}

export interface CompleteDecadeItem {
  discogs_release_id: number;
  title: string;
  artist: string;
  year: number | null;
  label: string | null;
  lowest_price: PgNum;
  currency: string | null;
  num_for_sale: number | null;
  availability: boolean | null;
  decade_label: string;
  releases_owned: PgNum;
}

export interface GenreValueEntry {
  genre: string;
  wantlist_count: PgNum;
  avg_price: PgNum;
  avg_rating: PgNum;
}

// ── /api/artist, /api/new-releases ───────────────────────────────────────────

export interface ArtistPageData {
  artist: string;
  collection: Release[];
  wantlist: WantlistItem[];
}

// ── /api/discover ─────────────────────────────────────────────────────────────

export type DiscoverStatus = 'owned' | 'wantlist' | 'gap';

export interface StyleResult {
  id: number;
  title: string;
  year: number | null;
  label: string | null;
  format: string | null;
  genres: string[];
  styles: string[];
  country: string | null;
  thumb: string | null;
  community_have: number | null;
  community_want: number | null;
  status: DiscoverStatus;
}

export interface ExpandResult {
  style: string;
  owned_count: number;
  topLabels: string[];
  topArtists: string[];
  results: Array<{
    discogs_release_id: number;
    title: string;
    artist: string;
    year: number | null;
    label: string | null;
    format: string | null;
    genres: string[] | null;
    country: string | null;
    thumb: string | null;
    /** 'top-label' | 'top-artist' | 'style' */
    match: string;
    status: DiscoverStatus;
  }>;
  feed_tip: string | null;
}

export interface DiscogsListMeta {
  id: number;
  slug: string;
  name: string;
  url: string;
}

export interface DiscogsListItem {
  id: number;
  title: string;
  thumb: string | null;
  uri: string | null;
  type: string;
  comment: string;
  status: DiscoverStatus;
}

export interface DiscogsListDetail {
  id: number;
  name: string;
  description: string;
  item_count: number;
  items: DiscogsListItem[];
  owned: number;
  wanted: number;
  gaps: number;
}

export interface NewRelease {
  id: number;
  discogs_release_id: number;
  title: string;
  artist: string;
  year: number | null;
  label: string | null;
  format: string | null;
  genres: string[] | null;
  country: string | null;
  source: string;
  discovered_at: string;
  thumb: string | null;
  in_wantlist: boolean;
}

export interface NewReleasePriceEntry {
  lowest_price: number | null;
  currency: string | null;
  num_for_sale: number;
}

export interface NewReleasesResponse {
  items: NewRelease[];
  count: number;
  latest_sync: string | null;
}
