# 🚀 Despliegue con GitHub + Docker

## 📋 Ventajas de usar GitHub

- ✅ Control de versiones
- ✅ Fácil actualización (git pull)
- ✅ Historial de cambios
- ✅ Colaboración en equipo
- ✅ No necesitas subir archivos manualmente

---

## 1️⃣ CONFIGURACIÓN INICIAL - LOCAL

### Inicializar Git (si no lo has hecho)

```bash
# En la raíz del proyecto pmo-gore
cd C:\Users\AmarilisProject\Development\pmo-gore

# Inicializar Git
git init

# Añadir archivos
git add .

# Commit inicial
git commit -m "Configuración inicial Python API con Docker"

# Conectar con GitHub (crea el repositorio primero en GitHub)
git remote add origin https://github.com/tu-usuario/pmo-gore.git

# Subir cambios
git push -u origin main
```

### O si ya tienes Git configurado, solo actualiza:

```bash
cd C:\Users\AmarilisProject\Development\pmo-gore

# Ver cambios
git status

# Añadir cambios de python-deploy
git add python-deploy/

# Commit
git commit -m "Añadir configuración Docker para Python API"

# Subir
git push
```

---

## 2️⃣ CONFIGURACIÓN EN EL SERVIDOR

### Primera vez - Clonar repositorio

```bash
# Conectar al servidor
ssh tu-usuario@pmopy.sistemasudh.com

# Navegar al directorio
cd /home/cloudpanel/htdocs/

# Clonar el repositorio
git clone https://github.com/tu-usuario/pmo-gore.git pmopy.sistemasudh.com

# Entrar a python-deploy
cd pmopy.sistemasudh.com/python-deploy

# Crear .env desde la plantilla
cp .env.docker .env
nano .env  # Configurar variables
```

### Configurar Git para no pedir contraseña

```bash
# Opción 1: SSH (recomendado)
ssh-keygen -t ed25519 -C "tu-email@ejemplo.com"
cat ~/.ssh/id_ed25519.pub
# Copiar la clave y agregarla en GitHub: Settings > SSH Keys

# Cambiar remote a SSH
git remote set-url origin git@github.com:tu-usuario/pmo-gore.git

# Opción 2: Token de acceso personal
# Generar token en GitHub: Settings > Developer settings > Personal access tokens
git remote set-url origin https://TOKEN@github.com/tu-usuario/pmo-gore.git
```

### Construir y ejecutar Docker

```bash
cd /home/cloudpanel/htdocs/pmopy.sistemasudh.com/python-deploy

# Construir imagen
docker build -t pmo-python-api:latest .

# Iniciar con docker-compose
docker-compose up -d

# Verificar
curl http://localhost:5001/health
```

---

## 3️⃣ ACTUALIZACIONES - FLUJO DE TRABAJO

### En tu máquina local (Windows):

```powershell
# Hacer cambios en python-deploy/
# Por ejemplo, modificar app.py o agregar funcionalidades

# Ver cambios
git status

# Añadir cambios
git add python-deploy/

# Commit con mensaje descriptivo
git commit -m "Mejorar manejo de errores en bind_pdf"

# Subir a GitHub
git push
```

### En el servidor (automático):

```bash
# Conectar al servidor
ssh tu-usuario@pmopy.sistemasudh.com

# Ir al directorio
cd /home/cloudpanel/htdocs/pmopy.sistemasudh.com

# Descargar últimos cambios
git pull

# Ir a python-deploy
cd python-deploy

# Si cambiaron dependencias, reconstruir
docker build -t pmo-python-api:latest .

# Reiniciar contenedor
docker-compose restart

# O si necesitas recrear completamente
docker-compose down
docker-compose up -d

# Verificar
curl http://localhost:5001/health
```

---

## 4️⃣ SCRIPT DE ACTUALIZACIÓN AUTOMÁTICA

Crea este script en el servidor para actualizar fácilmente:

```bash
# Crear script
nano /home/cloudpanel/htdocs/pmopy.sistemasudh.com/update.sh
```

Contenido del script:

```bash
#!/bin/bash

echo "🚀 Actualizando PMO Python API desde GitHub..."

cd /home/cloudpanel/htdocs/pmopy.sistemasudh.com

# Obtener cambios
echo "📥 Descargando cambios..."
git pull

# Ir a python-deploy
cd python-deploy

# Verificar si cambió requirements.txt
if git diff HEAD@{1} HEAD --name-only | grep -q "requirements.txt"; then
    echo "📦 Dependencias cambiaron, reconstruyendo imagen..."
    docker build -t pmo-python-api:latest .
else
    echo "✓ Sin cambios en dependencias"
fi

# Reiniciar contenedor
echo "🔄 Reiniciando contenedor..."
docker-compose down
docker-compose up -d

# Esperar que inicie
sleep 5

# Verificar
echo "✅ Verificando salud de la API..."
curl -f http://localhost:5001/health || echo "❌ Error al verificar API"

echo "✨ Actualización completa!"
echo "Ver logs con: docker logs -f pmo-python-api"
```

Dar permisos de ejecución:

```bash
chmod +x /home/cloudpanel/htdocs/pmopy.sistemasudh.com/update.sh
```

### Uso del script:

```bash
# Cada vez que quieras actualizar, solo ejecuta:
/home/cloudpanel/htdocs/pmopy.sistemasudh.com/update.sh
```

---

## 5️⃣ ARCHIVOS QUE NO SE SUBEN A GIT

El `.gitignore` ya está configurado para **NO subir**:

- ❌ `.env` (variables de entorno con secretos)
- ❌ `venv/` (entorno virtual)
- ❌ `logs/` (archivos de log)
- ❌ `temp/` (archivos temporales)
- ❌ `__pycache__/` (archivos compilados)
- ❌ Archivos PDF/imágenes temporales

**SÍ se suben**:

- ✅ `Dockerfile`
- ✅ `docker-compose.yml`
- ✅ `.env.docker` (plantilla sin secretos)
- ✅ `.env.example` (plantilla)
- ✅ Todo el código Python
- ✅ `requirements.txt`
- ✅ `models/yolov8n.pt` (modelo YOLO)

---

## 6️⃣ GITHUB ACTIONS (OPCIONAL - AVANZADO)

Si quieres despliegue automático cuando haces push:

Crea `.github/workflows/deploy.yml` en tu repositorio:

```yaml
name: Deploy Python API

on:
  push:
    branches: [ main ]
    paths:
      - 'python-deploy/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /home/cloudpanel/htdocs/pmopy.sistemasudh.com
            /home/cloudpanel/htdocs/pmopy.sistemasudh.com/update.sh
```

Configurar secrets en GitHub:
- Settings > Secrets > New secret
- `SERVER_HOST`: tu-servidor.com
- `SERVER_USER`: tu-usuario
- `SSH_KEY`: tu clave privada SSH

---

## 🎯 FLUJO RECOMENDADO

### Desarrollo diario:

```powershell
# 1. En Windows - Hacer cambios
code python-deploy/modules/bind_pdf/core.py

# 2. Probar localmente (opcional)
cd python-deploy
docker-compose up

# 3. Commit y push
git add .
git commit -m "Descripción de cambios"
git push

# 4. En servidor - Actualizar
ssh usuario@servidor
/home/cloudpanel/htdocs/pmopy.sistemasudh.com/update.sh
```

---

## ✅ VERIFICACIÓN

```bash
# Ver estado de Git
git status

# Ver historial
git log --oneline

# Ver diferencias antes de commit
git diff

# Ver ramas
git branch

# Cambiar de rama
git checkout -b nueva-funcionalidad
```

---

## 🔧 TROUBLESHOOTING

### Conflictos de Git

```bash
# Si hay conflictos al hacer pull
git stash  # Guardar cambios temporalmente
git pull
git stash pop  # Recuperar cambios
```

### Archivo .env no existe en servidor

```bash
# Siempre crear .env desde la plantilla
cp .env.docker .env
nano .env
```

### Docker imagen desactualizada

```bash
# Forzar rebuild
docker build --no-cache -t pmo-python-api:latest .
```

---

## 📊 RESUMEN

| Acción | Comando |
|--------|---------|
| Clonar repo primera vez | `git clone URL` |
| Ver cambios | `git status` |
| Subir cambios | `git add . && git commit -m "msg" && git push` |
| Actualizar servidor | `git pull && ./update.sh` |
| Ver logs Docker | `docker logs -f pmo-python-api` |

---

¿Necesitas ayuda para configurar el repositorio de GitHub o tienes dudas sobre el flujo?
