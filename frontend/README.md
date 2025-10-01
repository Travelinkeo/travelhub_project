# TravelHub Frontend (Next.js)

Base inicial para el frontend público de TravelHub.

## Stack
- Next.js 14 (App Router) + React 18 + TypeScript
- Tailwind CSS
- ESLint + Prettier

## Scripts
- `npm run dev` inicia servidor desarrollo (http://localhost:3000)
- `npm run build` build producción
- `npm start` arranca modo producción
- `npm run lint` linting
- `npm run type-check` verificación TS
- `npm run format` formateo con Prettier

## Variables de entorno
Crear `.env.local` basado en `.env.example`:
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Seguridad inicial
- Headers de seguridad básicos en `next.config.mjs` (CSP en modo inicial — ajustar dominios).
- Deshabilitado `X-Powered-by`.
- Wrapper `apiFetch` centraliza llamadas para futura inyección de auth tokens / refresh.

## Próximos pasos sugeridos
1. Añadir autenticación (JWT via DRF o cookies httpOnly).
2. Generar tipos cliente desde OpenAPI (drf-spectacular + openapi-typescript).
3. Añadir design system (componentes base: Button, Input, Card, Modal).
4. Configurar tests (Jest + Testing Library + Playwright E2E).
5. Integrar analítica (Plausible / Posthog).
6. Migrar CSP a modo estricto quitando `unsafe-inline`.

## Desarrollo
Iniciar backend (Django) en 8000 y luego:
```
npm install
npm run dev
```

## Licencia
Propietario interno TravelHub / Travelinkeo.

---

## Arquitectura del Frontend y Patrones de Desarrollo

Para asegurar un desarrollo robusto, escalable y libre de errores de tipo, seguimos una serie de patrones y una arquitectura definida.

### 1. Centralización de Tipos de la API

**Objetivo:** Tener una única fuente de verdad para la "forma" de los datos que se intercambian con el backend de Django.

**Implementación:**
- Todas las interfaces de TypeScript que definen la estructura de los objetos de la API (ej: `Cliente`, `Venta`, `Proveedor`) deben estar en el archivo `src/types/api.ts`.
- Esto previene errores de inconsistencia y tipos duplicados, y permite reutilizar las definiciones en todo el frontend.

*(Este es el Paso 1 del plan de refactorización iniciado el 23/09/2025 para estabilizar el proyecto.)*

### 2. Hook de API Reutilizable (`useApi`)

**Objetivo:** Centralizar la lógica de fetching de datos, manejo de estados de carga y errores en un solo lugar.

**Implementación:**
- Se ha creado el hook `useApi` en `src/hooks/useApi.ts`.
- Utiliza `SWR` para gestionar el ciclo de vida de los datos (fetching, caching, revalidación).
- Debe usarse en los componentes para obtener datos de la API de forma segura y tipada.
- **Ejemplo de uso:** `const { data, isLoading, error } = useApi<Cliente[]>('/api/clientes/');`

*(Este es el Paso 2 del plan de refactorización iniciado el 23/09/2025.)*

### 3. Saneamiento del Entorno y Refactorización

**Objetivo:** Eliminar todos los errores de tipo y aplicar los nuevos patrones al código existente.

**Implementación:**
- Se degradaron las dependencias de `@mui/material` de una versión inestable v7 a la versión estable v5, lo que solucionó errores de tipo irresolubles en el componente `Grid`.
- Se refactorizaron todos los componentes de CRM (`clientes`, `proveedores`) y el listado de `ventas` para usar el patrón de tipos centralizados y el hook `useApi`.
- Se corrigieron errores de ejecución gracias a la mejora del hook `useApi` para que maneje la paginación de la API de Django automáticamente.

**Resultado:** El proyecto está 100% libre de errores de TypeScript, es estable y está listo para seguir creciendo sobre una base sólida.

*(Este es el Paso 3 del plan de refactorización completado el 23/09/2025.)*