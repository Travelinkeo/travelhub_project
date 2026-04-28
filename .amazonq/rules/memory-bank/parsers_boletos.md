# Parsers de Boletos - Estado Actual

## Parsers Implementados y Funcionando

### 1. KIU Parser ✅
- **Archivo**: `core/kiu_parser.py`
- **Estado**: Completamente funcional
- **Plantilla PDF**: `core/templates/core/tickets/ticket_template_kiu.html`
- **Características**:
  - Parsea boletos de KIU GDS
  - Genera PDF con formato profesional
  - Extrae información de pasajero, vuelos, precios

### 2. SABRE Parser ✅
- **Archivo**: `core/sabre_parser.py`
- **Estado**: Completamente funcional
- **Plantilla PDF**: `core/templates/core/tickets/ticket_template_sabre.html`
- **Características**:
  - Parsea boletos de SABRE GDS
  - Genera PDF con formato profesional
  - Maneja múltiples formatos de SABRE

### 3. TK Connect Parser ✅
- **Archivo**: `core/tk_connect_parser.py`
- **Estado**: Completamente funcional
- **Plantilla PDF**: `core/templates/core/tickets/ticket_template_tk_connect.html`
- **Características**:
  - Parsea boletos de Turkish Airlines (TK Connect)
  - Genera PDF con formato profesional
  - Extrae información específica de TK

## Parsers Completados

### 4. AMADEUS Parser ✅
- **Archivo**: `core/amadeus_parser.py`
- **Estado**: Completamente funcional e integrado
- **Plantilla PDF**: `core/templates/core/tickets/ticket_template_amadeus.html`
- **Color**: #0c66e1 (azul AMADEUS)
- **Características**:
  - Parsea boletos de AMADEUS GDS
  - Extrae PNR, número de boleto, pasajero
  - Extrae información de agencia (IATA, dirección)
  - Extrae vuelos completos con todos los detalles
  - Genera PDF con estilo SABRE adaptado
  - Integrado en sistema de ventas

### 5. Copa SPRK Parser ✅
- **Archivo**: `core/copa_sprk_parser.py`
- **Estado**: Completamente funcional e integrado
- **Plantilla PDF**: `core/templates/core/tickets/ticket_template_copa_sprk.html`
- **Color**: #0032a0 (azul Copa Airlines)
- **Archivo de prueba**: `OTRA CARPETA\OSCAR DUQUE.pdf`
- **Características**:
  - Parsea boletos de Copa Airlines (sistema SPRK)
  - Extrae PNR, número de boleto, pasajero
  - Extrae 4 vuelos con origen, destino, fechas, horas
  - Clase y cabina de vuelo
  - Genera PDF con estilo SABRE
  - Integrado en sistema de ventas

### 6. Wingo Parser ✅
- **Archivo**: `core/wingo_parser.py`
- **Estado**: Completamente funcional e integrado
- **Plantilla PDF**: `core/templates/core/tickets/ticket_template_wingo.html`
- **Color**: #6633cb (morado Wingo)
- **Archivo de prueba**: `OTRA CARPETA\MSYHMI.pdf`
- **Características**:
  - Parsea reservas de Wingo (aerolínea low-cost)
  - Extrae PNR y pasajero
  - NO genera número de boleto (low-cost)
  - Fecha automática del sistema si no hay fecha
  - Extrae vuelos con origen, destino, fechas, horas
  - Genera PDF simplificado sin número de boleto
  - Integrado en sistema de ventas

## Estructura General de Parsers

Todos los parsers siguen esta estructura:
1. Lectura del archivo PDF del boleto
2. Extracción de texto usando PyPDF2 o similar
3. Parsing de información (pasajero, vuelos, precios, etc.)
4. Generación de PDF usando plantilla HTML
5. Guardado en `media/boletos_generados/`

## Plantillas HTML

Ubicación: `core/templates/core/tickets/`
- `ticket_template_kiu.html`
- `ticket_template_sabre.html`
- `ticket_template_tk_connect.html`
- `ticket_template_amadeus.html` (en desarrollo)
- `ticket_template_wingo.html`
- `ticket_template_copa_sprk.html`

Todas usan:
- Paleta de colores Travelinkeo (azules)
- Logo de la agencia
- Formato profesional A4
- Estilos CSS inline para PDF

## Sistema Completo

Todos los parsers están completamente integrados en el sistema de ventas:
- ✅ Detección automática por heurística
- ✅ Generación de PDF con plantillas personalizadas
- ✅ Colores corporativos de cada aerolínea/GDS
- ✅ Endpoint API `/api/boletos/upload/`
- ✅ Guardado automático en BoletoImportado

## Heurísticas de Detección

1. **SABRE**: `'ETICKET RECEIPT'` + `'RESERVATION CODE'`
2. **KIU**: `'KIUSYS.COM'` o `'PASSENGER ITINERARY RECEIPT'`
3. **AMADEUS**: `'ELECTRONIC TICKET RECEIPT'` + `'BOOKING REF:'`
4. **TK Connect**: `'IDENTIFICACIÓN DEL PEDIDO'` o `'GRUPO SOPORTE GLOBAL'`
5. **Copa SPRK**: `'COPA AIRLINES'` + `'LOCALIZADOR DE RESERVA'` o `'SPRK'`
6. **Wingo**: `'WINGO'` o `'WINGO.COM'`
