import { apiRequest, setTokens } from '@/api/client';
import type {
  BodyMetric,
  BodyMetricCreate,
  ChatConversation,
  ChatConversationDetail,
  Exercise,
  Me,
  Meal,
  MealCreate,
  MuscleGroup,
  ParsedMeal,
  ParsedWorkout,
  Profile,
  Recommendation,
  SuggestResponse,
  Timer,
  TimerCreate,
  TokenPair,
  WorkoutSession,
  WorkoutSessionCreate,
} from '@/api/types';

export async function register(email: string, password: string): Promise<TokenPair> {
  const t = await apiRequest<TokenPair>('/auth/register', {
    method: 'POST',
    body: { email, password },
    auth: false,
  });
  await setTokens(t.access_token, t.refresh_token);
  return t;
}

export async function login(email: string, password: string): Promise<TokenPair> {
  const t = await apiRequest<TokenPair>('/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  });
  await setTokens(t.access_token, t.refresh_token);
  return t;
}

export function getMe(): Promise<Me> {
  return apiRequest<Me>('/auth/me');
}

export function getProfile(): Promise<Profile> {
  return apiRequest<Profile>('/profile');
}

export function updateProfile(body: Partial<Profile>): Promise<Profile> {
  return apiRequest<Profile>('/profile', { method: 'PUT', body });
}

export function listMuscleGroups(): Promise<MuscleGroup[]> {
  return apiRequest<MuscleGroup[]>('/muscle-groups', { auth: false });
}

export function listTimers(since?: string): Promise<Timer[]> {
  return apiRequest<Timer[]>('/timers', { query: { since, include_deleted: true } });
}

export function listCurrentTimers(): Promise<Timer[]> {
  return apiRequest<Timer[]>('/timers/current');
}

export function createTimer(body: TimerCreate): Promise<Timer> {
  return apiRequest<Timer>('/timers', { method: 'POST', body });
}

export function deleteTimer(id: string): Promise<void> {
  return apiRequest<void>(`/timers/${id}`, { method: 'DELETE' });
}

// --- Exercises ---

export function searchExercises(q?: string): Promise<Exercise[]> {
  return apiRequest<Exercise[]>('/exercises', { query: { q } });
}

// --- Workouts ---

export function listWorkoutSessions(params?: {
  day?: string;
  since?: string;
}): Promise<WorkoutSession[]> {
  return apiRequest<WorkoutSession[]>('/workouts/sessions', { query: params });
}

export function createWorkoutSession(
  body: WorkoutSessionCreate,
): Promise<WorkoutSession> {
  return apiRequest<WorkoutSession>('/workouts/sessions', {
    method: 'POST',
    body,
  });
}

export function deleteWorkoutSession(id: string): Promise<void> {
  return apiRequest<void>(`/workouts/sessions/${id}`, { method: 'DELETE' });
}

// --- Meals ---

export function listMeals(params?: { day?: string; since?: string }): Promise<Meal[]> {
  return apiRequest<Meal[]>('/meals', { query: params });
}

export function createMeal(body: MealCreate): Promise<Meal> {
  return apiRequest<Meal>('/meals', { method: 'POST', body });
}

export function deleteMeal(id: string): Promise<void> {
  return apiRequest<void>(`/meals/${id}`, { method: 'DELETE' });
}

// --- Body metrics ---

export function listBodyMetrics(): Promise<BodyMetric[]> {
  return apiRequest<BodyMetric[]>('/profile/body-metrics');
}

export function createBodyMetric(body: BodyMetricCreate): Promise<BodyMetric> {
  return apiRequest<BodyMetric>('/profile/body-metrics', { method: 'POST', body });
}

// --- Chat ---

export function listConversations(): Promise<ChatConversation[]> {
  return apiRequest<ChatConversation[]>('/chat/conversations');
}

export function createConversation(title?: string): Promise<ChatConversation> {
  return apiRequest<ChatConversation>('/chat/conversations', {
    method: 'POST',
    body: { title: title ?? null, mode: 'text' },
  });
}

export function getConversation(id: string): Promise<ChatConversationDetail> {
  return apiRequest<ChatConversationDetail>(`/chat/conversations/${id}`);
}

export function deleteConversation(id: string): Promise<void> {
  return apiRequest<void>(`/chat/conversations/${id}`, { method: 'DELETE' });
}

// --- Parse ---

export function parseWorkoutText(text: string): Promise<ParsedWorkout> {
  return apiRequest<ParsedWorkout>('/workouts/parse', { method: 'POST', body: { text } });
}

export function parseMealText(text: string): Promise<ParsedMeal> {
  return apiRequest<ParsedMeal>('/meals/parse', { method: 'POST', body: { text } });
}

// --- Recommendations ---

export function listTodayRecommendations(): Promise<Recommendation[]> {
  return apiRequest<Recommendation[]>('/recommendations/today');
}

export function generateRecommendations(force = false): Promise<Recommendation[]> {
  return apiRequest<Recommendation[]>('/recommendations/generate', {
    method: 'POST',
    body: { force },
  });
}

export function suggestRecoveryForSession(sessionId: string): Promise<SuggestResponse> {
  return apiRequest<SuggestResponse>('/timers/suggest', {
    method: 'POST',
    body: { session_id: sessionId },
  });
}
