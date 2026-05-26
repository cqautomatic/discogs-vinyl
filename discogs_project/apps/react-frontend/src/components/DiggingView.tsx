import { useState } from 'react';
import { discoverStyle, discoverExpand, searchDiscogsLists, loadDiscogsList, getStyles } from '../api';
import type { StyleResult, ExpandResult, DiscogsListMeta, DiscogsListDetail, StyleStat } from '../types';
import ExternalLinks from './ExternalLinks';

// ── Status badge ──────────────────────────────────────────────────────────────

const STATUS_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  owned:    { bg: '#1a3a1a', color: '#4caf50', label: 'Owned' },
  wantlist: { bg: '#3a2a00', color: '#ffb300', label: 'Wantlist' },
  gap:      { bg: '#1a2a3a', color: '#64b5f6', label: 'Gap' },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.gap;
  return (
    <span style={{
      background: s.bg, color: s.color,
      border: `1px solid ${s.color}44`,
      borderRadius: '4px', padding: '1px 7px',
      fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.04em',
      textTransform: 'uppercase', whiteSpace: 'nowrap',
    }}>
      {s.label}
    </span>
  );
}

// ── Shared result row ─────────────────────────────────────────────────────────

function ResultRow({
  thumb, title, artist, year, label, status, discogsId,
}: {
  thumb: string | null; title: string; artist?: string; year?: number | null;
  label?: string | null; status: string; discogsId?: number | null;
}) {
  const [imgErr, setImgErr] = useState(false);
  return (
    <div style={{
      display: 'flex', gap: '12px', alignItems: 'center',
      padding: '10px 0', borderBottom: '1px solid var(--border)',
    }}>
      <div style={{
        width: 52, height: 52, flexShrink: 0,
        background: 'var(--bg-card)', borderRadius: '4px', overflow: 'hidden',
      }}>
        {thumb && !imgErr ? (
          <img src={thumb} alt="" width={52} height={52}
            style={{ objectFit: 'cover', display: 'block' }}
            onError={() => setImgErr(true)} />
        ) : (
          <div style={{ width: 52, height: 52, background: 'var(--bg-card)' }} />
        )}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: '0.88rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {title}
        </div>
        {artist && (
          <div style={{ fontSize: '0.8rem', color: 'var(--txt-2)', marginTop: 1 }}>
            {artist}{year ? ` · ${year}` : ''}{label ? ` · ${label}` : ''}
          </div>
        )}
        {!artist && (year || label) && (
          <div style={{ fontSize: '0.8rem', color: 'var(--txt-2)', marginTop: 1 }}>
            {year}{label ? ` · ${label}` : ''}
          </div>
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6, flexShrink: 0 }}>
        <StatusBadge status={status} />
        {status !== 'owned' && (
          <div style={{ fontSize: '0.72rem' }}>
            <ExternalLinks
              title={title}
              artist={artist ?? ''}
              discogs_id={discogsId ?? null}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Tab 1: Style Explorer ─────────────────────────────────────────────────────

function StyleExplorer() {
  const [input, setInput]   = useState('City Pop');
  const [results, setResults] = useState<StyleResult[]>([]);
  const [total, setTotal]   = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function search() {
    if (!input.trim()) return;
    setLoading(true); setError(null); setSearched(true);
    try {
      const res = await discoverStyle({ style: input.trim(), limit: 50 });
      setResults(res.results);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  const gaps     = results.filter((r) => r.status === 'gap');
  const wantlist = results.filter((r) => r.status === 'wantlist');
  const owned    = results.filter((r) => r.status === 'owned');

  return (
    <div>
      <p style={{ fontSize: '0.85rem', color: 'var(--txt-2)', marginBottom: '1rem' }}>
        Search Discogs live by style or genre. Returns the most-collected vinyl you don&apos;t own yet.
      </p>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '1.5rem' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="Style (e.g. City Pop, Boogie, Ambient…)"
          style={{
            flex: 1, background: 'var(--bg-card)', border: '1px solid var(--border)',
            color: 'var(--txt)', borderRadius: '6px', padding: '8px 12px', fontSize: '0.9rem',
          }}
        />
        <button
          onClick={search} disabled={loading || !input.trim()}
          className="btn-primary"
          style={{ padding: '8px 20px', fontSize: '0.88rem' }}
        >
          {loading ? 'Searching…' : 'Search'}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {searched && !loading && results.length > 0 && (
        <>
          <div style={{ display: 'flex', gap: '16px', marginBottom: '1rem', fontSize: '0.83rem', color: 'var(--txt-2)' }}>
            <span>~{total.toLocaleString()} releases on Discogs</span>
            <span style={{ color: '#64b5f6' }}>● {gaps.length} gaps</span>
            <span style={{ color: '#ffb300' }}>● {wantlist.length} on wantlist</span>
            <span style={{ color: '#4caf50' }}>● {owned.length} owned</span>
          </div>

          {gaps.length > 0 && (
            <>
              <h4 style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--txt-2)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>
                Gaps — vinyl you don&apos;t own
              </h4>
              {gaps.map((r) => (
                <ResultRow key={r.id} thumb={r.thumb}
                  title={r.title} year={r.year} label={r.label}
                  status={r.status} discogsId={r.id} />
              ))}
            </>
          )}

          {wantlist.length > 0 && (
            <>
              <h4 style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--txt-2)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: '1rem 0 4px' }}>
                On your wantlist
              </h4>
              {wantlist.map((r) => (
                <ResultRow key={r.id} thumb={r.thumb}
                  title={r.title} year={r.year} label={r.label}
                  status={r.status} discogsId={r.id} />
              ))}
            </>
          )}

          {owned.length > 0 && (
            <>
              <h4 style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--txt-2)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: '1rem 0 4px' }}>
                Already owned
              </h4>
              {owned.map((r) => (
                <ResultRow key={r.id} thumb={r.thumb}
                  title={r.title} year={r.year} label={r.label}
                  status={r.status} discogsId={r.id} />
              ))}
            </>
          )}
        </>
      )}

      {searched && !loading && results.length === 0 && !error && (
        <p className="empty-state">No vinyl results found for &ldquo;{input}&rdquo;.</p>
      )}
    </div>
  );
}

// ── Tab 2: Collection Expander ────────────────────────────────────────────────

function CollectionExpander() {
  const [styles, setStyles]     = useState<StyleStat[]>([]);
  const [selectedStyle, setSelectedStyle] = useState('City Pop');
  const [result, setResult]     = useState<ExpandResult | null>(null);
  const [loading, setLoading]   = useState(false);
  const [loadingStyles, setLoadingStyles] = useState(false);
  const [error, setError]       = useState<string | null>(null);

  // Load user's top styles once
  useState(() => {
    setLoadingStyles(true);
    getStyles()
      .then(setStyles)
      .catch(() => {})
      .finally(() => setLoadingStyles(false));
  });

  async function expand() {
    setLoading(true); setError(null);
    try {
      const res = await discoverExpand(selectedStyle || undefined, 50);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <p style={{ fontSize: '0.85rem', color: 'var(--txt-2)', marginBottom: '1rem' }}>
        Pick a style, see what Discogs has in it — sorted so your favourite labels and artists
        appear first. Every result is guaranteed to be in the same style.
      </p>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {loadingStyles ? (
          <span style={{ color: 'var(--txt-2)', fontSize: '0.85rem' }}>Loading styles…</span>
        ) : (
          <select
            value={selectedStyle}
            onChange={(e) => setSelectedStyle(e.target.value)}
            style={{
              flex: 1, background: 'var(--bg-card)', border: '1px solid var(--border)',
              color: 'var(--txt)', borderRadius: '6px', padding: '8px 12px', fontSize: '0.9rem',
            }}
          >
            {styles.map((s) => (
              <option key={s.style} value={s.style}>
                {s.style} ({Number(s.release_count).toLocaleString()} owned)
              </option>
            ))}
          </select>
        )}
        <button
          onClick={expand} disabled={loading}
          className="btn-primary"
          style={{ padding: '8px 20px', fontSize: '0.88rem' }}
        >
          {loading ? 'Expanding…' : 'Expand'}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {result && !loading && (
        <>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '8px', padding: '14px 16px', marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.83rem', color: 'var(--txt-2)', marginBottom: '8px' }}>
              You own <strong style={{ color: 'var(--txt)' }}>{result.owned_count}</strong> releases tagged <strong style={{ color: 'var(--accent)' }}>{result.style}</strong>
            </div>
            {result.topLabels.length > 0 && (
              <div style={{ fontSize: '0.8rem', marginBottom: '4px' }}>
                <span style={{ color: 'var(--txt-2)' }}>Top labels: </span>
                {result.topLabels.slice(0, 6).join(' · ')}
              </div>
            )}
            {result.topArtists.length > 0 && (
              <div style={{ fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--txt-2)' }}>Top artists: </span>
                {result.topArtists.slice(0, 6).join(' · ')}
              </div>
            )}
          </div>

          {result.results.length > 0 ? (
            <>
              <h4 style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--txt-2)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>
                {result.results.length} {result.style} releases — sorted by your collection DNA
              </h4>
              {result.results.map((r) => (
                <div key={r.discogs_release_id} style={{ position: 'relative' }}>
                  {(r.match === 'top-label' || r.match === 'top-artist') && (
                    <span style={{
                      position: 'absolute', top: 14, right: 0,
                      fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.05em',
                      color: r.match === 'top-label' ? '#ce93d8' : '#80cbc4',
                      textTransform: 'uppercase',
                    }}>
                      {r.match === 'top-label' ? '★ your label' : '♪ your artist'}
                    </span>
                  )}
                  <ResultRow
                    thumb={r.thumb}
                    title={r.title}
                    artist={r.artist}
                    year={r.year}
                    label={r.label}
                    status={r.status}
                    discogsId={r.discogs_release_id}
                  />
                </div>
              ))}
            </>
          ) : (
            <p className="empty-state">No {result.style} results found on Discogs.</p>
          )}
        </>
      )}
    </div>
  );
}

// ── Tab 3: Discogs Lists ──────────────────────────────────────────────────────

// Extract a numeric list ID from a raw input — handles plain IDs and full URLs.
function extractListId(raw: string): number | null {
  const s = raw.trim();
  // Plain integer
  if (/^\d+$/.test(s)) return parseInt(s, 10);
  // Full or partial URL: discogs.com/lists/some-slug/1234567
  const m = s.match(/\/lists\/[A-Za-z0-9_-]+\/(\d+)/);
  if (m) return parseInt(m[1], 10);
  return null;
}

function DiscogsListsTab() {
  const [query, setQuery]       = useState('');
  const [listMetas, setListMetas] = useState<DiscogsListMeta[]>([]);
  const [searchUrl, setSearchUrl] = useState('');
  const [scrapeError, setScrapeError] = useState<string | null>(null);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loadedList, setLoadedList]   = useState<DiscogsListDetail | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [listError, setListError]     = useState<string | null>(null);
  const [activeListId, setActiveListId] = useState<number | null>(null);
  const [filterStatus, setFilterStatus] = useState<'all' | 'gap' | 'wantlist' | 'owned'>('all');

  // If input looks like a list URL/ID, load it directly; otherwise search.
  async function go() {
    if (!query.trim()) return;
    const directId = extractListId(query);
    if (directId !== null) {
      await loadList(directId);
      return;
    }
    // Fallback: search (returns empty + Discogs URL due to Cloudflare)
    setLoadingSearch(true); setScrapeError(null); setListMetas([]); setLoadedList(null);
    try {
      const res = await searchDiscogsLists(query.trim());
      setListMetas(res.lists);
      setSearchUrl(res.discogs_search_url);
      // Always show the fallback link when doing a keyword search
      setScrapeError(
        res.lists.length === 0
          ? 'Discogs list search requires a browser session. Find the list on Discogs, then paste the URL or ID below.'
          : null,
      );
    } catch (e) {
      setScrapeError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoadingSearch(false);
    }
  }

  async function loadList(id: number) {
    setActiveListId(id); setLoadingList(true); setListError(null); setListMetas([]);
    try {
      const res = await loadDiscogsList(id);
      setLoadedList(res);
      setFilterStatus('all');
    } catch (e) {
      setListError(e instanceof Error ? e.message : 'Failed to load list');
    } finally {
      setLoadingList(false);
    }
  }

  const filteredItems = loadedList
    ? loadedList.items.filter((i) => filterStatus === 'all' || i.status === filterStatus)
    : [];

  return (
    <div>
      <p style={{ fontSize: '0.85rem', color: 'var(--txt-2)', marginBottom: '1rem' }}>
        Load any Discogs community list and instantly see what you own, what&apos;s on your wantlist, and what&apos;s a gap.
        Paste a list URL like <code style={{ fontSize: '0.8rem', color: 'var(--accent)' }}>discogs.com/lists/City-Pop/123456</code> or
        just the numeric ID — or search on Discogs and paste from there.
      </p>

      {/* Input bar */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '0.75rem' }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && go()}
          placeholder="Paste a list URL or ID (e.g. 123456)"
          style={{
            flex: 1, background: 'var(--bg-card)', border: '1px solid var(--border)',
            color: 'var(--txt)', borderRadius: '6px', padding: '8px 12px', fontSize: '0.9rem',
          }}
        />
        <button
          onClick={go} disabled={loadingSearch || loadingList || !query.trim()}
          className="btn-primary"
          style={{ padding: '8px 20px', fontSize: '0.88rem' }}
        >
          {loadingSearch || loadingList ? 'Loading…' : 'Load'}
        </button>
      </div>

      {/* Always-visible link to search Discogs */}
      <div style={{ fontSize: '0.8rem', color: 'var(--txt-2)', marginBottom: '1.5rem' }}>
        Don&apos;t have a URL?{' '}
        <a
          href={`https://www.discogs.com/search/?type=list${query && !extractListId(query) ? `&q=${encodeURIComponent(query)}` : ''}`}
          target="_blank" rel="noopener noreferrer"
          style={{ color: 'var(--accent)' }}
        >
          Search Discogs lists ↗
        </a>
        {' '}— find a list, then copy &amp; paste its URL here.
      </div>

      {/* Error / feedback */}
      {(scrapeError || listError) && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '8px', padding: '12px 16px', marginBottom: '1rem', fontSize: '0.85rem', color: 'var(--txt-2)' }}>
          {scrapeError ?? listError}
          {searchUrl && (
            <>
              {' '}
              <a href={searchUrl} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent)' }}>
                Open search on Discogs ↗
              </a>
            </>
          )}
        </div>
      )}

      {/* List search results — only shown if scraping actually returns hits */}
      {listMetas.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h4 style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--txt-2)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {listMetas.length} lists found for &ldquo;{query}&rdquo;
            </h4>
            {searchUrl && (
              <a href={searchUrl} target="_blank" rel="noopener noreferrer"
                style={{ fontSize: '0.78rem', color: 'var(--accent)' }}>
                See all on Discogs ↗
              </a>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {listMetas.map((list) => (
              <div key={list.id} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                background: activeListId === list.id ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                border: `1px solid ${activeListId === list.id ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: '6px', padding: '10px 14px',
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.87rem' }}>{list.name}</div>
                  <a href={list.url} target="_blank" rel="noopener noreferrer"
                    style={{ fontSize: '0.75rem', color: 'var(--txt-2)' }}>
                    discogs.com/lists/…/{list.id} ↗
                  </a>
                </div>
                <button
                  onClick={() => loadList(list.id)}
                  disabled={loadingList && activeListId === list.id}
                  style={{
                    background: activeListId === list.id ? 'var(--accent)' : 'var(--bg-card-hover)',
                    color: activeListId === list.id ? '#fff' : 'var(--accent)',
                    border: '1px solid var(--accent)',
                    borderRadius: '5px', padding: '5px 14px',
                    fontSize: '0.82rem', cursor: 'pointer', flexShrink: 0,
                  }}
                >
                  {loadingList && activeListId === list.id ? 'Loading…' : 'Load List'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {listError && <div className="error-banner">{listError}</div>}

      {/* Loaded list detail */}
      {loadedList && !loadingList && (
        <div>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '8px', padding: '14px 16px', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '6px' }}>{loadedList.name}</h3>
            {loadedList.description && (
              <p style={{ fontSize: '0.82rem', color: 'var(--txt-2)', marginBottom: '8px' }}>{loadedList.description}</p>
            )}
            <div style={{ display: 'flex', gap: '16px', fontSize: '0.82rem' }}>
              <span style={{ color: '#64b5f6' }}>● {loadedList.gaps} gaps</span>
              <span style={{ color: '#ffb300' }}>● {loadedList.wanted} wantlist</span>
              <span style={{ color: '#4caf50' }}>● {loadedList.owned} owned</span>
              <span style={{ color: 'var(--txt-2)' }}>/ {loadedList.item_count} total</span>
            </div>
          </div>

          {/* Filter tabs */}
          <div style={{ display: 'flex', gap: '6px', marginBottom: '1rem' }}>
            {(['all', 'gap', 'wantlist', 'owned'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilterStatus(f)}
                style={{
                  background: filterStatus === f ? 'var(--accent)' : 'var(--bg-card)',
                  color: filterStatus === f ? '#fff' : 'var(--txt-2)',
                  border: '1px solid var(--border)',
                  borderRadius: '5px', padding: '4px 12px',
                  fontSize: '0.8rem', cursor: 'pointer',
                }}
              >
                {f === 'all' ? `All (${loadedList.item_count})` :
                 f === 'gap' ? `Gaps (${loadedList.gaps})` :
                 f === 'wantlist' ? `Wantlist (${loadedList.wanted})` :
                 `Owned (${loadedList.owned})`}
              </button>
            ))}
          </div>

          {filteredItems.map((item) => (
            <ResultRow
              key={item.id}
              thumb={item.thumb}
              title={item.title}
              status={item.status}
              discogsId={item.type === 'release' ? item.id : null}
            />
          ))}

          {filteredItems.length === 0 && (
            <p className="empty-state">No items match this filter.</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main DiggingView ──────────────────────────────────────────────────────────

type DiggingTab = 'style' | 'expand' | 'lists';

const TABS: { id: DiggingTab; label: string; description: string }[] = [
  { id: 'style',  label: '🔍 Style Search',       description: 'Search Discogs live by style/genre' },
  { id: 'expand', label: '🧬 Collection Expander', description: 'Expand from your DNA (instant)' },
  { id: 'lists',  label: '📋 Discogs Lists',       description: 'Find & cross-reference curated lists' },
];

function DiggingView() {
  const [activeTab, setActiveTab] = useState<DiggingTab>('style');

  return (
    <div className="digging-view">
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 className="section-title">Dig</h2>
        <p style={{ fontSize: '0.83rem', color: 'var(--txt-2)', marginTop: '4px' }}>
          Find what you&apos;re missing — by style, by collection DNA, or from community lists.
        </p>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: '6px', marginBottom: '2rem', flexWrap: 'wrap' }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            title={tab.description}
            style={{
              background: activeTab === tab.id ? 'var(--accent)' : 'var(--bg-card)',
              color: activeTab === tab.id ? '#fff' : 'var(--txt)',
              border: `1px solid ${activeTab === tab.id ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: '7px', padding: '8px 18px',
              fontSize: '0.87rem', fontWeight: activeTab === tab.id ? 700 : 400,
              cursor: 'pointer', transition: 'all 0.12s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'style'  && <StyleExplorer />}
      {activeTab === 'expand' && <CollectionExpander />}
      {activeTab === 'lists'  && <DiscogsListsTab />}
    </div>
  );
}

export default DiggingView;
