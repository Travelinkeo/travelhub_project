// Script para probar los datos que envía el frontend
// Ejecutar con: node test_frontend_data.js

const sampleVentaData = {
  "cliente": 6,
  "moneda": 4,
  "descripcion_general": "Reserva Hotel Marriott desde Frontend",
  "tipo_venta": "B2C",
  "canal_origen": "WEB",
  "items_venta": [
    {
      "producto_servicio": 2,
      "cantidad": 1,
      "precio_unitario_venta": 450.00,
      "alojamiento_details": {
        "nombre_establecimiento": "Hotel Marriott Caracas",
        "ciudad": 1,
        "check_in": "2025-10-30",
        "check_out": "2025-11-02",
        "regimen_alimentacion": "Todo Incluido",
        "habitaciones": 1,
        "proveedor": 1,
        "notas": "Habitación con vista al mar - Frontend Test"
      }
    }
  ]
};

console.log("Datos que debería enviar el frontend:");
console.log(JSON.stringify(sampleVentaData, null, 2));

// Validar estructura
const requiredFields = ['cliente', 'moneda', 'items_venta'];
const missingFields = requiredFields.filter(field => !sampleVentaData[field]);

if (missingFields.length > 0) {
  console.error("❌ Campos faltantes:", missingFields);
} else {
  console.log("✅ Estructura básica correcta");
}

// Validar items
if (sampleVentaData.items_venta.length === 0) {
  console.error("❌ No hay items en la venta");
} else {
  console.log("✅ Items presentes:", sampleVentaData.items_venta.length);
  
  sampleVentaData.items_venta.forEach((item, index) => {
    if (!item.producto_servicio || !item.precio_unitario_venta) {
      console.error(`❌ Item ${index + 1} incompleto`);
    } else {
      console.log(`✅ Item ${index + 1} válido`);
      
      if (item.alojamiento_details) {
        const aloj = item.alojamiento_details;
        if (!aloj.nombre_establecimiento || !aloj.ciudad) {
          console.error(`❌ Alojamiento ${index + 1} incompleto`);
        } else {
          console.log(`✅ Alojamiento ${index + 1} válido`);
        }
      }
    }
  });
}

console.log("\n🔍 Verificar que estos valores existan en tu base de datos:");
console.log(`- Cliente ID: ${sampleVentaData.cliente}`);
console.log(`- Moneda ID: ${sampleVentaData.moneda}`);
console.log(`- Producto ID: ${sampleVentaData.items_venta[0].producto_servicio}`);
console.log(`- Ciudad ID: ${sampleVentaData.items_venta[0].alojamiento_details.ciudad}`);
console.log(`- Proveedor ID: ${sampleVentaData.items_venta[0].alojamiento_details.proveedor}`);