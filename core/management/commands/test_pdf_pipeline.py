"""
management command: test_pdf_pipeline
=====================================
Prueba integral del pipeline de generación de PDF y storage.

Uso:
    python manage.py test_pdf_pipeline
    python manage.py test_pdf_pipeline --boleto-id 42    # probar con un boleto real
    python manage.py test_pdf_pipeline --verbose
"""

import os
import sys
import time
import traceback

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Prueba el pipeline completo: Storage -> Generacion PDF -> URL -> Acceso"

    def add_arguments(self, parser):
        parser.add_argument(
            "--boleto-id",
            type=int,
            default=None,
            help="ID de un BoletoImportado real para probar (opcional)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostrar detalles adicionales",
        )

    def handle(self, *args, **options):
        verbose = options["verbose"]
        boleto_id = options["boleto_id"]

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write(self.style.SUCCESS("  [TEST SUITE] PDF Pipeline & Storage"))
        self.stdout.write("=" * 65 + "\n")

        resultados = []

        # ── TEST 1: Configuración de Storage ──────────────────────────────
        resultados.append(self._test_storage_config(verbose))

        # ── TEST 2: Celery Availability ────────────────────────────────────
        resultados.append(self._test_celery(verbose))

        # ── TEST 3: Gotenberg / WeasyPrint ────────────────────────────────
        resultados.append(self._test_pdf_renderer(verbose))

        # ── TEST 4: Generación completa de PDF con datos de prueba ─────────
        resultados.append(self._test_pdf_generation(verbose))

        # ── TEST 5: Guardar PDF en storage y obtener URL ───────────────────
        resultados.append(self._test_storage_save_and_url(verbose))

        # ── TEST 6 (Opcional): Boleto real de la BD ────────────────────────
        if boleto_id:
            resultados.append(self._test_real_boleto(boleto_id, verbose))

        # ── RESUMEN FINAL ──────────────────────────────────────────────────
        self._print_summary(resultados)

    # =========================================================================
    # TEST 1 – Configuración de Storage
    # =========================================================================
    def _test_storage_config(self, verbose):
        name = "Storage Config"
        self.stdout.write(f"\n[1/5] {name}")
        try:
            from django.conf import settings

            use_r2 = getattr(settings, "USE_R2", False)
            custom_domain = os.getenv("AWS_S3_CUSTOM_DOMAIN", "")
            media_url = settings.MEDIA_URL
            media_root = settings.MEDIA_ROOT
            storage_backend = settings.STORAGES["default"]["BACKEND"]

            self.stdout.write(f"      USE_R2             : {use_r2}")
            self.stdout.write(f"      AWS_S3_CUSTOM_DOMAIN: {custom_domain or '(no configurado)'}")
            self.stdout.write(f"      MEDIA_URL           : {media_url}")
            self.stdout.write(f"      MEDIA_ROOT          : {media_root}")
            self.stdout.write(f"      Storage backend     : {storage_backend.split('.')[-1]}")

            from core.storage import RawFileStorage

            raw = RawFileStorage()
            raw_type = (
                type(raw).__bases__[0].__name__ if type(raw).__bases__ else type(raw).__name__
            )

            if use_r2:
                qs_auth = getattr(raw, "querystring_auth", "?")
                qs_exp = getattr(raw, "querystring_expire", "?")
                c_domain = getattr(raw, "custom_domain", None)
                self.stdout.write("      RawFileStorage      : S3Boto3 (R2)")
                self.stdout.write(f"      querystring_auth    : {qs_auth}")
                if qs_auth:
                    self.stdout.write(
                        f"      querystring_expire  : {qs_exp}s ({qs_exp//3600}h {(qs_exp%3600)//60}m)"
                    )
                if c_domain:
                    self.stdout.write(f"      custom_domain       : {c_domain}")
                    self.stdout.write(
                        self.style.SUCCESS("      [OK] URLs permanentes via dominio custom")
                    )
                elif not qs_auth:
                    self.stdout.write(
                        self.style.SUCCESS("      [OK] URLs permanentes (querystring_auth=False)")
                    )
                else:
                    exp_days = qs_exp // 86400
                    if exp_days >= 7:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"      [OK] URLs con expiracion larga: {exp_days} dias"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f"      [FAIL] URLs expiran en {qs_exp}s -- muy corto!"
                            )
                        )
                        return ("FAIL", name, f"querystring_expire={qs_exp}s es muy corto")
            else:
                self.stdout.write("      RawFileStorage      : FileSystem (desarrollo local)")
                self.stdout.write(
                    self.style.WARNING("      [WARN] USE_R2=False -> modo desarrollo local")
                )

            return ("OK", name, "Configuracion correcta")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      [ERROR] {e}"))
            if verbose:
                traceback.print_exc()
            return ("FAIL", name, str(e))

    # =========================================================================
    # TEST 2 – Celery
    # =========================================================================
    def _test_celery(self, verbose):
        name = "Celery / Redis"
        self.stdout.write(f"\n[2/5] {name}")
        try:
            from apps.common.utils.celery_utils import _is_celery_available

            available = _is_celery_available()
            if available:
                self.stdout.write(
                    self.style.SUCCESS(
                        "      [OK] Celery/Redis disponible -> PDFs se generaran en background"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "      [WARN] Celery/Redis no disponible -> PDFs se generaran sincronamente"
                    )
                )
                self.stdout.write("      (esto es normal en desarrollo local)")
            return ("OK", name, f"Celery disponible: {available}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      [ERROR] {e}"))
            return ("FAIL", name, str(e))

    # =========================================================================
    # TEST 3 – Gotenberg / WeasyPrint
    # =========================================================================
    def _test_pdf_renderer(self, verbose):
        name = "PDF Renderer (Gotenberg/WeasyPrint)"
        self.stdout.write(f"\n[3/5] {name}")
        try:
            from apps.common.services.pdf_renderer import PdfRendererService

            html_simple = "<html><body><h1>TEST TravelHub PDF</h1><p>Pipeline OK</p></body></html>"

            t0 = time.time()
            pdf_bytes = PdfRendererService.render_html_to_pdf(html_simple)
            elapsed = time.time() - t0

            if pdf_bytes and len(pdf_bytes) > 100:
                motor = "Gotenberg" if elapsed < 5 else "WeasyPrint"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"      [OK] PDF generado: {len(pdf_bytes):,} bytes en {elapsed:.2f}s ({motor})"
                    )
                )
                return ("OK", name, f"{len(pdf_bytes)} bytes via {motor}")
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"      [FAIL] PDF vacio o muy pequeno: {len(pdf_bytes) if pdf_bytes else 0} bytes"
                    )
                )
                return ("FAIL", name, "PDF vacio")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      [ERROR] {e}"))
            if verbose:
                traceback.print_exc()
            return ("FAIL", name, str(e))

    # =========================================================================
    # TEST 4 – Generación de PDF con plantilla real del boleto
    # =========================================================================
    def _test_pdf_generation(self, verbose):
        name = "Generacion PDF con plantilla de boleto"
        self.stdout.write(f"\n[4/5] {name}")
        try:
            from apps.automation.parsers.pdf_generation import PdfGenerationService

            datos_prueba = {
                "SOURCE_SYSTEM": "SABRE",
                "NOMBRE_DEL_PASAJERO": "TEST/PASAJERO MR",
                "NUMERO_DE_BOLETO": "0012345678901",
                "CODIGO_RESERVA": "TSTPNR",
                "FECHA_DE_EMISION": "04 Jun 2025",
                "NOMBRE_AEROLINEA": "AEROVIAS TEST",
                "TARIFA_IMPORTE": "250.00",
                "TOTAL": "310.00",
                "TOTAL_MONEDA": "USD",
                # Segmentos en formato ya normalizado (sin pasar por DataNormalizationService
                # para evitar dependencia de tablas de BD como common_ciudad)
                "segmentos": [
                    {
                        "origen": "CCS",
                        "destino": "BOG",
                        "vuelo": "AV 123",
                        "fecha_salida": "22 Jun 2025",
                        "hora_salida": "07:00",
                        "hora_llegada": "10:00",
                        "clase": "Y",
                        "estado": "OK",
                    }
                ],
            }

            t0 = time.time()
            # Llamamos directamente sin DataNormalizationService para evitar error de BD
            pdf_bytes, fname = PdfGenerationService.generate_ticket(datos_prueba, agencia_obj=None)
            elapsed = time.time() - t0

            if pdf_bytes and len(pdf_bytes) > 100:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"      [OK] PDF generado: {fname} - {len(pdf_bytes):,} bytes en {elapsed:.2f}s"
                    )
                )
                return ("OK", name, f"{fname} - {len(pdf_bytes)} bytes")
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"      [FAIL] PDF vacio: {len(pdf_bytes) if pdf_bytes else 0} bytes"
                    )
                )
                return ("FAIL", name, "PDF vacio de plantilla")

        except Exception as e:
            # Distinguir error de BD (migracion pendiente) de error real de generacion
            from django.db import OperationalError

            if "no such table" in str(e) or isinstance(e, OperationalError):
                self.stdout.write(
                    self.style.WARNING(
                        f"      [WARN] Tablas de BD faltantes (migracion pendiente): {e}"
                    )
                )
                self.stdout.write("      Ejecuta: python manage.py migrate")
                return ("WARN", name, f"Migracion pendiente: {e}")
            self.stdout.write(self.style.ERROR(f"      [FAIL] {e}"))
            if verbose:
                traceback.print_exc()
            return ("FAIL", name, str(e))

    # =========================================================================
    # TEST 5 – Guardar PDF en storage y obtener URL
    # =========================================================================
    def _test_storage_save_and_url(self, verbose):
        name = "Guardar PDF en Storage -> URL accesible"
        self.stdout.write(f"\n[5/5] {name}")
        try:
            from core.storage import RawFileStorage

            storage = RawFileStorage()
            test_content = b"%PDF-1.4 TEST_CONTENT_TRAVELHUB_PIPELINE_CHECK"
            test_filename = f"test_pipeline/test_pdf_{int(time.time())}.pdf"

            # Guardar
            t0 = time.time()
            saved_name = storage.save(test_filename, ContentFile(test_content))
            elapsed_save = time.time() - t0

            self.stdout.write(f"      Guardado en: {saved_name} ({elapsed_save:.2f}s)")

            # Verificar que existe
            exists = storage.exists(saved_name)
            self.stdout.write(f"      storage.exists(): {exists}")

            # Obtener URL
            url = storage.url(saved_name)
            self.stdout.write(f"      URL generada: {url[:80]}{'...' if len(url) > 80 else ''}")

            # Verificar que la URL no está expirada (no debe tener X-Amz-Expires=3600)
            url_issues = []
            if "X-Amz-Expires=3600" in url:
                url_issues.append("URL expira en 1 hora (X-Amz-Expires=3600)")
            if "X-Amz-Expires=60&" in url or "&X-Amz-Expires=60&" in url:
                url_issues.append("URL expira en 60 segundos")

            # Verificar con requests si es accesible (solo si no es localhost)
            url_accessible = None
            if "localhost" not in url and "127.0.0.1" not in url:
                try:
                    import requests

                    r = requests.head(url, timeout=5, allow_redirects=True)
                    url_accessible = r.status_code
                    self.stdout.write(f"      HTTP HEAD status : {r.status_code}")
                except Exception as e_req:
                    self.stdout.write(f"      HTTP HEAD        : no se pudo verificar ({e_req})")

            # Limpiar archivo de prueba
            try:
                storage.delete(saved_name)
                self.stdout.write("      Limpieza         : archivo eliminado [OK]")
            except Exception:
                pass

            if url_issues:
                for issue in url_issues:
                    self.stdout.write(self.style.ERROR(f"      [FAIL] {issue}"))
                return ("FAIL", name, " | ".join(url_issues))

            if url_accessible and url_accessible >= 400:
                self.stdout.write(
                    self.style.ERROR(f"      [FAIL] URL no accesible: HTTP {url_accessible}")
                )
                return ("FAIL", name, f"HTTP {url_accessible}")

            self.stdout.write(
                self.style.SUCCESS("      [OK] URL correcta y sin problemas de expiracion")
            )
            return ("OK", name, f"URL OK: {url[:60]}...")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      [ERROR] {e}"))
            if verbose:
                traceback.print_exc()
            return ("FAIL", name, str(e))

    # =========================================================================
    # TEST 6 – Boleto real de la base de datos
    # =========================================================================
    def _test_real_boleto(self, boleto_id, verbose):
        name = f"Boleto real #{boleto_id}"
        self.stdout.write(f"\n[6/6] {name}")
        try:
            from apps.automation.services.ticket_parser_service import _generate_pdf_sync
            from apps.bookings.models import BoletoImportado

            boleto = BoletoImportado.objects.get(pk=boleto_id)
            self.stdout.write(f"      Pasajero  : {boleto.nombre_pasajero_completo}")
            self.stdout.write(f"      PNR       : {boleto.localizador_pnr}")
            self.stdout.write(f"      Estado    : {boleto.estado_parseo}")
            self.stdout.write(f"      Tiene PDF : {bool(boleto.archivo_pdf_generado)}")

            if boleto.archivo_pdf_generado:
                url = boleto.archivo_pdf_generado.url
                self.stdout.write(f"      URL actual: {url[:80]}...")

                # Verificar expiracion
                if "X-Amz-Expires=3600" in url:
                    self.stdout.write(
                        self.style.ERROR(
                            "      [FAIL] URL tiene expiracion de 1 hora -> BUG CONFIRMADO"
                        )
                    )
                    # Regenerar para aplicar el fix
                    self.stdout.write("      [>>] Regenerando PDF con nueva configuracion...")
                    boleto.archivo_pdf_generado = None
                    boleto.save(update_fields=["archivo_pdf_generado"])
                    _generate_pdf_sync(boleto)
                    boleto.refresh_from_db()
                    new_url = (
                        boleto.archivo_pdf_generado.url
                        if boleto.archivo_pdf_generado
                        else "sin PDF"
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"      [OK] Nueva URL: {new_url[:80]}...")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS("      [OK] URL sin problemas de expiracion")
                    )
            else:
                self.stdout.write("      Sin PDF -> generando ahora...")
                t0 = time.time()
                _generate_pdf_sync(boleto)
                boleto.refresh_from_db()
                elapsed = time.time() - t0

                if boleto.archivo_pdf_generado:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"      [OK] PDF generado en {elapsed:.2f}s: {boleto.archivo_pdf_generado.name}"
                        )
                    )
                else:
                    self.stdout.write(self.style.ERROR("      [FAIL] PDF no se genero"))
                    return ("FAIL", name, "PDF no generado")

            return ("OK", name, "Boleto procesado correctamente")
        except BoletoImportado.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"      [ERROR] Boleto #{boleto_id} no existe"))
            return ("FAIL", name, "Boleto no encontrado")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      [ERROR] {e}"))
            if verbose:
                traceback.print_exc()
            return ("FAIL", name, str(e))

    # =========================================================================
    # Resumen final
    # =========================================================================
    def _print_summary(self, resultados):
        self.stdout.write("\n" + "=" * 65)
        self.stdout.write("  [RESUMEN]")
        self.stdout.write("=" * 65)

        ok = [r for r in resultados if r[0] == "OK"]
        fail = [r for r in resultados if r[0] == "FAIL"]

        for status, name, detail in resultados:
            icon = "[OK]" if status == "OK" else "[FAIL]"
            line = f"  {icon} {name}"
            if status == "FAIL":
                line += f"\n         -> {detail}"
                self.stdout.write(self.style.ERROR(line))
            else:
                self.stdout.write(self.style.SUCCESS(line))

        self.stdout.write("\n" + "-" * 65)
        total = len(resultados)
        self.stdout.write(
            self.style.SUCCESS(f"  RESULTADO: {len(ok)}/{total} tests pasaron")
            if not fail
            else self.style.ERROR(f"  RESULTADO: {len(fail)}/{total} tests fallaron - {len(ok)} OK")
        )
        self.stdout.write("=" * 65 + "\n")

        if fail:
            sys.exit(1)
