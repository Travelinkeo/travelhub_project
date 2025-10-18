# Scripts Batch de TravelHub

Esta carpeta contiene scripts `.bat` para automatizar tareas comunes en Windows.

## 🚀 Scripts de Inicio

### `start_completo.bat`
Inicia el backend Django y el frontend Next.js simultáneamente.

```bash
.\batch_scripts\start_completo.bat
```

**Qué hace**:
- Activa el entorno virtual Python
- Inicia Django en puerto 8000
- Inicia Next.js en puerto 3000

---

### `start_frontend.bat`
Inicia solo el frontend Next.js.

```bash
.\batch_scripts\start_frontend.bat
```

---

## 🌐 Scripts de Exposición Pública

### `iniciar_con_ngrok.bat`
Expone el backend Django usando ngrok.

```bash
.\batch_scripts\iniciar_con_ngrok.bat
```

**Requisitos**: `ngrok.exe` en `tools_bin/`

---

### `iniciar_completo_ngrok.bat`
Inicia backend + frontend y expone ambos con ngrok.

```bash
.\batch_scripts\iniciar_completo_ngrok.bat
```

---

### `start_completo_publico.bat`
Inicia todo y expone públicamente.

```bash
.\batch_scripts\start_completo_publico.bat
```

---

### `exponer_frontend.bat`
Expone solo el frontend con ngrok.

```bash
.\batch_scripts\exponer_frontend.bat
```

---

### `start_cloudflare.bat`
Expone usando Cloudflare Tunnel.

```bash
.\batch_scripts\start_cloudflare.bat
```

**Requisitos**: `cloudflared.exe` en `tools_bin/`

---

### `start_localtunnel.bat`
Expone usando localtunnel.

```bash
.\batch_scripts\start_localtunnel.bat
```

**Requisitos**: `npm install -g localtunnel`

---

### `start_serveo.bat`
Expone usando serveo.net (SSH tunnel).

```bash
.\batch_scripts\start_serveo.bat
```

---

### `ngrok_pooling.bat`
Mantiene ngrok activo con reconexión automática.

```bash
.\batch_scripts\ngrok_pooling.bat
```

---

## 💰 Scripts de Contabilidad

### `sincronizar_bcv.bat`
Actualiza la tasa de cambio BCV automáticamente.

```bash
.\batch_scripts\sincronizar_bcv.bat
```

**Qué hace**:
- Consulta la API del BCV
- Actualiza la tasa USD/BSD en la base de datos
- Registra log de la operación

**Automatización**: Configura con Task Scheduler para ejecución diaria.

---

### `cierre_mensual.bat`
Ejecuta el proceso de cierre contable mensual.

```bash
.\batch_scripts\cierre_mensual.bat
```

**Qué hace**:
- Provisiona INATUR (1% sobre ingresos)
- Genera reportes contables
- Cierra el período contable

**Uso**: Ejecutar el último día de cada mes.

---

## 📧 Scripts de Notificaciones

### `enviar_recordatorios.bat`
Envía recordatorios de pago a clientes con saldo pendiente.

```bash
.\batch_scripts\enviar_recordatorios.bat
```

**Qué hace**:
- Busca ventas con saldo pendiente > 3 días
- Envía emails de recordatorio
- Registra log de envíos

**Automatización**: Configura con Task Scheduler para ejecución semanal.

---

## 🧪 Scripts de Testing

### `run_tests_fase5.bat`
Ejecuta todos los tests de Fase 5 (Mejoras de Calidad).

```bash
.\batch_scripts\run_tests_fase5.bat
```

**Qué hace**:
- Ejecuta 8 suites de tests
- Genera reporte de cobertura
- Valida calidad del código

**Tests incluidos**:
- Tests de notificaciones
- Tests de caché
- Tests de Celery
- Tests de ViewSets
- Tests de optimización de queries
- Tests de middleware
- Tests de comandos
- Tests adicionales de parsers

---

## 📋 Configuración de Tareas Programadas

### Sincronización BCV (Diaria)
```
Tarea: Sincronizar BCV
Frecuencia: Diaria a las 9:00 AM
Script: sincronizar_bcv.bat
```

### Recordatorios de Pago (Semanal)
```
Tarea: Recordatorios de Pago
Frecuencia: Lunes a las 10:00 AM
Script: enviar_recordatorios.bat
```

### Cierre Mensual (Mensual)
```
Tarea: Cierre Contable
Frecuencia: Último día del mes a las 11:59 PM
Script: cierre_mensual.bat
```

**Guía completa**: Ver `docs/deployment/CONFIGURAR_TASK_SCHEDULER.md`

---

## 🛠️ Requisitos

### Herramientas Necesarias
- Python 3.12+ con entorno virtual activado
- Node.js 18+ para frontend
- ngrok (opcional, en `tools_bin/`)
- cloudflared (opcional, en `tools_bin/`)

### Variables de Entorno
Asegúrate de tener configurado `.env` con:
```
SECRET_KEY=...
DEBUG=True
DATABASE_URL=...
GEMINI_API_KEY=...
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
```

---

## 📝 Notas

- Todos los scripts asumen que estás en la raíz del proyecto
- Los logs se guardan en `logs/` (se crea automáticamente)
- Para producción, ajusta las rutas en los scripts según tu instalación

---

## 🆘 Solución de Problemas

### Error: "No se encuentra el comando python"
Asegúrate de tener Python en el PATH o usa la ruta completa:
```batch
C:\Python312\python.exe manage.py runserver
```

### Error: "No se puede activar el entorno virtual"
Verifica que existe `venv\Scripts\activate.bat`:
```bash
python -m venv venv
```

### Error: "ngrok no encontrado"
Descarga ngrok y colócalo en `tools_bin/`:
```bash
https://ngrok.com/download
```

---

## 📚 Documentación Relacionada

- [INSTRUCCIONES_NGROK.md](../docs_archive/INSTRUCCIONES_NGROK.md)
- [CIERRE_MENSUAL.md](../docs_archive/CIERRE_MENSUAL.md)
- [NOTIFICACIONES.md](../docs_archive/NOTIFICACIONES.md)
- [COMPARTIR_EN_RED_LOCAL.md](../docs_archive/COMPARTIR_EN_RED_LOCAL.md)
