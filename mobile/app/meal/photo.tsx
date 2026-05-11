import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImageManipulator from 'expo-image-manipulator';
import * as ImagePicker from 'expo-image-picker';
import { router, Stack } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { createMeal } from '@/api/endpoints';
import { analyzePhoto } from '@/api/photo';
import type { MealItemInput, PhotoAnalyzeItem } from '@/api/types';

type Step = 'camera' | 'analyzing' | 'review';

export default function PhotoMealScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView | null>(null);
  const [step, setStep] = useState<Step>('camera');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [items, setItems] = useState<PhotoAnalyzeItem[]>([]);
  const [storageKey, setStorageKey] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (permission && !permission.granted && permission.canAskAgain) {
      requestPermission();
    }
  }, [permission, requestPermission]);

  const takeShot = async () => {
    if (!cameraRef.current) return;
    try {
      const shot = await cameraRef.current.takePictureAsync({
        quality: 0.7,
        skipProcessing: false,
      });
      if (!shot?.uri) return;
      await runAnalyze(shot.uri);
    } catch (e) {
      Alert.alert('촬영 실패', String(e));
    }
  };

  const pickFromGallery = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.8,
      allowsMultipleSelection: false,
    });
    if (result.canceled || result.assets.length === 0) return;
    const a = result.assets[0]!;
    await runAnalyze(a.uri);
  };

  const runAnalyze = async (sourceUri: string) => {
    setStep('analyzing');
    try {
      // Compress to ~1024px JPEG q0.7 before upload (architecture spec).
      const manipulated = await ImageManipulator.manipulateAsync(
        sourceUri,
        [{ resize: { width: 1024 } }],
        { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG },
      );
      setImageUri(manipulated.uri);
      const res = await analyzePhoto({
        uri: manipulated.uri,
        mime: 'image/jpeg',
        fileName: 'meal.jpg',
      });
      setItems(res.items);
      setStorageKey(res.storage_key);
      setStep('review');
    } catch (e) {
      Alert.alert('분석 실패', String(e));
      setStep('camera');
    }
  };

  const updateItem = (i: number, patch: Partial<PhotoAnalyzeItem>) => {
    setItems((cur) => cur.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));
  };

  const removeItem = (i: number) => {
    setItems((cur) => cur.filter((_, idx) => idx !== i));
  };

  const onSave = async () => {
    if (!storageKey) return;
    if (items.length === 0) {
      Alert.alert('빈 식단', '항목을 하나 이상 남겨주세요');
      return;
    }
    const payload: MealItemInput[] = items.map((it) => ({
      name: it.name,
      serving_g: it.serving_g ?? undefined,
      kcal: it.kcal ?? undefined,
      protein_g: it.protein_g ?? undefined,
      carbs_g: it.carbs_g ?? undefined,
      fat_g: it.fat_g ?? undefined,
    }));
    setSaving(true);
    try {
      await createMeal({ items: payload, photo_storage_key: storageKey });
      router.back();
    } catch (e) {
      Alert.alert('저장 실패', String(e));
    } finally {
      setSaving(false);
    }
  };

  if (!permission) {
    return <View style={styles.root} />;
  }
  if (!permission.granted) {
    return (
      <SafeAreaView style={styles.root}>
        <Stack.Screen options={{ title: '사진 식단', headerStyle: { backgroundColor: '#0b0d10' }, headerTintColor: '#fff' }} />
        <View style={styles.center}>
          <Text style={styles.dim}>카메라 권한이 필요해요.</Text>
          <Pressable style={styles.primaryBtn} onPress={requestPermission}>
            <Text style={styles.primaryBtnText}>권한 요청</Text>
          </Pressable>
          <Pressable style={styles.outlineBtn} onPress={pickFromGallery}>
            <Text style={styles.outlineBtnText}>갤러리에서 선택</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  if (step === 'camera') {
    return (
      <View style={styles.root}>
        <Stack.Screen options={{ title: '사진 식단', headerStyle: { backgroundColor: '#0b0d10' }, headerTintColor: '#fff' }} />
        <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" />
        <SafeAreaView style={styles.cameraOverlay} edges={['bottom']}>
          <View style={styles.shutterRow}>
            <Pressable style={styles.smallBtn} onPress={pickFromGallery}>
              <Text style={styles.smallBtnText}>갤러리</Text>
            </Pressable>
            <Pressable style={styles.shutter} onPress={takeShot}>
              <View style={styles.shutterInner} />
            </Pressable>
            <View style={styles.smallBtn} />
          </View>
        </SafeAreaView>
      </View>
    );
  }

  if (step === 'analyzing') {
    return (
      <SafeAreaView style={styles.root}>
        <Stack.Screen options={{ title: '분석 중', headerStyle: { backgroundColor: '#0b0d10' }, headerTintColor: '#fff' }} />
        <View style={styles.center}>
          {imageUri ? <Image source={{ uri: imageUri }} style={styles.preview} /> : null}
          <ActivityIndicator size="large" color="#a78bfa" style={{ marginTop: 16 }} />
          <Text style={[styles.dim, { marginTop: 8 }]}>AI가 음식을 분석 중…</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.root} edges={['bottom']}>
      <Stack.Screen options={{ title: '결과 확인', headerStyle: { backgroundColor: '#0b0d10' }, headerTintColor: '#fff' }} />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView contentContainerStyle={styles.scroll}>
          {imageUri ? <Image source={{ uri: imageUri }} style={styles.previewLarge} /> : null}
          <Text style={styles.sectionTitle}>AI가 추정한 항목 (편집 가능)</Text>
          {items.length === 0 ? (
            <Text style={styles.dim}>인식된 항목이 없어요. 다시 촬영해주세요.</Text>
          ) : (
            items.map((it, i) => (
              <View key={i} style={styles.card}>
                <View style={styles.cardRow}>
                  <TextInput
                    style={[styles.input, { flex: 1 }]}
                    value={it.name}
                    onChangeText={(t) => updateItem(i, { name: t })}
                    placeholder="이름"
                    placeholderTextColor="#666"
                  />
                  <Pressable onPress={() => removeItem(i)} style={{ paddingHorizontal: 10 }}>
                    <Text style={styles.delete}>제거</Text>
                  </Pressable>
                </View>
                <View style={styles.inputRow}>
                  <NumField label="g" value={it.serving_g} onChange={(v) => updateItem(i, { serving_g: v })} />
                  <NumField label="kcal" value={it.kcal} onChange={(v) => updateItem(i, { kcal: v })} />
                </View>
                <View style={styles.inputRow}>
                  <NumField label="단백" value={it.protein_g} onChange={(v) => updateItem(i, { protein_g: v })} />
                  <NumField label="탄수" value={it.carbs_g} onChange={(v) => updateItem(i, { carbs_g: v })} />
                  <NumField label="지방" value={it.fat_g} onChange={(v) => updateItem(i, { fat_g: v })} />
                </View>
                {it.confidence ? (
                  <Text style={styles.confidence}>신뢰도 {Math.round(Number(it.confidence) * 100)}%</Text>
                ) : null}
              </View>
            ))
          )}

          <Pressable style={styles.outlineBtn} onPress={() => setStep('camera')}>
            <Text style={styles.outlineBtnText}>↺ 다시 촬영</Text>
          </Pressable>
          <Pressable
            style={[styles.primaryBtn, saving && { opacity: 0.5 }]}
            onPress={onSave}
            disabled={saving}
          >
            <Text style={styles.primaryBtnText}>{saving ? '저장 중…' : '식단 저장'}</Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function NumField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string | null;
  onChange: (v: string | null) => void;
}) {
  return (
    <View style={{ flex: 1 }}>
      <Text style={styles.numLabel}>{label}</Text>
      <TextInput
        style={styles.numInput}
        value={value ?? ''}
        onChangeText={(t) => onChange(t || null)}
        keyboardType="decimal-pad"
        placeholder="0"
        placeholderTextColor="#555"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0b0d10' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 12 },
  dim: { color: '#9aa1a8', fontSize: 14, textAlign: 'center' },
  cameraOverlay: { flex: 1, justifyContent: 'flex-end' },
  shutterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 32,
    paddingBottom: 24,
  },
  shutter: {
    width: 78,
    height: 78,
    borderRadius: 39,
    borderColor: '#fff',
    borderWidth: 4,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.2)',
  },
  shutterInner: { width: 58, height: 58, borderRadius: 29, backgroundColor: '#fff' },
  smallBtn: {
    width: 70,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  smallBtnText: { color: '#fff', fontWeight: '600' },
  scroll: { padding: 16, paddingBottom: 40 },
  sectionTitle: { color: '#fff', fontSize: 15, fontWeight: '700', marginVertical: 10 },
  card: {
    backgroundColor: '#16191e',
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
  },
  cardRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  delete: { color: '#ef4444', fontSize: 13 },
  inputRow: { flexDirection: 'row', gap: 8, marginTop: 6 },
  input: {
    backgroundColor: '#0b0d10',
    color: '#fff',
    borderRadius: 8,
    padding: 10,
    fontSize: 15,
    borderWidth: 1,
    borderColor: '#1f242c',
  },
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
  confidence: { color: '#a78bfa', fontSize: 11, marginTop: 6 },
  outlineBtn: {
    borderColor: '#374151',
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
    marginTop: 6,
  },
  outlineBtnText: { color: '#9aa1a8', fontWeight: '600' },
  primaryBtn: {
    backgroundColor: '#7c3aed',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginTop: 12,
  },
  primaryBtnText: { color: '#fff', fontWeight: '600' },
  preview: { width: 220, height: 220, borderRadius: 12 },
  previewLarge: { width: '100%', aspectRatio: 1, borderRadius: 12, marginBottom: 12 },
});
