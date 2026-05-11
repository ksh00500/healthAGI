import { useEffect, useState } from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
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
            onStart={() => start(item.group.id)}
            onStop={() => item.timer && stop(item.timer.id)}
          />
        )}
        ItemSeparatorComponent={() => <View style={styles.sep} />}
      />
    </SafeAreaView>
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
});
