from __future__ import annotations

import json
from typing import Any

from .config import AK_SOURCE_CODE, AK_VERSE_ID_OFFSET

TEXT_KEYS = ("gurmukhi", "Gurmukhi", "unicode", "GurmukhiUni", "Unicode", "text", "Text")


def pick(data: Any, *keys: str, default=None):
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def pick_any(data: Any, *names: str, default=None):
    if not isinstance(data, dict):
        return default
    for name in names:
        if name in data and data[name] not in (None, ""):
            return data[name]
        lower = {str(key).lower(): key for key in data}
        matched = lower.get(name.lower())
        if matched is not None and data[matched] not in (None, ""):
            return data[matched]
    return default


def nested_text(data: Any, *keys: str) -> str | None:
    value = pick(data, *keys)
    if value is None:
        value = data
        for key in keys:
            value = pick_any(value, key)
            if value is None:
                return None
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        return (
            pick_any(value, "unicode", "GurmukhiUni", "text", "Text", "gurmukhi", "Gurmukhi")
        )
    return str(value) if value not in (None, "") else None


def as_json(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            json.loads(value)
            return value
        except json.JSONDecodeError:
            return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def _payload_texts(payload: Any) -> tuple[str | None, str | None, str | None]:
    if payload in (None, ""):
        return None, None, None
    if isinstance(payload, str):
        return None, None, payload
    if isinstance(payload, dict):
        gurmukhi = pick_any(payload, "gurmukhi", "Gurmukhi")
        unicode_text = pick_any(payload, "unicode", "GurmukhiUni", "Unicode")
        text = pick_any(payload, "text", "Text") or unicode_text or gurmukhi
        return (
            gurmukhi if isinstance(gurmukhi, str) else None,
            unicode_text if isinstance(unicode_text, str) else None,
            text if isinstance(text, str) else None,
        )
    return None, None, str(payload)


def _looks_like_text_payload(payload: dict) -> bool:
    return any(key in payload for key in TEXT_KEYS)


def flatten_translations(raw: dict) -> list[dict]:
    rows: list[dict] = []
    translation = pick(raw, "translation") or pick_any(raw, "Translations", "translation") or {}
    if not isinstance(translation, dict):
        return rows
    seen: set[tuple[str, str]] = set()

    def add_row(language: str, translator_code: str, payload: Any) -> None:
        gurmukhi, unicode_text, text = _payload_texts(payload)
        if not any((gurmukhi, unicode_text, text)):
            return
        language = str(language)[:8]
        translator_code = str(translator_code)[:16]
        key = (language, translator_code)
        if key in seen:
            return
        seen.add(key)
        rows.append(
            {
                "language": language,
                "translator_code": translator_code,
                "gurmukhi": gurmukhi,
                "unicode": unicode_text,
                "text": text,
            }
        )

    for language, translators in translation.items():
        if translators in (None, ""):
            continue
        if isinstance(translators, str):
            add_row(language, "default", translators)
            continue
        if not isinstance(translators, dict):
            continue
        if _looks_like_text_payload(translators):
            add_row(language, "default", translators)
            continue
        for translator_code, payload in translators.items():
            if isinstance(payload, dict) and not _looks_like_text_payload(payload):
                nested = payload.get("ss") if "ss" in payload else None
                if isinstance(nested, dict):
                    add_row(language, translator_code, nested)
                    continue
            add_row(language, translator_code, payload)
    return rows


def flatten_transliterations(raw: dict) -> list[dict]:
    rows: list[dict] = []
    transliteration = (
        pick(raw, "transliteration") or pick_any(raw, "Transliterations", "transliteration") or {}
    )
    if not isinstance(transliteration, dict):
        return rows
    for script, text in transliteration.items():
        if isinstance(text, dict):
            text = pick_any(text, "text", "unicode", "GurmukhiUni", "gurmukhi")
        if text:
            rows.append({"script": str(script)[:16], "text": text})
    return rows


def translation_value(rows: list[dict], language: str, translator_code: str) -> str | None:
    for row in rows:
        if row["language"] == language and row["translator_code"] == translator_code:
            return row.get("text") or row.get("unicode") or row.get("gurmukhi")
    return None


def transliteration_value(rows: list[dict], *scripts: str) -> str | None:
    wanted = {script.lower() for script in scripts}
    for row in rows:
        if str(row.get("script", "")).lower() in wanted:
            return row.get("text")
    return None


def normalize_writer(raw: dict | None) -> dict | None:
    if not raw or not isinstance(raw, dict):
        return None
    writer_id = pick_any(raw, "writerId", "writer_id", "WriterID")
    if not writer_id:
        return None
    return {
        "writer_id": writer_id,
        "english": pick_any(raw, "english", "WriterEnglish"),
        "gurmukhi": pick_any(raw, "gurmukhi", "WriterGurmukhi"),
        "unicode": pick_any(raw, "unicode", "WriterUnicode"),
    }


def normalize_raag(raw: dict | None) -> dict | None:
    if not raw or not isinstance(raw, dict):
        return None
    raag_id = pick_any(raw, "raagId", "raag_id", "RaagID")
    if not raag_id:
        return None
    english = pick_any(raw, "english", "RaagEnglish")
    if isinstance(english, str) and english.strip().lower() == "no raag":
        return None
    return {
        "raag_id": raag_id,
        "english": english,
        "gurmukhi": pick_any(raw, "gurmukhi", "RaagGurmukhi"),
        "unicode": pick_any(raw, "unicode", "RaagUnicode"),
        "raag_with_page": pick_any(raw, "raagWithPage", "raag_with_page", "RaagWithPage"),
    }


def _fill_denorm(verse: dict) -> dict:
    translations = verse.get("translations") or []
    transliterations = verse.get("transliterations") or []
    verse["english_ms"] = verse.get("english_ms") or translation_value(translations, "en", "ms")
    verse["english_bdb"] = verse.get("english_bdb") or translation_value(translations, "en", "bdb")
    verse["english_ssk"] = verse.get("english_ssk") or translation_value(translations, "en", "ssk")
    verse["punjabi_ss"] = verse.get("punjabi_ss") or translation_value(translations, "pu", "ss")
    verse["punjabi_ft"] = verse.get("punjabi_ft") or translation_value(translations, "pu", "ft")
    verse["punjabi_bdb"] = verse.get("punjabi_bdb") or translation_value(translations, "pu", "bdb")
    verse["hindi_ss"] = verse.get("hindi_ss") or translation_value(translations, "hi", "ss")
    verse["hindi_sts"] = verse.get("hindi_sts") or translation_value(translations, "hi", "sts")
    verse["spanish_sn"] = verse.get("spanish_sn") or translation_value(translations, "es", "sn")
    verse["translit_english"] = verse.get("translit_english") or transliteration_value(
        transliterations, "english", "en"
    )
    verse["translit_hindi"] = verse.get("translit_hindi") or transliteration_value(
        transliterations, "hindi", "hi"
    )
    verse["translit_ipa"] = verse.get("translit_ipa") or transliteration_value(transliterations, "ipa")
    verse["translit_urdu"] = verse.get("translit_urdu") or transliteration_value(
        transliterations, "urdu", "ur"
    )
    return verse


def normalize_verse(raw: dict, source_code: str, page_no: int) -> dict:
    verse = pick(raw, "verse") or {}
    larivaar = pick(raw, "larivaar") or {}
    translations = flatten_translations(raw)
    transliterations = flatten_transliterations(raw)
    return _fill_denorm(
        {
            "verse_id": raw.get("verseId") or raw.get("verse_id"),
            "shabad_id": raw.get("shabadId") or raw.get("shabad_id"),
            "source_code": source_code,
            "page_no": raw.get("pageNo") or raw.get("page_no") or page_no,
            "line_no": raw.get("lineNo") or raw.get("line_no"),
            "gurmukhi": verse.get("gurmukhi"),
            "unicode": verse.get("unicode"),
            "larivaar_gurmukhi": larivaar.get("gurmukhi"),
            "larivaar_unicode": larivaar.get("unicode"),
            "updated_at": raw.get("updated") or None,
            "visraam_json": as_json(pick(raw, "visraam")),
            "writer": normalize_writer(pick(raw, "writer")),
            "raag": normalize_raag(pick(raw, "raag")),
            "translations": translations,
            "transliterations": transliterations,
            "index_id": None,
            "header_id": None,
            "ang": None,
            "source_page_no": None,
            "original_source_id": None,
            "original_source_english": None,
            "original_source_gurmukhi": None,
            "original_source_unicode": None,
            "header_unicode": None,
            "header_gurmukhi": None,
            "english_ms": nested_text(pick(raw, "translation"), "en", "ms"),
            "english_bdb": nested_text(pick(raw, "translation"), "en", "bdb"),
            "english_ssk": nested_text(pick(raw, "translation"), "en", "ssk"),
            "punjabi_ss": nested_text(pick(raw, "translation"), "pu", "ss")
            or nested_text(pick(raw, "translation"), "pu", "ss", "unicode"),
            "hindi_ss": nested_text(pick(raw, "translation"), "hi", "ss"),
            "translit_english": nested_text(pick(raw, "transliteration"), "english")
            or nested_text(pick(raw, "transliteration"), "en"),
        }
    )


def _nav_page(value: Any) -> int | None:
    if value in (None, 0, "0"):
        return None
    return int(value)


def ak_verse_id(index_id: int, offset: int = AK_VERSE_ID_OFFSET) -> int:
    return offset + int(index_id)


def normalize_ak_header(raw: dict) -> dict | None:
    header_id = pick_any(raw, "HeaderID", "header_id", "headerId")
    if header_id is None:
        return None
    translations = flatten_translations(raw)
    transliterations = flatten_transliterations(raw)
    return {
        "header_id": int(header_id),
        "gurmukhi": pick_any(raw, "Gurmukhi", "gurmukhi"),
        "unicode": pick_any(raw, "GurmukhiUni", "unicode"),
        "updated_at": pick_any(raw, "Updated", "updated") or None,
        "translations": translations,
        "transliterations": transliterations,
    }


def normalize_ak_item(raw: dict, index_no: int, header_map: dict[int, dict], offset: int) -> dict:
    index_id = pick_any(raw, "IndexID", "index_id", "indexId")
    header_id = pick_any(raw, "HeaderID", "header_id", "headerId")
    header = header_map.get(int(header_id)) if header_id is not None else None
    original_source_id = pick_any(raw, "SourceID", "source_id", "sourceId")
    if original_source_id is not None:
        original_source_id = str(original_source_id)[:1]
    writer = normalize_writer(
        {
            "WriterID": pick_any(raw, "WriterID", "writerId"),
            "WriterEnglish": pick_any(raw, "WriterEnglish"),
            "WriterGurmukhi": pick_any(raw, "WriterGurmukhi"),
            "WriterUnicode": pick_any(raw, "WriterUnicode"),
        }
    )
    raag = normalize_raag(
        {
            "RaagID": pick_any(raw, "RaagID", "raagId"),
            "RaagEnglish": pick_any(raw, "RaagEnglish"),
            "RaagGurmukhi": pick_any(raw, "RaagGurmukhi"),
            "RaagUnicode": pick_any(raw, "RaagUnicode"),
            "RaagWithPage": pick_any(raw, "RaagWithPage"),
        }
    )
    translations = flatten_translations(raw)
    transliterations = flatten_transliterations(raw)
    ang = pick_any(raw, "Ang", "ang")
    source_page_no = pick_any(raw, "PageNo", "page_no", "pageNo")
    return _fill_denorm(
        {
            "verse_id": ak_verse_id(int(index_id), offset) if index_id is not None else None,
            "index_id": int(index_id) if index_id is not None else None,
            "header_id": int(header_id) if header_id is not None else None,
            "shabad_id": pick_any(raw, "ShabadID", "shabad_id", "shabadId"),
            "source_code": AK_SOURCE_CODE,
            "page_no": index_no,
            "line_no": pick_any(raw, "LineNo", "line_no", "lineNo"),
            "ang": int(ang) if ang not in (None, "") else None,
            "source_page_no": int(source_page_no) if source_page_no not in (None, "") else None,
            "gurmukhi": pick_any(raw, "Gurmukhi", "gurmukhi") or "",
            "unicode": pick_any(raw, "GurmukhiUni", "unicode") or "",
            "larivaar_gurmukhi": None,
            "larivaar_unicode": None,
            "updated_at": pick_any(raw, "Updated", "updated") or None,
            "visraam_json": as_json(pick_any(raw, "Visraam", "visraam")),
            "writer": writer,
            "raag": raag,
            "translations": translations,
            "transliterations": transliterations,
            "original_source_id": original_source_id,
            "original_source_english": pick_any(raw, "SourceEnglish"),
            "original_source_gurmukhi": pick_any(raw, "SourceGurmukhi"),
            "original_source_unicode": pick_any(raw, "SourceUnicode"),
            "header_unicode": (header or {}).get("unicode"),
            "header_gurmukhi": (header or {}).get("gurmukhi"),
        }
    )


def normalize_amrit_keertan_index(
    payload: dict,
    index_no: int,
    max_index: int = 113,
    offset: int = AK_VERSE_ID_OFFSET,
) -> dict:
    headers = [normalize_ak_header(item) for item in payload.get("header") or []]
    headers = [header for header in headers if header]
    header_map = {header["header_id"]: header for header in headers}
    verses = [
        normalize_ak_item(item, index_no, header_map, offset) for item in payload.get("index") or []
    ]
    previous_page = index_no - 1 if index_no > 1 else None
    next_page = index_no + 1 if index_no < max_index else None
    return {
        "source": {
            "code": AK_SOURCE_CODE,
            "english": "Amrit Keertan",
            "gurmukhi": None,
            "unicode": None,
        },
        "page_no": index_no,
        "verse_count": len(verses),
        "previous_page": previous_page,
        "next_page": next_page,
        "headers": headers,
        "verses": verses,
    }


def normalize_page(
    payload: dict,
    source_code: str,
    page_no: int | None = None,
    max_index: int = 113,
    offset: int = AK_VERSE_ID_OFFSET,
) -> dict:
    if source_code == AK_SOURCE_CODE:
        if page_no is None:
            page_no = 1
        return normalize_amrit_keertan_index(payload, page_no, max_index=max_index, offset=offset)
    source = pick(payload, "source") or {}
    navigation = pick(payload, "navigation") or {}
    resolved_page = source.get("pageNo") or source.get("page_no") or payload.get("pageNo") or page_no
    verses = [normalize_verse(item, source_code, resolved_page) for item in payload.get("page") or []]
    previous_page = _nav_page(navigation.get("previous"))
    next_page = _nav_page(navigation.get("next"))
    return {
        "source": {
            "code": source.get("sourceId") or source.get("source_id") or source_code,
            "english": source.get("english"),
            "gurmukhi": source.get("gurmukhi"),
            "unicode": source.get("unicode"),
        },
        "page_no": resolved_page,
        "verse_count": payload.get("count") or len(verses),
        "previous_page": previous_page,
        "next_page": next_page,
        "headers": [],
        "verses": verses,
    }


def search_blob(verse: dict) -> str:
    parts = [
        verse.get("gurmukhi"),
        verse.get("unicode"),
        verse.get("larivaar_unicode"),
        verse.get("header_gurmukhi"),
        verse.get("header_unicode"),
        verse.get("english_ms"),
        verse.get("english_bdb"),
        verse.get("english_ssk"),
        verse.get("punjabi_ss"),
        verse.get("punjabi_ft"),
        verse.get("punjabi_bdb"),
        verse.get("hindi_ss"),
        verse.get("hindi_sts"),
        verse.get("spanish_sn"),
        verse.get("translit_english"),
        verse.get("translit_hindi"),
        verse.get("translit_ipa"),
        verse.get("translit_urdu"),
    ]
    for row in verse.get("translations") or []:
        parts.extend([row.get("gurmukhi"), row.get("unicode"), row.get("text")])
    for row in verse.get("transliterations") or []:
        parts.append(row.get("text"))
    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        if part and part not in seen:
            seen.add(part)
            ordered.append(part)
    return "\n".join(ordered)
