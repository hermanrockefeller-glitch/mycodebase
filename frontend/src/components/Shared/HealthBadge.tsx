import { colors, fonts, fontSizes } from '../../theme/tokens';
import { useConnectionStore } from '../../stores/connectionStore';

const base: React.CSSProperties = {
  padding: '3px 10px',
  borderRadius: '10px',
  fontSize: fontSizes.sm,
  fontFamily: fonts.mono,
  fontWeight: 600,
  color: 'white',
  letterSpacing: '0.5px',
  display: 'inline-block',
};

export default function HealthBadge() {
  const { dataSource, healthStatus } = useConnectionStore();

  let bg: string = colors.statusMock;
  if (dataSource === 'Bloomberg API') {
    bg = healthStatus === 'ok' ? colors.statusLive : colors.statusError;
  }

  return <span style={{ ...base, backgroundColor: bg }}>{dataSource}</span>;
}
