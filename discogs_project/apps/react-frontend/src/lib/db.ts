/**
 * IndexedDB layer for offline collection storage.
 * Uses `idb` for a promise-based wrapper around IndexedDB.
 */

import { openDB } from 'idb';

const DB_NAME    = 'vinyl-offline';
const DB_VERSION = 1;

export interface OfflineRelease {
  discogs_id:      number;
  title:           string;
  artist:          string;
  year:            number | null;
  label:           string | null;
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
  format:             string | null;
  genres:             string[];
  styles:             string[];
}

export interface OfflinePrice {
  discogs_release_id: number;
  lowest_price:       number | null;
  currency:           string | null;
  num_for_sale:       number;
  availability:       boolean;
}

export interface SyncMeta {
  synced_at:        string;
  collection_count: number;
  wantlist_count:   number;
  prices_count:     number;
  api_url:          string;
}

function getDB() {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('collection')) {
        const store = db.createObjectStore('collection', { keyPath: 'discogs_id' });
        store.createIndex('artist', 'artist');
        store.createIndex('year',   'year');
      }
      if (!db.objectStoreNames.contains('wantlist')) {
        db.createObjectStore('wantlist', { keyPath: 'discogs_release_id' });
      }
      if (!db.objectStoreNames.contains('prices')) {
        db.createObjectStore('prices', { keyPath: 'discogs_release_id' });
      }
      if (!db.objectStoreNames.contains('meta')) {
        db.createObjectStore('meta');
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

export async function searchCollection(query: string): Promise<OfflineRelease[]> {
  const db  = await getDB();
  const all = (await db.getAll('collection')) as OfflineRelease[];
  if (!query.trim()) return all;
  const q = query.toLowerCase();
  return all.filter(
    (r) =>
      r.title?.toLowerCase().includes(q) ||
      r.artist?.toLowerCase().includes(q) ||
      r.label?.toLowerCase().includes(q),
  );
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

// ── Write (called by sync) ────────────────────────────────────────────────────

export async function storeSnapshot(
  collection: OfflineRelease[],
  wantlist:   OfflineWantItem[],
  prices:     OfflinePrice[],
  meta:       SyncMeta,
): Promise<void> {
  const db = await getDB();

  // collection
  {
    const tx = db.transaction('collection', 'readwrite');
    await tx.store.clear();
    await Promise.all(collection.map((r) => tx.store.put(r)));
    await tx.done;
  }
  // wantlist
  {
    const tx = db.transaction('wantlist', 'readwrite');
    await tx.store.clear();
    await Promise.all(wantlist.map((r) => tx.store.put(r)));
    await tx.done;
  }
  // prices
  {
    const tx = db.transaction('prices', 'readwrite');
    await tx.store.clear();
    await Promise.all(prices.map((r) => tx.store.put(r)));
    await tx.done;
  }
  // meta
  await db.put('meta', meta, 'sync');
}
