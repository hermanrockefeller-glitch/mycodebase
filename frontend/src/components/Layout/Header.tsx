import { colors, fonts, fontSizes, spacing } from '../../theme/tokens';
import { useConnectionStore } from '../../stores/connectionStore';
import HealthBadge from '../Shared/HealthBadge';

const isBlotterOnly = window.location.pathname === '/blotter';

const navLinkStyle: React.CSSProperties = {
  fontSize: fontSizes.sm,
  fontFamily: fonts.mono,
  color: colors.accent,
  textDecoration: 'none',
};

export default function Header() {
  const { toggleSource, sourceError, wsConnected } = useConnectionStore();

  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: spacing.xl,
        padding: `${spacing.lg} ${spacing.xxl}`,
        backgroundColor: colors.bgSurface,
        borderBottom: `1px solid ${colors.borderSubtle}`,
      }}
    >
      <h1
        style={{
          fontSize: fontSizes.h1,
          fontWeight: 700,
          fontFamily: fonts.body,
          color: colors.textPrimary,
          margin: 0,
        }}
      >
        {isBlotterOnly ? 'Order Blotter' : 'IDB Options Pricer'}
      </h1>
      <a href={isBlotterOnly ? '/' : '/blotter'} style={navLinkStyle}>
        {isBlotterOnly ? 'Pricer' : 'Blotter Only'}
      </a>
      <HealthBadge />
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          fontSize: fontSizes.sm,
          fontFamily: fonts.mono,
          color: wsConnected ? colors.textSecondary : colors.textStale,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: wsConnected ? colors.greenPrimary : colors.textStale,
            display: 'inline-block',
          }}
        />
        {wsConnected ? 'Live' : 'Reconnecting...'}
      </span>
      <button
        onClick={toggleSource}
        style={{
          padding: `${spacing.sm} 12px`,
          fontSize: fontSizes.base,
          backgroundColor: colors.bgElevated,
          color: colors.textSecondary,
          border: `1px solid ${colors.borderDefault}`,
          borderRadius: '4px',
          cursor: 'pointer',
          fontFamily: fonts.mono,
        }}
      >
        Toggle Source
      </button>
      {sourceError && (
        <span style={{ color: colors.redPrimary, fontSize: fontSizes.sm }}>
          {sourceError}
        </span>
      )}
    </header>
  );
}
