import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import { AuthProvider } from './auth/AuthContext.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import './styles/tokens.css';
import './styles/base.css';
import './styles/layout.css';
import './styles/components.css';
import './styles/badges.css';
import './styles/forms.css';
import './styles/data.css';
import './styles/records.css';
import './styles/states.css';
import './styles/mentor-base.css';
import './styles/mentor-auth.css';
import './styles/auth-wide.css';
import './styles/mentor-home.css';
import './styles/mentor-child.css';
import './styles/mentor-record.css';
import './styles/staff-layout.css';
import './styles/staff-hero.css';
import './styles/staff-todo.css';
import './styles/staff-audit-filter.css';
import './styles/staff-audit-table.css';
import './styles/staff-records.css';
import './styles/staff-notes.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);
