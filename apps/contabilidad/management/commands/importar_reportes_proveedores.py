"""Comando de gestión Django para contabilidad: importar_reportes_proveedores.
"""

import email
import logging
import os
from email import policy

from django.core.management.base import BaseCommand

from apps.contabilidad.supplier_report_service import SupplierReportProcessorService
from core.models.agencia import Agencia

logger = logging.getLogger(__name__)


class Command:
    """Clase Command. Uso: según contexto de la aplicación.
    """
    help = "Importa masivamente reportes de ventas de proveedores (.eml o .pdf) desde un directorio local."

    def add_arguments(self, parser):
        # add_arguments: Add arguments. Args: según implementación. Returns: según implementación.
        parser.add_argument(
            "--dir",
            type=str,
            required=True,
            help="Ruta absoluta del directorio a procesar (ej. C:\\Users\\ARMANDO\\Downloads\\REPORTES DE VENTA)",
        )
        parser.add_argument(
            "--agencia",
            type=str,
            default="",
            help="Nombre o slug de la agencia (ej. Travelinkeo). Por defecto la primera agencia activa.",
        )

    def handle(self, *args, **options):
        # handle: Maneja/gestiona . Args: evento/datos. Returns: respuesta.
        target_dir = options["dir"]
        agencia_param = options["agencia"]

        self.stdout.write(self.style.HTTP_INFO("=" * 60))
        self.stdout.write(self.style.HTTP_INFO("  IMPORTADOR MASIVO DE REPORTES DE PROVEEDORES"))
        self.stdout.write(self.style.HTTP_INFO("=" * 60))

        # 1. Determinar la Agencia (Multi-Tenant)
        agencia = None
        if agencia_param:
            agencia = Agencia.objects.filter(nombre__icontains=agencia_param).first()
        if not agencia:
            agencia = Agencia.objects.filter(activa=True).first()

        if not agencia:
            self.stdout.write(
                self.style.ERROR("[ERROR] No se encontró una agencia activa en el sistema.")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"Agencia asignada: {agencia.nombre} (ID: {agencia.id})")
        )
        self.stdout.write(f"Buscando reportes en: {target_dir}\n")

        if not os.path.exists(target_dir):
            self.stdout.write(self.style.ERROR(f"[ERROR] El directorio {target_dir} no existe."))
            return

        total_procesados = 0
        total_boletos = 0

        # 2. Recorrer la carpeta y subcarpetas
        for root, _, files in os.walk(target_dir):
            for filename in files:
                filepath = os.path.join(root, filename)

                # Caso A: Archivos .eml
                if filename.lower().endswith(".eml"):
                    try:
                        with open(filepath, "rb") as f:
                            msg = email.message_from_binary_file(f, policy=policy.default)

                        subject = str(msg["subject"] or filename)
                        sender = str(msg["from"] or "")

                        for part in msg.walk():
                            fn = part.get_filename()
                            if fn and fn.lower().endswith(".pdf"):
                                pdf_bytes = part.get_payload(decode=True)
                                if pdf_bytes:
                                    reporte = SupplierReportProcessorService.procesar_pdf_reporte(
                                        pdf_bytes=pdf_bytes,
                                        filename=fn,
                                        subject=subject,
                                        sender_email=sender,
                                        agencia=agencia,
                                    )
                                    if reporte:
                                        total_procesados += 1
                                        num_items = reporte.items.count()
                                        total_boletos += num_items
                                        self.stdout.write(
                                            self.style.SUCCESS(
                                                f"  [OK] {reporte.proveedor_nombre} — {fn} "
                                                f"({num_items} boletos, Total: ${reporte.monto_total_ventas})"
                                            )
                                        )
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  [ERROR] Procesando {filename}: {e}"))

                # Caso B: Archivos .pdf directos
                elif filename.lower().endswith(".pdf"):
                    try:
                        with open(filepath, "rb") as f:
                            pdf_bytes = f.read()

                        reporte = SupplierReportProcessorService.procesar_pdf_reporte(
                            pdf_bytes=pdf_bytes,
                            filename=filename,
                            subject=filename,
                            sender_email="local_import@travelhub",
                            agencia=agencia,
                        )
                        if reporte:
                            total_procesados += 1
                            num_items = reporte.items.count()
                            total_boletos += num_items
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  [OK] {reporte.proveedor_nombre} — {filename} "
                                    f"({num_items} boletos, Total: ${reporte.monto_total_ventas})"
                                )
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  [ERROR] Procesando PDF {filename}: {e}")
                        )

        self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 60))
        self.stdout.write(
            self.style.SUCCESS(
                f"Procesamiento finalizado. Total reportes: {total_procesados}, Total boletos extraídos: {total_boletos}"
            )
        )
        self.stdout.write(self.style.HTTP_INFO("=" * 60))
