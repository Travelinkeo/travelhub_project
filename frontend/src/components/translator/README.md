# Componentes del Traductor de Itinerarios

Este directorio contiene los componentes React para la funcionalidad del traductor de itinerarios en TravelHub.

## Componentes

### 1. ItineraryTranslator.tsx
Componente principal para traducir itinerarios individuales.

**Características:**
- Selección de sistema GDS (SABRE, AMADEUS, KIU)
- Validación de formato antes de traducir
- Traducción en tiempo real
- Visualización de errores y advertencias

**Props:** Ninguna (usa contexto de autenticación)

### 2. PriceCalculator.tsx
Calculadora de precios de boletos con fees y porcentajes.

**Características:**
- Cálculo automático de precios
- Desglose detallado de costos
- Validación de valores negativos
- Formato de moneda

**Props:** Ninguna (usa contexto de autenticación)

### 3. BatchTranslator.tsx
Traductor en lote para múltiples itinerarios.

**Características:**
- Hasta 10 itinerarios por lote
- Gestión dinámica de items
- Resumen de procesamiento
- Resultados individuales por item

**Props:** Ninguna (usa contexto de autenticación)

## Uso

```tsx
import ItineraryTranslator from '@/components/translator/ItineraryTranslator';
import PriceCalculator from '@/components/translator/PriceCalculator';
import BatchTranslator from '@/components/translator/BatchTranslator';

// En tu componente
<ItineraryTranslator />
<PriceCalculator />
<BatchTranslator />
```

## APIs Utilizadas

Los componentes consumen las siguientes APIs:

- `GET /api/translator/gds/` - Sistemas GDS soportados
- `POST /api/translator/validate/` - Validar formato
- `POST /api/translator/itinerary/` - Traducir itinerario
- `POST /api/translator/calculate/` - Calcular precio
- `POST /api/translator/batch/` - Traducción en lote

## Estilos

Los estilos están definidos en `translator.css` usando Tailwind CSS con clases personalizadas para:

- `.flight-result` - Resultados de vuelos traducidos
- `.error` - Mensajes de error
- `.loading` - Estados de carga
- `.batch-*` - Estilos para procesamiento en lote

## Dependencias

- React 18+
- Next.js 13+
- Tailwind CSS
- Contexto de autenticación (`@/contexts/AuthContext`)

## Estados de Carga

Todos los componentes manejan estados de carga apropiados:
- Botones deshabilitados durante procesamiento
- Indicadores visuales de "Cargando..."
- Manejo de errores de red

## Validación

- Validación de entrada en tiempo real
- Mensajes de error descriptivos
- Límites de seguridad (10 items máximo en lote)
- Validación de valores numéricos

## Responsive Design

Los componentes están optimizados para:
- Desktop (grid layouts)
- Tablet (layouts adaptivos)
- Mobile (layouts apilados)

## Ejemplos de Uso

### Itinerario SABRE
```
1 AA 1234 15JAN W MIABOG 0800 1200
```

### Cálculo de Precio
- Tarifa: $100.00
- Fee Consolidador: $25.00
- Fee Interno: $15.00
- Porcentaje: 10%
- **Resultado: $154.00**

### Lote de Itinerarios
```json
[
  {
    "id": "vuelo_1",
    "itinerary": "1 AA 1234 15JAN W MIABOG 0800 1200",
    "gds_system": "SABRE"
  },
  {
    "id": "vuelo_2", 
    "itinerary": "2 UA 5678 16JAN W BOGMIA 1400 1800",
    "gds_system": "SABRE"
  }
]
```