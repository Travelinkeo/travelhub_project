# MANUAL MAESTRO DE AMADEUS: DE PRINCIPIANTE A EXPERTO
## *Guía de Referencia Completa y Base de Conocimientos (Incluye Actualizaciones 2024–2026)*

---

## INTRODUCCIÓN

El sistema global de distribución **Amadeus (GDS)** es la columna vertebral de la industria turística y de aviación a nivel mundial. Este manual tiene como objetivo guiar paso a paso a cualquier persona, sin importar su experiencia previa, desde los conceptos y comandos más básicos hasta las metodologías de tarificación, reemisión automática y la moderna integración de contenido **NDC (New Distribution Capability)** de última generación.

Con la evolución de la tecnología, Amadeus ha transicionado de un sistema puramente críptico (interfaz de línea de comandos en terminal de pantalla azul) a **Amadeus Selling Platform Connect**, una plataforma profesional basada en la nube y accesible de forma remota 24/7. Esta evolución introduce el concepto de **retailing inteligente**, combinando lo mejor del lenguaje críptico tradicional con interfaces de usuario intuitivas y automatización avanzada.

---

## CAPÍTULO 1: ACCESO, CONFIGURACIÓN Y COMANDOS DE AYUDA

El acceso seguro y la navegación por las diferentes áreas de trabajo son los primeros pasos para dominar el sistema.

### 1.1. Inicio y Cierre de Sesión (Sign-In / Sign-Out)
El acceso a Amadeus se realiza mediante la firma del agente (Sign) y está ligado a una oficina específica mediante un identificador único conocido como **Office ID** (u *Office Profile*).
*   **JI (Jump In):** Comando estándar para firmarse en el sistema.
    *   *Sintaxis:* `JI[Número de Agente][Duty Code]` o `JI[Número de Agente][Duty Code]-[Contraseña]` si se requiere contraseña.
    *   *Ejemplo:* `JI1234AB/GS` (Duty Code: *GS* para supervisor o agente general).
*   **JO (Jump Out):** Desconecta la firma del agente del área de trabajo activa.
*   **JD (Jump Display):** Muestra las áreas de trabajo disponibles (áreas de la A a la F). Permite al agente ver qué reservas u operaciones tiene activas en paralelo en cada pestaña virtual.

### 1.2. Preferencias de la Firma
*   **JGU (Jump General Update):** Permite configurar preferencias permanentes de la firma.
    *   *Ejemplo:* `JGU/LNG-SP` configura el idioma de respuesta predeterminado en español (siempre que la página de ayuda o comando esté traducida).

### 1.3. El Sistema de Ayuda (HELP)
La página de ayuda es la fuente de información más actualizada y rápida disponible directamente en el sistema central de Amadeus.
*   **HE [Comando/Tema]:** Abre la explicación y el concepto detrás de cualquier funcionalidad.
    *   *Ejemplo:* `HE SS` muestra la ayuda sobre el comando *Segment Sell* (venta de segmentos).
*   **HE/**: Si el sistema devuelve un error de transacción, escribir `HE/` inmediatamente después de recibir el error mostrará una descripción detallada de lo que causó la falla y cómo corregirla.
*   **HE SCROLLING (o HE MD, HE MU):** Ayuda sobre los comandos de desplazamiento vertical para navegar a través de pantallas con múltiples páginas de texto.

---

## CAPÍTULO 2: CODIFICACIÓN Y DECODIFICACIÓN

En el GDS, todos los aeropuertos, ciudades, aerolíneas, países y equipos de aeronaves se representan mediante códigos estandarizados por IATA. Memorizarlos es útil, pero saber buscarlos es imprescindible.

### 2.1. Ciudades y Aeropuertos
*   **DAN [Nombre de la ciudad]:** (Do All Name) Codifica el nombre de una ciudad o aeropuerto para obtener su código de tres letras.
    *   *Ejemplo:* `DAN MADRID` devuelve `MAD`.
*   **DAC [Código de 3 letras]:** (Do All Code) Decodifica un código de tres letras para conocer su nombre, país y huso horario.
    *   *Ejemplo:* `DAC MIA` devuelve `MIAMI, FL, USA`.

### 2.2. Aerolíneas y Compañías de Transporte
*   **DNA [Nombre de la aerolínea]:** Codifica una aerolínea.
*   **DNS [Código de aerolínea]:** Decodifica el código IATA de una aerolínea de 2 letras o 3 dígitos.
*   **DNC [Nombre de Rentadora/Código]:** Codifica o decodifica compañías arrendadoras de autos (ej. *AVIS* o *ZI*).
*   **DNH [Nombre de Cadena/Código]:** Codifica o decodifica cadenas hoteleras (ej. *HILTON* o *HH*).

### 2.3. Herramienta Calculadora Integrada
*   **DF [Operación]:** El comando `DF` funciona como una calculadora interna rápida dentro del sistema críptico.
    *   *Ejemplo:* `DF 1500 * 1.16` calcula tarifas con impuestos, o `DF 4500 P 10` (calcula el 10% de 4500).

---

## CAPÍTULO 3: CREACIÓN DE RESERVAS (EL PNR)

El **PNR** (*Passenger Name Record* o Registro de Nombre de Pasajero) es el expediente del viaje del pasajero. En Amadeus, para que un PNR se pueda guardar, debe cumplir con 5 elementos obligatorios básicos (conocidos tradicionalmente por el acrónimo **PRINT** o **SMART**).

### 3.1. Elementos Obligatorios del PNR
1.  **Name (Nombre - NM):** Registra los apellidos y nombres de los viajeros.
    *   *Comando:* `NM1[Apellido]/[Nombre] [Título]`
    *   *Ejemplo:* `NM1PEREZ/JUAN MR`
    *   *Casos especiales:* Niños `(CHD)` o infantes/bebés sin asiento `(INF)`. *Ejemplo:* `NM1GOMEZ/PEDRO(CHD)` o `NM1GOMEZ/ANA(INF)`.
2.  **Itinerary (Itinerario - SS):** Es la venta de los vuelos.
    *   Primero se busca disponibilidad con `AN` (Availability Neutral). *Ejemplo:* `AN20MAYBUEMAD` (Disponibilidad neutral de Buenos Aires a Madrid para el 20 de mayo).
    *   Luego se reserva el segmento deseado con `SS` (Segment Sell).
    *   *Sintaxis:* `SS[Cantidad de asientos][Clase de reserva][Fila de la pantalla]`
    *   *Ejemplo:* `SS1Y3` (Vende 1 espacio en clase Y de la línea 3 de la disponibilidad de vuelos desplegada).
3.  **Phone (Contacto - AP):** Información para contactar al pasajero o a la agencia.
    *   *Comando:* `AP [Contacto]`
    *   *Ejemplo:* `AP BUE 555-1234 - H` (Teléfono de casa/Home).
    *   *Email:* `APE-JUAN.PEREZ@EMAIL.COM` (Introduce el correo electrónico para el envío automático de itinerarios).
4.  **Ticketing (Límite de Emisión - TK):** Define la fecha de caducidad para emitir los boletos o el estado de confirmación.
    *   *Comando:* `TKTL[Fecha]/[Hora]` o `TKOK` si los boletos ya están emitidos.
    *   *Ejemplo:* `TKTL15SEP/1800` (El PNR se cancelará automáticamente si no se emite antes del 15 de septiembre a las 18:00).
5.  **Received From (Recibido de - RF):** Firma del emisor para responsabilizar los cambios en la transacción.
    *   *Comando:* `RF[Nombre de la persona]`
    *   *Ejemplo:* `RFSR. GOMEZ` (Recibido de parte del Sr. Gómez).

### 3.2. Comandos para Finalizar y Mostrar la Reserva
*   **ET (End Transaction):** Guarda los datos ingresados, cierra el PNR y libera los recursos. Envía la reserva a las aerolíneas involucradas.
*   **ER (End and Retrieve):** Guarda la reserva, la cierra y vuelve a mostrar el PNR final en pantalla con su localizador de 6 caracteres alfanuméricos.
*   **IG (Ignore):** Cancela los cambios que se hayan realizado en la sesión actual de edición sin afectar el PNR guardado en la base de datos.
*   **RT [Localizador]:** Recupera un PNR específico de la base de datos.
    *   *Ejemplo:* `RT AB12CD`
*   **RT/[Apellido]:** Recupera reservas buscando por el apellido del pasajero.

### 3.3. Modificaciones Avanzadas en el Itinerario
*   **SP (Split / Separar Pasajeros):** Si en un PNR de varios pasajeros, uno de ellos decide cambiar su itinerario o fecha, se debe "dividir" la reserva para no alterar el viaje de los demás.
    *   *Sintaxis:* `SP[Número del pasajero en la lista]`. *Ejemplo:* `SP2`.
    *   Posteriormente se debe firmar `RF`, archiva el PNR del pasajero separado con `EF` (End File), y finalmente realizar el cierre `ET` del PNR original.
*   **RRN (Repetir Reserva Nueva):** Permite duplicar un PNR existente con el mismo itinerario pero para diferentes pasajeros.

---

## CAPÍTULO 4: TARIFACIÓN, COTIZACIÓN Y REGISTRO DE TARIFAS (TST)

Una vez reservado el itinerario, se debe proceder a calcular el precio exacto del viaje. Este cálculo genera un registro de tarifa virtual llamado **TST** (*Transitional Stored Ticket*).

### 4.1. Despliegue de Tarifas (Sin Reserva Previa)
*   **FQD (Fare Quote Display):** Despliega las tarifas públicas publicadas por las aerolíneas entre dos ciudades.
    *   *Ejemplo:* `FQDBUEMAD`
    *   *Filtros:* `FQDBUEMAD/AIB` (Filtra solo tarifas de Iberia - IB) o `FQDBUEMAD/D15OCT` (Tarifas para viajar el 15 de octubre).

### 4.2. Comandos de Cotización (Con Reserva en Pantalla)
Estos comandos calculan las tarifas aplicables al itinerario que se tiene en el área de trabajo activa:

*   **FXX (Cotización Informativa):** Calcula el precio del itinerario tal como está reservado actualmente, pero **NO** guarda la tarifa.
    *   *Uso:* Excelente para dar presupuestos rápidos al cliente sin alterar el estado de emisión del PNR.
*   **FXP (Cotización Confirmada):** Calcula el precio actual y **SÍ guarda el TST** en el PNR. Es un paso indispensable para la emisión.
*   **FXB (Best Buy - Mejor Compra):** El sistema busca de manera inteligente si existe una clase de reserva disponible más barata en los mismos vuelos. Si la encuentra, **realiza un rebooking automático** (cambia la clase en el itinerario) y genera y almacena el nuevo TST económico.
*   **FXR (Best Buy Informativo):** Similar a `FXB`, pero **NO** guarda el TST de manera automática (solo informa de la clase y el precio más bajo).

### 4.3. Reglas y Notas Tarifarias
Antes de que el pasajero pague, es mandatorio informarle sobre las penalizaciones por cambios y devoluciones.
*   **FQN [Línea del FQD o del TST]:** Muestra las regulaciones de la tarifa.
    *   *Ejemplo:* `FQN1` (Despliega las reglas del componente de tarifa 1).
    *   *Sub-categorías clave:* Se pueden consultar directamente con palabras clave como `PE` (*Penalties* / Penalidades), `AP` (*Advance Purchase* / Compra anticipada) o `MX` (*Maximum Stay* / Estadía máxima).

### 4.4. Visualización y Edición del TST
*   **TQT:** Comando que despliega la máscara del TST almacenado en el PNR para revisar sus impuestos, base de tarifa y desglose de precios.
*   **TTC / TTI:** Permite abrir y actualizar manualmente un TST cuando la cotización automática no cubre combinaciones complejas.
    *   *Ejemplo:* `TTU/T1/S2-4` (Actualiza del segmento 2 al 4 en el TST número 1).

---

## CAPÍTULO 5: PROCESO DE EMISIÓN DE BILLETES (TICKETING)

Para que el TST almacenado se convierta en un boleto electrónico real con cupones de vuelo listos para el check-in, se debe emitir.

### 5.1. Carga de Elementos Financieros
Antes de emitir, se deben ingresar tres elementos clave en el PNR:
1.  **Forma de Pago (FP):**
    *   Efectivo: `FPCASH`
    *   Tarjeta de crédito: `FPCC[Código TC][Número]/[Vencimiento]`. *Ejemplo:* `FPCCVI4111111111111111/1229`.
2.  **Comisión de la Agencia (FM):**
    *   *Ejemplo:* `FM0` (0% de comisión) o `FM7` (7% de comisión).
3.  **Línea Aérea Validadora (FV):** Establece con qué placa se va a cobrar el boleto.
    *   *Ejemplo:* `FV IB` (Validadora de Iberia) o `FV AA` (Validadora de American Airlines).

### 5.2. Comando de Emisión
*   **TTP/ET:** Ejecuta la emisión física del billete electrónico (*E-Ticket*). El sistema genera un número de boleto electrónico de 13 dígitos.
*   **TTP/RT:** Emite el boleto y despliega el PNR actualizado de inmediato.

### 5.3. Post-Emisión y Control Financiero
*   **TWD (Ticket Work Display):** Muestra el cupón electrónico con su estado actual (`OK` para viajar, `VOID` para anulado, `USED` para usado).
    *   *Ejemplo:* `TWD/TKT5071234567890` (Consulta un boleto por su número).
*   **TRDC:** Comando para **ANULAR** (Void) un boleto emitido el mismo día (antes del cierre de ventas). El estado del boleto cambiará a "V" y no se realizará el cargo financiero.
*   **ITR:** Permite imprimir o generar el recibo de itinerario legible para el pasajero.
*   **TJQ:** Genera un listado (Query) de todas las transacciones de ventas y boletos emitidos en el día por el agente o por la oficina.
*   **TJD:** Muestra un resumen consolidado de las ventas del día, desglosado por formas de pago (efectivo vs. tarjetas de crédito).

---

## CAPÍTULO 6: REEMISIONES Y REVALIDACIONES (AMADEUS TICKET CHANGER - ATC)

Cuando un pasajero solicita un cambio de fecha, ruta o vuelo en un boleto ya emitido, se debe realizar un proceso de **Reemisión** (emisión de un nuevo boleto cobrando penalidad y/o diferencia de tarifa) o **Revalidación** (actualización digital del billete original sin costo adicional).

**Amadeus Ticket Changer (ATC)** automatiza este proceso calculando automáticamente la penalización por cambio estipulada en la Categoría 31 (*Voluntary Changes*) de la tarifa original.

### 6.1. Procedimiento de Reemisión con ATC
1.  **Modificar el itinerario:** Cancelar con `XE` el segmento antiguo y reservar el nuevo vuelo con `SS`. (Es fundamental no dar *ET* todavía).
2.  **Lanzar la cotización automática:**
    *   `FXQ`: Cotiza el cambio respetando la clase actual y **crea automáticamente el TST** de reemisión y la máscara MCO si hay penalidades o saldos.
    *   `FXO`: Cotiza el cambio buscando la tarifa más barata disponible (Best Buy) y crea los elementos del PNR correspondientes.
    *   `FXF`: Cotización de reemisión netamente **informativa** (no crea TST).
3.  **Completar elementos financieros:** Registrar las nuevas formas de pago para la diferencia de tarifa o penalización cobrada.
4.  **Emitir:** Ejecutar `TTP/ET` para emitir el nuevo boleto que reemplazará al original. El nuevo boleto estará conectado con el antiguo en el campo **FO** (Form of Original Issue).

### 6.2. Tipos de Resultados en Reemisiones
*   **Even Exchange:** El valor del nuevo boleto es exactamente igual al original. No se cobra diferencia, pero se requiere reemitir un nuevo documento.
*   **Additional Collection (ADC):** La nueva tarifa es más cara o incluye cargos adicionales. Se debe cobrar la diferencia de tarifa y de tasas.
*   **Residual Value (RV):** El boleto nuevo es más económico. El sistema genera un saldo residual a favor del cliente mediante un MCO (ahora EMD) reembolsable o para futuros viajes.

---

## CAPÍTULO 7: SERVICIOS NO AÉREOS (AUTOS Y HOTELES)

Amadeus permite integrar elementos terrestres en el mismo itinerario del PNR para ofrecer servicios de viaje completos.

### 7.1. Alquiler de Autos (Amadeus Cars)
*   **CA [Ciudad][Fechas]:** Despliega la disponibilidad de vehículos.
    *   *Ejemplo:* `CAMIA15DEC-20DEC/ARR-1000-1000` (Busca autos en Miami del 15 al 20 de diciembre de 10:00 AM a 10:00 AM).
*   **CS [Línea]:** Vende el auto seleccionado de la pantalla de disponibilidad.
    *   *Ejemplo:* `CS2` (Vende la opción 2).
*   **CPO [Proveedor][Ciudad]:** Muestra las políticas detalladas del proveedor de autos (seguros, cargos por combustible, edad mínima).

### 7.2. Reservas de Hoteles (Amadeus Hotels)
*   **HA [Ciudad][Fecha de entrada]-[Noches]:** Muestra la disponibilidad de hoteles.
    *   *Ejemplo:* `HACCS01APR-5` (Busca hoteles en Caracas del 1 de abril por 5 noches).
*   **HL [Ciudad]:** Muestra un listado general de hoteles en una ciudad determinada sin verificar disponibilidad de tarifas en tiempo real.
*   **HF [Código de hotel]:** (Hotel Features) Consulta las características, dirección, políticas de cancelación y servicios del hotel seleccionado.

---

## CAPÍTULO 8: GESTIÓN DE PERFILES Y ADMINISTRACIÓN (AIMO)

Para agencias medianas y grandes, la automatización y la integración con sistemas contables se realiza a través de perfiles de clientes y herramientas de Mid Office.

### 8.1. Perfiles de Amadeus (Profiles)
Los perfiles evitan tener que escribir manualmente la información fiscal, de contacto o preferencias del viajero recurrente cada vez.
*   **PM:** Inicia el módulo de perfiles.
*   **PC/-1:** Crea un perfil de viajero a partir de los datos existentes en un PNR activo.
*   **PDN/-[Apellido]:** Busca un perfil de viajero existente por su apellido.
*   **PBN/[Nombre Empresa]:** Busca un perfil de empresa o corporativo.
*   **PT:** Transfiere los datos del perfil cargado directamente al PNR activo, llenando automáticamente nombres, correos, números de viajero frecuente y teléfonos.

### 8.2. Amadeus Integrated Mid Office (AiMO)
AiMO es una plataforma de administración de back y mid office que unifica las operaciones.
*   **Carpetas de Reservas (Booking Folders):** Contenedores lógicos dentro de AiMO donde se asocia un PNR con sus respectivos elementos contables, facturas y cobros.
*   **Vincular Cliente a Elementos Financieros:** Es el paso mandatorio en AiMO para emitir facturas. Se seleccionan las casillas de los cargos generados y se hace clic en "Vincular Cliente" (Link Customer) para asociar el perfil fiscal que pagará el servicio.
*   **Gestión de Reglas de Honorarios (Fees):** Permite configurar el cobro automático de cargos de gestión de la agencia (por ejemplo, cobrar un cargo fijo de $25 por cada boleto emitido) mediante la creación de reglas en el módulo administrativo.

---

## CAPÍTULO 9: GESTIÓN DE COLAS (QUEUES) Y MENSAJERÍA

Las **Colas** son el sistema de buzones digitales integrados de Amadeus donde las aerolíneas envían notificaciones importantes (como cambios de horario de vuelos, cancelaciones, cancelaciones de espacio o confirmaciones de lista de espera).

### 9.1. Comandos de Gestión de Colas
*   **QT (Queue Total):** Muestra el número total de reservas pendientes de revisar en cada cola de la oficina.
*   **QS [Número de Cola]:** (Queue Start) Abre e inicia la revisión de reservas en una cola específica.
    *   *Ejemplo:* `QS8` (Inicia la revisión de la cola 8, destinada típicamente a cambios de itinerario).
*   **QE [Número de Cola]:** (Queue End) Envía la reserva activa en pantalla a una cola para que otro agente o sucursal la revise.
    *   *Ejemplo:* `QE0` (Envía a la cola 0 de la propia oficina).
    *   *Sintaxis inter-oficina:* `QE/BUE1A0900/0` (Envía a la cola 0 de otra sucursal).

### 9.2. Mensajería Directa
*   Amadeus permite enviar mensajes de texto libre a otras terminales del sistema escribiendo `QE/[Office ID]/97` (Cola de mensajes 97), seguido del texto libre y cerrando el mensaje con los caracteres `//`.

---

## CAPÍTULO 10: INFORMACIÓN ADICIONAL DE VIAJE (TIMATIC)

Antes de emitir o de que el pasajero aborde, la agencia debe garantizar que el pasajero cumple con las regulaciones de migración, pasaportes, visados y sanidad.

### 10.1. Métodos de Consulta de Timatic
1.  **Desde un PNR:** El sistema lee los segmentos aéreos reservados en pantalla y cruza la información de los países de origen, tránsito y destino automáticamente.
2.  **Modo Guiado:** Una serie de máscaras con campos en blanco donde el agente introduce datos específicos con el teclado.
3.  **Modo Experto:** Introducción manual de comandos crípticos completos.

### 10.2. Comandos en Modo Experto
*   **TIRULES:** Muestra el índice general de definiciones de migración.
*   **TINEWS:** Muestra las últimas actualizaciones de salud y aduanas a nivel mundial.
*   **TIRV/NA[Nacionalidad]/DE[Destino]/TR[Tránsito]:** Solicita información sobre visados.
    *   *Ejemplo:* `TIRV/NAUY/DEMZ/TRLON` (Solicita requisitos de Visa para un ciudadano uruguayo [NA UY] con destino a Mozambique [DE MZ] y tránsito en Londres [TR LON]).
*   **TIHEALTH:** Consulta rápida sobre requisitos de salud (como la obligatoriedad de la vacuna contra la Fiebre Amarilla).

---

## CAPÍTULO 11: LA REVOLUCIÓN TECNOLÓGICA (ACTUALIZACIONES 2024–2026)

El panorama de la distribución turística ha cambiado drásticamente entre 2024 y 2026. Amadeus se ha adaptado consolidándose como un agregador de contenido unificado.

### 11.1. Integración Total de Contenido (NDC, LCC y EDIFACT)
Hasta hace poco, los agentes debían cotizar tarifas tradicionales (EDIFACT) en el GDS y usar portales externos para aerolíneas de bajo costo (LCC) y tarifas especiales **NDC** (New Distribution Capability).
*   **All Fares & Módulo Gráfico:** Hoy, Amadeus Selling Platform Connect une todos los canales de contenido en un solo flujo de trabajo. Al buscar un vuelo, las tarifas de sistemas EDIFACT clásicos y las ofertas directas NDC de las aerolíneas se muestran juntas en una sola pantalla, permitiendo comparar precios y equipaje de forma homogénea.
*   **Smart PNR:** Permite integrar diferentes tipos de contenido en un mismo expediente contable y de viaje. Ya no hay duplicados ni procesos separados para el back office.

### 11.2. Servicing Gráfico de Boletos NDC
La emisión y el post-servicio de boletos NDC (que no utilizan boletos electrónicos tradicionales sino "Orders" u órdenes de servicio directas de la aerolínea) se realiza de forma visual:
*   **Modificaciones y Cancelaciones:** Selling Platform Connect soporta operaciones esenciales de post-venta para boletos NDC (anulaciones, cambios de fechas y reembolsos) directamente desde la interfaz gráfica de usuario (*Products Section*), eliminando el uso de comandos complejos de reemisión.
*   **Quality Monitor para NDC:** Se han integrado flujos de automatización para que las agencias puedan ejecutar reglas de calidad automática en las reservas que contienen segmentos NDC, asegurando que se cumplan las políticas de la empresa.

### 11.3. Mejoras en Hoteles Plus y Cars Plus
*   **Favorites & Filtros de Radio:** Los agentes pueden guardar hasta 10 hoteles favoritos para un acceso más rápido y usar un filtro de radio avanzado para buscar hospedaje cerca de puntos de interés específicos.
*   **Cars Plus "Copy to Clipboard":** Permite copiar instantáneamente al portapapeles la comparación de tarifas y condiciones de diferentes arrendadoras para enviársela de forma limpia y profesional al cliente por correo o chat.
*   **Cryptic Magic Tool:** Es la tecnología que traduce instantáneamente los comandos crípticos del teclado en interfaces visuales fáciles de usar, acelerando el entrenamiento de nuevos agentes mientras los agentes expertos mantienen su rapidez transaccional clásica.

---

## CAPÍTULO 12: RESUMEN DE ENTRADAS CRÍPTICAS ESENCIALES (DICCIONARIO RÁPIDO)

| Comando | Acción Principal | Categoría |
| :--- | :--- | :--- |
| **JI** | Iniciar sesión / Sign-in | Acceso |
| **JO** | Cerrar sesión / Sign-out | Acceso |
| **JD** | Desplegar áreas de trabajo activas | Acceso |
| **HE [tema]** | Solicitar ayuda interactiva | Ayuda |
| **DAN / DAC** | Codificar ciudad / Decodificar código | Codificación |
| **AN [fecha][origen][destino]** | Consultar disponibilidad aérea neutral | Reservas |
| **SS [pax][clase][línea]** | Vender asientos desde disponibilidad | Reservas |
| **NM1[apellido]/[nombre]** | Ingresar nombre de pasajero | Reservas |
| **AP [datos]** | Ingresar teléfono o contacto | Reservas |
| **TKTL [fecha]/[hora]** | Establecer tiempo límite de emisión | Reservas |
| **RF [nombre]** | Registrar firma / Recibido de | Reservas |
| **ET / ER** | Finalizar transacción / Finalizar y recuperar | Reservas |
| **RT [localizador]** | Recuperar reserva por localizador | Reservas |
| **FQD [ruta]** | Desplegar tarifas públicas de la ruta | Tarifas |
| **FXX** | Cotización informativa aérea (sin TST) | Tarifas |
| **FXP** | Cotizar reserva y crear registro TST | Tarifas |
| **FXB** | Cotizar la tarifa más baja y rebook automático | Tarifas |
| **FQN** | Mostrar notas y regulaciones de tarifa | Tarifas |
| **FPCASH** | Registrar forma de pago efectivo | Ticketing |
| **FM0** | Registrar comisión del 0% | Ticketing |
| **TTP/ET** | Emitir boletos electrónicos | Ticketing |
| **TRDC** | Anular boleto (Void) el mismo día de emisión | Ticketing |
| **TWD** | Desplegar boleto electrónico en pantalla | Ticketing |
| **TJQ** | Desplegar reporte de ventas diario | Contabilidad |
| **FXQ** | Cotizar reemisión automática con ATC (con TST) | Reemisiones |
| **QS [cola]** | Iniciar trabajo en cola específica | Colas |
| **QE [cola]** | Enviar PNR a cola | Colas |
| **TIRV/...** | Solicitar información de Visas en Timatic | Timatic |
