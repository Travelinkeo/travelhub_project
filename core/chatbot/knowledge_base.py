# core/chatbot/knowledge_base.py

"""
Base de conocimientos de Linkeo sobre TravelHub.
Información completa del sistema para respuestas precisas.
"""

TRAVELHUB_KNOWLEDGE = """
# INFORMACIÓN COMPLETA DE TRAVELHUB

## IDENTIDAD
- Nombre del sistema: TravelHub
- Desarrollado por: Linkeo Tech
- Tipo: CRM + ERP + CMS para agencias de viajes
- Región: Latinoamérica y Venezuela
- Asistente: Linkeo (tú)

## MÓDULOS PRINCIPALES

### 1. CRM (Gestión de Clientes)
- Gestión completa de clientes con historial
- Sistema de puntos de fidelidad automático
- Segmentación de clientes VIP
- Historial de compras y preferencias
- Alertas de vencimiento de documentos

### 2. ERP (Gestión Empresarial)
- Ventas y reservas con estados automáticos
- Facturación automática con PDF
- Liquidaciones a proveedores
- Contabilidad integrada (VEN-NIF para Venezuela)
- Gestión de pagos y cobranza
- Cálculo automático de diferencial cambiario
- Provisión INATUR automática

### 3. CMS (Gestión de Contenido)
- Sitio web público integrado
- Blog y páginas personalizables
- Formularios conectados al CRM
- Publicación automática de productos

### 4. PARSEO DE BOLETOS
- Importación automática desde Gmail
- Soporte para KIU, SABRE, AMADEUS
- Extracción automática de datos
- Creación automática de ventas
- Normalización de información

### 5. TRADUCTOR DE ITINERARIOS
- Traduce formatos GDS a lenguaje natural
- Soporta SABRE, AMADEUS, KIU
- Calculadora de precios con fees
- Procesamiento en lote (hasta 10)
- Validación de formato

### 6. OCR DE PASAPORTES
- Escaneo automático de pasaportes
- Extracción de datos (nombre, número, fechas)
- Creación automática de clientes
- Verificación de datos

### 7. NOTIFICACIONES
- Emails automáticos transaccionales
- Recordatorios de pago programables
- WhatsApp (estructura lista, Twilio)
- Confirmaciones de reserva

## FLUJO DE TRABAJO TÍPICO

### Paso 1: Importación y Creación de la Venta

**Proceso Manual (Panel de Administración):**
1. Ve a "Boletos Importados" en el panel de administración
2. Haz clic en "Añadir Boleto Importado"
3. Selecciona un archivo de boleto (.pdf, .eml, .txt)
4. Guarda el archivo

**Proceso Automático (al guardar):**
- El sistema parsea el boleto automáticamente
- Extrae toda la información relevante (pasajeros, vuelos, tarifas, localizador)
- Crea o actualiza una VENTA agrupando todos los boletos con el mismo LOCALIZADOR
- La Venta se crea SIN cliente asignado, lista para ser procesada

**Formatos Soportados:**
- KIU: PDF, TXT, EML
- SABRE: PDF, TXT, EML
- AMADEUS: PDF, TXT, EML (en desarrollo)

### Paso 2: Enriquecimiento de la Venta (Costos y Ganancias)

1. Ve a la sección "Ventas / Reservas"
2. Busca la venta creada (puedes usar el localizador)
3. Haz clic en la venta para ver su detalle
4. En la sección inferior "Items de Venta/Reserva" verás los boletos como items individuales
5. Rellena los campos financieros para cada item:
   - **Proveedor del Servicio**: Asigna el proveedor que emitió el boleto
   - **Costo Neto Proveedor**: El costo base del servicio
   - **Fee Emisión Proveedor**: El fee que cobra el proveedor por la emisión
   - **Comisión Agencia (Monto)**: La comisión que ganas del proveedor
   - **Fee Interno Agencia**: Tu fee de servicio propio
6. Guarda los cambios

**El sistema calcula automáticamente:**
- Márgenes de ganancia
- Totales por item
- Total de la venta

### Paso 3: Facturación al Cliente

1. En la lista de "Ventas / Reservas", marca la casilla de la venta que acabas de editar
2. En el menú desplegable de "Acciones" (parte superior), selecciona **"Asignar Cliente y Generar Factura"**
3. Haz clic en "Ir"
4. En la página intermedia, selecciona el Cliente al que le vas a facturar
5. Haz clic en "Confirmar y Facturar"

**Resultado:**
- La Venta ahora tendrá el cliente asignado
- Se crea una nueva Factura en "Facturas de Clientes"
- La Factura tendrá un PDF adjunto generado automáticamente
- Se envía email de confirmación al cliente (si está configurado)

### Paso 4: Liquidación al Proveedor (Cuentas por Pagar)

1. Vuelve a la lista de "Ventas / Reservas"
2. Selecciona la misma venta (que ahora ya tiene cliente y factura)
3. En el menú de "Acciones", selecciona **"Generar Liquidación a Proveedor(es)"**
4. Haz clic en "Ir"

**Resultado:**
- El sistema calcula automáticamente cuánto se le debe a cada proveedor
- Fórmula: (Costo Neto + Fee Proveedor) - Comisión Agencia
- Se crea un registro en "Liquidaciones a Proveedores"
- Este registro representa una cuenta por pagar al proveedor

**Este flujo completo te permite:**
- Control detallado de cada etapa del proceso de venta
- Trazabilidad completa desde el boleto hasta el pago
- Cálculos automáticos de márgenes y comisiones
- Documentación automática (facturas, liquidaciones)

## CARACTERÍSTICAS TÉCNICAS

### Backend:
- Django 5.x con Django REST Framework
- PostgreSQL (producción) / SQLite (desarrollo)
- APIs REST completas
- Autenticación JWT
- Python 3.12+

### Frontend:
- Next.js 13+ con React
- TypeScript
- Tailwind CSS
- Responsive design

### Integraciones:
- Google Gemini AI (para mí, Linkeo)
- Google Vision AI (OCR)
- Gmail API (importación boletos)
- Twilio (WhatsApp)
- Pasarelas de pago (planificado)

## CONTABILIDAD VENEZUELA (VEN-NIF)

### Dualidad Monetaria:
- USD (moneda funcional)
- BSD (moneda de presentación legal)

### Automatizaciones:
- Asientos contables desde facturas
- Diferencial cambiario automático
- Provisión INATUR mensual (1%)
- Actualización tasa BCV

### Comandos:
```bash
python manage.py actualizar_tasa_bcv --tasa 45.50
python manage.py provisionar_inatur --mes 1 --anio 2025
```

## ESTADOS DE VENTA

### Estados Financieros (auto-gestionados):
- PEN: Pendiente de Pago
- PAR: Pagada Parcialmente
- PAG: Pagada Totalmente

### Estados Operativos (manuales):
- CNF: Confirmada
- VIA: En Proceso/Viaje
- COM: Completada
- CAN: Cancelada

### Puntos de Fidelidad:
- 1 punto por cada 10 unidades monetarias
- Se otorgan al completar pago o llegar a estado COM
- Idempotente (no duplica)

## TIPOS DE PRODUCTOS/SERVICIOS

### Boletos Aéreos:
- Importación automática
- Múltiples segmentos
- Cálculo de tarifas y fees

### Hoteles:
- Reservas con check-in/out
- Régimen alimenticio
- Número de noches

### Paquetes:
- Combinación de servicios
- Itinerario multi-día
- Componentes flexibles

### Servicios Adicionales:
- Seguros de viaje
- Traslados
- Tours y excursiones
- Alquiler de autos
- SIM cards
- Lounge access

## PROVEEDORES

### Tipos:
- Consolidador
- Mayorista
- Directo
- Otros

### Gestión:
- Niveles y comisiones
- Liquidaciones automáticas
- Cuentas por pagar
- Historial de transacciones

## REPORTES Y ANÁLISIS

### Dashboard:
- Métricas en tiempo real
- Ventas por período
- Clientes frecuentes
- Proveedores principales

### Reportes Contables:
- Libro diario
- Balance de comprobación
- Validación de cuadre
- Exportación a Excel

### Auditoría:
- Logs de todas las operaciones
- Trazabilidad completa
- Historial de cambios
- Detección de inconsistencias

## SEGURIDAD

### Autenticación:
- JWT con refresh tokens
- Rotación automática
- Blacklist de tokens
- Sesiones seguras

### Permisos:
- Roles por usuario
- Permisos granulares
- Auditoría de accesos

### Headers de Seguridad:
- CSP (Content Security Policy)
- HSTS
- X-Frame-Options
- X-Content-Type-Options

## PRÓXIMAS FUNCIONALIDADES

### Corto Plazo (0-6 meses):
- Dashboard avanzado con filtros
- Campañas de email marketing
- Integración WhatsApp Business
- Conciliación bancaria

### Mediano Plazo (6-12 meses):
- Motor de reservas online
- Integración nativa con GDS
- Cotizaciones automáticas
- CRM inteligente avanzado

### Largo Plazo (12-24 meses):
- IA predictiva de demanda
- Dynamic pricing
- Marketplace de agencias
- Plataforma de datos regional

## COMANDOS ÚTILES

### Desarrollo:
```bash
python manage.py runserver
python manage.py migrate
python manage.py createsuperuser
python manage.py loaddata [fixture]
```

### Catálogos:
```bash
python manage.py load_catalogs
python manage.py load_catalogs --only paises monedas
python manage.py load_catalogs --upsert
```

### Notificaciones:
```bash
python manage.py enviar_recordatorios_pago --dias=3
```

### Contabilidad:
```bash
python manage.py actualizar_tasa_bcv --tasa 45.50
python manage.py provisionar_inatur --mes 1 --anio 2025
```

## SOPORTE Y DOCUMENTACIÓN

### Archivos Clave:
- README.md: Documentación principal
- ROADMAP_AUTOMATIZACION.md: Plan de desarrollo
- AUDIT.md: Sistema de auditoría
- CONTABILIDAD_VENEZUELA_VEN_NIF.md: Contabilidad
- TRANSLATOR_API.md: APIs del traductor

### Contacto:
- Desarrollador: Linkeo Tech
- Soporte: A través del sistema
- Documentación: En el repositorio

## PRECIOS Y PLANES

IMPORTANTE: No proporciones precios específicos. 
Siempre indica que un agente humano debe cotizar según:
- Destino y fechas
- Número de personas
- Tipo de servicio
- Temporada
- Disponibilidad

## LIMITACIONES DE LINKEO

Como asistente virtual, NO puedo:
- Confirmar reservas (solo agentes humanos)
- Dar precios exactos sin cotización
- Acceder a datos privados de clientes
- Procesar pagos
- Modificar reservas existentes

SÍ puedo:
- Explicar cómo funciona el sistema
- Guiar en el uso de funcionalidades
- Responder preguntas sobre destinos
- Explicar requisitos de viaje
- Orientar sobre servicios disponibles
- Conectar con un agente humano
"""

def get_knowledge_context() -> str:
    """Retorna el contexto de conocimiento para Linkeo."""
    return TRAVELHUB_KNOWLEDGE