# JobMail AI

Extrae ofertas laborales de tus correos de Gmail (LinkedIn, Computrabajo) y chatea con ellas mediante un agente local en LM Studio.

## Arranque Rápido con un Clic

En Windows puedes hacer **doble clic en `start-app.bat`** (o ejecutar en PowerShell `.\start-app.ps1`). Este script automatiza:
1. Verificación y creación de `backend/.env` si no existe.
2. Comprobación y encendido del contenedor PostgreSQL + pgvector (`docker-compose up db -d`).
3. Lanzamiento del servidor backend FastAPI en el puerto 8000.
4. Lanzamiento del frontend Vite o apertura directa de la consola interactiva Swagger UI.

---

## Requisitos previos

- **Docker Desktop** instalado y corriendo
- **LM Studio** con:
  - Modelo de chat cargado: `ibm/granite-4-h-tiny`
  - Modelo de embedding cargado: `text-embedding-nomic-embed-text-v1.5`
  - Servidor local activo en el puerto `1234`
- **Google Cloud Console**: proyecto con Gmail API habilitada y credenciales OAuth2

## Instalación y arranque

### 1. Configurar variables de entorno

```bash
cp backend/.env.example backend/.env
# Editar backend/.env con tus credenciales de Gmail API
```

### 2. Levantar la base de datos

```bash
docker-compose up db -d
```

### 3. Correr el backend en desarrollo

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

La API estará disponible en:
- **Docs interactivas**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

### 4. (Futuro) Levantar todo con Docker

```bash
docker-compose up --build
```

## Estructura del proyecto

```
jobmail-ai/
├── docs/PLAN.md          # Plan de arquitectura completo
├── backend/              # FastAPI + Python
│   ├── app/
│   │   ├── main.py       # Entry point
│   │   ├── config.py     # Variables de entorno
│   │   ├── database.py   # SQLAlchemy async
│   │   ├── models/       # Modelos de BD
│   │   ├── schemas/      # Schemas Pydantic
│   │   ├── routers/      # Endpoints API
│   │   └── services/     # Lógica de negocio
│   └── alembic/          # Migraciones de BD
└── frontend/             # React + Vite (Hito 3)
```

## Hitos

| Hito | Estado | Descripción |
|---|---|---|
| 1 — Infraestructura | ✅ | Docker, FastAPI, PostgreSQL, modelos |
| 2 — Gmail Extractor | 🔲 | OAuth2, parser LinkedIn/Computrabajo, embeddings |
| 3 — Dashboard | 🔲 | Frontend React con lista y filtros |
| 4 — RAG + Chat | 🔲 | Agente LM Studio con búsqueda semántica |
| 5 — Polish | 🔲 | Exportar CSV, métricas, mejoras UX |
