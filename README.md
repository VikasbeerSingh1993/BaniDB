# Bani Search Corpus

Local MySQL corpus of Sikh scripture from the public BaniDB APIs, built for fast text search and later model training.

Sources ingested in this repo:

- `G` Sri Guru Granth Sahib Ji — `GET https://api.banidb.com/v2/angs/{ang}/G`
- `D` Dasam Granth — `GET https://api.banidb.com/v2/angs/{n}/D`
- `B` Bhai Gurdas Ji Vaaran — `GET https://api.banidb.com/v2/angs/{n}/B`
- `S` Bhai Gurdas Singh Ji Vaaran — `GET https://api.banidb.com/v2/angs/{n}/S`
- `A` Amrit Keertan — `GET https://api.banidb.com/v2/amritkeertan/index/{n}` for indexes **1 through 113**

`G`, `D`, `B`, and `S` are crawled page by page until `navigation.next` is null (`0` is treated as null). Amrit Keertan is crawled sequentially from index 1 to 113. Progress is stored in `ingest_state`, so a stopped run can resume.

Bhai Nand Lal and Rehatnamas are not ingested as standalone sources. Amrit Keertan lines may cite those works in `original_source_id`; they are stored under collection source `A` and do not overwrite `G`/`D`/`B`/`S` verses. Amrit Keertan `verse_id` values are `2000000000 + IndexID`.

## Setup

Use a local MySQL 8 instance (this machine already has MySQL80 on port 3306). Copy `.env.example` to `.env` and set `MYSQL_USER` / `MYSQL_PASSWORD` to your local login. Do not commit `.env`.

```powershell
cd F:\BaniDB
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts\setup_mysql.py
```

`setup_mysql.py` creates `bani_search` if needed and applies `sql/schema.sql`. Docker Compose is optional and should stay off while local MySQL already owns 3306.

Then ingest:

```powershell
python -m src.ingest --source all
```

Single source or resume from a page/index:

```powershell
python -m src.ingest --source G --start-page 1
python -m src.ingest --source D
python -m src.ingest --source B
python -m src.ingest --source S
python -m src.ingest --source A
python -m src.ingest --source A --start-page 1
```

Search:

```powershell
python -m src.search ਨਾਨਕ --limit 5
```

## Schema

See `sql/schema.sql`. Core tables:

- `verses` — Gurmukhi, Unicode, larivaar, writer, raag; Amrit Keertan extras `index_id`, `header_id`, `ang`, `source_page_no`, `original_source_*`
- `verse_translations` / `verse_transliterations` — one row per language or script
- `amrit_keertan_headers` plus header translation/transliteration tables — section titles
- `search_documents` — denormalized ngram FULLTEXT row for comparison training
- `ingest_state` — last completed page or AK index per source
