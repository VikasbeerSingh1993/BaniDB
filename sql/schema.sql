-- Bani Search corpus: G, D, B, S, A (Amrit Keertan)
-- MySQL 8+ / utf8mb4 / FULLTEXT ngram for Gurmukhi and English search
-- Amrit Keertan lines use verse_id = 2000000000 + IndexID so they never
-- collide with Gurbani verse_id values. payload SourceID is stored in
-- original_source_id. Collection source_code is always A.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS sources (
  code CHAR(1) NOT NULL,
  english VARCHAR(128) NOT NULL,
  gurmukhi VARCHAR(256) NULL,
  unicode VARCHAR(256) NULL,
  PRIMARY KEY (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO sources (code, english, gurmukhi, unicode) VALUES
  ('G', 'Sri Guru Granth Sahib Ji', NULL, NULL),
  ('D', 'Dasam Granth', NULL, NULL),
  ('B', 'Bhai Gurdas Ji Vaaran', NULL, NULL),
  ('S', 'Bhai Gurdas Singh Ji Vaaran', NULL, NULL),
  ('A', 'Amrit Keertan', NULL, NULL)
ON DUPLICATE KEY UPDATE english = VALUES(english);

CREATE TABLE IF NOT EXISTS writers (
  writer_id INT NOT NULL,
  english VARCHAR(255) NULL,
  gurmukhi VARCHAR(255) NULL,
  unicode VARCHAR(255) NULL,
  PRIMARY KEY (writer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS raags (
  raag_id INT NOT NULL,
  english VARCHAR(255) NULL,
  gurmukhi VARCHAR(255) NULL,
  unicode VARCHAR(255) NULL,
  raag_with_page VARCHAR(255) NULL,
  PRIMARY KEY (raag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS pages (
  source_code CHAR(1) NOT NULL,
  page_no INT NOT NULL,
  verse_count INT NOT NULL DEFAULT 0,
  previous_page INT NULL,
  next_page INT NULL,
  fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (source_code, page_no),
  KEY idx_pages_next (source_code, next_page),
  CONSTRAINT fk_pages_source FOREIGN KEY (source_code) REFERENCES sources (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS verses (
  verse_id BIGINT NOT NULL,
  source_code CHAR(1) NOT NULL,
  shabad_id BIGINT NULL,
  page_no INT NOT NULL,
  line_no INT NULL,
  gurmukhi TEXT NOT NULL,
  unicode TEXT NOT NULL,
  larivaar_gurmukhi TEXT NULL,
  larivaar_unicode TEXT NULL,
  writer_id INT NULL,
  raag_id INT NULL,
  updated_at DATETIME NULL,
  visraam_json JSON NULL,
  index_id BIGINT NULL,
  header_id INT NULL,
  ang INT NULL,
  source_page_no INT NULL,
  original_source_id CHAR(1) NULL,
  original_source_english VARCHAR(128) NULL,
  original_source_gurmukhi VARCHAR(256) NULL,
  original_source_unicode VARCHAR(256) NULL,
  PRIMARY KEY (verse_id),
  UNIQUE KEY uq_verses_source_index (source_code, index_id),
  KEY idx_verses_source_page (source_code, page_no, line_no),
  KEY idx_verses_shabad (shabad_id),
  KEY idx_verses_writer (writer_id),
  KEY idx_verses_raag (raag_id),
  KEY idx_verses_header (header_id),
  KEY idx_verses_original_source (original_source_id),
  FULLTEXT KEY ft_verses_unicode (unicode) WITH PARSER ngram,
  FULLTEXT KEY ft_verses_gurmukhi (gurmukhi) WITH PARSER ngram,
  CONSTRAINT fk_verses_source FOREIGN KEY (source_code) REFERENCES sources (code),
  CONSTRAINT fk_verses_writer FOREIGN KEY (writer_id) REFERENCES writers (writer_id),
  CONSTRAINT fk_verses_raag FOREIGN KEY (raag_id) REFERENCES raags (raag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS verse_translations (
  id BIGINT NOT NULL AUTO_INCREMENT,
  verse_id BIGINT NOT NULL,
  language CHAR(8) NOT NULL,
  translator_code VARCHAR(16) NOT NULL,
  gurmukhi TEXT NULL,
  unicode TEXT NULL,
  text TEXT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_translation (verse_id, language, translator_code),
  KEY idx_tr_lang (language, translator_code),
  FULLTEXT KEY ft_tr_text (text) WITH PARSER ngram,
  FULLTEXT KEY ft_tr_unicode (unicode) WITH PARSER ngram,
  CONSTRAINT fk_tr_verse FOREIGN KEY (verse_id) REFERENCES verses (verse_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS verse_transliterations (
  id BIGINT NOT NULL AUTO_INCREMENT,
  verse_id BIGINT NOT NULL,
  script VARCHAR(16) NOT NULL,
  text TEXT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tl (verse_id, script),
  FULLTEXT KEY ft_tl_text (text) WITH PARSER ngram,
  CONSTRAINT fk_tl_verse FOREIGN KEY (verse_id) REFERENCES verses (verse_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS search_documents (
  verse_id BIGINT NOT NULL,
  source_code CHAR(1) NOT NULL,
  shabad_id BIGINT NULL,
  page_no INT NOT NULL,
  line_no INT NULL,
  writer_english VARCHAR(255) NULL,
  raag_english VARCHAR(255) NULL,
  gurmukhi TEXT NOT NULL,
  unicode TEXT NOT NULL,
  larivaar_unicode TEXT NULL,
  english_ms TEXT NULL,
  english_bdb TEXT NULL,
  english_ssk TEXT NULL,
  punjabi_ss TEXT NULL,
  hindi_ss TEXT NULL,
  translit_english TEXT NULL,
  search_blob LONGTEXT NOT NULL,
  index_id BIGINT NULL,
  header_id INT NULL,
  ang INT NULL,
  original_source_id CHAR(1) NULL,
  header_unicode TEXT NULL,
  punjabi_ft TEXT NULL,
  punjabi_bdb TEXT NULL,
  spanish_sn TEXT NULL,
  hindi_sts TEXT NULL,
  translit_hindi TEXT NULL,
  translit_ipa TEXT NULL,
  translit_urdu TEXT NULL,
  PRIMARY KEY (verse_id),
  KEY idx_sd_source_page (source_code, page_no),
  KEY idx_sd_shabad (shabad_id),
  KEY idx_sd_index (source_code, index_id),
  KEY idx_sd_original_source (original_source_id),
  FULLTEXT KEY ft_sd_blob (search_blob) WITH PARSER ngram,
  FULLTEXT KEY ft_sd_unicode (unicode) WITH PARSER ngram,
  FULLTEXT KEY ft_sd_english (english_bdb, english_ms, english_ssk),
  CONSTRAINT fk_sd_verse FOREIGN KEY (verse_id) REFERENCES verses (verse_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS ingest_state (
  source_code CHAR(1) NOT NULL,
  last_page INT NOT NULL DEFAULT 0,
  last_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  last_error TEXT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (source_code),
  CONSTRAINT fk_ingest_source FOREIGN KEY (source_code) REFERENCES sources (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO ingest_state (source_code, last_page, last_status)
VALUES ('G', 0, 'pending'), ('D', 0, 'pending'), ('B', 0, 'pending'), ('S', 0, 'pending'), ('A', 0, 'pending')
ON DUPLICATE KEY UPDATE source_code = source_code;

CREATE TABLE IF NOT EXISTS amrit_keertan_headers (
  header_id INT NOT NULL,
  gurmukhi TEXT NULL,
  unicode TEXT NULL,
  updated_at DATETIME NULL,
  PRIMARY KEY (header_id),
  FULLTEXT KEY ft_ak_header_unicode (unicode) WITH PARSER ngram,
  FULLTEXT KEY ft_ak_header_gurmukhi (gurmukhi) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS amrit_keertan_header_translations (
  id BIGINT NOT NULL AUTO_INCREMENT,
  header_id INT NOT NULL,
  language CHAR(8) NOT NULL,
  translator_code VARCHAR(16) NOT NULL,
  gurmukhi TEXT NULL,
  unicode TEXT NULL,
  text TEXT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_ak_hdr_tr (header_id, language, translator_code),
  FULLTEXT KEY ft_ak_hdr_tr_text (text) WITH PARSER ngram,
  FULLTEXT KEY ft_ak_hdr_tr_unicode (unicode) WITH PARSER ngram,
  CONSTRAINT fk_ak_hdr_tr FOREIGN KEY (header_id) REFERENCES amrit_keertan_headers (header_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS amrit_keertan_header_transliterations (
  id BIGINT NOT NULL AUTO_INCREMENT,
  header_id INT NOT NULL,
  script VARCHAR(16) NOT NULL,
  text TEXT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_ak_hdr_tl (header_id, script),
  FULLTEXT KEY ft_ak_hdr_tl_text (text) WITH PARSER ngram,
  CONSTRAINT fk_ak_hdr_tl FOREIGN KEY (header_id) REFERENCES amrit_keertan_headers (header_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;
