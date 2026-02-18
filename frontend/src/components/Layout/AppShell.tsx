import type { ReactNode } from 'react';
import { colors, spacing } from '../../theme/tokens';
import Header from './Header';
import AlertBanner from '../Shared/AlertBanner';

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.bgRoot }}>
      <Header />
      <AlertBanner />
      <main style={{ padding: spacing.xxl, maxWidth: '1600px', margin: '0 auto' }}>
        {children}
      </main>
    </div>
  );
}
