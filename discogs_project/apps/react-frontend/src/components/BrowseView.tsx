import { useState, useEffect, useCallback } from 'react';
import { getReleases, getGenres, getStyles } from '../api';
import type { Release, GenreStat, StyleStat, PgNum } from '../types';
import ReleaseCard from './ReleaseCard';
import ReleaseDetail from './ReleaseDetail';

const PAGE_SIZE = 24;

function toNum(v: PgNum): number {
  return Number(v) || 0;
}

function BrowseView() {
  const [releases, setReleases] = useState<Release[]>([]);
  const [resultCount, setResultCount] = useState<number>(0);
  const [offset, setOffset] = useState(0);
  const [genres, setGenres] = useState<GenreStat[]>([]);
  const [styles, setStyles] = useState<StyleStat[]>([]);
  const savedFilters = (() => {
    try { return JSON.parse(localStorage.getItem('browse-filters') ?? '{}'); } catch { return {}; }
  })();
  const [selectedGenre, setSelectedGenre] = useState<string>(savedFilters.genre ?? '');
  const [selectedStyle, setSelectedStyle] = useState<string>(savedFilters.style ?? '');
  const [selectedReleaseId, setSelectedReleaseId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load filter options once
  useEffect(() => {
    getGenres().then(setGenres).catch(() => { /* filter failure is non-fatal */ });
    getStyles().then(setStyles).catch(() => { /* filter failure is non-fatal */ });
  }, []);

  const loadReleases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getReleases({
        limit: PAGE_SIZE,
        offset,
        genre: selectedGenre || undefined,
        style: selectedStyle || undefined,
      });
      setReleases(res.releases);
      setResultCount(toNum(res.count));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load releases');
    } finally {
      setLoading(false);
    }
  }, [offset, selectedGenre, selectedStyle]);

  useEffect(() => {
    loadReleases();
  }, [loadReleases]);

  function handleGenreChange(genre: string) {
    setSelectedGenre(genre);
    setOffset(0);
    localStorage.setItem('browse-filters', JSON.stringify({ genre, style: selectedStyle }));
  }

  function handleStyleChange(style: string) {
    setSelectedStyle(style);
    setOffset(0);
    localStorage.setItem('browse-filters', JSON.stringify({ genre: selectedGenre, style }));
  }

  // API returns count of rows fetched (not total matching). Use it to detect last page.
  const hasMore = resultCount >= PAGE_SIZE;
  const hasPrev = offset > 0;
  const pageNum = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="browse-view">
      <div className="filter-bar">
        <div className="filter-group">
          <label htmlFor="genre-select">Genre</label>
          <select
            id="genre-select"
            value={selectedGenre}
            onChange={(e) => handleGenreChange(e.target.value)}
          >
            <option value="">All Genres</option>
            {genres.map((g) => (
              <option key={g.genre} value={g.genre}>
                {g.genre} ({toNum(g.release_count).toLocaleString()})
              </option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="style-select">Style</label>
          <select
            id="style-select"
            value={selectedStyle}
            onChange={(e) => handleStyleChange(e.target.value)}
          >
            <option value="">All Styles</option>
            {styles.map((s) => (
              <option key={s.style} value={s.style}>
                {s.style} ({toNum(s.release_count).toLocaleString()})
              </option>
            ))}
          </select>
        </div>
        {!loading && (
          <span className="result-count">
            Page {pageNum}
            {selectedGenre || selectedStyle ? ' (filtered)' : ''}
          </span>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="loading">Loading...</div>
      ) : (
        <div className="release-grid">
          {releases.map((r) => (
            <ReleaseCard
              key={r.release_id}
              release={r}
              onClick={() => setSelectedReleaseId(r.discogs_id)}
            />
          ))}
          {releases.length === 0 && (
            <p className="empty-state">No releases found for the selected filters.</p>
          )}
        </div>
      )}

      {(hasPrev || hasMore) && (
        <div className="pagination">
          <button
            type="button"
            disabled={!hasPrev}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            Previous
          </button>
          <span>Page {pageNum}</span>
          <button
            type="button"
            disabled={!hasMore}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next
          </button>
        </div>
      )}

      {selectedReleaseId !== null && (
        <ReleaseDetail
          releaseId={selectedReleaseId}
          onClose={() => setSelectedReleaseId(null)}
        />
      )}
    </div>
  );
}

export default BrowseView;
