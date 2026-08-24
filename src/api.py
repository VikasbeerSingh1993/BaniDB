from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import AK_SOURCE_CODE, Settings


class BaniClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        retry = Retry(
            total=settings.max_retries,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "BaniDB-search-ingest/1.0",
            }
        )

    def fetch_url(self, source_code: str, page_no: int) -> str:
        if source_code == AK_SOURCE_CODE:
            return f"{self.settings.banidb_amrit_keertan_url}/{page_no}"
        return f"{self.settings.banidb_base_url}/{page_no}/{source_code}"

    def fetch_page(self, source_code: str, page_no: int) -> dict[str, Any]:
        url = self.fetch_url(source_code, page_no)
        response = self.session.get(url, timeout=self.settings.request_timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"Unexpected payload for {url}")
        return payload
