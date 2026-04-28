# Auditoría (AuditLog)

Este documento describe el diseño actual del módulo de auditoría básico y lineamientos para su evolución.

## Objetivos

* Registrar eventos críticos que afectan la trazabilidad de ventas y sus componentes.
* Proveer un endpoint API de solo lectura para inspección y monitoreo.
* Mantener implementación mínima, extensible por iteraciones futuras (CREATE / UPDATE / STATE changes).

## Modelo `AuditLog`

Campo | Tipo | Descripción
------|------|------------
`id_audit_log` | AutoField | Identificador interno.
`modelo` | CharField | Nombre del modelo afectado (ej: `Venta`, `ItemVenta`).
`object_id` | CharField | ID (string) del objeto afectado (se almacena como texto para flexibilidad).
`venta` | FK nullable a `Venta` | Venta asociada (si aplica). `on_delete=CASCADE` (si la venta se elimina también sus logs). 
`accion` | CharField | Enum: `CREATE`, `UPDATE`, `DELETE`, `STATE` (solo `DELETE` activo en esta iteración).
`descripcion` | Text | Resumen breve legible.
`datos_previos` | JSON | Snapshot previo (reservado para futuras acciones UPDATE/STATE).
`datos_nuevos` | JSON | Snapshot nuevo (reservado para futuras acciones UPDATE/STATE).
`metadata_extra` | JSON | Datos adicionales libres (por ahora se usa para `venta_id` al eliminar una venta si cambiamos política futura de FK).
`creado` | DateTime | Marca de tiempo (indexed, ordering desc).

### Acciones Implementadas

Acción | Estado | Fuente | Detalle
-------|--------|--------|--------
`DELETE` | Activa | Señales `post_delete` | `Venta`, `ItemVenta`.
`STATE` | Activa | Override `Venta.save()` | Cambio de `estado` en `Venta`.
`CREATE` | Activa | Override `save()` | Creación de `Venta` e `ItemVenta` (subset campos).
`UPDATE` | Activa | Override `save()` | Cambios en campos de texto seleccionados (differences en `metadata_extra.diff`).

Para `STATE` se captura automáticamente el valor anterior y el nuevo en `datos_previos` / `datos_nuevos` al detectar que `estado` cambió entre la instancia original y la persistida.

Se registran actualmente:
* Eliminaciones (`DELETE`) de `Venta` e `ItemVenta`.
* Cambios de estado (`STATE`) de `Venta` (por ejemplo `PEN -> CNF`).
* Creaciones (`CREATE`) de `Venta` e `ItemVenta`.
* Actualizaciones (`UPDATE`) solo de campos seleccionados (ver abajo) para reducir ruido.

Motivación del alcance limitado inicial:
1. Reducir superficie de impacto y riesgo transaccional.
2. Validar performance y volumen esperado.
3. Establecer formato estable antes de capturar diffs complejos.

## Creación de Logs

La función interna `_crear_audit_log(...)` encapsula la creación y atrapa excepciones para no bloquear el flujo de negocio.

Se emplean señales `post_delete` para `Venta` e `ItemVenta`:
```python
@receiver(post_delete, sender=Venta)
@receiver(post_delete, sender=ItemVenta)
```

Para la protección de borrado de una `Venta` con componentes se usa el override de `Venta.delete()` (no señal `pre_delete`) evitando `TransactionManagementError` previos.

## API REST

Endpoint base (router DRF):
```
/ api / audit-logs /
```

Características:
* `ReadOnlyModelViewSet`.
* Paginación desactivada (`pagination_class = None`) para facilitar integraciones simples y tests (posible cambio futuro a limit/offset o cursor).
* Permisos: autenticado + admin para operaciones de escritura (actualmente no hay escritura vía API; sólo lectura). Clase aplicada: `IsAdminOrReadOnly` combinada con `IsAuthenticated`.
* Orden default: más recientes primero (`-creado`).

### Filtros y Búsqueda
Parámetro | Ejemplo | Descripción
----------|---------|------------
`modelo` | `?modelo=Venta` | Filtra por nombre exacto de modelo.
`accion` | `?accion=DELETE` | Filtra por acción.
`venta` | `?venta=123` | Filtra por venta asociada (solo si el log la conserva; en esta iteración el log de `Venta` al eliminarse NO conserva la FK a sí misma, porque se elimina por cascade después de generar el log de los items).
`created_from` | `?created_from=2025-08-01` | Fecha mínima (UTC date portion) de creación.
`created_to` | `?created_to=2025-08-31` | Fecha máxima (UTC date portion) de creación.
`search` | `?search=eliminada` | Búsqueda en `object_id` y `descripcion`.

Nota: Dado `on_delete=CASCADE`, un log que tenga `venta` y la venta se elimina, también desaparecerá. Extensión futura: cambiar a `SET_NULL` para preservación total.

### Ejemplo de Respuesta (DELETE Venta)
```json
[
  {
    "id_audit_log": 42,
    "modelo": "Venta",
    "object_id": "123",
    "venta": null,
    "accion": "DELETE",
    "descripcion": "Venta eliminada 123",
    "datos_previos": null,
    "datos_nuevos": null,
    "metadata_extra": {"venta_id": 123},
    "creado": "2025-08-30T19:20:03.970684-04:00"
  }
]
```

## Estrategia de Evolución

Iteración | Meta | Detalles Técnicos / Consideraciones
---------|------|-------------------------------------
1 (Inicial) | DELETE básico | Señales post_delete y override `delete()` en `Venta`.
2 | Añadido STATE (cambios estado Venta) | Override `Venta.save()` comparando estado anterior.
3 (Actual) | CREATE & UPDATE selectivo | Override `save()` con lista blanca de campos.
4 | Diffs compactos multi-modelo | Extender a más modelos, permitir máscara de campos.
4 | Diffs compactos | Guardar sólo campos cambiados (`changed_fields`) en `metadata_extra` para UPDATE (optimiza almacenamiento + lectura).
5 | Retención / Purga | Comando `manage.py purge_audit_logs --older-than 180` (días) parametrizable.
6 | Indexación ampliada | Índices compuestos (`modelo`, `accion`, `creado`) para acelerar analítica.
7 | Export / Streaming | Endpoint para descarga CSV/NDJSON y potencial WebSocket o webhook.
8 | Configuración Declarativa | Matriz en settings definible: qué modelos y acciones auditar, con exclusiones de campos.

## Descarga Masiva / Consideraciones de Volumen

Si el volumen crece y se reactiva paginación:
* Adoptar `LimitOffsetPagination` con límites razonables (`?limit=` / `?offset=`).
* Documentar un máximo (ej: 500) para proteger el servidor.
* Ofrecer export batch (NDJSON) para ETL.

## Buenas Prácticas Futuras
* Evitar auditar campos sensibles (tokens, credenciales, datos personales fuera de alcance necesario).
* Enmascarar valores (ej: 4 últimos dígitos) cuando se agreguen pagos u otros modelos financieros sensibles.
* Añadir pruebas de performance para lote de 10k registros.

## Tests

Archivo | Cobertura
-------|----------
`tests/test_auditlog.py` | Lógica de bloqueo y generación de logs en eliminación.
`tests/test_auditlog_api.py` | Endpoint listado, filtros básicos.

## Decisiones Tomadas en Esta Iteración
* `on_delete=CASCADE` se mantiene para simplificar consistencia referencial inicial.
* Paginación desactivada para respuestas simples y reducir fricción en primeras integraciones.
* Lista blanca de campos para UPDATE (Venta: `descripcion_general`, `notas`; ItemVenta: `descripcion_personalizada`, `codigo_reserva_proveedor`, `notas_item`).
* Diffs almacenados en `metadata_extra.diff` con estructura `{campo: {antes, despues}}`.

## Posibles Cambios Inmediatos (Low Hanging Fruit)
1. Cambiar FK a `SET_NULL` y reintroducir filtro por `venta` en API sin perder logs.
2. Añadir bandera de configuración (`settings.AUDIT_ENABLED_MODELS`).
3. Campo `usuario` (FK a User) para atribución si acción viene de API/panel admin.
4. Middleware capturando `request.META['REMOTE_ADDR']` en `metadata_extra`.

## Resumen
Implementación mínima viable centrada en DELETE para ganar visibilidad inmediata. El diseño permite crecer hacia CREATE/UPDATE/STATE y políticas de retención sin refactor invasivo.
