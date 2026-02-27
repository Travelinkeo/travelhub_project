
# Análisis de Revisiones de IA Externas (Meta-Análisis)

He analizado los informes de **ChatGPT, GLM, Grok, Qwen, DeepSeek y Gemini**. Todos coinciden de manera sorprendente en los puntos fuertes y débiles.

## 🏆 Veredicto Unánime: "Producto Sólido"
Todas las IAs validaron tu enfoque:
- **"MVP Plus" / "Nivel Senior":** No es un proyecto amateur. La lógica fiscal y la automatización "Cero Clics" son ventajas competitivas reales.
- **Arquitectura Correcta:** Django + HTMX + Servicios es la elección perfecta para la agilidad que necesitas.

---

## ⚠️ Los 3 Puntos Críticos (Consenso)

### 1. El "Talón de Aquiles": El Bot de Email
**Crítica:** Correr un `while True` es "suicida" o "frágil". Si falla, el negocio se detiene.
**Solución Propuesta:** Migrar a **Celery + Redis**.
**Prioridad:** Alta (Infraestructura).

### 2. El Problema de Negocio: Duplicados vs. Reemisiones
**Crítica:** Bloquear duplicados (PNR repetido) es un error en turismo, donde existen re-emisiones, cambios y anulaciones.
**Solución Propuesta:** Implementar **Versionado de Boletos**.
- En lugar de decir "Ya existe, error", el sistema debería decir: "Ya existe, esta es la Versión 2 (Re-emisión)".
**Prioridad:** Crítica (Afecta el Modelo de Datos).

### 3. Deuda Técnica: Tests y Logging
**Crítica:** "Si mueve dinero, debe tener tests". Depender de `print` es arriesgado.
**Solución Propuesta:** `pytest` para facturación y parser.
**Prioridad:** Media (Calidad).

---

## 🛡️ Plan de Mejora "Pre-Limpieza de BD"

Como solicitaste aplicar mejoras *antes* de cargar datos reales, mi recomendación estratégica es aplicar **solo los cambios que afectan la estructura de la Base de Datos (Modelos)**.

### Propuesta: Implementar "Multipasajero y Versionado"
*Antes de limpiar la BD, hagamos que la BD esté lista para la realidad.*

1.  **Modelo `BoletoImportado` (Upgrade):**
    - Agregar campo `version` (Entero, default 1).
    - Agregar campo `parent_boleto` (ForeignKey a sí mismo, opcional).
    - Agregar campo `status` (EMITIDO, REEMITIDO, ANULADO).
2.  **Lógica del Parser:**
    - Detectar si el PNR ya existe.
    - Si existe y el número de boleto es diferente -> Es otro pasajero del mismo PNR (Asociar a la misma Venta).
    - Si existe y el número es igual pero fecha distinta -> Es una Re-emisión (Crear Versión 2).

### ¿Por qué hacer esto ahora?
Si limpiamos la base de datos hoy y cargas 100 boletos reales mañana, cuando quieras implementar esto tendrás que migrar datos complejos. **Mejor tener la estructura perfecta desde el día 1.**

---

## Próximos Pasos Recomendados

1.  **Refactor de Modelos (Versionado):** Ajustar `core/models/boletos.py`.
2.  **Ajuste del Parser:** Enseñar al bot a manejar duplicados en lugar de rechazarlos.
3.  **Script de Semillas y Limpieza:** Borrar todo y empezar con la "Super Estructura".
4.  **(Fase 2 - Futuro):** Celery y Tests.

¿Estás de acuerdo con aplicar el **Versionado Inteligente** antes de la limpieza?
