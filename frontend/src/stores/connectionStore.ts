/** Zustand store for connection/health state. */

import { create } from 'zustand';
import * as api from '../api/client';

export interface ConnectionState {
  dataSource: string;
  healthStatus: string;
  sourceError: string;
  wsConnected: boolean;
  toggleSource: () => Promise<void>;
  setHealth: (source: string, status: string) => void;
  setWsConnected: (connected: boolean) => void;
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  dataSource: 'Mock Data',
  healthStatus: 'ok',
  sourceError: '',
  wsConnected: false,

  toggleSource: async () => {
    try {
      const res = await api.toggleSource();
      set({
        dataSource: res.source,
        sourceError: res.error || '',
      });
    } catch (e: unknown) {
      set({ sourceError: e instanceof Error ? e.message : String(e) });
    }
  },

  setHealth: (source, status) => set({ dataSource: source, healthStatus: status }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
}));
