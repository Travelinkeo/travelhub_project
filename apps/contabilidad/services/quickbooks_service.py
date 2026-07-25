"""
QuickBooks Online Integration Service.

Sincroniza facturas, pagos y clientes de TravelHub con QuickBooks Online.
Requiere:
  - pip install quickbooks-python (o requests para API directa)
  - Configurar QB_CLIENT_ID, QB_CLIENT_SECRET, QB_COMPANY_ID, QB_REFRESH_TOKEN

https://developer.intuit.com/app/developer/qbo/docs/api
"""

import logging
import time
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

QB_BASE = "https://sandbox-quickbooks.api.intuit.com"  # Sandbox
QB_BASE_PROD = "https://quickbooks.api.intuit.com"


class QuickBooksService:
    """Integración con QuickBooks Online API v3."""

    def __init__(self, company_id: str | None = None):
        # __init__: Inicializa una nueva instancia de QuickBooksService. Args: parámetros de inicialización.
        self.client_id = getattr(settings, "QB_CLIENT_ID", "")
        self.client_secret = getattr(settings, "QB_CLIENT_SECRET", "")
        self.company_id = company_id or getattr(settings, "QB_COMPANY_ID", "")
        self._access_token = None
        self._token_expires = 0

    @property
    def base_url(self) -> str:
        # base_url: Base url. Args: según implementación. Returns: según implementación.
        env = getattr(settings, "ENVIRONMENT", "development")
        base = QB_BASE if env in ("development", "test") else QB_BASE_PROD
        return f"{base}/v3/company/{self.company_id}"

    def _refresh_token(self) -> str:
        """Obtiene un nuevo access_token usando refresh_token."""
        refresh_token = getattr(settings, "QB_REFRESH_TOKEN", "")
        if not refresh_token:
            logger.error("QB_REFRESH_TOKEN not configured")
            return ""

        resp = requests.post(
            "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            auth=(self.client_id, self.client_secret),
            timeout=15,
        )
        if resp.status_code != 200:
            logger.error("QB token refresh failed: %s", resp.text[:200])
            return ""

        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 3600) - 60
        logger.info("QB token refreshed (expires in %ss)", data.get("expires_in", 3600))
        return self._access_token

    @property
    def access_token(self) -> str:
        # access_token: Access token. Args: según implementación. Returns: según implementación.
        if not self._access_token or time.time() > self._token_expires:
            return self._refresh_token()
        return self._access_token

    def _request(self, method: str, path: str, data: dict | None = None) -> dict[str, Any]:
        """Ejecuta una llamada a la API de QuickBooks."""
        token = self.access_token
        if not token:
            return {"error": "No access token"}

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = requests.request(method, url, json=data, headers=headers, timeout=30)
            if resp.status_code == 401:
                # Token expirado, reintentar
                self._access_token = None
                return self._request(method, path, data)
            if resp.status_code >= 400:
                logger.error("QB API error %s: %s", resp.status_code, resp.text[:300])
                return {"error": f"QB API error: {resp.status_code}", "detail": resp.text[:300]}
            return resp.json()
        except requests.RequestException as e:
            logger.error("QB request failed: %s", e)
            return {"error": str(e)[:200]}

    def create_invoice(self, invoice_data: dict) -> dict:
        """Crea una factura en QuickBooks."""
        return self._request("POST", "invoice", data=invoice_data)

    def create_customer(self, customer_data: dict) -> dict:
        """Crea o actualiza un cliente en QuickBooks."""
        return self._request("POST", "customer", data=customer_data)

    def query(self, sql: str) -> dict:
        """Ejecuta una consulta SQL contra QuickBooks."""
        return self._request("GET", f"query?query={requests.utils.quote(sql)}")

    def find_customer_by_email(self, email: str) -> dict | None:
        """Busca un cliente por email en QuickBooks."""
        escaped_email = email.replace("'", "''")
        result = self.query(
            f"SELECT * FROM Customer WHERE PrimaryEmailAddr = '{escaped_email}'"  # noqa: S608
        )
        customers = result.get("QueryResponse", {}).get("Customer", [])
        return customers[0] if customers else None

    def sync_invoice_from_venta(self, venta) -> dict:
        """Sincroniza una venta de TravelHub como factura en QuickBooks."""

        invoice = getattr(venta, "factura", None)
        if not invoice:
            return {"error": "Venta sin factura asociada"}

        # Buscar o crear cliente en QB
        cliente = venta.cliente
        customer_ref = None
        if cliente and cliente.email:
            existing = self.find_customer_by_email(cliente.email)
            if existing:
                customer_ref = {"value": existing["Id"], "name": existing["DisplayName"]}
            else:
                qb_customer = self.create_customer(
                    {
                        "DisplayName": cliente.nombre or cliente.razon_social or cliente.email,
                        "PrimaryEmailAddr": {"Address": cliente.email},
                        "GivenName": cliente.nombre or "",
                        "FamilyName": cliente.apellido or "",
                    }
                )
                if "error" not in qb_customer:
                    customer_ref = {
                        "value": qb_customer.get("Customer", {}).get("Id", ""),
                        "name": qb_customer.get("Customer", {}).get("DisplayName", ""),
                    }

        if not customer_ref:
            return {"error": "Could not resolve QB customer"}

        # Construir factura QB
        qb_invoice = {
            "CustomerRef": customer_ref,
            "Line": [
                {
                    "DetailType": "SalesItemLineDetail",
                    "Amount": float(invoice.total or venta.monto or 0),
                    "Description": f"Factura {invoice.numero or ''} - {venta.descripcion or ''}",
                    "SalesItemLineDetail": {
                        "ItemRef": {"value": "1", "name": "Servicios"},
                    },
                }
            ],
        }

        result = self.create_invoice(qb_invoice)
        if "error" not in result:
            invoice_id = result.get("Invoice", {}).get("Id", "")
            logger.info("QB invoice created: %s for venta %s", invoice_id, venta.id)
        return result
