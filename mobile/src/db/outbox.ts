import { openDB } from '@/db/database';

export type OutboxKind = 'timer.create' | 'timer.delete';

export interface OutboxItem {
  client_op_id: string;
  kind: OutboxKind;
  payload: string;       // JSON
  created_at: string;
  last_error: string | null;
  attempts: number;
}

export async function enqueue(item: {
  client_op_id: string;
  kind: OutboxKind;
  payload: unknown;
}): Promise<void> {
  const db = await openDB();
  await db.runAsync(
    `INSERT OR REPLACE INTO outbox (client_op_id, kind, payload, created_at, last_error, attempts)
     VALUES (?, ?, ?, ?, NULL, 0)`,
    [item.client_op_id, item.kind, JSON.stringify(item.payload), new Date().toISOString()],
  );
}

export async function listOutbox(): Promise<OutboxItem[]> {
  const db = await openDB();
  return db.getAllAsync<OutboxItem>('SELECT * FROM outbox ORDER BY created_at ASC');
}

export async function dequeue(opId: string): Promise<void> {
  const db = await openDB();
  await db.runAsync('DELETE FROM outbox WHERE client_op_id = ?', [opId]);
}

export async function recordFailure(opId: string, err: string): Promise<void> {
  const db = await openDB();
  await db.runAsync(
    'UPDATE outbox SET last_error = ?, attempts = attempts + 1 WHERE client_op_id = ?',
    [err, opId],
  );
}
