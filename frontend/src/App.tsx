import AppShell from './components/Layout/AppShell';
import OrderInput from './components/Pricer/OrderInput';
import OrderHeader from './components/Pricer/OrderHeader';
import BrokerQuote from './components/Pricer/BrokerQuote';
import PricerToolbar from './components/Pricer/PricerToolbar';
import PricingGrid from './components/Pricer/PricingGrid';
import StructureBuilder from './components/Pricer/StructureBuilder';
import AddOrderButton from './components/Pricer/AddOrderButton';
import BlotterGrid from './components/Blotter/BlotterGrid';
import ColumnToggle from './components/Blotter/ColumnToggle';
import { useWebSocket } from './hooks/useWebSocket';
import { useBlotterStore } from './stores/blotterStore';
import { colors, fonts, fontSizes, spacing, radius } from './theme/tokens';

const isBlotterOnly = window.location.pathname === '/blotter';

function BlotterSection() {
  const { deleteSelected, selectedIds } = useBlotterStore();

  return (
    <div
      style={{
        marginTop: isBlotterOnly ? 0 : spacing.xxl,
        paddingTop: isBlotterOnly ? 0 : spacing.xxl,
        borderTop: isBlotterOnly ? 'none' : `1px solid ${colors.borderSubtle}`,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: spacing.lg,
          marginBottom: spacing.lg,
        }}
      >
        <h2
          style={{
            fontSize: fontSizes.h3,
            fontWeight: 600,
            color: colors.textPrimary,
            fontFamily: fonts.body,
            margin: 0,
          }}
        >
          Order Blotter
        </h2>
        <ColumnToggle />
        {selectedIds.size > 0 && (
          <button
            onClick={deleteSelected}
            style={{
              padding: `${spacing.sm} 12px`,
              fontSize: fontSizes.base,
              backgroundColor: colors.redDestructive,
              color: colors.textPrimary,
              border: `1px solid ${colors.redMuted}`,
              borderRadius: radius.md,
              cursor: 'pointer',
              fontFamily: fonts.mono,
            }}
          >
            Delete ({selectedIds.size})
          </button>
        )}
      </div>
      <BlotterGrid />
    </div>
  );
}

export default function App() {
  useWebSocket();

  return (
    <AppShell>
      {!isBlotterOnly && (
        <>
          {/* Pricer Section */}
          <OrderInput />
          <OrderHeader />
          <BrokerQuote />
          <PricerToolbar />

          <div style={{ marginTop: spacing.xl }}>
            <div style={{ display: 'flex', gap: spacing.md, alignItems: 'center', marginBottom: spacing.md }}>
              <StructureBuilder />
              <div style={{ marginLeft: 'auto' }}>
                <AddOrderButton />
              </div>
            </div>
            <PricingGrid />
          </div>
        </>
      )}

      <BlotterSection />
    </AppShell>
  );
}
