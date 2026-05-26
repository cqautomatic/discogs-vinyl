interface Props {
  title: string;
  artist: string;
  discogs_id?: number | null;
}

function ExternalLinks({ title, artist, discogs_id }: Props) {
  // Combined query (artist + title) for sites that take a single search box
  const q       = encodeURIComponent(`${artist} ${title}`);
  const qArtist = encodeURIComponent(artist);
  const qTitle  = encodeURIComponent(title);

  const links = [
    // Marketplace / pricing
    ...(discogs_id ? [{ label: 'Discogs', href: `https://www.discogs.com/sell/release/${discogs_id}` }] : []),

    // Japanese stores — Disk Union: maniac search form pre-filled with artist + title
    {
      label: 'Disk Union',
      href: `https://diskunion.net/portal/ct/maniac_search?artist=${qArtist}&title=${qTitle}`,
    },
    // HMV Japan English vinyl search
    {
      label: 'HMV Japan',
      href: `https://www.hmv.co.jp/en/select/vinyl/list/?itemtype=0&keyword=${q}`,
    },
    // Mercari Japan — largest used-record marketplace in Japan (replaced Recofan which has no online shop)
    {
      label: 'Mercari JP',
      href: `https://jp.mercari.com/search?keyword=${q}`,
    },

    // Western stores
    { label: 'Juno',  href: `https://www.juno.co.uk/search/?solrOrder=relevancy&q=${q}` },
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
