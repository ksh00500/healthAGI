import * as SQLite from 'expo-sqlite';

let _db: SQLite.SQLiteDatabase | null = null;

export async function openDB(): Promise<SQLite.SQLiteDatabase> {
  if (_db) return _db;
  _db = await SQLite.openDatabaseAsync('healthagi.db');
  await migrate(_db);
  return _db;
}

async function migrate(db: SQLite.SQLiteDatabase): Promise<void> {
  await db.execAsync(`
    PRAGMA journal_mode = WAL;
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS muscle_groups (
      id TEXT PRIMARY KEY,
      display_name_ko TEXT NOT NULL,
      display_name_en TEXT NOT NULL,
      default_recovery_hours INTEGER NOT NULL,
      sort_order INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS recovery_timers (
      id TEXT PRIMARY KEY,
      muscle_group_id TEXT NOT NULL,
      start_time TEXT NOT NULL,
      duration_minutes INTEGER NOT NULL,
      intensity_score REAL,
      source TEXT NOT NULL DEFAULT 'manual',
      notes TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      deleted_at TEXT,
      notification_id TEXT,
      server_synced_at TEXT,
      pending_op TEXT
    );
    CREATE INDEX IF NOT EXISTS ix_timers_muscle_active
      ON recovery_timers (muscle_group_id, deleted_at);

    CREATE TABLE IF NOT EXISTS outbox (
      client_op_id TEXT PRIMARY KEY,
      kind TEXT NOT NULL,
      payload TEXT NOT NULL,
      created_at TEXT NOT NULL,
      last_error TEXT,
      attempts INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS sync_state (
      table_name TEXT PRIMARY KEY,
      last_pull_at TEXT
    );
  `);
}

export type DB = SQLite.SQLiteDatabase;
