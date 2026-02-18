import { colors, fonts, fontSizes, spacing, radius } from '../../theme/tokens';
import { useConnectionStore } from '../../stores/connectionStore';

export default function AlertBanner() {
  const { dataSource, healthStatus } = useConnectionStore();

  if (dataSource !== 'Bloomberg API' || healthStatus === 'ok') return null;

  return (
    <div
      style={{
        backgroundColor: colors.statusError,
        color: 'white',
        padding: `${spacing.md} ${spacing.xl}`,
        borderRadius: radius.md,
        fontSize: fontSizes.data,
        fontFamily: fonts.mono,
        marginTop: spacing.lg,
        textAlign: 'center',
        fontWeight: 500,
      }}
    >
      Bloomberg API is not responding. Market data may be unavailable.
    </div>
  );
}
