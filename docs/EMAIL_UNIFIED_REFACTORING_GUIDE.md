# Guía de Refactorización - email_unified.py

## Estado Actual

**Archivo:** `apps/communications/services/email_unified.py`  
**Líneas:** 1183  
**Problema:** God Class con múltiples responsabilidades

## Análisis de Responsabilidades

El archivo contiene:

### 1. Funciones de Envío de Emails (Líneas 34-408)
- `send_custom_email()` - Envío centralizado con Resend/SMTP
- `enviar_email_generico()` - Email genérico
- `enviar_email_html()` - Email con HTML y assets embebidos
- `enviar_confirmacion_venta()` - Confirmación de venta
- `enviar_recordatorio_pago()` - Recordatorio de pago
- `enviar_cambio_estado()` - Notificación de cambio de estado
- `enviar_confirmacion_pago()` - Confirmación de pago

### 2. Clase EmailMonitorService (Líneas 410-1183)
**Responsabilidades mezcladas:**
- Conexión IMAP y polling de emails
- Parseo de mensajes (texto, HTML, PDFs)
- Validación de PDFs de boletos
- Procesamiento de boletos
- Upload a Google Drive
- Envío de notificaciones (Telegram, WhatsApp, Email)
- Manejo de resultados

## Estrategia de Refactorización

### Estructura Propuesta

```
apps/communications/services/
├── email_unified.py (DEPRECATED - mantener por compatibilidad)
└── email_monitor/
    ├── __init__.py
    ├── email_sender.py              # Funciones de envío
    ├── email_monitor_service.py     # Servicio principal
    ├── email_parser.py              # Parseo de emails
    ├── pdf_validator.py             # Validación de PDFs
    ├── notification_dispatcher.py   # Notificaciones
    └── drive_uploader.py            # Upload a Drive
```

### Paso 1: Extraer Funciones de Envío

**Archivo destino:** `email_monitor/email_sender.py`

```python
"""
Email Sender Functions
Funciones para envío de emails usando Resend API o Django SMTP.
"""

import os
import logging
import resend
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def send_custom_email(subject, recipient, template_name, context, from_email=None, agencia=None):
    """Enviar email usando template con Resend o SMTP fallback."""
    # ... implementación desde email_unified.py líneas 34-116
    pass


def enviar_email_generico(destinatario, asunto, mensaje, from_email=None, agencia=None):
    """Enviar email genérico de texto plano."""
    # ... implementación desde email_unified.py líneas 119-165
    pass


def enviar_email_html(destinatario, asunto, html_content, from_email=None, agencia=None):
    """Enviar email con HTML y logo embebido."""
    # ... implementación desde email_unified.py líneas 167-237
    pass


def enviar_confirmacion_venta(venta):
    """Enviar confirmación de venta al cliente."""
    # ... implementación desde email_unified.py líneas 239-278
    pass


def enviar_recordatorio_pago(venta):
    """Enviar recordatorio de pago pendiente."""
    # ... implementación desde email_unified.py líneas 280-317
    pass


def enviar_cambio_estado(venta, estado_anterior):
    """Enviar notificación de cambio de estado."""
    # ... implementación desde email_unified.py líneas 319-350
    pass


def enviar_confirmacion_pago(pago_venta):
    """Enviar confirmación de pago recibido."""
    # ... implementación desde email_unified.py líneas 352-408
    pass
```

### Paso 2: Extraer Parseo de Emails

**Archivo destino:** `email_monitor/email_parser.py`

```python
"""
Email Parser
Funciones para parsear y extraer contenido de emails (IMAP).
"""

import email
import logging
from email import policy

logger = logging.getLogger(__name__)


def extraer_texto(message):
    """Extraer texto plano de un mensaje de email."""
    # ... implementación desde email_unified.py líneas 1163-1171
    pass


def extraer_html(message):
    """Extraer contenido HTML de un mensaje de email."""
    # ... implementación desde email_unified.py líneas 1173-1183
    pass


def extraer_pdf(message):
    """Extraer primer PDF adjunto del mensaje."""
    # ... implementación desde email_unified.py líneas 1158-1161
    pass


def extraer_adjuntos_pdf(message):
    """Extraer todos los PDFs adjuntos del mensaje."""
    # ... implementación desde email_unified.py líneas 1142-1156
    pass


def tiene_pdf_adjunto(message):
    """Verificar si el mensaje tiene al menos un PDF adjunto."""
    # ... implementación desde email_unified.py líneas 1029-1042
    pass
```

### Paso 3: Extraer Validación de PDFs

**Archivo destino:** `email_monitor/pdf_validator.py`

```python
"""
PDF Validator
Validación y procesamiento de PDFs de boletos aéreos.
"""

import logging
import PyPDF2
from io import BytesIO

logger = logging.getLogger(__name__)


def es_pdf_boleto_valido(pdf_content, filename=""):
    """
    Validar si un PDF es un boleto aéreo válido.
    
    Criterios:
    - Debe ser un PDF válido
    - Debe contener palabras clave de boletos
    - Debe tener al menos 1 página
    - No debe estar encriptado
    """
    # ... implementación desde email_unified.py líneas 1044-1140
    pass
```

### Paso 4: Extraer Notificaciones

**Archivo destino:** `email_monitor/notification_dispatcher.py`

```python
"""
Notification Dispatcher
Envío de notificaciones por múltiples canales (Telegram, WhatsApp, Email).
"""

import logging

logger = logging.getLogger(__name__)


def enviar_notificacion(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path):
    """Enviar notificación por todos los canales configurados."""
    # ... implementación desde email_unified.py líneas 882-897
    pass


def enviar_telegram(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path):
    """Enviar notificación por Telegram."""
    # ... implementación desde email_unified.py líneas 899-918
    pass


def enviar_whatsapp(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path):
    """Enviar notificación por WhatsApp."""
    # ... implementación desde email_unified.py líneas 920-936
    pass


def enviar_email(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path):
    """Enviar notificación por email."""
    # ... implementación desde email_unified.py líneas 938-967
    pass


def enviar_whatsapp_drive(sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_url):
    """Enviar notificación por WhatsApp con link a Drive."""
    # ... implementación desde email_unified.py líneas 969-1000
    pass
```

### Paso 5: Extraer Upload a Drive

**Archivo destino:** `email_monitor/drive_uploader.py`

```python
"""
Drive Uploader
Upload de archivos PDF a Google Drive.
"""

import logging
import os

logger = logging.getLogger(__name__)


class DriveUploader:
    """Servicio de upload a Google Drive."""
    
    def __init__(self, drive_service):
        self.drive_service = drive_service
    
    def upload_to_drive(self, pdf_path):
        """Subir PDF a Google Drive y retornar URL pública."""
        # ... implementación desde email_unified.py líneas 1002-1027
        pass
```

### Paso 6: Refactorizar EmailMonitorService

**Archivo destino:** `email_monitor/email_monitor_service.py`

```python
"""
Email Monitor Service
Servicio principal de monitoreo de emails vía IMAP.
"""

import imaplib
import logging
import time

from .email_parser import extraer_texto, extraer_html, extraer_pdf, tiene_pdf_adjunto
from .pdf_validator import es_pdf_boleto_valido
from .notification_dispatcher import enviar_notificacion
from .drive_uploader import DriveUploader

logger = logging.getLogger(__name__)


class EmailMonitorService:
    """
    Servicio de monitoreo de emails para captura automática de boletos.
    
    Responsabilidades:
    - Conectar a servidor IMAP
    - Polling de emails nuevos
    - Procesamiento de mensajes
    - Coordinación de parseo y notificaciones
    """
    
    def __init__(self, agencia):
        """Inicializar servicio con configuración de agencia."""
        # ... implementación desde email_unified.py líneas 413-447
        pass
    
    def _init_drive(self):
        """Inicializar servicio de Google Drive."""
        # ... implementación desde email_unified.py líneas 449-465
        pass
    
    def start(self):
        """Iniciar loop de monitoreo continuo."""
        # ... implementación desde email_unified.py líneas 474-484
        pass
    
    def procesar_una_vez(self):
        """Ejecutar un ciclo de procesamiento."""
        # ... implementación desde email_unified.py líneas 467-472
        pass
    
    def _procesar_correos(self):
        """Procesar todos los correos no leídos."""
        # ... implementación desde email_unified.py líneas 486-620
        pass
    
    def _procesar_mensaje(self, message, msg_num, mail_connection):
        """Procesar un mensaje individual."""
        # ... implementación desde email_unified.py líneas 622-735
        pass
    
    def _procesar_boleto_email(self, message, msg_num, mail_connection):
        """Procesar boleto desde contenido de email."""
        # ... implementación desde email_unified.py líneas 737-775
        pass
    
    def _procesar_boleto_pdf(self, message, msg_num, mail_connection):
        """Procesar boleto desde PDF adjunto."""
        # ... implementación desde email_unified.py líneas 777-819
        pass
    
    def _manejar_resultado_procesamiento(self, boleto, resultado):
        """Manejar resultado del procesamiento de boleto."""
        # ... implementación desde email_unified.py líneas 821-861
        pass
    
    def _enviar_respaldo_email(self, boleto, pdf_path):
        """Enviar email de respaldo con PDF."""
        # ... implementación desde email_unified.py líneas 863-880
        pass
```

### Paso 7: Crear Wrapper de Compatibilidad

**Archivo:** `email_unified.py` (modificado)

```python
"""
Email Unified Service - DEPRECATED

Este módulo mantiene compatibilidad hacia atrás mientras se migra al nuevo
módulo email_monitor.

Migración:
- Funciones de envío → email_monitor.email_sender
- EmailMonitorService → email_monitor.email_monitor_service
"""

import warnings
from .email_monitor import (
    send_custom_email,
    enviar_email_generico,
    enviar_email_html,
    enviar_confirmacion_venta,
    enviar_recordatorio_pago,
    enviar_cambio_estado,
    enviar_confirmacion_pago,
    EmailMonitorService,
)

warnings.warn(
    "email_unified.py está deprecado. "
    "Usar apps.communications.services.email_monitor en su lugar.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    'send_custom_email',
    'enviar_email_generico',
    'enviar_email_html',
    'enviar_confirmacion_venta',
    'enviar_recordatorio_pago',
    'enviar_cambio_estado',
    'enviar_confirmacion_pago',
    'EmailMonitorService',
]
```

## Plan de Migración

### Fase 1: Preparación (1 día)
1. Crear estructura de directorios `email_monitor/`
2. Crear archivos vacíos con docstrings
3. Configurar imports en `__init__.py`

### Fase 2: Extracción Incremental (2-3 días)
1. Extraer `email_sender.py` (funciones de envío)
2. Extraer `email_parser.py` (parseo de emails)
3. Extraer `pdf_validator.py` (validación de PDFs)
4. Extraer `notification_dispatcher.py` (notificaciones)
5. Extraer `drive_uploader.py` (upload a Drive)

### Fase 3: Refactorización de Clase Principal (1-2 días)
1. Refactorizar `EmailMonitorService` para usar los nuevos módulos
2. Mantener compatibilidad de API
3. Actualizar imports internos

### Fase 4: Testing (1 día)
1. Ejecutar tests existentes
2. Verificar que todas las funcionalidades funcionan
3. Corregir bugs si aparecen

### Fase 5: Deprecación (1 día)
1. Crear wrapper de compatibilidad en `email_unified.py`
2. Agregar warnings de deprecación
3. Actualizar documentación

### Fase 6: Limpieza (1 día)
1. Buscar y reemplazar imports en todo el proyecto
2. Eliminar `email_unified.py` después de período de gracia
3. Actualizar documentación

## Beneficios de la Refactorización

### Antes (God Class)
- ❌ 1183 líneas en un solo archivo
- ❌ Múltiples responsabilidades mezcladas
- ❌ Difícil de testear
- ❌ Difícil de mantener
- ❌ Alto acoplamiento

### Después (Módulos Separados)
- ✅ Archivos de 100-200 líneas cada uno
- ✅ Responsabilidades únicas y claras
- ✅ Fácil de testear (cada módulo independiente)
- ✅ Fácil de mantener
- ✅ Bajo acoplamiento
- ✅ Reutilizable (módulos pueden usarse independientemente)

## Métricas de Calidad

| Métrica | Antes | Después |
|---------|-------|---------|
| Líneas por archivo | 1183 | ~200 |
| Responsabilidades por clase | 7+ | 1-2 |
| Acoplamiento | Alto | Bajo |
| Cohesión | Baja | Alta |
| Testabilidad | Difícil | Fácil |

## Herramientas de Análisis

### Antes de Refactorizar
```bash
# Contar líneas
wc -l apps/communications/services/email_unified.py

# Analizar complejidad
radon cc apps/communications/services/email_unified.py

# Ver dependencias
pydeps apps/communications/services/email_unified.py
```

### Después de Refactorizar
```bash
# Verificar que todos los módulos son importables
python manage.py shell -c "from apps.communications.services.email_monitor import *; print('OK')"

# Ejecutar tests
pytest apps/communications/tests/

# Verificar que no hay imports circulares
python manage.py check
```

## Referencias

- [Clean Code: Chapter 10 - Classes](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)
- [Single Responsibility Principle](https://en.wikipedia.org/wiki/Single-responsibility_principle)
- [Django Best Practices: Services](https://docs.djangoproject.com/en/stable/topics/db/models/#module-django.db.models)
- [Refactoring Guru: Extract Class](https://refactoring.guru/extract-class)
