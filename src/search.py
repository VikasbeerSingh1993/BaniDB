from __future__ import annotations

import argparse
import json

from .db import db_cursor


def search_text(query: str, limit: int = 20) -> list[dict]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
              verse_id, source_code, shabad_id, page_no, line_no,
              writer_english, raag_english, unicode, english_bdb, english_ms,
              index_id, header_id, ang, original_source_id,
              MATCH(search_blob) AGAINST (%s IN NATURAL LANGUAGE MODE) AS score
            FROM search_documents
            WHERE MATCH(search_blob) AGAINST (%s IN NATURAL LANGUAGE MODE)
            ORDER BY score DESC
            LIMIT %s
            """,
            (query, query, limit),
        )
        return list(cursor.fetchall())


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the local Bani corpus")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(search_text(args.query, args.limit), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
