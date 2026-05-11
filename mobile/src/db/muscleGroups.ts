import { openDB } from '@/db/database';
import type { MuscleGroup } from '@/api/types';

export async function cacheMuscleGroups(groups: MuscleGroup[]): Promise<void> {
  const db = await openDB();
  await db.withTransactionAsync(async () => {
    for (const g of groups) {
      await db.runAsync(
        `INSERT INTO muscle_groups (id, display_name_ko, display_name_en, default_recovery_hours, sort_order)
         VALUES (?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET
           display_name_ko = excluded.display_name_ko,
           display_name_en = excluded.display_name_en,
           default_recovery_hours = excluded.default_recovery_hours,
           sort_order = excluded.sort_order`,
        [g.id, g.display_name_ko, g.display_name_en, g.default_recovery_hours, g.sort_order],
      );
    }
  });
}

export async function listMuscleGroupsLocal(): Promise<MuscleGroup[]> {
  const db = await openDB();
  return db.getAllAsync<MuscleGroup>(
    'SELECT * FROM muscle_groups ORDER BY sort_order ASC',
  );
}

// Bootstrap defaults so the timer screen is usable on cold start without server.
export const DEFAULT_MUSCLE_GROUPS: MuscleGroup[] = [
  { id: 'chest', display_name_ko: '가슴', display_name_en: 'Chest', default_recovery_hours: 48, sort_order: 10 },
  { id: 'back', display_name_ko: '등', display_name_en: 'Back', default_recovery_hours: 48, sort_order: 20 },
  { id: 'shoulders_front', display_name_ko: '어깨 전면', display_name_en: 'Front Delts', default_recovery_hours: 48, sort_order: 30 },
  { id: 'shoulders_side', display_name_ko: '어깨 측면', display_name_en: 'Side Delts', default_recovery_hours: 48, sort_order: 31 },
  { id: 'shoulders_rear', display_name_ko: '어깨 후면', display_name_en: 'Rear Delts', default_recovery_hours: 48, sort_order: 32 },
  { id: 'biceps', display_name_ko: '이두', display_name_en: 'Biceps', default_recovery_hours: 24, sort_order: 40 },
  { id: 'triceps', display_name_ko: '삼두', display_name_en: 'Triceps', default_recovery_hours: 24, sort_order: 41 },
  { id: 'forearms', display_name_ko: '전완', display_name_en: 'Forearms', default_recovery_hours: 24, sort_order: 42 },
  { id: 'quads', display_name_ko: '대퇴 사두', display_name_en: 'Quads', default_recovery_hours: 72, sort_order: 50 },
  { id: 'hamstrings', display_name_ko: '햄스트링', display_name_en: 'Hamstrings', default_recovery_hours: 72, sort_order: 51 },
  { id: 'glutes', display_name_ko: '둔근', display_name_en: 'Glutes', default_recovery_hours: 72, sort_order: 52 },
  { id: 'calves', display_name_ko: '종아리', display_name_en: 'Calves', default_recovery_hours: 48, sort_order: 53 },
  { id: 'core', display_name_ko: '코어', display_name_en: 'Core', default_recovery_hours: 24, sort_order: 60 },
];
