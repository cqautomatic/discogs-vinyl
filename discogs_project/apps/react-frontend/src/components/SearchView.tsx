import ApiErrorBanner from './ApiErrorBanner';
import { useState } from 'react';
import { searchReleases } from '../api';
import type { Release } from '../types';
import ReleaseCard from './ReleaseCard';
import ReleaseDetail from './ReleaseDetail';
import type { DrillField } from './ReleaseDetail';

interface SearchViewProps {
  onDrill?: (field: DrillField, value: string) => void;
}

function SearchView({ onDrill }: SearchViewProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Release[]>([]);
  const [total, setTotal] = useState(0);
  const [displayedQuery, setDisplayedQuery] = useState('');
  const [selectedReleaseId, setSelectedReleaseId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function handleSearch() {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    setDisplayedQuery(q);
    try {
      const res = await searchReleases(q);
      setResults(res.releases);
      setTotal(Number(res.count) || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="search-view">
      <div className="search-bar">
        <input
          type="search"
          className="search-input"
          placeholder="Search by title or artist..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
          aria-label="Search releases"
        />
        <button
          className="search-btn"
          type="button"
          onClick={handleSearch}
          disabled={loading || !query.trim()}
        >
          Search
        </button>
      </div>

      {error && <ApiErrorBanner error={error}  />}
      {loading && <div className="loading">Searching...</div>}

      {!loading && searched && (
        <p className="search-results-header">
          {total} result{total !== 1 ? 's' : ''} for &ldquo;{displayedQuery}&rdquo;
        </p>
      )}

      {!loading && results.length > 0 && (
        <div className="release-grid">
          {results.map((r) => (
            <ReleaseCard
              key={r.release_id}
              release={r}
              onClick={() => setSelectedReleaseId(r.discogs_id)}
            />
          ))}
        </div>
      )}

      {!loading && searched && results.length === 0 && !error && (
        <p className="empty-state">No results for &ldquo;{displayedQuery}&rdquo;.</p>
      )}

      {selectedReleaseId !== null && (
        <ReleaseDetail
          releaseId={selectedReleaseId}
          onClose={() => setSelectedReleaseId(null)}
          onDrill={onDrill}
        />
      )}
    </div>
  );
}

export default SearchView;
