# JobMail AI — Script de Inicio Rápido (Windows PowerShell)
$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "             🚀 INICIANDO JOBMAIL AI                      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Actualizar variable PATH en la sesión actual
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR = Join-Path $ROOT_DIR "backend"
$FRONTEND_DIR = Join-Path $ROOT_DIR "frontend"

# 1. Configuración de entorno
$ENV_FILE = Join-Path $BACKEND_DIR ".env"
$ENV_EXAMPLE = Join-Path $BACKEND_DIR ".env.example"
if (-not (Test-Path $ENV_FILE)) {
    Write-Host "[1/4] Creando backend/.env desde plantilla..." -ForegroundColor Yellow
    Copy-Item $ENV_EXAMPLE $ENV_FILE
} else {
    Write-Host "[1/4] Configuración backend/.env lista." -ForegroundColor Green
}

# 2. Base de datos con pgvector en puerto 5433 (evita colisión con PostgreSQL local en 5432)
Write-Host "[2/4] Verificando Docker Desktop para PostgreSQL + pgvector..." -ForegroundColor Yellow
$dockerOk = $false
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerOk = $true
    }
} catch {
    $dockerOk = $false
}

if (-not $dockerOk) {
    $dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerExe) {
        Write-Host "      Iniciando Docker Desktop en segundo plano..." -ForegroundColor Yellow
        Start-Process $dockerExe
        Write-Host "      Esperando a que el motor de Docker responda (15s)..." -ForegroundColor Gray
        Start-Sleep -Seconds 15
        try {
            $null = docker info 2>&1
            if ($LASTEXITCODE -eq 0) { $dockerOk = $true }
        } catch {}
    }
}

if ($dockerOk) {
    Write-Host "      Levantando contenedor 'jobmail_db' (puerto 5433)..." -ForegroundColor Green
    docker-compose -f (Join-Path $ROOT_DIR "docker-compose.yml") up db -d
} else {
    Write-Host "      ⚠️ Docker Desktop no está listo aún." -ForegroundColor Yellow
    Write-Host "      Asegúrate de que el icono de Docker en la barra de tareas esté verde." -ForegroundColor Yellow
    Write-Host "      (El backend arrancará de todos modos en modo tolerante)." -ForegroundColor Gray
}

# 3. Lanzar Backend FastAPI
Write-Host "[3/4] Lanzando Backend FastAPI en http://localhost:8000..." -ForegroundColor Green
$backendCmd = "`$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User'); Set-Location '$BACKEND_DIR'; uvicorn app.main:app --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$backendCmd"

# 4. Lanzar Frontend / Abrir navegador
Write-Host "[4/4] Verificando Frontend..." -ForegroundColor Yellow
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue

if ($nodeCmd) {
    Write-Host "      Node.js detectado. Iniciando servidor web..." -ForegroundColor Green
    $frontendCmd = "`$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User'); Set-Location '$FRONTEND_DIR'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "$frontendCmd"
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:5173"
} else {
    Write-Host "      Abriendo documentación interactiva Swagger UI..." -ForegroundColor Green
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8000/docs"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      ✅ ¡JobMail AI iniciado!" -ForegroundColor Green
Write-Host "      • Documentación API: http://localhost:8000/docs" -ForegroundColor White
Write-Host "      • Base de Datos:    localhost:5433 (jobmail_db)" -ForegroundColor White
Write-Host "      • LM Studio:        http://localhost:1234/v1" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
