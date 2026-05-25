interface Props {
  title: string;
  artist: string;
  discogs_id?: number | null;
}

function ExternalLinks({ title, artist, discogs_id }: Props) {
  const q = encodeURIComponent(`${artist} ${title}`);

  const links = [
    ...(discogs_id ? [{ label: 'Discogs', href: `https://www.discogs.com/sell/release/${discogs_id}` }] : []),
    { label: 'Disk Union', href: `https://diskunion.net/search/?q=${q}` },
    { label: 'Recofan', href: `https://www.recofan.co.jp/search/?k=${q}` },
    { label: 'Juno', href: `https://www.juno.co.uk/search/?solrOrder=relevancy&q=${q}` },
    { label: 'Clone', href: `https://clone.nl/search?q=${q}` },
  ];

  return (
    <div className="external-links">
      {links.map((l) => (
        <a key={l.label} href={l.href} target="_blank" rel="noopener noreferrer" className="ext-link">
          {l.label} ↗
        </a>
      ))}
    </div>
  );
}

export default ExternalLinks;
