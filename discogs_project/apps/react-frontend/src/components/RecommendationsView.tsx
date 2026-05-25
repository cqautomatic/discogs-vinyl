import { useState, useEffect } from 'react';
import {
  getSimilarArtists,
  getAffordableGrails,
  getCompleteDecade,
  getGenreValueMap,
  getLabelGaps,
  getDecadeGaps,
  getArtistGaps,
  getCollectionHealth,
} from '../api';
import type {
  SimilarArtist,
  AffordableGrail,
  CompleteDecadeItem,
  GenreValueEntry,
  LabelGap,
  DecadeGap,
  ArtistGap,
  CollectionHealth,
  PgNum,
} from '../types';

type RecTab =
  | 'similar-artists'
  | 'affordable-grails'
  | 'complete-decade'
  | 'genre-value-map'
  | 'label-gaps'
  | 'decade-gaps'
  | 'artist-gaps';

const TAB_LABELS: Record<RecTab, string> = {
  'similar-artists': 'Similar Artists',
  'affordable-grails': 'Affordable Grails',
  'complete-decade': 'Complete the Decade',
  'genre-value-map': 'Genre Value Map',
  'label-gaps': 'Label Gaps',
  'decade-gaps': 'Decade Gaps',
  'artist-gaps': 'Artist Gaps',
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
    getSimilarArtists(20)
      .then(r => setArtists(r.artists))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load similar artists'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (artists.length === 0) return <div className="loading">No data available.</div>;

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {['Artist', 'Wantlist Count', 'Shared Labels'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {artists.map(a => (
            <tr key={a.artist}>
              <td style={tdStyle}>{a.artist}</td>
              <td style={tdStyle}>{toNum(a.wantlist_count) ?? '—'}</td>
              <td style={tdStyle}>{a.shared_labels ? a.shared_labels.join(', ') : '—'}</td>
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

  function exportGrailsCSV(items: AffordableGrail[]) {
    const header = 'Artist,Title,Year,Label,Price,Currency,For Sale,Want,Have,Ratio';
    const rows = items.map((i) =>
      [i.artist, i.title, i.year ?? '', i.label ?? '',
       Number(i.lowest_price ?? 0).toFixed(2), i.currency ?? '',
       i.num_for_sale ?? 0, i.community_want_count ?? 0,
       i.community_have_count ?? 0, Number(i.want_have_ratio ?? 0).toFixed(2)].join(',')
    );
    const csv = [header, ...rows].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a = document.createElement('a');
    a.href = url; a.download = 'grails.csv'; a.click();
    URL.revokeObjectURL(url);
  }

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
      {error && <div className="error-banner">{error}</div>}
      {!loading && !error && items.length === 0 && <div className="loading">No data available.</div>}
      {!loading && !error && items.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <button type="button" className="export-btn" onClick={() => exportGrailsCSV(items)}>Export CSV</button>
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
                  <td style={tdStyle}>{item.artist}</td>
                  <td style={tdStyle}>{item.title}</td>
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

// ── Panel: Complete the Decade ────────────────────────────────────────────────

function CompleteDecadePanel() {
  const [items, setItems] = useState<CompleteDecadeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getCompleteDecade(20)
      .then(r => setItems(r.items))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load decade completions'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (items.length === 0) return <div className="loading">No data available.</div>;

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {['Decade', 'Artist', 'Title', 'Year', 'Price', 'Available'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.discogs_release_id}>
              <td style={tdStyle}>{item.decade_label}</td>
              <td style={tdStyle}>{item.artist}</td>
              <td style={tdStyle}>{item.title}</td>
              <td style={tdStyle}>{item.year ?? '—'}</td>
              <td style={tdStyle}>{item.availability ? fmtUSD(item.lowest_price) : '—'}</td>
              <td style={tdStyle}>
                <span style={{ color: item.availability ? '#4ade80' : 'var(--txt-2)' }}>
                  {item.availability ? 'Yes' : 'No'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Panel: Genre Value Map ────────────────────────────────────────────────────

function GenreValueMapPanel() {
  const [genres, setGenres] = useState<GenreValueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getGenreValueMap()
      .then(r => {
        const sorted = [...r.genres].sort((a, b) => {
          const ra = toNum(a.avg_rating) ?? 0;
          const rb = toNum(b.avg_rating) ?? 0;
          return rb - ra;
        });
        setGenres(sorted);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load genre value map'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (genres.length === 0) return <div className="loading">No data available.</div>;

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {['Genre', 'Wantlist Items', 'Avg Price', 'Avg Rating'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {genres.map(g => (
            <tr key={g.genre}>
              <td style={tdStyle}>{g.genre}</td>
              <td style={tdStyle}>{toNum(g.wantlist_count) ?? '—'}</td>
              <td style={tdStyle}>{fmtUSD(g.avg_price)}</td>
              <td style={tdStyle}>{fmtDec(g.avg_rating)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Panel: Label Gaps ─────────────────────────────────────────────────────────

function LabelGapsPanel() {
  const [labels, setLabels] = useState<LabelGap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getLabelGaps(15)
      .then(r => setLabels(r.labels))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load label gaps'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (labels.length === 0) return <div className="loading">No data available.</div>;

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {['Label', 'Owned Releases', 'Artists', 'Avg Rating'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {labels.map(l => (
            <tr key={l.label}>
              <td style={tdStyle}>{l.label}</td>
              <td style={tdStyle}>{toNum(l.owned_releases) ?? '—'}</td>
              <td style={tdStyle}>{toNum(l.unique_artists) ?? '—'}</td>
              <td style={tdStyle}>{fmtDec(l.avg_rating)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Panel: Decade Gaps ────────────────────────────────────────────────────────

function DecadeGapsPanel() {
  const [decades, setDecades] = useState<DecadeGap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getDecadeGaps()
      .then(r => setDecades(r.decades))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load decade gaps'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (decades.length === 0) return <div className="loading">No data available.</div>;

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {['Decade', 'Releases', 'Coverage'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {decades.map(d => {
            const pct = Math.min(100, Math.max(0, toNum(d.coverage_pct) ?? 0));
            return (
              <tr key={d.decade_start}>
                <td style={tdStyle}>{d.decade_label}</td>
                <td style={tdStyle}>{toNum(d.releases_owned) ?? '—'}</td>
                <td style={{ ...tdStyle, minWidth: 160 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, background: 'var(--bg-2)', borderRadius: 4, height: 8, overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, background: '#4ade80', height: '8px' }} />
                    </div>
                    <span style={{ color: 'var(--txt-2)', fontSize: 11, whiteSpace: 'nowrap' }}>
                      {pct.toFixed(1)}%
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Panel: Artist Gaps ────────────────────────────────────────────────────────

function ArtistGapsPanel() {
  const [artists, setArtists] = useState<ArtistGap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getArtistGaps(20)
      .then(r => setArtists(r.artists))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load artist gaps'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (artists.length === 0) return <div className="loading">No data available.</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <p style={{ color: 'var(--txt-2)', fontSize: 12 }}>
        Artists with fewest owned releases — potential collection gaps
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              {['Artist', 'Owned Releases', 'Avg Rating'].map(h => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {artists.map(a => (
              <tr key={a.artist}>
                <td style={tdStyle}>{a.artist}</td>
                <td style={tdStyle}>{toNum(a.owned_releases) ?? '—'}</td>
                <td style={tdStyle}>{fmtDec(a.avg_rating)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
        {activeTab === 'complete-decade' && <CompleteDecadePanel />}
        {activeTab === 'genre-value-map' && <GenreValueMapPanel />}
        {activeTab === 'label-gaps' && <LabelGapsPanel />}
        {activeTab === 'decade-gaps' && <DecadeGapsPanel />}
        {activeTab === 'artist-gaps' && <ArtistGapsPanel />}
      </div>
    </div>
  );
}

export default RecommendationsView;
