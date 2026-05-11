import { create } from 'zustand';

import { hydrateTokens, logout as apiLogout } from '@/api/client';
import { getMe, login as apiLogin, register as apiRegister } from '@/api/endpoints';
import type { Me } from '@/api/types';

type Status = 'idle' | 'loading' | 'authed' | 'unauthed';

interface AuthState {
  status: Status;
  user: Me | null;
  error: string | null;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  status: 'idle',
  user: null,
  error: null,

  bootstrap: async () => {
    set({ status: 'loading' });
    const hydrated = await hydrateTokens();
    if (!hydrated) {
      set({ status: 'unauthed', user: null });
      return;
    }
    try {
      const me = await getMe();
      set({ status: 'authed', user: me, error: null });
    } catch {
      await apiLogout();
      set({ status: 'unauthed', user: null });
    }
  },

  login: async (email, password) => {
    set({ status: 'loading', error: null });
    try {
      await apiLogin(email, password);
      const me = await getMe();
      set({ status: 'authed', user: me });
    } catch (e) {
      set({ status: 'unauthed', error: '로그인 실패. 이메일/비밀번호를 확인하세요.' });
      throw e;
    }
  },

  register: async (email, password) => {
    set({ status: 'loading', error: null });
    try {
      await apiRegister(email, password);
      const me = await getMe();
      set({ status: 'authed', user: me });
    } catch (e) {
      set({ status: 'unauthed', error: '가입 실패. 이미 존재하거나 비밀번호가 너무 짧을 수 있어요.' });
      throw e;
    }
  },

  logout: async () => {
    await apiLogout();
    set({ status: 'unauthed', user: null });
  },
}));
