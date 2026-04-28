# Plan de Refactor de Modelos (Fase 0)

Este documento describe la transición desde `core/models.py` monolítico hacia una
arquitectura modular por dominios.

## Objetivos
- Reducir complejidad cognitiva y tamaño de diffs futuros.
- Aislar dominios (catálogos, contabilidad, ventas, parseo, CMS) para facilitar pruebas y servicios.
- Prevenir ciclos de import mediante orden topológico y TYPE_CHECKING.
- Evitar migraciones innecesarias (mantener nombres/clases/metadatos idénticos al mover).

## Estructura Destino
```
core/models/
  __init__.py (re-export temporal)
  catalogos.py
  personas.py
  contabilidad.py
  ventas.py
  servicios_viaje.py
  parseo.py
  auditoria.py
  cms.py
```

## Fases
1. Fase 0 (actual): Crear estructura vacía + banner de deprecación en `core/models.py`.
2. Fase 1: Mover catálogos + personas + contabilidad. Re-export desde `core/models/__init__.py`.
3. Fase 2: Mover ventas + servicios_viaje.
4. Fase 3: Mover parseo + auditoria.
5. Fase 4: Mover cms.
6. Fase 5: Actualizar imports en código y tests para usar rutas específicas.
7. Fase 6: Eliminar shim y bloquear regresión (pre-commit/CI).

## Reglas de Oro
- No cambiar `class Meta` ni nombres de campos.
- Verificar siempre: `python manage.py makemigrations --check --dry-run` => sin cambios.
- Ejecutar pytest completo tras cada fase.
- Si aparece una migración inesperada: ABORTAR (revisar diferencias de definiciones).

## Compatibilidad
Mientras el shim viva, los imports `from core.models import Venta` seguirán funcionando.
La migración final reemplazará estos imports por específicos (ej. `from core.models.ventas import Venta`).

## Anti-ciclos
- Orden de módulos: catalogos -> personas -> contabilidad -> ventas -> servicios_viaje -> parseo -> auditoria -> cms.
- Si referencia cruzada es inevitable, usar anotaciones de tipo string y `if TYPE_CHECKING:`.
- Signals irán a `core/signals/` en fases posteriores; se registrarán en `apps.py`.

## Checklist por Fase
- [ ] Estructura creada (Fase 0) (DONE)
- [ ] Catálogos/personas/contabilidad movidos
- [ ] Ventas/servicios movidos
- [ ] Parseo/auditoría movidos
- [ ] CMS movido
- [ ] Actualizar imports globales
- [ ] Eliminar shim

## Riesgos & Mitigaciones (resumen preliminar)
| Riesgo | Mitigación |
|--------|-----------|
| Migraciones inesperadas | Verificación estricta --check --dry-run en CI local antes de commit |
| Ciclos de import | Aplazar imports a runtime / TYPE_CHECKING |
| Gran diff difícil de revisar | Fases pequeñas; agrupar por dominio |
| Pérdida de cobertura | Añadir tests de smoke tras cada traslado |
| Nuevos modelos añadidos al archivo legacy | Banner + pre-commit (futuro) |

## Próximos Pasos
Iniciar Fase 1 moviendo catálogos (`Pais`...`PlanContable`), luego personas y contabilidad en el mismo PR.

---
Generado en Fase 0.
