# Carbon Snapshot Console

Sistema de seguimiento y gestión de huella de carbono desarrollado con Flask.

## Requisitos

- Python 3.11+
- Docker y Docker Compose (opcional, recomendado)
- Redis (para tareas asíncronas con Celery)

## Instalación

### Opción 1: Con Docker (Recomendado)

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd vemo

# Copiar archivo de configuración
cp .env.example .env

# Levantar los contenedores
docker compose up --build

# En otra terminal, ejecutar migraciones y datos de prueba
docker compose exec web flask db upgrade
docker compose exec web python seed_data.py
```

La aplicación estará disponible en `http://localhost:8000`

### Opción 2: Instalación Local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o en Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de configuración
cp .env.example .env

# Ejecutar migraciones
flask db upgrade

# Cargar datos de prueba
python seed_data.py

# Ejecutar el servidor
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Ejecución de Migraciones

```bash
# Con Docker
docker compose exec web flask db upgrade

# Sin Docker
flask db upgrade
```

Para crear nuevas migraciones después de modificar modelos:

```bash
flask db migrate -m "Descripción del cambio"
flask db upgrade
```

## Ejecución de Tests

```bash
# Con Docker
docker compose exec web pytest

# Sin Docker
pytest

# Con cobertura
pytest --cov=. --cov-report=html
```

## Cargar Datos de Prueba (Seed)

```bash
# Con Docker
docker compose exec web python seed_data.py

# Sin Docker
python seed_data.py
```

Esto crea los siguientes usuarios:

**Usuarios Internos (Backoffice):**
- `admin@carbonconsole.com` / `admin123`
- `manager@carbonconsole.com` / `manager123`

**Usuarios Públicos (API Pública):**
- `user1@example.com` / `user123`
- `user2@example.com` / `user123`

## Obtener JWT (Tokens de Autenticación)

### Para usuarios internos (API interna / Backoffice)

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@carbonconsole.com", "password": "admin123"}'
```

Respuesta:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {"id": 1, "email": "admin@carbonconsole.com", "is_internal": true}
}
```

### Para usuarios públicos (API pública)

```bash
curl -X POST http://localhost:8000/public/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user1@example.com", "password": "user123"}'
```

## Endpoints de la API

### API Interna (`/api`)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/login/` | Login interno, devuelve JWT | No |
| POST | `/api/operations/` | Crear operación | JWT (interno) |
| GET | `/api/operations/` | Listar operaciones | JWT (interno) |

### API Pública (`/public`)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/public/auth/login/` | Login público, devuelve JWT | No |
| POST | `/public/operations/` | Crear operación (envía email) | JWT (público) |

### Recibos PDF

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/operations/<id>/receipt/` | Descargar PDF de operación | JWT |

### Backoffice HTML (`/bo`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET/POST | `/bo/login` | Página de login |
| GET | `/bo/logout` | Cerrar sesión |
| GET | `/bo/operations/` | Listado de operaciones |
| GET | `/bo/operations/<id>/` | Detalle de operación |
| GET | `/bo/operations/<id>/pdf` | Descargar PDF |

## Ejemplos de Uso de la API

### Crear una operación (API interna)

```bash
curl -X POST http://localhost:8000/api/operations/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <tu-token-jwt>" \
  -d '{
    "type": "electricity",
    "amount": 150.5,
    "user_email": "cliente@ejemplo.com"
  }'
```

### Crear una operación (API pública)

```bash
curl -X POST http://localhost:8000/public/operations/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <tu-token-jwt>" \
  -d '{
    "type": "transportation",
    "amount": 50.0,
    "user_email": "user1@example.com"
  }'
```

## Envío de Emails

El sistema envía emails de confirmación cuando se crean operaciones desde la API pública.

### Configuración para desarrollo (consola)

Por defecto, los emails se procesan de forma asíncrona con Celery y Redis. Para ver los emails en la consola durante desarrollo, revisa los logs del worker:

```bash
docker compose logs -f worker
```

### Configuración para producción

Configurar las siguientes variables en `.env`:

```env
MAIL_SERVER=smtp.tuservidor.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu-usuario
MAIL_PASSWORD=tu-contraseña
MAIL_DEFAULT_SENDER=noreply@tudominio.com
```

## Cálculo del Carbon Score

El sistema utiliza una **fórmula local** para calcular el `carbon_score`:

```
carbon_score = amount * factor
```

Factores por tipo de operación:
- `electricity`: 0.5
- `transportation`: 2.3
- `heating`: 1.8
- `manufacturing`: 3.2
- Otros: 1.0 (por defecto)

**Nota:** No se implementó integración con API externa (Climatiq, Carbon Interface). El sistema está preparado para añadirla en el futuro mediante el servicio `services/carbon_calculator.py`.

## Estructura del Proyecto

```
vemo/
├── app.py                 # Aplicación Flask y configuración
├── models.py              # Modelos SQLAlchemy (User, Operation)
├── wsgi.py                # Punto de entrada WSGI
├── celery_worker.py       # Configuración de Celery
├── seed_data.py           # Script de datos de prueba
├── requirements.txt       # Dependencias Python
├── routes/
│   ├── internal_api.py    # Endpoints API interna
│   ├── public_api.py      # Endpoints API pública
│   ├── receipts.py        # Generación de PDF
│   └── backoffice.py      # Backoffice HTML
├── services/
│   ├── carbon_calculator.py  # Cálculo de carbon score
│   └── email_service.py      # Envío de emails
├── templates/             # Plantillas Jinja2 (Backoffice)
├── migrations/            # Migraciones de base de datos
├── tests/                 # Tests automatizados
├── docker-compose.yml     # Configuración Docker (producción)
└── docker-compose.dev.yml # Configuración Docker (desarrollo)
```

## Variables de Entorno

Ver `.env.example` para todas las opciones disponibles:

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `SECRET_KEY` | Clave secreta de Flask | (requerido) |
| `JWT_SECRET_KEY` | Clave para firmar JWT | (requerido) |
| `DATABASE_URL` | URL de conexión a BD | `sqlite:///carbon_console.db` |
| `REDIS_URL` | URL de conexión a Redis | `redis://localhost:6379/0` |
| `MAIL_SERVER` | Servidor SMTP | `localhost` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
