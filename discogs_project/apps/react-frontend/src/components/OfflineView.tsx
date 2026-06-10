/**
 * My Vinyl view.
 *
 * Mac / browser:  pulls live from the API (database-backed).
 * iPhone PWA:     reads from IndexedDB (offline-capable local copy).
 *
 * The two modes share the same tab layout so the experience looks identical.
 */

import { useState, useEffect, useRef } from 'react';
import {
  searchCollection, getAllWantlist, getPriceFor,
  getOfflineNewReleases,
  type OfflineRelease, type OfflineWantItem, type OfflinePrice, type OfflineNewRelease,
  getSyncMeta,
} from '../lib/db';
import { getReleases, searchReleases, getWantlist, getArtworkUrl } from '../api';
import type { Release, WantlistItem } from '../types';
import PressingModal from './PressingModal';

const isStandalone = window.matchMedia('(display-mode: standalone)').matches;

// ── Shared helpers ────────────────────────────────────────────────────────────

function Thumb({ src, size = 48 }: { src: string | null; size?: number }) {
  const [err, setErr] = useState(false);
  return (
    <div style={{
      width: size, height: size, flexShrink: 0,
      background: '#222', borderRadius: '4px', overflow: 'hidden',
    }}>
      {src && !err ? (
        <img src={src} alt="" width={size} height={size}
          style={{ objectFit: 'cover', display: 'block' }}
          onError={() => setErr(true)} />
      ) : (
        <div style={{ width: size, height: size, background: '#2a2a2a' }} />
      )}
    </div>
  );
}

// ── LIVE (API-backed) components — shown on Mac ───────────────────────────────

function LiveCollectionSearch() {
  const [query,   setQuery]   = useState('');
  const [results, setResults] = useState<Release[]>([]);
  const [loading, setLoading] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Initial load
  useEffect(() => {
    setLoading(true);
    getReleases({ limit: 100, sort: 'artist_year' })
      .then(r => setResults(r.releases))
      .finally(() => setLoading(false));
  }, []);

  function handleChange(q: string) {
    setQuery(q);
    if (timer.current) clearTimeout(timer.current);
    if (!q.trim()) {
      // reset to full list
      timer.current = setTimeout(() => {
        setLoading(true);
        getReleases({ limit: 100, sort: 'artist_year' })
          .then(r => setResults(r.releases))
          .finally(() => setLoading(false));
      }, 200);
      return;
    }
    timer.current = setTimeout(() => {
      setLoading(true);
      searchReleases(q)
        .then(r => setResults(r.releases.slice(0, 100)))
        .finally(() => setLoading(false));
    }, 300);
  }

  return (
    <div>
      <input
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        placeholder="Search title, artist, label…"
        style={{
          width: '100%', boxSizing: 'border-box',
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          color: 'var(--txt)', borderRadius: '8px',
          padding: '10px 14px', fontSize: '1rem',
          marginBottom: '1rem',
        }}
      />

      {loading && <div style={{ color: 'var(--txt-2)', fontSize: '0.85rem' }}>Loading…</div>}

      {!loading && results.length === 0 && query && (
        <p className="empty-state">Nothing found for &ldquo;{query}&rdquo;</p>
      )}

      {results.map((r) => {
        const art = r.artwork_files?.find((a) => a.image_type === 'primary') ?? r.artwork_files?.[0];
        const thumb = getArtworkUrl(art?.thumbnail_file_path ?? null) ?? art?.original_url ?? null;
        return (
          <div key={r.discogs_id} style={{
            display: 'flex', gap: '12px', alignItems: 'center',
            padding: '10px 0', borderBottom: '1px solid var(--border)',
          }}>
            <Thumb src={thumb} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontWeight: 600, fontSize: '0.88rem',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }}>
                {r.title}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--txt-2)', marginTop: 2 }}>
                {r.artist}{r.year ? ` · ${r.year}` : ''}{r.label ? ` · ${r.label}` : ''}
              </div>
            </div>
            {r.rating ? (
              <span style={{ fontSize: '0.72rem', color: '#ffb300', flexShrink: 0 }}>
                {'★'.repeat(r.rating)}
              </span>
            ) : null}
          </div>
        );
      })}

      {results.length === 100 && (
        <p style={{ fontSize: '0.78rem', color: 'var(--txt-2)', textAlign: 'center', padding: '12px 0' }}>
          Showing first 100 — search to narrow down
        </p>
      )}
    </div>
  );
}

function LiveWantlistTab() {
  const [items,   setItems]   = useState<WantlistItem[]>([]);
  const [query,   setQuery]   = useState('');
  const [loading, setLoading] = useState(true);
  const [pressing, setPressing] = useState<{ masterId: number; releaseId: number; title: string } | null>(null);

  useEffect(() => {
    getWantlist(200)
      .then(r => setItems(r.items))
      .finally(() => setLoading(false));
  }, []);

  const filtered = query.trim()
    ? items.filter((i) =>
        i.title?.toLowerCase().includes(query.toLowerCase()) ||
        i.artist?.toLowerCase().includes(query.toLowerCase()) ||
        (i.label ?? '').toLowerCase().includes(query.toLowerCase()),
      )
    : items;

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search wantlist…"
        style={{
          width: '100%', boxSizing: 'border-box',
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          color: 'var(--txt)', borderRadius: '8px',
          padding: '10px 14px', fontSize: '1rem',
          marginBottom: '1rem',
        }}
      />

      {loading && <div style={{ color: 'var(--txt-2)', fontSize: '0.85rem' }}>Loading wantlist…</div>}

      {!loading && filtered.length === 0 && (
        <p className="empty-state">{query ? `Nothing found for "${query}"` : 'Wantlist is empty'}</p>
      )}

      {filtered.map((w) => (
        <div key={w.discogs_release_id} style={{
          display: 'flex', gap: '12px', alignItems: 'center',
          padding: '10px 0', borderBottom: '1px solid var(--border)',
        }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontWeight: 600, fontSize: '0.88rem',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {w.title}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--txt-2)', marginTop: 2 }}>
              {w.artist}{w.year ? ` · ${w.year}` : ''}{w.label ? ` · ${w.label}` : ''}
            </div>
          </div>
          <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
            {w.availability ? (
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', color: '#81c784', whiteSpace: 'nowrap' }}>
                  {w.currency ?? '$'}{Number(w.lowest_price ?? 0).toFixed(2)}
                </span>
                <div style={{ fontSize: '0.7rem', color: '#4caf50' }}>Available</div>
              </div>
            ) : (
              <span style={{ fontSize: '0.72rem', color: 'var(--txt-2)' }}>
                {w.lowest_price ? 'Unavailable' : 'No price'}
              </span>
            )}
            {w.master_id != null && w.master_id > 0 && (
              <button
                onClick={() => setPressing({ masterId: w.master_id!, releaseId: w.discogs_release_id, title: w.title })}
                style={{
                  fontSize: '0.68rem', padding: '2px 7px', borderRadius: 4,
                  background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer',
                }}
              >
                Pressings
              </button>
            )}
          </div>
        </div>
      ))}

      {pressing && (
        <PressingModal
          masterId={pressing.masterId}
          releaseId={pressing.releaseId}
          title={pressing.title}
          onClose={() => setPressing(null)}
        />
      )}
    </div>
  );
}

// ── OFFLINE (IndexedDB) components — shown on iPhone PWA ─────────────────────

function PriceTag({ price }: { price: OfflinePrice | null }) {
  if (!price || !price.lowest_price) return null;
  return (
    <span style={{ fontSize: '0.75rem', color: '#81c784', whiteSpace: 'nowrap' }}>
      {price.currency ?? '$'}{Number(price.lowest_price).toFixed(2)}
    </span>
  );
}

function OfflineCollectionSearch() {
  const [query,   setQuery]   = useState('');
  const [results, setResults] = useState<OfflineRelease[]>([]);
  const [prices,  setPrices]  = useState<Record<number, OfflinePrice | null>>({});
  const [loading, setLoading] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { runSearch(''); }, []);

  function runSearch(q: string) {
    setLoading(true);
    searchCollection(q)
      .then((res) => {
        setResults(res.slice(0, 100));
        const ids = res.slice(0, 100).map((r) => r.discogs_id);
        Promise.all(ids.map((id) => getPriceFor(id).then((p) => [id, p] as const)))
          .then((pairs) => {
            const map: Record<number, OfflinePrice | null> = {};
            for (const [id, p] of pairs) map[id] = p;
            setPrices(map);
          });
      })
      .finally(() => setLoading(false));
  }

  function handleChange(q: string) {
    setQuery(q);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => runSearch(q), 200);
  }

  return (
    <div>
      <input
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        placeholder="Search title, artist, label…"
        autoFocus
        style={{
          width: '100%', boxSizing: 'border-box',
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          color: 'var(--txt)', borderRadius: '8px',
          padding: '10px 14px', fontSize: '1rem',
          marginBottom: '1rem',
        }}
      />
      {loading && <div style={{ color: 'var(--txt-2)', fontSize: '0.85rem' }}>Searching…</div>}
      {!loading && results.length === 0 && query && (
        <p className="empty-state">Nothing found for &ldquo;{query}&rdquo;</p>
      )}
      {results.map((r) => (
        <div key={r.discogs_id} style={{
          display: 'flex', gap: '12px', alignItems: 'center',
          padding: '10px 0', borderBottom: '1px solid var(--border)',
        }}>
          <Thumb src={r.thumb} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontWeight: 600, fontSize: '0.88rem',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {r.title}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--txt-2)', marginTop: 2 }}>
              {r.artist}{r.year ? ` · ${r.year}` : ''}{r.label ? ` · ${r.label}` : ''}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
            <PriceTag price={prices[r.discogs_id] ?? null} />
            {r.rating ? (
              <span style={{ fontSize: '0.72rem', color: '#ffb300' }}>
                {'★'.repeat(r.rating)}
              </span>
            ) : null}
          </div>
        </div>
      ))}
      {results.length === 100 && (
        <p style={{ fontSize: '0.78rem', color: 'var(--txt-2)', textAlign: 'center', padding: '12px 0' }}>
          Showing first 100 — search to narrow down
        </p>
      )}
    </div>
  );
}

function OfflineWantlistTab() {
  const [items,   setItems]   = useState<OfflineWantItem[]>([]);
  const [query,   setQuery]   = useState('');
  const [prices,  setPrices]  = useState<Record<number, OfflinePrice | null>>({});
  const [loading, setLoading] = useState(true);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    getAllWantlist().then((all) => {
      setItems(all);
      setLoading(false);
      Promise.all(all.map((w) => getPriceFor(w.discogs_release_id).then((p) => [w.discogs_release_id, p] as const)))
        .then((pairs) => {
          const map: Record<number, OfflinePrice | null> = {};
          for (const [id, p] of pairs) map[id] = p;
          setPrices(map);
        });
    });
  }, []);

  const filtered = query.trim()
    ? items.filter((i) =>
        i.title?.toLowerCase().includes(query.toLowerCase()) ||
        i.artist?.toLowerCase().includes(query.toLowerCase()) ||
        i.label?.toLowerCase().includes(query.toLowerCase()),
      )
    : items;

  function handleChange(q: string) {
    setQuery(q);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {}, 0);
  }

  return (
    <div>
      <input
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        placeholder="Search wantlist…"
        style={{
          width: '100%', boxSizing: 'border-box',
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          color: 'var(--txt)', borderRadius: '8px',
          padding: '10px 14px', fontSize: '1rem',
          marginBottom: '1rem',
        }}
      />
      {loading && <div style={{ color: 'var(--txt-2)', fontSize: '0.85rem' }}>Loading wantlist…</div>}
      {!loading && filtered.length === 0 && (
        <p className="empty-state">{query ? `Nothing found for "${query}"` : 'Wantlist is empty'}</p>
      )}
      {filtered.map((w) => {
        const price = prices[w.discogs_release_id] ?? null;
        return (
          <div key={w.discogs_release_id} style={{
            display: 'flex', gap: '12px', alignItems: 'center',
            padding: '10px 0', borderBottom: '1px solid var(--border)',
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontWeight: 600, fontSize: '0.88rem',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }}>
                {w.title}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--txt-2)', marginTop: 2 }}>
                {w.artist}{w.year ? ` · ${w.year}` : ''}{w.label ? ` · ${w.label}` : ''}
              </div>
            </div>
            <div style={{ flexShrink: 0 }}>
              {price?.availability ? (
                <div style={{ textAlign: 'right' }}>
                  <PriceTag price={price} />
                  <div style={{ fontSize: '0.7rem', color: '#4caf50' }}>Available</div>
                </div>
              ) : (
                <span style={{ fontSize: '0.72rem', color: 'var(--txt-2)' }}>
                  {price ? 'Unavailable' : 'No price'}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Offline New Releases tab ──────────────────────────────────────────────────

function OfflineNewReleasesTab() {
  const [items, setItems]   = useState<OfflineNewRelease[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery]   = useState('');

  useEffect(() => {
    getOfflineNewReleases().then((r) => { setItems(r); setLoading(false); });
  }, []);

  const filtered = query.trim()
    ? items.filter((i) =>
        i.title?.toLowerCase().includes(query.toLowerCase()) ||
        i.artist?.toLowerCase().includes(query.toLowerCase()),
      )
    : items;

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search new finds…"
        style={{
          width: '100%', boxSizing: 'border-box',
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          color: 'var(--txt)', borderRadius: '8px',
          padding: '10px 14px', fontSize: '1rem',
          marginBottom: '1rem',
        }}
      />
      {loading && <div style={{ color: 'var(--txt-2)', fontSize: '0.85rem' }}>Loading…</div>}
      {!loading && filtered.length === 0 && (
        <p className="empty-state">{query ? `Nothing found for "${query}"` : 'No new releases in snapshot'}</p>
      )}
      {filtered.map((item) => (
        <div key={item.id} style={{
          display: 'flex', gap: '12px', alignItems: 'center',
          padding: '10px 0', borderBottom: '1px solid var(--border)',
        }}>
          <Thumb src={item.thumb} size={48} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontWeight: 600, fontSize: '0.88rem',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {item.title}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--txt-2)', marginTop: 2 }}>
              {item.artist}{item.year ? ` · ${item.year}` : ''}{item.label ? ` · ${item.label}` : ''}
            </div>
          </div>
          <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
            {item.cached_lowest_price != null && (
              <span style={{ fontSize: '0.75rem', color: '#81c784', whiteSpace: 'nowrap' }}>
                {item.cached_currency ?? '$'}{Number(item.cached_lowest_price).toFixed(2)}
              </span>
            )}
            {item.in_wantlist && (
              <span style={{ fontSize: '0.68rem', color: 'var(--accent)', fontWeight: 700 }}>WANTLIST</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main OfflineView ──────────────────────────────────────────────────────────

type Tab = 'collection' | 'wantlist' | 'new-releases';

export default function OfflineView() {
  const [tab, setTab] = useState<Tab>('collection');

  // iPhone-only offline state
  const [syncedAt,        setSyncedAt]        = useState<string | null>(null);
  const [count,           setCount]           = useState<number | null>(null);
  const [newReleasesCount, setNewReleasesCount] = useState<number | null>(null);

  useEffect(() => {
    if (isStandalone) {
      getSyncMeta().then((m) => {
        if (m) {
          setSyncedAt(m.synced_at);
          setCount(m.collection_count);
          setNewReleasesCount(m.new_releases_count ?? null);
        }
      });
    }
  }, []);

  const tabDefs: { key: Tab; label: string }[] = [
    { key: 'collection',   label: '🎵 Collection'  },
    { key: 'wantlist',     label: '❤️ Wantlist'    },
    { key: 'new-releases', label: '✨ New Finds'   },
  ];

  const tabBar = (
    <div style={{ display: 'flex', gap: '6px', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
      {tabDefs.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => setTab(key)}
          style={{
            background:   tab === key ? 'var(--accent)' : 'var(--bg-card)',
            color:        tab === key ? '#fff' : 'var(--txt)',
            border:       `1px solid ${tab === key ? 'var(--accent)' : 'var(--border)'}`,
            borderRadius: '7px', padding: '7px 16px',
            fontSize:     '0.87rem', fontWeight: tab === key ? 700 : 400,
            cursor:       'pointer',
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );

  // ── Mac / browser: live from database ──────────────────────────────────────
  if (!isStandalone) {
    return (
      <div>
        <div style={{ marginBottom: '1.5rem' }}>
          <h2 className="section-title">My Vinyl</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--txt-2)', marginTop: 4 }}>
            Live from database
          </p>
        </div>
        {/* Only show collection + wantlist tabs on desktop — new finds are in their own view */}
        <div style={{ display: 'flex', gap: '6px', marginBottom: '1.25rem' }}>
          {tabDefs.filter(d => d.key !== 'new-releases').map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTab(key as Tab)}
              style={{
                background:   tab === key ? 'var(--accent)' : 'var(--bg-card)',
                color:        tab === key ? '#fff' : 'var(--txt)',
                border:       `1px solid ${tab === key ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: '7px', padding: '7px 18px',
                fontSize:     '0.87rem', fontWeight: tab === key ? 700 : 400,
                cursor:       'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>
        {tab === 'collection' && <LiveCollectionSearch />}
        {tab === 'wantlist'   && <LiveWantlistTab />}
      </div>
    );
  }

  // ── iPhone PWA: offline from IndexedDB ─────────────────────────────────────
  const hasData = count !== null && count > 0;

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 className="section-title">My Vinyl</h2>
        {syncedAt ? (
          <p style={{ fontSize: '0.8rem', color: 'var(--txt-2)', marginTop: 4 }}>
            {count?.toLocaleString()} records
            {newReleasesCount != null && newReleasesCount > 0 ? ` · ${newReleasesCount.toLocaleString()} new finds` : ''}
            {' · synced '}
            {new Date(syncedAt).toLocaleDateString()}
          </p>
        ) : (
          <p style={{ fontSize: '0.8rem', color: 'var(--txt-2)', marginTop: 4 }}>
            Tap the sync button above to download your collection for offline use.
          </p>
        )}
      </div>

      {!hasData ? (
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: '10px', padding: '32px 24px', textAlign: 'center',
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '12px' }}>📲</div>
          <div style={{ fontWeight: 600, marginBottom: '8px' }}>No offline data yet</div>
          <div style={{ fontSize: '0.83rem', color: 'var(--txt-2)', lineHeight: 1.5 }}>
            Tap <strong>Sync to device</strong> in the top bar while connected to your Mac
            to download your collection. After that it works anywhere — no internet needed.
          </div>
        </div>
      ) : (
        <>
          {tabBar}
          {tab === 'collection'   && <OfflineCollectionSearch />}
          {tab === 'wantlist'     && <OfflineWantlistTab />}
          {tab === 'new-releases' && <OfflineNewReleasesTab />}
        </>
      )}
    </div>
  );
}
