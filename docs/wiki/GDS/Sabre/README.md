# 🌌 Oráculo de Comandos SABRE
> **GDS líder mundial.** Base de conocimiento completa para agentes de viajes. Usa el buscador para encontrar cualquier comando al instante.

---

## 📋 0. Gestión del PNR (Passenger Name Record)
El PNR es el registro central de cada reserva. Dominar estos comandos es fundamental.

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Añadir Nombre (Adulto)** | `-[Apellido]/[Nombre]` | `-PEREZ/JUAN MR` |
| **Añadir Infante** | `-[Apellido]/[Nombre](INF/[Apellido]/[Nombre]/[FechaNac])` | `-PEREZ/ANA MRS(INF/PEREZ/CARLOS/15JAN24)` |
| **Ver PNR Completo** | `*A` | Muestra todos los campos del PNR. |
| **Ver Itinerario** | `*I` | Solo los segmentos de vuelo. |
| **Ver Nombres** | `*N` | Lista de pasajeros del PNR. |
| **Ver Boletos** | `*T` | Muestra el campo de ticketing. |
| **Ver Historial** | `*H` | Historial de cambios del PNR. |
| **Ver SSR/Servicios** | `*S` | Todos los elementos SSR del PNR. |
| **Recuperar PNR por Localizador** | `*ABCDEF` | `*GHHKLB` (6 caracteres del localizador). |
| **Recuperar por Apellido** | `*-PEREZ` | Muestra PNRs activos con ese apellido. |
| **Guardar (End)** | `E` | Guarda y sale del PNR. |
| **Guardar y Recuperar** | `ER` | End and Retrieve: Guarda y muestra el PNR. |
| **Ignorar cambios** | `I` | Descarta los cambios no guardados. |
| **Ignorar y Recuperar** | `IR` | Descarta cambios y vuelve a mostrar el PNR. |
| **Añadir Teléfono Agencia** | `9BOGOTAAGENCIA-A` | Formato: `9[Ciudad][DescripciónTel]-A` |
| **Añadir Teléfono Móvil Pax** | `9[Numero]-M-1.1` | `9+58 414 1234567-M-1.1` |
| **Agregar Observación** | `5[Texto]` | `5CLIENTE VIP - TRATO PREFERENCIAL` |
| **Received From (RF)** | `6[Nombre]` | `6JUAN` — Obligatorio antes de cerrar el PNR. |
| **Agregar Forma de Pago** | `FP[Tipo]` | `FPCASH` / `FPCC[Red][Nro]/[Exp]` |

---

## ✈️ 1. Reservas de Vuelos (Air)

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Disponibilidad básica** | `1[Fecha][Origen][Destino]` | `120OCTCCSMAD` (CCS → MAD, 20 Oct) |
| **Disponibilidad vuelta** | `1[Fecha][Origen][Destino]¥[Fecha][Regreso]` | `120OCTCCSMAD¥13NOVMADCCS` |
| **Vender Asiento** | `0[Clase][Cantidad][Línea]` | `0Y21` (2 asientos clase Y, línea 1) |
| **Vender + Especificar Aerolínea** | `0[Clase][Cantidad][Linea][Aerolínea]` | `0Y2 1AV` (Avianca) |
| **Cambiar Clase de un Segmento** | `3[Segmento]¤[Clase]` | `31¤M` (Cambia seg. 1 a clase M) |
| **Cancelar un Segmento** | `X[Segmento]` | `X2` (Cancela el segmento 2) |
| **Ver Disponibilidad día siguiente** | `MD` | Move Down: Avanza un día en disponibilidad. |
| **Ver Disponibilidad día anterior** | `MU` | Move Up: Retrocede un día. |
| **Seats Map (Mapa de Asientos)** | `WPMS[Segmento]` | `WPMS1` — Mapa de la cabina del seg. 1. |
| **Asignar Asiento Específico** | `4G[Fila][Letra]/[Pasajero]/S[Seg]` | `4G12A/1.1/S1` (Asiento 12A, Pax1, Seg1) |
| **Frecuent Flyer** | `FF[Aerolínea][Numero]-[Pax]` | `FFAV2NH69800-1.1` |

---

## 🛂 2. Formatos Especiales (APIS, DOCS, FOID)

### DOCS — Pasaporte Internacional (APIS)
```
3DOCS*/P/[PaísEmisor]/[NumPasaporte]/[Nacionalidad]/[FechaNac]/[Género]/[VencPasaporte]/[Apellidos]/[Nombres]-[Pax]
```
**Ejemplo:**
```
3DOCS*/P/VEN/A12345678/VEN/15JUL85/M/20OCT28/PEREZ MENDOZA/JUAN CARLOS-1.1
```

| Campo | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `P` | Tipo: Pasaporte | `P` / `N` (ID Nacional) |
| País Emisor | ISO 3 letras | `VEN`, `COL`, `USA` |
| Fecha Nacimiento | Formato DDMMMYY | `15JUL85` |
| Género | M/F | `M` = Masculino |
| Vencimiento | Fecha expiración doc. | `20OCT28` |

### FOID — Forma de Identificación
* **Cédula:** `3FOID/NI[Numero]-[Pax]` ➔ `3FOID/NI24322251-1.1`
* **Pasaporte:** `3FOID/PP[Pais][Numero]-[Pax]` ➔ `3FOID/PPVEN12345678-1.1`
* **Tarjeta de Crédito:** `3FOID/CC[Red][Numero]-[Pax]` ➔ `3FOID/CCVI4111111111111111-1.1`

### OSI — Other Service Information (Informativo)
| Tipo | Comando | Ejemplo |
| :--- | :--- | :--- |
| **Pasajero VIP** | `3OSI [AL] VIP PAX-[Pax]` | `3OSI AV VIP PAX-1.1` |
| **Pasajero con niños** | `3OSI [AL] PAX TRAVELING WITH CHILD` | `3OSI IB PAX TRAVELING WITH CHILD` |
| **Nombre difiere** | `3OSI [AL] NAME DIFFERS FROM ID` | Para alertar a la aerolínea |
| **Eliminar OSI** | `3[Linea]¤` | `31¤` — Borra la línea 1 de OSI |

### SSR — Special Service Request (Requiere confirmación)
| Código | Descripción | Comando |
| :--- | :--- | :--- |
| `WCHR` | Silla de Ruedas (puede caminar) | `3SSR WCHR [AL] NN1-1.1` |
| `WCHS` | Silla de Ruedas (sube escaleras) | `3SSR WCHS [AL] NN1-1.1` |
| `WCHC` | Silla de Ruedas (no puede moverse) | `3SSR WCHC [AL] NN1-1.1` |
| `VGML` | Comida Vegetariana | `3SSR VGML [AL] NN1-1.1` |
| `KSML` | Comida Kosher | `3SSR KSML [AL] NN1-1.1` |
| `DBML` | Comida Diabética | `3SSR DBML [AL] NN1-1.1` |
| `CHML` | Comida Infantil | `3SSR CHML [AL] NN1-1.1` |
| `BSCT` | Cuna/Moisés (Infante) | `3SSR BSCT [AL] NN1-1.1` |
| `UMNR` | Menor No Acompañado | `3SSR UMNR [AL] NN1/[Edad]-1.1` |
| `PETC` | Mascota en Cabina | `3SSR PETC [AL] NN1/[Especie]/[Peso]KG-1.1` |
| `BIKE` | Bicicleta como Equipaje | `3SSR BIKE [AL] NN1-1.1` |
| `XBAG` | Exceso de Equipaje | `3SSR XBAG [AL] NN1/[Peso]KG-1.1` |

---

## 🏨 3. Hoteles (Hotels)

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Búsqueda por Ciudad** | `HOT[Ciudad]/[FechaIn]-[FechaOut]` | `HOTMAD/20OCT-25OCT` |
| **Buscar con # Habitaciones** | `HOT[Ciudad]/[FechIn]-[FechaOut]/[N]` | `HOTMIA/20OCT-25OCT/2` (2 hab.) |
| **Disponibilidad Propiedad** | `HOD[Línea]` | `HOD1` — Tarifas del hotel línea 1 |
| **Reglas Tarifarias Hotel** | `HOD[Línea]R` | `HOD1R` — Condiciones de cancelación |
| **Vender Habitación** | `0H1[Tarifa]` | `0H1A1` — Reserva tarifa A1 |
| **Ver Reserva Hotel** | `*HOT` | Muestra el segmento de hotel del PNR |
| **Cancelar Hotel** | `XH[Segmento]` | `XH2` |

---

## 🚗 4. Vehículos (Cars)

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Disponibilidad** | `CQ[Ciudad]/[FechaIn]-[FechaOut]` | `CQMIA/20OCT-25OCT` |
| **Por Arrendadora** | `CQA[Arrendadora]/[Ciudad]/[Dates]` | `CQAZE/MIA/20OCT-25OCT` (ZE=Hertz) |
| **Vender Auto** | `0C[Línea]` | `0C1` |
| **Ver Reserva Auto** | `*CAR` | Muestra el segmento de auto del PNR |

**Códigos de Arrendadoras Frecuentes:**

| Código | Arrendadora | Código | Arrendadora |
| :--- | :--- | :--- | :--- |
| `ZE` | Hertz | `ZR` | Dollar |
| `AU` | Avis | `ET` | Enterprise |
| `ZI` | Avis International | `AL` | Alamo |
| `EP` | Europcar | `NU` | National |

---

## 💳 5. Tarifas (Fares) y Pricing

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Display Tarifas (FD)** | `FQ[Origen][Destino]` | `FQCCSMAD` — Tarifas publicadas CCS-MAD |
| **Cotizar PNR básico** | `WP` | Cotiza el itinerario tal como está. |
| **Cotizar al más barato** | `WPNCB` | Busca y re-reserva la clase más económica. |
| **Cotizar + Guardar (PQ)** | `PQ` | **Price Quote:** Guarda la tarifa en el PNR. |
| **Ver Price Quote** | `*PQ` | Muestra el PQ guardado. |
| **Añadir Comisión (%)** | `5-[N]C` | `5-10C` — 10% de comisión. |
| **Añadir Comisión (monto)** | `5-[N]A` | `5-50A` — $50 USD de comisión fija. |
| **Forma de Pago Efectivo** | `FPCASH` | Pago en efectivo. |
| **Forma de Pago Tarjeta** | `FPCC[Red][Nro]/[Exp]` | `FPCCVI4111111111111111/0126` |

---

## 🎫 6. Emisión de Boletos (Ticketing)

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Ticket al más barato y emitir** | `W‡PQ` | Emite basado en el Price Quote guardado. |
| **Emitir PQ específico** | `W‡PQ[N]` | `W‡PQ1` — Emite el PQ número 1. |
| **Emitir e-Ticket** | `W‡ET` | Emisión electrónica. |
| **Ver e-Ticket** | `*HTE` | Muestra el itinerario del e-ticket emitido. |
| **Fecha límite de ticketing** | `7TAW[Fecha]/` | `7TAW20OCT/` — Agrega TAW al PNR. |
| **Boleto en Queue** | `7TAW/` | Coloca en Queue 9 para emisión inmediata. |
| **Anular Boleto (VOID)** | `TRDC[NumBoleto]` | Solo válido el mismo día de emisión. |

---

## 🔄 7. Reemisiones (Ticket Exchange)

| Paso | Acción | Comando |
| :--- | :--- | :--- |
| **1** | Recuperar el PNR | `*[Localizador]` |
| **2** | Iniciar Exchange | `WFR[NumBoleto13dig]` |
| **3** | Modificar segmentos | Cancelar y re-reservar vuelos |
| **4** | Recotizar con penalidad | `WP` o `WPNCB` + añadir penalidad |
| **5** | Nuevo Price Quote | `PQ` |
| **6** | Emitir reemisión | `W‡PQ` |

> **⚠️ Nota:** Para boletos parcialmente usados, usar `WFR` con el número de segmento no usado. El sistema Exchange Manager (QREX) maneja reembolsos automáticos.

---

## 📬 8. Colas (Queues)

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Contar PNRs en colas** | `QC/` | Muestra cuántos PNRs hay en cada queue. |
| **Entrar a una cola** | `Q/[N]` | `Q/9` — Entra a la cola 9 (ticketing). |
| **Siguiente PNR en cola** | `QN` | Avanza al siguiente PNR de la cola. |
| **Remover PNR de cola** | `QR` | Saca el PNR actual de la cola. |
| **Salir de la cola** | `QXI` | Exit queue sin remover el PNR. |
| **Poner PNR en cola** | `7TAW[Fecha][N]/` | `7TAW20OCT9/` — Cola 9, venc. 20 Oct. |
| **Historial de colas** | `*QH` | Muestra en qué colas ha estado el PNR. |
| **Cola múltiple (varios PCC)** | `QP/[PCC1]/[N1]#[PCC2]/[N2]` | `QP/KB7399/1#WH5B132/1` |

> **Numeración estándar de Queues:** Q1-49 = Sistema Sabre | Q50-199 = Uso Agencia | Q200-511 = Agente disponible

---

## 🔧 9. Comandos de Utilidad y Ayuda

| Acción | Comando | Explicación |
| :--- | :--- | :--- |
| **Ayuda de un Comando** | `H-[Entrada]` | `H-0Y21` — Explica el comando. |
| **Ver Códigos SSR/OSI** | `N*/OSI SSR CODES` | Lista todos los códigos disponibles. |
| **Zona Horaria Ciudad** | `DCLCCS` | Información del aeropuerto de CCS. |
| **Tipo de Cambio** | `DC[Moneda1][Moneda2]` | `DCUSDVEF` — Tasa USD a VEF. |
| **Mínima Tarifa Aerolínea** | `FQ[Org][Dst]*[Aerolínea]` | `FQCCSMAD*AV` — Solo tarifas Avianca. |
| **Verificar e-ticket** | `WETR/[Num]` | Consulta el estado del e-ticket. |
| **Copia de Reserva (Duplicate)** | `DUP[Localizador]` | Duplica un PNR existente. |
