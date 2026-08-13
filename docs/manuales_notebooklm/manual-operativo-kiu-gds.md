# MANUAL OPERATIVO MAESTRO: KIU GDS Y GESTIÓN DE AGENCIAS DE VIAJES (EDICIÓN ACTUALIZADA 2026)

Este documento constituye el **Documento Maestro de Procesos, Comandos y Estructuras Administrativas** para el sistema **KIU GDS** y la gestión integral de agencias de viajes. Está diseñado para consolidar toda la base de conocimiento operativa e incorporar las últimas actualizaciones de la plataforma (versión 2025/2026), sirviendo de guía exhaustiva para Counter Nacional, Internacional, Turismo y personal administrativo.

---

## ÍNDICE DE CONTENIDOS
1. [Acceso, Control del Sistema y Personalización](#1-acceso-control-del-sistema-y-personalizacion)
2. [Flujo de Trabajo para la Creación y Modificación de Reservas (PNR)](#2-flujo-de-trabajo-para-la-creacion-y-modificacion-de-reservas-pnr)
3. [Servicios Especiales, Información Adicional y Seguridad (SSR, OSI, Remarks, Secure Flight)](#3-servicios-especiales-informacion-adicional-y-seguridad-ssr-osi-remarks-secure-flight)
4. [Estructura y Gestión de Tarifas y Cotización Automática](#4-estructura-y-gestion-de-tarifas-y-cotizacion-automatica)
5. [Proceso Completo de Emisión de Boletos (Ticketing) y Reportes de Ventas](#5-proceso-completo-de-emision-de-boletos-ticketing-y-reportes-de-ventas)
6. [Post-Venta, Cambios, Revalidaciones, Canjes (Exchange) y Colas](#6-post-venta-cambios-revalidaciones-canjes-exchange-y-colas)
7. [Administración de Dispositivos y Control Center](#7-administracion-de-dispositivos-y-control-center)
8. [Novedades Tecnológicas y Actualizaciones de Plataforma (2025/2026)](#8-novedades-tecnologicas-y-actualizaciones-de-plataforma-20252026)
9. [Gestión de Agencias de Viajes y Estructura Organizativa (Ecuador/Cuenca)](#9-gestion-de-agencias-de-viajes-y-estructura-organizativa-ecuadorcuenca)
10. [Requisitos de Visas para Viajes Emisivos y Países de Destino](#10-requisitos-de-visas-para-viajes-emisivos-y-paises-de-destino)

---

## 1. ACCESO, CONTROL DEL SISTEMA Y PERSONALIZACIÓN

El sistema **KIU GDS** es una plataforma multihosting avanzada que permite a agencias IATA (conectadas al circuito BSP/ARC) y NO IATA (mediante cuentas corrientes electrónicas) gestionar todas sus operaciones de forma fluida. El sistema cuenta con entornos crípticos (**KIU Command**) y gráficos avanzados (**KIU Click** y **Easy-KIU**).

### 1.1 Ingreso (Sign In / Log In) y Salida (Sign Out)
*   **Sign In (Firma de Agente):** Es la clave identificadora única del agente (de 4 a 6 dígitos). El comando críptico es:
    *   *Comando:* `SI` + [Número de Agente] (Ej: `SI2001`)
    *   *Salida Esperada:* El sistema despliega una máscara solicitando la contraseña actual (campo *Current Password*, de 4 a 8 caracteres alfanuméricos) y, al pulsar ENTER, se ingresa con el nivel de atribución (*Duty*) predeterminado.
*   **Cambio de Contraseña (Password):** Se realiza durante el proceso de firma:
    *   *Comando:* `SI2001` -> En la máscara, ingresar la clave actual en *Current Password*, usar la tecla TAB para posicionarse en *New Password*, escribir la nueva contraseña y presionar ENTER.
    *   *Salida Esperada:* Mensaje confirmando la actualización de la clave.
*   **Sign Out (Salida de Áreas):**
    *   *Comando:* `SO` (Cierra la sesión del área actual) o `SO*` (Cierra la sesión de todas las áreas de trabajo activas).
    *   *Salida Esperada:* Desconexión del usuario. Si existe un PNR activo sin guardar o ignorar, el sistema devolverá el error: `PNR PRESENT - FINISH OR IGNORE`.

### 1.2 Configuración de Áreas de Trabajo y Pantallas
KIU ofrece **3 áreas crípticas de trabajo** independientes que se ejecutan simultáneamente, y hasta **10 ventanas gráficas** en el Asistente de Reservas y Ventas.
*   **Navegación entre áreas crípticas:**
    *   *Comando:* `Ø` + [Número de área] (El carácter `Ø` representa el comando *Change* y se ejecuta pulsando la tecla `TAB` o `[`). Por ejemplo, `Ø2` cambia al Área 2. También se puede utilizar `CTRL + TAB`.
*   **Consulta del estado de las áreas:**
    *   *Comando:* `*S`
    *   *Salida Esperada:* Muestra un reporte con los ID de las terminales, la oficina, el sign del agente, si se encuentra en colas, y el estado del PNR activo en cada ventana (`DISPLAY` si está desplegado, `CREATE` en creación o `MODIFY` si se ha modificado). Un asterisco (`*`) indica el área actualmente seleccionada.

### 1.3 Personalización y Teclas del Sistema
*   **Tecla CHANGE:** Representada por el símbolo `Ø`. Se utiliza para modificar campos de un PNR. Puede ser configurada a través de *Tools -> Options -> Application -> Key for Change*.
*   **Tecla END OF ITEM (Fin de Elemento):** Representada por el símbolo `¶`. Se ejecuta con `SHIFT + ENTER` y sirve para realizar ingresos múltiples de datos (multientrada) en una sola transacción.
*   **Modo TEST (Entorno de Práctica):** Permite trabajar sobre una base de datos emulada sin afectar el inventario o la facturación real.
    *   *Ingreso:* `øøTEST` (o `øøTSTS` / `øøTS`)
    *   *Salida:* `øøEND` (o `øøRES` / `øøLIVE`)
    *   *Verificar estado:* `øø` (Muestra en qué modo se encuentra la terminal).
*   **Limpiar pantalla:** Se ejecuta con el comando `CLS` o el atajo de teclado `CTRL + BACKSPACE`.
*   **KIU Sense:** Es un asistente críptico-gráfico. Al habilitarse, los colores del PNR cambian en pantalla. Al hacer clic derecho sobre cualquier elemento del PNR, se abre un menú contextual interactivo para modificar, agregar o eliminar campos sin necesidad de memorizar formatos crípticos.

---

## 2. FLUJO DE TRABAJO PARA LA CREACIÓN Y MODIFICACIÓN DE RESERVAS (PNR)

El **PNR (Passenger Name Record)** es el expediente electrónico del pasajero. Para que un PNR pueda ser guardado e incorporado al inventario, requiere de **5 elementos obligatorios** (Nombres, Itinerario, Contacto, Tiempo Límite y Recibido).

### 2.1 Disponibilidad de Vuelos (Paso 1)
*   **Búsqueda Neutral de Disponibilidad (AN):**
    *   *Comando:* `1` + [Fecha] + [Ruta] (Ej: `120MARCCSSDQ` o `AN20MARCCSSDQ`)
    *   *Salida Esperada:* Lista con un máximo de 6 vuelos ordenados de forma cronológica ascendente por hora de salida. Indica la aerolínea, número de vuelo, clases de servicio, cantidad de asientos disponibles (del 1 al 8, `9` para 9 o más, `0` para lista de espera abierta, `R` a requerir, `C` cerrado), aeropuertos, horas de salida/llegada, escalas, equipo (avión) y días de operación (donde 1=Lunes, 7=Domingo).
    *   *Ver más vuelos:* `1*` (Trae los siguientes vuelos disponibles).
    *   *Disponibilidad de ruta inversa:* `1R` (Ruta inversa para el mismo día) o `1R20JAN` (Para una fecha específica).
    *   *Modificar fecha sobre búsqueda:* `1+2` (Dos días más tarde), `1-3` (Tres días antes).

### 2.2 Venta / Toma de Cupos (Paso 2)
*   **Venta desde Disponibilidad:**
    *   *Comando:* `0` + [Cantidad Pasajeros] + [Clase de servicio] + [Línea del vuelo] (Ej: `01Y3` para tomar 1 cupo en clase Y de la línea 3).
    *   *Salida Esperada:* El segmento se incorpora temporalmente al PNR en estado de venta confirmada `SS`.
*   **Venta Directa (Venta con datos conocidos):**
    *   *Comando:* `0` + [Aerolínea] + [Vuelo] + [Clase] + [Fecha] + [Ruta] + `NN` + [Cantidad] (Ej: `0XX4520Y20JUNAEPCORNN1`).
*   **Segmentos en Conexión:**
    *   Si los vuelos aparecen conectados en la disponibilidad (línea del segmento con indicador `->`), se puede vender en la misma clase para ambos vuelos mediante: `02P1` (donde P es la clase común). Si son clases diferentes para cada tramo, se utiliza: `02PS1` (P para el primer tramo, S para el segundo).

### 2.3 Ingreso de Nombres de Pasajeros y Documentos (Paso 3)
El formato básico del campo de nombre es `-APELLIDO/NOMBRE`. El sistema rechaza duplicados exactos (`INVALID - CHECK PAX DUPE`).
*   **Pasajero Adulto:**
    *   *Comando:* `-PEREZ/JOSE MR` o `NM1PEREZ/JOSE MR`
*   **Documento de Identidad (FOID) en el Nombre:** Es fundamental asociar el documento al nombre del pasajero para la emisión:
    *   *Comando:* `-APELLIDO/NOMBRE` + `.` + [Tipo de FOID] + [Número]
    *   *Tipos de FOID autorizados:* `PP` (Pasaporte), `NI` (ID Nacional/DNI/Cédula), `ID` (ID Local), `CC` (Tarjeta de crédito), `DL` (Licencia de conducir).
    *   *Ejemplo Pasaporte:* `-PEREZ/JOSE MR.PP12345678`
    *   *Ejemplo Cédula:* `-PEREZ/JOSE MR.NI171189706`
*   **Pasajero Menor (CHILD - de 2 a 11 años):**
    *   *Comando:* `-PEREZ/LUIS CHD` (Debe existir un espacio antes de la sigla `CHD`).
*   **Pasajero Infante (INFANT - de 0 a 23 meses):** No ocupa asiento en la cabina y debe ser ingresado asociado a un pasajero adulto:
    *   *Comando:* `-I/APELLIDO/NOMBRE.NI1234567*P1` (La instrucción `*P1` lo asocia al pasajero adulto ubicado en la línea 1 del PNR). El sistema exige que el pasajero que precede a un infante sea un adulto (`PREVIOUS PSGR MUST BE ADT`).
*   **Ingreso de la Fecha de Nacimiento (DOB):**
    *   *Comando:* `-GOMEZ/DANIELA.DNI25820362/19APR74` (Formato de fecha DDMMMYY).

### 2.4 Campo de Contacto (Paso 4)
Almacena teléfonos, correos y direcciones de la agencia y de los pasajeros.
*   **Ingreso de Teléfono:**
    *   *Comando:* `9` + [Ciudad] + [Número] + [Texto descriptivo] (Ej: `9CCS-0414-1234455-CEL PAX`).
    *   *Ubicación descriptiva:* Se puede agregar un guión y códigos de ubicación (`A` para Agencia, `H` para Hogar, `C` para celular, `M` para móvil). Ejemplo: `9M-04127702125`.
*   **Ingreso de Correo Electrónico (E-Mail):**
    *   *Comando:* `9E-` + [Correo] (Ej: `9E-jperez@gmail.com`). Esto generará un enlace directo de tipo `MAILTO:` en el PNR activo.

### 2.5 Campo de Tiempo Límite de Emisión (Paso 5)
Establece la fecha y hora máximas en que la reserva debe emitirse antes de ser cancelada por el inventario de la aerolínea.
*   **Cancelación Automática (Robot TX):**
    *   *Comando:* `8X` + [Hora/Fecha] (Ej: `8X2000/30SEP` o `8+24` para dar un plazo de 24 horas desde la creación de la reserva).
    *   *Salida Esperada:* Campo `TKT/TIME LIMIT` registrado como `TKT/TX HDQ 1800/10APR`.
*   **Cancelación Manual (Informativa):**
    *   *Comando:* `8` + [Hora/Fecha] (Ej: `81800/30SEP` o `TKTL`).

### 2.6 Campo Recibido (Paso 6) y Cierre de Reserva (Paso 7)
*   **Recibido (Firma de solicitud):**
    *   *Comando:* `6` + [Nombre de quien solicita] (Ej: `6JUAN` o `RFJUAN`). Si es el pasajero directo, se puede ingresar `62` (asociado al pasajero 2) o simplemente `6` (por defecto asume `PAX`).
*   **Cerrar y Obtener Localizador:**
    *   *Comando:* `E` (Cierra la pantalla y guarda) o `ER` (Guarda y redespliega el PNR con el localizador asignado, denominado *Record Locator* o *Récord*).
*   **Ignorar cambios:** `I` (Deshace los cambios no grabados y limpia la pantalla) o `IR` (Ignora los cambios y redespliega la reserva en su estado previo).

### 2.7 Modificaciones en el PNR Creado
*   **Discontinuidad de ruta (ARNK - Arrival Unknown):** Si hay una diferencia entre el destino del tramo anterior y el origen del siguiente, el sistema incorpora de manera automática la leyenda `*** ARNK ***`.
*   **Cancelar Itinerario:** `XI` (Cancela todos los segmentos de vuelo) o `X1` (Cancela únicamente el segmento 1).
*   **Modificar Nombre/Documento:** Solo se permite antes de grabar el PNR. Una vez asignado el localizador, cualquier cambio de nombre requiere autorización de la aerolínea.
    *   *Modificar apellido:* `-1øPRADO` (Usa la tecla Change `ø` para cambiar el apellido del pax 1 a Prado).
    *   *Modificar nombre:* `-1ø/GUILLE`.
    *   *Eliminar pasaporte:* `-1ø.`.
*   **Mover o Dividir Pasajeros (Split):** Permite separar pasajeros de una misma reserva para crear un nuevo localizador.
    *   *Comando:* `D2,6` (Divide a los pasajeros 2 y 6). Al dar fin de transacción (`E`), el sistema genera el nuevo localizador y registra de forma permanente en ambos PNRs un *Remark de División* inviolable (`»» SPLIT BY [Agente]`).
*   **Asociación de PNRs (ADN):** Despliega el árbol genealógico de las subdivisiones que ha tenido un PNR.
    *   *Comando:* `ADN` (Muestra la jerarquía de localizadores asociados con sus respectivos nombres).
*   **Cambio de Clase Directo (SB):** Modifica la clase de reserva sin borrar la estructura del PNR.
    *   *Comando:* `SB1V2` (Cambia a clase V para 1 pasajero en el segmento 2).
*   **Eliminar Remarks:** `54[` (Borra el comentario ubicado en la línea 4 de Remarks).

---

## 3. SERVICIOS ESPECIALES, INFORMACIÓN ADICIONAL Y SEGURIDAD (SSR, OSI, SECURE FLIGHT)

KIU GDS divide los elementos suplementarios en **SSR (Special Service Request)** que requieren confirmación y acción por parte de la aerolínea, y **OSI (Other Service Information)** que son mensajes meramente informativos.

### 3.1 Servicios Especiales (SSR)
El comando principal de ingreso es `4` o `SR`.
*   **Formatos de Solicitud de SSR:**
    *   *Comida Vegetariana:* `4VGML` (Aplica a todos los pasajeros y segmentos).
    *   *Segmento Específico:* `4VGML/S2` (Aplica en el segmento de vuelo 2).
    *   *Pasajero Específico:* `4VGML/P2` (Asociado al pasajero 2 en todos los tramos).
    *   *Pasajero y Segmento:* `4VGML/S1/P2`.
*   **Servicios Comunes:**
    *   `4WCHR/P1` (Silla de ruedas para rampa, asociado al pax 1).
    *   `4PETC/CANICHE_5KG/P2` (Mascota en cabina). El peso especificado debe incluir el contenedor.
    *   `4AVIH/PASTOR_15KG/P1` (Mascota en bodega).
    *   `4UMNR/UM10` (Menor no acompañado de 10 años).
*   **Estados del SSR:**
    *   `NN` (Solicitado en pantalla). Al guardar la reserva, cambia a `PN` (Pendiente).
    *   `KK` (Acción de confirmación recibida por la aerolínea).
    *   `HK` (Confirmado por el agente). El operador cambia de KK a HK con `41.HK` (línea 1 del SSR).
    *   `UC` (Rechazado/No disponible). Las agencias de viajes no pueden forzar estados KK o UC.
*   **Visualizar la tabla general de códigos del sistema:**
    *   `JJSSR/KIU` (Muestra códigos estándar y configurables).
    *   `JJSSR/KIU/CTMEAL` (Filtra la lista de comidas especiales).
    *   *Redespliegue único de SSR en PNR:* `*O` (Muestra solo las líneas de SSR activos).

### 3.2 Seguridad y Secure Flight (APIS - SSR DOCS)
Para rutas internacionales, es estrictamente obligatorio registrar la información del documento de viaje (Secure Flight) antes de realizar la emisión del boleto.
*   **Formato Universal SSR DOCS:**
    `SRDOCS [Aerolínea] /P/ [Nac. Pax] / [Pasaporte] / [País Emisión] / [F. Nacimiento] / [Sexo] / [F. Vencimiento Pasaporte] / [Apellido] / [Nombre] /P [Línea Pax]`
    *   *Ejemplo:* `SRDOCSQL/P/VEN/123456789/VEN/01DEC79/F/24MAR29/LOPEZ/MARIA/P1`
*   **Formatos para Aerolíneas Específicas:**
    *   **Aruba Airlines:** `SRDOCS AG HK1/P/VE/123456789/VE/11OCT11/M/11OCT29/GARCIA/BRANDON/P1`
    *   **Laser:** `SRDOCS QL KH1 P/VE/N.PP/VE/F.NACI/SEXO/F.VENC.PP/APELLIDO/NOMBRE/S1/P1` (S1=Segmento del vuelo, P1=Línea del pasajero).
    *   **Venezolana:** `SRDOCS AW HK1 P/VE/N.PP/VE/FECH.NAC./SEXO/F.VENC.PP/APELLIDO/NOMBRE/P1`
*   **Información de Visado (SRDOCO):** Requerido obligatoriamente para vuelos hacia o a través de EE. UU. (Fly the World, Avior, Laser).
    *   *Formato con Visa:* `SRDOCO [Aerolínea] / [Lugar Nacimiento] /V/ [Nro Visa] / [Lugar Emisión] / [F. Emisión] /US/P [Pax]`
        *   *Ejemplo:* `SRDOCOWL/VE/V/8532/VE/07DEC13/US/P1`
    *   *Formato con ESTA (Visado electrónico):* `SRDOCOWL/VE/K/8532/ES/07DEC13/US/P1` (Se usa la letra `K`).
    *   *Residentes Americanos:* `SRDOCOWL/R/[Nro Pasaporte Americano]/DOCO`
*   **Dirección de Destino y Residencia (SRDOCA):** Obligatorio para Laser y Avior en rutas internacionales.
    *   *DOCA de Residencia:* `SRDOCAQL/R/VE/AV PPAL CASTELLANA/CARACAS/VE/1080/P1` (Indicador `R`).
    *   *DOCA de Destino:* `SRDOCAQL/D/PA/VIA BRASIL CL 50/PANAMA/PA/5001/P1` (Indicador `D`).

### 3.3 Mensajes OSI y Remarks
*   **OSI (Other Service Information):** Mensajes que se transmiten directamente al sistema de la aerolínea sin requerir confirmación de espacio.
    *   *Comando:* `OS` + [Código Aerolínea] + [Texto] (Ej: `OS YY PASAJERO VIP` para enviar el aviso a todas las aerolíneas del itinerario).
*   **Remarks (Remarks generales - Campo 5):** Comentarios locales para control de la agencia de viajes. No generan mensajes a la aerolínea.
    *   *Comando:* `5` + [Texto] (Ej: `5H ITA 1415`).

---

## 4. ESTRUCTURA Y GESTIÓN DE TARIFAS Y COTIZACIÓN AUTOMÁTICA

### 4.1 Consulta de Tarifas (FQD / FQT)
Permite verificar las tarifas vigentes para un par de ciudades antes de realizar una reserva.
*   **Consulta por aerolínea específica:**
    *   *Comando:* `FQD` + [Ruta] + `/A` + [Aerolínea] (Ej: `FQDAEPROS/A8R`)
    *   *Salida Esperada:* Tabla de tarifas listadas por líneas, indicando la base tarifaria (*Fare Basis*), valor en One Way (OW) o Round Trip (RT), clase de reserva, penalidades, restricciones de compra anticipada (AP), estadías mínimas y máximas.
*   **Consulta detallada con tasas e impuestos incluidos (FQT):**
    *   *Comando:* `FQT` + [Ruta] + `/A` + [Aerolínea] (Ej: `FQTAEPCOR/A5U`)
*   **Verificar Regulación Tarifaria (Notas):**
    *   *Comando:* `FQN` + [Número de línea] (Ej: `FQN4` tras desplegar la lista de tarifas).

### 4.2 Cotización en la Reserva Abierta (WS, WP, WW)
*   **WP (Cotiza pero NO guarda):** Realiza un cálculo básico de la tarifa e impuestos del itinerario actual sin guardar la máscara en el PNR.
    *   *Comando:* `WP` (o `FXX`).
*   **WS (Cotiza y GUARDA):** Almacena la cotización activa en el PNR para que el boleto pueda ser emitido posteriormente exactamente al valor cotizado.
    *   *Comando:* `WS` (o `FXP`).
    *   *Salida Esperada:* Desglose de tarifa base, tasas e impuestos por pasajero. Tras guardar la reserva con `ER`, el PNR mostrará la leyenda: `FARE - PRICE RETAINED`.
*   **WW (Detalles de Cotización):**
    *   *Comando:* `WW` o `WW` + [Número de Pasajero] (Ej: `WW1` o `TQT`). Muestra la construcción tarifaria completa (Fare Calculation) y el desglose de tasas.

### 4.3 Cotizaciones Avanzadas e Impuestos
*   **Cotizar Pasajeros Específicos:** `WS*P` + [Tipo] (Ej: `WS*PCHD1` para un niño, `WS*PINF1` para un infante).
*   **Cotizar Segmentos Específicos:** `WS*S1,2` (Cotiza segmentos 1 y 2). Para conexiones complejas (ej. rutas triangulares como CCS-MIA-CCS), se puede dividir: `WS*S1,4` y `WS*S2,3`.
*   **Forzar Base Tarifaria:** `WS*Q` + [Base Tarifaria] (Ej: `WS*QVAP10`).
*   **Reemplazo y Exención de Tasas en Emisión:**
    *   *Eximir todas las tasas:* `WS*TXEX`.
    *   *Reemplazar tasas:* `WS*TX20TQ/65SF` (Reemplaza las tasas de la cotización por 20 de TQ y 65 de SF).
    *   *Agregar tasas:* `WS*TX+12QO`.
*   **Despliegue General de Tasas de un País o Aeropuerto:**
    *   *Por País:* `TX*AR` (Muestra códigos, descripción, tipo de viaje y porcentaje de IVA, tasas de aeropuerto como TQ o XR).
    *   *Por Aeropuerto:* `TX*AEP`.

---

## 5. PROCESO COMPLETO DE EMISIÓN DE BOLETOS (TICKETING) Y REPORTES DE VENTAS

La emisión de boletos se realiza de manera integrada tras verificar que el PNR se encuentra cotizado y grabado (`FARE - PRICE RETAINED`), que no cuenta con segmentos UN o cancelados, y que se han registrado los pasaportes/documentos correspondientes.

### 5.1 Apertura y Control del Reporte de Ventas (WA)
El reporte es el libro de contabilidad diario donde se registran las emisiones y anulaciones de cada agente.
*   **Apertura del Reporte:**
    *   *Comando:* `WA*OPEN` (Requerido obligatoriamente antes de realizar la primera emisión del día).
*   **Visualizar Reporte Personal:**
    *   *Comando:* `WA*` (Muestra columnas de secuencia, número de boleto, tarifa, tasas, comisión aplicada, monto neto cobrado, forma de pago, tipo de transacción: `TKTT` para emitido, `CANX` para anulado/void, y localizador).
*   **Consultar Reportes de la Oficina:**
    *   *Comando:* `WL/` + [Oficina] + `/` + [Fecha] (Ej: `WL/BUEA050/16JAN`). Requiere el keyword de supervisor `RPGSPV`.
    *   *Filtro de Excepción de Impuestos Iquitos (Perú):* `WL/LIMH2160#12APR/EXPE` (Aplica el descuento del IGV según Ley 29285).
*   **Cierre del Reporte de Ventas:**
    *   *Comando:* `WA*CLOSE` (Se debe ejecutar al finalizar la jornada de ventas).

### 5.2 Emisión según Formas de Pago
El comando básico de emisión es `WK*`.
*   **Emisión en Efectivo (CASH):**
    *   *Comando:* `WK*FCA` (Emite boletos para todos los pasajeros).
    *   *Salida Esperada:* `OK. TKTs Nr. 9992200001131...` con un enlace directo para visualizar los cupones. El PNR se actualiza reemplazando la fecha de tiempo límite por los números de ticket: `TKT/ET 9992200001131`.
*   **Emisión con Cheque:**
    *   *Comando:* `WK*FCK` + [Número de cheque] + [Banco] (Ej: `WK*FCK123456 BCO NACION`). Se consolida en el reporte contable como CASH.
*   **Emisión con Tarjeta de Crédito:**
    *   *Comando:* `WK*F/` + [Código Tarjeta y Número] + `/` + [Vencimiento MMYY] + `/Z` + [Autorización] (Ej: `WK*F/VI4054343467672121/1229/Z8990`).
    *   *Códigos de tarjeta comunes:* `VI` (Visa), `AX` (American Express), `MC` (MasterCard), `DC` (Diners Club).
    *   *Emisión en cuotas y lotes:* `WK*F/AX3489798789789797/1229/Z1235/C3/L354` (donde C3 indica 3 cuotas y L354 indica número de lote).
*   **Emisión con Tarjeta de Débito:**
    *   *Comando:* `WK*F.` + [Código Tarjeta y Número] + `/Z` + [Autorización] (Ej: `WK*F.EL4054343467672121/Z123`).
*   **Emisión Múltiple (Dos formas de pago):** Permite pagar con Cash y Tarjeta:
    *   *Comando:* `WK*FCA#/VI4054343467672121/1229/Z8990-120/40XT` (Paga la diferencia de tarifa [120] e impuestos de la tarjeta con el formato de corte).
*   **Emisión a Facturar (Invoice / Cuenta Corriente):**
    *   *Comando:* `WK*FIN/` + [Nombre de la empresa] (Ej: `WK*FIN/MEDITERRANEO`). Descuenta del saldo de cuenta corriente autorizado.

### 5.3 Variantes de Emisión
*   **Emisión de Pasajeros Seleccionados:** `WK*FCA*N1,2` (Solo emite para los pax 1 y 2).
*   **Emisión de Segmentos Seleccionados:** `WK*FCA*S1` (Emisión parcial).
*   **Emisión con Comisión de Agencia:** `WK*FCA*KP10` (Registra un 10% de comisión en el e-ticket y reporte).
*   **Ingreso de Endoso Manual:** `WK*FCA*ED/NON END/NON REF`.
*   **Ingreso de Clave Fiscal:** `WK*FCA*VT/NUMERO-CLAVE-FISCAL`.

---

## 6. POST-VENTA, CAMBIOS, REVALIDACIONES, CANJES (EXCHANGE) Y COLAS

### 6.1 Anulación de Boletos (Void)
Solo se permite anular un e-ticket el mismo día de la emisión, antes de que el reporte de ventas del agente se haya cerrado.
*   *Comando:* `W*V` + [Número de boleto] (Ej: `W*V9992100212135`)
    *   *Reingresar para confirmar:* `W*V9992100212135/Y`
    *   *Salida Esperada:* `OK SALE IS CANCELLED IN REPORTING SYSTEM`. El estado de los cupones en la base de datos cambia a `V` (Void). Si es el único boleto del PNR, se le asigna de manera automática un tiempo límite de cancelación de 10 minutos.

### 6.2 Revalidación de Cupón de Vuelo (ETRV)
Permite actualizar fecha de viaje, número de vuelo u horarios de un ticket emitido, siempre que no existan cambios en la clase de reserva, ruta ni nombre del pasajero (evitando costos de exchange).
*   *Comando:* `ETRV/L` + [Línea del Ticket] + `/S` + [Línea del Segmento] + `/E` + [Cupón] (Ej: `ETRV/L2/S1/E1`).
*   *Revalidación con comentarios:* `ETRV/L2/S1/E1/POR CANCELACION DE VUELO`.
    *   *Salida Esperada:* El cupón modificado mantiene el estado `O` (Open for Use), y el cupón anterior se archiva en el historial del e-ticket precedido por un guión (`-`).

### 6.3 Canjes y Reemisiones (Exchange)
Se utiliza para reemitir un boleto por cambios voluntarios que conllevan cobros de diferencias de tarifa o penalidades.
*   **Exchange por Máscara (Guiado paso a paso):**
    *   1. Desplegar el PNR con el nuevo itinerario cotizado y guardado.
    *   2. Desplegar el ticket anterior con `ET/2` (línea 2 del ticket).
    *   3. Ejecutar: `WK*FEX`.
    *   4. Seguir los pasos de la máscara interactiva (Paso 1: cupones a canjear; Paso 2: diferencias de tarifa y tasas; Paso 3: forma de pago de adicionales) y confirmar haciendo clic en *NEXT* o *FINISH*.
*   **Exchange Directo por Comando:**
    *   *Comando:* `WK*FEX#CA` (Si la diferencia a cobrar es en efectivo) o `WK*FEX#CA*PE50.00XP` (Cobrando una penalidad de 50.00 con código XP).
    *   *Confirmar comando:* `WK*FEX#CA/Y`.
    *   *Salida Esperada:* El estado de los cupones del ticket original cambia de `OPEN` a `E` (Exchanged), y se emiten los nuevos números de e-tickets.

### 6.4 Mover e-tickets (ETMV) y Tickets Desasociados
*   **Asociar ticket a nueva reserva:** Útil si un PNR original se purgó por inactividad.
    *   *Comando:* `ETMV/P1` (Asocia el ticket desplegado al pasajero 1 de la nueva reserva abierta). El apellido del pasajero debe coincidir exactamente.
*   **Tickets Desasociados:** Si se realiza un cambio en el campo del nombre de un pasajero que ya tiene un boleto emitido, el sistema romperá la asociación:
    *   *Salida Esperada:* `OK * FARE DELETED ** PAX WITH TICKET // UNASSOCIATED TICKET **`. En la historia se registrará con `XN`. El pasajero queda libre de tickets y el ticket permanece en la reserva pero desasociado del nombre.

### 6.5 Gestión de Colas (Queues)
Las colas son bandejas de entrada del sistema donde el robot de KIU o la aerolínea depositan reservas para revisión de cambios.
*   **Colas Preestablecidas:**
    *   `Cola 1:` PNRs con vencimiento de tiempo límite dentro de las próximas 24 horas.
    *   `Cola 2:` PNRs con vencimiento dentro de las próximas 48 horas.
    *   `Cola 5:` Reservas canceladas automáticamente por vencimiento de tiempo límite.
    *   `Cola 10:` PNRs confirmados automáticamente desde lista de espera (status `KL`).
    *   `Cola 30:` Reservas afectadas por modificaciones de horario de vuelos (Schedule Change - status `UN` o `TK`).
*   **Comandos de Colas:**
    *   *Verificar colas activas de la oficina:* `QC/` (Muestra número de cola, cantidad de elementos, PNRs en acción y descripción).
    *   *Ingresar a una cola:* `Q/30` (Abre el primer PNR de la Cola 30).
    *   *Mover de cola:* `QMOV/214/212` (Mueve todas las reservas de la cola 214 a la 212).
    *   *Salir de cola (Ignorar cambios):* `QXI`.
    *   *Salir de cola (Remover PNR trabajado de la cola):* `QXR`.
    *   *Remover PNR y programar reingreso:* `QR+8*CONTACTAR NUEVAMENTE` (Saca de cola y volverá a ingresar en 8 horas).

---

## 7. ADMINISTRACIÓN DE DISPOSITIVOS Y CONTROL CENTER

El módulo **Control Center** de KIU (disponible a través de https://control.kiusys.com) es la consola web para los administradores de la agencia de viajes.

### 7.1 Alta de Usuario 1000
El usuario 1000 tiene privilegios de administrador maestro para dar de alta otros vendedores y resetear contraseñas de terminales.
*   **Configuración inicial de e-mail:**
    *   1. Ingresar a KIU-RES críptico con la firma `SI1000`.
    *   2. Ejecutar: `MAILCOUNTER@KIUSYS.COM`.
    *   3. Confirmar la autenticidad de los datos a través del correo de validación recibido por soporte de KIU.

### 7.2 Funcionalidades Web del Administrador (Mantenimiento)
*   **Administración de Usuarios (List of Users):**
    *   Permite habilitar o deshabilitar vendedores (Signs).
    *   *Asignación de Roles:* Habilitar el *check box* de `Administrator` activa el **Duty 1** (permite ver reportes consolidados y estados de cuentas corrientes de sucursales). Habilitar `Allow Issue` activa el **Duty 4** (permite al vendedor emitir tickets).
*   **Reseteo de Claves de Vendedores:**
    *   Al hacer clic en `Reset Password`, el sistema asigna de forma automática una contraseña aleatoria de 6 dígitos que se envía al correo corporativo.
*   **Reseteo de Terminales (Devices - Campo B):**
    *   El sistema KIU identifica cada instalación mediante un Office ID y un número de terminal (ej. `BUEA777001`). Cada terminal se asocia a un código único de autenticación denominado **Campo B**.
    *   Si se formatea la computadora, se bloquea la terminal, o se instala el sistema en una nueva máquina, el administrador debe resetear la terminal en el Control Center haciendo clic en `Reset Device` para generar un nuevo Campo B.

---

## 8. NOVEDADES TECNOLÓGICAS Y ACTUALIZACIONES DE PLATAFORMA (2025/2026)

KIU System Solutions ha integrado tecnologías de vanguardia en su suite de GDS y PSS para adaptarla a los estándares modernos de la industria de la aviación comercial:

1.  **Integración Avanzada con ATPCO:**
    *   El cotizador automático de KIU es capaz de extraer en tiempo real las estructuras tarifarias y reglas de **ATPCO** (Airline Tariff Publishing Company). Esto permite a los agentes cotizar tarifas con total exactitud, ejecutar exchanges complejos y reembolsos automatizados de manera precisa.
2.  **Venta y Emisión de Servicios Auxiliares (Ancillaries) vía EMD:**
    *   Soporte completo para la emisión de **EMD-A (Electronic Miscellaneous Document - Associated)** para servicios directamente relacionados con cupones de vuelo (como exceso de equipaje, abordaje prioritario o selección de asientos preferenciales).
    *   Soporte para la emisión de **EMD-S (Electronic Miscellaneous Document - Standalone)** para servicios independientes o cargos de penalidad de la aerolínea. Las tarifas y disponibilidad de ancillaries se cotizan dinámicamente conectando con ATPCO.
3.  **Cuentas Corrientes Electrónicas para Agencias NO BSP:**
    *   Para agencias de viaje que operan fuera del ecosistema IATA BSP, KIU implementó cuentas corrientes electrónicas prepagas o de crédito, permitiendo a la aerolínea definir límites de emisión y realizar conciliaciones directas sin comisiones bancarias intermediarias.
4.  **Omnicanalidad Avanzada y Omniterminal:**
    *   KIU PSS y GDS se integran de manera transparente con canales de distribución tradicional, portales e-Commerce, agencias OTAs y estándares **NDC (New Distribution Capability)**, permitiendo a las agencias acceder al mismo inventario enriquecido de servicios tradicionales y auxiliares de manera uniforme.
5.  **Análisis Predictivo mediante Inteligencia Artificial (AI Concierge):**
    *   Optimización de la previsión de demanda del inventario aéreo y asistentes interactivos integrados dentro de la plataforma para facilitar el servicio al cliente y la post-venta.
6.  **Sostenibilidad Ambiental y Operaciones sin Papel:**
    *   Check-in completamente digitalizado (Web check-in responsive para móviles), flujos de e-ticket 100% electrónicos eliminando de manera definitiva los cupones impresos de auditoría de agencia, reduciendo de forma significativa el desperdicio físico de papel.

---

## 9. GESTIÓN DE AGENCIAS DE VIAJES Y ESTRUCTURA ORGANIZATIVA (ECUADOR/CUENCA)

### 9.1 Requisitos de Constitución Legal de una Agencia de Viajes (Ecuador)
Para constituir legalmente una Agencia de Viajes en el Ecuador, se debe seguir la normativa de la Superintendencia de Compañías y obtener las licencias del Ministerio de Turismo:

1.  **Reserva de Nombre:** Se realiza ante la Superintendencia de Compañías (mínimo 10 opciones). Se requiere solicitar un certificado de búsqueda de nombre comercial ante el IEPI (Instituto Ecuatoriano de Propiedad Intelectual).
2.  **Minuta de Constitución:** Firmada por un abogado, estableciendo el tipo de compañía (Limitada: capital mínimo $5,000; Sociedad Anónima: capital mínimo $10,000) y se eleva a escritura pública.
3.  **Escritura y Aprobación:** Presentar los contratos constitutivos a la Superintendencia de Compañías para su resolución aprobatoria.
4.  **Inscripciones Administrativas:**
    *   Inscripción de nombramientos de administradores en el Registro Mercantil.
    *   Obtención del RUC (Registro Único de Contribuyentes) de persona jurídica en el SRI.
    *   Apertura del número patronal en el IESS.
5.  **Permisos para Operar (Establecimiento Turístico):**
    *   *Registro de Turismo:* Expedido por el Ministerio de Turismo (requiere escritura, RUC, planos de local con mínimo 30 m² exclusivos, declaración juramentada de activos fijos).
    *   *Afiliación Obligatoria a la CAPTUR* (Cámara Provincial de Turismo).
    *   *Licencia Única Anual de Funcionamiento (LUAF):* Emitida por el Municipio de la ciudad (Cuenca, Quito, etc.) antes del 30 de junio de cada año.
    *   *Patente Municipal y Permiso de Bomberos.*
    *   *Contribución del 1 por Mil sobre Activos Fijos:* Pago anual obligatorio para el Fondo de Promoción Turística del Ecuador (FMPTE).

### 9.2 Estructura Organizativa de la Agencia de Viajes Acreditada (Roles)
*   **Gerencia General:** Planifica, organiza y dirige el rumbo de la agencia, negociando con aerolíneas y coordinando finanzas.
*   **Jefe de Counter:** Supervisa la impresión y validez de boletos, consolida despachos de aeropuerto y administra colas de novedades.
*   **Counter Nacional:** Encargado de reservas, cotización y emisión en rutas locales (Tame, Aerogal/Avianca) e informes al BSP.
*   **Counter Internacional:** Encargado de itinerarios complejos de vuelos, reservas de hoteles y alquiler de vehículos globales, y emisión de e-tickets interlineales.
*   **Departamento Corporativo:** Administra cuentas clave de empresas, coordinando los códigos *Tour Code* y tarifas corporativas.
*   **Departamento de Turismo (Emisivo/Receptivo):** Diseña y comercializa paquetes turísticos nacionales e internacionales (*Landtours*, cruceros y excursiones).
*   **Departamento Financiero / Contabilidad:** Gestiona declaraciones tributarias del SRI, facturación de comisiones y conciliación de boletos emitidos.

---

## 10. REQUISITOS DE VISAS PARA VIAJES EMISIVOS Y PAÍSES DE DESTINO

Para un asesoramiento de viaje de excelencia, el counter internacional debe verificar con antelación los requisitos migratorios de los países destino.

### 10.1 Visado Schengen (Espacio Europeo Común)
Aplica para 27 estados europeos (Alemania, España, Francia, Italia, etc.). Para permanencias inferiores a 90 días por turismo o visita familiar, se requiere:
1.  **Formulario de Solicitud:** Completamente lleno y firmado.
2.  **Pasaporte Vigente:** Mínimo de 6 meses de validez a partir de la salida del espacio europeo.
3.  **Itinerario Completo:** Reserva de boletos aéreos de ida y vuelta que cubra la entrada y salida de Schengen.
4.  **Solvencia Económica:** Certificado de trabajo (salario, cargo y antigüedad), estados de cuenta bancarios de los últimos 6 meses, tarjetas de crédito internacionales y escrituras de propiedades.
5.  **Alojamiento Garantizado:** Vouchers hoteleros prepagados o carta de invitación notariada y legalizada de un residente del país europeo.
6.  **Seguro Internacional de Viaje:** Cobertura mínima obligatoria de **30,000 euros** para repatriación sanitaria y gastos médicos de urgencia en todos los países Schengen.

### 10.2 Visado para Canadá
1.  **Formulario de Información Familiar y Solicitud.**
2.  **Carta Explicativa de Viaje:** Dirigida al cónsul detallando de forma clara los planes y rutas del viaje.
3.  **Certificación Laboral o Copia de RUC:** Indicando la estabilidad laboral del aplicante.
4.  **Solvencia Económica:** Copias y originales de cuentas de ahorro, certificados de inversiones, matrículas de autos y escrituras de bienes raíces.
5.  **Carta de Invitación:** Si visita familiares en Canadá, se debe presentar carta del invitante con su estatus migratorio canadiense, referencias de empleo y estados de ingresos.

### 10.3 Visado para Estados Unidos
El trámite se inicia de forma virtual a través de http://evisaforms.state.gov/ y requiere:
1.  **Formulario DS-160** completado y firmado con código de barras.
2.  **Tasa Consular cancelada** en la entidad bancaria autorizada (Banco de Guayaquil).
3.  **Cita programada** en la sección consular del Consulado de Guayaquil o Embajada de Quito.
4.  **Pasaporte con validez mínima de un año.**
5.  **Fotografía:** Formato específico de 5x5 cm con fondo blanco.
6.  **Documentación de Solvencia:** El aplicante debe llevar a la entrevista consular todos sus documentos de arraigo en Ecuador (bienes raíces, estados bancarios de los últimos 6 meses, roles de pago y constancias de empleo de su compañía).

---
*Manual de Operaciones y Procesos consolidado bajo normativas y estándares actualizados a agosto de 2026.*
