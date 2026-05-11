import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { router } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';

import {
  createMeal,
  createWorkoutSession,
  deleteMeal,
  deleteWorkoutSession,
  listMeals,
  listWorkoutSessions,
  parseMealText,
  parseWorkoutText,
  searchExercises,
} from '@/api/endpoints';
import type {
  Exercise,
  Meal,
  MealItemInput,
  WorkoutSession,
  WorkoutSetInput,
} from '@/api/types';
import { isoDay, sessionVolumeKg } from '@/features/workouts/helpers';

type Tab = 'workout' | 'meal';

export default function LogScreen() {
  const [tab, setTab] = useState<Tab>('workout');
  return (
    <SafeAreaView style={styles.root} edges={['bottom']}>
      <View style={styles.segments}>
        <SegmentBtn label="운동" active={tab === 'workout'} onPress={() => setTab('workout')} />
        <SegmentBtn label="식단" active={tab === 'meal'} onPress={() => setTab('meal')} />
      </View>
      {tab === 'workout' ? <WorkoutPanel /> : <MealPanel />}
    </SafeAreaView>
  );
}

function SegmentBtn({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  return (
    <Pressable style={[styles.seg, active && styles.segActive]} onPress={onPress}>
      <Text style={[styles.segText, active && styles.segTextActive]}>{label}</Text>
    </Pressable>
  );
}

// ----------------- Workout panel -----------------

interface SetDraft {
  exercise: Exercise;
  reps: string;
  weight_kg: string;
  rpe: string;
  is_warmup: boolean;
}

function WorkoutPanel() {
  const [sessions, setSessions] = useState<WorkoutSession[]>([]);
  const [drafts, setDrafts] = useState<SetDraft[]>([]);
  const [picker, setPicker] = useState(false);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [aiInput, setAiInput] = useState('');
  const [aiBusy, setAiBusy] = useState(false);

  const refresh = async () => {
    try {
      const today = isoDay();
      const r = await listWorkoutSessions({ day: today });
      setSessions(r);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const addExercise = (ex: Exercise) => {
    setDrafts((cur) => [
      ...cur,
      { exercise: ex, reps: '', weight_kg: '', rpe: '', is_warmup: false },
    ]);
    setPicker(false);
  };

  const updateDraft = (idx: number, patch: Partial<SetDraft>) => {
    setDrafts((cur) => cur.map((d, i) => (i === idx ? { ...d, ...patch } : d)));
  };

  const removeDraft = (idx: number) => {
    setDrafts((cur) => cur.filter((_, i) => i !== idx));
  };

  const save = async () => {
    if (drafts.length === 0) {
      Alert.alert('빈 세션', '세트를 한 개 이상 추가하세요');
      return;
    }
    const grouped = new Map<string, number>();
    const setInputs: WorkoutSetInput[] = drafts.map((d) => {
      const ix = (grouped.get(d.exercise.id) ?? 0) + 1;
      grouped.set(d.exercise.id, ix);
      return {
        exercise_id: d.exercise.id,
        set_index: ix,
        reps: d.reps ? Number(d.reps) : undefined,
        weight_kg: d.weight_kg || undefined,
        rpe: d.rpe || undefined,
        is_warmup: d.is_warmup,
      };
    });
    setSaving(true);
    try {
      await createWorkoutSession({ notes: notes || undefined, sets: setInputs });
      setDrafts([]);
      setNotes('');
      await refresh();
    } catch {
      Alert.alert('저장 실패', '서버 연결 확인');
    } finally {
      setSaving(false);
    }
  };

  const onDeleteSession = async (id: string) => {
    try {
      await deleteWorkoutSession(id);
      await refresh();
    } catch {
      Alert.alert('삭제 실패');
    }
  };

  const onAiParse = async () => {
    if (!aiInput.trim()) return;
    setAiBusy(true);
    try {
      const parsed = await parseWorkoutText(aiInput.trim());
      const ex = parsed.exercises;
      if (ex.length === 0) {
        Alert.alert('파싱 결과 없음', '입력 텍스트에서 운동을 찾지 못했어요.');
        return;
      }
      // Resolve each parsed exercise → real Exercise object.
      const unresolved: string[] = [];
      const newDrafts: SetDraft[] = [];
      for (const e of ex) {
        let exercise: Exercise | null = null;
        if (e.matched_exercise_id) {
          const list = await searchExercises(e.name);
          exercise = list.find((x) => x.id === e.matched_exercise_id) ?? null;
        }
        if (!exercise) {
          unresolved.push(e.name);
          continue;
        }
        for (const s of e.sets) {
          newDrafts.push({
            exercise,
            reps: s.reps != null ? String(s.reps) : '',
            weight_kg: s.weight_kg ?? '',
            rpe: s.rpe ?? '',
            is_warmup: s.is_warmup,
          });
        }
      }
      if (newDrafts.length > 0) {
        setDrafts((cur) => [...cur, ...newDrafts]);
      }
      if (parsed.notes && !notes) setNotes(parsed.notes);
      setAiInput('');
      if (unresolved.length > 0) {
        Alert.alert(
          '일부 운동 매칭 실패',
          `다음 운동은 직접 추가해주세요:\n${unresolved.join(', ')}`,
        );
      }
    } catch (e) {
      Alert.alert('AI 파싱 실패', String(e));
    } finally {
      setAiBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.sectionTitle}>오늘의 세션</Text>
        {sessions.length === 0 ? (
          <Text style={styles.dim}>오늘 기록된 세션이 없어요.</Text>
        ) : (
          sessions.map((s) => (
            <View key={s.id} style={styles.card}>
              <View style={styles.cardRow}>
                <Text style={styles.cardTitle}>
                  {new Date(s.started_at).toLocaleTimeString('ko-KR', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}{' '}
                  · 세트 {s.sets.length}
                </Text>
                <Pressable onPress={() => onDeleteSession(s.id)}>
                  <Text style={styles.delete}>삭제</Text>
                </Pressable>
              </View>
              <Text style={styles.dim}>볼륨 {sessionVolumeKg(s).toFixed(0)}kg</Text>
              {s.notes ? <Text style={styles.cardNote}>{s.notes}</Text> : null}
            </View>
          ))
        )}

        <Text style={[styles.sectionTitle, { marginTop: 24 }]}>새 세션</Text>

        <View style={styles.aiBox}>
          <Text style={styles.aiTitle}>AI로 빠르게 입력</Text>
          <Text style={styles.dim}>예: "벤치 80kg 5,5,4 / 스쿼트 120 x 5 x 3"</Text>
          <TextInput
            style={[styles.input, { marginTop: 8 }]}
            placeholder="자유 텍스트 입력"
            placeholderTextColor="#666"
            value={aiInput}
            onChangeText={setAiInput}
            multiline
          />
          <Pressable
            style={[styles.aiBtn, (aiBusy || !aiInput.trim()) && { opacity: 0.5 }]}
            onPress={onAiParse}
            disabled={aiBusy || !aiInput.trim()}
          >
            <Text style={styles.aiBtnText}>{aiBusy ? '분석 중…' : '✨ AI 파싱'}</Text>
          </Pressable>
        </View>

        {drafts.map((d, i) => (
          <View key={`${d.exercise.id}-${i}`} style={styles.card}>
            <View style={styles.cardRow}>
              <Text style={styles.cardTitle}>
                {d.exercise.display_name_ko ?? d.exercise.canonical_name}
              </Text>
              <Pressable onPress={() => removeDraft(i)}>
                <Text style={styles.delete}>제거</Text>
              </Pressable>
            </View>
            <View style={styles.inputRow}>
              <NumberField
                label="reps"
                value={d.reps}
                onChangeText={(t) => updateDraft(i, { reps: t })}
              />
              <NumberField
                label="kg"
                value={d.weight_kg}
                onChangeText={(t) => updateDraft(i, { weight_kg: t })}
              />
              <NumberField
                label="RPE"
                value={d.rpe}
                onChangeText={(t) => updateDraft(i, { rpe: t })}
              />
            </View>
            <Pressable
              style={styles.warmupRow}
              onPress={() => updateDraft(i, { is_warmup: !d.is_warmup })}
            >
              <View style={[styles.checkbox, d.is_warmup && styles.checkboxOn]} />
              <Text style={styles.dim}>워밍업 세트</Text>
            </Pressable>
          </View>
        ))}

        <Pressable style={styles.outlineBtn} onPress={() => setPicker(true)}>
          <Text style={styles.outlineBtnText}>+ 운동 추가</Text>
        </Pressable>

        <TextInput
          style={[styles.input, styles.multiline]}
          placeholder="메모 (선택)"
          placeholderTextColor="#666"
          value={notes}
          onChangeText={setNotes}
          multiline
        />

        <Pressable
          style={[styles.primaryBtn, saving && { opacity: 0.5 }]}
          onPress={save}
          disabled={saving}
        >
          <Text style={styles.primaryBtnText}>{saving ? '저장 중…' : '세션 저장'}</Text>
        </Pressable>
      </ScrollView>

      <ExercisePicker visible={picker} onClose={() => setPicker(false)} onPick={addExercise} />
    </KeyboardAvoidingView>
  );
}

function NumberField({
  label,
  value,
  onChangeText,
}: {
  label: string;
  value: string;
  onChangeText: (t: string) => void;
}) {
  return (
    <View style={styles.numField}>
      <Text style={styles.numLabel}>{label}</Text>
      <TextInput
        style={styles.numInput}
        value={value}
        onChangeText={onChangeText}
        keyboardType="decimal-pad"
        placeholder="0"
        placeholderTextColor="#555"
      />
    </View>
  );
}

function ExercisePicker({
  visible,
  onClose,
  onPick,
}: {
  visible: boolean;
  onClose: () => void;
  onPick: (e: Exercise) => void;
}) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Exercise[]>([]);

  useEffect(() => {
    if (!visible) return;
    const handle = setTimeout(() => {
      searchExercises(q.trim() || undefined)
        .then(setResults)
        .catch(() => setResults([]));
    }, 200);
    return () => clearTimeout(handle);
  }, [q, visible]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>운동 선택</Text>
          <Pressable onPress={onClose}>
            <Text style={styles.delete}>닫기</Text>
          </Pressable>
        </View>
        <TextInput
          style={styles.input}
          placeholder="검색 (예: 벤치, squat, 풀업)"
          placeholderTextColor="#666"
          autoFocus
          value={q}
          onChangeText={setQ}
        />
        <FlatList
          data={results}
          keyExtractor={(e) => e.id}
          ItemSeparatorComponent={() => <View style={{ height: 1, backgroundColor: '#16191e' }} />}
          renderItem={({ item }) => (
            <Pressable style={styles.pickRow} onPress={() => onPick(item)}>
              <Text style={styles.pickTitle}>
                {item.display_name_ko ?? item.canonical_name}
              </Text>
              <Text style={styles.dim}>
                {item.primary_muscle_group_id ?? '-'}
                {item.equipment ? ` · ${item.equipment}` : ''}
              </Text>
            </Pressable>
          )}
          ListEmptyComponent={
            <Text style={[styles.dim, { padding: 16 }]}>결과 없음</Text>
          }
        />
      </SafeAreaView>
    </Modal>
  );
}

// ----------------- Meal panel -----------------

interface ItemDraft {
  name: string;
  serving_g: string;
  kcal: string;
  protein_g: string;
  carbs_g: string;
  fat_g: string;
}

function emptyItem(): ItemDraft {
  return { name: '', serving_g: '', kcal: '', protein_g: '', carbs_g: '', fat_g: '' };
}

function MealPanel() {
  const [meals, setMeals] = useState<Meal[]>([]);
  const [items, setItems] = useState<ItemDraft[]>([emptyItem()]);
  const [rawInput, setRawInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);

  const refresh = async () => {
    try {
      setMeals(await listMeals({ day: isoDay() }));
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const totals = useMemo(() => {
    const sum = (key: keyof Meal) =>
      meals.reduce((a, m) => a + (m[key] ? Number(m[key]) : 0), 0);
    return {
      kcal: sum('total_kcal'),
      protein: sum('total_protein_g'),
      carbs: sum('total_carbs_g'),
      fat: sum('total_fat_g'),
    };
  }, [meals]);

  const update = (i: number, patch: Partial<ItemDraft>) =>
    setItems((cur) => cur.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));

  const save = async () => {
    const cleaned: MealItemInput[] = items
      .filter((i) => i.name.trim().length > 0)
      .map((i) => ({
        name: i.name.trim(),
        serving_g: i.serving_g || undefined,
        kcal: i.kcal || undefined,
        protein_g: i.protein_g || undefined,
        carbs_g: i.carbs_g || undefined,
        fat_g: i.fat_g || undefined,
      }));
    if (cleaned.length === 0) {
      Alert.alert('빈 식단', '항목을 하나 이상 입력하세요');
      return;
    }
    setSaving(true);
    try {
      await createMeal({ raw_input: rawInput || undefined, items: cleaned });
      setItems([emptyItem()]);
      setRawInput('');
      await refresh();
    } catch {
      Alert.alert('저장 실패');
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async (id: string) => {
    try {
      await deleteMeal(id);
      await refresh();
    } catch {
      Alert.alert('삭제 실패');
    }
  };

  const onAiParse = async () => {
    if (!rawInput.trim()) return;
    setAiBusy(true);
    try {
      const parsed = await parseMealText(rawInput.trim());
      if (parsed.items.length === 0) {
        Alert.alert('파싱 결과 없음', '입력 텍스트에서 항목을 찾지 못했어요.');
        return;
      }
      const newItems: ItemDraft[] = parsed.items.map((it) => ({
        name: it.name,
        serving_g: it.serving_g ?? '',
        kcal: it.kcal ?? '',
        protein_g: it.protein_g ?? '',
        carbs_g: it.carbs_g ?? '',
        fat_g: it.fat_g ?? '',
      }));
      // Replace empty starter row, else append.
      setItems((cur) =>
        cur.length === 1 && !cur[0]!.name ? newItems : [...cur, ...newItems],
      );
    } catch (e) {
      Alert.alert('AI 파싱 실패', String(e));
    } finally {
      setAiBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.totals}>
          <Text style={styles.totalsTitle}>오늘 합계</Text>
          <View style={styles.totalsRow}>
            <TotalCell label="kcal" value={totals.kcal.toFixed(0)} />
            <TotalCell label="단백질" value={`${totals.protein.toFixed(0)}g`} />
            <TotalCell label="탄수" value={`${totals.carbs.toFixed(0)}g`} />
            <TotalCell label="지방" value={`${totals.fat.toFixed(0)}g`} />
          </View>
        </View>

        <Text style={styles.sectionTitle}>오늘의 식단</Text>
        {meals.length === 0 ? (
          <Text style={styles.dim}>아직 기록 없음</Text>
        ) : (
          meals.map((m) => (
            <View key={m.id} style={styles.card}>
              <View style={styles.cardRow}>
                <Text style={styles.cardTitle}>
                  {new Date(m.eaten_at).toLocaleTimeString('ko-KR', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}{' '}
                  · {m.total_kcal ? `${Number(m.total_kcal).toFixed(0)}kcal` : '-'}
                </Text>
                <Pressable onPress={() => onDelete(m.id)}>
                  <Text style={styles.delete}>삭제</Text>
                </Pressable>
              </View>
              {m.items.map((it) => (
                <Text key={it.id} style={styles.dim}>
                  · {it.name}
                  {it.serving_g ? ` ${it.serving_g}g` : ''}
                  {it.kcal ? ` (${Number(it.kcal).toFixed(0)}kcal)` : ''}
                </Text>
              ))}
            </View>
          ))
        )}

        <Text style={[styles.sectionTitle, { marginTop: 24 }]}>새 식단 기록</Text>

        <Pressable
          style={styles.photoBtn}
          onPress={() => router.push('/meal/photo')}
        >
          <Text style={styles.photoBtnText}>📷 사진으로 식단 추가</Text>
        </Pressable>

        <View style={styles.aiBox}>
          <Text style={styles.aiTitle}>AI로 빠르게 입력</Text>
          <Text style={styles.dim}>예: "닭가슴살 200g, 밥 1공기, 김치"</Text>
          <TextInput
            style={[styles.input, { marginTop: 8 }]}
            placeholder="자유 텍스트 입력"
            placeholderTextColor="#666"
            value={rawInput}
            onChangeText={setRawInput}
          />
          <Pressable
            style={[styles.aiBtn, (aiBusy || !rawInput.trim()) && { opacity: 0.5 }]}
            onPress={onAiParse}
            disabled={aiBusy || !rawInput.trim()}
          >
            <Text style={styles.aiBtnText}>{aiBusy ? '분석 중…' : '✨ AI 파싱'}</Text>
          </Pressable>
        </View>

        {items.map((it, i) => (
          <View key={i} style={styles.card}>
            <TextInput
              style={styles.input}
              placeholder={`항목 ${i + 1} 이름 (예: 닭가슴살)`}
              placeholderTextColor="#666"
              value={it.name}
              onChangeText={(t) => update(i, { name: t })}
            />
            <View style={styles.inputRow}>
              <NumberField label="g" value={it.serving_g} onChangeText={(t) => update(i, { serving_g: t })} />
              <NumberField label="kcal" value={it.kcal} onChangeText={(t) => update(i, { kcal: t })} />
            </View>
            <View style={styles.inputRow}>
              <NumberField label="단백" value={it.protein_g} onChangeText={(t) => update(i, { protein_g: t })} />
              <NumberField label="탄수" value={it.carbs_g} onChangeText={(t) => update(i, { carbs_g: t })} />
              <NumberField label="지방" value={it.fat_g} onChangeText={(t) => update(i, { fat_g: t })} />
            </View>
          </View>
        ))}

        <Pressable
          style={styles.outlineBtn}
          onPress={() => setItems((cur) => [...cur, emptyItem()])}
        >
          <Text style={styles.outlineBtnText}>+ 항목 추가</Text>
        </Pressable>

        <Pressable style={[styles.primaryBtn, saving && { opacity: 0.5 }]} onPress={save} disabled={saving}>
          <Text style={styles.primaryBtnText}>{saving ? '저장 중…' : '식단 저장'}</Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function TotalCell({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.totalCell}>
      <Text style={styles.totalValue}>{value}</Text>
      <Text style={styles.totalLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0b0d10' },
  scroll: { padding: 16, paddingBottom: 40 },
  segments: { flexDirection: 'row', padding: 12, gap: 8 },
  seg: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: '#16191e',
    alignItems: 'center',
  },
  segActive: { backgroundColor: '#3b82f6' },
  segText: { color: '#9aa1a8', fontWeight: '600' },
  segTextActive: { color: '#fff' },
  sectionTitle: { color: '#fff', fontSize: 16, fontWeight: '700', marginBottom: 10 },
  dim: { color: '#9aa1a8', fontSize: 13 },
  card: {
    backgroundColor: '#16191e',
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
  },
  cardRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  cardTitle: { color: '#fff', fontWeight: '600' },
  cardNote: { color: '#9aa1a8', fontSize: 12, marginTop: 4 },
  delete: { color: '#ef4444', fontSize: 13 },
  inputRow: { flexDirection: 'row', gap: 8, marginTop: 6 },
  input: {
    backgroundColor: '#0b0d10',
    color: '#fff',
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#1f242c',
  },
  multiline: { minHeight: 60, textAlignVertical: 'top' },
  numField: { flex: 1 },
  numLabel: { color: '#9aa1a8', fontSize: 11, marginBottom: 2 },
  numInput: {
    backgroundColor: '#0b0d10',
    color: '#fff',
    borderRadius: 8,
    padding: 10,
    fontSize: 15,
    borderWidth: 1,
    borderColor: '#1f242c',
  },
  warmupRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8 },
  checkbox: {
    width: 18,
    height: 18,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#374151',
    backgroundColor: 'transparent',
  },
  checkboxOn: { backgroundColor: '#3b82f6', borderColor: '#3b82f6' },
  outlineBtn: {
    borderColor: '#374151',
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
    marginTop: 4,
  },
  outlineBtnText: { color: '#9aa1a8', fontWeight: '600' },
  primaryBtn: {
    backgroundColor: '#3b82f6',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginTop: 16,
  },
  primaryBtnText: { color: '#fff', fontWeight: '600' },
  totals: {
    backgroundColor: '#16191e',
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
  },
  totalsTitle: { color: '#9aa1a8', fontSize: 12, marginBottom: 8 },
  totalsRow: { flexDirection: 'row', justifyContent: 'space-between' },
  totalCell: { alignItems: 'center', flex: 1 },
  totalValue: { color: '#fff', fontSize: 18, fontWeight: '700' },
  totalLabel: { color: '#9aa1a8', fontSize: 11 },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  modalTitle: { color: '#fff', fontSize: 18, fontWeight: '700' },
  aiBox: {
    backgroundColor: '#0f1419',
    borderColor: '#1f2937',
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginBottom: 14,
  },
  aiTitle: { color: '#a78bfa', fontWeight: '700', marginBottom: 4 },
  aiBtn: {
    backgroundColor: '#7c3aed',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  aiBtnText: { color: '#fff', fontWeight: '600' },
  photoBtn: {
    backgroundColor: '#0ea5e9',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginBottom: 12,
  },
  photoBtnText: { color: '#fff', fontWeight: '600' },
  pickRow: { padding: 14, paddingHorizontal: 16 },
  pickTitle: { color: '#fff', fontSize: 15, fontWeight: '600' },
});
