# TravelHub Project

**Sistema de Gestión Integral para Agencias de Viajes (SaaS)**

TravelHub es una plataforma moderna diseñada para automatizar la operación de agencias de viajes, con foco en la normativa fiscal venezolana (VEN-NIF) y la automatización de boletos aéreos.

---

## 📚 Documentación Maestra (Bus Factor 1)

Toda la información técnica, operativa y de negocio se encuentra centralizada en la carpeta `docs/`.

> **⚠️ REGLA DE ORO:**
> Ningún cambio de código se considera "Terminado" hasta que la documentación correspondiente en `docs/` haya sido actualizada.
> *   ¿Cambiaste un Modelo? -> Actualiza `DATA_DICTIONARY.md`.
> *   ¿Cambiaste la Arquitectura? -> Actualiza `ARCHITECTURE.md`.

### Índice de Manuales
*   [🏛️ Arquitectura del Sistema](docs/ARCHITECTURE.md): Visión general, stack tecnológico y estructura de módulos.
*   [📖 Diccionario de Datos y Reglas](docs/DATA_DICTIONARY.md): Modelos, Plan de Cuentas y Lógica de Automatización.
*   [💻 Manual de Desarrollo](docs/DEVELOPMENT.md): Setup, instalación y guía de estilo.
*   [🚀 Manual de Operaciones](docs/OPERATIONS.md): Despliegue en Coolify y mantenimiento.

---

## Estado del Proyecto
*   **Versión:** En desarrollo activo (Refactorización & Automatización).
*   **Stack:** Django 5, TailwindCSS, HTMX, PostgreSQL, Celery.

## Características Clave
*   **Parser de Boletos:** Extracción automática de datos desde PDFs (KIU, Sabre).
*   **Contabilidad Invisible:** Generación automática de asientos contables y cálculo de impuestos (IVA/IGTF).
*   **UI Premium:** Interfaz Glassmorphism con modo oscuro.
