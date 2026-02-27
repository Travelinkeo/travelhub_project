# Manual de Desarrollo TravelHub

**Versión:** 1.0
**Última Actualización:** 28 de Noviembre de 2025

Guía para configurar el entorno de desarrollo y contribuir al código.

## 1. Requisitos Previos
*   **Python:** 3.13.5 o superior.
*   **Base de Datos:** PostgreSQL (Localhost).
*   **Redis:** Necesario para Celery (puede usarse Memcached o DB en dev simple, pero Redis es recomendado).
*   **Sistema Operativo:** Windows 10/11 (PowerShell) o Linux/Mac.

## 2. Configuración Inicial (Setup)

### 1. Clonar y Entorno Virtual
```powershell
git clone <repo-url>
cd travelhub_project
python -m venv venv
.\venv\Scripts\activate
```

### 2. Instalar Dependencias
```powershell
pip install -r requirements.txt
```

### 3. Variables de Entorno (.env)
Crear un archivo `.env` en la raíz con:
```ini
DEBUG=True
SECRET_KEY=tu_clave_secreta_local
DATABASE_URL=postgres://usuario:password@localhost:5432/travelhub_db
REDIS_URL=redis://localhost:6379/0
# Email (para pruebas de parser)
EMAIL_HOST_USER=boletotravelinkeo@gmail.com
EMAIL_HOST_PASSWORD=tu_app_password
```

### 4. Base de Datos
```powershell
python manage.py migrate
python manage.py loaddata fixtures/plan_cuentas_venezuela.json
python manage.py createsuperuser
```

## 3. Comandos Diarios

### Correr Servidor
```powershell
python manage.py runserver
```

### Correr Worker de Celery (Procesamiento de Emails)
En una terminal separada:
```powershell
celery -A travelhub worker --pool=solo -l info
```
*(Nota: En Windows usar `--pool=solo`)*

### Correr Tareas Periódicas (Beat)
```powershell
celery -A travelhub beat -l info
```

## 4. Guía de Estilo y Arquitectura

### Estructura de Apps
*   **`core`**: Solo modelos base y utilidades transversales.
*   **`core/services/`**: Aquí va la Lógica de Negocio. **No escribir lógica compleja en las Vistas.**
    *   Bien: `VentaAutomationService.crear_venta(...)`
    *   Mal: Calcular comisiones dentro de `views.py`.

### Frontend (Tailwind + HTMX)
*   Usar clases de utilidad de Tailwind directamente en el HTML.
*   Para interactividad, preferir atributos `hx-*` (HTMX) antes que escribir JavaScript.
*   **Glassmorphism:** Usar la clase `.glass-panel` para contenedores.

### Reglas de Git
1.  **Ramas:** `feature/nombre-feature` o `fix/nombre-bug`.
2.  **Commits:** Descriptivos (ej: "feat: agrega calculo automatico de comision").
3.  **Documentación:** Actualizar `docs/` antes de hacer merge.
