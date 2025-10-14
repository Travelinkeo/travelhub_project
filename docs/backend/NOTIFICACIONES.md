# Sistema de Notificaciones TravelHub

Sistema completo de notificaciones multicanal (Email + WhatsApp) para eventos de ventas.

## 📋 Características

### Notificaciones Automáticas
- ✅ Confirmación de venta creada
- 🔄 Notificación de cambio de estado
- 💰 Confirmación de pago recibido
- ⏰ Recordatorio de pago pendiente (comando manual/cron)

### Canales Soportados
- 📧 **Email** (Gmail SMTP) - Plantillas HTML profesionales
- 📱 **WhatsApp** (Twilio API) - Mensajes formateados con emojis

---

## 🚀 Configuración

### 1. Instalar Dependencias

```bash
pip install twilio
# o
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Edita tu archivo `.env`:

```env
# Email (Ya configurado)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=travelinkeo@gmail.com
EMAIL_HOST_PASSWORD=tddfugdgvsfgtgwq
DEFAULT_FROM_EMAIL=travelinkeo@gmail.com

# WhatsApp / Twilio (Nuevo)
WHATSAPP_NOTIFICATIONS_ENABLED=True
TWILIO_ACCOUNT_SID=tu_account_sid_aqui
TWILIO_AUTH_TOKEN=tu_auth_token_aqui
TWILIO_WHATSAPP_NUMBER=+14155238886
```

### 3. Obtener Credenciales de Twilio

#### Paso 1: Crear Cuenta en Twilio
1. Ve a https://www.twilio.com/try-twilio
2. Regístrate (obtienes $15 USD de crédito gratis)
3. Verifica tu número de teléfono

#### Paso 2: Obtener Credenciales
1. En el Dashboard de Twilio, copia:
   - **Account SID** → `TWILIO_ACCOUNT_SID`
   - **Auth Token** → `TWILIO_AUTH_TOKEN`

#### Paso 3: Configurar WhatsApp Sandbox (Desarrollo)
1. En Twilio Console, ve a: **Messaging** → **Try it out** → **Send a WhatsApp message**
2. Sigue las instrucciones para conectar tu WhatsApp personal
3. Envía el código de activación desde tu WhatsApp al número de Twilio
4. Copia el número de WhatsApp de Twilio → `TWILIO_WHATSAPP_NUMBER`

**Formato del número:** `+14155238886` (incluye el `+` y código de país)

#### Paso 4: Producción (Opcional)
Para usar en producción con clientes reales:
1. Solicita aprobación de WhatsApp Business API en Twilio
2. Configura plantillas de mensajes aprobadas
3. Costo aproximado: $0.005 USD por mensaje

---

## 📱 Configurar Campo Teléfono en Cliente

El modelo `Cliente` debe tener un campo `telefono` para WhatsApp:

```python
# En personas/models.py
class Cliente(models.Model):
    # ... otros campos ...
    telefono = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text="Formato internacional: +584121234567"
    )
```

Si no existe, crear migración:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 🧪 Probar el Sistema

### Prueba Rápida de Email
```bash
python test_email.py
```

### Prueba Completa (Email + WhatsApp)
```bash
python test_email_notifications.py
```

### Prueba Manual de WhatsApp
```python
from core.whatsapp_notifications import enviar_whatsapp

# Enviar mensaje de prueba
enviar_whatsapp(
    '+584121234567',  # Tu número en formato internacional
    '¡Hola! Este es un mensaje de prueba de TravelHub 🌍'
)
```

---

## 🔧 Uso

### Notificaciones Automáticas

Las notificaciones se envían automáticamente cuando:

1. **Se crea una venta** con cliente asignado
2. **Cambia el estado** de una venta
3. **Se registra un pago** confirmado

No requiere configuración adicional, funciona con las señales de Django.

### Recordatorios de Pago

Enviar recordatorios manualmente:

```bash
# Enviar a ventas sin actualizar en 3 días (default)
python manage.py enviar_recordatorios_pago

# Enviar a ventas sin actualizar en 7 días
python manage.py enviar_recordatorios_pago --dias=7

# Simular sin enviar (dry-run)
python manage.py enviar_recordatorios_pago --dry-run
```

### Automatizar con Cron (Linux/Mac)

```bash
# Editar crontab
crontab -e

# Agregar línea (enviar diariamente a las 9 AM)
0 9 * * * cd /ruta/proyecto && /ruta/venv/bin/python manage.py enviar_recordatorios_pago --dias=3
```

### Automatizar con Task Scheduler (Windows)

1. Abrir **Programador de tareas**
2. Crear tarea básica
3. Configurar:
   - **Desencadenador:** Diariamente a las 9:00 AM
   - **Acción:** Iniciar programa
   - **Programa:** `C:\ruta\venv\Scripts\python.exe`
   - **Argumentos:** `manage.py enviar_recordatorios_pago --dias=3`
   - **Iniciar en:** `C:\Users\ARMANDO\travelhub_project`

---

## 🎨 Personalizar Plantillas

### Plantillas de Email (HTML)

Ubicación: `core/templates/core/emails/`

- `base_email.html` - Plantilla base
- `confirmacion_venta.html` - Confirmación de venta
- `cambio_estado.html` - Cambio de estado
- `confirmacion_pago.html` - Confirmación de pago
- `recordatorio_pago.html` - Recordatorio de pago

### Mensajes de WhatsApp

Editar: `core/whatsapp_notifications.py`

Los mensajes usan formato Markdown de WhatsApp:
- `*texto*` = negrita
- `_texto_` = cursiva
- Emojis soportados: 🌍 ✅ 🔄 💰 ⏰ 📋

---

## 🔐 Seguridad

### Proteger Credenciales

**NUNCA** subas el archivo `.env` a Git:

```bash
# Verificar que .env está en .gitignore
cat .gitignore | grep .env
```

### Rotar Credenciales

Si las credenciales se exponen:

1. **Gmail:** Revocar contraseña de aplicación y generar nueva
2. **Twilio:** Regenerar Auth Token en el dashboard

---

## 📊 Monitoreo

### Logs

Los envíos se registran en los logs de Django:

```python
# Ver logs en consola
python manage.py runserver

# Buscar en logs
grep "Notificación" logs/django.log
```

### Dashboard de Twilio

Ver estadísticas de WhatsApp:
- Mensajes enviados
- Mensajes entregados
- Mensajes fallidos
- Costo por mensaje

---

## 💰 Costos

### Email (Gmail)
- **Gratis** hasta 500 emails/día
- Para más volumen: usar SendGrid, AWS SES, etc.

### WhatsApp (Twilio)
- **Sandbox (desarrollo):** Gratis
- **Producción:** ~$0.005 USD por mensaje
- **Ejemplo:** 1000 mensajes/mes = $5 USD

---

## 🐛 Troubleshooting

### Email no se envía

```bash
# Verificar configuración
python test_email.py

# Revisar credenciales en .env
# Verificar que Gmail permite "Aplicaciones menos seguras"
```

### WhatsApp no se envía

```bash
# Verificar que Twilio está instalado
pip show twilio

# Verificar credenciales
python -c "from core.whatsapp_notifications import get_twilio_client; print(get_twilio_client())"

# Verificar formato de número: +584121234567 (con + y código país)
```

### "Twilio no está instalado"

```bash
pip install twilio
```

### Cliente sin teléfono

Agregar campo `telefono` al modelo `Cliente` y ejecutar migraciones.

---

## 📚 Recursos

- [Twilio WhatsApp Docs](https://www.twilio.com/docs/whatsapp)
- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [Django Email](https://docs.djangoproject.com/en/5.0/topics/email/)

---

## 🎯 Próximos Pasos

- [ ] Implementar Celery para envíos asíncronos
- [ ] Agregar SMS como canal adicional
- [ ] Dashboard de estadísticas de notificaciones
- [ ] Plantillas personalizables desde admin
- [ ] Preferencias de notificación por cliente
- [ ] Integración con WhatsApp Business API oficial

---

**¿Preguntas?** Contacta al equipo de desarrollo.
