import { create } from 'zustand';

import { createTimer, deleteTimer, listCurrentTimers, listMuscleGroups } from '@/api/endpoints';
import { DEFAULT_MUSCLE_GROUPS, cacheMuscleGroups, listMuscleGroupsLocal } from '@/db/muscleGroups';
import { dequeue, enqueue, listOutbox, recordFailure } from '@/db/outbox';
import {
  type LocalTimer,
  hardDeleteTimer,
  listCurrentTimers as listCurrentTimersLocal,
  markSynced,
  softDeleteTimer,
  upsertTimer,
} from '@/db/timers';
import type { MuscleGroup, Timer } from '@/api/types';
import { cancelScheduled, scheduleRecoveryEnd } from '@/lib/notifications';
import { uuidv4 } from '@/lib/uuid';

interface TimersState {
  muscleGroups: MuscleGroup[];
  timers: LocalTimer[];
  online: boolean;
  loadFromLocal: () => Promise<void>;
  sync: () => Promise<void>;
  start: (muscleGroupId: string, durationMinutes?: number) => Promise<void>;
  stop: (timerId: string) => Promise<void>;
}

function toLocal(t: Timer): LocalTimer {
  return {
    id: t.id,
    muscle_group_id: t.muscle_group_id,
    start_time: t.start_time,
    duration_minutes: t.duration_minutes,
    intensity_score: t.intensity_score ? Number(t.intensity_score) : null,
    source: t.source,
    notes: t.notes,
    created_at: t.created_at,
    updated_at: t.updated_at,
    deleted_at: t.deleted_at,
    notification_id: null,
    server_synced_at: new Date().toISOString(),
    pending_op: null,
  };
}

export const useTimers = create<TimersState>((set, get) => ({
  muscleGroups: [],
  timers: [],
  online: true,

  loadFromLocal: async () => {
    const groupsLocal = await listMuscleGroupsLocal();
    const groups = groupsLocal.length > 0 ? groupsLocal : DEFAULT_MUSCLE_GROUPS;
    const timers = await listCurrentTimersLocal();
    set({ muscleGroups: groups, timers });
  },

  sync: async () => {
    try {
      const remoteGroups = await listMuscleGroups();
      await cacheMuscleGroups(remoteGroups);
      set({ muscleGroups: remoteGroups, online: true });
    } catch {
      set({ online: false });
    }

    // Flush outbox: retry pending mutations.
    const queue = await listOutbox();
    for (const item of queue) {
      try {
        if (item.kind === 'timer.create') {
          const payload = JSON.parse(item.payload);
          const created = await createTimer(payload);
          // The local stub used clientOpId as its primary key; replace it
          // with the server-issued row so future deletes hit the real id.
          if (payload.client_op_id && payload.client_op_id !== created.id) {
            await hardDeleteTimer(payload.client_op_id);
          }
          await upsertTimer(toLocal(created));
          await markSynced(created.id, new Date().toISOString());
          await dequeue(item.client_op_id);
        } else if (item.kind === 'timer.delete') {
          const { id } = JSON.parse(item.payload);
          try {
            await deleteTimer(id);
          } catch (e) {
            // 404 means the row only existed locally (never synced) —
            // safe to drop the queued delete and the local row.
            if (String(e).includes('404')) {
              await hardDeleteTimer(id);
            } else {
              throw e;
            }
          }
          await dequeue(item.client_op_id);
        }
      } catch (e) {
        await recordFailure(item.client_op_id, String(e));
        set({ online: false });
        break;
      }
    }

    // Pull latest current timers.
    try {
      const remote = await listCurrentTimers();
      for (const t of remote) await upsertTimer(toLocal(t));
      const local = await listCurrentTimersLocal();
      set({ timers: local, online: true });
    } catch {
      set({ online: false });
    }
  },

  start: async (muscleGroupId, durationMinutes) => {
    const group = get().muscleGroups.find((g) => g.id === muscleGroupId);
    if (!group) throw new Error(`unknown muscle group: ${muscleGroupId}`);
    const duration = durationMinutes ?? group.default_recovery_hours * 60;
    const now = new Date();
    const endTime = new Date(now.getTime() + duration * 60 * 1000);
    const clientOpId = uuidv4();
    const localId = clientOpId; // use op id as local pk until server returns

    const notificationId = await scheduleRecoveryEnd({
      muscleNameKo: group.display_name_ko,
      endTime,
    });

    const local: LocalTimer = {
      id: localId,
      muscle_group_id: muscleGroupId,
      start_time: now.toISOString(),
      duration_minutes: duration,
      intensity_score: null,
      source: 'manual',
      notes: null,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
      deleted_at: null,
      notification_id: notificationId,
      server_synced_at: null,
      pending_op: 'create',
    };
    await upsertTimer(local);
    await enqueue({
      client_op_id: clientOpId,
      kind: 'timer.create',
      payload: {
        muscle_group_id: muscleGroupId,
        start_time: now.toISOString(),
        duration_minutes: duration,
        source: 'manual',
        client_op_id: clientOpId,
      },
    });
    set({ timers: await listCurrentTimersLocal() });

    // fire-and-forget sync attempt
    void get().sync();
  },

  stop: async (timerId) => {
    const local = (await listCurrentTimersLocal()).find((t) => t.id === timerId);
    if (local?.notification_id) await cancelScheduled(local.notification_id);
    const now = new Date().toISOString();
    await softDeleteTimer(timerId, now);
    await enqueue({
      client_op_id: uuidv4(),
      kind: 'timer.delete',
      payload: { id: timerId },
    });
    set({ timers: await listCurrentTimersLocal() });
    void get().sync();
  },
}));

export function timerProgress(t: LocalTimer, now: number = Date.now()): {
  remainingMs: number;
  ratio: number;
  endTimeMs: number;
} {
  const startMs = new Date(t.start_time).getTime();
  const endTimeMs = startMs + t.duration_minutes * 60 * 1000;
  const remainingMs = Math.max(0, endTimeMs - now);
  const total = t.duration_minutes * 60 * 1000;
  const ratio = total === 0 ? 1 : 1 - remainingMs / total;
  return { remainingMs, ratio, endTimeMs };
}

export function formatRemaining(ms: number): string {
  if (ms <= 0) return '00:00:00';
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
