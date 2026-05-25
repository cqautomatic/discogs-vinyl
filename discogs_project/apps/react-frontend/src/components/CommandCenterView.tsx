import { useState, useEffect } from 'react';
import { getWantlist, getHighDemand, getBudgetRecs } from '../api';
import type { WantlistItem, HighDemandItem, BudgetItem, PgNum } from '../types';

type CmdTab = 'wantlist' | 'high-demand' | 'budget';

function toNum(v: PgNum): number | null {
  if (v == null) return null;
  const n = Number(v);
  return isNaN(n) ? null : n;
}

function fmtUSD(v: PgNum): string {
  const n = toNum(v);
  return n == null ? '—' : `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const TAB_LABELS: Record<CmdTab, string> = {
  wantlist: 'Wantlist',
  'high-demand': 'High Demand',
  budget: 'Budget Buys',
};

// ── Wantlist Panel ────────────────────────────────────────────────────────────

function WantlistPanel() {
  const [items, setItems] = useState<WantlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getWantlist(50)
      .then(r => setItems(r.items))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load wantlist'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (items.length === 0) return <div className="loading">No data available.</div>;

  // Sort: available first
  const sorted = [...items].sort((a, b) => {
    const av = a.availability ? 1 : 0;
    const bv = b.availability ? 1 : 0;
    return bv - av;
  });

  function exportWantlistCSV(items: WantlistItem[]) {
    const header = 'Title,Artist,Year,Label,Price,Currency,Available,For Sale';
    const rows = items.map((i) =>
      [i.title, i.artist, i.year ?? '', i.label ?? '',
       Number(i.lowest_price ?? 0).toFixed(2), i.currency ?? '',
       i.availability ? 'Yes' : 'No', i.num_for_sale ?? 0].join(',')
    );
    const csv = [header, ...rows].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a = document.createElement('a');
    a.href = url; a.download = 'wantlist.csv'; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <button type="button" className="export-btn" onClick={() => exportWantlistCSV(items)}>Export CSV</button>
      <table style={tableStyle}>
        <thead>
          <tr>
            {['Artist', 'Title', 'Year', 'Label', 'Price', 'Available', '# For Sale'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map(item => (
            <tr key={item.discogs_release_id} style={trStyle}>
              <td style={tdStyle}>{item.artist}</td>
              <td style={tdStyle}>{item.title}</td>
              <td style={tdStyle}>{item.year ?? '—'}</td>
              <td style={tdStyle}>{item.label ?? '—'}</td>
              <td style={tdStyle}>
                {item.availability ? fmtUSD(item.lowest_price) : '—'}
              </td>
              <td style={tdStyle}>
                <span style={{ color: item.availability ? '#4ade80' : 'var(--txt-2)' }}>
                  {item.availability ? 'Yes' : 'No'}
                </span>
              </td>
              <td style={tdStyle}>{item.num_for_sale ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── High Demand Panel ─────────────────────────────────────────────────────────

function HighDemandPanel() {
  const [items, setItems] = useState<HighDemandItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getHighDemand(20)
      .then(r => setItems(r.items))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load high demand'),
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
            {['Artist', 'Title', 'Want', 'Have', 'Ratio'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map(item => {
            const ratio = toNum(item.want_have_ratio);
            return (
              <tr key={item.release_id} style={trStyle}>
                <td style={tdStyle}>{item.artist}</td>
                <td style={tdStyle}>{item.title}</td>
                <td style={tdStyle}>{item.community_want_count ?? '—'}</td>
                <td style={tdStyle}>{item.community_have_count ?? '—'}</td>
                <td style={tdStyle}>
                  <span style={ratio != null && ratio > 5.0 ? { fontWeight: 700, color: 'var(--accent)' } : {}}>
                    {ratio != null ? ratio.toFixed(2) : '—'}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Budget Buys Panel ─────────────────────────────────────────────────────────

function BudgetPanel() {
  const [maxPrice, setMaxPrice] = useState(50);
  const [items, setItems] = useState<BudgetItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  function handleFind() {
    setLoading(true);
    setError(null);
    setSearched(true);
    getBudgetRecs(maxPrice, 20)
      .then(r => setItems(r.items))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load budget recs'),
      )
      .finally(() => setLoading(false));
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <label style={{ color: 'var(--txt-2)', fontSize: 13 }}>
          Max price ($):
          <input
            type="number"
            min={1}
            max={500}
            value={maxPrice}
            onChange={e => setMaxPrice(Number(e.target.value))}
            style={{
              marginLeft: 8,
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              color: 'var(--txt)',
              padding: '5px 10px',
              fontSize: 13,
              width: 80,
            }}
          />
        </label>
        <button
          onClick={handleFind}
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
          type="button"
        >
          Find Deals
        </button>
      </div>
      {loading && <div className="loading">Loading...</div>}
      {error && <div className="error-banner">{error}</div>}
      {!loading && searched && !error && items.length === 0 && (
        <div className="loading">No deals found under ${maxPrice}.</div>
      )}
      {!loading && items.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                {['Artist', 'Title', 'Label', 'Price', '# For Sale', 'Source'].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={item.discogs_release_id} style={trStyle}>
                  <td style={tdStyle}>{item.artist}</td>
                  <td style={tdStyle}>{item.title}</td>
                  <td style={tdStyle}>{item.label ?? '—'}</td>
                  <td style={tdStyle}>{fmtUSD(item.lowest_price)}</td>
                  <td style={tdStyle}>{item.num_for_sale ?? '—'}</td>
                  <td style={tdStyle}>{item.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
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

const trStyle: React.CSSProperties = {};

// ── CommandCenterView ─────────────────────────────────────────────────────────

function CommandCenterView() {
  const [activeTab, setActiveTab] = useState<CmdTab>('wantlist');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h2 className="section-title">Command Center</h2>
      <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
        {(Object.keys(TAB_LABELS) as CmdTab[]).map(tab => (
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
        {activeTab === 'wantlist' && <WantlistPanel />}
        {activeTab === 'high-demand' && <HighDemandPanel />}
        {activeTab === 'budget' && <BudgetPanel />}
      </div>
    </div>
  );
}

export default CommandCenterView;
