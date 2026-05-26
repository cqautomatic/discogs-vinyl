import { useState, useEffect, useCallback } from 'react';
import { getNewReleases, syncNewReleases } from '../api';
import type { NewRelease } from '../types';
import ExternalLinks from './ExternalLinks';

function NewReleasesView() {
  const [items, setItems] = useState<NewRelease[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getNewReleases()
      .then((res) => setItems(res.items))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const res = await syncNewReleases();
      setSyncMsg(res.message);
      load();
    } catch (e: unknown) {
      setSyncMsg(e instanceof Error ? e.message : 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="new-releases-view">
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
        <h2 className="section-title" style={{ margin: 0 }}>New Releases</h2>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-primary"
          style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
        >
          {syncing ? 'Syncing…' : '↻ Sync'}
        </button>
        {syncMsg && <span style={{ fontSize: '0.85rem', color: 'var(--accent)' }}>{syncMsg}</span>}
      </div>

      {loading ? (
        <div className="loading">Loading new releases...</div>
      ) : error ? (
        <div className="error-banner">{error}</div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <p>No new releases found. Hit <strong>↻ Sync</strong> to fetch the latest from Discogs.</p>
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
