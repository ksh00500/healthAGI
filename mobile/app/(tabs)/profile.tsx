import { useEffect, useState } from 'react';
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { getProfile, updateProfile } from '@/api/endpoints';
import { useAuth } from '@/features/auth/store';
import type { Profile } from '@/api/types';

export default function ProfileScreen() {
  const user = useAuth((s) => s.user);
  const logout = useAuth((s) => s.logout);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [heightCm, setHeightCm] = useState('');
  const [goals, setGoals] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void getProfile()
      .then((p) => {
        setProfile(p);
        setDisplayName(p.display_name ?? '');
        setHeightCm(p.height_cm ?? '');
        setGoals(p.goals ?? '');
      })
      .catch(() => Alert.alert('프로필 불러오기 실패', '서버 연결 확인'));
  }, []);

  const onSave = async () => {
    setSaving(true);
    try {
      const updated = await updateProfile({
        display_name: displayName || null,
        height_cm: (heightCm || null) as Profile['height_cm'],
        goals: goals || null,
      });
      setProfile(updated);
      Alert.alert('저장됨');
    } catch {
      Alert.alert('저장 실패');
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.root} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.email}>{user?.email}</Text>

        <Text style={styles.label}>표시 이름</Text>
        <TextInput
          style={styles.input}
          value={displayName}
          onChangeText={setDisplayName}
          placeholderTextColor="#666"
          placeholder="예: 홍길동"
        />

        <Text style={styles.label}>키 (cm)</Text>
        <TextInput
          style={styles.input}
          value={heightCm}
          onChangeText={setHeightCm}
          placeholderTextColor="#666"
          placeholder="예: 178"
          keyboardType="decimal-pad"
        />

        <Text style={styles.label}>목표</Text>
        <TextInput
          style={[styles.input, styles.multiline]}
          value={goals}
          onChangeText={setGoals}
          placeholderTextColor="#666"
          placeholder="예: 근비대 + 체지방 감량"
          multiline
        />

        <Pressable style={[styles.btn, saving && { opacity: 0.5 }]} onPress={onSave} disabled={saving}>
          <Text style={styles.btnText}>{saving ? '저장 중…' : '저장'}</Text>
        </Pressable>

        {profile ? (
          <View style={styles.meta}>
            <Text style={styles.metaText}>로케일: {profile.locale}</Text>
            <Text style={styles.metaText}>타임존: {profile.timezone}</Text>
          </View>
        ) : null}

        <Pressable style={styles.logout} onPress={logout}>
          <Text style={styles.logoutText}>로그아웃</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0b0d10' },
  container: { padding: 20 },
  email: { color: '#fff', fontSize: 18, fontWeight: '600', marginBottom: 16 },
  label: { color: '#9aa1a8', fontSize: 13, marginBottom: 6, marginTop: 12 },
  input: {
    backgroundColor: '#16191e',
    color: '#fff',
    borderRadius: 10,
    padding: 14,
    fontSize: 15,
  },
  multiline: { minHeight: 80, textAlignVertical: 'top' },
  btn: { backgroundColor: '#3b82f6', borderRadius: 10, padding: 14, marginTop: 20, alignItems: 'center' },
  btnText: { color: '#fff', fontWeight: '600' },
  meta: { marginTop: 24, padding: 12, backgroundColor: '#16191e', borderRadius: 10 },
  metaText: { color: '#9aa1a8', fontSize: 12, marginVertical: 2 },
  logout: { marginTop: 24, padding: 12, alignItems: 'center' },
  logoutText: { color: '#ef4444', fontSize: 14 },
});
