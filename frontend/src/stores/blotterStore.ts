/** Zustand store for blotter state. */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { BlotterOrder } from '../types';
import * as api from '../api/client';

const DEFAULT_VISIBLE = [
  'id', 'added_time', 'underlying', 'structure',
  'bid', 'mid', 'offer',
  'side', 'size', 'traded', 'traded_price', 'initiator', 'pnl',
];

export interface BlotterState {
  orders: BlotterOrder[];
  visibleColumns: string[];
  selectedIds: Set<string>;
  // Actions
  loadOrders: () => Promise<void>;
  setOrders: (orders: BlotterOrder[]) => void;
  addOrder: (order: BlotterOrder) => Promise<void>;
  updateOrderField: (id: string, field: string, value: string) => Promise<void>;
  deleteSelected: () => Promise<void>;
  toggleColumn: (colId: string) => void;
  toggleSelectAll: () => void;
  toggleSelect: (id: string) => void;
  updatePrices: (updates: Record<string, Partial<BlotterOrder>>) => void;
}

export const useBlotterStore = create<BlotterState>()(
  persist(
    (set, get) => ({
      orders: [],
      visibleColumns: DEFAULT_VISIBLE,
      selectedIds: new Set<string>(),

      loadOrders: async () => {
        const res = await api.getOrders();
        set({ orders: res.orders });
      },

      setOrders: (orders) => set({ orders }),

      addOrder: async (order) => {
        const res = await api.addOrder(order);
        set({ orders: res.orders });
      },

      updateOrderField: async (id, field, value) => {
        await api.updateOrder(id, { [field]: value });
        // Optimistic: update local
        set((s) => ({
          orders: s.orders.map((o) =>
            o.id === id ? { ...o, [field]: value } : o,
          ),
        }));
      },

      deleteSelected: async () => {
        const ids = Array.from(get().selectedIds);
        if (ids.length === 0) return;
        const res = await api.deleteOrders(ids);
        set({ orders: res.orders, selectedIds: new Set() });
      },

      toggleColumn: (colId) => {
        set((s) => {
          const vis = s.visibleColumns.includes(colId)
            ? s.visibleColumns.filter((c) => c !== colId)
            : [...s.visibleColumns, colId];
          return { visibleColumns: vis };
        });
      },

      toggleSelectAll: () => {
        set((s) => {
          if (s.selectedIds.size === s.orders.length) {
            return { selectedIds: new Set() };
          }
          return { selectedIds: new Set(s.orders.map((o) => o.id)) };
        });
      },

      toggleSelect: (id) => {
        set((s) => {
          const next = new Set(s.selectedIds);
          if (next.has(id)) next.delete(id);
          else next.add(id);
          return { selectedIds: next };
        });
      },

      updatePrices: (updates) => {
        set((s) => ({
          orders: s.orders.map((o) =>
            updates[o.id] ? { ...o, ...updates[o.id] } : o,
          ),
        }));
      },
    }),
    {
      name: 'blotter-settings',
      partialize: (s) => ({ visibleColumns: s.visibleColumns }),
    },
  ),
);
