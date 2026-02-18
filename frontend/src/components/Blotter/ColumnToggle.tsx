import { colors, fonts, fontSizes, spacing, radius } from '../../theme/tokens';
import { useBlotterStore } from '../../stores/blotterStore';
import { useState } from 'react';

const ALL_COLUMN_IDS = [
  { id: 'id', label: 'ID' },
  { id: 'added_time', label: 'Time' },
  { id: 'underlying', label: 'Underlying' },
  { id: 'structure', label: 'Structure' },
  { id: 'bid', label: 'Bid' },
  { id: 'mid', label: 'Mid' },
  { id: 'offer', label: 'Offer' },
  { id: 'bid_size', label: 'Bid Size' },
  { id: 'offer_size', label: 'Offer Size' },
  { id: 'side', label: 'Bid/Offered' },
  { id: 'size', label: 'Size' },
  { id: 'traded', label: 'Traded' },
  { id: 'bought_sold', label: 'Bought/Sold' },
  { id: 'traded_price', label: 'Traded Px' },
  { id: 'initiator', label: 'Initiator' },
  { id: 'pnl', label: 'PnL' },
];

export default function ColumnToggle() {
  const { visibleColumns, toggleColumn } = useBlotterStore();
  const [open, setOpen] = useState(false);

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          padding: `${spacing.sm} 12px`,
          fontSize: fontSizes.base,
          backgroundColor: colors.bgElevated,
          color: colors.textSecondary,
          border: `1px solid ${colors.borderDefault}`,
          borderRadius: radius.md,
          cursor: 'pointer',
          fontFamily: fonts.mono,
        }}
      >
        Columns
      </button>
      {open && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            zIndex: 10,
            backgroundColor: colors.bgSurface,
            border: `1px solid ${colors.borderDefault}`,
            borderRadius: radius.md,
            padding: spacing.md,
            minWidth: '150px',
            marginTop: spacing.sm,
          }}
        >
          {ALL_COLUMN_IDS.map((col) => (
            <label
              key={col.id}
              style={{
                display: 'block',
                padding: `${spacing.xs} 0`,
                color: colors.textPrimary,
                fontSize: fontSizes.sm,
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={visibleColumns.includes(col.id)}
                onChange={() => toggleColumn(col.id)}
                style={{ marginRight: spacing.md }}
              />
              {col.label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
