import { useState, useEffect } from 'react';
import { getRelease, getArtworkUrl } from '../api';
import type { Release, PgNum } from '../types';
import ExternalLinks from './ExternalLinks';

export type DrillField = 'genre' | 'style' | 'label' | 'year' | 'country' | 'artist';

interface Props {
  releaseId: number;
  onClose: () => void;
  onDrill?: (field: DrillField, value: string) => void;
}

function fmtPrice(v: PgNum, currency?: string | null): string {
  if (v == null) return '—';
  const n = Number(v);
  if (isNaN(n)) return '—';
  const sym = currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : '$';
  return `${sym}${n.toFixed(2)}`;
}

function Chip({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        color: 'var(--accent)',
        borderRadius: '4px',
        padding: '2px 8px',
        fontSize: '0.82rem',
        cursor: 'pointer',
        marginRight: '4px',
        marginBottom: '4px',
        transition: 'border-color 0.12s, background 0.12s',
      }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
    >
      {label}
    </button>
  );
}

function ReleaseDetail({ releaseId, onClose, onDrill }: Props) {
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

  const primary = release?.artwork_files?.find((a) => a.image_type === 'primary')
    ?? release?.artwork_files?.[0];
  // Prefer full-size local file; fall back to thumbnail, then remote URL
  const imageUrl = getArtworkUrl(primary?.local_file_path ?? null)
    ?? getArtworkUrl(primary?.thumbnail_file_path ?? null)
    ?? primary?.original_url ?? null;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  function drill(field: DrillField, value: string) {
    onClose();
    onDrill?.(field, value);
  }

  return (
    <div className="detail-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        <button className="detail-close" onClick={onClose} type="button" aria-label="Close">✕</button>

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

              {/* Artist — drillable */}
              <p className="detail-artist">
                <Chip label={release.artist} onClick={() => drill('artist', release.artist)} />
              </p>

              <table className="detail-table">
                <tbody>

                  {/* Year — drillable */}
                  {release.year != null && (
                    <tr>
                      <th>Year</th>
                      <td><Chip label={String(release.year)} onClick={() => drill('year', String(release.year))} /></td>
                    </tr>
                  )}

                  {/* Label — drillable */}
                  {release.label && (
                    <tr>
                      <th>Label</th>
                      <td><Chip label={release.label} onClick={() => drill('label', release.label!)} /></td>
                    </tr>
                  )}

                  {release.catno && (
                    <tr><th>Cat #</th><td>{release.catno}</td></tr>
                  )}
                  {release.format && (
                    <tr><th>Format</th><td>{release.format}</td></tr>
                  )}

                  {/* Country — drillable */}
                  {release.country && (
                    <tr>
                      <th>Country</th>
                      <td><Chip label={release.country} onClick={() => drill('country', release.country!)} /></td>
                    </tr>
                  )}

                  {/* Genres — each drillable */}
                  {release.genres && release.genres.length > 0 && (
                    <tr>
                      <th>Genre</th>
                      <td>{release.genres.map(g => (
                        <Chip key={g} label={g} onClick={() => drill('genre', g)} />
                      ))}</td>
                    </tr>
                  )}

                  {/* Styles — each drillable */}
                  {release.styles && release.styles.length > 0 && (
                    <tr>
                      <th>Style</th>
                      <td>{release.styles.map(s => (
                        <Chip key={s} label={s} onClick={() => drill('style', s)} />
                      ))}</td>
                    </tr>
                  )}

                  {release.condition && (
                    <tr>
                      <th>Condition</th>
                      <td>{release.condition}{release.sleeve_condition ? ` / ${release.sleeve_condition}` : ''}</td>
                    </tr>
                  )}
                  {release.rating != null && release.rating > 0 && (
                    <tr>
                      <th>My Rating</th>
                      <td>{'★'.repeat(release.rating)}{'☆'.repeat(5 - release.rating)}</td>
                    </tr>
                  )}
                  {release.community_average_rating != null && (
                    <tr>
                      <th>Community</th>
                      <td>
                        {Number(release.community_average_rating).toFixed(2)}
                        {release.community_rating_count != null
                          ? ` (${Number(release.community_rating_count).toLocaleString()} votes)`
                          : ''}
                      </td>
                    </tr>
                  )}
                  {release.community_have_count != null && (
                    <tr>
                      <th>Have / Want</th>
                      <td>
                        {Number(release.community_have_count).toLocaleString()}
                        {' / '}
                        {Number(release.community_want_count).toLocaleString()}
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
                      <td>{Number(release.num_for_sale).toLocaleString()}</td>
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
