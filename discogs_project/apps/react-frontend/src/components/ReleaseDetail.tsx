import { useState, useEffect } from 'react';
import { getRelease } from '../api';
import type { Release, PgNum } from '../types';
import ExternalLinks from './ExternalLinks';

interface Props {
  releaseId: number;
  onClose: () => void;
}

function fmtPrice(v: PgNum, currency?: string | null): string {
  if (v == null) return '—';
  const n = Number(v);
  if (isNaN(n)) return '—';
  const sym = currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : '$';
  return `${sym}${n.toFixed(2)}`;
}

function ReleaseDetail({ releaseId, onClose }: Props) {
  const [release, setRelease] = useState<Release | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setRelease(null);
    getRelease(releaseId)
      .then(setRelease)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load release'),
      )
      .finally(() => setLoading(false));
  }, [releaseId]);

  const primary = release?.artwork_files.find((a) => a.image_type === 'primary')
    ?? release?.artwork_files[0];
  const imageUrl = primary?.original_url ?? null;

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      className="detail-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Release detail"
    >
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        <button className="detail-close" onClick={onClose} type="button" aria-label="Close">
          ✕
        </button>

        {loading && <div className="loading">Loading...</div>}
        {error && <div className="error-banner">{error}</div>}

        {release && !loading && (
          <div className="detail-content">
            {imageUrl && (
              <div className="detail-art">
                <img src={imageUrl} alt={`${release.title} cover art`} />
              </div>
            )}
            <div className="detail-info">
              <h2 className="detail-title">{release.title}</h2>
              <p className="detail-artist">{release.artist}</p>

              <table className="detail-table">
                <tbody>
                  {release.year != null && (
                    <tr><th>Year</th><td>{release.year}</td></tr>
                  )}
                  {release.label && (
                    <tr><th>Label</th><td>{release.label}</td></tr>
                  )}
                  {release.catno && (
                    <tr><th>Cat #</th><td>{release.catno}</td></tr>
                  )}
                  {release.format && (
                    <tr><th>Format</th><td>{release.format}</td></tr>
                  )}
                  {release.country && (
                    <tr><th>Country</th><td>{release.country}</td></tr>
                  )}
                  {release.genres && release.genres.length > 0 && (
                    <tr><th>Genre</th><td>{release.genres.join(', ')}</td></tr>
                  )}
                  {release.styles && release.styles.length > 0 && (
                    <tr><th>Style</th><td>{release.styles.join(', ')}</td></tr>
                  )}
                  {release.condition && (
                    <tr>
                      <th>Condition</th>
                      <td>
                        {release.condition}
                        {release.sleeve_condition ? ` / ${release.sleeve_condition}` : ''}
                      </td>
                    </tr>
                  )}
                  {release.rating != null && release.rating > 0 && (
                    <tr>
                      <th>My Rating</th>
                      <td>
                        {'★'.repeat(release.rating)}{'☆'.repeat(5 - release.rating)}
                      </td>
                    </tr>
                  )}
                  {release.community_average_rating != null && (
                    <tr>
                      <th>Community</th>
                      <td>
                        {release.community_average_rating.toFixed(2)}
                        {release.community_rating_count != null
                          ? ` (${release.community_rating_count.toLocaleString()} votes)`
                          : ''}
                      </td>
                    </tr>
                  )}
                  {release.community_have_count != null && (
                    <tr>
                      <th>Have / Want</th>
                      <td>
                        {release.community_have_count.toLocaleString()}
                        {' / '}
                        {release.community_want_count?.toLocaleString() ?? '—'}
                      </td>
                    </tr>
                  )}
                  {release.lowest_price != null && (
                    <tr>
                      <th>Market Low</th>
                      <td>{fmtPrice(release.lowest_price, release.rp_currency)}</td>
                    </tr>
                  )}
                  {release.num_for_sale != null && (
                    <tr>
                      <th>For Sale</th>
                      <td>{release.num_for_sale.toLocaleString()}</td>
                    </tr>
                  )}
                </tbody>
              </table>
              <ExternalLinks title={release.title} artist={release.artist} discogs_id={release.discogs_id} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ReleaseDetail;
