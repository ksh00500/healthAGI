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

export interface BodyMetric {
  id: string;
  measured_at: string;
  weight_kg: string | null;
  body_fat_pct: string | null;
  resting_hr: number | null;
  sleep_hours: string | null;
  notes: string | null;
  updated_at: string;
  deleted_at: string | null;
}

export interface BodyMetricCreate {
  measured_at: string;
  weight_kg?: string;
  body_fat_pct?: string;
  resting_hr?: number;
  sleep_hours?: string;
  notes?: string;
}

export interface Exercise {
  id: string;
  canonical_name: string;
  display_name_ko: string | null;
  display_name_en: string | null;
  primary_muscle_group_id: string | null;
  secondary_muscle_group_ids: string[];
  equipment: string | null;
  is_compound: boolean;
}

export interface WorkoutSet {
  id: string;
  exercise_id: string;
  set_index: number;
  reps: number | null;
  weight_kg: string | null;
  rpe: string | null;
  is_warmup: boolean;
  notes: string | null;
}

export interface WorkoutSetInput {
  exercise_id: string;
  set_index: number;
  reps?: number;
  weight_kg?: string;
  rpe?: string;
  is_warmup?: boolean;
  notes?: string;
}

export interface WorkoutSession {
  id: string;
  started_at: string;
  ended_at: string | null;
  notes: string | null;
  raw_input: string | null;
  sets: WorkoutSet[];
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface WorkoutSessionCreate {
  started_at?: string;
  ended_at?: string;
  notes?: string;
  raw_input?: string;
  sets: WorkoutSetInput[];
}

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack';

export interface MealItem {
  id: string;
  name: string;
  serving_g: string | null;
  kcal: string | null;
  protein_g: string | null;
  carbs_g: string | null;
  fat_g: string | null;
  ai_confidence: string | null;
  user_confirmed: boolean;
}

export interface MealItemInput {
  name: string;
  serving_g?: string;
  kcal?: string;
  protein_g?: string;
  carbs_g?: string;
  fat_g?: string;
  user_confirmed?: boolean;
}

export interface Meal {
  id: string;
  eaten_at: string;
  meal_type: MealType | null;
  raw_input: string | null;
  total_kcal: string | null;
  total_protein_g: string | null;
  total_carbs_g: string | null;
  total_fat_g: string | null;
  source: string;
  notes: string | null;
  items: MealItem[];
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface MealCreate {
  eaten_at?: string;
  meal_type?: MealType;
  raw_input?: string;
  notes?: string;
  items: MealItemInput[];
}

// --- Chat ---

export type ChatMode = 'text' | 'voice';
export type ChatRole = 'system' | 'user' | 'assistant' | 'tool';

export interface ChatConversation {
  id: string;
  title: string | null;
  mode: ChatMode;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string | null;
  tool_name: string | null;
  tool_args: Record<string, unknown> | null;
  tool_result: Record<string, unknown> | null;
  model: string | null;
  created_at: string;
}

export interface ChatConversationDetail extends ChatConversation {
  messages: ChatMessage[];
}

// --- Parse ---

export interface ParsedSet {
  set_index: number;
  reps: number | null;
  weight_kg: string | null;
  rpe: string | null;
  is_warmup: boolean;
}

export interface ParsedExercise {
  matched_exercise_id: string | null;
  name: string;
  sets: ParsedSet[];
}

export interface ParsedWorkout {
  exercises: ParsedExercise[];
  notes: string | null;
  raw: string;
}

export interface ParsedMealItem {
  name: string;
  serving_g: string | null;
  kcal: string | null;
  protein_g: string | null;
  carbs_g: string | null;
  fat_g: string | null;
  confidence: string | null;
}

export interface ParsedMeal {
  items: ParsedMealItem[];
  raw: string;
}
