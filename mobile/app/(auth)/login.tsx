import { Link } from 'expo-router';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuth } from '@/features/auth/store';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const login = useAuth((s) => s.login);
  const error = useAuth((s) => s.error);

  const onSubmit = async () => {
    setSubmitting(true);
    try {
      await login(email.trim(), password);
    } catch {
      // store handles error text
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.root}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.container}
      >
        <Text style={styles.title}>healthAGI</Text>
        <Text style={styles.subtitle}>로그인</Text>

        <TextInput
          style={styles.input}
          placeholder="이메일"
          placeholderTextColor="#666"
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          style={styles.input}
          placeholder="비밀번호"
          placeholderTextColor="#666"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Pressable
          style={[styles.button, submitting && styles.buttonDisabled]}
          onPress={onSubmit}
          disabled={submitting}
        >
          <Text style={styles.buttonText}>{submitting ? '로그인 중…' : '로그인'}</Text>
        </Pressable>

        <Link href="/(auth)/register" style={styles.link}>
          <Text style={styles.linkText}>계정 만들기</Text>
        </Link>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0b0d10' },
  container: { flex: 1, padding: 24, justifyContent: 'center' },
  title: { color: '#fff', fontSize: 32, fontWeight: '700', marginBottom: 4 },
  subtitle: { color: '#9aa1a8', fontSize: 16, marginBottom: 32 },
  input: {
    backgroundColor: '#16191e',
    color: '#fff',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    marginBottom: 12,
  },
  button: {
    backgroundColor: '#3b82f6',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 16 },
  link: { marginTop: 20, alignSelf: 'center' },
  linkText: { color: '#9aa1a8', fontSize: 14 },
  error: { color: '#ef4444', marginVertical: 8 },
});
