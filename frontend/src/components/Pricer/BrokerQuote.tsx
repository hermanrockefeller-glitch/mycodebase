import { colors, fonts, fontSizes, spacing, radius } from '../../theme/tokens';
import { usePricerStore } from '../../stores/pricerStore';

export default function BrokerQuote() {
  const brokerQuote = usePricerStore((s) => s.brokerQuote);
  if (!brokerQuote) return null;

  const edgeColor =
    brokerQuote.edge != null && brokerQuote.edge > 0
      ? colors.greenPrimary
      : colors.redPrimary;

  return (
    <div
      style={{
        backgroundColor: colors.bgSurface,
        padding: `15px ${spacing.xxl}`,
        borderRadius: radius.lg,
        marginTop: '15px',
        display: 'flex',
        gap: spacing.xxl,
        alignItems: 'center',
        flexWrap: 'wrap',
      }}
    >
      <span style={{ fontSize: fontSizes.lg, fontFamily: fonts.mono }}>
        Broker: {brokerQuote.broker_price.toFixed(2)} {brokerQuote.quote_side}
      </span>
      {brokerQuote.screen_mid != null ? (
        <span style={{ fontSize: fontSizes.lg, fontFamily: fonts.mono }}>
          Screen Mid: {brokerQuote.screen_mid.toFixed(2)}
        </span>
      ) : (
        <span
          style={{
            fontSize: fontSizes.lg,
            fontFamily: fonts.mono,
            color: colors.textStale,
            fontStyle: 'italic',
          }}
        >
          Screen Mid: --
        </span>
      )}
      {brokerQuote.edge != null && (
        <span
          style={{
            fontSize: fontSizes.lg,
            color: edgeColor,
            fontWeight: 700,
            fontFamily: fonts.mono,
          }}
        >
          Edge: {brokerQuote.edge >= 0 ? '+' : ''}
          {brokerQuote.edge.toFixed(2)}
        </span>
      )}
    </div>
  );
}
