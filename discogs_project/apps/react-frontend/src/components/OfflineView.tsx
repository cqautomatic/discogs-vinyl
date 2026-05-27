/**
 * OfflineView — browse your collection and wantlist from IndexedDB.
 * Works with zero network connection. Perfect for crate digging.
 */

import { useState, useEffect, useRef } from 'react';
import {
  searchCollection, getAllWantlist, getPriceFor,
  type OfflineRelease, type OfflineWantItem, type OfflinePrice,
} from '../lib/db';
import { getSyncMeta } from '../lib/db';

// ── Shared helpers ────────────────────────────────────────────────────────────

function PriceTag({ price }: { price: OfflinePrice | null }) {
  if (!price || !price.lowest_price) return null;
  return (
    <span style={{ fontSize: '0.75rem', color: '#81c784', whiteSpace: 'nowrap' }}>
      {price.currency ?? '$'}{Number(price.lowest_price).toFixed(2)}
    </span>
  );
}

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

// ── Collection search tab ─────────────────────────────────────────────────────

function CollectionSearch() {
  const [query,   setQuery]   = useState('');
  const [results, setResults] = useState<OfflineRelease[]>([]);
  const [prices,  setPrices]  = useState<Record<number, OfflinePrice | null>>({});
  const [loading, setLoading] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load all on mount
  useEffect(() => { runSearch(''); }, []);

  function runSearch(q: string) {
    setLoading(true);
    searchCollection(q)
      .then((res) => {
        setResults(res.slice(0, 100));
        // Fetch prices for visible results
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

// ── Wantlist tab ──────────────────────────────────────────────────────────────

function WantlistTab() {
  const [items,   setItems]   = useState<OfflineWantItem[]>([]);
  const [query,   setQuery]   = useState('');
  const [prices,  setPrices]  = useState<Record<number, OfflinePrice | null>>({});
  const [loading, setLoading] = useState(true);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    getAllWantlist().then((all) => {
      setItems(all);
      setLoading(false);
      // Fetch prices
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
    timer.current = setTimeout(() => {}, 0); // just triggers re-render via state
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

// ── Main OfflineView ──────────────────────────────────────────────────────────

type Tab = 'collection' | 'wantlist';

export default function OfflineView() {
  const [tab, setTab]         = useState<Tab>('collection');
  const [syncedAt, setSyncedAt] = useState<string | null>(null);
  const [count, setCount]     = useState<number | null>(null);

  useEffect(() => {
    getSyncMeta().then((m) => {
      if (m) { setSyncedAt(m.synced_at); setCount(m.collection_count); }
    });
  }, []);

  const hasData = count !== null && count > 0;

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 className="section-title">My Vinyl</h2>
        {syncedAt ? (
          <p style={{ fontSize: '0.8rem', color: 'var(--txt-2)', marginTop: 4 }}>
            {count?.toLocaleString()} records · synced {new Date(syncedAt).toLocaleDateString()}
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
          {/* Tab bar */}
          <div style={{ display: 'flex', gap: '6px', marginBottom: '1.25rem' }}>
            {(['collection', 'wantlist'] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                style={{
                  background:   tab === t ? 'var(--accent)' : 'var(--bg-card)',
                  color:        tab === t ? '#fff' : 'var(--txt)',
                  border:       `1px solid ${tab === t ? 'var(--accent)' : 'var(--border)'}`,
                  borderRadius: '7px', padding: '7px 18px',
                  fontSize:     '0.87rem', fontWeight: tab === t ? 700 : 400,
                  cursor:       'pointer',
                }}
              >
                {t === 'collection' ? '🎵 Collection' : '❤️ Wantlist'}
              </button>
            ))}
          </div>

          {tab === 'collection' && <CollectionSearch />}
          {tab === 'wantlist'   && <WantlistTab />}
        </>
      )}
    </div>
  );
}
