/**
 * Fetches the full collection snapshot from the API and stores it in IndexedDB.
 */

import { storeSnapshot, type OfflineRelease, type OfflineWantItem, type OfflinePrice, type OfflineNewRelease, type SyncMeta } from './db';

export type SyncStage = 'idle' | 'fetching' | 'storing' | 'done' | 'error';

export interface SyncProgress {
  stage:    SyncStage;
  message:  string;
  percent?: number;
}

interface SnapshotResponse {
  collection:   OfflineRelease[];
  wantlist:     OfflineWantItem[];
  prices:       OfflinePrice[];
  new_releases: OfflineNewRelease[];
  synced_at:    string;
  stats: {
    collection_count:   number;
    wantlist_count:     number;
    prices_count:       number;
    new_releases_count: number;
  };
}

export async function syncToDevice(
  apiUrl:     string,
  onProgress: (p: SyncProgress) => void,
): Promise<SyncMeta> {
  onProgress({ stage: 'fetching', message: 'Downloading collection…', percent: 5 });

  const res = await fetch(`${apiUrl}/api/sync/snapshot`);
  if (!res.ok) {
    throw new Error(`Server returned ${res.status} — is the API running at ${apiUrl}?`);
  }

  const data = (await res.json()) as SnapshotResponse;
  const { collection, wantlist, prices, new_releases, synced_at, stats } = data;

  onProgress({
    stage:   'storing',
    message: `Storing ${collection.length.toLocaleString()} records…`,
    percent: 50,
  });

  const meta: SyncMeta = {
    synced_at,
    collection_count:   stats.collection_count,
    wantlist_count:     stats.wantlist_count,
    prices_count:       stats.prices_count,
    new_releases_count: stats.new_releases_count,
    api_url:            apiUrl,
  };

  await storeSnapshot(collection, wantlist, prices, new_releases, meta, (p) => {
    onProgress({ stage: 'storing', message: p.message, percent: 50 + Math.round(p.percent * 0.45) });
  });

  onProgress({
    stage:   'done',
    message: `${collection.length.toLocaleString()} records · ${new_releases.length.toLocaleString()} new finds ready offline`,
    percent: 100,
  });

  return meta;
}

// ── API URL helpers ───────────────────────────────────────────────────────────

const API_URL_KEY = 'vinyl-api-url';

/**
 * Default is same-origin: the API serves the frontend, so the page's own
 * origin is the API. A saved override only applies if it doesn't create
 * mixed content (http: API on an https: page).
 */
export function getSavedApiUrl(): string {
  const saved = localStorage.getItem(API_URL_KEY);
  if (saved && !(window.location.protocol === 'https:' && saved.startsWith('http://'))) {
    return saved;
  }
  const { hostname, port, protocol } = window.location;
  if ((port === '5173' || port === '4173') && protocol === 'http:') {
    return `http://${hostname}:3001`; // Vite dev/preview — API on its own port
  }
  return window.location.origin;
}

export function saveApiUrl(url: string): void {
  const clean = url.replace(/\/$/, '');
  if (clean === window.location.origin || clean === '') {
    localStorage.removeItem(API_URL_KEY); // back to same-origin default
  } else {
    localStorage.setItem(API_URL_KEY, clean);
  }
}
