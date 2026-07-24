# 📚 Manual de Operación: Lector de Reportes de Ventas de Proveedores (Multi-Tenant)

## 📌 1. Descripción General

El **Lector de Reportes de Ventas de Proveedores** es un módulo automatizado de TravelHub diseñado para procesar los estados de cuenta y reportes de ventas semanales o mensuales enviados por consolidadores y proveedores turísticos (como **CTG** y **MY DESTINY**).

El módulo funciona bajo una **arquitectura Multi-Tenant**, lo que garantiza que cada agencia (por ejemplo, *Travelinkeo*) tenga aislamiento total sobre sus datos de proveedores, saldos y comisiones.

---

## 🏢 2. Proveedores Soportados

Actualmente, el sistema cuenta con reglas de extracción específicas para:

| Proveedor | Formato de Archivo | Identificadores de Extracción | Datos Extraídos |
| :--- | :--- | :--- | :--- |
| **CTG** *(Grupo Soporte Global Inc)* | PDF (*Client Statement*) | `Client No: 7842`<br>`ID: J402496982` | Boletos, Facturas, Pasajeros, Aerolíneas (Laser, Jet Link, Estelar, Avior, Rutaca, etc.), Ruta, Fare, Service Fee y Saldos. |
| **MY DESTINY** | PDF (*Ventas de Agencia*) | `Código Agencia: PTYS3650` | Boletos, Pasajeros, Aerolíneas, Fecha emisión, Fare, TAX, Subtotal, Fee, % Comisión, Monto Comisión y Saldos. |

> 💡 **Nota:** La arquitectura usa el patrón de diseño **Strategy**, permitiendo agregar nuevos proveedores de forma transparente sin alterar la base del sistema.

---

## ⚡ 3. Formas de Importación

El sistema ofrece dos vías para procesar reportes:

### 3.1. Modo 1: Procesamiento Automático por Correo Electrónico (Recomendado)

1. **Funcionamiento:**
   * El servicio de fondo `EmailMonitorService` (ejecutado por **Celery Beat** cada 2 minutos) revisa la bandeja de entrada configurada para la agencia (ejemplo: `travelinkeo@gmail.com`).
   * Al recibir un correo no leído con un archivo PDF adjunto enviado por un proveedor:
     1. Intercepta el archivo PDF.
     2. Identifica automáticamente al proveedor (*CTG* o *MY DESTINY*).
     3. Parsea todas las filas de boletos, comisiones y saldos.
     4. Registra la información en la base de datos vinculada a la agencia correspondiente.

2. **Acción Requerida por el Usuario:** **Ninguna.** El proceso es 100% transparente y automatizado.

---

### 3.2. Modo 2: Importación Manual desde Archivos Locales (Vía Terminal)

Si recibes reportes descargados manualmente en tu equipo o deseas importar un histórico de reportes pasados:

1. **Ubicación de Archivos:**
   Coloca los archivos PDF (o archivos `.eml` de correos guardados) dentro de la carpeta del proyecto:
   `c:\Users\ARMANDO\travelhub_project\media\reportes_proveedores`

2. **Comando de Ejecución:**
   Abre una consola/PowerShell en el directorio del proyecto y ejecuta:

   ```powershell
   docker-compose exec web python manage.py importar_reportes_proveedores --agencia=Travelinkeo --dir="/app/media/reportes_proveedores"
   ```

3. **Parámetros del Comando:**
   * `--agencia`: Nombre exacto o ID de la agencia a la cual se le asignarán los registros (ej. `Travelinkeo`).
   * `--dir`: Ruta del directorio que contiene los archivos PDF/EML (dentro del contenedor `/app/media/...`).

---

## 📊 4. Estructura de Datos Almacenados

El módulo registra los datos en dos modelos de base de datos multi-tenant:

### 4.1. Encabezado del Reporte (`ReporteVentaProveedor`)
* **Agencia:** Instancia de la agencia propietaria.
* **Proveedor:** Nombre comercial (`CTG`, `MY DESTINY`).
* **Código de Agencia en Proveedor:** Código asignado por el proveedor (ej. `7842` o `PTYS3650`).
* **Rango del Reporte:** `fecha_reporte_desde` y `fecha_reporte_hasta`.
* **Saldos:** `saldo_anterior`, `monto_total_ventas` y `saldo_final`.
* **Estado:** `PROCESADO`, `CONCILIADO`, `DIFERENCIA`, `ERROR`.

### 4.2. Detalle de Boletos (`ItemReporteVentaProveedor`)
* **Pasajero:** Nombre y apellido del pasajero.
* **Número de Boleto / Documento:** N° de ticket o ID de Service Fee.
* **Aerolínea:** Nombre de la línea aérea.
* **Detalle Financiero:**
  * Tarifa Base (`monto_fare`)
  * Impuestos (`monto_tax`)
  * Subtotal (`monto_subtotal`)
  * Service Fee (`monto_fee`)
  * % Comisión (`porcentaje_comision`)
  * Monto Comisión (`monto_comision`)
  * Neto a Pagar al Proveedor (`monto_neto_pagar`)

---

## 🛠️ 5. Guía Técnica: Cómo Agregar un Nuevo Proveedor

Para agregar un nuevo proveedor (ejemplo: *Servivuelo*, *Amadeus Direct*, etc.):

1. **Crear el Parser Específico:**
   Crea un nuevo archivo en `apps/contabilidad/supplier_parsers/nuevo_proveedor_parser.py`:

   ```python
   from .base_parser import BaseSupplierReportParser

   class NuevoProveedorReportParser(BaseSupplierReportParser):
       def parse(self) -> dict:
           # Lógica de extracción usando pypdf o regex
           return {
               "proveedor_nombre": "NUEVO PROVEEDOR",
               "codigo_agencia_proveedor": "...",
               "saldo_anterior": Decimal("0.00"),
               "monto_total_ventas": Decimal("0.00"),
               "saldo_final": Decimal("0.00"),
               "items": [...]
           }
   ```

2. **Registrarlo en la Fábrica (`factory.py`):**
   Edita `apps/contabilidad/supplier_parsers/factory.py` y agrega la condición de auto-detección:

   ```python
   if "nuevoproveedor" in sender_clean or "nuevo proveedor" in first_page_text.lower():
       return NuevoProveedorReportParser(pdf_bytes, filename, subject)
   ```

---

## 🔍 6. Diagnóstico y Preguntas Frecuentes

* **¿Qué pasa si importo dos veces el mismo reporte PDF?**
  El servicio valida duplicados para evitar registros repetidos.
* **¿Qué sucede si un PDF de reporte no pertenece a un proveedor registrado?**
  El sistema registrará una advertencia en el log (`No se encontró parser adecuado`) y omitirá la ingesta sin detener el flujo de otros correos.
* **¿Dónde se visualizan los reportes procesados?**
  Se pueden consultar desde el panel de administración de Django (`/admin/contabilidad/reporteventaproveedor/`) o a través de las pantallas contables del ERP.
