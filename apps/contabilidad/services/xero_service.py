"""
Xero Integration Service.
Sincroniza facturas y pagos de TravelHub con Xero Accounting.

Requiere:
    pip install xero-python

Configuración en settings.py:
    XERO_CLIENT_ID = os.getenv('XERO_CLIENT_ID')
    XERO_CLIENT_SECRET = os.getenv('XERO_CLIENT_SECRET')
    XERO_REDIRECT_URI = os.getenv('XERO_REDIRECT_URI', 'http://localhost:8000/xero/callback/')
"""

import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class XeroService:
    """
    Servicio para integrar con Xero Accounting API.

    Uso:
        service = XeroService()
        invoice_id = service.create_invoice(factura)
        service.create_payment(pago)
    """

    SCOPES = [
        "accounting.transactions",
        "accounting.contacts",
        "accounting.settings",
        "payroll.employees",
    ]

    def __init__(self, tenant_id: str | None = None):
        """
        Inicializa el servicio con credenciales de Xero.

        Args:
            tenant_id: ID del tenant de Xero (opcional)
        """
        self.client_id = getattr(settings, "XERO_CLIENT_ID", None)
        self.client_secret = getattr(settings, "XERO_CLIENT_SECRET", None)
        self.redirect_uri = getattr(
            settings, "XERO_REDIRECT_URI", "http://localhost:8000/xero/callback/"
        )
        self.tenant_id = tenant_id
        self._api_client = None
        self._accounting_api = None

    def _get_api_client(self):
        """Obtiene o crea el cliente API de Xero."""
        if self._api_client:
            return self._api_client

        try:
            from xero_python.api_client import ApiClient
            from xero_python.api_client.configuration import Configuration

            configuration = Configuration(
                oauth2_token={
                    "access_token": getattr(settings, "XERO_ACCESS_TOKEN", None),
                    "token_type": "Bearer",
                }
            )

            self._api_client = ApiClient(configuration)
            return self._api_client

        except ImportError:
            logger.error("Xero Python SDK not installed. Run: pip install xero-python")
            return None
        except Exception as e:
            logger.error(f"Error initializing Xero API client: {e}")
            return None

    def _get_accounting_api(self):
        """Obtiene o crea la instancia de AccountingApi."""
        if self._accounting_api:
            return self._accounting_api

        try:
            from xero_python.accounting.api import AccountingApi

            api_client = self._get_api_client()
            if not api_client:
                return None

            self._accounting_api = AccountingApi(api_client)
            return self._accounting_api

        except ImportError:
            logger.error("Xero Python SDK not installed")
            return None
        except Exception as e:
            logger.error(f"Error initializing Xero Accounting API: {e}")
            return None

    def create_invoice(self, factura, tenant_id: str | None = None) -> str | None:
        """
        Crea una factura en Xero desde una factura de TravelHub.

        Args:
            factura: Instancia del modelo Factura
            tenant_id: ID del tenant de Xero

        Returns:
            ID de la factura en Xero o None si falla
        """
        accounting_api = self._get_accounting_api()
        if not accounting_api:
            return None

        tenant = tenant_id or self.tenant_id
        if not tenant:
            logger.error("Xero tenant_id not configured")
            return None

        try:
            from xero_python.accounting.models import Contact, Invoice, InvoiceLineItem

            # Construir contact
            contact = Contact(
                name=f"{factura.cliente.nombres} {factura.cliente.apellidos}"
                if factura.cliente
                else "N/A",
                emailAddress=factura.cliente.email if factura.cliente else "",
            )

            # Construir líneas de factura
            line_items = []
            for item in factura.items_factura.all():
                line_item = InvoiceLineItem(
                    description=item.descripcion,
                    quantity=item.cantidad,
                    unit_amount=float(item.precio_unitario),
                    account_code="200",  # Sales account code
                )
                line_items.append(line_item)

            # Si no hay ítems, crear uno básico
            if not line_items:
                line_item = InvoiceLineItem(
                    description=f"Factura {factura.numero_factura}",
                    quantity=1,
                    unit_amount=float(factura.total),
                    account_code="200",
                )
                line_items.append(line_item)

            # Crear factura
            invoice = Invoice(
                type="ACCREC",  # Accounts Receivable
                contact=contact,
                line_items=line_items,
                date=factura.fecha_emision.strftime("%Y-%m-%d")
                if factura.fecha_emision
                else datetime.now().strftime("%Y-%m-%d"),
                due_date=(factura.fecha_emision + timezone.timedelta(days=30)).strftime("%Y-%m-%d")
                if factura.fecha_emision
                else None,
                reference=factura.numero_factura or f"TravelHub #{factura.pk}",
                status="DRAFT",
            )

            result = accounting_api.create_invoices(tenant, invoices=[invoice])

            if result.invoices:
                xero_invoice_id = result.invoices[0].invoice_id
                logger.info(f"Xero invoice created for factura {factura.pk}: {xero_invoice_id}")
                return xero_invoice_id

            return None

        except Exception as e:
            logger.error(f"Error creating Xero invoice for factura {factura.pk}: {e}")
            return None

    def create_payment(self, pago, tenant_id: str | None = None) -> str | None:
        """
        Registra un pago en Xero.

        Args:
            pago: Instancia del modelo PagoVenta
            tenant_id: ID del tenant de Xero

        Returns:
            ID del pago en Xero o None si falla
        """
        accounting_api = self._get_accounting_api()
        if not accounting_api:
            return None

        tenant = tenant_id or self.tenant_id
        if not tenant:
            logger.error("Xero tenant_id not configured")
            return None

        try:
            from xero_python.accounting.models import Payment

            # Buscar la factura asociada en Xero
            xero_invoice_id = getattr(pago.venta, "xero_invoice_id", None)
            if not xero_invoice_id:
                logger.warning(f"No Xero invoice ID found for venta {pago.venta_id}")
                return None

            payment = Payment(
                invoice={"invoice_id": xero_invoice_id},
                amount=float(pago.monto),
                date=pago.fecha_pago.strftime("%Y-%m-%d")
                if pago.fecha_pago
                else datetime.now().strftime("%Y-%m-%d"),
                reference=f"TravelHub Payment #{pago.pk}",
            )

            result = accounting_api.create_payments(tenant, payments=[payment])

            if result.payments:
                xero_payment_id = result.payments[0].payment_id
                logger.info(f"Xero payment created for pago {pago.pk}: {xero_payment_id}")
                return xero_payment_id

            return None

        except Exception as e:
            logger.error(f"Error creating Xero payment for pago {pago.pk}: {e}")
            return None

    def sync_contacts(self, clientes, tenant_id: str | None = None) -> dict:
        """
        Sincroniza clientes de TravelHub con contactos de Xero.

        Args:
            clientes: Queryset de modelos Cliente
            tenant_id: ID del tenant de Xero

        Returns:
            Dict con resultados de la sincronización
        """
        accounting_api = self._get_accounting_api()
        if not accounting_api:
            return {"error": "Xero API not available"}

        tenant = tenant_id or self.tenant_id
        if not tenant:
            return {"error": "Xero tenant_id not configured"}

        results = {"created": 0, "updated": 0, "errors": 0}

        try:
            from xero_python.accounting.models import Contact

            for cliente in clientes:
                try:
                    contact = Contact(
                        name=f"{cliente.nombres} {cliente.apellidos}",
                        emailAddress=cliente.email or "",
                        phoneNumber=cliente.telefono or "",
                        contactNumber=cliente.cedula_identidad or "",
                    )

                    # Verificar si ya existe
                    existing = None
                    try:
                        contacts = accounting_api.get_contacts(
                            tenant,
                            where=f'EmailAddress="{cliente.email}"' if cliente.email else None,
                        )
                        if contacts.contacts:
                            existing = contacts.contacts[0]
                    except Exception:
                        logger.debug("No se pudo obtener contacto existente de Xero")
                        pass

                    if existing:
                        # Actualizar
                        accounting_api.update_contact(tenant, existing.contact_id, contact)
                        results["updated"] += 1
                    else:
                        # Crear
                        accounting_api.create_contacts(tenant, contacts=[contact])
                        results["created"] += 1

                except Exception as e:
                    logger.error(f"Error syncing cliente {cliente.pk} to Xero: {e}")
                    results["errors"] += 1

            logger.info(f"Xero contacts sync completed: {results}")
            return results

        except Exception as e:
            logger.error(f"Error in Xero contacts sync: {e}")
            return {"error": str(e)}

    def get_invoices(self, tenant_id: str | None = None) -> list:
        """
        Obtiene facturas de Xero.

        Args:
            tenant_id: ID del tenant de Xero

        Returns:
            Lista de facturas
        """
        accounting_api = self._get_accounting_api()
        if not accounting_api:
            return []

        tenant = tenant_id or self.tenant_id
        if not tenant:
            return []

        try:
            result = accounting_api.get_invoices(tenant)
            return result.invoices or []

        except Exception as e:
            logger.error(f"Error getting Xero invoices: {e}")
            return []


# ============================================================================
# Helper functions for use in Django views/tasks
# ============================================================================


def sync_factura_to_xero(factura) -> str | None:
    """
    Sincroniza una factura con Xero.
    Útil para llamar desde señales o tareas Celery.

    Args:
        factura: Instancia del modelo Factura

    Returns:
        ID de la factura en Xero o None
    """
    service = XeroService()
    return service.create_invoice(factura)


def sync_pago_to_xero(pago) -> str | None:
    """
    Sincroniza un pago con Xero.

    Args:
        pago: Instancia del modelo PagoVenta

    Returns:
        ID del pago en Xero o None
    """
    service = XeroService()
    return service.create_payment(pago)


def sync_clientes_to_xero(agencia=None) -> dict:
    """
    Sincroniza todos los clientes de una agencia con Xero.

    Args:
        agencia: Instancia del modelo Agencia (opcional)

    Returns:
        Dict con resultados
    """
    from apps.crm.models import Cliente

    service = XeroService()

    queryset = Cliente.objects.all()
    if agencia:
        queryset = queryset.filter(agencia=agencia)

    return service.sync_contacts(queryset)
