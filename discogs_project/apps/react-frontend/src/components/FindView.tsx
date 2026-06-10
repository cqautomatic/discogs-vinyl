/**
 * FindView — "why a collector buys" hub
 *
 * Sub-tabs:
 *   🔥 Buy Now  — wantlist items for sale right now, ranked by want/have ratio
 *   🧩 Gaps     — label or artist catalogue minus what you own
 *   🧭 Explore  — Similar Artists, Affordable Grails, Style Search,
 *                 Collection Expander, Discogs Lists, New Releases
 */

import { useState, useEffect, useCallback } from 'react';
import ApiErrorBanner from './ApiErrorBanner';
import DiggingView from './DiggingView';
import NewReleasesView from './NewReleasesView';
import { fetchJSON } from '../api';
import { getSimilarArtists, getAffordableGrails } from '../api';
import type { SimilarArtist, AffordableGrail, PgNum } from '../types';

// ── Types ─────────────────────────────────────────────────────────────────────

interface BuyNowItem {
  discogs_release_id: number;
  title: string;
  artist: string;
  year: number | null;
  label: string | null;
  lowest_price: number | null;
  currency: string | null;
  num_for_sale: number;
  community_want_count: number | null;
  community_have_count: number | null;
  ratio: number | null;
  thumb: string | null;
}

interface GapItem {
  discogs_id: number;
  title: string;
  artist?: string;
  year: number | null;
  thumb: string | null;
  role?: string | null;
  format?: string | null;
  community_want: number;
  community_have: number;
  ratio?: number | null;
}

// ── Shared styles ─────────────────────────────────────────────────────────────

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: 13,
};

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '8px 12px',
  borderBottom: '1px solid var(--border)',
  color: 'var(--txt-2)',
  fontWeight: 600,
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  whiteSpace: 'nowrap',
};

const tdStyle: React.CSSProperties = {
  padding: '8px 12px',
  borderBottom: '1px solid var(--border)',
  color: 'var(--txt)',
};

const linkStyle: React.CSSProperties = {
  color: 'var(--accent)',
  textDecoration: 'none',
};

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
  borderRadius: 6,
  color: 'var(--txt)',
  padding: '6px 12px',
  fontSize: 13,
  width: 180,
};

const btnStyle: React.CSSProperties = {
  background: 'var(--accent)',
  border: 'none',
  borderRadius: 6,
  color: '#fff',
  padding: '6px 18px',
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtUSD(v: number | null | undefined): string {
  if (v == null) return '—';
  return `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDec(v: PgNum | number | null | undefined, digits = 2): string {
  if (v == null) return '—';
  const n = Number(v);
  return isNaN(n) ? '—' : n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function discogsReleaseUrl(id: number): string {
  return `https://www.discogs.com/release/${id}`;
}

function discogsArtistUrl(name: string): string {
  return `https://www.discogs.com/search/?q=${encodeURIComponent(name)}&type=artist`;
}


// ── Album thumbnail ───────────────────────────────────────────────────────────

function AlbumThumb({ src, alt }: { src: string | null; alt: string }) {
  if (!src) {
    return (
      <div style={{
        width: 36, height: 36, borderRadius: 4, flexShrink: 0,
        background: 'var(--bg-card)', border: '1px solid var(--border)',
      }} />
    );
  }
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      style={{ width: 36, height: 36, borderRadius: 4, objectFit: 'cover', flexShrink: 0 }}
    />
  );
}

// ── Badge: want/have ratio indicator ─────────────────────────────────────────

function RatioBadge({ ratio }: { ratio: number | null }) {
  if (ratio == null || ratio < 2) return null;
  return (
    <span
      title="High want/have ratio"
      style={{
        background: '#1a3050',
        color: '#64b5f6',
        border: '1px solid #64b5f644',
        borderRadius: 4,
        padding: '1px 6px',
        fontSize: '0.7rem',
        fontWeight: 700,
        marginLeft: 4,
        letterSpacing: '0.04em',
      }}
    >
      ⭐ {fmtDec(ratio, 1)}×
    </span>
  );
}

// Phase 2 placeholder badges (rendered dimmed, not yet computed)
function Phase2Badges() {
  return (
    <span style={{ marginLeft: 4 }}>
      <span title="Price drop badge — coming in Phase 2" style={{ opacity: 0.25, fontSize: '0.75rem', marginRight: 3 }}>📉</span>
      <span title="Grail badge — coming in Phase 2" style={{ opacity: 0.25, fontSize: '0.75rem' }}>🔥</span>
    </span>
  );
}

// ── Sub-tab: Buy Now ──────────────────────────────────────────────────────────

function BuyNowPanel() {
  const [maxPrice, setMaxPrice] = useState('');
  const [items, setItems] = useState<BuyNowItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((mp: string) => {
    setLoading(true);
    setError(null);
    const qs = mp ? `?max_price=${encodeURIComponent(mp)}` : '';
    fetchJSON<{ items: BuyNowItem[] }>(`/api/find/buy-now${qs}`)
      .then((r) => setItems(r.items))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(''); }, [load]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <p style={{ color: 'var(--txt-2)', fontSize: 13, margin: 0 }}>
        Wantlist items with copies for sale right now, ranked by want/have ratio.
      </p>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <label style={{ color: 'var(--txt-2)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
          Max price ($):
          <input
            type="number"
            min={1}
            value={maxPrice}
            placeholder="any"
            onChange={(e) => setMaxPrice(e.target.value)}
            style={{ ...inputStyle, width: 100 }}
          />
        </label>
        <button type="button" style={btnStyle} onClick={() => load(maxPrice)} disabled={loading}>
          Apply
        </button>
        {maxPrice && (
          <button
            type="button"
            style={{ ...btnStyle, background: 'var(--bg-card)', color: 'var(--txt-2)', border: '1px solid var(--border)' }}
            onClick={() => { setMaxPrice(''); load(''); }}
          >
            Clear
          </button>
        )}
      </div>

      {loading && <div className="loading">Loading…</div>}
      {error && <ApiErrorBanner error={error} />}
      {!loading && !error && items.length === 0 && (
        <div className="loading">No wantlist items for sale right now.</div>
      )}
      {!loading && !error && items.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                {['', '', 'Artist', 'Title', 'Year', 'Label', 'Price', '# For Sale', 'Want', 'Have', 'Ratio'].map((h, i) => (
                  <th key={i} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.discogs_release_id}>
                  <td style={{ ...tdStyle, padding: '6px 8px' }}>
                    <AlbumThumb src={item.thumb} alt={item.title} />
                  </td>
                  <td style={{ ...tdStyle, whiteSpace: 'nowrap' }}>
                    <RatioBadge ratio={Number(item.ratio)} />
                    <Phase2Badges />
                  </td>
                  <td style={tdStyle}>
                    <a href={discogsArtistUrl(item.artist)} target="_blank" rel="noopener noreferrer" style={linkStyle}>
                      {item.artist}
                    </a>
                  </td>
                  <td style={tdStyle}>
                    <a href={discogsReleaseUrl(item.discogs_release_id)} target="_blank" rel="noopener noreferrer" style={linkStyle}>
                      {item.title}
                    </a>
                  </td>
                  <td style={tdStyle}>{item.year ?? '—'}</td>
                  <td style={tdStyle}>{item.label ?? '—'}</td>
                  <td style={tdStyle}>{fmtUSD(item.lowest_price)}{item.currency && item.currency !== 'USD' ? ` ${item.currency}` : ''}</td>
                  <td style={tdStyle}>{item.num_for_sale}</td>
                  <td style={tdStyle}>{item.community_want_count ?? '—'}</td>
                  <td style={tdStyle}>{item.community_have_count ?? '—'}</td>
                  <td style={tdStyle}>{fmtDec(item.ratio)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Sub-tab: Gaps ─────────────────────────────────────────────────────────────

type GapsMode = 'label' | 'artist';

function GapsPanel() {
  const [mode, setMode] = useState<GapsMode>('label');
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<GapItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [cached, setCached] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function search() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setItems([]);
    const param = mode === 'label' ? `label` : `artist`;
    fetchJSON<{ items: GapItem[]; cached: boolean }>(
      `/api/find/gaps/${mode}?${param}=${encodeURIComponent(query.trim())}`,
    )
      .then((r) => { setItems(r.items); setCached(r.cached); })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }

  // Reset results when mode changes
  useEffect(() => { setItems([]); setQuery(''); setError(null); }, [mode]);

  const placeholder = mode === 'label' ? 'e.g. Blue Note' : 'e.g. John Coltrane';
  const columns = mode === 'label'
    ? ['', 'Title', 'Artist', 'Year', 'Want', 'Have', 'Ratio']
    : ['', 'Title', 'Year', 'Role', 'Format', 'Want', 'Have'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Mode toggle */}
      <div className="sub-nav">
        {(['label', 'artist'] as GapsMode[]).map((m) => (
          <button
            key={m}
            type="button"
            className={`nav-btn${mode === m ? ' active' : ''}`}
            onClick={() => setMode(m)}
            style={{ fontSize: 13 }}
          >
            {m === 'label' ? '🏷 Label' : '🎤 Artist'}
          </button>
        ))}
      </div>

      <p style={{ color: 'var(--txt-2)', fontSize: 13, margin: 0 }}>
        {mode === 'label'
          ? 'Find desirable records from a label you don\'t own yet. Only shows releases with want/have > 1.0 and 150+ wants.'
          : 'Find releases by an artist that aren\'t in your collection, ranked by popularity.'}
      </p>

      {/* Search input */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') search(); }}
          style={inputStyle}
        />
        <button type="button" style={btnStyle} onClick={search} disabled={loading || !query.trim()}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </div>

      {loading && (
        <div className="loading">
          Fetching Discogs catalogue — this can take a moment for large catalogues…
        </div>
      )}
      {error && <ApiErrorBanner error={error} />}
      {!loading && !error && items.length === 0 && query && (
        <div className="loading">No gaps found — you may already own everything desirable, or try a different spelling.</div>
      )}

      {!loading && !error && items.length > 0 && (
        <>
          <div style={{ fontSize: 12, color: 'var(--txt-2)' }}>
            {items.length} results for <strong style={{ color: 'var(--txt)' }}>{query}</strong>
            {cached && <span style={{ marginLeft: 8, color: 'var(--accent)' }}>⚡ cached</span>}
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  {columns.map((h) => (
                    <th key={h} style={thStyle}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.discogs_id}>
                    <td style={{ ...tdStyle, padding: '6px 8px' }}>
                      <AlbumThumb src={item.thumb} alt={item.title} />
                    </td>
                    <td style={tdStyle}>
                      <a
                        href={discogsReleaseUrl(item.discogs_id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={linkStyle}
                      >
                        {item.title}
                      </a>
                    </td>
                    {mode === 'label' && (
                      <td style={tdStyle}>
                        {item.artist ? (
                          <a href={discogsArtistUrl(item.artist)} target="_blank" rel="noopener noreferrer" style={linkStyle}>
                            {item.artist}
                          </a>
                        ) : '—'}
                      </td>
                    )}
                    <td style={tdStyle}>{item.year ?? '—'}</td>
                    {mode === 'artist' && (
                      <>
                        <td style={tdStyle}>{item.role ?? '—'}</td>
                        <td style={tdStyle}>{item.format ?? '—'}</td>
                      </>
                    )}
                    <td style={tdStyle}>{item.community_want}</td>
                    <td style={tdStyle}>{item.community_have}</td>
                    {mode === 'label' && <td style={tdStyle}>{fmtDec(item.ratio)}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

// ── Sub-tab: Explore ──────────────────────────────────────────────────────────

type ExploreTab = 'similar-artists' | 'affordable-grails' | 'style-search' | 'new-releases';

const EXPLORE_TABS: { key: ExploreTab; label: string }[] = [
  { key: 'similar-artists',  label: 'Similar Artists'  },
  { key: 'affordable-grails', label: 'Affordable Grails' },
  { key: 'style-search',     label: 'Style / Dig'      },
  { key: 'new-releases',     label: 'New Releases'     },
];

function SimilarArtistThumb({ src, title }: { src: string | null; title: string }) {
  const [err, setErr] = useState(false);
  if (!src || err) {
    return (
      <div style={{
        width: 56, height: 56, flexShrink: 0,
        background: 'var(--bg)', borderRadius: 6,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '1.4rem', color: 'var(--txt-2)',
      }}>♪</div>
    );
  }
  return (
    <img
      src={src} alt={title} onError={() => setErr(true)}
      style={{ width: 56, height: 56, flexShrink: 0, objectFit: 'cover', borderRadius: 6 }}
    />
  );
}

// Thin wrappers that re-use existing panel logic from RecommendationsView
function SimilarArtistsPanel() {
  const [artists, setArtists] = useState<SimilarArtist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSimilarArtists(30)
      .then((r) => setArtists(r.artists))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading…</div>;
  if (error) return <ApiErrorBanner error={error} />;
  if (artists.length === 0) return <div className="loading">No data.</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {artists.map((a) => (
        <div key={a.artist} style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 10, padding: '12px 14px',
          display: 'flex', gap: 12, alignItems: 'flex-start',
        }}>
          {/* Top release art — links to that release */}
          {a.top_release_discogs_id ? (
            <a href={`https://www.discogs.com/release/${a.top_release_discogs_id}`} target="_blank" rel="noopener noreferrer" style={{ flexShrink: 0 }}>
              <SimilarArtistThumb src={a.top_release_thumb} title={a.top_release_title ?? a.artist} />
            </a>
          ) : (
            <SimilarArtistThumb src={null} title={a.artist} />
          )}

          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Artist name */}
            <a href={discogsArtistUrl(a.artist)} target="_blank" rel="noopener noreferrer"
              style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--txt)', textDecoration: 'none' }}>
              {a.artist}
            </a>

            {/* Top release title */}
            {a.top_release_title && (
              <div style={{ fontSize: '0.78rem', color: 'var(--txt-2)', marginTop: 2,
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {a.top_release_discogs_id
                  ? <a href={`https://www.discogs.com/release/${a.top_release_discogs_id}`} target="_blank" rel="noopener noreferrer" style={linkStyle}>{a.top_release_title}</a>
                  : a.top_release_title}
              </div>
            )}

            {/* Similar to */}
            {a.similar_to_artists?.length ? (
              <div style={{ fontSize: '0.75rem', color: 'var(--txt-2)', marginTop: 4 }}>
                Similar to:{' '}
                {a.similar_to_artists.map((sa, i) => (
                  <span key={sa}>
                    <a href={discogsArtistUrl(sa)} target="_blank" rel="noopener noreferrer" style={linkStyle}>{sa}</a>
                    {i < (a.similar_to_artists?.length ?? 0) - 1 ? ', ' : ''}
                  </span>
                ))}
              </div>
            ) : null}

            {/* Shared labels + wantlist count */}
            <div style={{ fontSize: '0.72rem', color: 'var(--txt-2)', marginTop: 4, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {a.shared_labels?.length ? (
                <span>{a.shared_labels.slice(0, 3).join(', ')}</span>
              ) : null}
              <span style={{ color: 'var(--accent)' }}>{a.wantlist_count} on wantlist</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function AffordableGrailsPanel() {
  const [maxPrice, setMaxPrice] = useState(25);
  const [minRatio, setMinRatio] = useState(2.0);
  const [items, setItems] = useState<AffordableGrail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function doFetch(mp: number, mr: number) {
    setLoading(true);
    setError(null);
    getAffordableGrails(mp, mr, 20)
      .then((r) => setItems(r.items))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed'))
      .finally(() => setLoading(false));
  }

  useEffect(() => { doFetch(maxPrice, minRatio); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const ctrlInput: React.CSSProperties = { ...inputStyle, width: 80 };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <label style={{ color: 'var(--txt-2)', fontSize: 13 }}>
          Max price ($):
          <input type="number" min={1} value={maxPrice} onChange={(e) => setMaxPrice(Number(e.target.value))} style={{ ...ctrlInput, marginLeft: 8 }} />
        </label>
        <label style={{ color: 'var(--txt-2)', fontSize: 13 }}>
          Min ratio:
          <input type="number" min={0.1} step={0.1} value={minRatio} onChange={(e) => setMinRatio(Number(e.target.value))} style={{ ...ctrlInput, marginLeft: 8 }} />
        </label>
        <button type="button" style={btnStyle} onClick={() => doFetch(maxPrice, minRatio)} disabled={loading}>Apply</button>
      </div>
      {loading && <div className="loading">Loading…</div>}
      {error && <ApiErrorBanner error={error} />}
      {!loading && !error && items.length === 0 && <div className="loading">No data.</div>}
      {!loading && !error && items.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                {['', 'Artist', 'Title', 'Price', 'Want', 'Have', 'Ratio'].map((h, i) => (
                  <th key={i} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.discogs_release_id}>
                  <td style={{ ...tdStyle, padding: '6px 8px' }}>
                    <AlbumThumb src={item.thumb} alt={item.title} />
                  </td>
                  <td style={tdStyle}>
                    <a href={discogsArtistUrl(item.artist)} target="_blank" rel="noopener noreferrer" style={linkStyle}>{item.artist}</a>
                  </td>
                  <td style={tdStyle}>
                    <a href={discogsReleaseUrl(item.discogs_release_id)} target="_blank" rel="noopener noreferrer" style={linkStyle}>{item.title}</a>
                  </td>
                  <td style={tdStyle}>{fmtUSD(Number(item.lowest_price))}</td>
                  <td style={tdStyle}>{item.community_want_count ?? '—'}</td>
                  <td style={tdStyle}>{item.community_have_count ?? '—'}</td>
                  <td style={tdStyle}>{fmtDec(item.want_have_ratio)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ExplorePanel() {
  const [tab, setTab] = useState<ExploreTab>('similar-artists');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="sub-nav">
        {EXPLORE_TABS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            className={`nav-btn${tab === key ? ' active' : ''}`}
            onClick={() => setTab(key)}
            style={{ fontSize: 13 }}
          >
            {label}
          </button>
        ))}
      </div>
      <div>
        {tab === 'similar-artists'  && <SimilarArtistsPanel />}
        {tab === 'affordable-grails' && <AffordableGrailsPanel />}
        {tab === 'style-search'     && <DiggingView />}
        {tab === 'new-releases'     && <NewReleasesView />}
      </div>
    </div>
  );
}

// ── FindView ──────────────────────────────────────────────────────────────────

type FindTab = 'buy-now' | 'gaps' | 'explore';

const FIND_TABS: { key: FindTab; label: string }[] = [
  { key: 'buy-now',  label: '🔥 Buy Now'  },
  { key: 'gaps',     label: '🧩 Gaps'     },
  { key: 'explore',  label: '🧭 Explore'  },
];

function FindView() {
  const [tab, setTab] = useState<FindTab>('buy-now');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h2 className="section-title">Find</h2>

      {/* Top tab bar */}
      <div className="sub-nav">
        {FIND_TABS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            className={`nav-btn${tab === key ? ' active' : ''}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <div>
        {tab === 'buy-now'  && <BuyNowPanel />}
        {tab === 'gaps'     && <GapsPanel />}
        {tab === 'explore'  && <ExplorePanel />}
      </div>
    </div>
  );
}

export default FindView;
