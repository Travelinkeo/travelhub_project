8# MANUAL DEL USUARIO — TravelHub ERP

**Versión:** 1.0 | **Mayo 2026**

---

## Índice

1. [Acceso al Sistema](#1-acceso-al-sistema)
2. [Dashboard Principal](#2-dashboard-principal)
3. [Importación de Boletos con IA](#3-importación-de-boletos-con-ia)
4. [Ventas y Reservas](#4-ventas-y-reservas)
5. [CRM — Clientes y Pasajeros](#5-crm--clientes-y-pasajeros)
6. [Cotizaciones](#6-cotizaciones)
7. [Hoteles y Tarifarios](#7-hoteles-y-tarifarios)
8. [Finanzas y Facturación](#8-finanzas-y-facturación)
9. [Contabilidad](#9-contabilidad)
10. [Marketing](#10-marketing)
11. [CMS — Contenido](#11-cms--contenido)
12. [Configuración de Agencia](#12-configuración-de-agencia)
13. [WhatsApp Business](#13-whatsapp-business)
14. [Panel de Administración (Admin)](#14-panel-de-administración-admin)
15. [Herramientas Avanzadas](#15-herramientas-avanzadas)

---

## 1. Acceso al Sistema

### URL de acceso
```
http://localhost:8000/
```

### Inicio de Sesión
1. Ingresa tu **nombre de usuario** y **contraseña**
2. Si olvidaste tu contraseña, usa el enlace mágico ingresando tu email
3. Al iniciar sesión, serás redirigido al Dashboard de tu agencia

### Roles de Usuario
| Rol | Permisos |
|-----|----------|
| **Admin** | Acceso total a la agencia: configuración, usuarios, ventas, reportes |
| **Gerente** | Ventas, clientes, cotizaciones, reportes (sin configuración) |
| **Vendedor** | Crear ventas, clientes, cotizaciones |
| **Contador** | Facturación, contabilidad, reportes financieros |
| **Operador** | Importar boletos, gestionar reservas |
| **Consulta** | Solo lectura de ventas y reportes |

---

## 2. Dashboard Principal

**URL:** `/dashboard/`

El dashboard muestra:

### Panel de Métricas
- **Ventas del mes**: Total de ventas y monto acumulado
- **Boletos procesados**: Hoy / Semana / Mes
- **Pendientes de pago**: Ventas con saldo por cobrar
- **Margen estimado**: Ganancia proyectada del mes

### Alertas
- Boletos con errores de parseo
- Pasaportes próximos a vencer
- Pagos pendientes > 7 días

### Acciones Rápidas
- **Subir Boleto**: Importa un PDF/TXT/EML para parseo automático
- **Nueva Venta**: Crea una venta manual
- **Nuevo Cliente**: Registra un cliente

---

## 3. Importación de Boletos con IA

### Cómo funciona
TravelHub usa Inteligencia Artificial (Google Gemini) para extraer automáticamente los datos de boletos aéreos desde archivos PDF, TXT o EML.

### Paso a Paso

**Opción A — Subir Archivo**
1. Ve a **Dashboard → Subir Boleto** o a `/erp/boletos-importar/`
2. Arrastra tu archivo (PDF, TXT, EML) a la zona de carga
3. El sistema detecta automáticamente el formato GDS (Sabre, KIU, Amadeus, Copa, Wingo, TK Connect)
4. En segundos, la IA extrae: PNR, pasajero, vuelos, tarifas, impuestos
5. Serás redirigido a la pantalla de **Revisión del Boleto**

**Opción B — Por Email (Automático)**
1. Configura tu correo de emisiones en Configuración de Agencia
2. Reenvía los boletos a ese correo
3. El sistema los procesa automáticamente cada 2 minutos

### Pantalla de Revisión
Después del parseo, verás:
- **Datos del pasajero**: Nombre, identificación (editable)
- **Itinerario**: Todos los segmentos de vuelo con fechas, horas, aerolíneas
- **Datos financieros**: Tarifa base, impuestos, total, comisión
- **Asignar cliente**: Selecciona un cliente existente o crea uno nuevo

### Acciones
| Botón | Función |
|-------|---------|
| **Aprobar y Guardar** | Crea la Venta con todos los datos extraídos |
| **Re-procesar** | Vuelve a ejecutar la IA si hay errores |
| **Desasociar Venta** | Desvincula el boleto de su venta actual |

### Búsqueda de Boletos
**URL:** `/erp/boletos-busqueda/`
- Busca por nombre de pasajero, PNR, origen, destino, o fecha
- Filtra por GDS (Sabre, KIU, Amadeus, etc.)
- Ve boletos pendientes, procesados, o con errores

### Reportes de Boletos
**URL:** `/erp/boletos-reportes/`
- Comisiones por aerolínea
- Volumen de boletos por mes
- Gráficos de tendencias

---

## 4. Ventas y Reservas

### Crear una Venta Manual
1. Ve a **Dashboard → Nueva Venta** o `/erp/ventas/nueva/`
2. Completa:
   - **Cliente**: Selecciona de la lista o crea nuevo
   - **Localizador**: Código de reserva (se auto-genera)
   - **Moneda**: USD, VES, EUR
   - **Items**: Añade servicios (boleto aéreo, hotel, traslado, etc.)
   - **Precio y costo**: Por cada item
3. **Guardar**

### Estados de una Venta
| Estado | Significado |
|--------|-------------|
| **Pendiente de Pago** | Creada, esperando pago del cliente |
| **Pagada Parcial** | Se recibió parte del pago |
| **Pagada Total** | Pago completo recibido |
| **Confirmada** | Reserva confirmada con proveedor |
| **En Proceso de Viaje** | El cliente está viajando |
| **Completada** | Viaje finalizado |

### Componentes de Venta
Cada venta puede incluir:
- **Boleto Aéreo**: Segmentos de vuelo con aerolínea, fechas, clase
- **Alojamiento**: Hotel, check-in/out, habitaciones
- **Traslado**: Aeropuerto-Hotel, tipo de vehículo
- **Actividad**: Tour, excursión, entrada
- **Alquiler de Auto**: Categoría, fechas, seguro
- **Crucero**: Naviera, barco, cabina, paquete de bebidas
- **Circuito**: Itinerario multi-día con actividades

### Registrar un Pago
1. Abre la venta → pestaña **Pagos**
2. Ingresa: monto, método de pago (Efectivo, Transferencia, Zelle, Binance), fecha
3. El sistema recalcula automáticamente el saldo pendiente

### Generar Voucher / Factura
- **Voucher PDF**: Para entregar al cliente con su itinerario
- **Factura**: Documento fiscal (Venezuela: IVA 16%, IGTF 3% si aplica)
- **Doble Facturación**: Para operaciones en divisas (USD + Bolívares)

---

## 5. CRM — Clientes y Pasajeros

### Clientes
**URL:** `/erp/clientes/`

- **Lista**: Todos los clientes de tu agencia
- **Crear**: Nombre, apellido, email, teléfono, documento de identidad
- **Ficha del cliente**: Historial de ventas, pagos, preferencias de viaje
- **Cliente frecuente**: Se marca automáticamente tras 5+ compras

### Pasajeros
**URL:** `/erp/pasajeros/`

- Diferente de "Cliente" — un pasajero es quien viaja (puede no ser el comprador)
- Datos: nombre, fecha de nacimiento, documento, nacionalidad, vencimiento

### Escaneo de Pasaportes con IA
1. Sube una foto del pasaporte
2. La IA (Gemini Vision) extrae: nombres, apellidos, número de pasaporte, nacionalidad, fechas
3. Se crea automáticamente el registro del pasajero

### Verificación Migratoria
- Al crear una venta con vuelos internacionales, el sistema verifica:
  - Requisitos de visa según nacionalidad y destino
  - Vigencia mínima del pasaporte (6 meses)
  - Vacunas requeridas
- Resultado: 🟢 Sin problemas / 🟡 Requiere atención / 🔴 Alerta

---

## 6. Cotizaciones

### Magic Quoter (Cotizador con IA)
**URL:** `/cotizaciones/magic/`

1. Pega el texto GDS (Sabre, Amadeus, KIU) de una cotización
2. La IA extrae: vuelos, tarifas, impuestos, fechas
3. Genera automáticamente:
   - Items de cotización con precios
   - Fee de agencia configurable
   - Imagen del destino

### Cotización Manual
1. Ve a **Cotizaciones → Nueva**
2. Selecciona cliente, destino, fechas
3. Añade items (vuelos, hoteles, actividades)
4. Agrega términos y condiciones
5. **Enviar** — se genera PDF profesional

### Ciclo de Vida
| Estado | Acción |
|--------|--------|
| **Borrador** | Editando |
| **Enviada** | Cliente la recibe |
| **Vista** | Cliente abrió el enlace |
| **Aceptada** | → Convertir a Venta |
| **Rechazada** | Archivada |
| **Vencida** | Pasó fecha límite |

---

## 7. Hoteles y Tarifarios

### Buscar Hoteles
**URL:** `/hoteles/`

1. Ingresa destino, fechas, huéspedes
2. El sistema busca en todos los tarifarios cargados
3. Resultados ordenados por precio (menor a mayor)
4. Cada resultado muestra:
   - Precio por noche
   - Comisión para la agencia
   - Descripción, amenities, fotos

### Cargar Tarifario
1. Ve al **Admin → Hoteles → Tarifarios Proveedor**
2. Sube el PDF del tarifario del proveedor
3. La IA extrae: hoteles, tipos de habitación, tarifas por temporada
4. Revisa y ajusta los datos extraídos

### Generar Contenido de Marketing
- **Generar Copy**: La IA crea textos para Instagram/Facebook con diferentes tonos
- **Generar Story**: Crea una imagen promocional del hotel

---

## 8. Finanzas y Facturación

### Facturación
**URL:** `/facturacion/`

- **Emitir Factura**: Desde una venta, genera factura fiscal
- **Factura Consolidada**: Agrupa múltiples ventas (formato SENIAT Venezuela)
- **Nota de Crédito/Débito**: Para ajustes y devoluciones

### Campos de Factura (Venezuela)
- Número de control
- Base imponible (USD)
- IVA 16% (alícuota general)
- IGTF 3% (si aplica — SPE)
- INATUR 1% (provisión trimestral)
- Equivalente en Bolívares (tasa BCV del día)

### Libro de Ventas
**URL:** `/api/libro-ventas/`
- Reporte fiscal mensual obligatorio
- Ventas propias vs ventas de terceros
- Total débito fiscal

### Conciliación de Proveedores
**URL:** `/finance/supplier-reconciliation/`
1. Sube el reporte del proveedor (PDF/Excel)
2. El sistema cruza con tus ventas por número de boleto/PNR
3. Detecta discrepancias, boletos huérfanos, posibles fraudes

### Gastos Operativos
- Registra gastos: alquiler, servicios, comisiones, papelería
- Se contabilizan automáticamente (Debe: Gasto / Haber: Caja/Banco)

---

## 9. Contabilidad

### Plan de Cuentas
Estructura contable pre-cargada para agencias de viajes (VEN-NIF):
- **Clase 1**: Activos (Caja, Bancos, Cuentas por Cobrar)
- **Clase 2**: Pasivos (Cuentas por Pagar, Impuestos)
- **Clase 4**: Ingresos (Venta Boletería, Comisiones)
- **Clase 5**: Gastos (Personal, Operativos, Administrativos, Financieros)

### Asientos Contables Automáticos
Cada operación genera su asiento:
| Operación | Débito | Crédito |
|-----------|--------|---------|
| Venta al contado | Caja/Banco | Ingresos + IVA |
| Venta a crédito | Cuentas por Cobrar | Ingresos + IVA |
| Cobro de venta | Caja/Banco | Cuentas por Cobrar |
| Gasto operativo | Gasto | Caja/Banco |
| Diferencial cambiario | Caja/Banco o Gasto | Ingreso o Caja/Banco |

### Reportes Contables
**URL:** `/reportes/`

| Reporte | Descripción |
|---------|-------------|
| **Libro Diario** | Todas las transacciones en orden cronológico |
| **Balance de Comprobación** | Sumas y saldos por cuenta |
| **Estado de Resultados** | Ingresos - Costos - Gastos = Utilidad |
| **Validación de Cuadre** | Detecta asientos descuadrados |

### Tasas BCV
- Se sincronizan automáticamente 2 veces al día
- Usadas para calcular equivalentes en Bolívares
- Histórico de tasas consultable

---

## 10. Marketing

### Centro de Marketing
**URL:** `/marketing/hub/`

- **Generar Flyer**: Crea imagen promocional de un destino/hotel
- **AI Copywriter**: Genera textos para redes sociales (tonos: profesional, aventurero, romántico)
- **Magic Newsletter**: Boletín de email en HTML con ofertas

### Campañas
- Crea campañas con fecha de inicio/fin
- Programa publicaciones en Instagram, Facebook, WhatsApp
- Seguimiento de resultados

---

## 11. CMS — Contenido

### Blog / Artículos
- Crea artículos con título, slug, contenido (Markdown)
- Categoriza por destino
- Genera con IA o escribe manualmente
- Optimiza SEO con meta título y descripción

### Guías de Destino
- Información turística: mejor época, visa, idioma, moneda
- Se muestran en el portal público

---

## 12. Configuración de Agencia

**URL:** `/agencia/configuracion/`

### Datos Generales
- Nombre comercial, RIF, IATA
- Teléfono, email, dirección
- Moneda principal, zona horaria

### Branding y PDFs
**URL:** `/settings/branding/`
- **Color primario**: Se aplica a todos los PDFs (boletos, vouchers, facturas)
- **Tema del sitio**: Obsidian Emerald, Neon Sunset, Midnight Gold, Nordic Snow, Cyber Fuchsia, Swiss Vintage
- **Plantilla de Boletos**: Diseño del PDF de boleto (6 variantes)
- **Plantilla de Vouchers**: Diseño del comprobante (5 variantes)
- **Plantilla de Facturas**: Diseño fiscal

### WhatsApp
**URL:** `/agencia/configuracion/` (pestaña WhatsApp)
- **Estado**: Conectado / Desconectado / Esperando escaneo
- **QR**: Escanea con WhatsApp para vincular
- La instancia se crea automáticamente por agencia

### Usuarios de la Agencia
**URL:** `/agencia/usuarios/`
- Invita nuevos usuarios (email + nombre + rol)
- Activa/desactiva usuarios
- Cambia roles

---

## 13. WhatsApp Business

### Configuración Inicial
1. Ve a Configuración de Agencia → pestaña **WhatsApp**
2. Si el QR no aparece como imagen, haz clic en "Abrir QR en Evolution"
3. Escanea el QR con WhatsApp en tu celular
4. La página se actualiza mostrando "CONECTADO"

### Funcionalidades
- **Notificaciones automáticas**: Pago recibido, boleto procesado, recordatorio de viaje
- **Envío de PDFs**: Boletos y vouchers por WhatsApp
- **Chatbot**: Responde consultas de clientes (ventas, estado de reserva, requisitos migratorios)

---

## 14. Panel de Administración (Admin)

**URL:** `/admin/`

El panel de administración usa el tema **Unfold** (moderno, TailwindCSS, modo oscuro/claro).

### Barra Lateral
Organizada en 13 secciones colapsables:
- **Operaciones**: Dashboard, subir boleto, buffer de revisión
- **Ventas y Reservas**: Todos los modelos de ventas y componentes
- **Hoteles y Tarifarios**: Gestión de tarifarios y habitaciones
- **CRM**: Clientes, pasajeros, oportunidades
- **Cotizaciones**: Cotizaciones e items
- **Finanzas**: Facturas, gastos, conciliaciones
- **Contabilidad**: Plan de cuentas, asientos, tasas BCV
- **Marketing**: Campañas, activos, configuración
- **CMS**: Artículos, guías, posts
- **Configuración Global**: Agencias, catálogos, feature flags
- **SuperAdmin**: God Mode, GDS Analyzer

### Acciones en Admin
- **Añadir**: Botón "Añadir" en la esquina superior derecha de cada lista
- **Editar**: Click en cualquier registro
- **Eliminar**: Selecciona registros → Acción "Eliminar"
- **Buscar**: Barra de búsqueda superior
- **Filtrar**: Panel de filtros a la derecha

### Tema Claro/Oscuro
El admin sigue la preferencia de tu sistema operativo. Para cambiar:
- Click en el icono ☀️/🌙 en la esquina superior derecha
- Selecciona: Claro, Oscuro, o Automático

---

## 15. Herramientas Avanzadas

### Traductor de Itinerarios GDS
**URL:** `/tools/traductor/`
1. Pega texto crudo de GDS (Sabre, Amadeus, KIU)
2. El sistema traduce a un itinerario legible en HTML
3. Calcula automáticamente el precio con fees configurados
4. Copia el resultado o genera una cotización

### GDS Analyzer (IA)
**URL:** `/intelligence/gds-analyzer/`
1. Pega la terminal completa de GDS
2. La IA analiza y extrae todos los boletos
3. Inyecta directamente al ERP como Ventas

### Búsqueda Global (Ctrl+K)
- Presiona **Ctrl+K** en cualquier página
- Busca clientes, ventas, boletos por nombre, PNR, o ID
- Navegación instantánea

### Portal del Pasajero
Cada venta genera un enlace público:
- **URL:** `/v/<uuid>/`
- El cliente puede ver su itinerario, vuelos, vouchers
- Descargar PDFs
- La agencia puede personalizar con su logo y colores

### Vouchers PDF
Por tipo de servicio, con 5 variantes de diseño:
- Voucher Unificado (todos los servicios)
- Voucher de Hotel
- Voucher de Traslado
- Voucher de Actividad
- Voucher de Alquiler de Auto
- Voucher de Seguro

---

## Atajos y Consejos

| Atajo / Tip | Descripción |
|-------------|-------------|
| **Ctrl+K** | Búsqueda global en todo el sistema |
| **Arrastrar archivo** | Importa boletos soltando PDF/TXT en la zona de carga |
| **Auto-guardado** | Los formularios guardan al presionar Enter |
| **HTMX polling** | Las notificaciones y el QR de WhatsApp se actualizan solos |
| **Modo oscuro** | Disponible en Admin (☀️/🌙) y en el frontend (según tema de agencia) |

---

## Solución de Problemas

### Un boleto no se procesa
1. Verifica que el archivo sea PDF, TXT o EML
2. Revisa en **Boletos → Buscar** si tiene error
3. Usa **Re-procesar** en la pantalla de revisión
4. Si persiste, ingresa los datos manualmente en **Boletos → Manual**

### No aparece el QR de WhatsApp
1. Asegúrate de que Evolution API esté corriendo
2. Recarga la página (F5)
3. Ve a Configuración de Agencia → WhatsApp

### No puedo ver todas las opciones del Admin
- Verifica que tu usuario tenga el rol adecuado (Admin)
- Si eres superadmin, ve a `/god-mode/` e impersona tu agencia

---

> **TravelHub ERP** — Automatización inteligente para agencias de viajes.
