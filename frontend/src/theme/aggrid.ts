/** AG Grid CSS overrides for the dark trading theme. */

import { colors, fonts, fontSizes } from './tokens';

/** Inject AG Grid custom CSS into document head. */
export function injectAgGridTheme(): void {
  const style = document.createElement('style');
  style.textContent = `
    .ag-theme-alpine-dark {
      --ag-background-color: ${colors.bgElevated};
      --ag-header-background-color: ${colors.bgSurface};
      --ag-header-foreground-color: ${colors.textSecondary};
      --ag-row-hover-color: ${colors.bgHover};
      --ag-selected-row-background-color: ${colors.bgHover};
      --ag-border-color: ${colors.borderSubtle};
      --ag-font-family: ${fonts.mono};
      --ag-font-size: ${fontSizes.data};
      --ag-cell-horizontal-padding: 8px;
      --ag-row-border-color: ${colors.borderSubtle};
      --ag-header-cell-hover-background-color: ${colors.bgElevated};
    }
    .ag-theme-alpine-dark .ag-header-cell-label {
      font-family: ${fonts.body};
      font-size: ${fontSizes.base};
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .ag-theme-alpine-dark .ag-cell {
      font-feature-settings: 'tnum' 1, 'lnum' 1;
    }
    .ag-theme-alpine-dark .ag-row-pinned {
      background-color: ${colors.bgStructure} !important;
      font-weight: 700;
      border-top: 2px solid ${colors.accentDim};
      color: ${colors.accent};
      font-size: 15px;
    }
    .ag-theme-alpine-dark .ag-row-selected {
      background-color: #353548 !important;
      border-color: ${colors.accent} !important;
    }
    .ag-theme-alpine-dark .ag-value-change-value-highlight {
      background-color: transparent !important;
      transition: color 0.3s ease;
    }
    .ratio-buy { color: ${colors.greenPrimary}; font-weight: 700; }
    .ratio-sell { color: ${colors.redPrimary}; font-weight: 700; }
  `;
  document.head.appendChild(style);
}
