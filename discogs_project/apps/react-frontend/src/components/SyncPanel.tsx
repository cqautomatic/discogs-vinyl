/**
 * SyncPanel — compact control for syncing the collection to device storage.
 * Shown in the App header. Handles API URL config, sync progress, and status.
 */

import { useState, useEffect } from 'react';
import { syncToDevice, getSavedApiUrl, saveApiUrl, type SyncProgress } from '../lib/sync';
import { getSyncMeta } from '../lib/db';

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins  = Math.floor(diff / 60_000);
  const hours = Math.floor(diff / 3_600_000);
  const days  = Math.floor(diff / 86_400_000);
  if (mins < 1)   return 'just now';
  if (mins < 60)  return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

interface Props {
  isOnline: boolean;
}

export default function SyncPanel({ isOnline }: Props) {
  const [open,     setOpen]     = useState(false);
  const [apiUrl,   setApiUrl]   = useState(getSavedApiUrl);
  const [editUrl,  setEditUrl]  = useState(getSavedApiUrl);
  const [progress, setProgress] = useState<SyncProgress>({ stage: 'idle', message: '' });
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [count,    setCount]    = useState<number | null>(null);

  useEffect(() => {
    getSyncMeta().then((m) => {
      if (m) {
        setLastSync(m.synced_at);
        setCount(m.collection_count);
      }
    });
  }, []);

  async function handleSync() {
    setProgress({ stage: 'fetching', message: 'Downloading collection…', percent: 5 });
    try {
      const meta = await syncToDevice(apiUrl, setProgress);
      setLastSync(meta.synced_at);
      setCount(meta.collection_count);
    } catch (e) {
      setProgress({ stage: 'error', message: e instanceof Error ? e.message : 'Sync failed' });
    }
  }

  function handleSaveUrl() {
    let clean = editUrl.trim().replace(/\/$/, '');
    // Prepend https:// if no protocol given
    if (clean && !clean.startsWith('http://') && !clean.startsWith('https://')) {
      clean = 'https://' + clean;
      setEditUrl(clean);
    }
    setApiUrl(clean);
    saveApiUrl(clean);
  }

  const syncing   = progress.stage === 'fetching' || progress.stage === 'storing';
  const hasData   = count !== null && count > 0;
  const statusDot = !isOnline ? '🔴' : hasData ? '🟢' : '⚪️';

  return (
    <div style={{ position: 'relative' }}>
      {/* Compact trigger */}
      <button
        onClick={() => setOpen((o) => !o)}
        title="Offline sync"
        style={{
          background:   'var(--bg-card)',
          border:       '1px solid var(--border)',
          borderRadius: '6px',
          padding:      '5px 10px',
          cursor:       'pointer',
          fontSize:     '0.78rem',
          color:        'var(--txt-2)',
          display:      'flex',
          alignItems:   'center',
          gap:          '5px',
          whiteSpace:   'nowrap',
        }}
      >
        {statusDot}
        {hasData ? `${(count ?? 0).toLocaleString()} offline` : 'Sync to device'}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div style={{
          position:     'absolute',
          top:          'calc(100% + 6px)',
          right:        0,
          zIndex:       200,
          width:        '300px',
          background:   'var(--bg-card)',
          border:       '1px solid var(--border)',
          borderRadius: '10px',
          padding:      '16px',
          boxShadow:    '0 8px 32px rgba(0,0,0,0.4)',
        }}>
          <div style={{ fontWeight: 700, fontSize: '0.88rem', marginBottom: '12px' }}>
            📲 Offline Sync
          </div>

          {/* Status */}
          {lastSync && (
            <div style={{ fontSize: '0.78rem', color: 'var(--txt-2)', marginBottom: '10px' }}>
              Last synced: <strong style={{ color: 'var(--txt)' }}>{timeAgo(lastSync)}</strong>
              {count && <span> · {count.toLocaleString()} records</span>}
            </div>
          )}

          {/* API URL config */}
          <div style={{ marginBottom: '10px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--txt-2)', marginBottom: '4px' }}>
              API URL (defaults to this site — only change if needed)
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <input
                value={editUrl}
                onChange={(e) => setEditUrl(e.target.value)}
                onBlur={handleSaveUrl}
                onKeyDown={(e) => e.key === 'Enter' && handleSaveUrl()}
                placeholder="http://192.168.1.x:3001"
                style={{
                  flex:         1,
                  background:   'var(--bg)',
                  border:       '1px solid var(--border)',
                  color:        'var(--txt)',
                  borderRadius: '5px',
                  padding:      '5px 8px',
                  fontSize:     '0.75rem',
                }}
              />
              <button
                onClick={handleSaveUrl}
                style={{
                  background:   'var(--bg)',
                  border:       '1px solid var(--border)',
                  color:        'var(--accent)',
                  borderRadius: '5px',
                  padding:      '5px 8px',
                  fontSize:     '0.72rem',
                  cursor:       'pointer',
                }}
              >
                Save
              </button>
            </div>
          </div>

          {/* Progress bar */}
          {syncing && (
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--txt-2)', marginBottom: '4px' }}>
                {progress.message}
              </div>
              <div style={{ background: 'var(--bg)', borderRadius: '4px', height: '4px', overflow: 'hidden' }}>
                <div style={{
                  height:     '100%',
                  width:      `${progress.percent ?? 20}%`,
                  background: 'var(--accent)',
                  transition: 'width 0.3s',
                }} />
              </div>
            </div>
          )}

          {/* Done / error message */}
          {(progress.stage === 'done' || progress.stage === 'error') && (
            <div style={{
              fontSize:     '0.78rem',
              color:        progress.stage === 'done' ? '#4caf50' : '#ef5350',
              marginBottom: '10px',
            }}>
              {progress.stage === 'done' ? '✓ ' : '✗ '}{progress.message}
            </div>
          )}

          {/* Sync button */}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn-primary"
            style={{ width: '100%', padding: '8px', fontSize: '0.85rem' }}
          >
            {syncing ? 'Syncing…' : lastSync ? '↻ Sync now' : '⬇ Download collection'}
          </button>

          {!isOnline && (
            <div style={{ fontSize: '0.75rem', color: 'var(--txt-2)', marginTop: '8px', textAlign: 'center' }}>
              Offline — showing cached data
            </div>
          )}

          {/* Install hint (only shown once, on mobile) */}
          <div style={{ fontSize: '0.72rem', color: 'var(--txt-2)', marginTop: '10px', lineHeight: 1.4 }}>
            To install: tap <strong>Share ↑</strong> → <strong>Add to Home Screen</strong> in Safari
          </div>
        </div>
      )}
    </div>
  );
}
