import { useState, useEffect } from 'react';
import { getArtist } from '../api';
import type { ArtistPageData, PgNum } from '../types';
import ReleaseCard from './ReleaseCard';
import ReleaseDetail from './ReleaseDetail';

interface Props { artistName: string; onClose: () => void; }

function ArtistView({ artistName, onClose }: Props) {
  const [data, setData] = useState<ArtistPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    getArtist(artistName)
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [artistName]);

  // Escape key to close
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose]);

  return (
    <div className="detail-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="detail-panel artist-panel" onClick={(e) => e.stopPropagation()}>
        <button className="detail-close" onClick={onClose} type="button" aria-label="Close">✕</button>
        <h2 className="section-title">{artistName}</h2>
        {loading && <div className="loading">Loading...</div>}
        {error && <div className="error-banner">{error}</div>}
        {data && (
          <div className="artist-view-body">
            <div className="artist-section">
              <h3>In Collection ({data.collection.length})</h3>
              {data.collection.length === 0 ? (
                <p className="empty-state">None in collection.</p>
              ) : (
                <div className="release-grid">
                  {data.collection.map((r) => (
                    <ReleaseCard key={r.release_id} release={r} onClick={() => setSelectedId(r.release_id)} />
                  ))}
                </div>
              )}
            </div>
            <div className="artist-section">
              <h3>On Wantlist ({data.wantlist.length})</h3>
              {data.wantlist.length === 0 ? (
                <p className="empty-state">None on wantlist.</p>
              ) : (
                <table className="data-table">
                  <thead><tr><th>Title</th><th>Year</th><th>Label</th><th>Price</th><th>Available</th></tr></thead>
                  <tbody>
                    {data.wantlist.map((w) => (
                      <tr key={w.discogs_release_id}>
                        <td>{w.title}</td>
                        <td>{w.year ?? '—'}</td>
                        <td>{w.label ?? '—'}</td>
                        <td>{w.lowest_price != null ? `$${Number(w.lowest_price as PgNum).toFixed(2)}` : '—'}</td>
                        <td>{w.availability ? 'Yes' : 'No'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
        {selectedId !== null && (
          <ReleaseDetail releaseId={selectedId} onClose={() => setSelectedId(null)} />
        )}
      </div>
    </div>
  );
}
export default ArtistView;
