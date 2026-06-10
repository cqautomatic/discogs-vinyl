/**
 * API response cache — persists fetch results in IndexedDB so the app
 * can serve stale-but-useful data when the Mac / network is unreachable.
 */

import { openDB } from 'idb';

const DB_NAME    = 'vinyl-api-cache';
const DB_VERSION = 1;
const STORE      = 'responses';

interface CacheEntry {
  key:        string;   // the request URL/path
  data:       unknown;
  cachedAt:   string;   // ISO timestamp
}

function getDB() {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'key' });
      }
    },
  });
}

export async function cacheSet(key: string, data: unknown): Promise<void> {
  try {
    const db = await getDB();
    await db.put(STORE, { key, data, cachedAt: new Date().toISOString() } satisfies CacheEntry);
  } catch {
    // Cache write failing is non-fatal
  }
}

export async function cacheGet<T>(key: string): Promise<{ data: T; cachedAt: string } | null> {
  try {
    const db    = await getDB();
    const entry = (await db.get(STORE, key)) as CacheEntry | undefined;
    if (!entry) return null;
    return { data: entry.data as T, cachedAt: entry.cachedAt };
  } catch {
    return null;
  }
}
