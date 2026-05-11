import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import {
  createBodyMetric,
  generateRecommendations,
  listBodyMetrics,
  listMeals,
  listTodayRecommendations,
  listWorkoutSessions,
} from '@/api/endpoints';
import type { BodyMetric, Meal, Recommendation, WorkoutSession } from '@/api/types';
import { formatRemaining, timerProgress, useTimers } from '@/features/timers/store';
import { isoDay, sessionVolumeKg } from '@/features/workouts/helpers';

export default function TodayScreen() {
  const { timers, muscleGroups, loadFromLocal, sync } = useTimers();
  const [sessions, setSessions] = useState<WorkoutSession[]>([]);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [latestMetric, setLatestMetric] = useState<BodyMetric | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [recsLoading, setRecsLoading] = useState(false);
  const [weight, setWeight] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [tick, setTick] = useState(0);

  const refresh = useCallback(async () => {
    const day = isoDay();
    const [s, m, metrics, r] = await Promise.allSettled([
      listWorkoutSessions({ day }),
      listMeals({ day }),
      listBodyMetrics(),
      listTodayRecommendations(),
    ]);
    if (s.status === 'fulfilled') setSessions(s.value);
    if (m.status === 'fulfilled') setMeals(m.value);
    if (metrics.status === 'fulfilled') setLatestMetric(metrics.value[0] ?? null);
    if (r.status === 'fulfilled') setRecs(r.value);
  }, []);

  const onGenerateRecs = async (force = false) => {
    setRecsLoading(true);
    try {
      const next = await generateRecommendations(force);
      setRecs(next);
    } catch (e) {
      Alert.alert('추천 생성 실패', String(e));
    } finally {
      setRecsLoading(false);
    }
  };

  const onAskWhy = (rec: Recommendation) => {
    const prefill = `"${rec.title}" 이 추천에 대해 더 자세히 설명해줘. 근거: ${
      rec.rationale ?? rec.body
    }`;
    router.push({ pathname: '/(tabs)/ai', params: { prefill } });
  };

  useEffect(() => {
    void loadFromLocal().then(() => sync()).then(refresh);
  }, [loadFromLocal, sync, refresh]);

  useEffect(() => {
    const id = setInterval(() => setTick((n) => n + 1), 30_000); // refresh every 30s
    return () => clearInterval(id);
  }, []);

  void tick; // silence unused if tick is used only to trigger re-renders below indirectly

  const onPullRefresh = async () => {
    setRefreshing(true);
    await Promise.allSettled([sync(), refresh()]);
    setRefreshing(false);
  };

  const activeTimers = timers.filter((t) => !t.deleted_at);
  const totalKcal = meals.reduce((a, m) => a + (m.total_kcal ? Number(m.total_kcal) : 0), 0);
  const totalProtein = meals.reduce((a, m) => a + (m.total_protein_g ? Number(m.total_protein_g) : 0), 0);
  const totalVolume = sessions.reduce((a, s) => a + sessionVolumeKg(s), 0);

  const muscleName = (id: string): string =>
    muscleGroups.find((g) => g.id === id)?.display_name_ko ?? id;

  const onSubmitWeight = async () => {
    if (!weight.trim()) return;
    try {
      const created = await createBodyMetric({
        measured_at: new Date().toISOString(),
        weight_kg: weight.trim(),
      });
      setLatestMetric(created);
      setWeight('');
    } catch {
      Alert.alert('저장 실패');
    }
  };

  return (
    <SafeAreaView style={styles.root} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onPullRefresh} tintColor="#fff" />
        }
      >
        <Text style={styles.date}>
          {new Date().toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'long',
          })}
        </Text>

        <View style={styles.recHeader}>
          <Text style={styles.recHeading}>오늘의 AI 추천</Text>
          <Pressable
            onPress={() => onGenerateRecs(recs.length > 0)}
            disabled={recsLoading}
            style={[styles.recRefresh, recsLoading && { opacity: 0.5 }]}
          >
            {recsLoading ? (
              <ActivityIndicator size="small" color="#a78bfa" />
            ) : (
              <Text style={styles.recRefreshText}>
                {recs.length > 0 ? '새로고침' : '생성하기'}
              </Text>
            )}
          </Pressable>
        </View>
        {recs.length === 0 ? (
          <View style={styles.card}>
            <Text style={styles.dim}>
              AI 추천 카드가 아직 없어요. "생성하기"를 눌러 오늘의 추천을 받아보세요.
            </Text>
          </View>
        ) : (
          recs.map((r) => (
            <View key={r.id} style={[styles.card, styles.recCard]}>
              <Text style={styles.recKind}>{recKindLabel(r.kind)}</Text>
              <Text style={styles.recTitle}>{r.title}</Text>
              <Text style={styles.recBody}>{r.body}</Text>
              <Pressable style={styles.whyBtn} onPress={() => onAskWhy(r)}>
                <Text style={styles.whyBtnText}>왜? →</Text>
              </Pressable>
            </View>
          ))
        )}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>회복 중인 부위</Text>
          {activeTimers.length === 0 ? (
            <Text style={styles.dim}>모든 부위 운동 가능</Text>
          ) : (
            activeTimers.map((t) => {
              const p = timerProgress(t);
              if (p.remainingMs <= 0) return null;
              return (
                <View key={t.id} style={styles.row}>
                  <Text style={styles.rowLabel}>{muscleName(t.muscle_group_id)}</Text>
                  <Text style={styles.rowValue}>{formatRemaining(p.remainingMs)}</Text>
                </View>
              );
            })
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>오늘의 운동</Text>
          {sessions.length === 0 ? (
            <Text style={styles.dim}>아직 기록 없음 — Log 탭에서 추가</Text>
          ) : (
            <>
              {sessions.map((s) => (
                <View key={s.id} style={styles.row}>
                  <Text style={styles.rowLabel}>
                    {new Date(s.started_at).toLocaleTimeString('ko-KR', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}{' '}
                    · {s.sets.length}세트
                  </Text>
                  <Text style={styles.rowValue}>{sessionVolumeKg(s).toFixed(0)}kg</Text>
                </View>
              ))}
              <View style={[styles.row, styles.totalRow]}>
                <Text style={styles.rowLabel}>합계 볼륨</Text>
                <Text style={styles.rowValueStrong}>{totalVolume.toFixed(0)}kg</Text>
              </View>
            </>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>오늘의 식단</Text>
          {meals.length === 0 ? (
            <Text style={styles.dim}>아직 기록 없음 — Log 탭에서 추가</Text>
          ) : (
            <View style={styles.macroRow}>
              <Macro label="kcal" value={totalKcal.toFixed(0)} />
              <Macro label="단백질" value={`${totalProtein.toFixed(0)}g`} />
              <Macro label="식단 수" value={String(meals.length)} />
            </View>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>오늘 체중</Text>
          {latestMetric?.weight_kg ? (
            <Text style={styles.dim}>
              최근 기록:{' '}
              {new Date(latestMetric.measured_at).toLocaleDateString('ko-KR')} ·{' '}
              {Number(latestMetric.weight_kg).toFixed(1)} kg
            </Text>
          ) : (
            <Text style={styles.dim}>최근 기록 없음</Text>
          )}
          <View style={styles.weightRow}>
            <TextInput
              style={styles.weightInput}
              placeholder="예: 76.4"
              placeholderTextColor="#666"
              keyboardType="decimal-pad"
              value={weight}
              onChangeText={setWeight}
            />
            <Pressable style={styles.weightBtn} onPress={onSubmitWeight}>
              <Text style={styles.weightBtnText}>kg 기록</Text>
            </Pressable>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function recKindLabel(kind: Recommendation['kind']): string {
  switch (kind) {
    case 'workout_split':
      return '🏋️ 운동 추천';
    case 'nutrition_focus':
      return '🥗 영양 포커스';
    case 'recovery_check':
      return '😴 회복 점검';
  }
}

function Macro({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.macroCell}>
      <Text style={styles.macroValue}>{value}</Text>
      <Text style={styles.macroLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0b0d10' },
  scroll: { padding: 16, paddingBottom: 40 },
  date: { color: '#9aa1a8', fontSize: 13, marginBottom: 12 },
  recHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  recHeading: { color: '#fff', fontSize: 17, fontWeight: '700' },
  recRefresh: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#1f1633',
  },
  recRefreshText: { color: '#a78bfa', fontSize: 12, fontWeight: '600' },
  recCard: {
    backgroundColor: '#1a1330',
    borderLeftColor: '#a78bfa',
    borderLeftWidth: 3,
  },
  recKind: { color: '#a78bfa', fontSize: 12, fontWeight: '700', marginBottom: 4 },
  recTitle: { color: '#fff', fontSize: 16, fontWeight: '700', marginBottom: 4 },
  recBody: { color: '#cbd5e1', fontSize: 14, lineHeight: 20 },
  whyBtn: { alignSelf: 'flex-start', marginTop: 8, paddingVertical: 4 },
  whyBtnText: { color: '#a78bfa', fontSize: 13, fontWeight: '600' },
  card: {
    backgroundColor: '#16191e',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  cardTitle: { color: '#fff', fontSize: 14, fontWeight: '700', marginBottom: 10 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  totalRow: { marginTop: 6, borderTopWidth: 1, borderTopColor: '#1f242c', paddingTop: 10 },
  rowLabel: { color: '#fff', fontSize: 14 },
  rowValue: { color: '#fbbf24', fontSize: 14, fontWeight: '500' },
  rowValueStrong: { color: '#fff', fontSize: 14, fontWeight: '700' },
  dim: { color: '#9aa1a8', fontSize: 13 },
  macroRow: { flexDirection: 'row', justifyContent: 'space-between' },
  macroCell: { alignItems: 'center', flex: 1 },
  macroValue: { color: '#fff', fontSize: 18, fontWeight: '700' },
  macroLabel: { color: '#9aa1a8', fontSize: 11, marginTop: 2 },
  weightRow: { flexDirection: 'row', gap: 8, marginTop: 10 },
  weightInput: {
    flex: 1,
    backgroundColor: '#0b0d10',
    color: '#fff',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#1f242c',
    fontSize: 15,
  },
  weightBtn: {
    backgroundColor: '#3b82f6',
    borderRadius: 10,
    paddingHorizontal: 16,
    justifyContent: 'center',
  },
  weightBtnText: { color: '#fff', fontWeight: '600' },
});
