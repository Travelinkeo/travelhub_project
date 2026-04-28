# 🧪 Tests de TravelHub

Esta carpeta contiene todos los tests automatizados del proyecto TravelHub.

## 📊 Cobertura Actual

**Cobertura Total**: 85%+  
**Tests Totales**: 66+  
**Framework**: pytest

---

## 📁 Estructura de Tests

```
tests/
├── parsers/                    # Tests de parsers multi-GDS
│   ├── test_base_parser.py
│   ├── test_registry.py
│   └── test_parsers_integration.py
├── fixtures/                   # Archivos de prueba
│   └── sabre_rosangela_diaz_fixture.txt
├── conftest.py                 # Fixtures compartidas
└── test_*.py                   # Tests por módulo
```

---

## 🎯 Tests por Categoría

### 1. Tests de Parsers (19 tests)
- `test_base_parser.py` - Clase base de parsers
- `test_registry.py` - Registro dinámico
- `test_parsers_integration.py` - Integración
- `test_sabre_parser_enhanced.py` - Parser SABRE
- `test_parsers_coverage.py` - Cobertura adicional

**Cobertura**: 88%

### 2. Tests de APIs (25 tests)
- `test_api_ventas.py` - API de ventas
- `test_api_permissions.py` - Permisos
- `test_api_coverage_boost.py` - Cobertura
- `test_dashboard_api.py` - Dashboard
- `test_liquidaciones_api.py` - Liquidaciones
- `test_new_components_api.py` - Componentes

**Cobertura**: 85%

### 3. Tests de Notificaciones (6 tests) ⭐ FASE 5
- `test_notifications.py` - Email + WhatsApp

**Cobertura**: 90%

### 4. Tests de Caché (5 tests) ⭐ FASE 5
- `test_cache.py` - Redis caché

**Cobertura**: 95%

### 5. Tests de Celery (4 tests) ⭐ FASE 5
- `test_tasks.py` - Tareas asíncronas

**Cobertura**: 90%

### 6. Tests de ViewSets (5 tests) ⭐ FASE 5
- `test_cached_viewsets.py` - ViewSets con caché

**Cobertura**: 85%

### 7. Tests de Queries (4 tests) ⭐ FASE 5
- `test_query_optimization.py` - Optimización N+1

**Cobertura**: 90%

### 8. Tests de Middleware (5 tests) ⭐ FASE 5
- `test_middleware_performance.py` - Performance

**Cobertura**: 85%

### 9. Tests de Comandos (2 tests) ⭐ FASE 5
- `test_management_commands.py` - Comandos Django

**Cobertura**: 80%

### 10. Tests de Seguridad (11 tests)
- `test_security.py` - Seguridad general
- `test_security_headers.py` - Headers
- `test_csp_headers.py` - CSP
- `test_jwt_auth.py` - JWT

**Cobertura**: 90%

### 11. Tests de Auditoría (8 tests)
- `test_auditlog.py` - Logs de auditoría
- `test_audit_hash_chain.py` - Cadena de hash

**Cobertura**: 85%

### 12. Tests de Contabilidad (3 tests)
- `test_facturacion_venezuela.py` - VEN-NIF

**Cobertura**: 75%

---

## 🚀 Cómo Ejecutar

### Todos los tests
```bash
pytest
```

### Con cobertura
```bash
pytest --cov --cov-report=term-missing
```

### Tests de Fase 5
```bash
.\batch_scripts\run_tests_fase5.bat
```

### Tests específicos
```bash
# Tests de parsers
pytest tests/parsers/ -v

# Tests de APIs
pytest tests/test_api_*.py -v

# Tests de notificaciones
pytest tests/test_notifications.py -v

# Tests de caché
pytest tests/test_cache.py -v

# Tests de Celery
pytest tests/test_tasks.py -v
```

### Reporte HTML
```bash
pytest --cov --cov-report=html
# Abrir htmlcov/index.html
```

---

## 🔧 Fixtures Disponibles

### En `conftest.py`

#### Usuarios y Autenticación
- `usuario_staff` - Usuario con permisos de staff
- `api_client_staff` - Cliente API autenticado como staff
- `usuario_api` - Usuario normal
- `api_client_autenticado` - Cliente API autenticado

#### Datos de Prueba
- `venta_base` - Venta de ejemplo
- `sample_pais` - País de ejemplo (Venezuela)
- `sample_ciudad` - Ciudad de ejemplo (Caracas)

#### Mocks (Fase 5)
- `mock_redis` - Mock de Redis para tests de caché
- `mock_celery_task` - Mock de tareas Celery

---

## 📊 Cobertura por Módulo

| Módulo | Cobertura | Tests |
|--------|-----------|-------|
| core/cache_utils.py | 95% | 5 |
| core/tasks.py | 90% | 4 |
| core/notification_service.py | 90% | 6 |
| core/parsers/ | 88% | 19 |
| core/middleware_performance.py | 85% | 5 |
| core/views.py | 82% | 25 |
| contabilidad/ | 75% | 3 |

---

## 🎯 Objetivos de Cobertura

- ✅ **Cobertura total**: 85%+ (logrado)
- ✅ **Módulos críticos**: 90%+ (logrado)
- ✅ **APIs**: 85%+ (logrado)
- ✅ **Parsers**: 85%+ (logrado)

---

## 💡 Buenas Prácticas

### Naming
- Tests de módulo: `test_<module_name>.py`
- Tests de API: `test_api_<resource>.py`
- Tests de integración: `test_<feature>_integration.py`

### Estructura de Test
```python
def test_feature_description():
    # Arrange (preparar)
    data = {...}
    
    # Act (ejecutar)
    result = function(data)
    
    # Assert (verificar)
    assert result == expected
```

### Fixtures
- Usar fixtures para datos compartidos
- Mantener fixtures simples y reutilizables
- Documentar fixtures complejas

### Mocking
- Mockear servicios externos (Redis, Celery, APIs)
- No mockear código propio
- Usar `pytest-mock` para mocks

---

## 🐛 Debugging

### Ejecutar con debugger
```bash
pytest --pdb
```

### Ver prints
```bash
pytest -s
```

### Ver traceback completo
```bash
pytest --tb=long
```

### Solo tests que fallaron
```bash
pytest --lf
```

---

## 📈 CI/CD

Los tests se ejecutan automáticamente en GitHub Actions:
- ✅ En cada push
- ✅ En cada pull request
- ✅ Reporte de cobertura automático
- ✅ Tests deben pasar antes de merge

Ver: `.github/workflows/ci.yml`

---

## 📚 Documentación Relacionada

- `FASE5_CALIDAD_COMPLETADA.md` - Resumen de Fase 5
- `COMANDOS_FASE5.txt` - Comandos rápidos
- `CHECKLIST_FASE5.md` - Checklist de verificación
- `PROGRESO_PROYECTO.md` - Progreso general

---

## 🆘 Solución de Problemas

### Error: "No module named 'pytest'"
```bash
pip install pytest pytest-django pytest-cov pytest-mock
```

### Error: "Database not found"
```bash
python manage.py migrate
```

### Error: "Redis connection failed"
Los tests de caché usan mocks, no requieren Redis real.

### Tests lentos
```bash
# Ejecutar en paralelo
pip install pytest-xdist
pytest -n auto
```

---

**Última actualización**: Enero 2025  
**Cobertura**: 85%+  
**Tests**: 66+  
**Estado**: ✅ Fase 5 Completada
