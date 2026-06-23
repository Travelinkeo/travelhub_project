"""
apps/bookings/admin.py — Punto de entrada del Admin de Bookings
================================================================
El admin de esta app está dividido en módulos temáticos para facilitar
la navegación y el mantenimiento. Este archivo los importa todos.

  admin_ventas.py    → VentaAdmin + Inlines + acciones (facturación, vouchers, liquidaciones)
  admin_boletos.py   → BoletoImportadoAdmin + AuditLogAdmin + SegmentoVueloAdmin + FeeVentaAdmin + PagoVentaAdmin
  admin_servicios.py → Hotel, Auto, Traslado, Actividad, Circuito, Tarifarios + Catálogos

Para agregar o editar un admin, edita el módulo correspondiente.
"""

# ruff: noqa: F401, F403
from .admin_boletos import *
from .admin_servicios import *
from .admin_ventas import *
