#!/bin/bash
# Script de actualización automática para PMO Python API
# Ubicación: /home/cloudpanel/htdocs/pmopy.sistemasudh.com/update-python.sh

set -e  # Detener si hay error

echo "================================================"
echo "  🚀 Actualizando PMO Python API desde GitHub"
echo "================================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directorio base
BASE_DIR="/home/cloudpanel/htdocs/pmopy.sistemasudh.com"
cd "$BASE_DIR"

# Verificar que estamos en un repo git
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Error: No es un repositorio Git${NC}"
    exit 1
fi

# Guardar cambios locales si los hay
echo -e "${YELLOW}📋 Verificando cambios locales...${NC}"
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠️  Hay cambios locales, guardando...${NC}"
    git stash save "Auto-stash antes de actualizar $(date)"
fi

# Obtener branch actual
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${GREEN}📍 Branch actual: $CURRENT_BRANCH${NC}"

# Descargar cambios
echo -e "${YELLOW}📥 Descargando cambios desde GitHub...${NC}"
git pull origin "$CURRENT_BRANCH"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al descargar cambios${NC}"
    exit 1
fi

# Ir a python-deploy
cd python-deploy

# Verificar si cambió requirements.txt
REBUILD=false
if git diff HEAD@{1} HEAD --name-only | grep -q "python-deploy/requirements.txt"; then
    echo -e "${YELLOW}📦 Dependencias cambiaron, se necesita rebuild${NC}"
    REBUILD=true
fi

# Verificar si cambió Dockerfile
if git diff HEAD@{1} HEAD --name-only | grep -q "python-deploy/Dockerfile"; then
    echo -e "${YELLOW}🐳 Dockerfile cambió, se necesita rebuild${NC}"
    REBUILD=true
fi

# Reconstruir imagen si es necesario
if [ "$REBUILD" = true ]; then
    echo -e "${YELLOW}🔨 Reconstruyendo imagen Docker...${NC}"
    docker build -t pmo-python-api:latest .
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error al construir imagen${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Imagen reconstruida${NC}"
else
    echo -e "${GREEN}✓ Sin cambios en dependencias, usando imagen existente${NC}"
fi

# Detener y eliminar contenedor actual
echo -e "${YELLOW}🛑 Deteniendo contenedor actual...${NC}"
docker-compose down

# Iniciar nuevo contenedor
echo -e "${YELLOW}▶️  Iniciando nuevo contenedor...${NC}"
docker-compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al iniciar contenedor${NC}"
    exit 1
fi

# Esperar que el servicio inicie
echo -e "${YELLOW}⏳ Esperando que el servicio inicie...${NC}"
sleep 10

# Verificar health check
echo -e "${YELLOW}🏥 Verificando salud de la API...${NC}"
RETRY=0
MAX_RETRIES=5

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:5001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API funcionando correctamente!${NC}"
        break
    else
        RETRY=$((RETRY+1))
        echo -e "${YELLOW}⏳ Intento $RETRY de $MAX_RETRIES...${NC}"
        sleep 5
    fi
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ API no responde después de $MAX_RETRIES intentos${NC}"
    echo -e "${YELLOW}Ver logs con: docker logs -f pmo-python-api${NC}"
    exit 1
fi

# Mostrar información final
echo ""
echo "================================================"
echo -e "${GREEN}  ✨ Actualización completa!${NC}"
echo "================================================"
echo ""
echo -e "${GREEN}📊 Estado del contenedor:${NC}"
docker ps | grep pmo-python-api

echo ""
echo -e "${GREEN}📋 Comandos útiles:${NC}"
echo "  Ver logs:      docker logs -f pmo-python-api"
echo "  Ver estado:    docker ps"
echo "  Reiniciar:     docker-compose restart"
echo "  Entrar:        docker exec -it pmo-python-api bash"
echo ""
echo -e "${GREEN}🌐 API disponible en:${NC} https://pmopy.sistemasudh.com"
echo ""
