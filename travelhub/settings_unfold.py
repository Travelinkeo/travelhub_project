UNFOLD = {
    "SITE_TITLE": "TravelHub Admin",
    "SITE_SYMBOL": "travel_explore",
    "STYLES": [
        "/static/css/custom_admin.css",
    ],
    "COLORS": {
        "primary": {
            "50": "239 246 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "59 130 246",
            "600": "37 99 235",
            "700": "29 78 216",
            "800": "30 64 175",
            "900": "30 58 138",
            "950": "23 37 84",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Operaciones",
                "collapsible": True,
                "items": [
                    {"title": "Dashboard Principal", "icon": "dashboard", "link": "/dashboard/"},
                    {
                        "title": "Subir Boleto (IA)",
                        "icon": "upload_file",
                        "link": "/system/dashboard/erp/boletos/importar/",
                    },
                    {
                        "title": "Buffer de Revision",
                        "icon": "rate_review",
                        "link": "/admin/bookings/boletoimportado/",
                    },
                ],
            },
            {
                "title": "Ventas y Reservas",
                "collapsible": True,
                "items": [
                    {"title": "Ventas", "icon": "shopping_cart", "link": "/admin/bookings/venta/"},
                    {
                        "title": "Items de Venta",
                        "icon": "list_alt",
                        "link": "/admin/bookings/itemventa/",
                    },
                    {
                        "title": "Boletos Importados",
                        "icon": "flight",
                        "link": "/admin/bookings/boletoimportado/",
                    },
                    {
                        "title": "Segmentos de Vuelo",
                        "icon": "connecting_airports",
                        "link": "/admin/bookings/segmentovuelo/",
                    },
                    {
                        "title": "Alojamientos",
                        "icon": "hotel",
                        "link": "/admin/bookings/alojamientoreserva/",
                    },
                    {
                        "title": "Traslados",
                        "icon": "airport_shuttle",
                        "link": "/admin/bookings/trasladoservicio/",
                    },
                    {
                        "title": "Actividades",
                        "icon": "hiking",
                        "link": "/admin/bookings/actividadservicio/",
                    },
                    {
                        "title": "Alquiler de Autos",
                        "icon": "directions_car",
                        "link": "/admin/bookings/alquilerautoreserva/",
                    },
                    {
                        "title": "Circuitos",
                        "icon": "map",
                        "link": "/admin/bookings/circuitoturistico/",
                    },
                    {
                        "title": "Paquetes Aereos",
                        "icon": "flight_takeoff",
                        "link": "/admin/bookings/paqueteaereo/",
                    },
                    {
                        "title": "Cruceros",
                        "icon": "directions_boat",
                        "link": "/admin/bookings/cruceroreserva/",
                    },
                    {
                        "title": "Fee de Venta",
                        "icon": "attach_money",
                        "link": "/admin/bookings/feeventa/",
                    },
                    {
                        "title": "Pagos de Venta",
                        "icon": "payments",
                        "link": "/admin/bookings/pagoventa/",
                    },
                    {
                        "title": "Proveedores",
                        "icon": "local_shipping",
                        "link": "/admin/bookings/proveedor/",
                    },
                    {
                        "title": "Productos y Servicios",
                        "icon": "inventory",
                        "link": "/admin/bookings/productoservicio/",
                    },
                ],
            },
            {
                "title": "Hoteles y Tarifarios",
                "collapsible": True,
                "items": [
                    {
                        "title": "Tarifarios Proveedor",
                        "icon": "request_quote",
                        "link": "/admin/bookings/tarifarioproveedor/",
                    },
                    {
                        "title": "Hoteles en Tarifario",
                        "icon": "king_bed",
                        "link": "/admin/bookings/hoteltarifario/",
                    },
                    {
                        "title": "Tipos de Habitacion",
                        "icon": "bed",
                        "link": "/admin/bookings/tipohabitacion/",
                    },
                    {
                        "title": "Tarifas por Temporada",
                        "icon": "calendar_month",
                        "link": "/admin/bookings/tarifahabitacion/",
                    },
                    {"title": "Amenities", "icon": "spa", "link": "/admin/bookings/amenity/"},
                ],
            },
            {
                "title": "CRM",
                "collapsible": True,
                "items": [
                    {"title": "Clientes", "icon": "people", "link": "/admin/crm/cliente/"},
                    {"title": "Pasajeros", "icon": "person", "link": "/admin/crm/pasajero/"},
                    {
                        "title": "Oportunidades (Kanban)",
                        "icon": "lightbulb",
                        "link": "/admin/crm/oportunidadviaje/",
                    },
                    {
                        "title": "Pasaportes Escaneados",
                        "icon": "scanner",
                        "link": "/admin/crm/pasaporteescaneado/",
                    },
                ],
            },
            {
                "title": "Cotizaciones",
                "collapsible": True,
                "items": [
                    {
                        "title": "Cotizaciones",
                        "icon": "description",
                        "link": "/admin/cotizaciones/cotizacion/",
                    },
                    {
                        "title": "Items Cotizacion",
                        "icon": "format_list_bulleted",
                        "link": "/admin/cotizaciones/itemcotizacion/",
                    },
                ],
            },
            {
                "title": "Finanzas",
                "collapsible": True,
                "items": [
                    {
                        "title": "Facturas",
                        "icon": "receipt_long",
                        "link": "/admin/finance/factura/",
                    },
                    {
                        "title": "Facturas Consolidadas",
                        "icon": "description",
                        "link": "/admin/finance/facturaconsolidada/",
                    },
                    {"title": "Libro de Ventas", "icon": "menu_book", "link": "/admin/finance/factura/"},
                    {
                        "title": "Gastos Operativos",
                        "icon": "money_off",
                        "link": "/admin/finance/gastooperativo/",
                    },
                    {
                        "title": "Pagos (Link de Pago)",
                        "icon": "link",
                        "link": "/admin/finance/linkdepago/",
                    },
                    {
                        "title": "Conciliaciones",
                        "icon": "compare_arrows",
                        "link": "/admin/finance/conciliacionboleto/",
                    },
                    {
                        "title": "Retenciones ISLR",
                        "icon": "receipt",
                        "link": "/admin/finance/retencionislr/",
                    },
                ],
            },
            {
                "title": "Contabilidad",
                "collapsible": True,
                "items": [
                    {
                        "title": "Plan de Cuentas",
                        "icon": "account_tree",
                        "link": "/admin/contabilidad/plancontable/",
                    },
                    {
                        "title": "Asientos Contables",
                        "icon": "book",
                        "link": "/admin/contabilidad/asientocontable/",
                    },
                    {
                        "title": "Tasas BCV",
                        "icon": "currency_exchange",
                        "link": "/admin/contabilidad/tasacambiobcv/",
                    },
                    {"title": "Reportes Contables", "icon": "assessment", "link": "/admin/contabilidad/asientocontable/"},
                ],
            },
            {
                "title": "Marketing",
                "collapsible": True,
                "items": [
                    {"title": "Campañas", "icon": "campaign", "link": "/admin/marketing/campania/"},
                    {
                        "title": "Activos Marketing",
                        "icon": "photo_library",
                        "link": "/admin/marketing/activomarketing/",
                    },
                    {
                        "title": "Config Marketing",
                        "icon": "settings",
                        "link": "/admin/marketing/configuracionmarketing/",
                    },
                    {
                        "title": "Centro de Marketing",
                        "icon": "auto_awesome",
                        "link": "/bookings/marketing/hub/",
                    },
                ],
            },
            {
                "title": "CMS / Contenido",
                "collapsible": True,
                "items": [
                    {"title": "Articulos", "icon": "article", "link": "/admin/cms/articulo/"},
                    {
                        "title": "Guias de Destino",
                        "icon": "travel_explore",
                        "link": "/admin/cms/guiadestino/",
                    },
                    {
                        "title": "Posts Redes",
                        "icon": "share",
                        "link": "/admin/cms/postredessociales/",
                    },
                ],
            },
            {
                "title": "Configuracion Global",
                "collapsible": True,
                "items": [
                    {"title": "Agencias", "icon": "corporate_fare", "link": "/admin/core/agencia/"},
                    {"title": "Usuarios", "icon": "group", "link": "/admin/auth/user/"},
                    {"title": "Paises", "icon": "public", "link": "/admin/common/pais/"},
                    {"title": "Ciudades", "icon": "location_city", "link": "/admin/common/ciudad/"},
                    {"title": "Aerolineas", "icon": "flight", "link": "/admin/common/aerolinea/"},
                    {"title": "Monedas", "icon": "paid", "link": "/admin/finance/moneda/"},
                    {
                        "title": "Tipos de Cambio",
                        "icon": "trending_up",
                        "link": "/admin/finance/tipocambio/",
                    },
                    {
                        "title": "Feature Flags",
                        "icon": "toggle_on",
                        "link": "/admin/core/featureflag/",
                    },
                    {"title": "Cron API Keys", "icon": "key", "link": "/admin/core/cronapikey/"},
                    {"title": "Audit Logs", "icon": "history", "link": "/admin/core/auditlog/"},
                ],
            },
            {
                "title": "SuperAdmin",
                "collapsible": True,
                "items": [
                    {"title": "Control de Mando", "icon": "shield", "link": "/system/god-mode/"},
                    {
                        "title": "Gestion de Agencias",
                        "icon": "corporate_fare",
                        "link": "/admin/core/agencia/",
                    },
                    {
                        "title": "IA - GDS Analyzer",
                        "icon": "analytics",
                        "link": "/system/intelligence/gds-analyzer/",
                    },
                    {
                        "title": "Conciliacion Proveedores",
                        "icon": "account_balance",
                        "link": "/finance/supplier-reconciliation/",
                    },
                ],
            },
            {
                "title": "Ajustes de Agencia",
                "collapsible": True,
                "items": [
                    {
                        "title": "Configuración de Agencias",
                        "icon": "corporate_fare",
                        "link": "/admin/core/agencia/",
                    },
                    {
                        "title": "Branding y Logos",
                        "icon": "palette",
                        "link": "/admin/core/agenciabranding/",
                    },
                    {
                        "title": "Parámetros SaaS",
                        "icon": "settings",
                        "link": "/admin/core/agenciaconfiguracion/",
                    },
                    {
                        "title": "Usuarios de Agencia",
                        "icon": "group",
                        "link": "/admin/core/usuarioagencia/",
                    },
                ],
            },
        ],
    },
}
