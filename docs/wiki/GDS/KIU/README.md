# 🥝 Oráculo de Comandos KIU SYSTEM
> **El GDS de Latinoamérica.** Usado por Avior, Aserca, Conviasa, Estelar, Laser y más de 3,600 agencias en la región. Optimizado para aerolíneas low-cost y regionales.

---

## 📋 0. Gestión del PNR en KIU

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Añadir Nombre (Adulto)** | `-[Apellido]/[Nombre]` | `-PEREZ/JUAN` |
| **Añadir Infante** | `-[Apellido]/[Nombre](INF/[Apellido]/[Nombre]/[FechaNac])` | `-PEREZ/ANA(INF/PEREZ/CARLOS/15JAN24)` |
| **Ver PNR Completo** | `*A` | Muestra todos los elementos del PNR. |
| **Ver solo Itinerario** | `*I` | Solo los segmentos de vuelo. |
| **Ver Nombres** | `*N` | Lista de pasajeros. |
| **Guardar y Cerrar** | `E` | End: Genera el localizador y cierra. |
| **Guardar y Recuperar** | `ER` | End and Retrieve: Guarda y muestra el PNR. |
| **Ignorar Cambios** | `I` | Ignora toda la transacción actual. |
| **Recuperar PNR** | `*[Localizador]` | `*ABCDEF` |
| **Recuperar por Apellido** | `*-[Apellido]` | `*-PEREZ` |
| **Añadir Teléfono** | `9[Ciudad][Tel]-[Tipo]` | `9CCS+58 212 5551234-A` (A=Agencia) |
| **Received From (RF)** | `6[Nombre]` | `6MARIA` — **Obligatorio antes de E o ER** |
| **Agregar Observación** | `5[Texto libre]` | `5PAGO POR TRANSFERENCIA MERCANTIL` |

---

## ✈️ 1. Reservas de Vuelos (Air)
*KIU comparte arquitectura de comandos con Sabre por su origen tecnológico común.*

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Disponibilidad** | `D[Fecha][Origen][Destino]` | `D20OCTCCSMIA` (CCS → MIA, 20 Oct) |
| **Disponibilidad por Aerolínea** | `D[Fecha][Orig][Dest][AL]` | `D20OCTCCSMIAQL` (solo Laser) |
| **Vender Asiento** | `N[Cant][Clase][Línea]` | `N2Y1` (2 asientos clase Y, línea 1) |
| **Ver PNR Completo** | `*A` | Muestra el PNR con itinerario. |
| **Ver solo Itinerario** | `*I` | Segmentos de vuelo del PNR. |
| **Cancelar Segmento** | `X[Seg]` | `X2` — Cancela el segmento 2. |
| **Día siguiente en disponibilidad** | `MD` | Avanza un día en la pantalla. |
| **Asignar Asiento** | `4G[Fila][Letra]/[Pasajero]/S[Seg]` | `4G12A/1.1/S1` |
| **Cotizar disponibilidad** | `WS` | Muestra tarifas del vuelo seleccionado. |
| **Cerrar y Guardar PNR** | `E` | End Transaction — genera el localizador. |

**Aerolíneas Regionales en KIU (códigos IATA):**

| Código | Aerolínea | País |
| :--- | :--- | :--- |
| `VH` | Avior Airlines | Venezuela |
| `V0` | Conviasa | Venezuela |
| `QL` | Laser Airlines | Venezuela |
| `ES` | Estelar Latinoamérica | Venezuela |
| `R7` | Aserca Airlines | Venezuela |
| `9V` | Avior Regional | Venezuela |
| `5Z` | Cemair | Sudáfrica |
| `P6` | Pascan Aviation | Canadá |

---

## 🛂 2. Formatos Especiales (APIS, DOCS, FOID)
KIU hereda los formatos de documentación de Sabre con algunas variaciones regionales.

### 3DOCS — Pasaporte / APIS Internacional
```
3DOCS[Aerolínea]/P/[PaísEmisor]/[NumPasaporte]/[Nacionalidad]/[FechaNac]/[Género]/[VencPasaporte]/[Apellidos]/[Nombres]-[Pasajero]
```
**Ejemplo:**
```
3DOCSV0/P/VEN/A12345678/VEN/15JUL85/M/20OCT28/PEREZ MENDOZA/JUAN CARLOS-1.1
```

| Aerolínea | Código | 3DOCS Ejemplo |
| :--- | :--- | :--- |
| Conviasa | `V0` | `3DOCSV0/P/VEN/...` |
| Avior | `VH` | `3DOCSVH/P/VEN/...` |
| Laser | `QL` | `3DOCSQL/P/VEN/...` |
| Estelar | `ES` | `3DOCSES/P/VEN/...` |

### 3FOID — Forma de Identificación
Esencial para vuelos domésticos e internacionales en Venezuela.

* **Cédula Venezolana (V):** `3FOID/NIV[Numero]-[Pasajero]` ➔ `3FOID/NIV24322251-1.1`
* **Cédula Extranjero (E):** `3FOID/NIE[Numero]-[Pasajero]` ➔ `3FOID/NIE12345678-1.1`
* **Pasaporte:** `3FOID/PP[Pais][Numero]-[Pasajero]` ➔ `3FOID/PPVEN12345678-1.1`
* **Pasaporte sin país:** `3FOID/PPVEN[Numero]-[Pasajero]`

> **⚠️ Importante Venezuela:** Las aerolíneas domésticas exigen el prefijo V (venezolano) o E (extranjero) antes del número de cédula.

### DOCA — Dirección del Viajero (APIS destinos internacionales)
Requerido por USA, Canadá y algunos países europeos.
```
3DOCA[Aerolínea]/R/[PaísResidencia]/[CiudadResidencia]/[Dirección]/[CódPostal]/[País]-[Pax]
```
**Ejemplo:**
```
3DOCAV0/R/VEN/CARACAS/AV PRINCIPAL LOS PALOS GRANDES/1060/VEN-1.1
```

### 3OSI — Other Service Information
| Tipo | Comando | Ejemplo |
| :--- | :--- | :--- |
| **Pasajero VIP** | `3OSI [AL] VIP PAX-[Pax]` | `3OSI QL VIP PAX-1.1` (Laser) |
| **Mascota notificada** | `3OSI [AL] MASCOTA NOTIFICADA-[Pax]` | Solo informativo |
| **Pasajero con menor** | `3OSI [AL] PAX CON MENOR-[Pax]` | Aviso a la aerolínea |

### 3SSR — Special Service Request
| Código | Descripción | Comando KIU |
| :--- | :--- | :--- |
| `WCHR` | Silla de Ruedas (camina) | `3SSR WCHR [AL] NN1-1.1` |
| `WCHS` | Silla de Ruedas (escaleras) | `3SSR WCHS [AL] NN1-1.1` |
| `WCHC` | Silla de Ruedas (total) | `3SSR WCHC [AL] NN1-1.1` |
| `VGML` | Comida Vegetariana | `3SSR VGML [AL] NN1-1.1` |
| `KSML` | Comida Kosher | `3SSR KSML [AL] NN1-1.1` |
| `CHML` | Comida Infantil | `3SSR CHML [AL] NN1-1.1` |
| `BSCT` | Moisés/Cuna (Infante) | `3SSR BSCT [AL] NN1-1.1` |
| `UMNR` | Menor No Acompañado | `3SSR UMNR [AL] NN1/[Edad]Y-1.1` |
| `PETC` | Mascota en Cabina | `3SSR PETC [AL] NN1/[ESPECIE]/[N]KG-1.1` |
| `XBAG` | Equipaje Extra | `3SSR XBAG [AL] NN1/[N]KG-1.1` |

---

## 🏨 3. Módulos Terrestres en KIU
> **Nota:** KIU es predominantemente aéreo. Los módulos terrestres varían según la versión contratada por la agencia y los convenios con proveedores.

### Tarifas y Disponibilidad Aérea (Fare Display)
| Acción | Comando | Ejemplo |
| :--- | :--- | :--- |
| **Display de Tarifas** | `FQ[Origen][Destino][Fecha]` | `FQCCSMIA20OCT` |
| **Reglas Tarifarias** | `FQN[Línea]` | `FQN1` — Reglamento de tarifa línea 1. |
| **Tarifas de una aerolínea** | `FQ[Orig][Dest]/[AL]` | `FQCCSMIA/VH` — Solo Avior. |
| **Mínimas históricas** | `FQL[Orig][Dest]` | Tarifas más bajas por mes. |

---

## 💳 4. Pricing y Emisión (Ticketing)

| Acción | Comando | Ejemplo / Explicación |
| :--- | :--- | :--- |
| **Cotizar PNR básico** | `WP` | Cotiza según los segmentos actuales. |
| **Cotizar al más barato** | `WPNCB` | **Best Price:** Re-reserva en clase más económica. |
| **Guardar Cotización** | `PQ` | **Price Quote:** Guarda la máscara de tarifa. |
| **Ver Price Quote** | `*PQ` | Muestra el PQ guardado en el PNR. |
| **Añadir Comisión (%)** | `5-[N]C` | `5-10C` — 10% de comisión. |
| **Añadir Comisión (monto)** | `5-[N]A` | `5-50A` — $50 USD de comisión fija. |
| **Firma del Agente (RF)** | `6[Nombre]` | `6CARLOS` — **Obligatorio antes de emitir.** |
| **Emisión de Boleto** | `TKP` o `W‡` | Ejecuta la emisión del e-ticket. |
| **Emisión basada en PQ** | `W‡PQ[N]` | `W‡PQ1` — Emite el PQ número 1. |
| **Forma de Pago Efectivo** | `FPCASH` | Pago en efectivo al emitir. |
| **Forma de Pago Tarjeta** | `FPCC[Red][Nro]/[Exp]` | `FPCCVI4111111111111111/0127` |
| **Ver e-ticket emitido** | `*HTE` | Muestra el itinerario del boleto. |
| **Verificar estado ticket** | `WETR/[NumBoleto]` | Consulta el e-ticket en la aerolínea. |

---

## 🔄 5. Reemisiones y Revalidaciones

| Tipo | Acción | Comando / Proceso |
| :--- | :--- | :--- |
| **Revalidación (cambio menor)** | Cambio de fecha/vuelo sin diferencia de tarifa | Revalidar con comando de la aerolínea |
| **Reemisión (diferencia de tarifa)** | Nuevo boleto con cobro de penalidad | `WFR[NumBoleto]` → cambios → `W‡` |
| **Anulación (VOID)** | Solo el mismo día de emisión | `TRDC[NumBoleto]` |
| **Reembolso** | Requiere contactar a la aerolínea | Variable según tarifa |

> **Consejo KIU:** Las aerolíneas venezolanas (Avior, Laser, Conviasa) a menudo requieren autorización directa para reemisiones. Consulta siempre las reglas tarifarias con `FQN`.

---

## 📬 6. Colas (Queues)

| Acción | Comando | Explicación |
| :--- | :--- | :--- |
| **Ver colas activas** | `QC/` | Cuenta PNRs pendientes por cola. |
| **Entrar a una cola** | `Q/[N]` | `Q/9` — Cola de ticketing. |
| **Siguiente PNR** | `QN` | Avanza al siguiente en la cola. |
| **Remover de cola** | `QR` | Saca el PNR actual de la cola. |
| **Salir de la cola** | `QXI` | Sale sin alterar el PNR. |
| **Poner en cola pendiente** | `7TAW[Fecha]/` | `7TAW20OCT/` — PNR pendiente al 20 Oct. |
| **Administración de colas** | `QP/[Cola]/[N]` | Asigna PNR a cola específica. |

---

## 🔧 7. Comandos de Acceso y Utilidad

| Acción | Comando | Explicación |
| :--- | :--- | :--- |
| **Salir del área de trabajo** | `SO` | Sign Out: Sale del área activa. |
| **Salir de todas las áreas** | `SO*` | Cierra todas las sesiones activas. |
| **Info de aeropuerto** | `DAP[Código]` | `DAPCCS` — Info del aeropuerto CCS. |
| **Horario de vuelo** | `SN[AL][Vuelo][Fecha]` | `SNVH123 20OCT` — Detalles del vuelo. |
| **Equivalencia tarifaria** | `DC[Divisa1][Divisa2]` | `DCUSDVEF` — Conversión de moneda. |
| **Abrir nueva área** | `MD` o `MU` | Navegar entre áreas/pantallas. |
| **Anular e-ticket** | Ver proceso VOID | Mismo día: `TRDC[NumBoleto13dig]` |

---

## 🏷️ 8. Particularidades de KIU para Venezuela

### Regulación INAC (Instituto Nacional de Aviación Civil)
> Todos los pasajeros en vuelos domésticos venezolanos deben tener su cédula registrada en el 3FOID antes de la emisión. Las aerolíneas pueden rechazar el boleto sin este dato.

### Aerolíneas Nacionales — Rutas Frecuentes en KIU
| Ruta | Aerolínea Principal | Observación |
| :--- | :--- | :--- |
| CCS → PMV (Margarita) | Avior, Laser | Alta demanda, reservar con anticipación |
| CCS → MAR (Maracaibo) | Avior, Estelar | Vuelos frecuentes |
| CCS → BLA (Barcelona) | Avior regional | Hub de Avior |
| CCS → MIA (Miami) | Avior, Conviasa | Requiere APIS completo y DOCA |
| CCS → BOG (Bogotá) | Avianca, Conviasa | Doble FOID: VEN + Pasaporte |
| PMV → CCS | Laser, Avior | Alta ocupación en temporada |

### Emisión con Moneda Venezolana (Bs)
* En KIU, algunas aerolíneas venezolanas permiten emisión en bolívares al tipo de cambio del BCV.
* El comando de forma de pago en efectivo: `FPCASH` aplica en la moneda configurada en tu PCC.
* Para verificar la moneda activa de tu agencia: consultar con el administrador KIU de tu oficina.
