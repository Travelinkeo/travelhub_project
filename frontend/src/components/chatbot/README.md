# Linkeo - Chatbot de TravelHub

Asistente virtual inteligente para TravelHub con IA de Gemini.

## Componentes

### ChatWidget.tsx
Widget flotante que aparece en todas las páginas del sistema.

**Características:**
- Botón flotante en la esquina inferior derecha
- Ventana de chat desplegable
- Avatar de Linkeo
- Respuestas rápidas
- Historial de conversación
- Indicador de escritura

**Uso:**
```tsx
import ChatWidget from '@/components/chatbot/ChatWidget';

// Ya está incluido en el layout principal
<ChatWidget />
```

## Página Dedicada

Accesible en `/chatbot` - Interfaz completa de chat con:
- Vista amplia de conversación
- Estado del bot en tiempo real
- Botón para limpiar chat
- Respuestas rápidas expandidas

## APIs Utilizadas

### POST /api/chatbot/message/
Envía un mensaje al chatbot.

```json
{
  "message": "Hola, necesito información sobre viajes",
  "conversation_history": [
    {"role": "user", "content": "mensaje anterior"},
    {"role": "assistant", "content": "respuesta anterior"}
  ]
}
```

**Respuesta:**
```json
{
  "success": true,
  "response": "¡Hola! Soy Linkeo...",
  "fallback": false,
  "intent": "greeting",
  "quick_replies": ["¿Destinos populares?", "Cotizar viaje", ...]
}
```

### GET /api/chatbot/quick-replies/
Obtiene respuestas rápidas sugeridas.

### GET /api/chatbot/status/
Estado del chatbot y configuración.

```json
{
  "success": true,
  "status": "online",
  "name": "Linkeo",
  "avatar": "/static/images/linkeo-avatar.png",
  "gemini_available": true,
  "fallback_enabled": true
}
```

## Características

### Inteligencia
- **Gemini AI**: Respuestas naturales y contextuales
- **Sistema de Fallback**: Funciona sin IA usando reglas
- **Detección de Intenciones**: Identifica qué busca el usuario
- **Historial Contextual**: Recuerda la conversación

### Intenciones Detectadas
- `greeting` - Saludos
- `pricing` - Consultas de precios
- `booking` - Reservas
- `documents` - Documentación de viaje
- `hotels` - Alojamiento
- `packages` - Paquetes turísticos
- `contact` - Contacto con agente
- `farewell` - Despedidas
- `general` - Consultas generales

### Respuestas Rápidas
Sugerencias contextuales que facilitan la interacción:
- "¿Cuáles son los destinos más populares?"
- "Necesito información sobre documentos"
- "Quiero cotizar un viaje"
- "¿Ofrecen paquetes turísticos?"
- "Hablar con un agente"

## Personalización

### Avatar
Ubicado en: `/static/images/linkeo-avatar.png`

### Colores
- Primario: `bg-blue-600`
- Hover: `bg-blue-700`
- Mensajes usuario: `bg-blue-600`
- Mensajes bot: `bg-gray-100`

### Posición Widget
```css
fixed bottom-6 right-6
```

## Estado del Sistema

### Con Gemini AI Activo
- Respuestas naturales y contextuales
- Comprensión avanzada de consultas
- Personalización según historial

### Con Sistema de Fallback
- Respuestas basadas en palabras clave
- Funcional pero menos natural
- Siempre disponible como backup

## Próximas Mejoras

- [ ] Integración con CRM (datos de cliente)
- [ ] Búsqueda en base de conocimientos
- [ ] Cotizaciones automáticas
- [ ] Creación de leads desde chat
- [ ] Notificaciones push
- [ ] Soporte multiidioma
- [ ] Análisis de sentimiento
- [ ] Exportar conversaciones

## Troubleshooting

### El chatbot no responde
1. Verificar autenticación (token JWT)
2. Revisar consola del navegador
3. Verificar que el backend esté corriendo
4. Comprobar estado en `/api/chatbot/status/`

### Respuestas genéricas
- Gemini puede estar inactivo
- Sistema de fallback activado
- Verificar cuota de Gemini AI

### Avatar no se muestra
- Verificar ruta: `/static/images/linkeo-avatar.png`
- Ejecutar `collectstatic` en Django
- Verificar permisos de archivos estáticos