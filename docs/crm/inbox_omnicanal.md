# Inbox Omnicanal (WhatsApp + CRM + IA)

Sistema de inbox conversacional para que agentes humanos se comuniquen directamente con clientes vía WhatsApp usando Evolution API.

## Arquitectura

```
Cliente WhatsApp
      ↕
Evolution API (Docker: atendai/evolution-api)
      ↕
Webhook → EvolutionWebhookView → MensajeWhatsApp (DB)
      ↕
Inbox Omnicanal → SendMessageView → send_evolution_message_task (Celery)
      ↕
Agente Humano (Interfaz Web)
```

## Componentes

### Vistas (apps/crm/views/inbox_views.py)

| Vista | URL | Método | Descripción |
|---|---|---|---|
| `InboxView` | `/crm/inbox/` | GET | Página principal del inbox |
| `InboxSearchView` | `/crm/inbox/search/` | GET (HTMX) | Búsqueda de clientes por nombre/teléfono/email |
| `ChatThreadView` | `/crm/inbox/chat/<cliente_id>/` | GET (HTMX) | Carga el workspace de chat del cliente |
| `SendMessageView` | `/crm/inbox/send/<cliente_id>/` | POST (HTMX) | Envía un mensaje al cliente |
| `GenerateSuggestedReplyView` | `/crm/inbox/ai-reply/<cliente_id>/` | GET (HTMX) | Sugerencia de respuesta con Gemini AI |

### Templates

| Template | Descripción |
|---|---|
| `crm/inbox/omnichannel_inbox.html` | Layout principal (sidebar + workspace) |
| `crm/inbox/partials/chat_workspace.html` | Área de chat (mensajes + input + contexto CRM) |
| `crm/inbox/partials/message_bubble.html` | Burbuja individual de mensaje |
| `crm/inbox/partials/client_list.html` | Lista de clientes en sidebar |

### Modelo

**`MensajeWhatsApp`** (`apps/crm/models.py:332`)
- `cliente` → FK a Cliente
- `direccion` → IN (entrante) / OUT (saliente)
- `texto` → Contenido del mensaje
- `timestamp` → Fecha/hora auto
- `estado` → pending / sent / delivered / read / failed
- `message_id` → ID del mensaje en WhatsApp
- `es_bot` → True si lo envió el bot automático
- `tipo_mensaje` → text / buttons / list / image / document / etc.

## Flujo de mensaje saliente (agente → cliente)

1. Agente escribe mensaje en el textarea del inbox
2. HTMX envía POST a `/crm/inbox/send/<cliente_id>/`
3. `SendMessageView`:
   - Crea `MensajeWhatsApp` con `direccion="OUT"` en DB
   - Encola `send_evolution_message_task` en Celery
   - Devuelve la burbuja HTML via HTMX
4. Celery ejecuta `send_evolution_message_task`:
   - Resuelve `WhatsAppEvolutionService(agencia_id)`
   - Obtiene `evolution_instance_name`, `evolution_api_url`, `evolution_api_key` de `AgenciaConfiguracion`
   - Llama a `POST /message/sendText/{instance}` de Evolution API
5. Evolution API envía el mensaje al número del cliente

## Flujo de mensaje entrante (cliente → agente)

1. Cliente envía WhatsApp al número de la agencia
2. Evolution API envía webhook a `POST /crm/webhook/evolution/`
3. `EvolutionWebhookView._handle_message_upsert()`:
   - Identifica la agencia por `instance_name`
   - Busca o crea `Cliente` por `telefono_principal`
   - Crea `MensajeWhatsApp` con `direccion="IN"`
   - Encola `whatsapp_ai_task` para respuesta automática con Gemini
4. El mensaje aparece automáticamente en el inbox del agente

## Características

### Búsqueda en el inbox
- Campo de búsqueda con debounce de 300ms
- Busca por: nombre, apellido, teléfono, email
- Resultados vía HTMX sin recargar la página

### Clientes sin historial
- El inbox muestra todos los clientes con teléfono, incluso sin mensajes previos
- Permite iniciar conversaciones nuevas desde el inbox

### Auto-selección desde perfil del cliente
- Botón "Chat" junto al teléfono en el perfil del cliente
- Enlace a `/crm/inbox/?chat=<id>` que auto-carga la conversación

### Sidebar de contexto CRM
- Muestra lead activo (oportunidad de viaje) del cliente en Kanban
- Resumen del viaje: destino, fechas, pasajeros
- Acceso rápido para armar cotización

### Sugerencias de IA (Gemini)
- Botón "auto_awesome" en el input
- Genera respuesta sugerida basada en el historial de la conversación

## Envío de notificaciones automáticas

Además del inbox manual, el sistema envía notificaciones automáticas:

- `enviar_whatsapp_confirmacion_venta` - Al crear reserva
- `enviar_whatsapp_cambio_estado` - Al cambiar estado
- `enviar_whatsapp_confirmacion_pago` - Al recibir pago
- `enviar_whatsapp_recordatorio_pago` - Recordatorio de saldo pendiente

Estas usan `send_whatsapp_message()` en `whatsapp_unified.py` con Evolution como proveedor primario y Meta Cloud API como fallback.

## URL Referencia

| Ruta | Namespace |
|---|---|
| `/crm/inbox/` | `crm:inbox` |
| `/crm/inbox/search/` | `crm:inbox_search` |
| `/crm/inbox/chat/<id>/` | `crm:chat_thread` |
| `/crm/inbox/send/<id>/` | `crm:send_message` |
| `/crm/inbox/ai-reply/<id>/` | `crm:ai_suggested_reply` |
| `/crm/webhook/evolution/` | `crm:evolution_webhook` |
| `/crm/webhook/whatsapp/` | `crm:whatsapp_webhook` |
