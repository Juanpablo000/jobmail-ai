import React, { useState, useEffect } from 'react';
import Filters from '../components/Filters';
import JobCard from '../components/JobCard';
import { fetchJobs } from '../services/api';

export default function Dashboard() {
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [filters, setFilters] = useState({
    search: '',
    platform: '',
    location: '',
    dateFrom: '',
    dateTo: '',
  });

  const loadJobs = async (targetPage = page) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJobs({
        page: targetPage,
        pageSize,
        ...filters,
      });
      setJobs(data.items || []);
      setTotal(data.total || 0);
      setPage(data.page || 1);
    } catch (err) {
      setError(err.message || 'Error cargando ofertas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs(1);
  }, []);

  const handleApplyFilters = () => {
    setPage(1);
    loadJobs(1);
  };

  const handleResetFilters = () => {
    const emptyFilters = {
      search: '',
      platform: '',
      location: '',
      dateFrom: '',
      dateTo: '',
    };
    setFilters(emptyFilters);
    setPage(1);
    fetchJobs({ page: 1, pageSize, ...emptyFilters })
      .then((data) => {
        setJobs(data.items || []);
        setTotal(data.total || 0);
        setPage(1);
      })
      .catch((err) => setError(err.message));
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div style={styles.container}>
      <div style={styles.headerRow}>
        <div>
          <h2 style={styles.pageTitle}>Ofertas Laborales</h2>
          <p style={styles.pageSubtitle}>
            {total} {total === 1 ? 'oferta extraída' : 'ofertas extraídas'} de tus correos
          </p>
        </div>
        <a
          href="/api/jobs/export/csv"
          download="ofertas_laborales.csv"
          style={styles.exportBtn}
        >
          📥 Exportar CSV
        </a>
      </div>

      <Filters
        filters={filters}
        setFilters={setFilters}
        onApply={handleApplyFilters}
        onReset={handleResetFilters}
      />

      {error && (
        <div style={styles.errorBanner}>
          ⚠️ {error} — Asegúrate de que el backend y la base de datos PostgreSQL estén activos.
        </div>
      )}

      {loading ? (
        <div style={styles.loadingContainer}>
          <div style={styles.spinner}></div>
          <p style={styles.loadingText}>Cargando ofertas laborales...</p>
        </div>
      ) : jobs.length === 0 ? (
        <div style={styles.emptyState}>
          <span style={styles.emptyIcon}>📭</span>
          <h3>No se encontraron ofertas</h3>
          <p style={styles.emptyText}>
            Aún no hay ofertas registradas o ninguna coincide con tus filtros.
            Prueba presionar el botón <strong>Sincronizar</strong> en la barra superior.
          </p>
        </div>
      ) : (
        <>
          <div style={styles.grid}>
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>

          <div style={styles.pagination}>
            <button
              onClick={() => {
                const prev = Math.max(1, page - 1);
                loadJobs(prev);
              }}
              disabled={page <= 1}
              style={{
                ...styles.pageBtn,
                opacity: page <= 1 ? 0.4 : 1,
                cursor: page <= 1 ? 'not-allowed' : 'pointer',
              }}
            >
              ← Anterior
            </button>

            <span style={styles.pageIndicator}>
              Página {page} de {totalPages}
            </span>

            <button
              onClick={() => {
                const next = Math.min(totalPages, page + 1);
                loadJobs(next);
              }}
              disabled={page >= totalPages}
              style={{
                ...styles.pageBtn,
                opacity: page >= totalPages ? 0.4 : 1,
                cursor: page >= totalPages ? 'not-allowed' : 'pointer',
              }}
            >
              Siguiente →
            </button>
          </div>
        </>
      )}
    </div>
  );
}

const styles = {
  container: {
    maxWidth: '1280px',
    margin: '0 auto',
    padding: '2rem 1.5rem',
  },
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.25rem',
  },
  exportBtn: {
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)',
    color: 'var(--accent)',
    padding: '0.5rem 1rem',
    borderRadius: '8px',
    fontSize: '0.85rem',
    fontWeight: '600',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    transition: 'all 0.2s ease',
  },
  pageTitle: {
    fontSize: '1.6rem',
    fontWeight: '700',
    color: 'var(--text-main)',
  },
  pageSubtitle: {
    fontSize: '0.9rem',
    color: 'var(--text-muted)',
    marginTop: '0.2rem',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
    gap: '1.25rem',
  },
  loadingContainer: {
    textAlign: 'center',
    padding: '4rem 1rem',
  },
  spinner: {
    width: '40px',
    height: '40px',
    margin: '0 auto 1rem',
    border: '4px solid var(--border-color)',
    borderTopColor: 'var(--accent)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    color: 'var(--text-muted)',
  },
  emptyState: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '12px',
    border: '1px solid var(--border-color)',
    padding: '4rem 2rem',
    textAlign: 'center',
    maxWidth: '500px',
    margin: '2rem auto',
  },
  emptyIcon: {
    fontSize: '3rem',
    display: 'block',
    marginBottom: '1rem',
  },
  emptyText: {
    color: 'var(--text-muted)',
    fontSize: '0.9rem',
    marginTop: '0.5rem',
    lineHeight: '1.5',
  },
  errorBanner: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid #b91c1c',
    color: '#f87171',
    padding: '0.85rem 1.2rem',
    borderRadius: '8px',
    marginBottom: '1.5rem',
    fontSize: '0.9rem',
  },
  pagination: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '1rem',
    marginTop: '2.5rem',
  },
  pageBtn: {
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)',
    color: 'var(--text-main)',
    padding: '0.55rem 1.1rem',
    fontSize: '0.9rem',
    fontWeight: '500',
  },
  pageIndicator: {
    color: 'var(--text-muted)',
    fontSize: '0.88rem',
  },
};
