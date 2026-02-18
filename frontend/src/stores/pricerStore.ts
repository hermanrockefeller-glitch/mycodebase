/** Zustand store for pricer state — replaces Dash's dcc.Store + callback outputs. */

import { create } from 'zustand';
import type {
  LegRow,
  OrderHeader,
  BrokerQuote,
  CurrentStructure,
  PriceResponse,
  BlotterOrder,
} from '../types';
import * as api from '../api/client';

// Structure templates (mirrors STRUCTURE_TEMPLATES from app.py)
const STRUCTURE_TEMPLATES: Record<string, Array<{ type: string; ratio: number }>> = {
  call: [{ type: 'C', ratio: 1 }],
  put: [{ type: 'P', ratio: 1 }],
  put_spread: [{ type: 'P', ratio: 1 }, { type: 'P', ratio: -1 }],
  call_spread: [{ type: 'C', ratio: 1 }, { type: 'C', ratio: -1 }],
  risk_reversal: [{ type: 'P', ratio: -1 }, { type: 'C', ratio: 1 }],
  straddle: [{ type: 'C', ratio: 1 }, { type: 'P', ratio: 1 }],
  strangle: [{ type: 'P', ratio: 1 }, { type: 'C', ratio: 1 }],
  butterfly: [{ type: 'C', ratio: 1 }, { type: 'C', ratio: -2 }, { type: 'C', ratio: 1 }],
  put_fly: [{ type: 'P', ratio: 1 }, { type: 'P', ratio: -2 }, { type: 'P', ratio: 1 }],
  call_fly: [{ type: 'C', ratio: 1 }, { type: 'C', ratio: -2 }, { type: 'C', ratio: 1 }],
  iron_butterfly: [
    { type: 'P', ratio: 1 }, { type: 'P', ratio: -1 },
    { type: 'C', ratio: -1 }, { type: 'C', ratio: 1 },
  ],
  iron_condor: [
    { type: 'P', ratio: 1 }, { type: 'P', ratio: -1 },
    { type: 'C', ratio: -1 }, { type: 'C', ratio: 1 },
  ],
  put_condor: [
    { type: 'P', ratio: 1 }, { type: 'P', ratio: -1 },
    { type: 'P', ratio: -1 }, { type: 'P', ratio: 1 },
  ],
  call_condor: [
    { type: 'C', ratio: 1 }, { type: 'C', ratio: -1 },
    { type: 'C', ratio: -1 }, { type: 'C', ratio: 1 },
  ],
  collar: [{ type: 'P', ratio: 1 }, { type: 'C', ratio: -1 }],
  call_spread_collar: [
    { type: 'P', ratio: 1 }, { type: 'C', ratio: -1 }, { type: 'C', ratio: 1 },
  ],
  put_spread_collar: [
    { type: 'P', ratio: -1 }, { type: 'P', ratio: 1 }, { type: 'C', ratio: -1 },
  ],
  put_stupid: [{ type: 'P', ratio: 1 }, { type: 'P', ratio: 1 }],
  call_stupid: [{ type: 'C', ratio: 1 }, { type: 'C', ratio: 1 }],
};

function emptyRow(i: number): LegRow {
  return {
    leg: `Leg ${i}`,
    expiry: '', strike: '', type: '', ratio: 1,
    bid_size: '', bid: '', mid: '', offer: '', offer_size: '',
  };
}

export interface PricerState {
  // Order text
  orderText: string;
  // Table data
  tableData: LegRow[];
  // Display sections
  header: OrderHeader | null;
  brokerQuote: BrokerQuote | null;
  currentStructure: CurrentStructure | null;
  // Errors
  parseError: string;
  tableError: string;
  // Toolbar fields
  underlying: string;
  structureType: string;
  stockRef: string;
  delta: string;
  brokerPrice: string;
  quoteSide: string;
  quantity: string;
  // Loading
  loading: boolean;
  // Actions
  setOrderText: (text: string) => void;
  setToolbarField: (field: string, value: string) => void;
  parseAndPrice: () => Promise<void>;
  repriceFromTable: () => Promise<void>;
  applyTemplate: (structureType: string) => void;
  addRow: () => void;
  removeRow: () => void;
  flipStructure: () => void;
  clearAll: () => void;
  recallOrder: (order: BlotterOrder) => void;
  applyPriceResponse: (res: PriceResponse, parsed?: { underlying: string; structure_name: string; stock_ref: number; delta: number; price: number; quote_side: string; quantity: number }) => void;
}

export const usePricerStore = create<PricerState>((set, get) => ({
  orderText: '',
  tableData: [emptyRow(1), emptyRow(2)],
  header: null,
  brokerQuote: null,
  currentStructure: null,
  parseError: '',
  tableError: '',
  underlying: '',
  structureType: '',
  stockRef: '',
  delta: '',
  brokerPrice: '',
  quoteSide: 'bid',
  quantity: '',
  loading: false,

  setOrderText: (text) => set({ orderText: text }),

  setToolbarField: (field, value) => set({ [field]: value } as Partial<PricerState>),

  parseAndPrice: async () => {
    const { orderText } = get();
    if (!orderText.trim()) {
      set({ parseError: 'Please enter an order.' });
      return;
    }
    set({ loading: true, parseError: '', tableError: '' });
    try {
      const parsed = await api.parseOrder(orderText);
      const res = await api.priceStructure(parsed);

      const structName = parsed.structure_name.toLowerCase().replace(/ /g, '_');
      set({
        loading: false,
        parseError: '',
        underlying: parsed.underlying,
        structureType: structName in STRUCTURE_TEMPLATES ? structName : '',
        stockRef: parsed.stock_ref > 0 ? String(parsed.stock_ref) : '',
        delta: parsed.delta !== 0 ? String(parsed.delta) : '',
        brokerPrice: parsed.price > 0 ? String(parsed.price) : '',
        quoteSide: parsed.quote_side,
        quantity: parsed.quantity > 0 ? String(parsed.quantity) : '',
      });
      get().applyPriceResponse(res);
    } catch (e: unknown) {
      set({
        loading: false,
        parseError: e instanceof Error ? e.message : String(e),
      });
    }
  },

  repriceFromTable: async () => {
    const state = get();
    if (!state.underlying.trim()) return;

    // Build legs from table rows
    const legRows = state.tableData.filter(r => r.leg.startsWith('Leg'));
    const legs = [];
    for (const row of legRows) {
      const expiry = String(row.expiry).trim();
      const strike = Number(row.strike);
      const type = String(row.type).trim();
      const ratio = Number(row.ratio);
      if (!expiry || !strike || !type || !ratio) continue;

      // Convert expiry "Jun26" -> "2026-06-16" (approximate)
      const monthMap: Record<string, string> = {
        Jan: '01', Feb: '02', Mar: '03', Apr: '04', May: '05', Jun: '06',
        Jul: '07', Aug: '08', Sep: '09', Oct: '10', Nov: '11', Dec: '12',
      };
      const monthStr = expiry.slice(0, 3);
      const yearStr = expiry.slice(3);
      const month = monthMap[monthStr];
      if (!month || !yearStr) continue;

      const year = 2000 + parseInt(yearStr);
      const expiryDate = `${year}-${month}-16`;

      legs.push({
        expiry: expiryDate,
        strike,
        option_type: type === 'C' ? 'call' : 'put',
        side: ratio > 0 ? 'buy' : 'sell',
        quantity: Math.abs(ratio),
        ratio: Math.abs(ratio),
      });
    }

    if (legs.length === 0) return;

    set({ tableError: '', loading: true });
    try {
      const structName = (state.structureType || 'custom').replace(/_/g, ' ');
      const res = await api.priceFromTable({
        underlying: state.underlying.trim().toUpperCase(),
        structure_name: structName,
        legs,
        stock_ref: parseFloat(state.stockRef) || 0,
        delta: parseFloat(state.delta) || 0,
        price: parseFloat(state.brokerPrice) || 0,
        quote_side: state.quoteSide || 'bid',
        quantity: parseInt(state.quantity) || 1,
      });
      set({ loading: false });
      get().applyPriceResponse(res);
    } catch (e: unknown) {
      set({ loading: false, tableError: e instanceof Error ? e.message : String(e) });
    }
  },

  applyPriceResponse: (res) => {
    // Separate structure row (pinned) from leg rows
    const legRows = res.table_data.filter(r => r.leg !== 'Structure');
    const structRow = res.table_data.find(r => r.leg === 'Structure');
    set({
      tableData: structRow ? [...legRows, structRow] : legRows,
      header: res.header,
      brokerQuote: res.broker_quote,
      currentStructure: res.current_structure,
    });
  },

  applyTemplate: (structureType) => {
    const template = STRUCTURE_TEMPLATES[structureType];
    if (!template) return;
    const rows = template.map((t, i) => ({
      ...emptyRow(i + 1),
      type: t.type,
      ratio: t.ratio,
    }));
    set({ tableData: rows, structureType });
  },

  addRow: () => {
    const rows = get().tableData.filter(r => r.leg !== 'Structure');
    rows.push(emptyRow(rows.length + 1));
    set({ tableData: rows });
  },

  removeRow: () => {
    const rows = get().tableData.filter(r => r.leg !== 'Structure');
    if (rows.length > 1) rows.pop();
    set({ tableData: rows });
  },

  flipStructure: () => {
    const { tableData, delta, underlying } = get();
    const newRows = tableData.map(row => {
      if (row.leg.startsWith('Leg') && row.ratio !== '' && row.ratio !== 0) {
        return { ...row, ratio: -Number(row.ratio) };
      }
      return row;
    });
    const newDelta = delta ? String(-parseFloat(delta)) : '';
    set({ tableData: newRows, delta: newDelta });
    if (underlying.trim()) {
      get().repriceFromTable();
    }
  },

  clearAll: () => {
    set({
      orderText: '',
      tableData: [emptyRow(1), emptyRow(2)],
      header: null,
      brokerQuote: null,
      currentStructure: null,
      parseError: '',
      tableError: '',
      underlying: '',
      structureType: '',
      stockRef: '',
      delta: '',
      brokerPrice: '',
      quoteSide: 'bid',
      quantity: '',
    });
  },

  recallOrder: (order) => {
    if (!order._table_data) return;
    set({
      tableData: order._table_data,
      underlying: order._underlying || '',
      structureType: order._structure_type || '',
      stockRef: order._stock_ref != null ? String(order._stock_ref) : '',
      delta: order._delta != null ? String(order._delta) : '',
      brokerPrice: order._broker_price != null ? String(order._broker_price) : '',
      quoteSide: order._quote_side || 'bid',
      quantity: order._quantity != null ? String(order._quantity) : '',
      currentStructure: order._current_structure || null,
      header: order._current_structure ? {
        underlying: order._current_structure.underlying,
        structure_name: order._current_structure.structure_name,
        stock_ref: order._stock_ref || 0,
        stock_price: 0,
        delta: order._delta || 0,
      } : null,
      brokerQuote: order._broker_price && order._broker_price > 0 && order._current_structure?.mid != null
        ? {
            broker_price: order._broker_price,
            quote_side: (order._quote_side || 'bid').toUpperCase(),
            screen_mid: order._current_structure.mid,
            edge: order._broker_price - order._current_structure.mid,
          }
        : null,
      parseError: '',
      tableError: '',
    });
  },
}));
