/** Hook that connects the WebSocket and routes messages to stores. */

import { useEffect } from 'react';
import { priceSocket } from '../api/ws';
import { useBlotterStore } from '../stores/blotterStore';
import { useConnectionStore } from '../stores/connectionStore';
import type { BlotterOrder } from '../types';

export function useWebSocket() {
  useEffect(() => {
    priceSocket.onStatusChange((connected) => {
      useConnectionStore.getState().setWsConnected(connected);
    });
    priceSocket.connect();

    const unsubs = [
      // Blotter price updates (every 1s from background broadcaster)
      priceSocket.subscribe('blotter_prices', (msg) => {
        const data = msg.data as Record<string, Partial<BlotterOrder>>;
        useBlotterStore.getState().updatePrices(data);
      }),

      // Health updates
      priceSocket.subscribe('health', (msg) => {
        const data = msg.data as { source: string; status: string };
        useConnectionStore.getState().setHealth(data.source, data.status);
      }),

      // Cross-tab order sync
      priceSocket.subscribe('order_sync', (msg) => {
        const data = msg.data as { orders: BlotterOrder[] };
        useBlotterStore.getState().setOrders(data.orders);
      }),
    ];

    return () => {
      unsubs.forEach((fn) => fn());
      priceSocket.disconnect();
    };
  }, []);
}
