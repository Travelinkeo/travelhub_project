"""
Cliente mejorado para obtener múltiples tasas de cambio de Venezuela:
- BCV (oficial)
- Promedio (mercado)
- P2P (peer-to-peer vía Binance)
- Otras monedas (EUR, COP, etc.)
"""

import logging
from datetime import datetime
from decimal import Decimal

import requests

PY_DOLAR_VENEZUELA_AVAILABLE = False

logger = logging.getLogger(__name__)


class TasasVenezuelaClient:
    """Cliente para obtener tasas de cambio de múltiples fuentes"""

    API_URL = "https://ve.dolarapi.com/v1/dolares"
    BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    CRIPTOYA_P2P_URL = "https://criptoya.com/api/binancep2p/usdt/ves/1"
    YADIO_P2P_URL = "https://api.yadio.io/json"
    TIMEOUT = 10

    @classmethod
    def obtener_tasa_binance_p2p(cls) -> dict | None:
        """
        Obtiene la tasa P2P desde Binance (USDT/VES).
        Toma el mejor precio de venta (promedio top 3).
        """
        try:
            payload = {
                "page": 1,
                "rows": 5,
                "payTypes": [],
                "asset": "USDT",
                "fiat": "VES",
                "tradeType": "SELL",
                "publisherType": None,
            }
            logger.info(f"Consultando Binance P2P: {cls.BINANCE_P2P_URL}")
            response = requests.post(
                cls.BINANCE_P2P_URL,
                json=payload,
                timeout=cls.TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            ads = data.get("data", [])
            if not ads:
                logger.warning("Binance P2P: no se encontraron anuncios")
                return None

            prices = []
            for adv in ads:
                adv_data = adv.get("adv", {})
                price = adv_data.get("price")
                if price:
                    prices.append(Decimal(str(price)))

            if not prices:
                logger.warning("Binance P2P: no se pudieron extraer precios")
                return None

            # Promedio de los top N mejores precios
            prices.sort(reverse=True)
            top = prices[:3]
            promedio = sum(top) / len(top)

            return {
                "price": promedio.quantize(Decimal("0.01")),
                "last_update": datetime.now().isoformat(),
                "title": "Binance P2P (USDT/VES)",
                "symbol": "Bs.",
            }

        except requests.RequestException as e:
            logger.error(f"Error HTTP consultando Binance P2P: {e}")
            return None
        except Exception as e:
            logger.error(f"Error procesando respuesta Binance P2P: {e}")
            return None

    @classmethod
    def obtener_tasa_p2p_fallback(cls) -> dict | None:
        """
        Fallback secundario y terciario para la tasa P2P:
        1. CriptoYa API (proxy dedicado a Binance P2P USDT/VES)
        2. Yadio API (agregador P2P Venezuela)
        """
        # Fallback 1: CriptoYa
        try:
            logger.info(f"Consultando fallback CriptoYa P2P: {cls.CRIPTOYA_P2P_URL}")
            res = requests.get(
                cls.CRIPTOYA_P2P_URL,
                timeout=cls.TIMEOUT,
                headers={"User-Agent": "TravelHub/1.0"},
            )
            if res.status_code == 200:
                data = res.json()
                ask = data.get("ask")
                bid = data.get("bid")
                if ask and bid:
                    promedio = (Decimal(str(ask)) + Decimal(str(bid))) / Decimal("2")
                elif ask:
                    promedio = Decimal(str(ask))
                elif bid:
                    promedio = Decimal(str(bid))
                else:
                    promedio = None

                if promedio:
                    logger.info(f"Tasa P2P obtenida vía CriptoYa: {promedio}")
                    return {
                        "price": promedio.quantize(Decimal("0.01")),
                        "last_update": datetime.now().isoformat(),
                        "title": "Binance P2P (CriptoYa)",
                        "symbol": "Bs.",
                    }
        except Exception as e:
            logger.warning(f"Fallback CriptoYa P2P falló: {e}")

        # Fallback 2: Yadio
        try:
            logger.info(f"Consultando fallback Yadio P2P: {cls.YADIO_P2P_URL}")
            res = requests.get(
                cls.YADIO_P2P_URL,
                timeout=cls.TIMEOUT,
                headers={"User-Agent": "TravelHub/1.0"},
            )
            if res.status_code == 200:
                data = res.json()
                p2p_rate = data.get("USD", {}).get("other", {}).get("p2p_usdt", {}).get("rate")
                if p2p_rate:
                    monto = Decimal(str(p2p_rate))
                    logger.info(f"Tasa P2P obtenida vía Yadio: {monto}")
                    return {
                        "price": monto.quantize(Decimal("0.01")),
                        "last_update": datetime.now().isoformat(),
                        "title": "Binance P2P (Yadio)",
                        "symbol": "Bs.",
                    }
        except Exception as e:
            logger.warning(f"Fallback Yadio P2P falló: {e}")

        return None

    @classmethod
    def obtener_todas_tasas(cls) -> dict | None:
        """
        Obtiene todas las tasas disponibles desde DolarApi Venezuela
        + Binance P2P (con fallbacks).
        """
        try:
            logger.info(f"Consultando DolarApi Venezuela: {cls.API_URL}")
            response = requests.get(
                cls.API_URL, timeout=cls.TIMEOUT, headers={"User-Agent": "TravelHub/1.0"}
            )
            response.raise_for_status()

            data = response.json()

            tasas = {}

            # 1. Intentar obtener Tasa Oficial DIRECTAMENTE del BCV
            try:
                from apps.finance.services.bcv_scraper import obtener_tasas_bcv

                tasas_bcv = obtener_tasas_bcv()

                if not tasas_bcv:
                    logger.warning("Scraper BCV no pudo obtener tasas.")

                if tasas_bcv:
                    if "USD" in tasas_bcv:
                        tasas["oficial"] = {
                            "price": Decimal(str(tasas_bcv["USD"])).quantize(Decimal("0.0001")),
                            "last_update": datetime.now().isoformat(),
                            "title": "BCV Oficial",
                            "symbol": "Bs.",
                        }

                    if "EUR" in tasas_bcv:
                        tasas["euro_bcv"] = {
                            "price": Decimal(str(tasas_bcv["EUR"])).quantize(Decimal("0.0001")),
                            "last_update": datetime.now().isoformat(),
                            "title": "BCV Euro",
                            "symbol": "Bs.",
                        }

            except Exception as e:
                logger.error(f"Fallo en obtención resiliente BCV: {e}")

            # 2. Procesar datos de DolarApi
            for item in data:
                try:
                    fuente = item.get("fuente", "unknown")

                    if fuente == "oficial" and "oficial" in tasas:
                        continue

                    promedio = item.get("promedio")

                    if promedio and promedio > 0:
                        nombre_map = {
                            "oficial": "BCV Oficial",
                            "paralelo": "Dólar No Oficial",
                            "bitcoin": "Bitcoin",
                        }

                        tasas[fuente] = {
                            "price": Decimal(str(promedio)).quantize(Decimal("0.01")),
                            "last_update": item.get("fechaActualizacion", ""),
                            "title": nombre_map.get(fuente, item.get("nombre", fuente)),
                            "symbol": "Bs.",
                        }
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Error procesando item: {e}")
                    continue

            # 3. Obtener tasa Binance P2P (con fallbacks resilientes)
            p2p = cls.obtener_tasa_binance_p2p()
            if not p2p:
                logger.warning(
                    "No se pudo obtener tasa Binance P2P directa. Intentando fallbacks..."
                )
                p2p = cls.obtener_tasa_p2p_fallback()

            if p2p:
                tasas["p2p"] = p2p
                logger.info(f"Tasa P2P obtenida ({p2p.get('title', 'P2P')}): {p2p['price']}")
            else:
                logger.warning("No se pudo obtener tasa Binance P2P de ninguna fuente.")

            if tasas:
                logger.info(f"Tasas obtenidas: {len(tasas)} fuentes")
                return tasas
            else:
                logger.error("No se obtuvieron tasas válidas de ninguna fuente")
                return None

        except requests.RequestException as e:
            logger.error(f"Error HTTP consultando DolarApi: {e}")
            return None
        except Exception as e:
            logger.error(f"Error procesando respuesta: {e}")
            return None

    @classmethod
    def obtener_tasa_bcv(cls) -> Decimal | None:
        """Obtiene solo la tasa BCV oficial"""
        tasas = cls.obtener_todas_tasas()
        if tasas and "oficial" in tasas:
            return tasas["oficial"]["price"]
        return None

    @classmethod
    def obtener_tasa_paralelo(cls) -> Decimal | None:
        """Obtiene la tasa del mercado paralelo"""
        tasas = cls.obtener_todas_tasas()
        if tasas and "paralelo" in tasas:
            return tasas["paralelo"]["price"]
        return None

    @classmethod
    def obtener_tasa_bitcoin(cls) -> Decimal | None:
        """Obtiene la tasa Bitcoin"""
        tasas = cls.obtener_todas_tasas()
        if tasas and "bitcoin" in tasas:
            return tasas["bitcoin"]["price"]
        return None

    @classmethod
    def obtener_tasa_p2p(cls) -> Decimal | None:
        """Obtiene la tasa Binance P2P (USDT/VES)"""
        tasas = cls.obtener_todas_tasas()
        if tasas and "p2p" in tasas:
            return tasas["p2p"]["price"]
        return None

    @classmethod
    def actualizar_tasas_db(cls) -> dict[str, bool]:
        """
        Actualiza la tasa oficial (BCV) en la base de datos y TipoCambio (Core).

        Returns:
            Dict con resultados: {'oficial': True, 'paralelo': False, ...}
        """
        from datetime import date

        from django.core.cache import cache
        from django.utils import timezone

        from apps.common.models import Moneda
        from apps.finance.models import TasaCambioBCV
        from apps.finance.models_stubs import TasaCambio, TipoCambio

        resultados = {}
        tasas = cls.obtener_todas_tasas()

        if not tasas:
            logger.error("No se pudieron obtener tasas")
            return resultados

        hoy = date.today()

        # 1. Actualizar tabla historica TasaCambioBCV (Solo USD)
        if "oficial" in tasas:
            try:
                TasaCambioBCV.objects.update_or_create(
                    fecha=hoy,
                    defaults={
                        "tasa": tasas["oficial"]["price"],
                    },
                )
                resultados["oficial"] = True
                logger.info(f"Tasa BCV (USD) actualizada: {tasas['oficial']['price']}")
            except Exception as e:
                logger.error(f"Error guardando tasa BCV: {e}")
                resultados["oficial"] = False

        # 1.1 Actualizar tabla central TasaCambio (Caché de UI)
        now = timezone.now()
        if "oficial" in tasas:
            try:
                TasaCambio.objects.update_or_create(
                    fecha=hoy,
                    moneda="USD",
                    defaults={"monto": tasas["oficial"]["price"], "ultima_actualizacion": now},
                )
                logger.info(f"TasaCambio UI (USD) actualizada: {tasas['oficial']['price']}")
            except Exception as e:
                logger.error(f"Error guardando TasaCambio UI (USD): {e}")

        if "euro_bcv" in tasas:
            try:
                TasaCambio.objects.update_or_create(
                    fecha=hoy,
                    moneda="EUR",
                    defaults={"monto": tasas["euro_bcv"]["price"], "ultima_actualizacion": now},
                )
                logger.info(f"TasaCambio UI (EUR) actualizada: {tasas['euro_bcv']['price']}")
            except Exception as e:
                logger.error(f"Error guardando TasaCambio UI (EUR): {e}")

        # 1.2 Persistir tasa Binance P2P
        if "p2p" in tasas:
            try:
                TasaCambio.objects.update_or_create(
                    fecha=hoy,
                    moneda="P2P",
                    defaults={"monto": tasas["p2p"]["price"], "ultima_actualizacion": now},
                )
                logger.info(f"TasaCambio UI (P2P) actualizada: {tasas['p2p']['price']}")
            except Exception as e:
                logger.error(f"Error guardando TasaCambio UI (P2P): {e}")

        # Limpiar caché de la UI
        try:
            cache.delete("tasa_bcv_context")
            logger.info("Caché tasa_bcv_context eliminado")
        except Exception as cache_err:
            logger.warning(f"No se pudo limpiar caché tasa_bcv_context: {cache_err}")

        # 2. Actualizar tabla central TipoCambio (USD y EUR)
        moneda_ves = Moneda.objects.filter(codigo_iso="VES").first()

        if not moneda_ves:
            logger.error("No se encontró moneda VES para actualizar tasas.")
            return resultados

        mapa_monedas = {"oficial": "USD", "euro_bcv": "EUR"}

        for clave_tasa, codigo_iso_origen in mapa_monedas.items():
            if clave_tasa in tasas:
                try:
                    moneda_origen = Moneda.objects.filter(codigo_iso=codigo_iso_origen).first()
                    if moneda_origen:
                        valor_tasa = tasas[clave_tasa]["price"]

                        TipoCambio.objects.update_or_create(
                            moneda_origen=moneda_origen,
                            moneda_destino=moneda_ves,
                            fecha_efectiva=hoy,
                            defaults={"tasa_conversion": valor_tasa},
                        )
                        logger.info(
                            f"TipoCambio {codigo_iso_origen}->VES actualizado: {valor_tasa}"
                        )
                except Exception as e:
                    logger.error(f"Error actualizando TipoCambio {codigo_iso_origen}: {e}")

        return resultados

    @classmethod
    def obtener_resumen_tasas(cls) -> dict:
        """
        Obtiene un resumen de las tasas principales para mostrar en frontend.

        Returns:
            {
                'oficial': {'valor': Decimal, 'fecha': str, 'nombre': str},
                'paralelo': {'valor': Decimal, 'fecha': str, 'nombre': str},
                'p2p': {'valor': Decimal, 'fecha': str, 'nombre': str},
                'bitcoin': {'valor': Decimal, 'fecha': str, 'nombre': str}
            }
        """
        tasas = cls.obtener_todas_tasas()
        resumen = {}

        if not tasas:
            return resumen

        if "oficial" in tasas:
            resumen["oficial"] = {
                "valor": float(tasas["oficial"]["price"]),
                "fecha": tasas["oficial"]["last_update"],
                "nombre": "BCV Oficial",
            }

        if "paralelo" in tasas:
            resumen["paralelo"] = {
                "valor": float(tasas["paralelo"]["price"]),
                "fecha": tasas["paralelo"]["last_update"],
                "nombre": "Dólar No Oficial",
            }

        if "p2p" in tasas:
            resumen["p2p"] = {
                "valor": float(tasas["p2p"]["price"]),
                "fecha": tasas["p2p"]["last_update"],
                "nombre": "Binance P2P (USDT/VES)",
            }

        if "bitcoin" in tasas:
            resumen["bitcoin"] = {
                "valor": float(tasas["bitcoin"]["price"]),
                "fecha": tasas["bitcoin"]["last_update"],
                "nombre": "Bitcoin",
            }

        return resumen
