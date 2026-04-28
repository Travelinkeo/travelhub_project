# Estrategia anti-ciclos y orden de carga para modularización de modelos

## Patrones recomendados

1. **Imports diferidos con TYPE_CHECKING**
   - Utilizar `from typing import TYPE_CHECKING` y bloques `if TYPE_CHECKING:` para importar modelos solo en tiempo de análisis, evitando ciclos de importación.
   - Ejemplo:
     ```python
     from typing import TYPE_CHECKING
     if TYPE_CHECKING:
         from core.models.ventas import Venta
     ```

2. **Uso de get_user_model()**
   - Para referencias al modelo de usuario, usar `get_user_model()` en vez de importar directamente el modelo.
   - Ejemplo:
     ```python
     from django.contrib.auth import get_user_model
     User = get_user_model()
     ```

3. **Señales (signals) al final del módulo**
   - Definir y conectar señales al final de cada archivo de modelos, nunca en la parte superior, para asegurar que todos los modelos estén cargados.
   - Ejemplo:
     ```python
     # ...definición de modelos...
     from django.db.models.signals import post_save
     # conectar señales aquí
     ```

4. **Imports locales en funciones/métodos**
   - Cuando sea necesario importar modelos de otros módulos, hacerlo dentro de funciones o métodos para evitar ciclos globales.
   - Ejemplo:
     ```python
     def procesar_venta(...):
         from core.models.ventas import Venta
         # lógica aquí
     ```

5. **Evitar imports directos entre módulos de modelos**
   - Preferir interfaces desacopladas y acceso por métodos/fábricas cuando sea posible.

## Orden de carga recomendado
- Mantener la inicialización de modelos y señales en el orden: modelos → señales → utilidades.
- Verificar que ningún modelo dependa de la inicialización de otro en el constructor (`__init__`).

---

# Riesgos y mitigaciones en modularización de modelos

## Riesgos principales
1. **Ciclos de importación**
   - Causa: Referencias cruzadas entre modelos en distintos módulos.
   - Mitigación: Imports diferidos, uso de TYPE_CHECKING, imports locales.

2. **Migraciones accidentales**
   - Causa: Cambios en rutas de importación o nombres de modelos.
   - Mitigación: Mantener nombres y rutas hasta cleanup final, usar re-export en `__init__.py`, verificar con `makemigrations --check`.

3. **Conflictos en PRs**
   - Causa: Refactor simultáneo por varios desarrolladores.
   - Mitigación: Fases bien definidas, PRs pequeños y secuenciales, comunicación clara.

4. **Errores en señales**
   - Causa: Señales conectadas antes de que todos los modelos estén cargados.
   - Mitigación: Conectar señales al final de cada módulo.

5. **Tiempos de importación aumentados**
   - Causa: Imports innecesarios o globales.
   - Mitigación: Imports locales y diferidos.

## Checklist de verificación técnica
- Build y tests pasan sin errores.
- `makemigrations --check` no genera migraciones inesperadas.
- Cobertura de tests estable.
- Tiempos de importación similares o mejores.

---

# Entregable final
Este documento consolida el plan de modularización de modelos, patrones anti-ciclos, riesgos y mitigaciones. Listo para revisión y ejecución en equipo.

> Última actualización: 2025-09-02
