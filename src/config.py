from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

AK_SOURCE_CODE = "A"
AK_VERSE_ID_OFFSET = 2_000_000_000
AK_MAX_INDEX_DEFAULT = 113


def _api_root(angs_url: str) -> str:
    explicit = os.getenv("BANIDB_API_ROOT", "").strip().rstrip("/")
    if explicit:
        return explicit
    base = angs_url.rstrip("/")
    if base.endswith("/angs"):
        return base[: -len("/angs")]
    return base.rsplit("/", 1)[0] if "/" in base else base


@dataclass(frozen=True)
class Settings:
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str
    banidb_base_url: str
    banidb_api_root: str
    banidb_amrit_keertan_url: str
    request_timeout_seconds: int
    request_delay_seconds: float
    max_retries: int
    ingest_sources: tuple[str, ...]
    amrit_keertan_max_index: int
    ak_verse_id_offset: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    sources = tuple(
        code.strip().upper()
        for code in os.getenv("INGEST_SOURCES", "G,D,B,S,A").split(",")
        if code.strip()
    )
    angs_url = os.getenv("BANIDB_BASE_URL", "https://api.banidb.com/v2/angs").rstrip("/")
    api_root = _api_root(angs_url)
    ak_url = os.getenv(
        "BANIDB_AMRIT_KEERTAN_URL",
        f"{api_root}/amritkeertan/index",
    ).rstrip("/")
    return Settings(
        mysql_host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
        mysql_user=os.getenv("MYSQL_USER", "banidb"),
        mysql_password=os.getenv("MYSQL_PASSWORD", "banidb"),
        mysql_database=os.getenv("MYSQL_DATABASE", "bani_search"),
        banidb_base_url=angs_url,
        banidb_api_root=api_root,
        banidb_amrit_keertan_url=ak_url,
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        request_delay_seconds=float(os.getenv("REQUEST_DELAY_SECONDS", "0.25")),
        max_retries=int(os.getenv("MAX_RETRIES", "5")),
        ingest_sources=sources or ("G", "D", "B", "S", "A"),
        amrit_keertan_max_index=int(os.getenv("AMRIT_KEERTAN_MAX_INDEX", str(AK_MAX_INDEX_DEFAULT))),
        ak_verse_id_offset=int(os.getenv("AK_VERSE_ID_OFFSET", str(AK_VERSE_ID_OFFSET))),
    )
