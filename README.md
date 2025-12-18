# PMO Python API - Servicio Independiente con Docker

## 📋 Descripción

API Python independiente que proporciona servicios de:
- **bind-pdf**: Procesamiento de PDFs con YOLO + OCR (detección de foliación)
- **admisibilidad**: Verificación de documentos

**Servidor**: pmopy.sistemasudh.com  
**Puerto**: 5001  
**Consumida por**: file-review (Node.js) en otro servidor

---

## 🐳 Despliegue con Docker (RECOMENDADO)

### Ventajas
- ✅ NO necesitas permisos sudo
- ✅ Todas las dependencias incluidas (Tesseract, Poppler, OpenCV)
- ✅ Servicio aislado e independiente
- ✅ Fácil de mantener

### Opción 1: Con GitHub (Recomendado)

```bash
# En el servidor Python (pmopy.sistemasudh.com)
cd /home/cloudpanel/htdocs/pmopy.sistemasudh.com

# Clonar solo python-deploy
git clone https://github.com/TU-USUARIO/pmo-gore.git temp-repo
mv temp-repo/python-deploy/* .
rm -rf temp-repo

# O si clonas todo el repo
git clone https://github.com/TU-USUARIO/pmo-gore.git
cd pmo-gore/python-deploy

# Configurar
cp .env.docker .env
nano .env  # Ajustar CORS_ORIGINS si es necesario

# Construir y ejecutar
docker build -t pmo-python-api:latest .
docker-compose up -d

# Verificar
curl http://localhost:5001/health
```

### Opción 2: Subir ZIP manualmente

```bash
# Subir python-deploy-docker.zip al servidor

cd /home/cloudpanel/htdocs/pmopy.sistemasudh.com
unzip -o python-deploy-docker.zip
cp .env.docker .env
nano .env

docker build -t pmo-python-api:latest .
docker-compose up -d
```

---

## 🔧 Configuración

### Variables de Entorno (.env)

```env
# Flask
FLASK_ENV=production
FLASK_DEBUG=False
PORT=5001

# Roboflow (para detección YOLO)
ROBOFLOW_API_KEY=IkzCz5uodkvvJigVmhen
MODEL_ID=foliacionpdf-u6br4/2

# CORS - Permitir acceso desde el servidor Node.js
CORS_ORIGINS=https://pmonode.sistemasudh.com,https://pmopy.sistemasudh.com

# Paths internos del contenedor (no cambiar)
UPLOAD_FOLDER=/app/temp
MODEL_PATH=/app/models/yolov8n.pt
TESSERACT_CMD=/usr/bin/tesseract
```

---

## 🌐 Configuración de Nginx

Para que el servicio sea accesible desde internet (y desde file-review):

```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name pmopy.sistemasudh.com;

    # SSL configurado por Cloud Panel automáticamente

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

## 🔗 Integración con file-review

En el servidor de Node.js (pmonode.sistemasudh.com), file-review consume esta API:

**Configuración en file-review/.env:**
```env
PYTHON_API_URL=https://pmopy.sistemasudh.com
```

**Ejemplo de llamada desde Node.js:**
```javascript
const axios = require('axios');

// Procesar PDF
const formData = new FormData();
formData.append('file', pdfFile);

const response = await axios.post(
  'https://pmopy.sistemasudh.com/process-pdf',
  formData,
  {
    params: {
      dpi: 300,
      ocr: true,
      digits_only: true
    }
  }
);
```

---

## 📊 Endpoints Disponibles

### Health Check
```bash
GET /health
```

### Procesamiento de PDF (Principal)
```bash
POST /process-pdf
```
Parámetros:
- `file`: Archivo PDF (multipart/form-data)
- `dpi`: DPI para conversión (default: 300)
- `ocr`: Ejecutar OCR (default: true)
- `digits_only`: Solo dígitos (default: true)

### Otros Endpoints
```bash
GET / - Información del servicio
POST /api/bind-pdf/process-pdf - Alias del endpoint principal
POST /api/admisibilidad/verificar - Verificación de documentos
```

---

## 🔄 Actualizaciones

### Con Git
```bash
cd /home/cloudpanel/htdocs/pmopy.sistemasudh.com
git pull
docker-compose down
docker build -t pmo-python-api:latest .
docker-compose up -d
```

### Script automático
```bash
./update-python.sh
```

---

## 📋 Comandos Útiles

```bash
# Ver logs
docker logs -f pmo-python-api

# Estado
docker ps | grep pmo-python-api

# Reiniciar
docker-compose restart

# Detener
docker-compose down

# Iniciar
docker-compose up -d

# Reconstruir
docker build --no-cache -t pmo-python-api:latest .

# Ver uso de recursos
docker stats pmo-python-api

# Entrar al contenedor
docker exec -it pmo-python-api bash

# Ver archivos del modelo
docker exec pmo-python-api ls -lh /app/models/
```

---

## 🔍 Troubleshooting

### API no responde
```bash
# Ver logs
docker logs --tail 100 pmo-python-api

# Verificar que el contenedor está corriendo
docker ps

# Verificar puerto
netstat -tlnp | grep 5001

# Reiniciar
docker-compose restart
```

### CORS errors desde file-review
Asegúrate que `CORS_ORIGINS` en `.env` incluye el dominio de file-review:
```env
CORS_ORIGINS=https://pmonode.sistemasudh.com,https://pmopy.sistemasudh.com
```

### Modelo YOLO no carga
```bash
# Verificar que existe
docker exec pmo-python-api ls -lh /app/models/yolov8n.pt

# Ver logs de inicialización
docker logs pmo-python-api | grep -i "modelo\|yolo\|ultralytics"
```

---

## 📦 Estructura del Proyecto

```
python-deploy/
├── Dockerfile              # Imagen Docker con dependencias
├── docker-compose.yml      # Orquestación
├── app.py                  # Aplicación principal
├── requirements.txt        # Dependencias Python
├── gunicorn_config.py      # Config servidor producción
├── .env.docker            # Plantilla variables entorno
├── modules/               # Módulos de la API
│   ├── bind_pdf/
│   │   ├── core.py       # Funciones YOLO + OCR
│   │   └── api.py        # Endpoints
│   └── admisibilidad/
│       ├── verificador_admisibilidad.py
│       └── api.py
├── models/
│   └── yolov8n.pt        # Modelo YOLO
├── temp/                 # Archivos temporales
└── logs/                 # Logs del servicio
```

---

## 🚀 Testing Local (Windows)

Si quieres probar antes de subir:

```powershell
cd python-deploy

# Construir
docker build -t pmo-python-api:latest .

# Ejecutar
docker-compose up

# Probar
curl http://localhost:5001/health
```

---

## 📞 Contacto API

- **Base URL**: https://pmopy.sistemasudh.com
- **Documentación**: GET /
- **Health**: GET /health
- **Principal endpoint**: POST /process-pdf

---

## 📖 Más Información

- `DEPLOY_DOCKER.md` - Guía completa de despliegue
- `DEPLOY_GITHUB.md` - Flujo con Git
- `GITHUB_QUICKSTART.md` - Inicio rápido Git
