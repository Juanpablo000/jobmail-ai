const API_BASE = '';

export async function fetchJobs({
  page = 1,
  pageSize = 12,
  platform = '',
  location = '',
  search = '',
  dateFrom = '',
  dateTo = '',
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });

  if (platform) params.append('platform', platform);
  if (location) params.append('location', location);
  if (search) params.append('search', search);
  if (dateFrom) params.append('date_from', dateFrom);
  if (dateTo) params.append('date_to', dateTo);

  const res = await fetch(`${API_BASE}/api/jobs?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Error obteniendo ofertas: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchJobById(jobId) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!res.ok) {
    throw new Error('Oferta no encontrada');
  }
  return res.json();
}

export async function triggerSync(sinceDays = 7) {
  const res = await fetch(`${API_BASE}/api/sync?since_days=${sinceDays}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Error en la sincronización');
  }
  return res.json();
}

export async function fetchSyncStatus() {
  const res = await fetch(`${API_BASE}/api/sync/status`);
  if (!res.ok) throw new Error('Error al consultar estado del scheduler');
  return res.json();
}

export async function fetchAuthStatus() {
  const res = await fetch(`${API_BASE}/auth/status`);
  if (!res.ok) return { authenticated: false };
  return res.json();
}
