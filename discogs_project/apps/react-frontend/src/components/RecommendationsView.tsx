import ApiErrorBanner from './ApiErrorBanner';
import { useState, useEffect } from 'react';
import {
  getSimilarArtists,
  getAffordableGrails,
  getCollectionHealth,
} from '../api';
import type {
  SimilarArtist,
  AffordableGrail,
  CollectionHealth,
  PgNum,
} from '../types';

type RecTab =
  | 'similar-artists'
  | 'affordable-grails';

const TAB_LABELS: Record<RecTab, string> = {
  'similar-artists': 'Similar Artists',
  'affordable-grails': 'Affordable Grails',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function toNum(v: PgNum): number | null {
  if (v == null) return null;
  const n = Number(v);
  return isNaN(n) ? null : n;
}

function fmtUSD(v: PgNum): string {
  const n = toNum(v);
  return n == null ? '—' : `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDec(v: PgNum, digits = 2): string {
  const n = toNum(v);
  return n == null ? '—' : n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function discogsArtistUrl(name: string): string {
  return `https://www.discogs.com/search/?q=${encodeURIComponent(name)}&type=artist`;
}


const linkStyle: React.CSSProperties = {
  color: 'var(--accent)',
  textDecoration: 'none',
};

// ── Shared table styles ───────────────────────────────────────────────────────

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

// ── Health Card ───────────────────────────────────────────────────────────────

interface HealthCardProps {
  label: string;
  value: string;
}

function HealthCard({ label, value }: HealthCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function CollectionHealthBar() {
  const [health, setHealth] = useState<CollectionHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCollectionHealth()
      .then(r => setHealth(r.health))
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading" style={{ padding: 16 }}>Loading health...</div>;
  if (!health) return <div style={{ color: 'var(--txt-2)', padding: 8 }}>Health data unavailable</div>;

  return (
    <div className="stat-grid" style={{ marginBottom: 8 }}>
      <HealthCard label="Total Wantlist" value={String(toNum(health.total_wantlist) ?? '—')} />
      <HealthCard label="Available Now" value={String(toNum(health.available_now) ?? '—')} />
      <HealthCard label="Total Available Value" value={fmtUSD(health.total_available_value)} />
      <HealthCard label="Items Under $20" value={String(toNum(health.items_under_20) ?? '—')} />
      <HealthCard label="Avg Available Price" value={fmtUSD(health.avg_available_price)} />
    </div>
  );
}

// ── Panel: Similar Artists ────────────────────────────────────────────────────

function SimilarArtistsPanel() {
  const [artists, setArtists] = useState<SimilarArtist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getSimilarArtists(30)
      .then(r => setArtists(r.artists))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load similar artists'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <ApiErrorBanner error={error} />;
  if (artists.length === 0) return <div className="loading">No data available.</div>;

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {['Artist', 'Similar To', 'Shared Labels', 'Wantlist'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {artists.map(a => (
            <tr key={a.artist}>
              <td style={tdStyle}>
                <a href={discogsArtistUrl(a.artist)} target="_blank" rel="noopener noreferrer" style={linkStyle}>
                  {a.artist}
                </a>
              </td>
              <td style={tdStyle}>
                {a.similar_to_artists && a.similar_to_artists.length > 0
                  ? a.similar_to_artists.map((sa, i) => (
                      <span key={sa}>
                        <a href={discogsArtistUrl(sa)} target="_blank" rel="noopener noreferrer" style={linkStyle}>
                          {sa}
                        </a>
                        {i < a.similar_to_artists!.length - 1 ? ', ' : ''}
                      </span>
                    ))
                  : '—'}
              </td>
              <td style={tdStyle}>{a.shared_labels ? a.shared_labels.join(', ') : '—'}</td>
              <td style={tdStyle}>{toNum(a.wantlist_count) ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Panel: Affordable Grails ──────────────────────────────────────────────────

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
      .then(r => setItems(r.items))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load grails'),
      )
      .finally(() => setLoading(false));
  }

  useEffect(() => { doFetch(maxPrice, minRatio); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const inputStyle: React.CSSProperties = {
    marginLeft: 8,
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 6,
    color: 'var(--txt)',
    padding: '5px 10px',
    fontSize: 13,
    width: 80,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <label style={{ color: 'var(--txt-2)', fontSize: 13 }}>
          Max price ($):
          <input
            type="number"
            min={1}
            value={maxPrice}
            onChange={e => setMaxPrice(Number(e.target.value))}
            style={inputStyle}
          />
        </label>
        <label style={{ color: 'var(--txt-2)', fontSize: 13 }}>
          Min ratio:
          <input
            type="number"
            min={0.1}
            step={0.1}
            value={minRatio}
            onChange={e => setMinRatio(Number(e.target.value))}
            style={inputStyle}
          />
        </label>
        <button
          type="button"
          onClick={() => doFetch(maxPrice, minRatio)}
          disabled={loading}
          style={{
            background: 'var(--accent)',
            border: 'none',
            borderRadius: 6,
            color: '#fff',
            padding: '6px 16px',
            fontSize: 13,
            fontWeight: 600,
            cursor: loading ? 'default' : 'pointer',
            opacity: loading ? 0.6 : 1,
          }}
        >
          Apply
        </button>
      </div>
      {loading && <div className="loading">Loading...</div>}
      {error && <ApiErrorBanner error={error} />}
      {!loading && !error && items.length === 0 && <div className="loading">No data available.</div>}
      {!loading && !error && items.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                {['Artist', 'Title', 'Price', 'Want', 'Have', 'Ratio'].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={item.discogs_release_id}>
                  <td style={tdStyle}>
                    <a href={discogsArtistUrl(item.artist)} target="_blank" rel="noopener noreferrer" style={linkStyle}>
                      {item.artist}
                    </a>
                  </td>
                  <td style={tdStyle}>
                    <a
                      href={`https://www.discogs.com/release/${item.discogs_release_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={linkStyle}
                    >
                      {item.title}
                    </a>
                  </td>
                  <td style={tdStyle}>{fmtUSD(item.lowest_price)}</td>
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


// ── RecommendationsView ───────────────────────────────────────────────────────

function RecommendationsView() {
  const [activeTab, setActiveTab] = useState<RecTab>('similar-artists');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h2 className="section-title">Discover</h2>
      <CollectionHealthBar />
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
        {(Object.keys(TAB_LABELS) as RecTab[]).map(tab => (
          <button
            key={tab}
            type="button"
            className={`nav-btn${activeTab === tab ? ' active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>
      <div>
        {activeTab === 'similar-artists' && <SimilarArtistsPanel />}
        {activeTab === 'affordable-grails' && <AffordableGrailsPanel />}
      </div>
    </div>
  );
}

export default RecommendationsView;
