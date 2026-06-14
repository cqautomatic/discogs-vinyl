"""Shared Discogs API client with rate limiting and retry logic.

Usage:
    from lib.discogs_api import DiscogsClient

    client = DiscogsClient()  # reads DISCOGS_TOKEN from env
    data = client.get("/users/me/collection/folders/0/releases", per_page=100)
    data = client.get("/releases/12345")
"""

import os
import time
import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.discogs.com"
DEFAULT_USER_AGENT = "DiscogsCollectionApp/1.0"
DEFAULT_RATE_DELAY = 1.0  # seconds between calls
RATE_LIMIT_BACKOFF = 60   # seconds to wait on 429


class DiscogsClient:
    """Thin HTTP client for the Discogs API.

    Handles auth headers, per-call rate limiting, and 429 retry.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        rate_delay: float = DEFAULT_RATE_DELAY,
        timeout: int = 20,
    ):
        self.token = token or os.environ.get("DISCOGS_TOKEN", "")
        self.rate_delay = rate_delay
        self.timeout = timeout
        self._last_request_time = 0.0
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Discogs token={self.token}",
            "User-Agent": user_agent,
        })

    # ── Core request methods ──────────────────────────────────────────

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_delay:
            time.sleep(self.rate_delay - elapsed)

    def get(self, path: str, **params: Any) -> Optional[Dict]:
        """GET a Discogs API endpoint. Returns parsed JSON or None on error.

        Args:
            path: API path (e.g. "/releases/12345") or full URL.
            **params: Query parameters.
        """
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        return self._request("GET", url, params=params)

    def put(self, path: str, **params: Any) -> Optional[Dict]:
        """PUT to a Discogs API endpoint."""
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        return self._request("PUT", url, params=params)

    def _request(
        self, method: str, url: str, params: Optional[Dict] = None
    ) -> Optional[Dict]:
        self._wait_for_rate_limit()
        self._last_request_time = time.time()

        try:
            resp = self._session.request(
                method, url, params=params, timeout=self.timeout
            )

            if resp.status_code == 200 or resp.status_code == 201:
                return resp.json()

            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", RATE_LIMIT_BACKOFF))
                logger.warning("Rate limited, waiting %ds...", wait)
                time.sleep(wait)
                return self._request(method, url, params=params)

            if resp.status_code == 404:
                logger.debug("Not found: %s", url)
                return None

            logger.error("Discogs API %s %d: %s", url, resp.status_code, resp.text[:200])
            return None

        except requests.exceptions.RequestException as exc:
            logger.error("Request failed: %s — %s", url, exc)
            return None

    # ── Convenience wrappers ──────────────────────────────────────────

    def identity(self) -> Optional[Dict]:
        """Get the authenticated user's identity."""
        return self.get("/oauth/identity")

    def collection_page(
        self, username: str, page: int = 1, per_page: int = 100,
        sort: str = "added", sort_order: str = "desc",
    ) -> Optional[Dict]:
        """Get one page of a user's collection."""
        return self.get(
            f"/users/{username}/collection/folders/0/releases",
            page=page, per_page=per_page, sort=sort, sort_order=sort_order,
        )

    def release(self, release_id: int) -> Optional[Dict]:
        """Get detailed release info."""
        return self.get(f"/releases/{release_id}")

    def master(self, master_id: int) -> Optional[Dict]:
        """Get master release info."""
        return self.get(f"/masters/{master_id}")

    def artist(self, artist_id: int) -> Optional[Dict]:
        """Get artist details."""
        return self.get(f"/artists/{artist_id}")

    def label(self, label_id: int) -> Optional[Dict]:
        """Get label details."""
        return self.get(f"/labels/{label_id}")

    def marketplace_stats(self, release_id: int) -> Optional[Dict]:
        """Get marketplace stats (num_for_sale, lowest_price)."""
        return self.get(f"/marketplace/stats/{release_id}")

    def search(self, **params: Any) -> list:
        """Search the Discogs database. Returns the results list."""
        data = self.get("/database/search", **params)
        return data.get("results", []) if data else []

    def wantlist_page(
        self, username: str, page: int = 1, per_page: int = 100
    ) -> Optional[Dict]:
        """Get one page of a user's wantlist."""
        return self.get(
            f"/users/{username}/wants", page=page, per_page=per_page
        )

    def wantlist_add(self, username: str, release_id: int) -> Optional[Dict]:
        """Add a release to the user's wantlist."""
        return self.put(f"/users/{username}/wants/{release_id}")
