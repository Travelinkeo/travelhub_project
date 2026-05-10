import logging
import re
from hashlib import sha256
from django.db import models
from apps.crm.models import Cliente, Pasajero

logger = logging.getLogger(__name__)

class CustomerService:
    @staticmethod
    def identify_or_create(data, agencia, forced_cliente_id=None):
        """
        Identifies an existing customer by ID, document, or name, or creates a new one.
        """
        cliente = None
        if forced_cliente_id:
            try:
                cliente = Cliente.objects.get(pk=forced_cliente_id)
            except Cliente.DoesNotExist:
                pass

        if not cliente:
            # 1. Search by Document (Priority)
            doc_pax = data.get('passenger_document') or data.get('foid') or data.get('CODIGO_IDENTIFICACION')
            
            if doc_pax:
                doc_clean = re.sub(r'[^A-Z0-9]', '', str(doc_pax).upper())
                doc_hash = sha256(doc_clean.encode()).hexdigest()
                
                # Use exact match for document search
                cliente = Cliente.objects.filter(agencia=agencia).filter(
                    models.Q(documento_hash=doc_hash) | models.Q(cedula_identidad__iexact=doc_clean)
                ).first()

            # 2. Search by Name (Fallback)
            if not cliente:
                nombre_pax = data.get('passenger_name') or "PASAJERO DESCONOCIDO"
                nombre_search = nombre_pax.split('/')[0].strip() if '/' in nombre_pax else nombre_pax.strip()
                if len(nombre_search) > 3:
                    # Using iexact for better integrity as per CTO report
                    cliente = Cliente.objects.filter(agencia=agencia, nombres__iexact=nombre_search).first()
            
            # 3. Creation
            if not cliente:
                cliente = Cliente.objects.create(
                    agencia=agencia,
                    nombres=data.get('passenger_name') or "PASAJERO",
                    apellidos='(Auto-Generado)',
                    tipo_cliente='IND'
                )
                if doc_pax:
                    cliente.cedula_identidad = doc_pax
                    doc_clean = re.sub(r'[^A-Z0-9]', '', str(doc_pax).upper())
                    cliente.documento_hash = sha256(doc_clean.encode()).hexdigest()
                    cliente.save()
        
        return cliente

    @staticmethod
    def sync_pasajero(nombre_pax, agencia, venta):
        """
        Syncs a passenger record and adds it to the sale.
        """
        pax_obj, _ = Pasajero.objects.get_or_create(
            agencia=agencia,
            nombres=nombre_pax,
            defaults={'apellidos': '.'}
        )
        venta.pasajeros.add(pax_obj)
        return pax_obj
