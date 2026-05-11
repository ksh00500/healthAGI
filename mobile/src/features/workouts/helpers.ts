import type { WorkoutSession } from '@/api/types';

export function sessionVolumeKg(s: WorkoutSession): number {
  let v = 0;
  for (const set of s.sets) {
    if (set.is_warmup) continue;
    const reps = set.reps ?? 0;
    const w = set.weight_kg ? Number(set.weight_kg) : 0;
    v += reps * w;
  }
  return v;
}

export function isoDay(d: Date = new Date()): string {
  return d.toISOString().slice(0, 10);
}
