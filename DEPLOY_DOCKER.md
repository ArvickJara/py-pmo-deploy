# 🐳 Despliegue con Docker - Sin permisos sudo

## ✨ Ventajas de usar Docker

- ✅ **No necesitas permisos sudo** para instalar dependencias del sistema
- ✅ Todas las librerías incluidas (Tesseract, Poppler, OpenCV)
- ✅ Funciona igual en local y en producción
- ✅ Fácil de actualizar y revertir cambios
- ✅ Aislamiento completo del sistema

---

## 📋 Requisitos en el Servidor

Solo necesitas que Docker esté instalado. Si tu proveedor (Cloud Panel) ya tiene Docker, estás listo. Si no:

```bash
# Tu administrador del servidor solo necesita instalar Docker una vez:
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**Nota**: Una vez Docker instalado, NO necesitas más permisos sudo.

---

## 🚀 Despliegue Paso a Paso

### 1. Preparar archivos en local

```powershell
# En Windows, desde la raíz del proyecto
cd C:\Users\AmarilisProject\Development\pmo-gore\python-deploy

# Crear archivo .env para Docker
Copy-Item .env.docker .env

# Editar variables si es necesario
notepad .env
```

### 2. Comprimir TODO el proyecto

```powershell
# Comprimir python-deploy completo (incluye Dockerfile)
cd C:\Users\AmarilisProject\Development\pmo-gore
Compress-Archive -Path python-deploy\* -DestinationPath python-deploy-docker.zip -Force
```

### 3. Subir al servidor

Sube `python-deploy-docker.zip` a tu servidor en:
```
/home/cloudpanel/htdocs/pmopy.sistemasudh.com/
```

### 4. Conectar al servidor

```bash
ssh tu-usuario@pmopy.sistemasudh.com
```

### 5. Extraer y preparar

```bash
cd /home/cloudpanel/htdocs/pmopy.sistemasudh.com/

# Extraer archivos
unzip -o python-deploy-docker.zip

# Verificar que Dockerfile está presente
ls -la Dockerfile docker-compose.yml

# Crear .env si no existe
cp .env.docker .env
nano .env  # Editar si es necesario
```

### 6. Construir la imagen Docker

```bash
# Construir imagen (solo la primera vez o cuando cambien dependencias)
docker build -t pmo-python-api:latest .

# Esto tomará unos minutos la primera vez
# Instala Python, Tesseract, Poppler, OpenCV, etc.
```

### 7. Iniciar el contenedor

```bash
# Opción A: Usar docker-compose (recomendado)
docker-compose up -d

# Opción B: Usar docker run directamente
docker run -d \
  --name pmo-python-api \
  --restart unless-stopped \
  -p 5001:5001 \
  -v $(pwd)/temp:/app/temp \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  pmo-python-api:latest
```

### 8. Verificar que funciona

```bash
# Ver logs
docker logs pmo-python-api

# Ver logs en tiempo real
docker logs -f pmo-python-api

# Verificar que el contenedor está corriendo
docker ps

# Probar la API
curl http://localhost:5001/health
```

Deberías ver:
```json
{
  "status": "healthy",
  "service": "pmo-python-api",
  "modules": {
    "bind_pdf": true,
    "admisibilidad": true
  }
}
```

### 9. Configurar Nginx (si es necesario)

Si usas Nginx como proxy reverso:

```nginx
server {
    listen 80;
    server_name pmopy.sistemasudh.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Importante para archivos grandes
        client_max_body_size 50M;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

---

## 🔄 Actualizaciones Futuras

Cuando hagas cambios en el código:

```bash
# 1. Detener contenedor actual
docker stop pmo-python-api
docker rm pmo-python-api

# 2. Subir nuevos archivos (o hacer git pull si usas git)
# unzip -o python-deploy-docker.zip

# 3. Reconstruir imagen solo si cambió requirements.txt
docker build -t pmo-python-api:latest .

# 4. Reiniciar
docker-compose up -d
# O si usaste docker run, ejecutar el comando de nuevo
```

**Actualización rápida sin rebuild** (si solo cambiaste código Python):

```bash
# Simplemente reinicia el contenedor
docker restart pmo-python-api
```

---

## 📊 Comandos Útiles

```bash
# Ver contenedores corriendo
docker ps

# Ver todos los contenedores
docker ps -a

# Ver logs
docker logs pmo-python-api
docker logs -f pmo-python-api  # Seguir logs en tiempo real
docker logs --tail 100 pmo-python-api  # Últimas 100 líneas

# Entrar al contenedor (debugging)
docker exec -it pmo-python-api bash

# Ver uso de recursos
docker stats pmo-python-api

# Detener contenedor
docker stop pmo-python-api

# Iniciar contenedor
docker start pmo-python-api

# Reiniciar contenedor
docker restart pmo-python-api

# Eliminar contenedor
docker rm pmo-python-api

# Ver imágenes
docker images

# Eliminar imagen
docker rmi pmo-python-api:latest

# Limpiar recursos no usados
docker system prune -a
```

---

## 🔧 Troubleshooting

### El contenedor no inicia

```bash
# Ver logs detallados
docker logs pmo-python-api

# Ver eventos
docker events &
docker start pmo-python-api
```

### Puerto 5001 ya en uso

```bash
# Ver qué está usando el puerto
netstat -tlnp | grep 5001

# Cambiar puerto en docker-compose.yml
ports:
  - "5002:5001"  # Puerto externo:interno
```

### Problemas con permisos de archivos

```bash
# Dar permisos a carpetas temp y logs
chmod 777 temp logs
```

### El modelo YOLO no se encuentra

```bash
# Verificar que el modelo está en la imagen
docker exec pmo-python-api ls -lh /app/models/

# Si falta, copiarlo al contenedor
docker cp models/yolov8n.pt pmo-python-api:/app/models/
docker restart pmo-python-api
```

### Memoria insuficiente

```bash
# Limitar memoria del contenedor
docker run -d --memory="2g" --memory-swap="2g" ...
```

---

## 🎯 Ventajas de esta Configuración

1. **Sin dependencias del sistema**: Todo está en el contenedor
2. **Portable**: Funciona en cualquier servidor con Docker
3. **Fácil rollback**: `docker run` con tag anterior
4. **Logs centralizados**: `docker logs`
5. **Health checks**: Docker reinicia si falla
6. **Aislamiento**: No afecta otras aplicaciones

---

## 📦 Estructura de Archivos

```
python-deploy/
├── Dockerfile              # Definición de la imagen
├── docker-compose.yml      # Orquestación
├── gunicorn_config.py      # Config de Gunicorn
├── .env                    # Variables de entorno
├── .dockerignore           # Archivos a ignorar
├── app.py                  # Aplicación principal
├── requirements.txt        # Dependencias Python
├── modules/                # Módulos
│   ├── bind_pdf/
│   └── admisibilidad/
├── models/                 # Modelos ML
│   └── yolov8n.pt
├── temp/                   # Archivos temporales
└── logs/                   # Logs
```

---

## 🚀 Despliegue Completo (Resumen)

```bash
# 1. Subir archivos al servidor
cd /home/cloudpanel/htdocs/pmopy.sistemasudh.com/
unzip -o python-deploy-docker.zip

# 2. Crear .env
cp .env.docker .env

# 3. Construir y correr
docker-compose up -d

# 4. Verificar
curl http://localhost:5001/health
docker logs -f pmo-python-api

# ¡Listo! 🎉
```
