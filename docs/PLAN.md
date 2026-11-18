# 📋 JobMail AI — Plan de Arquitectura

> Aplicación web para extraer ofertas laborales de Gmail (LinkedIn, Computrabajo)
> y chatear con ellas mediante un agente local en LM Studio.
>
> Directorio del proyecto: `C:\Users\juanp\OneDrive\Documentos\www\jobmail-ai`
> Última actualización: 2026-11-13

---

## 🧱 Stack Tecnológico

| Capa | Tecnología | Razón |
|---|---|---|
| **Backend** | Python 3.11+ + FastAPI | Async, tipado, OpenAPI docs automáticas |
| **Base de datos** | PostgreSQL 16 + pgvector | Relacional + búsqueda semántica en un solo motor |
| **ORM / Migraciones** | SQLAlchemy (async) + Alembic | Estándar de la industria |
| **Extracción de emails** | Gmail API v1 (OAuth2) | Oficial, seguro, sin IMAP legacy |
| **Parsing HTML** | BeautifulSoup4 + regex | Extracción de campos de correos HTML |
| **Agente LLM local** | LM Studio → endpoint OpenAI-compatible | Sin costo, privado, fácil de cambiar modelo |
| **Embeddings** | text-embedding-nomic-embed-text-v1.5 (via LM Studio) | 768 dims, ya descargado |
| **Frontend** | React + Vite (JavaScript) | Simple, reactivo, sin overhead de TypeScript |
| **Scheduler** | APScheduler (integrado en FastAPI) | Polling automático de Gmail cada N minutos |
| **Containerización** | Docker + docker-compose | PostgreSQL+pgvector + Backend + Frontend |

---

## 🤖 Modelo LLM Seleccionado

**Modelo inicial**: `ibm/granite-4-h-tiny` (7B, 4.23 GB)
- ✅ Soporta **tool use** / function calling nativo → ideal para Text-to-SQL estructurado
- ✅ Ligero, corre local en LM Studio
- ⚠️ Puede cambiarse por cualquiera de la lista sin tocar el código (solo cambiar variable de entorno)

**Alternativas disponibles** (si Granite no rinde bien en SQL):
- `qwen2.5-coder-7b-instruct` → específico para código/SQL, muy buena opción
- `qwen/qwen3-4b-thinking-2507` → razonamiento paso a paso
- `google/gemma-3-12b` → más capaz pero más pesado

**Embedding**: `text-embedding-nomic-embed-text-v1.5` (768 dimensiones)
- Corre también desde LM Studio, no se necesita librería externa

---

## 🗄️ Modelo de Base de Datos

```sql
-- Extensión requerida
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla principal
CREATE TABLE job_offers (
    id                  SERIAL PRIMARY KEY,
    -- Campos de la oferta
    title               VARCHAR(500) NOT NULL,
    company             VARCHAR(255),
    location            VARCHAR(255),
    salary              VARCHAR(255),          -- texto libre: "$3M - $5M COP", "No especificado"
    platform            VARCHAR(50),           -- 'linkedin' | 'computrabajo' | 'otro'
    offer_url           TEXT,
    published_at        TIMESTAMP,             -- fecha publicación de la oferta (si viene en el correo)
    -- Campos del correo
    email_received_at   TIMESTAMP NOT NULL,    -- fecha en que llegó el correo a Gmail
    email_message_id    VARCHAR(255) UNIQUE,   -- Gmail message ID → previene duplicados
    email_body_raw      TEXT,                  -- HTML crudo del correo (para re-parsear si el parser mejora)
    -- Búsqueda semántica
    embedding           vector(768),           -- nomic-embed-text-v1.5 = 768 dims
    -- Metadata
    created_at          TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_platform        ON job_offers(platform);
CREATE INDEX idx_published_at    ON job_offers(published_at);
CREATE INDEX idx_email_received  ON job_offers(email_received_at);
CREATE INDEX idx_embedding       ON job_offers USING ivfflat (embedding vector_cosine_ops)
                                 WITH (lists = 100);
```

> **Nota sobre `email_body_raw`**: Guarda el HTML crudo del correo. Es útil porque el parser
> es heurístico (regex/BeautifulSoup) y puede fallar en algunos formatos. Con el raw guardado
> puedes re-parsear toda la DB sin volver a llamar a Gmail. Se puede dejar en NULL si el correo
> no tiene cuerpo HTML. Después de tener confianza en el parser, se puede borrar o archivar.

---

## 🏗️ Arquitectura de la Aplicación

```
Gmail API
    │  OAuth2 + polling (APScheduler)
    ▼
Email Extractor Service
    │  BeautifulSoup4 + regex por remitente
    ▼
Parser Service ──────────────────────────────────────────────┐
    │  {title, company, location, salary,                    │
    │   platform, url, published_at, email_received_at}      │
    ▼                                                        │
Embedding Service                                           email_body_raw (raw HTML)
    │  POST http://localhost:1234/v1/embeddings
    │  modelo: text-embedding-nomic-embed-text-v1.5
    ▼
PostgreSQL + pgvector
    │
    ├── GET /api/jobs      →  Dashboard React (lista + filtros)
    │
    └── POST /api/chat     →  RAG Engine
                                │
                                ├── 1. Embed pregunta del usuario
                                ├── 2. Vector search → Top K ofertas similares
                                ├── 3. Construir prompt con contexto
                                └── 4. POST http://localhost:1234/v1/chat/completions
                                        modelo: ibm/granite-4-h-tiny (tool use)
                                        → Respuesta en streaming (SSE)
```

---

## 📁 Estructura de Directorios

```
jobmail-ai/
├── docs/
│   └── PLAN.md                      ← este archivo
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, routers, lifespan (scheduler)
│   │   ├── config.py                # Settings via pydantic-settings + .env
│   │   ├── database.py              # AsyncEngine, AsyncSession, Base
│   │   ├── scheduler.py             # APScheduler: job de sync de Gmail
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── job_offer.py         # SQLAlchemy model: JobOffer
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── job_offer.py         # Pydantic: JobOfferCreate, JobOfferRead
│   │   │
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── jobs.py              # GET /api/jobs, GET /api/jobs/{id}
│   │   │   ├── sync.py              # POST /api/sync (trigger manual)
│   │   │   ├── chat.py              # POST /api/chat (SSE streaming)
│   │   │   └── auth.py             # GET /auth/callback (OAuth2 Gmail)
│   │   │
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── gmail_service.py     # Auth OAuth2, fetch emails, decode body
│   │       ├── parser_service.py    # Extracción campos por plataforma (linkedin/computrabajo)
│   │       ├── embedding_service.py # Llama a LM Studio /v1/embeddings
│   │       └── rag_service.py       # Vector search + prompt builder + stream LM Studio
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   ├── alembic.ini
│   │   └── versions/               # Migraciones autogeneradas
│   │
│   ├── .env                         # Variables de entorno (NO commitear)
│   ├── .env.example                 # Plantilla pública
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx                 # Punto de entrada React
│   │   ├── App.jsx                  # Router principal
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx        # Lista de ofertas + filtros
│   │   │   └── Chat.jsx             # Chat con el agente
│   │   ├── components/
│   │   │   ├── JobCard.jsx          # Tarjeta de una oferta
│   │   │   ├── Filters.jsx          # Filtros: plataforma, fecha, ubicación
│   │   │   └── ChatMessage.jsx      # Burbuja de mensaje (user/assistant)
│   │   └── services/
│   │       └── api.js               # fetch wrapper para el backend
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml               # PostgreSQL+pgvector + Backend + Frontend
└── README.md
```

---

## 🔄 Flujo de Extracción de Emails

```
Scheduler (cada 30 min)
    │
    ├── Gmail API: buscar correos de:
    │     - noreply@linkedin.com          → platform = 'linkedin'
    │     - noreply@computrabajo.com.co   → platform = 'computrabajo'
    │     - empleo@computrabajo.com.co
    │
    ├── Por cada correo (message_id no existe en DB → no duplicar):
    │     1. Decodificar body (base64 → HTML)
    │     2. Parser específico por plataforma:
    │           LinkedIn:     buscar <h2>, <span data-job>, etc.
    │           Computrabajo: buscar estructura propia del correo
    │     3. Generar embedding del texto: "{title} {company} {location} {salary}"
    │     4. INSERT en job_offers
    │
    └── Log: N ofertas nuevas insertadas
```

---

## 🤖 Flujo del Chat con RAG

```
Usuario: "¿Hay ofertas de trainee en analítica de datos?"
    │
    ├── 1. Embed la pregunta → vector[768] (nomic via LM Studio)
    │
    ├── 2. Vector search en PostgreSQL:
    │       SELECT * FROM job_offers
    │       ORDER BY embedding <=> $query_vector
    │       LIMIT 10;
    │
    ├── 3. (Opcional) Granite puede generar SQL adicional con tool use:
    │       Tool: query_database(sql: "SELECT ... WHERE title ILIKE '%trainee%'")
    │
    ├── 4. Construir prompt:
    │       "Eres un asistente de búsqueda de empleo.
    │        Tienes acceso a estas ofertas: [contexto JSON]
    │        Pregunta del usuario: ..."
    │
    └── 5. POST /v1/chat/completions → LM Studio (ibm/granite-4-h-tiny)
            → Stream SSE al frontend
```

---

## ⚙️ Variables de Entorno (`.env.example`)

```env
# ── Base de datos ──────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://jobmail:jobmail@localhost:5432/jobmail_db

# ── Gmail API (Google Cloud Console) ──────────────────────
GOOGLE_CLIENT_ID=tu_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# ── LM Studio (local) ─────────────────────────────────────
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_CHAT_MODEL=ibm/granite-4-h-tiny
LM_STUDIO_EMBED_MODEL=text-embedding-nomic-embed-text-v1.5

# ── Scheduler ─────────────────────────────────────────────
EMAIL_SYNC_INTERVAL_MINUTES=30

# ── App ───────────────────────────────────────────────────
BACKEND_PORT=8000
FRONTEND_PORT=5173
CORS_ORIGINS=http://localhost:5173
```

---

## 🚀 Hitos de Desarrollo

### Hito 1 — Infraestructura Base (1–2 días)
- [ ] `docker-compose.yml` con PostgreSQL + pgvector
- [ ] FastAPI skeleton con health check
- [ ] SQLAlchemy model `JobOffer` + migración Alembic inicial
- [ ] Configuración `.env` + pydantic-settings

### Hito 2 — Gmail Extractor + Parser (2–3 días)
- [ ] Flujo OAuth2 de Gmail (ruta `/auth/callback`)
- [ ] `gmail_service.py`: listar y decodificar correos
- [ ] `parser_service.py`: extractores por plataforma (LinkedIn, Computrabajo)
- [ ] `embedding_service.py`: llamada a LM Studio `/v1/embeddings`
- [ ] Endpoint `POST /api/sync` + APScheduler
- [ ] Deduplicación por `email_message_id`

### Hito 3 — Dashboard Frontend (1–2 días)
- [ ] React + Vite (JavaScript) scaffold
- [ ] Página `Dashboard.jsx`: tabla/tarjetas de ofertas
- [ ] Filtros: plataforma, rango de fechas, ubicación, búsqueda de texto
- [ ] Botón "Sincronizar ahora"

### Hito 4 — RAG + Chat con LM Studio (2–3 días)
- [ ] `rag_service.py`: vector search + construcción de prompt
- [ ] Endpoint `POST /api/chat` con streaming SSE
- [ ] Tool use de Granite: herramienta `query_database` para Text-to-SQL
- [ ] Página `Chat.jsx`: interfaz de chat con streaming

### Hito 5 — Polish y Extras (1–2 días)
- [ ] Exportar ofertas a CSV
- [ ] Indicadores: total por plataforma, por semana
- [ ] Manejo de errores y reintentos en el parser
- [ ] README con instrucciones de instalación

---

## ⚠️ Consideraciones Importantes

### Gmail API — Setup Google Cloud Console
1. Ir a https://console.cloud.google.com
2. Crear proyecto nuevo
3. Habilitar **Gmail API**
4. Crear credenciales OAuth2 (tipo: "Aplicación web")
5. Agregar URI de redirección: `http://localhost:8000/auth/callback`
6. Descargar `credentials.json`

### LM Studio — Configuración
- Asegúrate de tener el **servidor local activo** en LM Studio (menú: Local Server → Start)
- Puerto por defecto: `1234`
- Cargar el modelo `ibm/granite-4-h-tiny` antes de hacer consultas
- Para embeddings, cargar `text-embedding-nomic-embed-text-v1.5` en paralelo (o secuencial)

### pgvector — Dimensión del vector
- `nomic-embed-text-v1.5` produce **768 dimensiones**
- El campo `embedding vector(768)` en el schema está configurado correctamente
- El índice `ivfflat` requiere al menos ~1000 filas para ser efectivo; con menos filas la búsqueda secuencial es automática

### Parsing de correos — Limitaciones
- LinkedIn y Computrabajo cambian su HTML de correo periódicamente
- El parser usa selectores CSS + regex con fallback a extracción genérica
- `email_body_raw` permite re-parsear sin volver a llamar a Gmail si el parser falla
