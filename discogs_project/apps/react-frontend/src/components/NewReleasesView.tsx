import ApiErrorBanner from './ApiErrorBanner';
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getNewReleases, syncNewReleases,
  getNewReleasePrices, dismissNewRelease, undismissNewRelease, addToWantlistFromFeed,
} from '../api';
import type { NewRelease, NewReleasePriceEntry } from '../types';

// ── Chip config: display label → comma-separated style filter string ──────────
const CHIPS: { key: string; label: string; styles?: string }[] = [
  { key: 'all',     label: 'All' },
  { key: 'disco',   label: 'Disco',    styles: 'Disco,Nu-Disco,Italo-Disco' },
  { key: 'house',   label: 'House',    styles: 'House,Deep House,Garage House,Tech House,Acid House,Tribal House' },
  { key: 'boogie',  label: 'Boogie',   styles: 'Boogie' },
  { key: 'citypop', label: 'City Pop', styles: 'City Pop' },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function AlbumArt({ src, title }: { src: string | null; title: string }) {
  const [err, setErr] = useState(false);
  if (!src || err) {
    return (
      <div style={{
        width: '100%', aspectRatio: '1 / 1',
        background: 'var(--bg)', borderRadius: 6,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '2rem', color: 'var(--txt-2)',
      }}>
        ♪
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={title}
      onError={() => setErr(true)}
      style={{ width: '100%', aspectRatio: '1 / 1', objectFit: 'cover', borderRadius: 6, display: 'block' }}
    />
  );
}

interface OverlayBtnProps {
  onClick: (e: React.MouseEvent) => void;
  style?: React.CSSProperties;
  children: React.ReactNode;
  title: string;
}
function OverlayBtn({ onClick, style, children, title }: OverlayBtnProps) {
  return (
    <button
      title={title}
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClick(e); }}
      style={{
        position: 'absolute',
        width: 44, height: 44,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,0.55)',
        border: 'none', borderRadius: '50%',
        cursor: 'pointer', color: '#fff',
        fontSize: '1rem', lineHeight: 1,
        padding: 0,
        ...style,
      }}
    >
      {children}
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

function NewReleasesView() {
  const [items, setItems] = useState<NewRelease[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [prices, setPrices] = useState<Record<string, NewReleasePriceEntry>>({});
  const [latestSync, setLatestSync] = useState<string | null>(null);
  const [activeChip, setActiveChip] = useState<string>('all');
  const [toast, setToast] = useState<{ item: NewRelease; index: number; msg?: string } | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearToast = () => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = null;
    setToast(null);
  };

  const load = useCallback((styleFilter?: string) => {
    setLoading(true);
    setError(null);
    setPrices({});
    getNewReleases(40, styleFilter)
      .then((res) => {
        setItems(res.items);
        setLatestSync(res.latest_sync);
        // Fire-and-forget price fetch after grid loads
        if (res.items.length) {
          const ids = res.items.map(i => i.discogs_release_id);
          getNewReleasePrices(ids)
            .then(r => setPrices(r.prices))
            .catch(() => { /* prices are non-critical, silently skip */ });
        }
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const chip = CHIPS.find(c => c.key === activeChip);
    load(chip?.styles);
  }, [load, activeChip]);

  // Cleanup toast timer on unmount
  useEffect(() => () => { if (toastTimerRef.current) clearTimeout(toastTimerRef.current); }, []);

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const res = await syncNewReleases();
      setSyncMsg(res.message);
      const chip = CHIPS.find(c => c.key === activeChip);
      load(chip?.styles);
    } catch (e: unknown) {
      setSyncMsg(e instanceof Error ? e.message : 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const handleDismiss = async (item: NewRelease) => {
    const index = items.findIndex(i => i.id === item.id);
    // Optimistically remove
    setItems(prev => prev.filter(i => i.id !== item.id));
    // Clear any existing toast
    clearToast();
    // Show undo toast for 5s
    toastTimerRef.current = setTimeout(clearToast, 5000);
    setToast({ item, index });

    try {
      await dismissNewRelease(item.id);
    } catch {
      // Restore on failure
      setItems(prev => {
        const next = [...prev];
        next.splice(index, 0, item);
        return next;
      });
      clearToast();
      setToast({ item, index, msg: 'Dismiss failed' });
      toastTimerRef.current = setTimeout(clearToast, 3000);
    }
  };

  const handleUndo = async () => {
    if (!toast) return;
    const { item, index } = toast;
    clearToast();
    // Re-insert at original position
    setItems(prev => {
      const next = [...prev];
      next.splice(index, 0, item);
      return next;
    });
    try {
      await undismissNewRelease(item.id);
    } catch {
      // If undismiss fails, remove again silently — it will be gone on next load
      setItems(prev => prev.filter(i => i.id !== item.id));
    }
  };

  const handleWant = async (item: NewRelease) => {
    // Optimistic update
    setItems(prev => prev.map(i => i.id === item.id ? { ...i, in_wantlist: true } : i));
    try {
      await addToWantlistFromFeed(item.id);
    } catch (e: unknown) {
      // Revert
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, in_wantlist: false } : i));
      clearToast();
      const msg = e instanceof Error ? e.message : 'Failed to add to wantlist';
      setToast({ item, index: 0, msg });
      toastTimerRef.current = setTimeout(clearToast, 3000);
    }
  };

  const isNew = (item: NewRelease): boolean => {
    if (!latestSync) return false;
    return (new Date(latestSync).getTime() - new Date(item.discovered_at).getTime()) < 24 * 60 * 60 * 1000;
  };

  const formatPrice = (entry: NewReleasePriceEntry | undefined): React.ReactNode => {
    if (!entry) return <span style={{ display: 'block', height: '1em' }} />;
    if (entry.num_for_sale == null || entry.num_for_sale === 0) return <span style={{ fontSize: '0.65rem', color: 'var(--txt-2)' }}>not for sale</span>;
    const price = entry.lowest_price != null
      ? `$${entry.lowest_price.toFixed(2)}`
      : '—';
    return (
      <span style={{ fontSize: '0.65rem', color: 'var(--accent)' }}>
        {price} · {entry.num_for_sale} for sale
      </span>
    );
  };

  return (
    <div className="new-releases-view">
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        <h2 className="section-title" style={{ margin: 0 }}>New Releases</h2>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-primary"
          style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
        >
          {syncing ? 'Syncing…' : '↻ Sync'}
        </button>
        {syncMsg && <span style={{ fontSize: '0.8rem', color: 'var(--accent)' }}>{syncMsg}</span>}
      </div>

      {/* Style filter chips */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        {CHIPS.map(chip => (
          <button
            key={chip.key}
            onClick={() => setActiveChip(chip.key)}
            style={{
              padding: '0.3rem 0.85rem',
              borderRadius: 20,
              border: '1px solid var(--border)',
              background: activeChip === chip.key ? 'var(--accent)' : 'var(--bg-card)',
              color: activeChip === chip.key ? '#fff' : 'var(--txt)',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: activeChip === chip.key ? 600 : 400,
              transition: 'background 0.15s, color 0.15s',
            }}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading">Loading new releases...</div>
      ) : error ? (
        <ApiErrorBanner error={error} onRetry={() => { const c = CHIPS.find(ch => ch.key === activeChip); load(c?.styles); }} />
      ) : items.length === 0 ? (
        <div className="empty-state">
          <p>No new releases found. Hit <strong>↻ Sync</strong> to fetch the latest from Discogs.</p>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
          gap: '1rem',
        }}>
          {items.map((item) => {
            const priceEntry = prices[String(item.discogs_release_id)];
            const newBadge = isNew(item);
            return (
              <a
                key={item.id}
                href={`https://www.discogs.com/release/${item.discogs_release_id}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ textDecoration: 'none', color: 'inherit' }}
              >
                <div
                  style={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 8,
                    overflow: 'hidden',
                    transition: 'border-color 0.15s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                >
                  {/* Art with overlays */}
                  <div style={{ position: 'relative' }}>
                    <AlbumArt src={item.thumb} title={item.title} />

                    {/* NEW badge — top left */}
                    {newBadge && (
                      <span style={{
                        position: 'absolute', top: 6, left: 6,
                        background: 'var(--accent)', color: '#fff',
                        fontSize: '0.6rem', fontWeight: 700,
                        padding: '2px 6px', borderRadius: 10,
                        pointerEvents: 'none',
                      }}>
                        NEW
                      </span>
                    )}

                    {/* ✕ dismiss — top right */}
                    <OverlayBtn
                      title="Not interested"
                      onClick={() => handleDismiss(item)}
                      style={{ top: 4, right: 4 }}
                    >
                      ✕
                    </OverlayBtn>

                    {/* ♡ / WANTLIST — bottom right */}
                    {item.in_wantlist ? (
                      <span style={{
                        position: 'absolute', bottom: 6, right: 6,
                        background: 'var(--accent)', color: '#fff',
                        fontSize: '0.6rem', fontWeight: 700,
                        padding: '2px 6px', borderRadius: 10,
                        pointerEvents: 'none',
                      }}>
                        ❤ WANT
                      </span>
                    ) : (
                      <OverlayBtn
                        title="Add to wantlist"
                        onClick={() => handleWant(item)}
                        style={{ bottom: 4, right: 4, fontSize: '1.1rem' }}
                      >
                        ♡
                      </OverlayBtn>
                    )}
                  </div>

                  {/* Card text */}
                  <div style={{ padding: '8px 10px' }}>
                    <div style={{
                      fontWeight: 600, fontSize: '0.78rem',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      {item.title}
                    </div>
                    <div style={{
                      fontSize: '0.72rem', color: 'var(--txt-2)',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                      marginTop: 2,
                    }}>
                      {item.artist}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--txt-2)', marginTop: 2 }}>
                      {item.year ?? '—'}{item.label ? ` · ${item.label}` : ''}
                    </div>
                    <div style={{ marginTop: 3, minHeight: '1em' }}>
                      {formatPrice(priceEntry)}
                    </div>
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      )}

      {/* Dismiss toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 8, padding: '0.6rem 1.2rem',
          display: 'flex', alignItems: 'center', gap: '1rem',
          boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
          zIndex: 1000, fontSize: '0.85rem',
          whiteSpace: 'nowrap',
        }}>
          <span>{toast.msg ?? 'Dismissed'}</span>
          {!toast.msg && (
            <button
              onClick={handleUndo}
              style={{
                background: 'var(--accent)', color: '#fff',
                border: 'none', borderRadius: 6,
                padding: '0.3rem 0.8rem', cursor: 'pointer',
                fontSize: '0.8rem', fontWeight: 600,
              }}
            >
              Undo
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default NewReleasesView;
