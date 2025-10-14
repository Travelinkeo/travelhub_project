# Monitoreo de Notificaciones en Twilio

## 📊 Dashboard de Twilio

### Acceder al Dashboard
1. Ve a: https://console.twilio.com/
2. Inicia sesión con tu cuenta
3. Dashboard principal muestra resumen

---

## 📱 Monitorear WhatsApp

### Ver Mensajes Enviados
1. En el menú lateral: **Monitor** → **Logs** → **Messaging**
2. Filtra por:
   - **Channel:** WhatsApp
   - **Date Range:** Últimos 7 días
   - **Status:** All / Delivered / Failed

### Información de Cada Mensaje
- **SID:** Identificador único
- **To:** Número destinatario
- **From:** Tu número de Twilio
- **Status:** 
  - `queued` - En cola
  - `sent` - Enviado
  - `delivered` - Entregado ✅
  - `failed` - Fallido ❌
  - `undelivered` - No entregado
- **Error Code:** Si falló, código de error
- **Price:** Costo del mensaje

### Estados de Mensaje

| Estado | Significado | Acción |
|--------|-------------|--------|
| `delivered` | ✅ Mensaje entregado | Ninguna |
| `sent` | 📤 Enviado, esperando confirmación | Esperar |
| `failed` | ❌ Error al enviar | Revisar error |
| `undelivered` | ⚠️ No se pudo entregar | Verificar número |

---

## 💰 Monitorear Costos

### Ver Uso y Facturación
1. **Account** → **Usage**
2. Selecciona período
3. Ve desglose por:
   - WhatsApp Messages
   - SMS
   - Voice

### Costos Típicos (USD)
- **WhatsApp (Sandbox):** Gratis
- **WhatsApp (Producción):** ~$0.005/mensaje
- **SMS:** ~$0.0075/mensaje
- **Número de teléfono:** ~$1/mes

### Configurar Alertas de Gasto
1. **Account** → **Notifications**
2. **Usage Triggers**
3. Configura:
   - Límite de gasto (ej: $10)
   - Email de notificación
   - Acción (alerta o suspender)

---

## 📈 Estadísticas Útiles

### Tasa de Entrega
```
Tasa = (Mensajes Entregados / Mensajes Enviados) × 100
```

**Objetivo:** >95%

### Mensajes por Día
1. **Monitor** → **Logs** → **Messaging**
2. Agrupa por fecha
3. Exporta CSV para análisis

### Errores Comunes

| Código | Error | Solución |
|--------|-------|----------|
| 21211 | Número inválido | Verificar formato +país |
| 21408 | Permiso denegado | Verificar sandbox |
| 21610 | Mensaje bloqueado | Usuario bloqueó bot |
| 63007 | Fuera de ventana 24h | Usar plantilla aprobada |

---

## 🔍 Debugging

### Ver Detalles de un Mensaje
1. Clic en el SID del mensaje
2. Ve:
   - Timeline completo
   - Webhooks enviados
   - Errores detallados
   - Precio exacto

### Logs en Django
```bash
# Ver logs de notificaciones
python manage.py shell
>>> from core.models import Venta
>>> venta = Venta.objects.last()
>>> # Revisar logs en consola
```

### Probar Conectividad
```python
from twilio.rest import Client
import os

client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

# Listar últimos 5 mensajes
messages = client.messages.list(limit=5)
for msg in messages:
    print(f"{msg.sid}: {msg.status} - {msg.to}")
```

---

## 📊 Reportes Personalizados

### Exportar Datos
1. **Monitor** → **Logs** → **Messaging**
2. Aplica filtros
3. **Export** → CSV
4. Analiza en Excel/Google Sheets

### Métricas Recomendadas
- Mensajes enviados por día
- Tasa de entrega por hora
- Costo total mensual
- Errores por tipo
- Clientes más activos

---

## 🔔 Configurar Webhooks (Avanzado)

### Recibir Notificaciones de Estado
1. **Messaging** → **Settings** → **WhatsApp Sandbox Settings**
2. **Status Callback URL:**
   ```
   https://tu-dominio.com/api/twilio/webhook/
   ```
3. Eventos:
   - ✅ Message Delivered
   - ✅ Message Failed
   - ✅ Message Sent

### Implementar Webhook en Django
```python
# En urls.py
path('api/twilio/webhook/', twilio_webhook, name='twilio_webhook'),

# En views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

@csrf_exempt
def twilio_webhook(request):
    if request.method == 'POST':
        message_sid = request.POST.get('MessageSid')
        status = request.POST.get('MessageStatus')
        
        # Guardar en base de datos o log
        logger.info(f"Mensaje {message_sid}: {status}")
        
        return HttpResponse(status=200)
    return HttpResponse(status=405)
```

---

## 🎯 KPIs Recomendados

### Operacionales
- **Mensajes enviados/día:** Meta >10
- **Tasa de entrega:** Meta >95%
- **Tiempo de respuesta:** <5 segundos

### Financieros
- **Costo por mensaje:** ~$0.005
- **Costo mensual total:** Monitorear
- **ROI:** Comparar con llamadas telefónicas

### Calidad
- **Tasa de error:** Meta <5%
- **Mensajes bloqueados:** Meta <1%
- **Quejas de spam:** Meta 0

---

## 🛠️ Herramientas Útiles

### Twilio CLI (Opcional)
```bash
# Instalar
npm install -g twilio-cli

# Login
twilio login

# Ver últimos mensajes
twilio api:core:messages:list --limit 10

# Ver detalles de mensaje
twilio api:core:messages:fetch --sid SMxxxxx
```

### Python Script de Monitoreo
```python
# monitor_twilio.py
from twilio.rest import Client
import os
from datetime import datetime, timedelta

client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

# Mensajes de las últimas 24 horas
yesterday = datetime.now() - timedelta(days=1)
messages = client.messages.list(
    date_sent_after=yesterday
)

print(f"Mensajes enviados: {len(messages)}")
delivered = sum(1 for m in messages if m.status == 'delivered')
print(f"Entregados: {delivered} ({delivered/len(messages)*100:.1f}%)")
```

---

## 📞 Soporte de Twilio

### Contactar Soporte
- **Email:** help@twilio.com
- **Docs:** https://www.twilio.com/docs
- **Status:** https://status.twilio.com/
- **Community:** https://www.twilio.com/community

### Recursos
- [WhatsApp Business API Docs](https://www.twilio.com/docs/whatsapp)
- [Error Codes](https://www.twilio.com/docs/api/errors)
- [Best Practices](https://www.twilio.com/docs/whatsapp/best-practices)

---

**Tip:** Revisa el dashboard de Twilio semanalmente para detectar problemas temprano.
