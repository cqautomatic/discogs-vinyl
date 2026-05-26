import { useState, useEffect, useCallback, useRef } from 'react';
import { getReleases, getGenres, getStyles } from '../api';
import type { SortOption } from '../api';
import type { Release, GenreStat, StyleStat, PgNum } from '../types';
import ReleaseCard from './ReleaseCard';
import ReleaseDetail from './ReleaseDetail';
import type { DrillField } from './ReleaseDetail';

const PAGE_SIZE = 24;

function toNum(v: PgNum): number {
  return Number(v) || 0;
}

export interface BrowseFilters {
  genre?: string;
  style?: string;
  label?: string;
  year?: number;
  country?: string;
  artist?: string;
}

interface BrowseViewProps {
  externalFilters?: BrowseFilters;
}

function BrowseView({ externalFilters }: BrowseViewProps) {
  const [releases, setReleases] = useState<Release[]>([]);
  const [resultCount, setResultCount] = useState<number>(0);
  const [offset, setOffset] = useState(0);
  const [genres, setGenres] = useState<GenreStat[]>([]);
  const [styles, setStyles] = useState<StyleStat[]>([]);
  const [selectedReleaseId, setSelectedReleaseId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Filter state ──────────────────────────────────────────────────────────────
  const savedFilters = (() => {
    try { return JSON.parse(localStorage.getItem('browse-filters') ?? '{}'); } catch { return {}; }
  })();

  const [selectedGenre,   setSelectedGenre]   = useState<string>(externalFilters?.genre   ?? savedFilters.genre   ?? '');
  const [selectedStyle,   setSelectedStyle]   = useState<string>(externalFilters?.style   ?? savedFilters.style   ?? '');
  const [selectedLabel,   setSelectedLabel]   = useState<string>(externalFilters?.label   ?? '');
  const [selectedYear,    setSelectedYear]    = useState<number | undefined>(externalFilters?.year);
  const [selectedCountry, setSelectedCountry] = useState<string>(externalFilters?.country ?? '');
  const [selectedArtist,  setSelectedArtist]  = useState<string>(externalFilters?.artist  ?? '');
  const [sort, setSort] = useState<SortOption>('artist_year');

  // Sync when externalFilters prop changes (e.g., drill fired while browse is already visible)
  const prevExternalKey = useRef<string | null>(null);
  useEffect(() => {
    if (!externalFilters) return;
    const key = JSON.stringify(externalFilters);
    if (key === prevExternalKey.current) return;
    prevExternalKey.current = key;
    const hasFilter = Object.values(externalFilters).some((v) => v !== undefined && v !== '');
    if (!hasFilter) return;
    setSelectedGenre(externalFilters.genre   ?? '');
    setSelectedStyle(externalFilters.style   ?? '');
    setSelectedLabel(externalFilters.label   ?? '');
    setSelectedYear(externalFilters.year);
    setSelectedCountry(externalFilters.country ?? '');
    setSelectedArtist(externalFilters.artist  ?? '');
    setOffset(0);
  }, [externalFilters]);

  // ── Data loading ──────────────────────────────────────────────────────────────

  // Load filter options once
  useEffect(() => {
    getGenres().then(setGenres).catch(() => {});
    getStyles().then(setStyles).catch(() => {});
  }, []);

  const loadReleases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getReleases({
        limit: PAGE_SIZE,
        offset,
        genre:   selectedGenre   || undefined,
        style:   selectedStyle   || undefined,
        label:   selectedLabel   || undefined,
        year:    selectedYear,
        country: selectedCountry || undefined,
        artist:  selectedArtist  || undefined,
        sort,
      });
      setReleases(res.releases);
      setResultCount(toNum(res.count));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load releases');
    } finally {
      setLoading(false);
    }
  }, [offset, selectedGenre, selectedStyle, selectedLabel, selectedYear, selectedCountry, selectedArtist, sort]);

  useEffect(() => {
    loadReleases();
  }, [loadReleases]);

  // ── Filter handlers ───────────────────────────────────────────────────────────

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

  function clearDrillFilter() {
    setSelectedLabel('');
    setSelectedYear(undefined);
    setSelectedCountry('');
    setSelectedArtist('');
    setOffset(0);
  }

  // Called by ReleaseDetail when a chip is clicked; close the modal and filter by that field
  function handleDrill(field: DrillField, value: string) {
    // Reset everything, then set the one drilled field
    setSelectedGenre('');
    setSelectedStyle('');
    setSelectedLabel('');
    setSelectedYear(undefined);
    setSelectedCountry('');
    setSelectedArtist('');
    setOffset(0);
    switch (field) {
      case 'genre':   setSelectedGenre(value);         break;
      case 'style':   setSelectedStyle(value);         break;
      case 'label':   setSelectedLabel(value);         break;
      case 'year':    setSelectedYear(Number(value));  break;
      case 'country': setSelectedCountry(value);       break;
      case 'artist':  setSelectedArtist(value);        break;
    }
  }

  // ── Derived values ────────────────────────────────────────────────────────────

  const hasMore = resultCount >= PAGE_SIZE;
  const hasPrev = offset > 0;
  const pageNum  = Math.floor(offset / PAGE_SIZE) + 1;

  // Non-dropdown active filters (label / year / country / artist)
  const activeDrillChips: { label: string; clear: () => void }[] = [];
  if (selectedArtist)  activeDrillChips.push({ label: `Artist: ${selectedArtist}`,   clear: () => { setSelectedArtist('');  setOffset(0); } });
  if (selectedLabel)   activeDrillChips.push({ label: `Label: ${selectedLabel}`,     clear: () => { setSelectedLabel('');   setOffset(0); } });
  if (selectedYear)    activeDrillChips.push({ label: `Year: ${selectedYear}`,       clear: () => { setSelectedYear(undefined); setOffset(0); } });
  if (selectedCountry) activeDrillChips.push({ label: `Country: ${selectedCountry}`, clear: () => { setSelectedCountry(''); setOffset(0); } });

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

        <div className="filter-group">
          <label htmlFor="sort-select">Sort</label>
          <select
            id="sort-select"
            value={sort}
            onChange={(e) => { setSort(e.target.value as SortOption); setOffset(0); }}
          >
            <option value="artist_year">Artist / Year</option>
            <option value="date_added">Recently Added</option>
            <option value="year">Release Year</option>
            <option value="title">Title</option>
          </select>
        </div>

        {/* Active drill filter chips (label / year / country / artist) */}
        {activeDrillChips.map(({ label, clear }) => (
          <button
            key={label}
            type="button"
            onClick={clear}
            style={{
              background: 'var(--accent)',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '0.82rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            {label} <span style={{ fontWeight: 700 }}>✕</span>
          </button>
        ))}

        {activeDrillChips.length > 1 && (
          <button
            type="button"
            onClick={clearDrillFilter}
            style={{
              background: 'var(--bg-card)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '0.78rem',
              cursor: 'pointer',
            }}
          >
            Clear all
          </button>
        )}

        {!loading && (
          <span className="result-count">
            Page {pageNum}
            {(selectedGenre || selectedStyle || activeDrillChips.length > 0) ? ' (filtered)' : ''}
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
          onDrill={handleDrill}
        />
      )}
    </div>
  );
}

export default BrowseView;
