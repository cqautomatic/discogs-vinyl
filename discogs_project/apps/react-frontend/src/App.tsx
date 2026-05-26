import { useState, useEffect, useRef } from 'react';
import StatsOverview from './components/StatsOverview';
import BrowseView from './components/BrowseView';
import type { BrowseFilters } from './components/BrowseView';
import SearchView from './components/SearchView';
import CommandCenterView from './components/CommandCenterView';
import RecommendationsView from './components/RecommendationsView';
import NewReleasesView from './components/NewReleasesView';
import ReleaseDetail from './components/ReleaseDetail';
import type { DrillField } from './components/ReleaseDetail';
import { searchReleases } from './api';
import type { Release } from './types';
import './App.css';

const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:3001';

type View = 'overview' | 'browse' | 'search' | 'command-center' | 'discover' | 'new-releases';

function App() {
  const [view, setView] = useState<View>('overview');

  // ── Recommendations badge ─────────────────────────────────────────────────────
  const [availableNow, setAvailableNow] = useState(0);
  useEffect(() => {
    fetch(`${API_BASE}/api/recommendations/health`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d?.health?.available_now) setAvailableNow(Number(d.health.available_now) || 0); })
      .catch(() => {});
  }, []);

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
            className={`nav-btn${view === 'new-releases' ? ' active' : ''}`}
            onClick={() => setView('new-releases')}
            type="button"
          >
            New Releases
          </button>
          <button
            className={`nav-btn${view === 'command-center' ? ' active' : ''}`}
            onClick={() => setView('command-center')}
            type="button"
          >
            Command Center{availableNow > 0 && <span className="nav-badge">{availableNow}</span>}
          </button>
          <button
            className={`nav-btn${view === 'discover' ? ' active' : ''}`}
            onClick={() => setView('discover')}
            type="button"
          >
            Discover
          </button>
        </nav>
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
      <main className="app-main">
        {view === 'overview'       && <StatsOverview />}
        {view === 'browse'         && <BrowseView externalFilters={browseFilters} />}
        {view === 'search'         && <SearchView onDrill={handleGlobalDrill} />}
        {view === 'command-center' && <CommandCenterView />}
        {view === 'discover'       && <RecommendationsView />}
        {view === 'new-releases'   && <NewReleasesView />}

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
