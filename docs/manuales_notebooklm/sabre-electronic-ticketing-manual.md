# MANUAL COMPLETO DE BOLETERÍA, EMISIÓN ELECTRÓNICA Y GESTIÓN DE TARIFAS EN EL SISTEMA SABRE (GDS)
## Guía de Referencia y Base de Conocimiento de Nueva Generación (Actualizado 2026)

---

## INTRODUCCIÓN Y CONCEPTOS FUNDAMENTALES

### 1. El Contrato de Transporte Aéreo
Un **boleto de avión** es el contrato o acuerdo formal entre la línea aérea y el pasajero. Mediante este acuerdo:
*   La **aerolínea** se compromete a transportar al pasajero y su equipaje según las condiciones específicas de la tarifa seleccionada.
*   El **pasajero** se compromete a abonar el importe total de la transportación de acuerdo con las condiciones y restricciones de dicha tarifa.

### 2. Concepto de Boleto Electrónico (e-Ticket)
El **billete electrónico** (e-ticket) representa de forma enteramente digital la compra de un asiento en una línea de pasajeros (aérea, de autobús o de ferrocarril). Sustituye por completo al antiguo cupón físico multicapa de papel.
Una vez realizada la reserva, el boleto electrónico existe únicamente como un registro digital en los servidores de la línea aérea, denominado **ETR (Electronic Ticket Record)**. El pasajero conserva únicamente un recibo impreso o digital con el código de confirmación o localizador (PNR) y el número largo de boleto (generalmente de 13 dígitos).

#### Ventajas de la Boletería Electrónica:
*   **Eliminación de Costos de Infraestructura**: Facilita el proceso de acreditación ante IATA, eliminando requisitos físicos en las agencias como cajas fuertes homologadas para guardar inventario físico de papel.
*   **Emisiones de Último Momento**: Los pasajes se pueden emitir inmediatamente antes de la salida del vuelo de forma directa.
*   **Ahorros Administrativos y de Envío**: Se eliminan cargos de envío físico de cupones y la necesidad de preparar órdenes de transferencia de pasajes (PTA).
*   **Seguridad de Inventario**: No existen documentos físicos que puedan extraviarse o ser robados, ya que se resguardan de manera segura en el sistema de la aerolínea.
*   **Flexibilidad en Cambios y Reemisiones**: Facilita modificaciones de itinerario, intercambios de cupones y reembolsos, procesando los cupones digitales al instante.
*   **Accesibilidad a Largo Plazo**: El registro del e-ticket permanece accesible en la base de datos de Sabre por un lapso de hasta 13 meses posteriores a la fecha en que se completa el itinerario.
*   **Impresión Simplificada**: Los recibos e itinerarios de pasajes se pueden imprimir en impresoras de oficina convencionales.

---

## ESTRUCTURA DE UN BOLETO DE AVIÓN

Todo boleto en Sabre se divide en dos bloques principales de datos que configuran la transacción:

### 1. RBD (Reservation Booking Date)
Contiene la información de la reserva activa y el perfil del pasajero, incluyendo:
*   Nombre del pasajero (Passenger Detail - PD).
*   Itinerario detallado del vuelo.
*   Clases de tarifa asignadas (RBD / Clase de reserva).
*   Restricciones básicas de la tarifa.

### 2. BREAKDOWN (Desglose Tarifario)
Detalla los elementos económicos que componen el precio final de la transportación:
*   **Tarifa Base**: El importe base del pasaje en la moneda de origen.
*   **Impuestos (Taxes)**: Tasas gubernamentales, cargos aeroportuarios, tasas de seguridad, de combustible, etc., representados por códigos específicos (por ejemplo: AR, XT, UY, YQ).
*   **NUC (Neutral Unit of Construction)**: Unidad de cálculo tarifario internacional equivalente a 1 USD utilizada para construir tarifas multilínea.
*   **ROE (Rate of Exchange)**: Tipo de cambio aplicado para convertir las unidades de cálculo NUC a la divisa de pago.
*   **Costo por Segmento / Ruta**: Desglose financiero individual de cada tramo volado.
*   **Cargos Adicionales y Tarifa Total**: Sumatoria total a debitar.

---

## CONCEPTOS DE VIAJE, RUTAS Y CLASIFICACIONES

### 1. Terminología de Rutas
*   **Itinerario**: Secuencia ordenada de vuelos, con horarios de salida y llegada, ciudades de origen, conexión y destino que el pasajero debe seguir.
*   **Segmento de Vuelo**: El tramo aéreo directo (distancia volada o por volar) entre un punto de salida (ciudad de origen) y un punto de llegada (ciudad de destino).
*   **Parada (Stop)**: Cualquier punto intermedio de la ruta del viajero.
*   **Parada con Estancia (Stopover)**: Interrupción voluntaria del viaje en un punto intermedio seleccionada por el pasajero que implica pasar la noche (pernoctación intermedia).
*   **Parada de Conexión (Transfer)**: Interrupción involuntaria establecida por la aerolínea para cambiar de avión y continuar hacia el siguiente punto del viaje.

### 2. Tipos de Viajes según la Ruta
*   **One Way (OW)**: Viaje de solo ida que no retorna al punto de inicio.
*   **Round Trip (RT)**: Viaje clásico de ida y vuelta que retorna al punto de origen exacto.
*   **Open Jaw (OJ)**: Viaje de ida y vuelta con un tramo o segmento terrestre no volado (por ejemplo, volar de Buenos Aires a París, y regresar desde Roma a Buenos Aires).
*   **Open Jaw Doble**: Un itinerario que incluye un segmento terrestre no volado tanto en el destino como en el punto de origen.
*   **Viaje Alrededor del Mundo (Round the World - RW)**: Un viaje continuo de ida y vuelta que requiere tocar al menos un punto en cada una de las tres zonas geográficas de la IATA.

### 3. Tipos de Pasajeros según la Edad
*   **Infante (INF)**: Pasajero menor de 2 años. Debe viajar acompañado de un adulto.
    *   *Sin Asiento (Infante Acompañado)*: Generalmente abona el 10% de la tarifa de adulto, viaja en el regazo y no se despliega en las tarifas automáticas de adulto hasta la confirmación de la línea aérea.
    *   *Con Asiento*: Paga habitualmente el 50% de la tarifa de adulto y ocupa un asiento físico en el avión.
    *   *Dos Infantes con un Solo Adulto*: Uno de ellos debe abonar obligatoriamente la tarifa del 50% y ocupar asiento.
*   **Infante No Acompañado**: Pasajero de más de 7 días de vida y menor de 2 años viajando sin tutor. Su tarifa y aceptación están sujetas a estrictas políticas individuales de la línea aérea operadora.
*   **Niño (Child - CNN o CHD)**: Pasajero de entre 2 y 12 años (puede variar según el transportador). Se le aplican descuentos de Child basados en la regulación del viaje.
*   **Adulto (ADT)**: Pasajero de entre 12 y 64 años de edad. Abona el 100% de la tarifa base.
*   **Tercera Edad (Senior Citizen - SRC)**: Pasajero a partir de los 65 años de edad. Cuenta con tarifas especiales que generalmente ya traen incorporado el descuento.

### 4. Tipos de Tarifas según el Tiempo de Validez
*   **Tarifa Normal / Regular**: Válida por un año completo a partir del inicio del viaje o de la fecha de emisión (en caso de no haberse utilizado). Permite cambios libres de penalidad (sujetos a disponibilidad de clase).
*   **Tarifa Especial**: Publicada bajo ofertas limitadas por las aerolíneas. Posee fechas fijas de restricción de compra (emisión antes de "X" fecha) y de uso (vuelo completado antes de "Y" fecha).
*   **Tarifa de Excursión**: Tarifa especial aplicable principalmente para transporte aéreo como parte de un viaje turístico de grupo organizado.
*   **Tarifa Aplicable**: La tarifa publicada o construida que se encuentra vigente en el momento en que el pasajero inicia su viaje (o reinicia el viaje en caso de cambios de fecha).

### 5. Clases de Servicio y Restricciones
Las clases varían según el transportador, pero se dividen típicamente en:
*   **Ejecutiva / Business**: Representada por clases como `J`, `C`, `D`, `R`, `I` (según la aerolínea).
*   **Económica**: Representada por clases comunes como `Y`, `K`, `V`, `Q`, `H`.
*   **Tarifas Nobles (H e Y)**: Clases de tarifa económica con alta flexibilidad que pueden combinarse libremente con otras tarifas y clases.
*   **Clase K**: Tarifas económicas promocionales que no están disponibles todo el año. Tienen tiempos de estadía mínimos y máximos estrictos, no permiten paradas intermedias (stopovers), no son reembolsables y aplican penalidades por cualquier cambio. No ofrecen descuentos para niños ni ancianos.

---

## FORMATOS BÁSICOS, ALFABETO FONÉTICO Y TIEMPOS

### 1. El Alfabeto Fonético ICAO/IATA
Utilizado de manera obligatoria en la comunicación telefónica y soporte para dictar códigos de reserva, nombres y formatos:
*   **A** - Alfa | **B** - Bravo | **C** - Charlie | **D** - Delta | **E** - Eco | **F** - Fox
*   **G** - Golf | **H** - Hotel | **I** - India | **J** - Juliet | **K** - Kilo | **L** - Lima
*   **M** - Mike | **N** - November | **O** - Oscar | **P** - Papa | **Q** - Quebec | **R** - Romeo
*   **S** - Sierra | **T** - Tango | **U** - Uniform | **V** - Victor | **W** - Whisky | **X** - X-ray
*   **Y** - Yankee | **Z** - Zulu

### 2. Formato de Tiempos y Fechas
*   **Meses del Año**: Se abrevian estrictamente en tres letras y en idioma inglés:
    *   JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC
*   **Días de la Semana**: Se representan con números del 1 al 7 (Lunes a Domingo) o con sus abreviaturas en inglés (Mo, Tu, We, Th, Fr, Sa, Su).
    *   *Indicador de Excepción*: La presencia de una **X** delante del día indica exclusión. Por ejemplo: `X7` significa "Excepto Domingos".
*   **Formatos Horarios (12h vs 24h)**:
    *   `1:00` en formato de 12 horas es `1A` (AM).
    *   `13:00` en formato de 12 horas es `1P` (PM).
    *   `12:00` (Mediodía) se representa como `12N` (Noon).
    *   `0:00` (Medianoche) se representa como `12A` (Midnight).

---

## FORMATOS Y COMANDOS DE RESERVAS (PNR) EN SABRE

### 1. Formatos Principales del PNR
Para crear o desplegar registros de reserva, se utilizan comandos estructurados de un dígito inicial:
*   `1` (Avail): Solicita la disponibilidad de vuelos (Ej: `120OCTMVDMAD` para disponibilidad neutral de todas las compañías).
*   `2` (FLIFO): Solicita información operacional y de vuelo (Ej: `2CO35` o `2IB6251/2AUG` para una fecha futura).
*   `3` (FAX): Envía mensajes de servicios especiales (OSI/SSR) a las compañías asociadas de la reserva.
*   `4` (FAX AA): Envía mensajes exclusivos para American Airlines.
*   `5` (RMKS): Agrega comentarios generales en el campo Remarks del PNR (Ej: `5PAX NECESITA VISA CANADA`).
*   `6` (RCVD): Ingresa el nombre de la persona que solicita los cambios en el PNR (Ej: `6JUANA`). Es obligatorio antes de cerrar la reserva.
*   `7` (TKT): Registra el tiempo límite acordado con el cliente para emitir el boleto (Ej: `7TAW23DEC/`).
*   `8` (TAW): Tiempo límite especificando fecha y hora exacta de vencimiento (Ej: `8TAW/2APR1P`).
*   `9` (PHONE): Agrega números telefónicos de contacto (Ej: `9 26657777A` para teléfono de agencia).
*   `0` (Cero): Formato de compra o reserva directa (Ej: `02Y1` para reservar 2 asientos en la clase Y de la línea 1 de la disponibilidad).

### 2. Teclas Especiales y Símbolos de Consola
*   `CLEAR` o `CLEAR ALT`: Limpia la pantalla de información.
*   `ESC`: Posiciona el cursor en el extremo izquierdo de la pantalla de comandos.
*   `Cruz de Lorena (‡)`: Liga múltiples calificadores dentro de un mismo comando en una sola entrada de consola.
*   `Guion Bajo ( _ )`: Formato utilizado para ingresar o modificar nombres.
*   `Cambio (¤)`: Modifica datos o borra líneas específicas del registro (Ej: `1.1¤` para borrar el nombre del renglón 1.1).
*   `Fin de Comando (§)`: Da acceso a las bases de datos de Sabre y concatena formatos.
*   `Retorno (¶)`: Separa comandos para ejecutarlos en un solo paso de consola.
*   `Asterisco (*)`: Despliega información específica en la pantalla (Ej: `*A` despliega toda la reserva; `*T` despliega los datos de boletería).

### 3. Operaciones Avanzadas de Reservas
*   `VCT*`: Verifica los tiempos mínimos de conexión (MCT - Minimum Connection Time) en el PNR activo.
*   `*H`: Despliega el historial completo de transacciones del PNR, registrando quién, cuándo y qué se modificó.
*   `IC`: Clona los segmentos de vuelo de un PNR ignorando la transacción actual.
*   `D1.1`: Divide un PNR para separar a un pasajero (renglón 1.1) a un récord de reserva independiente.

---

## EMISIÓN DE BOLETOS EN SABRE: ASIGNACIÓN DE IMPRESORAS Y COMANDOS

Antes de proceder a la emisión de cualquier boleto, el agente debe programar y designar sus terminales de impresión asignadas.

### 1. Configuración de Impresoras y Administración de Stock
*   **Asignación de Impresoras (Formato general)**:
    ```sabre
    W*AR      (Establece el país de emisión, ej: Argentina)
    PTR/777777  (Designa la dirección física de la impresora de pantallas/itinerarios)
    DSIV777777 (Designa la impresora para itinerarios virtuales, normalmente coincidente con PTR)
    ```
*   **Desasignación de Impresoras**:
    ```sabre
    W*NO       (Desasigna la impresora de tickets)
    PTR/END    (Desasigna la impresora de pantalla)
    DSNO       (Desasigna la impresora de itinerarios)
    ```
*   **Verificación del Estado de Impresión**: El comando `*S*P` muestra la persona firmada en Sabre, su PCC (código de pseudo ciudad) y las direcciones de impresoras activas de boleto, pantalla e itinerarios.
*   **Control de Stock**: Para saber cuál es el próximo número correlativo de boleto electrónico asignado en el sistema, se utiliza el comando `DN*PTR`.

---

## EMISIÓN AUTOMÁTICA (FASE 3.0)

Esta es la manera estándar garantizada en su totalidad por Sabre. Ocurre cuando el itinerario se cotiza de manera automática mediante los formatos `WP` o `WPNCB`.

### 1. Estructura Básica del Comando de Emisión (Calificadores Obligatorios)
El comando debe contener al menos 3 calificadores obligatorios unidos por la cruz de Lorena:
```sabre
W‡F[forma de pago]‡A[línea aérea validadora]‡KP[porcentaje de comisión]
```
*Ejemplo:* `W‡FCASH‡AAR‡KP9` (Emite boleto validado por Aerolíneas Argentinas, forma de pago cash y 9% de comisión).

### 2. Calificadores Detallados de Formas de Pago (`‡F`)

#### A. Contado (CASH):
Se escribe simplemente la palabra `CASH` o `CA`:
```sabre
W‡FCASH‡AQF‡KP6
```

#### B. Tarjeta de Crédito (Total):
Se especifica el código de la tarjeta (ej: AX, VI, CA, TP), el número, la fecha de vencimiento (MMYY) y el código de aprobación manual precedido por `*Z`:
```sabre
W‡FCASH‡AAR‡KP9‡F*AX376412345601005/0706*Z27
```
*Aprobación Automática*: Si no se incluye el código `*Z`, Sabre lo solicita automáticamente a la entidad emisora. Si es denegada, no se emite el boleto ni se efectúa el cargo.

#### C. Tarjeta de Crédito en Cuotas:
Aplica bajo especificaciones de ciertos países (no disponible en Perú o Bolivia). Se añade el parámetro `*E` y la cantidad de cuotas (en dos dígitos) antes del código de aprobación. **Requiere aprobación telefónica previa obligatoria**:
```sabre
W‡KP6‡BA*02P‡AIB‡F*AX376412345601003/1108*E06*Z27
```

#### D. Pago Múltiple (Tarjeta de Crédito + Cash):
Se utiliza la instrucción `FMP` seguido de `CA*` y los datos de la tarjeta. Al final, se incluye una barra `/` con el monto total debitado en la tarjeta. Sabre calcula el restante automáticamente como pago CASH:
```sabre
W‡KP6‡BA*02P‡AUA‡FMPCA*AX376412345103/1108*Z27/1500.00
```
*(1500.00 es el monto total cobrado a la tarjeta de crédito para cada uno de los boletos. Si se pagan cuotas con pago múltiple, se añade el endoso ‡EDEP seguido de la cantidad de cuotas, ej: ‡EDEP03).*

### 3. Emisión Bajo la Metodología NET REMIT
Para aerolíneas adheridas a la facturación neta, el comando varía para reportar adecuadamente al BSP:
*   *Forma de Pago CASH (Con Tour Code)*:
    ```sabre
    W‡NET/V*ABC123‡FCASH‡AAA‡KP1
    ```
*   *Forma de Pago Múltiple (CC + Cash - Net Remit)*: Se debe especificar el total cobrado a la tarjeta menos impuestos, y el total completo de la tarjeta:
    ```sabre
    W‡NET/1500.00/CC1800.00/V*ABC123‡F*AX1234567890123/1009*Z56‡AAA‡KP1
    ```
    *(Donde 1500.00 es la tarifa asignada a la tarjeta sin impuestos, y 1800.00 es el total debitado en tarjeta).*
*   *Separador especial*: Si el Tour Code provisto tiene una barra divisoria (ej: PPP/123), se debe anteponer `/C*` a la segunda sección: `W‡NET/V*PPP/C*123`.

### 4. Modificadores Opcionales de Emisión
*   **Selección de Pasajeros (`‡N`)**: Permite emitir solo un pasajero o un grupo selecto: `W‡N1.1‡FCASH‡ABA` (Solo emite al pasajero 1.1).
*   **Selección de Segmentos (`‡S`)**: Emite tramos específicos del itinerario: `‡S1/4‡` o `‡S2-4‡`.
*   **Franquicia de Equipaje (`‡BA*`)**: Define el peso o piezas por segmento:
    *   `15K` o `20K` (Kilos de equipaje).
    *   `02P` (Concepto de hasta 2 piezas de equipaje).
    *   `NIL` (Sin equipaje permitido, obligatorio para infantes sin asiento).
    *   *Multisegmentos*: `W‡BA1*02P‡BA2*20K‡...` (Segmentos 1 y 2 con equipaje diferente).
*   **Endosos y Restricciones (`‡ED` / `‡EO/`)**: Añade o sobrescribe texto restrictivo en el boleto (máximo 58 caracteres): `‡EDNON END NON REF` o `‡EO/VALID PU ONLY`.
*   **Tour Code (`‡UN*` / `‡V*`)**: Agrega el código de descuento. `UN*` para líneas aéreas no Net Remit, `V*` para aerolíneas Net Remit.
*   **Impresión de Itinerario del Pasajero (`‡DPE`)**: En emisiones donde por defecto solo se genera el billete virtual, fuerza la impresión física del itinerario para constancia del pasajero: `W‡FCASH‡ALA‡KP7‡DPE`.

---

## COTIZACIÓN DESDE PRICE QUOTE (PQ)

Al cotizar con comandos de búsqueda como `WP`, `WPNC` o `WPNCS`, se genera un registro tarifario temporal denominado **PQ (Price Quote)**.
*   `PQ`: Guarda la cotización actual en la reserva.
*   `*PQ` o `*PQS`: Despliega el resumen o registro de cotizaciones activas en el PNR.
*   `PQDALL`: Borra todos los registros PQ guardados.
*   **Emisión desde un PQ**: Al momento de emitir, solo se necesita llamar al número de PQ almacenado mediante `W‡PQ1`. Se pueden emitir hasta un máximo de 4 máscaras PQ en un mismo comando.

---

## EMISIÓN POR COMANDO - FASE 3.5 (FORZAR BASE DE TARIFA)

Esta modalidad no está garantizada por Sabre. Se utiliza cuando el sistema no cotiza de manera automática la tarifa requerida, pero la base tarifaria sí existe cargada en la base de datos de Sabre para ese par de ciudades.
*   Se añade el modificador **`Q`** seguido por el código exacto de la base de tarifa:
    ```sabre
    W‡FCASH‡BA*02P‡ALA‡KP6‡QKLE30AN
    ```
*   *Segmentos con Tarifas Diferentes*:
    ```sabre
    W‡FCASH‡BA*02P‡ALA‡KP6‡S1*QKLXE30N‡S2*QKLWE30N
    ```
    *(Segmento 1 con base KLXE30N y Segmento 2 con base KLWE30N)*.

---

## EMISIÓN CON DESCUENTO - FASE 3.75

Permite forzar descuentos especiales (como planes familiares) que no se calculan de manera directa. Se añade el formato de descuento específico:
```sabre
Q[base de tarifa]/[ticket designator]/DP[porcentaje de descuento]
```
*Ejemplo:* `W‡QYLX/YLXM25/DP25‡FCASH‡KP6‡AJJ‡BA*15K` (Aplica 25% de descuento sobre la base tarifaria YLX, utilizando el designador YLXM25).
*   Si se aplica el descuento sobre la cotización automática del sistema, no es necesario incluir la base tarifaria, quedando como `Q//YLXM25/DP25`. Si tampoco se provee un ticket designator, se ingresan dos barras continuas: `Q//DP25`. En el billete se imprimirá automáticamente la leyenda "DISC".

---

## EMISIÓN MANUAL - FASE 4

Se emplea cuando la tarifa no está cargada en el sistema Sabre o no es posible cotizarla de manera automática. No está garantizada por Sabre y se puede realizar mediante dos métodos:

### Método A: Creación y Completado de Máscaras
Permite abrir una pantalla editable (máscara) para completar manualmente cada casillero del billete electrónico.

#### Paso 1: Creación de la Máscara:
Se abre una máscara por cada boleto diferente de la reserva.
*   `W‡CTKT`: Crea una máscara para todo el itinerario para un adulto.
*   `W‡CTKT‡PCNN`: Crea una máscara de niño.
*   `W‡CTKT‡S2/3/4`: Crea máscara de adulto para segmentos específicos 2, 3 y 4.
*   `**WTKT`: Despliega el listado de máscaras activas y su estatus.
*   `**WTKT2`: Abre o accede a la máscara número 2.
*   `W‡D1`: Borra la máscara número 1.

#### Paso 2: Completado de la Máscara (Pantallas de Edición):
*   **Pantalla 1**: El agente completa los campos como origen/destino, códigos de moneda de origen y pago, impuestos (hasta 6 desgloses), porcentaje de comisión y el Tour Code. Presionar `[Enter]` para guardar y avanzar.
*   **Pantalla 2 (WI - Phase IV Fare Info)**: Se completan las restricciones temporales por segmento: base tarifaria, fecha "Not Valid Before" (NVA), fecha "Not Valid After" (NVB) y franquicia de equipaje (`BAG ALLOW`). Presionar `[Enter]` para guardar y avanzar.
*   **Pantalla 3 (Construcción Tarifaria)**: Se ingresa de forma manual la construcción de la tarifa respetando la simbología técnica tradicional (Ej: `EZE AR MIA R500.00VLEX2 AR EZE R500.00VLEX2 NUC1000.00 END ROE1.00`). Presionar `[Enter]` para regresar a la primera pantalla.
*   *Salida de la máscara*: Presionar `[Esc]` y luego `[Ctrl] + [Clear]`.

#### Paso 3: Verificación y Cierre:
Una vez validados y guardados los cambios, se cierra y finaliza la reserva (`ER`).

#### Paso 4: Emisión:
Se relaciona la máscara creada con los pasajeros de la reserva para emitir el boleto:
```sabre
W‡T1N1.1‡FCASH‡ABA
```
*(Emite la máscara manual 1 para el pasajero 1.1 con forma de pago cash y validadora British Airways).*
*   *Copiar Máscaras*: Se puede transferir una máscara creada de un código de reserva a otra que comparta exactamente la misma ruta mediante el comando: `W‡CP*CÓDIGO`.

---

### Método B: Fase 4 en Forma Lineal
Permite cargar todos los datos de la Fase 4 en comandos lineales encadenados en lugar de pantallas interactivas:
*   `W‡C`: Encabeza la creación de la fase lineal.
*   `W‡I‡L1/2/3-QXE30*BA02P*‟‟‟‟‟07AUG`: Inserta segmentos de itinerario 1, 2 y 3 con base QXE30, equipaje de 2 piezas y vencimiento al 07AUG.
*   `W‡I‡CLIM AA MIA Q5.00 280.00HLE90P...`: Carga la construcción tarifaria lineal.
*   `W‡I‡YUSD468.00/84.24PE/24.00US/3.00XF`: Inserta la tarifa neta e impuestos.
*   `W‡I‡KP1`: Inserta el porcentaje de comisión.
*   `W‡I‡UN*12345`: Inserta el Tour Code.
*   `W‡I‡ED/NON END NON REF`: Inserta las restricciones de endoso.

---

### Emisión de Tarifas BT (Bulk Ticket) en Fase 4
Se utiliza cuando la aerolínea otorga una tarifa neta confidencial que no debe ser impresa en el boleto del pasajero:
1.  En la Pantalla 1, el importe `BASE FARE` se carga con la cifra exacta suministrada por la aerolínea. El casillero de comisión se carga en `0` o con el porcentaje acordado. El Tour Code se deja en blanco para ingresarse en el comando de emisión final.
2.  En la Pantalla 3 (Construcción de tarifa), se obvian las cifras monetarias y se escribe la sigla **`BT`** al final de la construcción (Ej: `EZE IB MAD IB EZE BT END ROE1.00`).
3.  *Emisión final*: Se emite llamando al PQ o máscara correspondiente y agregando el calificador `‡UB*XXXXX` con el código de tarifa provisto por la aerolínea:
    ```sabre
    W‡T2N1.2/1.3‡AIB‡FCASH‡UB*ITBUEIB1245
    ```

---

### Método Intermedio: El Comando `WD`
Este comando automatiza el inicio de la Fase 4. Genera una máscara de Fase 4 enteramente completa basándose en la cotización automática del comando `WP`.
*   El agente ejecuta `WP` para cotizar.
*   Inmediatamente después ejecuta `WD`, volcando automáticamente la información al registro manual.
*   Abre la máscara con `**WTKT1` y procede únicamente a sobrescribir o modificar los campos específicos que desea alterar sin necesidad de rellenar la máscara desde cero.
*   *Modificadores de WD*: Admite forzar bases de tarifas (`WDQVLXE30A`), seleccionar segmentos (`WDS1/3*QY`), o forzar fechas históricas de cotización (`WDB19JAN`).

---

## MANTENIMIENTO, GESTIÓN Y SEGUIMIENTO DEL BOLETO EMITIDO

### 1. Visualización del Registro del Boleto (ETR)
Una vez emitido el pasaje, se puede visualizar de dos maneras:
*   **Desde la Reserva Abierta**: Se despliega el campo Ticket con `*T`. Se localiza el renglón correspondiente marcado con el indicador `TE` (Ticket Electrónico). Para ver el desglose se escribe:
    ```sabre
    WETR*número de renglón   (Ej: WETR*2)
    ```
*   **Fuera de la Reserva**: Se consulta directamente mediante el número completo de e-ticket:
    ```sabre
    WETR*T1251686189134
    ```
    *(Para imprimir la pantalla del ETR se puede presionar [Shift] + [Enter] en lugar de solo [Enter]).*

### 2. Reexpedición y Reimpresión de Documentos
*   **Reexpedición de Cupón de Agente**: Para reimprimir el cupón correspondiente a la oficina de ventas:
    ```sabre
    W‡RG0161300000793‡RE
    ```
    *(Donde `RG` y `RE` son obligatorios y fijos en el formato, seguidos del número de ticket).*
*   **Reexpedición de Recibo de Pasajero (Passenger Receipt)**: Se inicia desplegando el historial de documentos emitidos con el comando `DWLIST`. Una vez visualizado el listado, se selecciona el ítem numérico del pasajero a reimprimir (ejemplo: Alexander, ítem 6):
    ```sabre
    DP2/3/6
    ```
    *(Donde `DP2/3` es parte obligatoria del formato e indica la reimpresión del recibo de pasajero, y `6` corresponde al número del listado).*

### 3. Revalidación de Boletos Electrónicos
Cuando se efectúa un cambio menor de fecha u horario en un itinerario ya emitido (sin modificar la ruta ni la tarifa de origen), se debe realizar la revalidación del e-ticket para sincronizar los cupones en el sistema de la aerolínea.
*   *Nota*: Algunas aerolíneas solo permiten revalidación telefónica. Para las que lo permiten por sistema, se abre la reserva y se ejecuta:
    ```sabre
    WETRL/Sn/Cm
    ```
    *(Donde `Sn` representa el número del SEGMENTO de vuelo en la reserva, y `Cm` corresponde al número del CUPÓN del ticket).*
    *Ejemplo:* `WETRL/S3/C2` (Revalida el segmento 3 de la reserva contra el cupón 2 del boleto electrónico).
    Si la operación es exitosa, el sistema responderá: `REVALIDATION SUCCESSFUL`. Se debe realizar una entrada individual por cada segmento a revalidar.

### 4. Anulación (Void) de Boletos Electrónicos
La anulación por sistema descuenta el importe del billete de la liquidación del reporte de ventas diarias de la agencia. **Únicamente es aceptada y procesada por el BSP si se realiza el mismo día de la emisión del boleto**. Cualquier anulación fuera de este plazo será cargada a la liquidación de la agencia.
*   **Desde la Reserva Abierta (Método Estándar)**:
    1.  Desplegar el campo de boletos con `*T`.
    2.  Identificar el renglón del boleto (ejemplo: renglón 2).
    3.  Ingresar el comando de anulación: `WV2`.
    4.  El sistema responderá: `REENTER IF [Número de ticket] IS TO BE VOIDED`.
    5.  Reingresar de manera idéntica: `WV2` para reconfirmar.
    6.  El sistema arrojará: `VOID MSG SENT`.
    7.  Cerrar y finalizar la transacción de forma inmediata (`6[Firma]§E` o `EMT`). Al consultar de nuevo con `*T`, el renglón mostrará el indicador `*VOID*`.
*   **Fuera de la Reserva (Directo)**:
    1.  Desplegar el e-ticket: `WETR*T[Número de boleto]`.
    2.  Ingresar: `WETRV` y presionar Enter.
    3.  Reingresar `WETRV` para reconfirmar.
    4.  Cerrar la transacción con `E`.
*   **Anulación sin Registro del Número de Boleto en el PNR**: En caso de que el PNR no retenga la información del ticket en el campo `*T`, se puede forzar la anulación de forma lineal ingresando todos los campos asociados del billete:
    ```sabre
    WV‡[nro boleto]/[moneda y valor]/[código agencia]/[fecha emisión]/[forma pago]/[indicador itinerario]
    ```
    *Ejemplo:* `WV‡0019465123456/ARS3450.78/AMNSXG/31FEB/CA/I` (Anula de forma manual un boleto internacional, pago cash, emitido el 31FEB).
*   **Anulación de Boletos Correlativos que no se Emitieron**:
    *   `ATCX/35893456776/1` (Anula un solo boleto sin emitir en stock, incluyendo dígito verificador).
    *   `ATCX/35893456776/4` (Anula 4 boletos a partir del inicial).
*   **Visualización de Anulaciones**: El comando `WV*` muestra la lista completa de todas las anulaciones de boletos realizadas en el mes en curso.

### 5. Reportes Financieros y Control de Emisiones
*   **Listado de Ventas Diarias (`DQB*`)**: Muestra un reporte ordenado de todas las emisiones y anulaciones de boletos efectuadas en el día en curso, detallando PNR, pasajero, número de ticket, comisión, forma de pago, moneda, total y si está anulado (marcado con una `V`).
    *   *Retroactividad*: Se puede consultar información de ventas pasadas con hasta 1 mes de retroactividad: `DQB*10DEC`.
*   **Reporte de Boletos Electrónicos No Utilizados**: Genera un listado detallado de aquellos boletos emitidos por la agencia que tienen al menos un segmento abierto después de 30 días de la fecha de viaje:
    *   *Requisito*: Requiere que la agencia tenga activo el **TJR (Travel Journal Record)**. Se activa mediante el comando `W/ETU‡ON` (requiere firma de nivel supervisor con duty code 9 y keyword SUBMGR). Se desactiva con `W/ETU‡OFF`. Se verifica el estatus con `W/ETU‡*`.
    *   *Comandos de Consulta de Boletos No Utilizados*:
        *   `DQB*ETU`: Despliega la información general.
        *   `DQB*ETU/DK999999999`: Despliega por número de cuenta corporativa (DK).
        *   `DQB*ETU/PX`: Despliega según la fecha de purga de datos del sistema.
        *   `DTB*ETU/15JUN`: Muestra boletos no utilizados por una fecha específica.
        *   `DTB*ETU/BA`: Muestra boletos no utilizados filtrados por aerolínea.

---

## INNOVACIONES Y ACTUALIZACIONES DEL SISTEMA SABRE (TECNOLOGÍAS 2025/2026)

La industria de distribución global y la gestión de tarifas han experimentado una transformación radical que complementa y actualiza los comandos tradicionales de Sabre.

### 1. Transición de Sabre Red 360 a Sabre Mosaic
La histórica suite de escritorio **Sabre Red 360** está evolucionando hacia **Sabre Mosaic Agency Workspace** (y su versión para agentes independientes **Agency Workspace Lite**, anteriormente conocida como Launchpad).
*   **Arquitectura Cloud-Native**: Diseñada para operar en la nube, eliminando retrasos por sincronización local de terminales.
*   **Inteligencia Artificial Nativa ("Hard-Wired AI")**: Incorpora de forma nativa asistentes conversacionales y agentes de consulta virtuales para automatizar tareas repetitivas y consultas en lenguaje natural directamente en el terminal del agente.
*   **Flujo de Trabajo Híbrido**: Permite combinar una interfaz gráfica intuitiva y simplificada para agentes noveles con la velocidad de la consola de comandos nativa de Sabre para los "power agents" o expertos.

### 2. Gestión Unificada de Órdenes y Contenido NDC (New Distribution Capability)
Con la llegada del protocolo NDC, las aerolíneas distribuyen tarifas personalizadas directamente desde sus sistemas, rompiendo el esquema clásico de clases GDS (EDIFACT).
*   **Sabre Mosaic Order Management**: Es el nuevo motor que normaliza las diferentes fuentes de datos de proveedores. Unifica el contenido NDC, EDIFACT y LCC (Low-Cost Carriers) en una sola pantalla.
*   **Sincronización Automática de EMD (Electronic Miscellaneous Documents)**: El sistema automatiza el seguimiento de "Paid Extras" (asientos pagados, maletas adicionales, comidas especiales). Los EMD se asocian y sincronizan de forma nativa con la orden principal de vuelo para evitar descuadres de inventario.
*   **Reducción del Riesgo de Notas de Débito (Debit Memos)**: Sabre Mosaic integra reglas de tarifas automatizadas y validaciones de impuestos en tiempo real antes de la emisión del boleto. Esto bloquea errores de cálculo que tradicionalmente generaban multas millonarias de las aerolíneas a las agencias.

### 3. Intercambios y Reembolsos Automatizados (AER)
*   **Integración CAT 31 (Voluntary Change)**: El módulo AER de Sabre automatiza por completo el proceso de reemisión. Al cambiar fechas, el sistema lee de forma nativa las condiciones CAT 31 de la tarifa, calcula la diferencia tarifaria y la penalidad de cambio exacta, reemitiendo el boleto en un proceso automatizado de cuatro pasos sin necesidad de rellenar máscaras manuales de Fase 4.

### 4. Integraciones de Back-Office e Interfaz
*   **Interface Option 6**: Es el estándar configurado en el Travel Journal Record (TJR) de la agencia que recopila de forma automática cada boleto emitido y anulado, enviándolo en tiempo real al software de contabilidad y administración (back-office) mediante el software Java Print Manager (SJPM) de Sabre. Requiere firmas EPR asignadas con el keyword **MINOPR** para ejecutar comandos de control de interfaz (`DX`).

---
