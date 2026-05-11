import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
} from '@/api/endpoints';
import { postSSE } from '@/api/sse';
import { uploadVoiceTurn } from '@/api/voice';
import type { ChatConversation, ChatMessage } from '@/api/types';
import { useTTSPlayer, useVoiceRecorder } from '@/features/voice/recorder';

interface TempMessage extends ChatMessage {
  streaming?: boolean;
}

export default function AIScreen() {
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<TempMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const listRef = useRef<FlatList<TempMessage>>(null);
  const voiceRecorder = useVoiceRecorder();
  const ttsPlayer = useTTSPlayer();

  const refreshConversations = useCallback(async () => {
    try {
      const list = await listConversations();
      setConversations(list);
      if (!activeId && list.length > 0) setActiveId(list[0]!.id);
    } catch {
      setError('대화 목록 불러오기 실패');
    }
  }, [activeId]);

  const loadActive = useCallback(async () => {
    if (!activeId) {
      setMessages([]);
      return;
    }
    try {
      const detail = await getConversation(activeId);
      setMessages(detail.messages);
    } catch {
      setError('대화 불러오기 실패');
    }
  }, [activeId]);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  useEffect(() => {
    loadActive();
  }, [loadActive]);

  const ensureConversation = async (): Promise<string> => {
    if (activeId) return activeId;
    const conv = await createConversation();
    setConversations((c) => [conv, ...c]);
    setActiveId(conv.id);
    return conv.id;
  };

  const onSend = async () => {
    if (!input.trim() || sending) return;
    const text = input.trim();
    setInput('');
    setError(null);
    setSending(true);

    let convId: string;
    try {
      convId = await ensureConversation();
    } catch {
      setError('대화 생성 실패');
      setSending(false);
      return;
    }

    const userMsg: TempMessage = {
      id: `local-user-${Date.now()}`,
      role: 'user',
      content: text,
      tool_name: null,
      tool_args: null,
      tool_result: null,
      model: null,
      created_at: new Date().toISOString(),
    };
    const assistantMsg: TempMessage = {
      id: `local-asst-${Date.now()}`,
      role: 'assistant',
      content: '',
      tool_name: null,
      tool_args: null,
      tool_result: null,
      model: null,
      created_at: new Date().toISOString(),
      streaming: true,
    };
    setMessages((m) => [...m, userMsg, assistantMsg]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      let buf = '';
      for await (const evt of postSSE(
        `/chat/conversations/${convId}/messages`,
        { content: text },
        controller.signal,
      )) {
        if (evt.event === 'token') {
          const { text: t } = JSON.parse(evt.data) as { text: string };
          buf += t;
          setMessages((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            if (last && last.role === 'assistant') {
              copy[copy.length - 1] = { ...last, content: buf };
            }
            return copy;
          });
        } else if (evt.event === 'done') {
          setMessages((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            if (last && last.role === 'assistant') {
              copy[copy.length - 1] = { ...last, streaming: false };
            }
            return copy;
          });
        } else if (evt.event === 'error') {
          const { message } = JSON.parse(evt.data) as { message: string };
          setError(message);
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setError(`전송 실패: ${String(e)}`);
    } finally {
      setSending(false);
      abortRef.current = null;
      // Pull authoritative messages from server (so id/model fields are real)
      void loadActive();
    }
  };

  const onNew = async () => {
    abortRef.current?.abort();
    try {
      const conv = await createConversation();
      setConversations((c) => [conv, ...c]);
      setActiveId(conv.id);
    } catch {
      setError('새 대화 생성 실패');
    }
  };

  const onMicPressIn = async () => {
    if (sending || voiceBusy) return;
    try {
      await voiceRecorder.start();
    } catch (e) {
      setError(String(e));
    }
  };

  const onMicPressOut = async () => {
    if (!voiceRecorder.recording) return;
    setError(null);
    let recording: Awaited<ReturnType<typeof voiceRecorder.stop>>;
    try {
      recording = await voiceRecorder.stop();
    } catch (e) {
      setError(`녹음 중단 실패: ${String(e)}`);
      return;
    }
    if (!recording || recording.durationMs < 400) {
      setError('너무 짧아요. 마이크 버튼을 길게 누르고 말씀하세요.');
      return;
    }
    setVoiceBusy(true);
    try {
      const res = await uploadVoiceTurn({
        audioUri: recording.uri,
        audioMime: recording.mime,
        fileName: recording.fileName,
        conversationId: activeId ?? undefined,
      });
      if (!activeId) {
        setActiveId(res.conversation_id);
        // Refresh list so the new voice conversation shows up.
        listConversations().then(setConversations).catch(() => undefined);
      }
      const now = new Date().toISOString();
      setMessages((m) => [
        ...m,
        {
          id: res.user_message_id,
          role: 'user',
          content: res.transcript,
          tool_name: null,
          tool_args: null,
          tool_result: null,
          model: null,
          created_at: now,
        },
        {
          id: res.assistant_message_id,
          role: 'assistant',
          content: res.reply_text,
          tool_name: null,
          tool_args: null,
          tool_result: null,
          model: null,
          created_at: now,
        },
      ]);
      const ext = res.audio_mime.includes('wav') ? 'wav' : 'm4a';
      void ttsPlayer.play(res.audio_b64, ext).catch(() => undefined);
    } catch (e) {
      setError(`음성 전송 실패: ${String(e)}`);
    } finally {
      setVoiceBusy(false);
    }
  };

  const onDelete = async (id: string) => {
    abortRef.current?.abort();
    try {
      await deleteConversation(id);
      setConversations((c) => c.filter((x) => x.id !== id));
      if (activeId === id) setActiveId(null);
    } catch {
      setError('삭제 실패');
    }
  };

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 50);
    }
  }, [messages]);

  return (
    <SafeAreaView style={styles.root} edges={['bottom']}>
      <View style={styles.header}>
        <Pressable style={styles.headerBtn} onPress={onNew}>
          <Text style={styles.headerBtnText}>+ 새 대화</Text>
        </Pressable>
        <FlatList
          data={conversations}
          keyExtractor={(c) => c.id}
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ gap: 8, paddingHorizontal: 4 }}
          renderItem={({ item }) => (
            <Pressable
              style={[styles.chip, activeId === item.id && styles.chipActive]}
              onPress={() => setActiveId(item.id)}
              onLongPress={() => onDelete(item.id)}
            >
              <Text style={[styles.chipText, activeId === item.id && styles.chipTextActive]}>
                {item.title ?? new Date(item.updated_at).toLocaleDateString('ko-KR')}
              </Text>
            </Pressable>
          )}
          ListEmptyComponent={<Text style={styles.dim}>대화가 없어요</Text>}
        />
      </View>

      {error ? (
        <View style={styles.errorBar}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(m) => m.id}
        contentContainerStyle={styles.thread}
        renderItem={({ item }) => (
          <MessageBubble msg={item} />
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.dim}>운동·식단·회복에 대해 물어보세요.</Text>
            <Text style={styles.dim}>예: "오늘 무슨 운동 하는게 좋을까?"</Text>
          </View>
        }
      />

      {voiceRecorder.recording ? (
        <View style={styles.voiceBanner}>
          <Text style={styles.voiceBannerText}>🎙️ 듣는 중… 손을 떼면 전송</Text>
        </View>
      ) : voiceBusy ? (
        <View style={styles.voiceBanner}>
          <ActivityIndicator color="#fff" />
          <Text style={styles.voiceBannerText}>  음성 분석 중…</Text>
        </View>
      ) : null}

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.composer}>
          <Pressable
            onPressIn={onMicPressIn}
            onPressOut={onMicPressOut}
            disabled={sending || voiceBusy}
            style={[
              styles.micBtn,
              voiceRecorder.recording && styles.micBtnActive,
              (sending || voiceBusy) && { opacity: 0.4 },
            ]}
          >
            <Text style={styles.micText}>🎤</Text>
          </Pressable>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder="메시지 입력 / 마이크 길게 누르기"
            placeholderTextColor="#666"
            editable={!sending && !voiceBusy && !voiceRecorder.recording}
            multiline
          />
          <Pressable
            style={[
              styles.sendBtn,
              (sending || voiceBusy || !input.trim()) && { opacity: 0.5 },
            ]}
            onPress={onSend}
            disabled={sending || voiceBusy || !input.trim()}
          >
            {sending ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.sendText}>↑</Text>
            )}
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function MessageBubble({ msg }: { msg: TempMessage }) {
  if (msg.role === 'user') {
    return (
      <View style={[styles.bubble, styles.user]}>
        <Text style={styles.bubbleText}>{msg.content}</Text>
      </View>
    );
  }
  if (msg.role === 'assistant') {
    return (
      <View style={[styles.bubble, styles.assistant]}>
        <Text style={styles.bubbleText}>
          {msg.content || (msg.streaming ? '…' : '')}
        </Text>
      </View>
    );
  }
  return null;
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0b0d10' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    gap: 8,
    borderBottomColor: '#16191e',
    borderBottomWidth: 1,
  },
  headerBtn: {
    backgroundColor: '#3b82f6',
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 8,
  },
  headerBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: '#16191e',
    borderRadius: 16,
  },
  chipActive: { backgroundColor: '#3b82f6' },
  chipText: { color: '#9aa1a8', fontSize: 12 },
  chipTextActive: { color: '#fff' },
  thread: { padding: 12, gap: 8 },
  bubble: {
    padding: 12,
    borderRadius: 14,
    maxWidth: '85%',
  },
  user: {
    alignSelf: 'flex-end',
    backgroundColor: '#3b82f6',
  },
  assistant: {
    alignSelf: 'flex-start',
    backgroundColor: '#16191e',
  },
  bubbleText: { color: '#fff', fontSize: 15, lineHeight: 21 },
  composer: {
    flexDirection: 'row',
    padding: 8,
    gap: 8,
    borderTopColor: '#16191e',
    borderTopWidth: 1,
    backgroundColor: '#0b0d10',
  },
  input: {
    flex: 1,
    backgroundColor: '#16191e',
    color: '#fff',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
    fontSize: 15,
    maxHeight: 120,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#3b82f6',
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'flex-end',
  },
  sendText: { color: '#fff', fontSize: 22, fontWeight: '700' },
  micBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#16191e',
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'flex-end',
  },
  micBtnActive: { backgroundColor: '#dc2626' },
  micText: { fontSize: 18 },
  voiceBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    backgroundColor: '#7c3aed',
  },
  voiceBannerText: { color: '#fff', fontWeight: '600', fontSize: 13 },
  errorBar: { backgroundColor: '#7c2d12', padding: 8 },
  errorText: { color: '#fff', fontSize: 12, textAlign: 'center' },
  empty: { padding: 24, alignItems: 'center', gap: 6 },
  dim: { color: '#9aa1a8', fontSize: 13 },
});
