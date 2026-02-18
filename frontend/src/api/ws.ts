/** WebSocket client with auto-reconnect and channel-based multiplexing. */

export interface WsMessage {
  channel: string;
  data: unknown;
  timestamp?: number;
  action?: string;
}

type MessageHandler = (msg: WsMessage) => void;

class PriceSocket {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<MessageHandler>>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _connected = false;
  private _onStatusChange: ((connected: boolean) => void) | null = null;

  get connected() {
    return this._connected;
  }

  onStatusChange(cb: (connected: boolean) => void) {
    this._onStatusChange = cb;
  }

  connect() {
    if (this.ws) return;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    this.ws = new WebSocket(`${proto}://${location.host}/api/ws/prices`);

    this.ws.onopen = () => {
      this._connected = true;
      this._onStatusChange?.(true);
    };

    this.ws.onmessage = (e) => {
      try {
        const msg: WsMessage = JSON.parse(e.data);
        const channel = msg.channel;
        this.handlers.get(channel)?.forEach((h) => h(msg));
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this._connected = false;
      this._onStatusChange?.(false);
      this.ws = null;
      this.reconnectTimer = setTimeout(() => this.connect(), 2000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
    this._connected = false;
  }

  subscribe(channel: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(channel)) {
      this.handlers.set(channel, new Set());
    }
    this.handlers.get(channel)!.add(handler);
    return () => {
      this.handlers.get(channel)?.delete(handler);
    };
  }

  send(msg: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  subscribeTicker(underlying: string) {
    this.send({ action: 'subscribe_ticker', underlying });
  }

  unsubscribeTicker() {
    this.send({ action: 'unsubscribe_ticker' });
  }
}

export const priceSocket = new PriceSocket();
