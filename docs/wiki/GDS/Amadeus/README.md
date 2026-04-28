# 🌐 Oráculo de Comandos AMADEUS
> **GDS europeo líder.** Base de conocimiento completa. El sistema más usado en Europa y Latinoamérica para agencias internacionales.

---

## 📋 0. Gestión del PNR en Amadeus

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Añadir Nombre (Adulto)** | `NM1[Apellido]/[Nombre][Título]` | `NM1PEREZ/JUANMR` |
| **Añadir Infante** | `NM1[Apellido]/[Nombre]MSTR(INFPEREZ/CARLOS/15JAN24)` | Ver formato oficial |
| **Ver PNR Completo** | `RT` | Retrieve: Muestra todo el PNR activo. |
| **Ver Itinerario** | `RTS` | Muestra solo los segmentos del PNR. |
| **Ver Nombres** | `RTN` | Solo los pasajeros del PNR. |
| **Recuperar por Localizador** | `RT[Localizador]` | `RTABCDEF` |
| **Recuperar por Apellido** | `RT[Apellido]/[Nombre]` | `RTPEREZ/JUAN` |
| **Ver Historial** | `RFA RH` | Historial completo de cambios del PNR. |
| **Guardar (End)** | `ET` | End Transaction: Guarda y cierra. |
| **Guardar y Recuperar** | `ER` | End and Retrieve: Guarda y muestra. |
| **Ignorar Cambios** | `IG` | Ignore: Descarta todos los cambios. |
| **Añadir Teléfono** | `AP[Ciudad] [Número]` | `APBOGOTá-JUAN 3001234567-M` |
| **Añadir Email** | `APE-[Email]/P[N]` | `APE-VIAJERO@EMAIL.COM/P1` |
| **Añadir Observación** | `RM [Texto]` | `RM CLIENTE VIP` |
| **Received From** | `RF[Nombre]` | `RFJUAN` — Obligatorio antes de guardar. |
| **Forma de Pago** | `FP [Tipo]` | `FP CASH` / `FP CC...` |

---

## ✈️ 1. Reservas de Vuelos (Air)

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Disponibilidad básica** | `AN[Fecha][Origen][Destino]` | `AN20OCTCCSMAD` |
| **Disponibilidad con Aerolínea** | `AN[Fecha][Origen][Destino][AL]` | `AN20OCTCCSMADAV` (solo Avianca) |
| **Disponibilidad vuelta** | `AN[FI][Orig][Dest][AL][FV][Dest][Orig]` | Continuación de la disponibilidad |
| **Vender Asiento** | `SS[Cant][Clase][Línea]` | `SS2Y1` (2 asientos clase Y, línea 1) |
| **Vender + Segmento Largo** | `SS[N][Clase][Línea]/NN[N]` | Forced sell con petición |
| **Desplegar Itinerario** | `RT` | Retrieve completo del PNR. |
| **Cancelar Segmento** | `XE[Segmento]` | `XE2` — Cancela el segmento 2. |
| **Día siguiente** | `MD` | More Days: Avanza en disponibilidad. |
| **Mapa de Asientos** | `SM[Vuelo][Fecha]` | `SMAV 46 20OCT` |
| **Asignar Asiento** | `ST[Fila][Letra]/P[N]/S[Seg]` | `ST12A/P1/S1` |
| **Frecuent Flyer** | `SR FQTV [AL] HK1-[AL][Nro]/P[N]` | `SR FQTV AV HK1-AV123456/P1` |

---

## 🛂 2. Formatos Especiales (APIS, DOCS, FOID)

### SRDOCS — Pasaporte / APIS
```
SRDOCS [AL] HK1-P-[PaísEmisor]-[NumPasaporte]-[Nacionalidad]-[FechaNac]-[Género]-[Vencimiento]-[Apellidos]-[Nombres]/P[N]
```
**Ejemplo:**
```
SRDOCS AV HK1-P-VEN-A12345678-VEN-15JUL85-M-20OCT28-PEREZ MENDOZA-JUAN CARLOS/P1
```

| Campo | Descripción | Código |
| :--- | :--- | :--- |
| `P` | Tipo de documento | `P` = Pasaporte, `N` = ID Nacional |
| País Emisor | ISO 3 letras | `VEN`, `COL`, `USA`, `ESP` |
| Fecha Nacimiento | DDMMMYY | `15JUL85` |
| Género | Un carácter | `M` = Masculino, `F` = Femenino |
| Vencimiento | DDMMMYY | `20OCT28` |

### SRFOID — Forma de Identificación
* **Cédula Nacional:** `SRFOID [AL] HK1-NI[Numero]/P[N]` ➔ `SRFOID AV HK1-NI24322251/P1`
* **Pasaporte:** `SRFOID [AL] HK1-PP[Pais][Numero]/P[N]` ➔ `SRFOID AV HK1-PPVEN12345678/P1`
* **Tarjeta de Crédito:** `SRFOID [AL] HK1-CC[Red][Numero]/P[N]`

### OS — Other Service Information (Informativo)
| Tipo | Comando | Ejemplo |
| :--- | :--- | :--- |
| **Pasajero VIP** | `OS [AL] VIP PAX/P[N]` | `OS AV VIP PAX/P1` |
| **Pasajero VIP con nombre** | `OS [AL] VIP PAX IS [Nombre]/P[N]` | `OS IB VIP PAX IS SENADOR GOMEZ/P1` |
| **Con menor** | `OS [AL] PAX TRAVELING WITH CHILD` | Informativo, sin confirmación |

### SR — Special Service Request (Requiere confirmación)
| Código | Descripción | Comando Amadeus |
| :--- | :--- | :--- |
| `WCHR` | Silla de Ruedas (camina) | `SR WCHR [AL] HK1/P[N]` |
| `WCHS` | Silla de Ruedas (escaleras) | `SR WCHS [AL] HK1/P[N]` |
| `WCHC` | Silla de Ruedas (inmóvil) | `SR WCHC [AL] HK1/P[N]` |
| `VGML` | Comida Vegetariana | `SR VGML [AL] HK1/P[N]` |
| `KSML` | Comida Kosher | `SR KSML [AL] HK1/P[N]` |
| `DBML` | Comida Diabética | `SR DBML [AL] HK1/P[N]` |
| `CHML` | Comida Infantil | `SR CHML [AL] HK1/P[N]` |
| `BSCT` | Cuna para Infante | `SR BSCT [AL] HK1/P[N]` |
| `UMNR` | Menor No Acompañado | `SR UMNR [AL] HK1/[Edad]Y/P[N]` |
| `PETC` | Mascota en Cabina | `SR PETC [AL] HK1/[ESPECIE]/[N]KG/P[N]` |
| `XBAG` | Equipaje Adicional | `SR XBAG [AL] HK1/[N]KG/P[N]` |

---

## 🏨 3. Hoteles (Hotels)

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Búsqueda por Ciudad** | `HA[Ciudad][FechaIn]-[FechaOut]` | `HAMAD20OCT-25OCT` |
| **Búsqueda por Nombre del Hotel** | `HAN[ComienzoNombre]/[Ciudad]` | `HANMELIAMAD` |
| **Disponibilidad Propiedad** | `HP[Línea]` | `HP1` — Tarifas del hotel línea 1 |
| **Reglas de Cancelación** | `HP[Línea]R` | `HP1R` — Política de cancelación |
| **Vender Habitación** | `HS[Línea]` | `HS1` — Reserva la tarifa línea 1 |
| **Ver Segmento Hotel en PNR** | `RT` | Se ve junto al itinerario de vuelo |
| **Cancelar Hotel** | `XE[Línea]` | `XE3` — Cancela el elemento 3 del PNR |

---

## 🚗 4. Vehículos (Cars)

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Disponibilidad** | `CA[Ciudad][FechaIn]-[FechaOut]` | `CAMIA20OCT-25OCT` |
| **Por Arrendadora Específica** | `CA[AL]/[Ciudad][Dates]` | `CAZE/MIA20OCT-25OCT` (ZE=Hertz) |
| **Vender Auto** | `CS[Línea]` | `CS1` — Reserva el vehículo línea 1 |

---

## 💳 5. Tarifas (Fares) y Pricing

| Acción | Comando | Descripción Expandida |
| :--- | :--- | :--- |
| **Display de Tarifas** | `FQ[Orig][Dest]` | `FQCCSMAD` — Tarifas publicadas |
| **Reglas de Tarifa** | `FQ[Orig][Dest]/R[Línea]` | `FQCCSMAD/R1` — Reglas tarifa línea 1 |
| **Cotizar Básico (sin guardar)** | `FXX` | Fx eXtended: informativo, no crea TST. |
| **Cotizar y Guardar (TST)** | `FXP` | **Price and Store:** Crea el TST. Recomendado. |
| **Cotizar al más barato** | `FXB` | **Best Buy:** Re-reserva en clase más barata. |
| **Lista de opciones más baratas** | `FXA` | Muestra alternativas económicas. |
| **Ver TST guardado** | `TQT` | Muestra el Transitional Stored Ticket. |
| **Añadir Comisión (%)** | `FM[N]` | `FM10` — 10% de comisión. |
| **Añadir Comisión (monto)** | `FMA[N]` | `FMA50` — $50 USD fijo de comisión. |
| **Cotizar por segmento** | `FXP/R,UP/S[N]-[N]` | `FXP/R,UP/S1-2` — Solo seg. 1 y 2. |

---

## 🎫 6. Emisión de Boletos (Ticketing)

| Acción | Comando | Explicación |
| :--- | :--- | :--- |
| **Emitir Boleto (básico)** | `TTP` | **Ticket To Print:** Emite el e-ticket. |
| **Emitir TST específico** | `TTP/T[N]` | `TTP/T1` — Emite el TST número 1. |
| **Emitir para Pax específico** | `TTP/P[N]` | `TTP/P1` — Solo el pasajero 1. |
| **Ver Boleto Emitido** | `TWD/TK-[NumBoleto]` | Consulta cualquier e-ticket. |
| **Anular Boleto (VOID)** | `TRDC[NumBoleto]` | Solo el mismo día de emisión. |
| **Fecha Límite de Ticketing** | `TKTL[Fecha]` | `TKTL20OCT` — Agrega límite al PNR. |

---

## 🔄 7. Reemisiones (Ticket Exchange / ATC)

| Paso | Acción | Comando |
| :--- | :--- | :--- |
| **1** | Ver boleto original | `TWD/TK-[NumBoleto]` |
| **2** | Verificar precio sin cambios | `FXF` — Informative reissue pricing |
| **3** | Rebooking y nuevo precio | `FXQ` — **Crea nuevo TST con diferencia** |
| **4** | Ver nuevos cargos (penalidad) | `TQM` — Ticket Quote Manager |
| **5** | Añadir pago de diferencia | `TMI/M[N]/FP-CC...` |
| **6** | Emitir reemisión + EMD penalidad | `TTP/TTM/M[N]/RT` |

> **⚠️ FXF** = Solo informativo (no hace cambios). **FXQ** = Confirma el exchange y guarda el nuevo TST.

---

## 📬 8. Colas (Queues)

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Ver colas activas** | `QC` | Cuenta de PNRs en cada cola. |
| **Entrar a una cola** | `QE[N]C[Categoría]` | `QE9C0` — Cola 9, categoría 0. |
| **Siguiente PNR** | `QN` | Avanza al siguiente PNR en la cola. |
| **Remover de cola** | `QR` | Saca el PNR actual de la cola y sale. |
| **Salir de cola** | `QEX` | Sale de la cola sin remover el PNR. |
| **Poner PNR en cola** | `TKTL[Fecha]` o `RF + ET` | El PNR queda en cola de ticketing. |

---

## 🔧 9. Comandos de Utilidad

| Acción | Comando | Descripción |
| :--- | :--- | :--- |
| **Info de Aeropuerto** | `DAP[Código]` | `DAPCCS` — Info Aeropuerto Simón Bolívar. |
| **Tipo de Cambio** | `DC[Divisa1][Divisa2]` | `DCUSDVEF` — Conversión USD a VEF. |
| **Ver Horarios de Vuelo** | `SN[AL][Vuelo][Fecha]` | `SNAV461 20OCT` — Detalles del vuelo. |
| **Disponibilidad Aerolínea** | `TN[AL][Num][Fecha]` | `TNAV461 20OCT` |
| **Espacio Disponible** | `SE[AL][Vuelo][Fecha]` | `SEAV461 20OCT/C` — Espacio clase C. |
| **Verificar e-ticket** | `TWD/ET-[NumBoleto]` | Estado del boleto electrónico. |
| **Duplicar PNR** | Requiere permisos de oficina | Consultar con supervisor. |
