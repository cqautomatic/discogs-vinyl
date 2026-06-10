import { useState, useEffect } from 'react';
import { getPressings } from '../api';
import type { PressingVersion, PressingResponse } from '../types';

interface Props {
  masterId: number;
  releaseId: number;
  title: string;
  onClose: () => void;
}

export default function PressingModal({ masterId, releaseId, title, onClose }: Props) {
  const [data, setData] = useState<PressingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPressings(masterId, releaseId)
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load pressings'));
  }, [masterId, releaseId]);

  const cheapest = data?.versions.find((v) => v.lowest_price !== null && !v.is_wantlist_pressing);
  const wantlistPressing = data?.versions.find((v) => v.is_wantlist_pressing);

  function fmtPrice(p: number | null, cur: string | null) {
    if (p === null) return '—';
    return `$${p.toFixed(2)}${cur && cur !== 'USD' ? ` ${cur}` : ''}`;
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box pressing-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-title">Vinyl Pressings</div>
            <div className="modal-subtitle">{title}</div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {!data && !error && (
          <div className="pressing-loading">
            <div className="loading-spinner" />
            <p>Checking pressings… first time can take ~30s</p>
          </div>
        )}

        {error && <div className="pressing-error">{error}</div>}

        {data && (
          <>
            {cheapest || wantlistPressing ? (
              <div className="pressing-summary">
                {cheapest && (
                  <span>Cheapest vinyl: <strong>{fmtPrice(cheapest.lowest_price, cheapest.currency)}</strong> ({cheapest.year} {cheapest.country})</span>
                )}
                {cheapest && wantlistPressing && <span className="pressing-summary-sep"> · </span>}
                {wantlistPressing && (
                  <span>Your wantlist pressing: <strong>{fmtPrice(wantlistPressing.lowest_price, wantlistPressing.currency)}</strong></span>
                )}
              </div>
            ) : null}

            {data.cached && (
              <div className="pressing-cache-note">
                Cached · fetched {data.fetched_at ? new Date(data.fetched_at).toLocaleDateString() : ''}
              </div>
            )}

            <div className="pressing-table-wrap">
              <table className="pressing-table">
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>Country</th>
                    <th>Label</th>
                    <th>Cat#</th>
                    <th>Format</th>
                    <th>Price</th>
                    <th>For Sale</th>
                  </tr>
                </thead>
                <tbody>
                  {data.versions.map((v) => (
                    <PressingRow key={v.discogs_release_id} v={v} fmtPrice={fmtPrice} />
                  ))}
                  {data.versions.length === 0 && (
                    <tr><td colSpan={7} style={{ textAlign: 'center', padding: '1rem', opacity: 0.5 }}>No vinyl pressings found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function PressingRow({ v, fmtPrice }: { v: PressingVersion; fmtPrice: (p: number | null, c: string | null) => string }) {
  let rowClass = '';
  if (v.is_wantlist_pressing) rowClass = 'pressing-row-wantlist';
  if (v.owned) rowClass = 'pressing-row-owned';

  return (
    <tr className={rowClass}>
      <td>{v.year ?? '—'}</td>
      <td>{v.country ?? '—'}</td>
      <td>{v.label ?? '—'}</td>
      <td>{v.catno ?? '—'}</td>
      <td>
        <a href={`https://www.discogs.com/release/${v.discogs_release_id}`} target="_blank" rel="noopener noreferrer" className="table-link">
          {v.format}
        </a>
      </td>
      <td>{fmtPrice(v.lowest_price, v.currency)}</td>
      <td>{v.num_for_sale ?? '—'}</td>
      {v.owned && <td><span className="badge badge-owned">OWNED</span></td>}
      {v.is_wantlist_pressing && !v.owned && <td><span className="badge badge-wantlist">WANTLIST</span></td>}
      {!v.owned && !v.is_wantlist_pressing && <td />}
    </tr>
  );
}
