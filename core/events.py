# core/events.py
# ==============================================================================
# 🏛️ KERNEL EVENTS
# ==============================================================================
# Este archivo centraliza la definición de todos los eventos de negocio
# (Django Signals) que permiten la comunicación desacoplada entre los
# diferentes módulos de dominio del proyecto.
#
# Principio Arquitectónico:
# Los módulos de dominio (ej. 'bookings', 'finance') NUNCA deben importarse
# entre sí. En su lugar, un módulo emite una señal y otro(s) reaccionan a ella.
#
# Ejemplo:
# - 'bookings' emite 'sale_recalculation_requested' cuando una venta cambia.
# - 'finance' se suscribe a esta señal y ejecuta la lógica de recálculo.
#
# De esta forma, 'bookings' no sabe ni necesita saber que 'finance' existe.
# ==============================================================================

"""Definición centralizada de eventos de negocio (Django Signals)."""

from django.dispatch import Signal

# --- Eventos de Bookings ---
sale_recalculation_requested = Signal()
# Proporciona los argumentos: sender, venta_id, agencia_id

ticket_invoicing_requested = Signal()
# Proporciona los argumentos: sender, venta_id, formato_detectado, agencia_id

sale_payment_recorded = Signal()
# Proporciona los argumentos: sender, pago_id, estado_accion (save/delete), agencia_id

# --- Eventos de Finance ---
# (Aquí se añadirían futuros eventos emitidos por el módulo de finanzas)

# --- Eventos de CRM ---
# (Aquí se añadirían futuros eventos emitidos por el módulo de CRM)
