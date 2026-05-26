import type { Release } from '../types';
import { getArtworkUrl } from '../api';

interface Props {
  release: Release;
  onClick: () => void;
}

function getImageUrl(release: Release): string | null {
  if (release.artwork_files.length > 0) {
    const primary = release.artwork_files.find((a) => a.image_type === 'primary');
    const art = primary ?? release.artwork_files[0];
    return getArtworkUrl(art.thumbnail_file_path) ?? art.original_url ?? null;
  }
  return null;
}

function ReleaseCard({ release, onClick }: Props) {
  const imageUrl = getImageUrl(release);
  const genreLabel = release.genres?.slice(0, 2).join(', ') ?? '';

  return (
    <button className="release-card" onClick={onClick} type="button">
      <div className="release-card-art">
        {imageUrl ? (
          <img src={imageUrl} alt={`${release.title} cover art`} loading="lazy" />
        ) : (
          <div className="art-placeholder" aria-hidden="true" />
        )}
      </div>
      <div className="release-card-info">
        <p className="release-title">{release.title}</p>
        <p className="release-artist">{release.artist}</p>
        <p className="release-meta">
          {release.year ?? '—'}
          {genreLabel ? ` · ${genreLabel}` : ''}
        </p>
      </div>
    </button>
  );
}

export default ReleaseCard;
