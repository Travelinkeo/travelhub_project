# 📄 Sistema de Generación de Vouchers (Voucher System)

## Descripción General
El sistema de vouchers de TravelHub ha sido refactorizado (Mayo 2026) para centralizar la lógica de generación de documentos PDF en un servicio especializado, separándolo de la lógica financiera de facturación.

## Arquitectura
El sistema se basa en tres componentes principales:

1.  **`core/services/voucher_service.py`**: El motor de negocio. Contiene la lógica para extraer datos de los modelos de reserva y prepararlos para las plantillas.
2.  **`core/services/pdf_renderer.py`**: El adaptador de infraestructura. Se comunica con el microservicio **Gotenberg** para transformar HTML en PDF de alta fidelidad.
3.  **Plantillas Dinámicas (`core/templates/vouchers/`)**: Un set de plantillas HTML/CSS que soportan múltiples variaciones visuales.

## Tipos de Vouchers Soportados
*   **Voucher Unificado (Venta)**: Resume todo el itinerario de una venta (Vuelos, Hoteles, Traslados, etc.) en un solo documento.
*   **Alojamiento**: Voucher específico para hoteles y estadías.
*   **Alquiler de Autos**: Detalles de la reserva de vehículos.
*   **Traslados**: Información de recogida y destino para transfers.
*   **Actividades**: Vouchers para tours y excursiones.
*   **Servicios Adicionales**: Genérico para seguros, asistencias u otros cargos.

## Variaciones de Diseño (Variations)
Las agencias pueden configurar su estilo visual preferido en su perfil (`Agencia.plantilla_vouchers`). Los estilos disponibles son:
- **v1_golden_classic**: Diseño tradicional y elegante.
- **v2_editorial**: Estilo revista moderna.
- **v3_executive**: Limpio y minimalista.
- **v4_timeline**: Enfocado en la cronología del viaje.
- **v5_modern**: Diseño contemporáneo con elementos visuales fuertes.

## Integración con Django Admin
Cada servicio en `apps.bookings` tiene integrada una acción de administrador para generar el PDF correspondiente:
- Seleccionar el registro.
- Elegir la acción `Generar Voucher ... (PDF)`.
- El sistema descarga automáticamente el archivo.

## Consideraciones Técnicas
- **Logos Adaptativos**: El sistema detecta el color primario de la agencia y selecciona automáticamente la versión clara u oscura del logo para asegurar el contraste.
- **Localización**: Las fechas se formatean automáticamente según el locale de la agencia (por defecto `es_ES`).
- **Extensibilidad**: Para añadir nuevos tipos de vouchers, simplemente agregue la función correspondiente en `voucher_service.py` y registre la acción en el `admin.py` respectivo.
