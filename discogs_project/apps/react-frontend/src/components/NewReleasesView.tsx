import { useState, useEffect } from 'react';
import { getNewReleases } from '../api';
import type { NewRelease } from '../types';
import ExternalLinks from './ExternalLinks';

function NewReleasesView() {
  const [items, setItems] = useState<NewRelease[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getNewReleases()
      .then((res) => setItems(res.items))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading new releases...</div>;
  if (error) return <div className="error-banner">{error}</div>;

  return (
    <div className="new-releases-view">
      <h2 className="section-title">New Releases</h2>
      {items.length === 0 ? (
        <div className="empty-state">
          <p>No new releases found.</p>
          <p>Run <code>python sync_new_releases.py</code> from the postgres app directory to populate this feed.</p>
        </div>
      ) : (
        <div className="new-releases-list">
          {items.map((item) => (
            <div key={item.id} className="new-release-row">
              <div className="new-release-info">
                <strong>{item.title}</strong>
                <span className="release-artist">{item.artist}</span>
                <span className="release-meta">
                  {item.year ?? '—'}{item.label ? ` · ${item.label}` : ''}{item.country ? ` · ${item.country}` : ''}
                </span>
              </div>
              <ExternalLinks title={item.title} artist={item.artist} discogs_id={item.discogs_release_id} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
export default NewReleasesView;
