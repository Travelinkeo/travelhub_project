# Frontend de Boletería - TravelHub

## 📁 Estructura Implementada

```
frontend/src/
├── types/
│   └── boletos.ts              # TypeScript types
├── lib/
│   └── api/
│       └── boletos.ts          # API functions
└── app/
    └── boletos/
        ├── layout.tsx          # Layout con navegación
        ├── dashboard/
        │   └── page.tsx        # Dashboard en tiempo real
        ├── buscar/
        │   └── page.tsx        # Búsqueda avanzada
        ├── reportes/
        │   └── page.tsx        # Reportes de comisiones
        └── anulaciones/
            └── page.tsx        # Solicitar anulaciones
```

## 🚀 Cómo Usar

### 1. Configurar Variables de Entorno

Crear `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Instalar Dependencias (si es necesario)

```bash
cd frontend
npm install
```

### 3. Iniciar Frontend

```bash
npm run dev
```

### 4. Acceder a las Páginas

- **Dashboard**: http://localhost:3000/boletos/dashboard
- **Buscar**: http://localhost:3000/boletos/buscar
- **Reportes**: http://localhost:3000/boletos/reportes
- **Anulaciones**: http://localhost:3000/boletos/anulaciones

## 📊 Funcionalidades Implementadas

### ✅ Dashboard en Tiempo Real
- Métricas de boletos procesados (hoy/semana/mes)
- Top 5 aerolíneas
- Boletos pendientes y con errores
- Actualización automática cada 30 segundos

### ✅ Búsqueda Avanzada
- Filtros múltiples:
  - Nombre de pasajero
  - PNR
  - Rango de fechas
  - Origen/Destino
  - Aerolínea
- Resultados en tiempo real

### ✅ Reportes de Comisiones
- Selección de período
- Totales generales
- Desglose por aerolínea
- Tabla detallada

### ✅ Anulaciones
- Formulario de solicitud
- Cálculo automático de reembolso
- Tipos: Voluntaria, Involuntaria, Cambio

## 🔐 Autenticación

El sistema usa JWT tokens almacenados en `localStorage`:

```javascript
// Login (implementar en tu página de login)
const response = await fetch('/api/auth/login/', {
  method: 'POST',
  body: JSON.stringify({ username, password })
});
const { access } = await response.json();
localStorage.setItem('accessToken', access);
```

## 🎨 Estilos

El proyecto usa **Tailwind CSS**. Los componentes ya tienen estilos básicos aplicados.

## 📝 Próximos Pasos

### Funcionalidades Adicionales a Implementar:

1. **Validación de Boletos**
   - Componente para validar boletos individuales
   - Mostrar errores y advertencias

2. **Historial de Cambios**
   - Vista de historial por boleto
   - Timeline de cambios

3. **Notificaciones**
   - Toast notifications para acciones exitosas/fallidas
   - Alertas en tiempo real

4. **Exportación**
   - Exportar reportes a Excel/PDF
   - Descargar resultados de búsqueda

## 🐛 Troubleshooting

### Error: "Cannot find module '@/types/boletos'"

Verificar que `tsconfig.json` tenga:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### Error: "localStorage is not defined"

Asegurarse de usar `'use client'` en componentes que usan localStorage.

### Error de CORS

Verificar que Django tenga configurado CORS:

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
```

## 📚 Recursos

- **Documentación Backend**: `.amazonq/rules/memory-bank/guia_integracion_frontend_boleteria.md`
- **API Endpoints**: Ver documentación de backend
- **Types**: `frontend/src/types/boletos.ts`

---

**Última actualización**: 25 de Enero de 2025  
**Estado**: ✅ 4 páginas principales implementadas  
**Autor**: Amazon Q Developer
