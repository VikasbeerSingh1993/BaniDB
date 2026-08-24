from __future__ import annotations

import time
from datetime import datetime, timezone

import mysql.connector

from .db import db_cursor
from .normalize import search_blob


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def last_page(source_code: str) -> int:
    with db_cursor() as cursor:
        cursor.execute(
            "SELECT last_page FROM ingest_state WHERE source_code = %s",
            (source_code,),
        )
        row = cursor.fetchone()
    return int(row["last_page"]) if row else 0


def last_status(source_code: str) -> str | None:
    with db_cursor() as cursor:
        cursor.execute(
            "SELECT last_status FROM ingest_state WHERE source_code = %s",
            (source_code,),
        )
        row = cursor.fetchone()
    return row["last_status"] if row else None


def mark_ingest(
    source_code: str,
    page_no: int,
    status: str,
    error: str | None = None,
) -> None:
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO ingest_state (source_code, last_page, last_status, last_error, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              last_page = VALUES(last_page),
              last_status = VALUES(last_status),
              last_error = VALUES(last_error),
              updated_at = VALUES(updated_at)
            """,
            (source_code, page_no, status, error, _now()),
        )


def _upsert_source(cursor, source: dict) -> None:
    cursor.execute(
        """
        INSERT INTO sources (code, english, gurmukhi, unicode)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          english = COALESCE(VALUES(english), english),
          gurmukhi = COALESCE(VALUES(gurmukhi), gurmukhi),
          unicode = COALESCE(VALUES(unicode), unicode)
        """,
        (source["code"], source.get("english"), source.get("gurmukhi"), source.get("unicode")),
    )


def _upsert_writer(cursor, writer: dict | None) -> int | None:
    if not writer:
        return None
    cursor.execute(
        """
        INSERT INTO writers (writer_id, english, gurmukhi, unicode)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          english = COALESCE(VALUES(english), english),
          gurmukhi = COALESCE(VALUES(gurmukhi), gurmukhi),
          unicode = COALESCE(VALUES(unicode), unicode)
        """,
        (
            writer["writer_id"],
            writer.get("english"),
            writer.get("gurmukhi"),
            writer.get("unicode"),
        ),
    )
    return writer["writer_id"]


def _upsert_raag(cursor, raag: dict | None) -> int | None:
    if not raag:
        return None
    cursor.execute(
        """
        INSERT INTO raags (raag_id, english, gurmukhi, unicode, raag_with_page)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          english = COALESCE(VALUES(english), english),
          gurmukhi = COALESCE(VALUES(gurmukhi), gurmukhi),
          unicode = COALESCE(VALUES(unicode), unicode),
          raag_with_page = COALESCE(VALUES(raag_with_page), raag_with_page)
        """,
        (
            raag["raag_id"],
            raag.get("english"),
            raag.get("gurmukhi"),
            raag.get("unicode"),
            raag.get("raag_with_page"),
        ),
    )
    return raag["raag_id"]


def _save_header(cursor, header: dict) -> None:
    cursor.execute(
        """
        INSERT INTO amrit_keertan_headers (header_id, gurmukhi, unicode, updated_at)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          gurmukhi = VALUES(gurmukhi),
          unicode = VALUES(unicode),
          updated_at = VALUES(updated_at)
        """,
        (
            header["header_id"],
            header.get("gurmukhi"),
            header.get("unicode"),
            header.get("updated_at"),
        ),
    )
    cursor.execute(
        "DELETE FROM amrit_keertan_header_translations WHERE header_id = %s",
        (header["header_id"],),
    )
    for row in header.get("translations") or []:
        cursor.execute(
            """
            INSERT INTO amrit_keertan_header_translations
              (header_id, language, translator_code, gurmukhi, unicode, text)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                header["header_id"],
                row["language"],
                row["translator_code"],
                row.get("gurmukhi"),
                row.get("unicode"),
                row.get("text"),
            ),
        )
    cursor.execute(
        "DELETE FROM amrit_keertan_header_transliterations WHERE header_id = %s",
        (header["header_id"],),
    )
    for row in header.get("transliterations") or []:
        cursor.execute(
            """
            INSERT INTO amrit_keertan_header_transliterations (header_id, script, text)
            VALUES (%s, %s, %s)
            """,
            (header["header_id"], row["script"], row.get("text")),
        )


def _save_verse(cursor, verse: dict) -> None:
    writer_id = _upsert_writer(cursor, verse.get("writer"))
    raag_id = _upsert_raag(cursor, verse.get("raag"))
    writer = verse.get("writer") or {}
    raag = verse.get("raag") or {}
    cursor.execute(
        """
        INSERT INTO verses (
          verse_id, source_code, shabad_id, page_no, line_no,
          gurmukhi, unicode, larivaar_gurmukhi, larivaar_unicode,
          writer_id, raag_id, updated_at, visraam_json,
          index_id, header_id, ang, source_page_no,
          original_source_id, original_source_english,
          original_source_gurmukhi, original_source_unicode
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          source_code = VALUES(source_code),
          shabad_id = VALUES(shabad_id),
          page_no = VALUES(page_no),
          line_no = VALUES(line_no),
          gurmukhi = VALUES(gurmukhi),
          unicode = VALUES(unicode),
          larivaar_gurmukhi = VALUES(larivaar_gurmukhi),
          larivaar_unicode = VALUES(larivaar_unicode),
          writer_id = VALUES(writer_id),
          raag_id = VALUES(raag_id),
          updated_at = VALUES(updated_at),
          visraam_json = VALUES(visraam_json),
          index_id = VALUES(index_id),
          header_id = VALUES(header_id),
          ang = VALUES(ang),
          source_page_no = VALUES(source_page_no),
          original_source_id = VALUES(original_source_id),
          original_source_english = VALUES(original_source_english),
          original_source_gurmukhi = VALUES(original_source_gurmukhi),
          original_source_unicode = VALUES(original_source_unicode)
        """,
        (
            verse["verse_id"],
            verse["source_code"],
            verse.get("shabad_id"),
            verse["page_no"],
            verse.get("line_no"),
            verse.get("gurmukhi") or "",
            verse.get("unicode") or "",
            verse.get("larivaar_gurmukhi"),
            verse.get("larivaar_unicode"),
            writer_id,
            raag_id,
            verse.get("updated_at"),
            verse.get("visraam_json"),
            verse.get("index_id"),
            verse.get("header_id"),
            verse.get("ang"),
            verse.get("source_page_no"),
            verse.get("original_source_id"),
            verse.get("original_source_english"),
            verse.get("original_source_gurmukhi"),
            verse.get("original_source_unicode"),
        ),
    )
    cursor.execute("DELETE FROM verse_translations WHERE verse_id = %s", (verse["verse_id"],))
    for row in verse.get("translations") or []:
        cursor.execute(
            """
            INSERT INTO verse_translations (verse_id, language, translator_code, gurmukhi, unicode, text)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                verse["verse_id"],
                row["language"],
                row["translator_code"],
                row.get("gurmukhi"),
                row.get("unicode"),
                row.get("text"),
            ),
        )
    cursor.execute("DELETE FROM verse_transliterations WHERE verse_id = %s", (verse["verse_id"],))
    for row in verse.get("transliterations") or []:
        cursor.execute(
            """
            INSERT INTO verse_transliterations (verse_id, script, text)
            VALUES (%s, %s, %s)
            """,
            (verse["verse_id"], row["script"], row.get("text")),
        )
    cursor.execute(
        """
        INSERT INTO search_documents (
          verse_id, source_code, shabad_id, page_no, line_no,
          writer_english, raag_english, gurmukhi, unicode, larivaar_unicode,
          english_ms, english_bdb, english_ssk, punjabi_ss, hindi_ss,
          translit_english, search_blob,
          index_id, header_id, ang, original_source_id, header_unicode,
          punjabi_ft, punjabi_bdb, spanish_sn, hindi_sts,
          translit_hindi, translit_ipa, translit_urdu
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
          source_code = VALUES(source_code),
          shabad_id = VALUES(shabad_id),
          page_no = VALUES(page_no),
          line_no = VALUES(line_no),
          writer_english = VALUES(writer_english),
          raag_english = VALUES(raag_english),
          gurmukhi = VALUES(gurmukhi),
          unicode = VALUES(unicode),
          larivaar_unicode = VALUES(larivaar_unicode),
          english_ms = VALUES(english_ms),
          english_bdb = VALUES(english_bdb),
          english_ssk = VALUES(english_ssk),
          punjabi_ss = VALUES(punjabi_ss),
          hindi_ss = VALUES(hindi_ss),
          translit_english = VALUES(translit_english),
          search_blob = VALUES(search_blob),
          index_id = VALUES(index_id),
          header_id = VALUES(header_id),
          ang = VALUES(ang),
          original_source_id = VALUES(original_source_id),
          header_unicode = VALUES(header_unicode),
          punjabi_ft = VALUES(punjabi_ft),
          punjabi_bdb = VALUES(punjabi_bdb),
          spanish_sn = VALUES(spanish_sn),
          hindi_sts = VALUES(hindi_sts),
          translit_hindi = VALUES(translit_hindi),
          translit_ipa = VALUES(translit_ipa),
          translit_urdu = VALUES(translit_urdu)
        """,
        (
            verse["verse_id"],
            verse["source_code"],
            verse.get("shabad_id"),
            verse["page_no"],
            verse.get("line_no"),
            writer.get("english"),
            raag.get("english"),
            verse.get("gurmukhi") or "",
            verse.get("unicode") or "",
            verse.get("larivaar_unicode"),
            verse.get("english_ms"),
            verse.get("english_bdb"),
            verse.get("english_ssk"),
            verse.get("punjabi_ss"),
            verse.get("hindi_ss"),
            verse.get("translit_english"),
            search_blob(verse),
            verse.get("index_id"),
            verse.get("header_id"),
            verse.get("ang"),
            verse.get("original_source_id"),
            verse.get("header_unicode"),
            verse.get("punjabi_ft"),
            verse.get("punjabi_bdb"),
            verse.get("spanish_sn"),
            verse.get("hindi_sts"),
            verse.get("translit_hindi"),
            verse.get("translit_ipa"),
            verse.get("translit_urdu"),
        ),
    )


def save_page(page: dict, attempts: int = 6) -> None:
    delay = 0.25
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            _save_page_once(page)
            return
        except mysql.connector.Error as exc:
            last_error = exc
            if getattr(exc, "errno", None) not in (1213, 3) or attempt == attempts - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 4.0)
    if last_error:
        raise last_error


def _save_page_once(page: dict) -> None:
    with db_cursor(commit=True) as cursor:
        _upsert_source(cursor, page["source"])
        cursor.execute(
            """
            INSERT INTO pages (source_code, page_no, verse_count, previous_page, next_page, fetched_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              verse_count = VALUES(verse_count),
              previous_page = VALUES(previous_page),
              next_page = VALUES(next_page),
              fetched_at = VALUES(fetched_at)
            """,
            (
                page["source"]["code"],
                page["page_no"],
                page["verse_count"],
                page.get("previous_page"),
                page.get("next_page"),
                _now(),
            ),
        )
        for header in page.get("headers") or []:
            _save_header(cursor, header)
        for verse in page["verses"]:
            if verse.get("verse_id") is None:
                continue
            _save_verse(cursor, verse)
