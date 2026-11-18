import React from 'react';

export default function Navbar({ activeTab, setActiveTab, authStatus, onSyncClick, syncing }) {
  return (
    <header style={styles.header}>
      <div style={styles.container}>
        <div style={styles.brand}>
          <span style={styles.logoIcon}>📬</span>
          <div>
            <h1 style={styles.brandTitle}>JobMail AI</h1>
            <p style={styles.brandSubtitle}>Monitor de ofertas de empleo</p>
          </div>
        </div>

        <nav style={styles.navTabs}>
          <button
            onClick={() => setActiveTab('dashboard')}
            style={{
              ...styles.tabBtn,
              ...(activeTab === 'dashboard' ? styles.tabBtnActive : {}),
            }}
          >
            📋 Ofertas
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            style={{
              ...styles.tabBtn,
              ...(activeTab === 'chat' ? styles.tabBtnActive : {}),
            }}
          >
            🤖 Chat con LM Studio
          </button>
        </nav>

        <div style={styles.actions}>
          <div style={styles.authBadge}>
            <span
              style={{
                ...styles.statusDot,
                backgroundColor: authStatus?.authenticated ? 'var(--success)' : 'var(--warning)',
              }}
            />
            <span style={styles.authText}>
              {authStatus?.authenticated ? 'Gmail Conectado' : 'Gmail Desconectado'}
            </span>
            {!authStatus?.authenticated && (
              <a href="http://localhost:8000/auth/login" style={styles.loginLink}>
                Conectar
              </a>
            )}
          </div>

          <button
            onClick={onSyncClick}
            disabled={syncing}
            style={{
              ...styles.syncBtn,
              opacity: syncing ? 0.7 : 1,
              cursor: syncing ? 'not-allowed' : 'pointer',
            }}
          >
            {syncing ? '⏳ Sincronizando...' : '🔄 Sincronizar'}
          </button>
        </div>
      </div>
    </header>
  );
}

const styles = {
  header: {
    backgroundColor: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border-color)',
    position: 'sticky',
    top: 0,
    zIndex: 100,
  },
  container: {
    maxWidth: '1280px',
    margin: '0 auto',
    padding: '0.85rem 1.5rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '1rem',
    flexWrap: 'wrap',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  logoIcon: {
    fontSize: '1.8rem',
  },
  brandTitle: {
    fontSize: '1.25rem',
    fontWeight: '700',
    color: 'var(--text-main)',
    letterSpacing: '-0.02em',
  },
  brandSubtitle: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
  navTabs: {
    display: 'flex',
    gap: '0.5rem',
    backgroundColor: 'var(--bg-primary)',
    padding: '0.25rem',
    borderRadius: '10px',
  },
  tabBtn: {
    padding: '0.5rem 1rem',
    backgroundColor: 'transparent',
    color: 'var(--text-muted)',
    fontWeight: '500',
    fontSize: '0.9rem',
  },
  tabBtnActive: {
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--accent)',
    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  authBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.85rem',
    backgroundColor: 'var(--bg-primary)',
    padding: '0.35rem 0.75rem',
    borderRadius: '20px',
    border: '1px solid var(--border-color)',
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  authText: {
    color: 'var(--text-muted)',
  },
  loginLink: {
    color: 'var(--accent)',
    fontWeight: '600',
    marginLeft: '0.25rem',
    textDecoration: 'underline',
  },
  syncBtn: {
    backgroundColor: 'var(--accent)',
    color: '#0f172a',
    fontWeight: '600',
    padding: '0.5rem 1.1rem',
    fontSize: '0.88rem',
  },
};
