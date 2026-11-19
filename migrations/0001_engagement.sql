CREATE TABLE IF NOT EXISTS engagement (
  kind TEXT NOT NULL CHECK(kind IN ('like','rating')),
  content_type TEXT NOT NULL CHECK(content_type IN ('article','review','ranking')),
  slug TEXT NOT NULL,
  visitor TEXT NOT NULL,
  value INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(kind, content_type, slug, visitor)
);
CREATE INDEX IF NOT EXISTS engagement_totals ON engagement(kind,content_type,slug);
