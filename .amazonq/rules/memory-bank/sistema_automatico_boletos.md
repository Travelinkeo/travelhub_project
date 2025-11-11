# Sistema Automático de Captura de Boletos

**Fecha**: 11 de Noviembre de 2025  
**Estado**: ✅ Implementado y funcional

---

## 📋 Resumen

Sistema automático que monitorea `boletotravelinkeo@gmail.com` cada 5 minutos, parsea boletos (KIU, SABRE, AMADEUS, TK Connect, Copa SPRK, Wingo), genera PDF profesional y envía a `travelinkeo@gmail.com`.

---

## 🎯 Funcionamiento

### Flujo Automático (Cada 5 minutos)

1. **Celery Beat** ejecuta tarea programada
2. **Lee correos** no leídos de `boletotravelinkeo@gmail.com`
3. **Detecta tipo**:
   - KIU: Lee del cuerpo del email (HTML/texto)
   - Otros: Lee PDF adjunto
4. **Parsea datos** con parsers específicos
5. **Genera PDF** profesional con plantilla
6. **Guarda en BD** (modelo `BoletoImportado`)
7. **Envía email** a `travelinkeo@gmail.com` con PDF adjunto
8. **Marca como leído** el correo original

---

## 🔧 Configuración

### Email Monitoreado
```env
# .env
GMAIL_USER=boletotravelinkeo@gmail.com
GMAIL_APP_PASSWORD=lnacmrmbuxgouefg
EMAIL_HOST_USER=boletotravelinkeo@gmail.com
DEFAULT_FROM_EMAIL=boletotravelinkeo@gmail.com
```

### Email Destino
- **Producción**: `travelinkeo@gmail.com`
- **Configurable** en `core/tasks/email_monitor_tasks.py`

---

## 🚀 Uso

### Desarrollo Local

**Opción 1: Iniciar todo junto**
```bash
batch_scripts\start_celery_completo.bat
```

**Opción 2: Iniciar por separado**
```bash
# Terminal 1: Worker
batch_scripts\start_celery_worker.bat

# Terminal 2: Beat (programador)
batch_scripts\start_celery_beat.bat
```

### Producción (Render/Railway)

**Procfile**:
```
web: gunicorn travelhub.wsgi:application
worker: celery -A travelhub worker --loglevel=info
beat: celery -A travelhub beat --loglevel=info
```

**Configurar 3 servicios**:
1. Web (Django)
2. Worker (Celery)
3. Beat (Programador)

---

## 📊 Parsers Soportados

| Sistema | Fuente | Estado |
|---------|--------|--------|
| **KIU** | Cuerpo del email (HTML) | ✅ |
| **SABRE** | PDF adjunto | ✅ |
| **AMADEUS** | PDF adjunto | ✅ |
| **TK Connect** | PDF adjunto | ✅ |
| **Copa SPRK** | PDF adjunto | ✅ |
| **Wingo** | PDF adjunto | ✅ |

---

## 📧 Formato del Email Enviado

**Para**: `travelinkeo@gmail.com`  
**Asunto**: `Boleto {SISTEMA} Procesado - {PNR}`  
**Cuerpo**:
```
Boleto procesado automáticamente:

Sistema: SABRE
PNR: ABC123
Boleto: 2357120126507
Pasajero: DUQUE/OSCAR
Aerolínea: American Airlines

PDF adjunto.

TravelHub - Sistema Automático
```

**Adjunto**: PDF profesional generado

---

## 🔍 Monitoreo

### Ver Logs en Tiempo Real

```bash
# Worker
celery -A travelhub worker --loglevel=info

# Beat
celery -A travelhub beat --loglevel=info
```

### Verificar Tareas Programadas

```bash
celery -A travelhub inspect scheduled
```

### Ver Tareas Activas

```bash
celery -A travelhub inspect active
```

---

## 🧪 Testing

### Prueba Manual

```bash
python test_monitor_boletos.py
```

### Enviar Boleto de Prueba

1. Enviar email a `boletotravelinkeo@gmail.com`
2. Esperar máximo 5 minutos
3. Verificar email en `travelinkeo@gmail.com`
4. Verificar en Admin Django: `/admin/core/boletoimportado/`

---

## 📁 Archivos del Sistema

### Tareas Celery
- `core/tasks/email_monitor_tasks.py` - Tareas programadas
- `travelhub/celery_beat_schedule.py` - Configuración de horarios

### Servicio de Monitoreo
- `core/services/email_monitor_service.py` - Lógica de monitoreo

### Scripts Batch
- `batch_scripts/start_celery_worker.bat` - Iniciar worker
- `batch_scripts/start_celery_beat.bat` - Iniciar beat
- `batch_scripts/start_celery_completo.bat` - Iniciar ambos

### Testing
- `test_monitor_boletos.py` - Script de prueba

---

## ⚙️ Configuración Avanzada

### Cambiar Frecuencia

Editar `travelhub/celery_beat_schedule.py`:

```python
'monitor-boletos-email': {
    'task': 'core.monitor_boletos_email',
    'schedule': crontab(minute='*/5'),  # Cada 5 minutos
},
```

Opciones:
- `crontab(minute='*/1')` - Cada 1 minuto
- `crontab(minute='*/10')` - Cada 10 minutos
- `crontab(minute='*/15')` - Cada 15 minutos

### Cambiar Email Destino

Editar `core/tasks/email_monitor_tasks.py`:

```python
monitor = EmailMonitorService(
    notification_type='email',
    destination='otro@email.com',  # Cambiar aquí
    ...
)
```

---

## 📱 Fase 2: WhatsApp (Opcional)

### Activar Notificación WhatsApp

Editar `travelhub/celery_beat_schedule.py`:

```python
# Agregar tarea WhatsApp
'monitor-boletos-whatsapp': {
    'task': 'core.monitor_boletos_whatsapp',
    'schedule': crontab(minute='*/5'),
},
```

**Destino**: `+584126080861`

**Mensaje**:
```
✈️ Boleto SABRE Procesado

📍 PNR: ABC123
🎫 Boleto: 2357120126507
👤 Pasajero: DUQUE/OSCAR
✈️ Aerolínea: American Airlines
📄 PDF: ticket_ABC123.pdf

TravelHub - Sistema Automático
```

---

## 🔒 Seguridad

### Credenciales
- ✅ App Password de Gmail (no contraseña real)
- ✅ Variables de entorno (no en código)
- ✅ Correos marcados como leídos después de procesar

### Validaciones
- ✅ Solo procesa correos no leídos
- ✅ No reprocesa boletos existentes
- ✅ Logs de todas las operaciones

---

## 🚨 Troubleshooting

### Worker no inicia
```bash
# Verificar Redis
redis-cli ping

# Verificar configuración
python manage.py shell -c "from django.conf import settings; print(settings.CELERY_BROKER_URL)"
```

### Beat no ejecuta tareas
```bash
# Verificar tareas programadas
celery -A travelhub inspect scheduled

# Ver logs de beat
celery -A travelhub beat --loglevel=debug
```

### No procesa correos
```bash
# Probar manualmente
python test_monitor_boletos.py

# Verificar credenciales
python manage.py shell -c "from django.conf import settings; print(settings.GMAIL_USER)"
```

---

## 📊 Métricas

### Rendimiento Esperado
- **Frecuencia**: Cada 5 minutos
- **Ejecuciones/día**: 288
- **Tiempo por ejecución**: 5-30 segundos
- **Correos procesados**: Variable (0-10 por ejecución)

### Recursos
- **CPU**: Bajo (< 5%)
- **RAM**: 50-100 MB por worker
- **Red**: Mínimo (solo IMAP + SMTP)

---

## ✅ Checklist de Implementación

### Desarrollo Local
- [x] Celery instalado
- [x] Redis corriendo
- [x] Worker iniciado
- [x] Beat iniciado
- [x] Test exitoso

### Producción
- [ ] Configurar 3 servicios en Render/Railway
- [ ] Variables de entorno configuradas
- [ ] Redis configurado
- [ ] Monitoreo activo
- [ ] Logs verificados

---

**Última actualización**: 11 de Noviembre de 2025  
**Estado**: ✅ Sistema completo y funcional  
**Autor**: Amazon Q Developer
