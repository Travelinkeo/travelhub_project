# Automatización de APIs REST para Modelos en Django Admin

## Resumen

Se ha implementado un sistema de automatización para generar APIs REST automáticamente para modelos registrados en Django Admin. Esto elimina la necesidad de crear manualmente Serializers y ViewSets para cada nuevo modelo, reduciendo errores 404/403 por modelos nuevos.

## Arquitectura

### Backend

- **api_registry.py**: Contiene la lógica para escanear `admin.site._registry` y generar Serializers y ViewSets dinámicos.
- **urls.py**: Registra automáticamente las APIs generadas en el router de DRF.

### Frontend

- **hooks/api.ts**: Hooks genéricos usando SWR para operaciones CRUD (listar, crear, actualizar, eliminar).
- **components/ApiTable.tsx**: Componente genérico para mostrar datos en tablas.

## Beneficios

- **Escalabilidad**: Nuevos modelos en admin generan APIs automáticamente.
- **Consistencia**: Todas las APIs siguen el mismo patrón.
- **Mantenibilidad**: Código reutilizable, menos duplicación.
- **Rapidez**: Desarrollo más rápido de nuevas funcionalidades.

## Uso

### Backend

1. Registra el modelo en admin.py.
2. Las APIs se generan automáticamente en `/api/{model_name}/`.

### Frontend

```tsx
import { ApiTable } from '../components/ApiTable';

const columns = [
  { key: 'id', label: 'ID' },
  { key: 'name', label: 'Nombre' },
];

<ApiTable endpoint="model_name" columns={columns} title="Título" />
```

## Limitaciones

- Modelos con relaciones complejas pueden requerir Serializers personalizados.
- No maneja automáticamente permisos avanzados (solo autenticación básica).
- Campos binarios o especiales pueden necesitar ajustes.

## Próximos Pasos

- Mejorar manejo de relaciones anidadas.
- Agregar filtros y búsqueda automática.
- Implementar paginación en componentes frontend.
- Añadir validaciones personalizadas.