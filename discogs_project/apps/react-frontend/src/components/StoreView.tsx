import { useState, useEffect, useRef, useCallback } from 'react';
import { storeCheck, bandcampCheck, fetchJSON } from '../api';
import type { StoreCheckResult, BandcampResponse } from '../types';
import PressingModal from './PressingModal';
import { offlineStoreSearch, getSyncMeta } from '../lib/db';

// ── Price verdict ─────────────────────────────────────────────────────────────

type Verdict = 'fair' | 'ok' | 'high' | 'rip-off';

interface VerdictResult {
  verdict: Verdict;
  label: string;
  color: string;
}

function getVerdict(shopPrice: number, low: number, high: number): VerdictResult {
  const mid = (low + high) / 2;
  if (shopPrice <= low * 1.1)  return { verdict: 'fair',    label: 'Fair deal',  color: '#4caf50' };
  if (shopPrice <= mid)        return { verdict: 'ok',      label: 'OK price',   color: '#26a69a' };
  if (shopPrice <= high)       return { verdict: 'high',    label: 'Pricey',     color: '#ffa726' };
  return                              { verdict: 'rip-off', label: 'Rip-off',    color: '#ef5350' };
}

// ── Bandcamp panel ────────────────────────────────────────────────────────────

function BandcampPanel({ artist, title }: { artist: string; title: string }) {
  const [data, setData] = useState<BandcampResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    bandcampCheck(artist, title)
      .then(setData)
      .catch(() => {
        const q = encodeURIComponent(`${artist} ${title}`);
        setData({ results: [], fallback_url: `https://bandcamp.com/search?q=${q}&item_type=a` });
      })
      .finally(() => setLoading(false));
  }, [artist, title]);

  if (loading) return <div style={{ fontSize: '0.78rem', color: 'var(--txt-2)' }}>Checking Bandcamp…</div>;
  if (!data)   return null;

  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontSize: '0.72rem', color: 'var(--txt-2)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Bandcamp</div>
      {data.results.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {data.results.map((r, i) => (
            <a key={i} href={r.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.82rem', color: 'var(--accent)' }}>
              {r.band_name} — {r.name} ↗
            </a>
          ))}
        </div>
      ) : (
        <a href={data.fallback_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.82rem', color: 'var(--accent)' }}>
          Search Bandcamp ↗
        </a>
      )}
    </div>
  );
}

// ── Expanded card ─────────────────────────────────────────────────────────────

function ExpandedCard({ item, onClose }: { item: StoreCheckResult; onClose: () => void }) {
  const [shopPriceStr, setShopPriceStr] = useState('');
  const [pressing, setPressing] = useState(false);

  const shopPrice = parseFloat(shopPriceStr);
  const hasShopPrice = !isNaN(shopPrice) && shopPrice > 0;

  const low  = item.low_sold_price  != null ? Number(item.low_sold_price)  : null;
  const high = item.high_sold_price != null ? Number(item.high_sold_price) : null;
  const currentLow = item.lowest_price != null ? Number(item.lowest_price) : null;

  let verdict: VerdictResult | null = null;
  if (hasShopPrice && low != null && high != null) {
    verdict = getVerdict(shopPrice, low, high);
  }

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--accent)',
      borderRadius: 10,
      padding: '14px 16px',
      marginTop: 6,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{item.title}</div>
          <div style={{ fontSize: '0.82rem', color: 'var(--txt-2)' }}>
            {item.artist}{item.year ? ` · ${item.year}` : ''}{item.label ? ` · ${item.label}` : ''}{item.catno ? ` · ${item.catno}` : ''}
          </div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--txt-2)', cursor: 'pointer', fontSize: '1rem', padding: '0 0 0 8px' }}>✕</button>
      </div>

      {/* Shop price input */}
      <div style={{ marginBottom: 10 }}>
        <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--txt-2)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Shop price
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--txt-2)', fontSize: '1rem' }}>$</span>
          <input
            type="number"
            inputMode="decimal"
            placeholder="0.00"
            value={shopPriceStr}
            onChange={(e) => setShopPriceStr(e.target.value)}
            style={{
              width: 100, background: 'var(--bg)', border: '1px solid var(--border)',
              color: 'var(--txt)', borderRadius: 6, padding: '6px 10px',
              fontSize: '1rem',
            }}
          />
          {verdict && (
            <span style={{
              background: verdict.color, color: '#fff',
              borderRadius: 12, padding: '3px 10px',
              fontSize: '0.8rem', fontWeight: 600,
            }}>
              {verdict.label}
            </span>
          )}
        </div>
      </div>

      {/* Price intelligence */}
      {(low != null && high != null) ? (
        <div style={{ fontSize: '0.8rem', color: 'var(--txt-2)', marginBottom: 8 }}>
          Sold range <strong style={{ color: 'var(--txt)' }}>${low.toFixed(2)}–${high.toFixed(2)}</strong>
          {item.last_sold_date && ` · last sold ${item.last_sold_date.split('T')[0]}`}
        </div>
      ) : currentLow != null ? (
        <div style={{ fontSize: '0.8rem', color: 'var(--txt-2)', marginBottom: 8 }}>
          Current cheapest online: <strong style={{ color: 'var(--txt)' }}>${currentLow.toFixed(2)}</strong>
          {item.num_for_sale != null && ` (${item.num_for_sale} for sale)`}
        </div>
      ) : null}

      {/* Discogs link */}
      <div style={{ marginBottom: 8 }}>
        <a
          href={`https://www.discogs.com/release/${item.discogs_release_id}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ fontSize: '0.82rem', color: 'var(--accent)' }}
        >
          View on Discogs ↗
        </a>
      </div>

      {/* Bandcamp */}
      <BandcampPanel artist={item.artist ?? ''} title={item.title} />

      {/* Pressings */}
      {item.master_id != null && item.master_id > 0 && (
        <div style={{ marginTop: 10 }}>
          <button
            onClick={() => setPressing(true)}
            style={{
              fontSize: '0.8rem', padding: '6px 14px', borderRadius: 6,
              background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer',
            }}
          >
            Compare pressings
          </button>
          {pressing && (
            <PressingModal
              masterId={item.master_id}
              releaseId={item.discogs_release_id}
              title={item.title}
              onClose={() => setPressing(false)}
            />
          )}
        </div>
      )}
    </div>
  );
}

// ── Result card ───────────────────────────────────────────────────────────────

function ResultCard({ item, selected, onSelect }: {
  item: StoreCheckResult;
  selected: boolean;
  onSelect: () => void;
}) {
  let chipLabel = '';
  let chipColor = '';
  let chipEmoji = '';
  if (item.owned)              { chipLabel = 'OWNED';       chipColor = '#4caf50'; chipEmoji = '✅ '; }
  else if (item.owns_version)  { chipLabel = 'OWN VERSION'; chipColor = '#26a69a'; chipEmoji = '♻️ '; }
  else if (item.wantlist)      { chipLabel = 'WANTLIST';    chipColor = 'var(--accent)'; chipEmoji = '❤️ '; }
  else                         { chipLabel = 'NEW';         chipColor = 'var(--txt-2)'; chipEmoji = '⬜ '; }

  return (
    <div
      onClick={onSelect}
      style={{
        background: 'var(--bg-card)',
        border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 10,
        padding: '12px 14px',
        cursor: 'pointer',
        userSelect: 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        <span style={{
          flexShrink: 0, background: chipColor, color: '#fff',
          borderRadius: 8, padding: '2px 8px', fontSize: '0.7rem', fontWeight: 700,
          marginTop: 2,
        }}>
          {chipEmoji}{chipLabel}
        </span>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {item.title}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--txt-2)', marginTop: 2 }}>
            {item.artist}{item.year ? ` · ${item.year}` : ''}{item.label ? ` · ${item.label}` : ''}
            {item.source === 'discogs' && <span style={{ color: 'var(--txt-2)', fontSize: '0.7rem' }}> · Discogs</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Cover scanner ─────────────────────────────────────────────────────────────

function CoverScanner({ onResult, onClose }: {
  onResult: (artist: string, title: string, catno: string) => void;
  onClose: () => void;
}) {
  const videoRef   = useRef<HTMLVideoElement>(null);
  const streamRef  = useRef<MediaStream | null>(null);
  const [ready,    setReady]    = useState(false);
  const [scanning, setScanning] = useState(false);
  const [camError,  setCamError]  = useState<string | null>(null); // camera unavailable — replaces video
  const [scanError, setScanError] = useState<string | null>(null); // scan failed — keep camera for retry
  const [identified, setIdentified] = useState<{ artist: string; title: string; catno: string } | null>(null);

  useEffect(() => {
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } } })
      .then((stream) => {
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => setReady(true);
        }
      })
      .catch(() => setCamError('Camera not available — check permissions'));

    return () => { streamRef.current?.getTracks().forEach(t => t.stop()); };
  }, []);

  const capture = async () => {
    const video = videoRef.current;
    if (!video || !ready) return;
    setScanning(true);
    setIdentified(null);
    setScanError(null);

    // Downscale to 768px longest edge before sending
    const MAX = 768;
    const scale = Math.min(MAX / video.videoWidth, MAX / video.videoHeight, 1);
    const w = Math.round(video.videoWidth  * scale);
    const h = Math.round(video.videoHeight * scale);
    const canvas = document.createElement('canvas');
    canvas.width = w; canvas.height = h;
    canvas.getContext('2d')?.drawImage(video, 0, 0, w, h);
    const base64 = canvas.toDataURL('image/jpeg', 0.85).split(',')[1];

    try {
      const result = await fetchJSON<{ artist: string; title: string; catno: string }>('/api/cover-scan', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ image: base64 }),
      });
      setIdentified(result);
    } catch (err) {
      // Surface the server's actual message (422 unreadable photo vs 503 not
      // configured vs Anthropic errors) and keep the camera live for a retry
      setScanError(err instanceof Error ? err.message : 'Could not identify cover — try again');
    } finally {
      setScanning(false);
    }
  };

  const useResult = () => {
    if (identified) {
      onResult(identified.artist, identified.title, identified.catno);
      onClose();
    }
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 100,
      background: 'rgba(0,0,0,0.92)',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: 16,
    }}>
      <div style={{ position: 'relative', width: '100%', maxWidth: 480 }}>
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: -36, right: 0,
            background: 'none', border: 'none', color: '#fff', fontSize: '1.2rem', cursor: 'pointer',
          }}
        >
          ✕ Close
        </button>

        {camError ? (
          <div style={{ color: '#ef5350', textAlign: 'center', padding: 24 }}>{camError}</div>
        ) : (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{ width: '100%', borderRadius: 10, background: '#111' }}
          />
        )}

        {scanError && !identified && (
          <div style={{ marginTop: 10, color: '#ef9a9a', fontSize: '0.82rem', textAlign: 'center' }}>
            {scanError}
          </div>
        )}

        {identified ? (
          <div style={{ marginTop: 12, background: '#1a1a2e', borderRadius: 10, padding: '12px 16px' }}>
            <div style={{ fontSize: '0.72rem', color: '#8888bb', marginBottom: 4, textTransform: 'uppercase' }}>Identified</div>
            <div style={{ fontWeight: 700 }}>{identified.artist}</div>
            <div style={{ color: 'var(--txt-2)', fontSize: '0.9rem' }}>{identified.title}</div>
            {identified.catno && (
              <div style={{ color: 'var(--txt-2)', fontSize: '0.78rem', marginTop: 2 }}>{identified.catno}</div>
            )}
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <button
                onClick={useResult}
                style={{
                  flex: 1, background: 'var(--accent)', color: '#fff',
                  border: 'none', borderRadius: 8, padding: '10px 0',
                  fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer',
                }}
              >
                Search my collection
              </button>
              <button
                onClick={() => setIdentified(null)}
                style={{
                  background: '#333', color: '#fff',
                  border: 'none', borderRadius: 8, padding: '10px 14px',
                  fontSize: '0.9rem', cursor: 'pointer',
                }}
              >
                Retake
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={capture}
            disabled={!ready || scanning}
            style={{
              marginTop: 12, width: '100%',
              background: scanning ? '#555' : 'var(--accent)', color: '#fff',
              border: 'none', borderRadius: 10, padding: '14px 0',
              fontSize: '1rem', fontWeight: 600, cursor: scanning ? 'default' : 'pointer',
            }}
          >
            {scanning ? 'Identifying cover…' : '📷  Identify cover'}
          </button>
        )}
      </div>
    </div>
  );
}

// ── Main view ─────────────────────────────────────────────────────────────────

export default function StoreView() {
  const [query,     setQuery]     = useState('');
  const [results,   setResults]   = useState<StoreCheckResult[]>([]);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState<string | null>(null);
  const [selected,  setSelected]  = useState<StoreCheckResult | null>(null);
  const [isOffline, setIsOffline] = useState(false);
  const [syncedAt,  setSyncedAt]  = useState<string | null>(null);
  const [scanning,  setScanning]  = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    getSyncMeta().then((m) => { if (m) setSyncedAt(m.synced_at); });
  }, []);

  const search = useCallback((q: string) => {
    if (!q.trim()) { setResults([]); setIsOffline(false); return; }
    setLoading(true);
    setError(null);
    setSelected(null);
    storeCheck(q)
      .then((r) => {
        setResults(r.results);
        setIsOffline(false);
        // Discogs fallback failed server-side — distinguish from a real no-match
        if (r.error && r.results.length === 0) setError(r.error);
      })
      .catch(async () => {
        // Network unavailable — fall back to local IndexedDB snapshot
        try {
          const { owned, wantlist } = await offlineStoreSearch(q);
          const wantlistIds = new Set(wantlist.map((w) => w.discogs_release_id));
          const ownedIds = new Set(owned.map((o) => o.discogs_id));
          const merged: StoreCheckResult[] = [
            ...owned.map((o) => ({
              discogs_release_id: o.discogs_id,
              title:    o.title,
              artist:   o.artist,
              year:     o.year,
              label:    o.label,
              catno:    o.catno,
              format:   o.format,
              master_id: null,
              owned:    true,
              owns_version: false,
              wantlist: wantlistIds.has(o.discogs_id),
              lowest_price:    null,
              currency:        null,
              num_for_sale:    null,
              low_sold_price:  null,
              high_sold_price: null,
              last_sold_date:  null,
              source:          'local' as const,
            })),
            ...wantlist
              .filter((w) => !ownedIds.has(w.discogs_release_id))
              .map((w) => ({
                discogs_release_id: w.discogs_release_id,
                title:    w.title,
                artist:   w.artist,
                year:     w.year,
                label:    w.label,
                catno:    w.catno,
                format:   w.format,
                master_id: w.master_id,
                owned:    false,
                owns_version: false,
                wantlist: true,
                lowest_price:    w.lowest_price,
                currency:        w.currency,
                num_for_sale:    w.num_for_sale,
                low_sold_price:  w.low_sold_price,
                high_sold_price: w.high_sold_price,
                last_sold_date:  w.last_sold_date,
                source:          'local' as const,
              })),
          ];
          setResults(merged);
          setIsOffline(true);
        } catch {
          setError('No connection and no offline data. Sync at home to use offline.');
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const handleScanResult = useCallback((artist: string, title: string, catno: string) => {
    // Prefer artist+title — catno is pressing-specific, so it misses owned
    // copies of a different pressing. Fall back to catno if text is unreadable.
    const q = [artist, title].filter(Boolean).join(' ') || catno;
    setQuery(q);
    search(q);
  }, [search]);

  function handleInput(e: React.ChangeEvent<HTMLInputElement>) {
    const q = e.target.value;
    setQuery(q);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(q), 250);
  }

  return (
    <div style={{ padding: '0 0 2rem', maxWidth: 640, margin: '0 auto' }}>
      {scanning && (
        <CoverScanner
          onResult={handleScanResult}
          onClose={() => setScanning(false)}
        />
      )}

      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ margin: '0 0 4px', fontSize: '1.2rem' }}>Store Check</h2>
        <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--txt-2)' }}>
          Search by artist, title, or cat#. Enter a shop price to see if it's fair.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: '1rem' }}>
        <input
          ref={inputRef}
          value={query}
          onChange={handleInput}
          placeholder="Artist, title, or catalog number…"
          style={{
            flex: 1, minWidth: 0,
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            color: 'var(--txt)', borderRadius: 10,
            padding: '14px 16px', fontSize: '1.1rem',
            minHeight: 44,
          }}
        />
        <button
          onClick={() => setScanning(true)}
          title="Identify cover with camera"
          style={{
            flexShrink: 0,
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            color: 'var(--txt)', borderRadius: 10,
            padding: '0 16px', fontSize: '1.3rem', cursor: 'pointer',
            minHeight: 44,
          }}
        >
          📷
        </button>
      </div>

      {isOffline && (
        <div style={{
          background: '#1a1a2e', border: '1px solid #3a3a5c',
          borderRadius: 8, padding: '8px 12px', marginBottom: 8,
          fontSize: '0.78rem', color: '#8888bb',
        }}>
          Offline · local snapshot{syncedAt ? ` from ${new Date(syncedAt).toLocaleDateString()}` : ''}
        </div>
      )}

      {loading && <div style={{ color: 'var(--txt-2)', fontSize: '0.85rem', marginBottom: 8 }}>Searching…</div>}
      {error && <div style={{ color: '#ef5350', fontSize: '0.85rem', marginBottom: 8 }}>{error}</div>}

      {results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {results.map((item) => (
            <div key={`${item.source}-${item.discogs_release_id}`}>
              <ResultCard
                item={item}
                selected={selected?.discogs_release_id === item.discogs_release_id}
                onSelect={() => setSelected(s => s?.discogs_release_id === item.discogs_release_id ? null : item)}
              />
              {selected?.discogs_release_id === item.discogs_release_id && (
                <ExpandedCard item={item} onClose={() => setSelected(null)} />
              )}
            </div>
          ))}
        </div>
      )}

      {!loading && query.trim() && results.length === 0 && !error && (
        <p style={{ color: 'var(--txt-2)', fontSize: '0.85rem' }}>No results for "{query}"</p>
      )}
    </div>
  );
}
