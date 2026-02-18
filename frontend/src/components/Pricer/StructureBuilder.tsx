import { colors, fonts, fontSizes, spacing, radius } from '../../theme/tokens';
import { usePricerStore } from '../../stores/pricerStore';

const btnStyle: React.CSSProperties = {
  padding: `${spacing.sm} 12px`,
  fontSize: fontSizes.base,
  backgroundColor: colors.bgElevated,
  color: colors.textSecondary,
  border: `1px solid ${colors.borderDefault}`,
  borderRadius: radius.md,
  cursor: 'pointer',
  fontFamily: fonts.mono,
};

export default function StructureBuilder() {
  const { addRow, removeRow, flipStructure, clearAll } = usePricerStore();

  return (
    <div
      style={{
        display: 'flex',
        gap: spacing.md,
        marginTop: spacing.lg,
        alignItems: 'center',
      }}
    >
      <button onClick={addRow} style={btnStyle}>
        + Row
      </button>
      <button onClick={removeRow} style={btnStyle}>
        - Row
      </button>
      <button onClick={flipStructure} style={btnStyle}>
        Flip
      </button>
      <button
        onClick={clearAll}
        style={{
          ...btnStyle,
          backgroundColor: colors.redDestructive,
          color: colors.textPrimary,
          border: `1px solid ${colors.redMuted}`,
          marginLeft: spacing.lg,
        }}
      >
        Clear
      </button>
    </div>
  );
}
