import { openDB } from '@/db/database';

export interface LocalTimer {
  id: string;
  muscle_group_id: string;
  start_time: string;        // ISO UTC
  duration_minutes: number;
  intensity_score: number | null;
  source: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  notification_id: string | null;
  server_synced_at: string | null;
  pending_op: string | null;
}

export async function upsertTimer(t: LocalTimer): Promise<void> {
  const db = await openDB();
  await db.runAsync(
    `INSERT INTO recovery_timers
       (id, muscle_group_id, start_time, duration_minutes, intensity_score, source, notes,
        created_at, updated_at, deleted_at, notification_id, server_synced_at, pending_op)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET
       muscle_group_id = excluded.muscle_group_id,
       start_time = excluded.start_time,
       duration_minutes = excluded.duration_minutes,
       intensity_score = excluded.intensity_score,
       source = excluded.source,
       notes = excluded.notes,
       updated_at = excluded.updated_at,
       deleted_at = excluded.deleted_at,
       notification_id = COALESCE(excluded.notification_id, recovery_timers.notification_id),
       server_synced_at = COALESCE(excluded.server_synced_at, recovery_timers.server_synced_at),
       pending_op = excluded.pending_op
    `,
    [
      t.id,
      t.muscle_group_id,
      t.start_time,
      t.duration_minutes,
      t.intensity_score,
      t.source,
      t.notes,
      t.created_at,
      t.updated_at,
      t.deleted_at,
      t.notification_id,
      t.server_synced_at,
      t.pending_op,
    ],
  );
}

export async function listCurrentTimers(): Promise<LocalTimer[]> {
  const db = await openDB();
  // One latest per muscle group, ignoring soft-deleted.
  const rows = await db.getAllAsync<LocalTimer>(
    `SELECT t.* FROM recovery_timers t
     WHERE deleted_at IS NULL
       AND start_time = (
         SELECT MAX(start_time) FROM recovery_timers
         WHERE muscle_group_id = t.muscle_group_id AND deleted_at IS NULL
       )
     ORDER BY t.muscle_group_id`,
  );
  return rows;
}

export async function getTimer(id: string): Promise<LocalTimer | null> {
  const db = await openDB();
  return db.getFirstAsync<LocalTimer>('SELECT * FROM recovery_timers WHERE id = ?', [id]);
}

export async function softDeleteTimer(id: string, deletedAt: string): Promise<void> {
  const db = await openDB();
  await db.runAsync(
    `UPDATE recovery_timers
       SET deleted_at = ?, updated_at = ?, pending_op = 'delete'
     WHERE id = ?`,
    [deletedAt, deletedAt, id],
  );
}

export async function markSynced(id: string, syncedAt: string): Promise<void> {
  const db = await openDB();
  await db.runAsync(
    'UPDATE recovery_timers SET server_synced_at = ?, pending_op = NULL WHERE id = ?',
    [syncedAt, id],
  );
}

export async function listPending(): Promise<LocalTimer[]> {
  const db = await openDB();
  return db.getAllAsync<LocalTimer>(
    "SELECT * FROM recovery_timers WHERE pending_op IS NOT NULL",
  );
}

export async function hardDeleteTimer(id: string): Promise<void> {
  const db = await openDB();
  await db.runAsync('DELETE FROM recovery_timers WHERE id = ?', [id]);
}
