export interface MuscleGroup {
  id: string;
  display_name_ko: string;
  display_name_en: string;
  default_recovery_hours: number;
  sort_order: number;
}

export interface Timer {
  id: string;
  muscle_group_id: string;
  start_time: string;
  duration_minutes: number;
  intensity_score: string | null;
  source: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface TimerCreate {
  muscle_group_id: string;
  start_time?: string;
  duration_minutes?: number;
  intensity_score?: number;
  source?: 'manual' | 'auto_from_workout' | 'ai';
  notes?: string;
  client_op_id?: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Me {
  id: string;
  email: string;
}

export interface Profile {
  display_name: string | null;
  birth_date: string | null;
  sex: 'M' | 'F' | 'O' | null;
  height_cm: string | null;
  timezone: string;
  locale: string;
  goals: string | null;
  notes: string | null;
  updated_at: string;
}
