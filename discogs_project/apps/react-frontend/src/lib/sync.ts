/**
 * Fetches the full collection snapshot from the API and stores it in IndexedDB.
 */

import { storeSnapshot, type OfflineRelease, type OfflineWantItem, type OfflinePrice, type SyncMeta } from './db';

export type SyncStage = 'idle' | 'fetching' | 'storing' | 'done' | 'error';

export interface SyncProgress {
  stage:    SyncStage;
  message:  string;
  percent?: number;
}

interface SnapshotResponse {
  collection: OfflineRelease[];
  wantlist:   OfflineWantItem[];
  prices:     OfflinePrice[];
  synced_at:  string;
  stats: {
    collection_count: number;
    wantlist_count:   number;
    prices_count:     number;
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
  const { collection, wantlist, prices, synced_at, stats } = data;

  onProgress({
    stage:   'storing',
    message: `Storing ${collection.length.toLocaleString()} records…`,
    percent: 50,
  });

  const meta: SyncMeta = {
    synced_at,
    collection_count: stats.collection_count,
    wantlist_count:   stats.wantlist_count,
    prices_count:     stats.prices_count,
    api_url:          apiUrl,
  };

  await storeSnapshot(collection, wantlist, prices, meta);

  onProgress({ stage: 'done', message: `${collection.length.toLocaleString()} records ready offline`, percent: 100 });

  return meta;
}

// ── API URL helpers ───────────────────────────────────────────────────────────

const API_URL_KEY = 'vinyl-api-url';

export function getSavedApiUrl(): string {
  return localStorage.getItem(API_URL_KEY) ?? 'http://localhost:3001';
}

export function saveApiUrl(url: string): void {
  localStorage.setItem(API_URL_KEY, url.replace(/\/$/, ''));
}
