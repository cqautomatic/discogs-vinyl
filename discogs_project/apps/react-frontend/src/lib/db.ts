/**
 * IndexedDB layer for offline collection storage.
 * Uses `idb` for a promise-based wrapper around IndexedDB.
 */

import { openDB } from 'idb';

const DB_NAME    = 'vinyl-offline';
const DB_VERSION = 2;

export interface OfflineRelease {
  discogs_id:      number;
  title:           string;
  artist:          string;
  year:            number | null;
  label:           string | null;
  catno:           string | null;
  format:          string | null;
  country:         string | null;
  genres:          string[];
  styles:          string[];
  thumb:           string | null;
  community_have:  number;
  community_want:  number;
  rating:          number | null;
}

export interface OfflineWantItem {
  discogs_release_id: number;
  title:              string;
  artist:             string;
  year:               number | null;
  label:              string | null;
  catno:              string | null;
  format:             string | null;
  genres:             string[];
  styles:             string[];
  master_id:          number | null;
  lowest_price:       number | null;
  currency:           string | null;
  num_for_sale:       number;
  low_sold_price:     number | null;
  high_sold_price:    number | null;
  last_sold_date:     string | null;
}

export interface OfflinePrice {
  discogs_release_id: number;
  lowest_price:       number | null;
  currency:           string | null;
  num_for_sale:       number;
  availability:       boolean;
  low_sold_price:     number | null;
  high_sold_price:    number | null;
  last_sold_date:     string | null;
}

export interface OfflineNewRelease {
  id:                   number;
  discogs_release_id:   number;
  title:                string;
  artist:               string;
  year:                 number | null;
  label:                string | null;
  format:               string | null;
  genres:               string[];
  styles:               string[];
  country:              string | null;
  source:               string;
  discovered_at:        string;
  thumb:                string | null;
  in_wantlist:          boolean;
  cached_lowest_price:  number | null;
  cached_currency:      string | null;
  cached_num_for_sale:  number | null;
}

export interface SyncMeta {
  synced_at:          string;
  collection_count:   number;
  wantlist_count:     number;
  prices_count:       number;
  new_releases_count: number;
  api_url:            string;
}

function getDB() {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db, oldVersion) {
      if (oldVersion < 1) {
        const col = db.createObjectStore('collection', { keyPath: 'discogs_id' });
        col.createIndex('artist', 'artist');
        col.createIndex('year',   'year');
        db.createObjectStore('wantlist', { keyPath: 'discogs_release_id' });
        db.createObjectStore('prices',   { keyPath: 'discogs_release_id' });
        db.createObjectStore('meta');
      }
      if (oldVersion < 2) {
        if (!db.objectStoreNames.contains('new_releases')) {
          db.createObjectStore('new_releases', { keyPath: 'id' });
        }
      }
    },
  });
}

// ── Read ─────────────────────────────────────────────────────────────────────

export async function getSyncMeta(): Promise<SyncMeta | null> {
  const db = await getDB();
  return (await db.get('meta', 'sync')) as SyncMeta | null;
}

export async function getCollectionCount(): Promise<number> {
  const db = await getDB();
  return db.count('collection');
}

/** Tokenized matcher shared by all offline search paths: every query word
 *  must appear somewhere across the combined fields. */
function tokenMatcher(query: string): (...fields: Array<string | null | undefined>) => boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  return (...fields) => {
    const haystack = fields.filter(Boolean).join(' ').toLowerCase();
    return words.every(w => haystack.includes(w));
  };
}

export async function searchCollection(query: string): Promise<OfflineRelease[]> {
  const db  = await getDB();
  const all = (await db.getAll('collection')) as OfflineRelease[];
  if (!query.trim()) return all;
  const matches = tokenMatcher(query);
  return all.filter((r) => matches(r.title, r.artist, r.label, r.catno));
}

export async function getAllWantlist(): Promise<OfflineWantItem[]> {
  const db = await getDB();
  return (await db.getAll('wantlist')) as OfflineWantItem[];
}

export async function getPriceFor(discogsId: number): Promise<OfflinePrice | null> {
  const db = await getDB();
  return (await db.get('prices', discogsId)) as OfflinePrice | null;
}

export async function checkOwned(discogsId: number): Promise<boolean> {
  const db  = await getDB();
  const rec = await db.get('collection', discogsId);
  return rec !== undefined;
}

/** Full-text search across owned + wantlist — powers offline Store Mode. */
export async function offlineStoreSearch(query: string): Promise<{
  owned:    OfflineRelease[];
  wantlist: OfflineWantItem[];
}> {
  if (!query.trim()) return { owned: [], wantlist: [] };
  const matches = tokenMatcher(query);
  const db = await getDB();
  const [allOwned, allWantlist] = await Promise.all([
    db.getAll('collection') as Promise<OfflineRelease[]>,
    db.getAll('wantlist')   as Promise<OfflineWantItem[]>,
  ]);
  return {
    owned:    allOwned.filter(r => matches(r.title, r.artist, r.catno)),
    wantlist: allWantlist.filter(w => matches(w.title, w.artist, w.catno)),
  };
}

/** Get all new releases from the local snapshot. */
export async function getOfflineNewReleases(): Promise<OfflineNewRelease[]> {
  const db = await getDB();
  return (await db.getAll('new_releases')) as OfflineNewRelease[];
}

// ── Write (called by sync) ────────────────────────────────────────────────────

async function putAllChunked<T>(
  db: Awaited<ReturnType<typeof getDB>>,
  storeName: 'collection' | 'wantlist' | 'prices' | 'new_releases',
  records: T[],
  chunkSize = 200,
  onChunk?: (written: number) => void,
): Promise<void> {
  // Write-then-prune instead of clear-then-write: if the page is killed
  // mid-sync (iOS low-memory eviction), the store still holds usable data
  // rather than being left empty.
  for (let i = 0; i < records.length; i += chunkSize) {
    const chunk = records.slice(i, i + chunkSize);
    const tx = db.transaction(storeName, 'readwrite');
    for (const r of chunk) tx.store.put(r as Parameters<typeof tx.store.put>[0]);
    await tx.done;
    onChunk?.(i + chunk.length);
  }
  // Prune rows that are no longer in the snapshot
  {
    const tx = db.transaction(storeName, 'readwrite');
    const keyPath = tx.store.keyPath as string;
    const valid = new Set(records.map((r) => (r as Record<string, unknown>)[keyPath] as IDBValidKey));
    const keys = await tx.store.getAllKeys();
    for (const k of keys) {
      if (!valid.has(k)) tx.store.delete(k);
    }
    await tx.done;
  }
}

export async function storeSnapshot(
  collection:   OfflineRelease[],
  wantlist:     OfflineWantItem[],
  prices:       OfflinePrice[],
  new_releases: OfflineNewRelease[],
  meta:         SyncMeta,
  onProgress?:  (p: { message: string; percent: number }) => void,
): Promise<void> {
  const db    = await getDB();
  const total = collection.length + wantlist.length + prices.length + new_releases.length;
  let done    = 0;

  const report = (msg: string) =>
    onProgress?.({ message: msg, percent: total > 0 ? Math.round((done / total) * 100) : 50 });

  report(`Saving collection (0 / ${collection.length.toLocaleString()})…`);
  await putAllChunked(db, 'collection', collection, 200, (n) => {
    done = n;
    report(`Saving collection (${n.toLocaleString()} / ${collection.length.toLocaleString()})…`);
  });

  done = collection.length;
  report('Saving wantlist…');
  await putAllChunked(db, 'wantlist', wantlist);
  done += wantlist.length;

  report('Saving prices…');
  await putAllChunked(db, 'prices', prices);
  done += prices.length;

  report(`Saving ${new_releases.length.toLocaleString()} new releases…`);
  await putAllChunked(db, 'new_releases', new_releases);

  await db.put('meta', meta, 'sync');
}
