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
- Deshabilitado `X-Powered-By`.
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
