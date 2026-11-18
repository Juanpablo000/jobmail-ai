import React from 'react';

export default function JobCard({ job }) {
  const isLinkedIn = job.platform?.toLowerCase() === 'linkedin';
  const isComputrabajo = job.platform?.toLowerCase() === 'computrabajo';

  const formatDate = (dateString) => {
    if (!dateString) return null;
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString('es-CO', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  return (
    <article style={styles.card}>
      <header style={styles.header}>
        <div style={styles.platformBadge(isLinkedIn, isComputrabajo)}>
          <span style={styles.platformDot(isLinkedIn, isComputrabajo)} />
          <span>{isLinkedIn ? 'LinkedIn' : isComputrabajo ? 'Computrabajo' : (job.platform || 'General')}</span>
        </div>
        <time style={styles.dateLabel} dateTime={job.email_received_at}>
          {formatDate(job.email_received_at)}
        </time>
      </header>

      <div style={styles.body}>
        <h3 style={styles.title} title={job.title}>
          {job.title}
        </h3>

        <div style={styles.companyRow}>
          <span style={styles.companyIcon}>🏢</span>
          <span style={styles.companyName}>
            {job.company || 'Empresa confidencial'}
          </span>
        </div>

        <div style={styles.metaChips}>
          {job.location && (
            <span style={styles.locationChip}>
              📍 {job.location}
            </span>
          )}
          {job.salary ? (
            <span style={styles.salaryChip}>
              💰 {job.salary}
            </span>
          ) : (
            <span style={styles.salaryNotSpecified}>
              Salario a convenir
            </span>
          )}
        </div>
      </div>

      <footer style={styles.footer}>
        <span style={styles.publishedNote}>
          {job.published_at ? `Publicado: ${formatDate(job.published_at)}` : 'Vía alerta de correo'}
        </span>

        {job.offer_url ? (
          <a
            href={job.offer_url}
            target="_blank"
            rel="noopener noreferrer"
            style={styles.actionBtn}
          >
            Ver oferta ↗
          </a>
        ) : (
          <span style={styles.disabledLink}>Sin link directo</span>
        )}
      </footer>
    </article>
  );
}

const styles = {
  card: {
    backgroundColor: 'var(--bg-card)',
    borderRadius: '12px',
    border: '1px solid var(--border-color)',
    padding: '1.35rem',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    minHeight: '260px',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.25)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.85rem',
  },
  platformBadge: (isLinkedIn, isComputrabajo) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.45rem',
    fontSize: '0.78rem',
    fontWeight: '600',
    padding: '0.25rem 0.65rem',
    borderRadius: '20px',
    backgroundColor: isLinkedIn
      ? 'rgba(14, 116, 144, 0.18)'
      : isComputrabajo
      ? 'rgba(217, 119, 6, 0.18)'
      : 'rgba(148, 163, 184, 0.15)',
    color: isLinkedIn ? '#38bdf8' : isComputrabajo ? '#fbbf24' : '#94a3b8',
    border: `1px solid ${
      isLinkedIn ? '#0284c7' : isComputrabajo ? '#d97706' : '#475569'
    }`,
  }),
  platformDot: (isLinkedIn, isComputrabajo) => ({
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: isLinkedIn ? '#38bdf8' : isComputrabajo ? '#fbbf24' : '#94a3b8',
  }),
  dateLabel: {
    fontSize: '0.76rem',
    color: 'var(--text-muted)',
    letterSpacing: '0.01em',
  },
  body: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.65rem',
    flex: 1,
    marginBottom: '1rem',
  },
  title: {
    fontSize: '1.18rem',
    fontWeight: '700',
    color: '#ffffff',
    lineHeight: '1.38',
    letterSpacing: '-0.015em',
  },
  companyRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.45rem',
    color: 'var(--text-secondary)',
    fontSize: '0.88rem',
  },
  companyIcon: {
    fontSize: '0.95rem',
    opacity: 0.85,
  },
  companyName: {
    fontWeight: '600',
    color: 'var(--text-main)',
  },
  metaChips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem',
    marginTop: '0.25rem',
  },
  locationChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.3rem',
    backgroundColor: 'rgba(30, 41, 59, 0.9)',
    border: '1px solid var(--border-highlight)',
    color: 'var(--text-secondary)',
    fontSize: '0.8rem',
    padding: '0.25rem 0.6rem',
    borderRadius: '6px',
  },
  salaryChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.3rem',
    backgroundColor: 'var(--success-bg)',
    border: '1px solid var(--success-border)',
    color: '#34d399',
    fontSize: '0.8rem',
    fontWeight: '600',
    padding: '0.25rem 0.6rem',
    borderRadius: '6px',
  },
  salaryNotSpecified: {
    fontSize: '0.78rem',
    color: 'var(--text-muted)',
    fontStyle: 'italic',
    padding: '0.25rem 0',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTop: '1px solid var(--border-color)',
    paddingTop: '0.9rem',
    marginTop: 'auto',
  },
  publishedNote: {
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
  },
  actionBtn: {
    backgroundColor: '#0284c7',
    color: '#ffffff',
    fontSize: '0.82rem',
    fontWeight: '600',
    padding: '0.45rem 0.95rem',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(2, 132, 199, 0.3)',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.3rem',
  },
  disabledLink: {
    fontSize: '0.78rem',
    color: 'var(--text-muted)',
    fontStyle: 'italic',
  },
};
