# 🤖 Linkeo - Asistente Virtual Inteligente de TravelHub

**Desarrollado por Linkeo Tech**

---

## 🎯 Descripción

Linkeo es el asistente virtual inteligente de TravelHub, entrenado con conocimiento completo del sistema para ayudar a usuarios y clientes con información precisa y contextual.

## ✨ Características Principales

### Conocimiento Completo del Sistema
Linkeo conoce TODO sobre TravelHub:
- ✅ Todos los módulos (CRM, ERP, CMS)
- ✅ Flujos de trabajo completos
- ✅ Funcionalidades técnicas
- ✅ Comandos y operaciones
- ✅ Integraciones disponibles
- ✅ Roadmap de desarrollo
- ✅ Contabilidad VEN-NIF
- ✅ Estados de ventas y procesos

### Inteligencia Artificial
- **Motor**: Google Gemini 2.5 Flash
- **Fallback**: Sistema de reglas cuando Gemini no está disponible
- **Contexto**: Mantiene historial de conversación
- **Intenciones**: Detecta automáticamente qué busca el usuario

### Capacidades

**Puede hacer:**
- Explicar cualquier funcionalidad de TravelHub
- Guiar en el uso del sistema
- Responder sobre destinos turísticos
- Explicar requisitos de viaje
- Orientar sobre servicios disponibles
- Conectar con agentes humanos
- Proporcionar información técnica del sistema

**NO puede hacer:**
- Confirmar reservas (solo agentes humanos)
- Dar precios exactos sin cotización
- Acceder a datos privados de clientes
- Procesar pagos
- Modificar reservas existentes

## 🎨 Interfaces Disponibles

### 1. Widget Flotante (Todas las páginas)
- Botón flotante en esquina inferior derecha
- Avatar personalizado de Linkeo
- Ventana de chat desplegable
- Respuestas rápidas
- Siempre disponible

### 2. Página Dedicada (/chatbot)
- Interfaz completa de chat
- Vista amplia de conversación
- Estado del bot en tiempo real
- Botón para limpiar chat
- Respuestas rápidas expandidas

## 📡 APIs Disponibles

### POST /api/chatbot/message/
Envía un mensaje a Linkeo.

**Request:**
```json
{
  "message": "¿Cómo funciona el parseo de boletos?",
  "conversation_history": [
    {"role": "user", "content": "mensaje anterior"},
    {"role": "assistant", "content": "respuesta anterior"}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "response": "El parseo de boletos en TravelHub...",
  "fallback": false,
  "intent": "general",
  "quick_replies": ["¿Qué GDS soporta?", "¿Cómo importar boletos?"]
}
```

### GET /api/chatbot/quick-replies/
Obtiene respuestas rápidas sugeridas.

### GET /api/chatbot/status/
Estado y configuración de Linkeo.

```json
{
  "success": true,
  "status": "online",
  "name": "Linkeo",
  "avatar": "/static/images/linkeo-avatar.png",
  "gemini_available": true,
  "fallback_enabled": true,
  "features": {
    "conversation_history": true,
    "quick_replies": true,
    "intent_detection": true,
    "multilanguage": false
  }
}
```

## 🧠 Base de Conocimientos

Linkeo está entrenado con información completa sobre:

### Módulos del Sistema
- CRM: Gestión de clientes, fidelidad, segmentación
- ERP: Ventas, facturación, contabilidad, liquidaciones
- CMS: Sitio web, blog, formularios
- Parseo: KIU, SABRE, AMADEUS
- Traductor: Itinerarios GDS
- OCR: Pasaportes y documentos
- Notificaciones: Email y WhatsApp

### Flujos de Trabajo
- Importación de boletos
- Enriquecimiento de ventas
- Facturación automática
- Liquidación a proveedores
- Gestión de pagos
- Contabilidad integrada

### Información Técnica
- Stack tecnológico
- Comandos disponibles
- Integraciones
- APIs REST
- Seguridad
- Próximas funcionalidades

## 🎯 Intenciones Detectadas

Linkeo identifica automáticamente:
- `greeting` - Saludos
- `pricing` - Consultas de precios
- `booking` - Reservas
- `documents` - Documentación
- `hotels` - Alojamiento
- `packages` - Paquetes turísticos
- `contact` - Contacto con agente
- `farewell` - Despedidas
- `general` - Consultas generales

## 💬 Ejemplos de Uso

### Consultas sobre el Sistema
```
Usuario: "¿Cómo funciona el sistema de puntos de fidelidad?"
Linkeo: "El sistema de puntos de fidelidad en TravelHub es automático..."
```

### Guía de Funcionalidades
```
Usuario: "¿Cómo importo boletos desde Gmail?"
Linkeo: "Para importar boletos desde Gmail, el sistema..."
```

### Información de Viajes
```
Usuario: "¿Qué documentos necesito para viajar a España?"
Linkeo: "Para viajar a España desde Latinoamérica necesitas..."
```

### Conexión con Agente
```
Usuario: "Quiero hacer una reserva"
Linkeo: "Para realizar una reserva, te conectaré con un agente..."
```

## 🔧 Configuración

### Variables de Entorno
```env
GEMINI_API_KEY=tu_api_key_aqui
```

### Avatar
Ubicación: `/static/images/linkeo-avatar.png`

### Personalización
Editar: `core/chatbot/knowledge_base.py`

## 📊 Métricas y Análisis

### Información Registrada
- Todas las conversaciones
- Intenciones detectadas
- Respuestas generadas
- Uso de fallback
- Errores y excepciones

### Análisis Disponible
- Consultas más frecuentes
- Intenciones más comunes
- Tasa de éxito de respuestas
- Tiempo de respuesta

## 🚀 Roadmap de Linkeo

### Fase Actual (Completada)
- ✅ Conocimiento completo del sistema
- ✅ Integración con Gemini AI
- ✅ Sistema de fallback robusto
- ✅ Detección de intenciones
- ✅ Respuestas rápidas
- ✅ Widget flotante
- ✅ Página dedicada

### Próximas Mejoras
- [ ] Integración con CRM (datos de cliente)
- [ ] Búsqueda en base de conocimientos
- [ ] Cotizaciones automáticas
- [ ] Creación de leads desde chat
- [ ] Notificaciones push
- [ ] Soporte multiidioma
- [ ] Análisis de sentimiento
- [ ] Exportar conversaciones
- [ ] Integración con WhatsApp Business
- [ ] Respuestas con imágenes/videos

## 🔐 Seguridad y Privacidad

### Datos Protegidos
- No accede a datos privados de clientes
- No almacena información sensible
- Conversaciones encriptadas en tránsito
- Autenticación JWT requerida

### Limitaciones
- No puede confirmar reservas
- No procesa pagos
- No modifica datos del sistema
- Solo proporciona información

## 📝 Mantenimiento

### Actualizar Conocimientos
Editar: `core/chatbot/knowledge_base.py`

### Agregar Nuevas Intenciones
Editar: `core/chatbot/chatbot_service.py` → `extract_intent()`

### Personalizar Respuestas de Fallback
Editar: `core/chatbot/chatbot_service.py` → `get_fallback_response()`

## 🆘 Troubleshooting

### Linkeo no responde
1. Verificar autenticación JWT
2. Revisar consola del navegador
3. Verificar backend ejecutándose
4. Comprobar `/api/chatbot/status/`

### Respuestas genéricas
- Gemini puede estar inactivo
- Sistema de fallback activado
- Verificar cuota de Gemini AI
- Revisar logs del servidor

### Avatar no se muestra
- Verificar ruta del archivo
- Ejecutar `collectstatic`
- Verificar permisos

## 📞 Soporte

Para soporte técnico o consultas sobre Linkeo:
- Documentación: Este archivo
- Código: `core/chatbot/`
- Frontend: `frontend/src/components/chatbot/`
- Desarrollador: Linkeo Tech

---

**Linkeo - Automatizando el futuro del turismo latinoamericano** 🚀