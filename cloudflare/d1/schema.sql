PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS scope_meta (
  scope_id TEXT PRIMARY KEY,
  scope_name TEXT NOT NULL,
  updated_at TEXT,
  diputados_count INTEGER NOT NULL DEFAULT 0,
  votaciones_count INTEGER NOT NULL DEFAULT 0,
  votos_count INTEGER NOT NULL DEFAULT 0,
  ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS groups (
  scope_id TEXT NOT NULL,
  group_idx INTEGER NOT NULL,
  group_name TEXT NOT NULL,
  PRIMARY KEY (scope_id, group_idx)
);

CREATE TABLE IF NOT EXISTS votaciones (
  scope_id TEXT NOT NULL,
  vot_idx INTEGER NOT NULL,
  id TEXT NOT NULL,
  legislatura TEXT,
  fecha TEXT,
  titulo_ciudadano TEXT,
  categoria_idx INTEGER,
  categoria_label TEXT,
  etiquetas_json TEXT,
  proponente TEXT,
  sub_tipo TEXT,
  expediente TEXT,
  result TEXT,
  favor INTEGER,
  contra INTEGER,
  abstencion INTEGER,
  total INTEGER,
  ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (scope_id, id)
);

CREATE INDEX IF NOT EXISTS idx_votaciones_scope_fecha
  ON votaciones(scope_id, fecha DESC);

CREATE INDEX IF NOT EXISTS idx_votaciones_scope_leg
  ON votaciones(scope_id, legislatura);

CREATE INDEX IF NOT EXISTS idx_votaciones_scope_categoria
  ON votaciones(scope_id, categoria_label);

CREATE TABLE IF NOT EXISTS diputados (
  scope_id TEXT NOT NULL,
  dip_idx INTEGER NOT NULL,
  nombre TEXT NOT NULL,
  nombre_search TEXT NOT NULL,
  main_grupo_idx INTEGER,
  main_grupo_name TEXT,
  total INTEGER,
  favor INTEGER,
  contra INTEGER,
  abstencion INTEGER,
  no_vota INTEGER,
  loyalty REAL,
  foto_json TEXT,
  provincia TEXT,
  ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (scope_id, dip_idx),
  UNIQUE (scope_id, nombre)
);

CREATE INDEX IF NOT EXISTS idx_diputados_scope_nombre_search
  ON diputados(scope_id, nombre_search);

CREATE INDEX IF NOT EXISTS idx_diputados_scope_grupo
  ON diputados(scope_id, main_grupo_name);
