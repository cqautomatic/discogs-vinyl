const DISCOGS_TOKEN = process.env.DISCOGS_TOKEN ?? '';
const DISCOGS_HEADERS: Record<string, string> = {
  Authorization: `Discogs token=${DISCOGS_TOKEN}`,
  'User-Agent':  'DiscogsCollectionApp/1.0',
};

export async function discogsGet(url: string): Promise<unknown> {
  const res = await fetch(url, { headers: DISCOGS_HEADERS });
  if (!res.ok) throw new Error(`Discogs API ${res.status} — ${url}`);
  return res.json();
}

export async function discogsPut(url: string): Promise<unknown> {
  const res = await fetch(url, { method: 'PUT', headers: DISCOGS_HEADERS });
  if (!res.ok) throw new Error(`Discogs API ${res.status} — ${url}`);
  return res.json();
}

export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
