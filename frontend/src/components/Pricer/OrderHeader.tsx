import { colors, fonts, fontSizes, spacing, radius } from '../../theme/tokens';
import { usePricerStore } from '../../stores/pricerStore';

export default function OrderHeader() {
  const header = usePricerStore((s) => s.header);
  if (!header) return null;

  const delta = header.delta;
  const deltaStr = delta > 0 ? `+${delta.toFixed(0)}` : delta < 0 ? delta.toFixed(0) : '';

  return (
    <div
      style={{
        backgroundColor: colors.bgSurface,
        padding: `${spacing.lg} ${spacing.xxl}`,
        borderRadius: radius.lg,
        marginBottom: '15px',
        borderLeft: `3px solid ${colors.accent}`,
        display: 'flex',
        gap: spacing.xxl,
        alignItems: 'center',
        flexWrap: 'wrap',
      }}
    >
      <span style={{ color: colors.accent, fontWeight: 700, fontSize: fontSizes.xl }}>
        {header.underlying} {header.structure_name}
      </span>
      {header.stock_ref > 0 && (
        <span style={{ color: colors.textPrimary, fontFamily: fonts.mono }}>
          Tie: ${header.stock_ref.toFixed(2)}
        </span>
      )}
      <span style={{ color: colors.textPrimary, fontFamily: fonts.mono }}>
        Stock: ${header.stock_price.toFixed(2)}
      </span>
      {deltaStr && (
        <span style={{ color: colors.textPrimary, fontFamily: fonts.mono }}>
          Delta: {deltaStr}
        </span>
      )}
    </div>
  );
}
