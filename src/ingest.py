from __future__ import annotations

import argparse
import time

from .api import BaniClient
from .config import AK_SOURCE_CODE, get_settings
from .normalize import normalize_page
from .db import db_cursor
from .store import last_page, last_status, mark_ingest, save_page


def ingest_angs(source_code: str, start_page: int | None = None) -> None:
    settings = get_settings()
    client = BaniClient(settings)
    if last_status(source_code) == "complete" and start_page is None:
        print(f"{source_code}: already complete")
        return
    if start_page is not None:
        page_no = start_page
        print(f"{source_code}: starting at page {page_no}")
    elif last_status(source_code) == "error":
        page_no = max(last_page(source_code), 1)
        print(f"{source_code}: retrying after error at page {page_no}")
    else:
        page_no = last_page(source_code) + 1
        if page_no < 1:
            page_no = 1
        print(f"{source_code}: starting at page {page_no}")
    while True:
        try:
            payload = client.fetch_page(source_code, page_no)
            page = normalize_page(payload, source_code, page_no=page_no)
            save_page(page)
            next_page = page.get("next_page")
            if next_page is None:
                mark_ingest(source_code, page_no, "complete")
                print(f"{source_code}: finished at page {page_no} ({page['verse_count']} verses)")
                return
            mark_ingest(source_code, page_no, "in_progress")
            print(f"{source_code}: page {page_no} ({page['verse_count']} verses) -> {next_page}")
            page_no = next_page
        except Exception as exc:
            mark_ingest(source_code, page_no, "error", str(exc))
            raise
        time.sleep(settings.request_delay_seconds)


def _ak_coverage() -> tuple[int, int]:
    with db_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS n FROM amrit_keertan_headers")
        headers = int(cursor.fetchone()["n"])
        cursor.execute(
            "SELECT COUNT(*) AS n FROM pages WHERE source_code = %s",
            (AK_SOURCE_CODE,),
        )
        pages = int(cursor.fetchone()["n"])
    return headers, pages


def ingest_amrit_keertan(start_page: int | None = None, force: bool = False) -> None:
    settings = get_settings()
    client = BaniClient(settings)
    max_index = settings.amrit_keertan_max_index
    headers, pages = _ak_coverage()
    incomplete = headers < max_index or pages < max_index
    if force or incomplete:
        page_no = start_page if start_page is not None else 1
        print(
            f"{AK_SOURCE_CODE}: recrawling from index {page_no} "
            f"(headers={headers}, pages={pages}, expected={max_index})"
        )
    else:
        page_no = start_page if start_page is not None else last_page(AK_SOURCE_CODE) + 1
        if page_no < 1:
            page_no = 1
        if last_status(AK_SOURCE_CODE) == "complete" and start_page is None:
            print(f"{AK_SOURCE_CODE}: already complete")
            return
        if page_no > max_index:
            mark_ingest(AK_SOURCE_CODE, max_index, "complete")
            print(f"{AK_SOURCE_CODE}: already complete through {max_index}")
            return
        print(f"{AK_SOURCE_CODE}: starting at index {page_no} (max {max_index})")
    while page_no <= max_index:
        try:
            payload = client.fetch_page(AK_SOURCE_CODE, page_no)
            page = normalize_page(
                payload,
                AK_SOURCE_CODE,
                page_no=page_no,
                max_index=max_index,
                offset=settings.ak_verse_id_offset,
            )
            save_page(page)
            if page_no >= max_index:
                mark_ingest(AK_SOURCE_CODE, page_no, "complete")
                print(
                    f"{AK_SOURCE_CODE}: finished at index {page_no} "
                    f"({page['verse_count']} lines, {len(page.get('headers') or [])} headers)"
                )
                return
            mark_ingest(AK_SOURCE_CODE, page_no, "in_progress")
            print(
                f"{AK_SOURCE_CODE}: index {page_no} "
                f"({page['verse_count']} lines) -> {page_no + 1}"
            )
            page_no += 1
        except Exception as exc:
            mark_ingest(AK_SOURCE_CODE, page_no, "error", str(exc))
            raise
        time.sleep(settings.request_delay_seconds)


def ingest_source(source_code: str, start_page: int | None = None, force: bool = False) -> None:
    if source_code == AK_SOURCE_CODE:
        ingest_amrit_keertan(start_page, force=force)
        return
    ingest_angs(source_code, start_page)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest BaniDB pages into MySQL")
    parser.add_argument("--source", default="all", help="G, D, B, S, A, or all")
    parser.add_argument("--start-page", type=int, default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recrawl from --start-page (or 1) even if ingest_state says complete",
    )
    args = parser.parse_args()
    settings = get_settings()
    sources = settings.ingest_sources if args.source.lower() == "all" else [args.source.upper()]
    for source_code in sources:
        ingest_source(source_code, args.start_page, force=args.force)


if __name__ == "__main__":
    main()
