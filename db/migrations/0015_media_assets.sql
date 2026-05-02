-- 0015_media_assets.sql
-- Phase 35 / ADR 0037: 媒体资产落盘

CREATE TABLE IF NOT EXISTS media_assets (
    media_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,                   -- image / audio / video / file
    path TEXT,                            -- 本地或远端路径
    content_hash TEXT NOT NULL,           -- sha256 去重用
    mime_type TEXT,
    size_bytes INTEGER,
    owner_type TEXT NOT NULL DEFAULT 'person',
    owner_id TEXT,
    visibility TEXT NOT NULL DEFAULT 'private',  -- private / shared / group
    scene_id TEXT,
    summary TEXT,                         -- OCR / 转录结果或手工描述
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_media_assets_hash ON media_assets(content_hash);
CREATE INDEX IF NOT EXISTS idx_media_assets_owner ON media_assets(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_scene ON media_assets(scene_id);

-- 媒体引用到 memory / event 的关联（多对多）
CREATE TABLE IF NOT EXISTS media_refs (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id TEXT NOT NULL REFERENCES media_assets(media_id),
    target_type TEXT NOT NULL,            -- memory / event
    target_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(media_id, target_type, target_id)
);

CREATE INDEX IF NOT EXISTS idx_media_refs_target ON media_refs(target_type, target_id);
