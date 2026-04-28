
# Manual Funcional y de Negocios - TravelHub

## 1. Introducción: ¿Qué es TravelHub?
**TravelHub** es el sistema operativo inteligente diseñado específicamente para la Agencia de Viajes moderna. A diferencia de los sistemas administrativos genéricos, TravelHub entiende el negocio del turismo: conoce de boletos aéreos, de GDS (Sabre/Amadeus/Kiu), de tasas aeroportuarias y de la estricta normativa fiscal venezolana.

Su filosofía es **"Cero Clics"**: Automatizar todo lo que es repetitivo para que el Agente de Viajes se dedique a vender, no a transcribir datos.

---

## 2. Para el Agente de Viajes: "Vende más, transcribe menos"

### ✈️ Importación Automática de Boletos (El "Robot")
Ya no necesitas transcribir manualmente los datos de un boleto al sistema.
- **Cómo funciona:** Simplemente envías (o reenvías) el boleto en PDF o el correo del GDS a `boletos@travelinkeo.com`.
- **Lo que hace el sistema:** 
    1.  Detecta el correo automáticamente en segundos.
    2.  Lee el PDF usando Inteligencia Artificial (no importa si es Sabre, Amadeus o un PDF escaneado).
    3.  Crea la Venta, crea el Cliente (si es nuevo) y registra el Boleto.
    4.  **¡Notifica al Agente!** Te llega un WhatsApp avisando que el boleto ya está cargado.

### 📱 Notificaciones Inteligentes
El sistema mantiene informado al equipo sin esfuerzo:
- **WhatsApp Automático:** Al procesar un boleto, envía un mensaje con un enlace directo al PDF del boleto (con tu logo y colores), listo para reenviar al pasajero.
- **Corrector de Errores:** Si el boleto tiene un error (fecha pasada, monto cero), el sistema avisa para corregirlo antes de facturar.

### 🪪 Escaneo de Pasaportes (IA)
Olvídate de teclear nombres raros o números de pasaporte eternos.
- **Función:** Sube una foto o PDF del pasaporte del cliente.
- **Resultado:** La IA extrae la foto, nombres, apellidos, fechas y nacionalidad, y llena la ficha del cliente por ti.

---

## 3. Para el Gerente / Dueño: "Control Total"

### 📊 Dashboard de Ventas en Tiempo Real
Toma decisiones con datos, no con intuición.
- Visualiza cuánto se ha vendido hoy, esta semana o este mes.
- Ranking de:
    - Aerolíneas más vendidas.
    - Mejores Clientes Corporativos.
    - Agentes con mayor rendimiento.

### 🛡️ Centralización de la Data
- **Base de Datos de Clientes (CRM):** Todos los pasajeros, sus preferencias, pasaportes y boletos históricos están en un solo lugar. Si un agente se va, la información se queda en la empresa.
- **Auditoría:** El sistema guarda un registro de quién cargó cada boleto, quién lo modificó y cuándo se emitió la factura.

---

## 4. Para el Contador / Administrador: "Paz Mental Fiscal"

### 🧾 La "Doble Facturación" Automática (Venezuela)
TravelHub resuelve el dolor de cabeza contable más grande de las agencias: cómo facturar un boleto según la norma.
Al procesar una venta, el sistema genera **dos registros automáticamente**:
1.  **Factura a Terceros (Boleto):** Refleja el costo del boleto que se paga a la aerolínea (No sujeto a IVA propio, ingreso de terceros).
2.  **Factura de Fee (Comisión):** Refleja la ganancia de la agencia (Sujeto a IVA e IGTF).
*El contador recibe los reportes listos y separados, sin tener que calcular manualmente qué parte es ingreso y qué parte es costo.*

### 📄 Reportes Listos para Declarar
- **Libro de Ventas:** Formato estándar compatible con las exigencias del SENIAT.
- **Reporte de Liquidación (BSP):** Muestra cuánto se le debe pagar a cada aerolínea o consolidador, descontando las comisiones ya cobradas.
- **Cuentas por Cobrar:** Control de qué clientes corporativos deben facturas y antigüedad de la deuda.

---

## 5. Herramientas de Marketing (Bonus)

### 🎨 Generador de Contenido para Redes
- **Post Maker:** Crea una imagen para Instagram Stories de un Hotel o Paquete con un solo clic, aplicando automáticamente el logo de la agencia, los precios y un diseño profesional.
- **Copywriter IA:** Redacta los textos (captions) para las redes sociales usando Inteligencia Artificial, diseñados para "vender la experiencia".

---

## Resumen del Ecosistema

| Característica | Beneficio Principal |
| :--- | :--- |
| **Robot de Correos** | Ahorra 15-20 min de transcripción por boleto. |
| **IA de Pasaportes** | Elimina errores de tipeo en nombres y documentos. |
| **Doble Facturación** | Garantiza cumplimiento fiscal sin trabajo manual. |
| **Dashboard** | Visibilidad financiera inmediata. |
| **Nube (Cloudinary)** | Acceso a los boletos desde cualquier lugar y dispositivo. |

*TravelHub no es solo un sistema administrativo, es un empleado digital que trabaja 24/7.*
