import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { injectAgGridTheme } from './theme/aggrid';

injectAgGridTheme();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
