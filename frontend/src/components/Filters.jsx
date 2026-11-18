import React from 'react';

export default function Filters({ filters, setFilters, onApply, onReset }) {
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onApply();
  };

  return (
    <form onSubmit={handleSubmit} style={styles.container}>
      <div style={styles.grid}>
        <div style={styles.field}>
          <label style={styles.label}>Buscar puesto o empresa</label>
          <input
            type="text"
            name="search"
            value={filters.search}
            onChange={handleChange}
            placeholder="Ej. Data Analyst, Python, Google..."
            style={styles.input}
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Plataforma</label>
          <select
            name="platform"
            value={filters.platform}
            onChange={handleChange}
            style={styles.select}
          >
            <option value="">Todas las plataformas</option>
            <option value="linkedin">LinkedIn</option>
            <option value="computrabajo">Computrabajo</option>
          </select>
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Ubicación</label>
          <input
            type="text"
            name="location"
            value={filters.location}
            onChange={handleChange}
            placeholder="Ej. Bogotá, Remoto, Medellín..."
            style={styles.input}
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Fecha desde</label>
          <input
            type="date"
            name="dateFrom"
            value={filters.dateFrom}
            onChange={handleChange}
            style={styles.input}
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Fecha hasta</label>
          <input
            type="date"
            name="dateTo"
            value={filters.dateTo}
            onChange={handleChange}
            style={styles.input}
          />
        </div>
      </div>

      <div style={styles.actions}>
        <button type="submit" style={styles.submitBtn}>
          🔍 Aplicar Filtros
        </button>
        <button type="button" onClick={onReset} style={styles.resetBtn}>
          Limpiar
        </button>
      </div>
    </form>
  );
}

const styles = {
  container: {
    backgroundColor: 'var(--bg-secondary)',
    padding: '1.25rem',
    borderRadius: '12px',
    border: '1px solid var(--border-color)',
    marginBottom: '1.5rem',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
    gap: '1rem',
    alignItems: 'end',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.4rem',
  },
  label: {
    fontSize: '0.78rem',
    color: 'var(--text-muted)',
    fontWeight: '500',
  },
  input: {
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    color: 'var(--text-main)',
    padding: '0.55rem 0.8rem',
    borderRadius: '8px',
    fontSize: '0.9rem',
    outline: 'none',
  },
  select: {
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    color: 'var(--text-main)',
    padding: '0.55rem 0.8rem',
    borderRadius: '8px',
    fontSize: '0.9rem',
    outline: 'none',
  },
  actions: {
    display: 'flex',
    gap: '0.75rem',
    marginTop: '1rem',
    justifyContent: 'flex-end',
  },
  submitBtn: {
    backgroundColor: 'var(--accent)',
    color: '#0f172a',
    fontWeight: '600',
    padding: '0.5rem 1.25rem',
    fontSize: '0.9rem',
  },
  resetBtn: {
    backgroundColor: 'transparent',
    color: 'var(--text-muted)',
    border: '1px solid var(--border-color)',
    padding: '0.5rem 1rem',
    fontSize: '0.9rem',
  },
};
