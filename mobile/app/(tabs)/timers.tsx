import { useEffect, useState } from 'react';
import {
  Alert,
  FlatList,
  Modal,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { formatRemaining, timerProgress, useTimers } from '@/features/timers/store';
import type { LocalTimer } from '@/db/timers';
import type { MuscleGroup } from '@/api/types';

interface Row {
  group: MuscleGroup;
  timer: LocalTimer | null;
}

export default function TimersScreen() {
  const { muscleGroups, timers, online, loadFromLocal, sync, start, stop } = useTimers();
  const [tick, setTick] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [picker, setPicker] = useState<MuscleGroup | null>(null);

  useEffect(() => {
    void loadFromLocal().then(() => sync());
  }, [loadFromLocal, sync]);

  useEffect(() => {
    const id = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const rows: Row[] = muscleGroups.map((group) => ({
    group,
    timer:
      timers.find((t) => t.muscle_group_id === group.id && !t.deleted_at) ?? null,
  }));

  const onRefresh = async () => {
    setRefreshing(true);
    await sync();
    setRefreshing(false);
  };

  const handleStart = async (group: MuscleGroup, hours: number) => {
    setPicker(null);
    const minutes = Math.max(1, Math.round(hours * 60));
    try {
      await start(group.id, minutes);
    } catch (e) {
      Alert.alert('타이머 시작 실패', String(e));
    }
  };

  return (
    <SafeAreaView style={styles.root} edges={['bottom']}>
      {!online ? (
        <View style={styles.offline}>
          <Text style={styles.offlineText}>오프라인 — 캐시된 데이터로 표시 중</Text>
        </View>
      ) : null}
      <FlatList
        data={rows}
        keyExtractor={(r) => r.group.id}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#fff" />}
        renderItem={({ item }) => (
          <TimerRow
            row={item}
            tick={tick}
            onStart={() => setPicker(item.group)}
            onStop={() => item.timer && stop(item.timer.id)}
          />
        )}
        ItemSeparatorComponent={() => <View style={styles.sep} />}
      />
      <DurationPickerModal
        group={picker}
        onCancel={() => setPicker(null)}
        onConfirm={handleStart}
      />
    </SafeAreaView>
  );
}

function DurationPickerModal({
  group,
  onCancel,
  onConfirm,
}: {
  group: MuscleGroup | null;
  onCancel: () => void;
  onConfirm: (group: MuscleGroup, hours: number) => void;
}) {
  const [custom, setCustom] = useState('');
  useEffect(() => {
    if (group) setCustom('');
  }, [group]);
  if (!group) return null;

  const presets = [
    { label: '24h', hours: 24 },
    { label: `기본 ${group.default_recovery_hours}h`, hours: group.default_recovery_hours },
    { label: '48h', hours: 48 },
    { label: '72h', hours: 72 },
  ];

  const submitCustom = () => {
    const v = Number(custom);
    if (!Number.isFinite(v) || v <= 0) {
      Alert.alert('잘못된 시간', '1 이상의 숫자를 입력하세요');
      return;
    }
    onConfirm(group, v);
  };

  return (
    <Modal visible transparent animationType="fade" onRequestClose={onCancel}>
      <Pressable style={styles.backdrop} onPress={onCancel}>
        <Pressable style={styles.sheet} onPress={() => undefined}>
          <Text style={styles.sheetTitle}>{group.display_name_ko} 회복 타이머</Text>
          <Text style={styles.sheetSub}>회복 시간을 선택하세요</Text>
          <View style={styles.presets}>
            {presets.map((p) => (
              <Pressable
                key={p.label}
                style={styles.presetBtn}
                onPress={() => onConfirm(group, p.hours)}
              >
                <Text style={styles.presetText}>{p.label}</Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.sheetSub}>또는 직접 입력 (시간 단위)</Text>
          <View style={styles.customRow}>
            <TextInput
              style={styles.customInput}
              value={custom}
              onChangeText={setCustom}
              keyboardType="decimal-pad"
              placeholder="예: 36"
              placeholderTextColor="#666"
            />
            <Pressable
              style={[styles.confirmBtn, !custom && { opacity: 0.4 }]}
              disabled={!custom}
              onPress={submitCustom}
            >
              <Text style={styles.confirmBtnText}>시작</Text>
            </Pressable>
          </View>
          <Pressable style={styles.cancelBtn} onPress={onCancel}>
            <Text style={styles.cancelBtnText}>취소</Text>
          </Pressable>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function TimerRow({
  row,
  tick: _tick,
  onStart,
  onStop,
}: {
  row: Row;
  tick: number;
  onStart: () => void;
  onStop: () => void;
}) {
  const { group, timer } = row;
  const active = timer && !timer.deleted_at;
  const progress = active ? timerProgress(timer!) : null;
  const expired = progress !== null && progress.remainingMs <= 0;

  return (
    <View style={styles.row}>
      <View style={styles.rowLeft}>
        <Text style={styles.muscle}>{group.display_name_ko}</Text>
        <Text style={styles.sub}>
          기본 회복: {group.default_recovery_hours}h
        </Text>
        {progress && !expired ? (
          <Text style={styles.remaining}>
            {formatRemaining(progress.remainingMs)} 남음
          </Text>
        ) : null}
        {expired ? <Text style={styles.ready}>준비 완료 ✓</Text> : null}
        {!active ? <Text style={styles.ready}>운동 가능</Text> : null}
      </View>
      {active && !expired ? (
        <Pressable style={[styles.btn, styles.btnStop]} onPress={onStop}>
          <Text style={styles.btnText}>취소</Text>
        </Pressable>
      ) : (
        <Pressable style={[styles.btn, styles.btnStart]} onPress={onStart}>
          <Text style={styles.btnText}>운동 완료</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0b0d10' },
  list: { padding: 16 },
  offline: {
    backgroundColor: '#7c2d12',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  offlineText: { color: '#fff', fontSize: 12, textAlign: 'center' },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#16191e',
    borderRadius: 12,
    padding: 16,
  },
  rowLeft: { flex: 1, marginRight: 12 },
  muscle: { color: '#fff', fontSize: 17, fontWeight: '600' },
  sub: { color: '#9aa1a8', fontSize: 12, marginTop: 2 },
  remaining: { color: '#fbbf24', fontSize: 15, fontWeight: '500', marginTop: 4 },
  ready: { color: '#22c55e', fontSize: 13, marginTop: 4 },
  sep: { height: 10 },
  btn: { paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10 },
  btnStart: { backgroundColor: '#3b82f6' },
  btnStop: { backgroundColor: '#374151' },
  btnText: { color: '#fff', fontWeight: '600', fontSize: 14 },
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: '#16191e',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    gap: 12,
  },
  sheetTitle: { color: '#fff', fontSize: 18, fontWeight: '700' },
  sheetSub: { color: '#9aa1a8', fontSize: 13 },
  presets: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  presetBtn: {
    backgroundColor: '#1f242c',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    flexGrow: 1,
    alignItems: 'center',
  },
  presetText: { color: '#fff', fontWeight: '600' },
  customRow: { flexDirection: 'row', gap: 8 },
  customInput: {
    flex: 1,
    backgroundColor: '#0b0d10',
    color: '#fff',
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    borderWidth: 1,
    borderColor: '#1f242c',
  },
  confirmBtn: {
    backgroundColor: '#3b82f6',
    borderRadius: 10,
    paddingHorizontal: 18,
    justifyContent: 'center',
  },
  confirmBtnText: { color: '#fff', fontWeight: '600' },
  cancelBtn: { padding: 12, alignItems: 'center' },
  cancelBtnText: { color: '#9aa1a8', fontWeight: '600' },
});
