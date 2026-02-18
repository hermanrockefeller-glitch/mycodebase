import { useCallback } from 'react';
import { colors, fonts, fontSizes, spacing, radius } from '../../theme/tokens';
import { usePricerStore } from '../../stores/pricerStore';
import { useBlotterStore } from '../../stores/blotterStore';
import type { BlotterOrder } from '../../types';

// Inline UUID generator (avoids uuid dependency)
function genId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/** Local ISO 8601 timestamp: "YYYY-MM-DDTHH:MM:SS" (no timezone — matches backend date.today()). */
function localISOTimestamp(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export default function AddOrderButton() {
  const currentStructure = usePricerStore((s) => s.currentStructure);
  const addOrder = useBlotterStore((s) => s.addOrder);

  const handleAdd = useCallback(async () => {
    const state = usePricerStore.getState();
    const cs = state.currentStructure;
    if (!cs) return;

    const sideMap: Record<string, string> = { bid: 'Bid', offer: 'Offered' };

    const order: BlotterOrder = {
      id: genId(),
      added_time: localISOTimestamp(),
      underlying: cs.underlying,
      structure: `${cs.structure_name} ${cs.structure_detail}`,
      bid: cs.bid != null ? cs.bid.toFixed(2) : '--',
      mid: cs.mid != null ? cs.mid.toFixed(2) : '--',
      offer: cs.offer != null ? cs.offer.toFixed(2) : '--',
      bid_size: cs.bid_size != null ? String(cs.bid_size) : '--',
      offer_size: cs.offer_size != null ? String(cs.offer_size) : '--',
      side: sideMap[state.quoteSide] || '',
      size: state.quantity || '',
      traded: 'No',
      bought_sold: '',
      traded_price: '',
      initiator: '',
      pnl: '',
      multiplier: cs.multiplier,
      _table_data: state.tableData,
      _underlying: state.underlying,
      _structure_type: state.structureType,
      _stock_ref: parseFloat(state.stockRef) || undefined,
      _delta: parseFloat(state.delta) || undefined,
      _broker_price: parseFloat(state.brokerPrice) || undefined,
      _quote_side: state.quoteSide,
      _quantity: parseInt(state.quantity) || undefined,
      _current_structure: cs,
    };

    await addOrder(order);
  }, [addOrder]);

  return (
    <button
      onClick={handleAdd}
      disabled={!currentStructure}
      style={{
        padding: `${spacing.md} ${spacing.xl}`,
        backgroundColor: currentStructure ? colors.accent : colors.bgElevated,
        color: currentStructure ? 'white' : colors.textTertiary,
        border: 'none',
        borderRadius: radius.md,
        cursor: currentStructure ? 'pointer' : 'default',
        fontFamily: fonts.body,
        fontSize: fontSizes.md,
        fontWeight: 600,
        opacity: currentStructure ? 1 : 0.5,
      }}
    >
      Add Order
    </button>
  );
}
