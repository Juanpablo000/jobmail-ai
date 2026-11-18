import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import { fetchAuthStatus, triggerSync } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [authStatus, setAuthStatus] = useState({ authenticated: false });
  const [syncing, setSyncing] = useState(false);
  const [syncToast, setSyncToast] = useState(null);

  useEffect(() => {
    // Verificar si viene de callback exitoso de Google OAuth2
    const params = new URLSearchParams(window.location.search);
    if (params.get('auth') === 'success') {
      setSyncToast({
        type: 'success',
        text: '¡Conexión con Gmail completada exitosamente!',
      });
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const status = await fetchAuthStatus();
      setAuthStatus(status);
    } catch {
      setAuthStatus({ authenticated: false });
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncToast(null);
    try {
      const res = await triggerSync(7);
      setSyncToast({
        type: 'success',
        text: `Sincronización terminada: ${res.inserted || 0} nuevas ofertas insertadas (${res.processed || 0} correos analizados).`,
      });
    } catch (err) {
      setSyncToast({
        type: 'error',
        text: `Error al sincronizar: ${err.message}`,
      });
    } finally {
      setSyncing(false);
      setTimeout(() => setSyncToast(null), 8000);
    }
  };

  return (
    <div style={styles.appContainer}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        authStatus={authStatus}
        onSyncClick={handleSync}
        syncing={syncing}
      />

      {syncToast && (
        <div
          style={{
            ...styles.toast,
            backgroundColor: syncToast.type === 'success' ? '#065f46' : '#991b1b',
            borderColor: syncToast.type === 'success' ? '#059669' : '#dc2626',
          }}
        >
          <span>{syncToast.text}</span>
          <button onClick={() => setSyncToast(null)} style={styles.toastClose}>
            ✕
          </button>
        </div>
      )}

      <main style={styles.main}>
        <div style={{ display: activeTab === 'dashboard' ? 'block' : 'none' }}>
          <Dashboard />
        </div>
        <div style={{ display: activeTab === 'chat' ? 'block' : 'none' }}>
          <Chat />
        </div>
      </main>
    </div>
  );
}

const styles = {
  appContainer: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: 'var(--bg-primary)',
  },
  main: {
    flex: 1,
  },
  toast: {
    position: 'fixed',
    bottom: '2rem',
    right: '2rem',
    color: '#ffffff',
    padding: '0.9rem 1.4rem',
    borderRadius: '10px',
    border: '1px solid',
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.4)',
    zIndex: 999,
    fontSize: '0.9rem',
    maxWidth: '450px',
  },
  toastClose: {
    backgroundColor: 'transparent',
    color: '#fff',
    fontSize: '1rem',
    padding: '0 0.25rem',
  },
};
