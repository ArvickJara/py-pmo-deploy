# Script para construir y probar Docker localmente en Windows
# Ejecutar desde: python-deploy/

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Construyendo imagen Docker de PMO Python API" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que Docker está corriendo
try {
    docker version | Out-Null
} catch {
    Write-Host "ERROR: Docker no está corriendo o no está instalado" -ForegroundColor Red
    Write-Host "Instala Docker Desktop desde: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Verificar archivos necesarios
$requiredFiles = @(
    "Dockerfile",
    "docker-compose.yml",
    "app.py",
    "requirements.txt",
    "modules/bind_pdf/core.py",
    "models/yolov8n.pt"
)

Write-Host "Verificando archivos necesarios..." -ForegroundColor Yellow
$missing = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missing += $file
        Write-Host "  ✗ Falta: $file" -ForegroundColor Red
    } else {
        Write-Host "  ✓ $file" -ForegroundColor Green
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "ERROR: Faltan archivos necesarios" -ForegroundColor Red
    exit 1
}

# Crear .env si no existe
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "Creando .env desde .env.docker..." -ForegroundColor Yellow
    Copy-Item ".env.docker" ".env"
    Write-Host "✓ .env creado" -ForegroundColor Green
}

# Construir imagen
Write-Host ""
Write-Host "Construyendo imagen Docker..." -ForegroundColor Yellow
Write-Host "(Esto puede tomar varios minutos la primera vez)" -ForegroundColor Gray
Write-Host ""

docker build -t pmo-python-api:latest .

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Fallo al construir la imagen" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  ✓ Imagen construida exitosamente" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

# Preguntar si quiere iniciar el contenedor
$response = Read-Host "¿Deseas iniciar el contenedor ahora? (s/n)"

if ($response -eq "s" -or $response -eq "S" -or $response -eq "si") {
    Write-Host ""
    Write-Host "Iniciando contenedor..." -ForegroundColor Yellow
    
    # Detener contenedor si existe
    docker stop pmo-python-api 2>$null
    docker rm pmo-python-api 2>$null
    
    # Iniciar con docker-compose
    docker-compose up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Contenedor iniciado" -ForegroundColor Green
        Write-Host ""
        Write-Host "Esperando que el servicio inicie..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        Write-Host ""
        Write-Host "Probando API..." -ForegroundColor Yellow
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:5001/health" -UseBasicParsing
            Write-Host ""
            Write-Host "✓ API funcionando correctamente!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Respuesta:" -ForegroundColor Cyan
            Write-Host $response.Content -ForegroundColor Gray
        } catch {
            Write-Host ""
            Write-Host "⚠️  No se pudo conectar a la API todavía" -ForegroundColor Yellow
            Write-Host "Puede tomar unos segundos más..." -ForegroundColor Gray
        }
        
        Write-Host ""
        Write-Host "Comandos útiles:" -ForegroundColor Cyan
        Write-Host "  Ver logs:     docker logs -f pmo-python-api" -ForegroundColor Gray
        Write-Host "  Detener:      docker-compose down" -ForegroundColor Gray
        Write-Host "  Reiniciar:    docker-compose restart" -ForegroundColor Gray
        Write-Host "  Entrar:       docker exec -it pmo-python-api bash" -ForegroundColor Gray
        Write-Host ""
        Write-Host "API disponible en: http://localhost:5001" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "ERROR al iniciar el contenedor" -ForegroundColor Red
        Write-Host "Ver logs con: docker logs pmo-python-api" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Para iniciar el contenedor manualmente:" -ForegroundColor Cyan
    Write-Host "  docker-compose up -d" -ForegroundColor Gray
    Write-Host ""
}
