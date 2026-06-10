import { useState, useEffect, useRef } from 'react';
import StatsOverview from './components/StatsOverview';
import BrowseView from './components/BrowseView';
import type { BrowseFilters } from './components/BrowseView';
import SearchView from './components/SearchView';
import FindView from './components/FindView';
import OfflineView from './components/OfflineView';
import StoreView from './components/StoreView';
import SyncPanel from './components/SyncPanel';
import ReleaseDetail from './components/ReleaseDetail';
import type { DrillField } from './components/ReleaseDetail';
import { searchReleases, onCacheHit } from './api';
import type { CacheHit } from './api';
import type { Release } from './types';
import './App.css';


type View = 'overview' | 'browse' | 'search' | 'find' | 'offline' | 'store';

function App() {
  // Default to offline view when running as installed PWA (no browser chrome)
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
  const [view, setView] = useState<View>(isStandalone ? 'offline' : 'overview');

  // ── Online status ─────────────────────────────────────────────────────────────
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  useEffect(() => {
    const up   = () => setIsOnline(true);
    const down = () => setIsOnline(false);
    window.addEventListener('online',  up);
    window.addEventListener('offline', down);
    return () => { window.removeEventListener('online', up); window.removeEventListener('offline', down); };
  }, []);

  // ── Offline cache banner ───────────────────────────────────────────────────
  const [cacheHit, setCacheHit] = useState<CacheHit | null>(null);
  useEffect(() => onCacheHit(setCacheHit), []);


  // ── Header search ─────────────────────────────────────────────────────────────
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState<Release[]>([]);
  const [searchReleaseId, setSearchReleaseId] = useState<number | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleSearchInput(q: string) {
    setSearchQ(q);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!q.trim()) { setSearchResults([]); return; }
    searchTimer.current = setTimeout(async () => {
      try {
        const res = await searchReleases(q);
        setSearchResults(res.releases.slice(0, 5));
      } catch { setSearchResults([]); }
    }, 300);
  }

  // ── Drill navigation ──────────────────────────────────────────────────────────
  // When a chip is clicked in any ReleaseDetail that isn't inside BrowseView,
  // we navigate to Browse and pre-populate the filters.
  const [browseFilters, setBrowseFilters] = useState<BrowseFilters>({});

  function handleGlobalDrill(field: DrillField, value: string) {
    const filters: BrowseFilters = { [field]: field === 'year' ? Number(value) : value };
    setBrowseFilters(filters);
    setView('browse');
    // Close any open search detail
    setSearchReleaseId(null);
    setSearchResults([]);
    setSearchQ('');
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">
          <span className="vinyl-icon" aria-hidden="true">&#9679;</span>
          <h1>Discogs Collection</h1>
        </div>
        <nav className="app-nav" aria-label="Main navigation">
          <button
            className={`nav-btn${view === 'overview' ? ' active' : ''}`}
            onClick={() => setView('overview')}
            type="button"
          >
            Overview
          </button>
          <button
            className={`nav-btn${view === 'browse' ? ' active' : ''}`}
            onClick={() => setView('browse')}
            type="button"
          >
            Browse
          </button>
          <button
            className={`nav-btn${view === 'search' ? ' active' : ''}`}
            onClick={() => setView('search')}
            type="button"
          >
            Search
          </button>
          <button
            className={`nav-btn${view === 'find' ? ' active' : ''}`}
            onClick={() => setView('find')}
            type="button"
          >
            Find
          </button>
          <button
            className={`nav-btn${view === 'offline' ? ' active' : ''}`}
            onClick={() => setView('offline')}
            type="button"
          >
            My Vinyl {!isOnline && <span style={{ fontSize: '0.65rem' }}>●</span>}
          </button>
          <button
            className={`nav-btn${view === 'store' ? ' active' : ''}`}
            onClick={() => setView('store')}
            type="button"
          >
            Store
          </button>
        </nav>
        {isStandalone && (
          <div className="header-actions">
            <SyncPanel isOnline={isOnline} />
          </div>
        )}
        <div className="header-search-wrap">
          <input
            className="header-search"
            placeholder="Quick search..."
            value={searchQ}
            onChange={(e) => handleSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Escape') { setSearchQ(''); setSearchResults([]); } }}
          />
          {searchResults.length > 0 && (
            <ul className="search-dropdown">
              {searchResults.map((r) => (
                <li key={r.release_id}>
                  <button
                    type="button"
                    onClick={() => { setSearchReleaseId(r.discogs_id); setSearchResults([]); setSearchQ(''); }}
                  >
                    {r.artist} — {r.title} {r.year ? `(${r.year})` : ''}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </header>
      {cacheHit && (
        <div className="cache-banner" role="status">
          📵 Offline — showing cached data from{' '}
          {new Date(cacheHit.cachedAt).toLocaleString([], {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit',
          })}
        </div>
      )}
      <main className="app-main">
        {view === 'overview'       && <StatsOverview />}
        {view === 'browse'         && <BrowseView externalFilters={browseFilters} />}
        {view === 'search'         && <SearchView onDrill={handleGlobalDrill} />}
        {view === 'find'           && <FindView />}
        {view === 'offline'        && <OfflineView />}
        {view === 'store'          && <StoreView />}

        {/* Header quick-search detail modal — lives outside the view tree */}
        {searchReleaseId !== null && (
          <ReleaseDetail
            releaseId={searchReleaseId}
            onClose={() => setSearchReleaseId(null)}
            onDrill={handleGlobalDrill}
          />
        )}
      </main>
    </div>
  );
}

export default App;
