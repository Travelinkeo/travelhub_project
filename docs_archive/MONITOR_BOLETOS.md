# Monitor Automático de Boletos por WhatsApp

Sistema de captura automática de boletos desde correo electrónico con envío por WhatsApp.

## Características

✅ **KIU**: Detecta correos de `noreply@kiusys.com` con asunto "E-TICKET ITINERARY RECEIPT"  
✅ **SABRE**: Detecta PDFs adjuntos y valida que sean boletos SABRE  
✅ **Actualización Automática**: Si un boleto SABRE llega sin tarifas y luego con tarifas, actualiza la venta existente  
✅ **Sin Duplicados**: Usa el localizador (PNR) como clave única  
✅ **Envío Inteligente**: Solo envía por WhatsApp cuando hay cambios relevantes  

## Requisitos

```bash
pip install twilio PyPDF2
```

Variables en `.env`:
```env
# Gmail IMAP
GMAIL_USER=travelinkeo@gmail.com
GMAIL_APP_PASSWORD=tu_app_password
GMAIL_IMAP_HOST=imap.gmail.com

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_WHATSAPP_NUMBER=+14155238886
```

## Uso

### Modo Básico
```bash
python manage.py monitor_tickets_whatsapp --phone +584121234567
```

### Con Opciones
```bash
# Marcar correos como leídos después de procesar
python manage.py monitor_tickets_whatsapp --phone +584121234567 --mark-read

# Chequear cada 2 minutos
python manage.py monitor_tickets_whatsapp --phone +584121234567 --interval 120
```

## Flujo de Trabajo

### KIU (Texto Plano)
1. Detecta correo de `noreply@kiusys.com` con asunto específico
2. Extrae texto del cuerpo del correo
3. Parsea con `parse_ticket()` (detecta automáticamente GDS)
4. Crea `Venta` con localizador
5. Genera PDF formateado
6. Envía por WhatsApp

### SABRE (PDF Adjunto)

#### Primera Captura (Sin Tarifas)
1. Detecta PDF adjunto en cualquier correo
2. Extrae texto del PDF
3. Valida que sea boleto SABRE (parser detecta automáticamente)
4. Crea `Venta` con `total_venta = 0`
5. **NO envía por WhatsApp** (sin tarifas)

#### Segunda Captura (Con Tarifas)
1. Detecta mismo localizador en nuevo correo
2. Encuentra `Venta` existente
3. Actualiza `total_venta` con las tarifas
4. Actualiza `VentaParseMetadata`
5. **SÍ envía por WhatsApp** con etiqueta "(Actualizado)"

#### Tercera Captura (Sin Cambios)
1. Detecta mismo localizador
2. Venta ya tiene tarifas
3. **Ignora** (no envía WhatsApp)

## Logs

El sistema genera logs detallados:

```
🚀 Iniciando monitor de boletos -> WhatsApp +584121234567
✅ Correo 123 procesado exitosamente
✨ Nueva Venta SABRE: ABC123
🔄 Actualizando Venta ABC123 con tarifas
⏭️ Venta ABC123 ya existe, sin cambios relevantes
⚠️ SABRE sin localizador
⏭️ PDF ignorado: no es SABRE válido
```

## Automatización con Task Scheduler (Windows)

1. Crear archivo `monitor_boletos.bat`:
```batch
@echo off
cd C:\Users\ARMANDO\travelhub_project
call venv\Scripts\activate
python manage.py monitor_tickets_whatsapp --phone +584121234567 --mark-read
```

2. Programar en Task Scheduler:
   - Trigger: Al iniciar sesión
   - Acción: Ejecutar `monitor_boletos.bat`

## Limitaciones Actuales

⚠️ **Envío de PDF por WhatsApp**: Actualmente solo envía el mensaje de texto. Para enviar el PDF adjunto se requiere:
- Subir el PDF a un servidor público (S3, Drive, etc.)
- Usar la URL pública en `media_url` de Twilio

## Próximas Mejoras

- [ ] Subida automática de PDFs a S3/Drive para adjuntar en WhatsApp
- [ ] Soporte para Amadeus
- [ ] Dashboard web para monitorear capturas
- [ ] Notificaciones de errores por email
- [ ] Filtros por aerolínea o rango de fechas
