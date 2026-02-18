/** Design tokens ported from layouts.py theme system. */

export const colors = {
  bgRoot: '#1a1a24',
  bgSurface: '#22222e',
  bgElevated: '#2a2a38',
  bgEditable: '#2f3044',
  bgHover: '#353548',
  bgStructure: '#1e2e4a',

  textPrimary: '#e8e8ec',
  textSecondary: '#9898a6',
  textTertiary: '#5c5c6e',
  textStale: '#4a4a5c',

  greenPrimary: '#2ecc71',
  greenMuted: '#1fa558',
  redPrimary: '#e74c3c',
  redMuted: '#c0392b',
  redDestructive: '#a62020',

  accent: '#4aa3df',
  accentBright: '#5bb8f5',
  accentDim: '#2d7ab8',

  borderSubtle: '#2a2a3a',
  borderDefault: '#3a3a4c',
  borderFocus: '#4aa3df',

  statusLive: '#27ae60',
  statusMock: '#3498db',
  statusError: '#c0392b',
} as const;

export const fonts = {
  body: "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
  mono: "'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'SF Mono', 'Consolas', monospace",
} as const;

export const fontSizes = {
  xs: '10px',
  sm: '11px',
  base: '12px',
  data: '13px',
  md: '14px',
  lg: '16px',
  xl: '18px',
  h3: '16px',
  h1: '22px',
} as const;

export const spacing = {
  xs: '2px',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  xxl: '20px',
} as const;

export const radius = {
  sm: '3px',
  md: '4px',
  lg: '6px',
} as const;

export const STRUCTURE_TYPE_OPTIONS = [
  { label: 'Call', value: 'call' },
  { label: 'Put', value: 'put' },
  { label: 'Put Spread', value: 'put_spread' },
  { label: 'Call Spread', value: 'call_spread' },
  { label: 'Risk Reversal', value: 'risk_reversal' },
  { label: 'Straddle', value: 'straddle' },
  { label: 'Strangle', value: 'strangle' },
  { label: 'Butterfly', value: 'butterfly' },
  { label: 'Put Fly', value: 'put_fly' },
  { label: 'Call Fly', value: 'call_fly' },
  { label: 'Iron Butterfly', value: 'iron_butterfly' },
  { label: 'Iron Condor', value: 'iron_condor' },
  { label: 'Put Condor', value: 'put_condor' },
  { label: 'Call Condor', value: 'call_condor' },
  { label: 'Collar', value: 'collar' },
  { label: 'Call Spread Collar', value: 'call_spread_collar' },
  { label: 'Put Spread Collar', value: 'put_spread_collar' },
  { label: 'Put Stupid', value: 'put_stupid' },
  { label: 'Call Stupid', value: 'call_stupid' },
] as const;
