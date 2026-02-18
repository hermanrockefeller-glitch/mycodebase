import { colors, fonts, fontSizes, spacing, radius } from '../../theme/tokens';
import { usePricerStore } from '../../stores/pricerStore';

export default function OrderInput() {
  const { orderText, setOrderText, parseAndPrice, parseError, loading } = usePricerStore();

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      parseAndPrice();
    }
  };

  return (
    <div style={{ marginBottom: spacing.xl }}>
      <div style={{ display: 'flex', gap: spacing.md, alignItems: 'flex-start' }}>
        <textarea
          value={orderText}
          onChange={(e) => setOrderText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Paste order text (e.g. AAPL Jun26 240/220 PS vs250 15d 500x @ 3.50)"
          rows={2}
          style={{
            flex: 1,
            padding: spacing.md,
            backgroundColor: colors.bgElevated,
            color: colors.textPrimary,
            border: `1px solid ${colors.borderDefault}`,
            borderRadius: radius.md,
            fontFamily: fonts.mono,
            fontSize: fontSizes.md,
            outline: 'none',
            resize: 'vertical',
          }}
        />
        <button
          onClick={parseAndPrice}
          disabled={loading}
          style={{
            padding: `${spacing.md} ${spacing.xl}`,
            backgroundColor: colors.accent,
            color: 'white',
            border: 'none',
            borderRadius: radius.md,
            cursor: loading ? 'wait' : 'pointer',
            fontFamily: fonts.body,
            fontSize: fontSizes.md,
            fontWeight: 600,
            whiteSpace: 'nowrap',
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? 'Pricing...' : 'Parse & Price'}
        </button>
      </div>
      {parseError && (
        <div
          style={{
            color: colors.redPrimary,
            fontSize: fontSizes.data,
            marginTop: spacing.md,
            fontFamily: fonts.mono,
          }}
        >
          {parseError}
        </div>
      )}
    </div>
  );
}
