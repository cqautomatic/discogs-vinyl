import { useState, useEffect } from 'react';
import { getStats } from '../api';
import type { Stats, PgNum } from '../types';

function toNum(v: PgNum): number | null {
  if (v == null) return null;
  const n = Number(v);
  return isNaN(n) ? null : n;
}

function fmtInt(v: PgNum): string {
  const n = toNum(v);
  return n == null ? '—' : n.toLocaleString();
}

function fmtDec(v: PgNum, digits = 2): string {
  const n = toNum(v);
  return n == null ? '—' : n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtUSD(v: PgNum): string {
  const n = toNum(v);
  return n == null ? '—' : `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

interface CardProps {
  label: string;
  value: string;
  sub?: string;
}

function StatCard({ label, value, sub }: CardProps) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function StatsOverview() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load stats'),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading stats...</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (!stats) return null;

  const earliest = toNum(stats.earliest_year);
  const latest = toNum(stats.latest_year);
  const yearRange =
    earliest && latest ? `${earliest} – ${latest}` : '—';

  return (
    <div className="stats-overview">
      <h2 className="section-title">Collection Overview</h2>
      <div className="stat-grid">
        <StatCard label="Total Releases" value={fmtInt(stats.total_items)} />
        <StatCard
          label="Downloaded"
          value={fmtInt(stats.downloaded_items)}
          sub={`of ${fmtInt(stats.total_items)}`}
        />
        <StatCard label="Unique Artists" value={fmtInt(stats.unique_artists)} />
        <StatCard label="Labels" value={fmtInt(stats.unique_labels)} />
        <StatCard label="Countries" value={fmtInt(stats.countries)} />
        <StatCard label="Year Range" value={yearRange} />
        <StatCard
          label="Avg Rating"
          value={fmtDec(stats.avg_rating)}
          sub={`${fmtInt(stats.rated_items)} rated`}
        />
        <StatCard label="Artwork Saved" value={fmtInt(stats.artwork_count)} />
        <StatCard
          label="Est. Collection Value"
          value={fmtUSD(stats.total_value)}
          sub={`${fmtInt(stats.priced_items)} priced items`}
        />
        <StatCard label="Avg Market Price" value={fmtUSD(stats.avg_price)} />
      </div>
    </div>
  );
}

export default StatsOverview;
