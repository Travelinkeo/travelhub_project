# Guía de Personalización de Plantillas

## 📧 Plantillas de Email (HTML)

### Ubicación
```
core/templates/core/emails/
├── base_email.html          # Plantilla base
├── confirmacion_venta.html  # Confirmación de venta
├── cambio_estado.html       # Cambio de estado
├── confirmacion_pago.html   # Confirmación de pago
└── recordatorio_pago.html   # Recordatorio de pago
```

### Personalizar Colores

Edita `base_email.html`, busca la sección `<style>` y modifica:

```css
/* Cambiar color principal (gradiente morado) */
.header { 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
}

/* Opciones de colores corporativos: */
/* Azul: #2563eb 0%, #1e40af 100% */
/* Verde: #10b981 0%, #059669 100% */
/* Naranja: #f59e0b 0%, #d97706 100% */
/* Rojo: #ef4444 0%, #dc2626 100% */

/* Cambiar color de acentos */
.info-box { 
    border-left: 4px solid #667eea; 
}
.info-box strong { 
    color: #667eea; 
}
.button { 
    background: #667eea; 
}
```

### Personalizar Logo

Agrega tu logo en `base_email.html`:

```html
<div class="header">
    <img src="https://tu-dominio.com/logo.png" alt="TravelHub" style="max-width: 150px; margin-bottom: 10px;">
    <h1>🌍 TravelHub</h1>
    <p style="margin: 5px 0 0 0; opacity: 0.9;">Tu Agencia de Viajes de Confianza</p>
</div>
```

### Personalizar Footer

Edita `base_email.html`, sección footer:

```html
<div class="footer">
    <p><strong>TravelHub</strong> - Haciendo realidad tus sueños de viaje</p>
    <p>📞 +58 212 123-4567 | 📧 info@travelhub.com</p>
    <p>📍 Caracas, Venezuela</p>
    <p style="margin-top: 15px; font-size: 11px;">
        Este es un email automático, por favor no responder.
    </p>
</div>
```

### Agregar Redes Sociales

```html
<div class="footer">
    <!-- ... contenido existente ... -->
    <p style="margin-top: 15px;">
        <a href="https://facebook.com/travelhub" style="margin: 0 10px;">Facebook</a>
        <a href="https://instagram.com/travelhub" style="margin: 0 10px;">Instagram</a>
        <a href="https://twitter.com/travelhub" style="margin: 0 10px;">Twitter</a>
    </p>
</div>
```

---

## 📱 Mensajes de WhatsApp

### Ubicación
```
core/whatsapp_notifications.py
```

### Personalizar Mensajes

Edita las funciones en `whatsapp_notifications.py`:

#### Confirmación de Venta
```python
mensaje = f"""
🌍 *TravelHub - Confirmación de Reserva*

Hola *{venta.cliente.get_nombre_completo()}* 👋

¡Tu reserva está lista! 🎉

📋 *Detalles:*
✈️ Localizador: *{venta.localizador}*
📅 Fecha: {venta.fecha_venta.strftime('%d/%m/%Y')}
💰 Total: {venta.moneda.simbolo}{venta.total_venta}
📊 Estado: {venta.get_estado_display()}

Nos pondremos en contacto pronto.

_Equipo TravelHub_ 🌟
""".strip()
```

#### Cambiar Emojis

Emojis disponibles en WhatsApp:
- Viajes: ✈️ 🌍 🗺️ 🧳 🏖️ 🏝️ 🎫
- Dinero: 💰 💵 💳 💸 🏦
- Estados: ✅ ❌ ⏰ 🔄 📊 📈
- Comunicación: 📞 📧 💬 📱
- Otros: 🎉 👋 🌟 ⭐ 🔔

#### Personalizar Formato

WhatsApp soporta:
- `*negrita*` → **negrita**
- `_cursiva_` → _cursiva_
- `~tachado~` → ~~tachado~~
- ` ```código``` ` → `código`

Ejemplo:
```python
mensaje = f"""
*IMPORTANTE:* Tu reserva está confirmada ✅

_Detalles de tu viaje:_
• Destino: ~París~ *Roma* 🇮🇹
• Fecha: `15/12/2024`

¡Buen viaje! ✈️
"""
```

---

## 🎨 Ejemplos de Personalización

### Estilo Minimalista

**Email:**
```css
.header { 
    background: #ffffff; 
    color: #000000;
    border-bottom: 3px solid #000000;
}
.info-box { 
    background: #f5f5f5; 
    border-left: 4px solid #000000; 
}
```

**WhatsApp:**
```python
mensaje = f"""
TRAVELHUB

Reserva confirmada
Localizador: {venta.localizador}
Total: ${venta.total_venta}

Gracias.
"""
```

### Estilo Corporativo

**Email:**
```css
.header { 
    background: #1e3a8a; 
    color: white;
}
.info-box { 
    border-left: 4px solid #1e3a8a; 
}
```

**WhatsApp:**
```python
mensaje = f"""
🏢 *TRAVELHUB CORPORATE*

Estimado/a {venta.cliente.get_nombre_completo()},

Su reserva corporativa ha sido procesada exitosamente.

*DETALLES DE LA RESERVA*
━━━━━━━━━━━━━━━━━━━━
Código: {venta.localizador}
Monto: ${venta.total_venta}
━━━━━━━━━━━━━━━━━━━━

Atentamente,
Departamento de Viajes Corporativos
"""
```

### Estilo Casual/Amigable

**WhatsApp:**
```python
mensaje = f"""
¡Hola {venta.cliente.get_nombre_completo()}! 👋😊

¡Genial! Tu reserva está lista 🎉✈️

🎫 Código: {venta.localizador}
💰 Total: ${venta.total_venta}

¿Dudas? ¡Escríbenos! 💬

Saludos,
El equipo de TravelHub 🌟
"""
```

---

## 🔧 Variables Disponibles

### En Plantillas de Email

```python
# Venta
{{ localizador }}
{{ fecha }}  # Formato: DD/MM/YYYY
{{ total }}
{{ moneda }}  # Símbolo: $, €, etc.
{{ estado }}

# Cliente
{{ cliente_nombre }}

# Pago (solo en confirmacion_pago.html)
{{ monto }}
{{ metodo }}
{{ saldo }}

# Estado (solo en cambio_estado.html)
{{ estado_anterior }}
{{ estado_actual }}
```

### En Funciones de WhatsApp

```python
# Venta
venta.localizador
venta.fecha_venta.strftime('%d/%m/%Y')
venta.total_venta
venta.moneda.simbolo
venta.get_estado_display()
venta.saldo_pendiente

# Cliente
venta.cliente.get_nombre_completo()
venta.cliente.email
venta.cliente.telefono_principal

# Pago
pago_venta.monto
pago_venta.get_metodo_display()
pago_venta.fecha_pago.strftime('%d/%m/%Y')
```

---

## 📝 Tips de Diseño

### Email
1. **Mantén simplicidad** - Menos es más
2. **Usa espacios en blanco** - Facilita lectura
3. **Colores contrastantes** - Texto legible
4. **Responsive** - Ya está configurado
5. **Prueba en múltiples clientes** - Gmail, Outlook, etc.

### WhatsApp
1. **Sé conciso** - Mensajes cortos
2. **Usa emojis con moderación** - 2-3 por mensaje
3. **Estructura clara** - Bullets y separadores
4. **Evita URLs largas** - Usa acortadores
5. **Prueba el formato** - Envía a ti mismo primero

---

## 🧪 Probar Cambios

### Email
```bash
python test_email.py
```

### WhatsApp
```bash
python test_whatsapp.py
```

### Flujo Completo
```bash
python test_email_notifications.py
```

---

## 📚 Recursos

- [Emojipedia](https://emojipedia.org/) - Todos los emojis
- [HTML Email Guide](https://www.campaignmonitor.com/css/) - CSS para emails
- [WhatsApp Formatting](https://faq.whatsapp.com/539178204879377) - Formato oficial
- [Color Picker](https://htmlcolorcodes.com/) - Elegir colores

---

**Recuerda:** Después de modificar plantillas, reinicia el servidor Django para ver los cambios.
