# Procesamiento Automático de Boletos desde Correo

## Descripción

Sistema automatizado que lee correos electrónicos de remitentes autorizados, extrae boletos adjuntos (PDF), los parsea automáticamente, genera PDFs profesionales y opcionalmente envía notificaciones por WhatsApp.

## Remitentes Autorizados

El sistema solo procesa correos de los siguientes remitentes:

### KIU (Sistema GDS)
- `noreply@kiusys.com`
- `ww@kiusys.com`

### Otros Proveedores
- `emisiones@grupoctg.com`
- `ventas1mydestiny@gmail.com`
- `ventas2mydestiny@gmail.com`
- `ventas3mydestiny@gmail.com`
- `ventas4mydestiny@gmail.com`

### Internos
- `travelinkeo@gmail.com`
- `viajes.travelinkeo@gmail.com`

## Flujo de Procesamiento

```
1. Conectar a travelinkeo@gmail.com (IMAP)
   ↓
2. Buscar correos NO LEÍDOS
   ↓
3. Verificar remitente autorizado
   ↓
4. Extraer adjuntos PDF
   ↓
5. Parsear boleto (detecta GDS automáticamente)
   ↓
6. Guardar en BoletoImportado
   ↓
7. Generar PDF profesional
   ↓
8. (Opcional) Enviar por WhatsApp
   ↓
9. Marcar correo como leído
```

## Configuración

### Variables de Entorno (.env)

```env
# Email (Gmail)
EMAIL_HOST_USER=travelinkeo@gmail.com
EMAIL_HOST_PASSWORD=tu_app_password_aqui

# WhatsApp (Twilio) - Opcional
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### Obtener App Password de Gmail

1. Ir a https://myaccount.google.com/security
2. Activar "Verificación en 2 pasos"
3. Ir a "Contraseñas de aplicaciones"
4. Generar contraseña para "Correo"
5. Copiar la contraseña generada a `EMAIL_HOST_PASSWORD`

## Uso

### Ejecución Manual

```bash
# Activar entorno virtual
venv\Scripts\activate

# Ejecutar comando
python manage.py procesar_boletos_email
```

### Ejecución con Script Batch

```bash
batch_scripts\procesar_boletos_email.bat
```

### Automatización con Task Scheduler

1. Abrir "Programador de tareas" (Task Scheduler)
2. Crear tarea básica:
   - **Nombre**: Procesar Boletos Email
   - **Desencadenador**: Repetir cada 15 minutos
   - **Acción**: Iniciar programa
   - **Programa**: `C:\Users\ARMANDO\travelhub_project\batch_scripts\procesar_boletos_email.bat`
   - **Iniciar en**: `C:\Users\ARMANDO\travelhub_project`

## Parsers Soportados

El sistema detecta automáticamente el tipo de boleto:

1. **KIU** - Sistema GDS
2. **SABRE** - Sistema GDS
3. **AMADEUS** - Sistema GDS
4. **TK Connect** - Turkish Airlines
5. **Copa SPRK** - Copa Airlines
6. **Wingo** - Aerolínea low-cost

## Archivos del Sistema

### Servicio Principal
- `core/services/email_ticket_processor.py` - Lógica de procesamiento

### Comando Django
- `core/management/commands/procesar_boletos_email.py` - Comando CLI

### Script Batch
- `batch_scripts/procesar_boletos_email.bat` - Ejecución Windows

### Notificaciones
- `core/whatsapp_notifications.py` - Envío de WhatsApp

## Logs

Los logs se guardan en:
- Consola (stdout)
- Archivo de logs de Django (si está configurado)

Ejemplo de log:
```
INFO: Encontrados 3 correos no leídos
INFO: Procesando correo de noreply@kiusys.com
INFO: Boleto procesado exitosamente: 123
INFO: PDF generado: Boleto_KIU_20251013.pdf
INFO: Procesados 3 boletos
```

## Seguridad

- ✅ Solo procesa remitentes autorizados
- ✅ Solo procesa archivos PDF
- ✅ Validación de datos parseados
- ✅ Logs de auditoría completos
- ✅ Credenciales en variables de entorno

## Notificaciones WhatsApp (Opcional)

Si está configurado Twilio, el sistema puede enviar:

```
✈️ TravelHub - Boleto Confirmado

Estimado/a NOMBRE PASAJERO,

Su boleto ha sido procesado exitosamente.

📋 Detalles:
• PNR: ABC123
• Sistema: KIU

El PDF de su boleto ha sido generado.

_Equipo TravelHub_
```

## Troubleshooting

### Error: "Credenciales de email no configuradas"
- Verificar `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` en `.env`

### Error: "Authentication failed"
- Verificar que la contraseña sea App Password, no la contraseña normal
- Verificar que 2FA esté activado en Gmail

### No se procesan correos
- Verificar que los correos estén NO LEÍDOS
- Verificar que el remitente esté en la lista autorizada
- Verificar que tengan adjuntos PDF

### Error parseando boleto
- Verificar que el PDF sea un boleto válido
- Revisar logs para ver el error específico

## Próximas Mejoras

- [ ] Envío automático de PDF por WhatsApp con adjunto
- [ ] Creación automática de venta en el sistema
- [ ] Notificación al cliente por email
- [ ] Dashboard de boletos procesados
- [ ] Reintento automático en caso de error

## Soporte

Para más información, consultar:
- `docs/api/FRONTEND_API_ENDPOINTS.md`
- `docs_archive/PARSERS_AEROLINEAS.md`
- `docs_archive/NOTIFICACIONES.md`
