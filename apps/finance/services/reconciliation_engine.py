import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.conf import settings

from core.services.ai_engine import ai_engine
from core.models.ai_schemas import ConciliacionLoteSchema
from core.prompts import RECONCILIATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class SmartReconciliator:
    """
    MOTOR HÍBRIDO DE CONCILIACIÓN FINANCIERA (IA + DETERMINÍSTICO):
    Diseñado para procesar miles de registros de proveedores (BSP, GDS, Consolidadores)
    y cruzarlos contra la base de datos local de TravelHub.
    
    Arquitectura:
    1. Fase Determinística: Match de alta velocidad O(n) sobre identificadores únicos.
    2. Fase AI Fuzzy: Inferencia semántica para resolver lo que el algoritmo ignora.
    """

    def conciliar_lote(self, lote_proveedor: List[Dict], ventas_agencia: List[Dict]) -> Dict[str, Any]:
        """
        Ejecuta el cruce de reconciliación entre el reporte del proveedor y las ventas locales.
        
        Args:
            lote_proveedor: Lista de cobros reportados (numero_boleto, pnr, pasajero, monto, ruta, etc.)
            ventas_agencia: Lista de candidatos en TravelHub (id, numero_boleto, pnr, pasajero, monto, ruta, etc.)
        """
        if not lote_proveedor:
            return {"matches": [], "huerfanos": [], "alertas": ["Reporte vacío."]}

        logger.info(f"⚖️ Iniciando Conciliación Inteligente: {len(lote_proveedor)} ítems del proveedor.")

        # --- FASE 1: CRUCE DETERMINÍSTICO (PANDAS SPEED) ---
        df_p = pd.DataFrame(lote_proveedor)
        df_a = pd.DataFrame(ventas_agencia) if ventas_agencia else pd.DataFrame(columns=['id', 'numero_boleto', 'pnr', 'monto'])

        # Normalización de llaves (Últimos 10 dígitos del boleto para ignorar prefijos de aerolínea variables)
        def _clean_ticket(val):
            s = str(val).replace("-", "").strip()
            return s[-10:] if len(s) >= 10 else s

        df_p['key'] = df_p['numero_boleto'].apply(_clean_ticket)
        if not df_a.empty:
            df_a['key'] = df_a['numero_boleto'].apply(_clean_ticket)
            
            # Cruce exacto por Ticket
            match_exacto = pd.merge(df_p, df_a, on='key', how='inner', suffixes=('_prov', '_agen'))
        else:
            match_exacto = pd.DataFrame()

        matches_finales = []
        cruzados_prov_ids = set()
        cruzados_agen_ids = set()

        for _, row in match_exacto.iterrows():
            dif = Decimal(str(row['monto_prov'])) - Decimal(str(row['monto_agen']))
            matches_finales.append({
                "venta_id": int(row['id']),
                "proveedor_item_id": str(row['numero_boleto_prov']),
                "diferencia_monto": float(dif),
                "confianza": 1.0,
                "comentario": "Match determinístico exactos por número de boleto."
            })
            cruzados_prov_ids.add(row['numero_boleto_prov'])
            cruzados_agen_ids.add(row['id'])

        # Identificar rezagados para la Fase 2 (IA)
        pendientes_prov = df_p[~df_p['numero_boleto'].isin(cruzados_prov_ids)]
        pendientes_agen = df_a[~df_a['id'].isin(cruzados_agen_ids)] if not df_a.empty else pd.DataFrame()

        # --- FASE 2: AI FUZZY MATCHING (AUDITORÍA SEMÁNTICA) ---
        huerfanos = []
        alertas = []

        if not pendientes_prov.empty and not pendientes_agen.empty:
            logger.info(f"🤖 Activando Auditor IA para {len(pendientes_prov)} discrepancias financieras.")
            
            # Formatear para Gemini (Compacto para ahorrar tokens)
            lista_ia_prov = pendientes_prov[['numero_boleto', 'pasajero', 'pnr', 'monto', 'ruta']].to_dict('records')
            lista_ia_agen = pendientes_agen[['id', 'numero_boleto', 'pasajero', 'pnr', 'monto', 'ruta']].to_dict('records')

            prompt_data = f"LISTA_PROVEEDOR:\n{lista_ia_prov}\n\nLISTA_AGENCIA:\n{lista_ia_agen}"
            
            try:
                resultado_ia = ai_engine.call_gemini(
                    prompt=prompt_data,
                    response_schema=ConciliacionLoteSchema,
                    system_instruction=RECONCILIATION_SYSTEM_PROMPT,
                    temperature=0.0
                )
                
                # Mezclar resultados de IA
                matches_finales.extend(resultado_ia.get("matches", []))
                huerfanos.extend(resultado_ia.get("huerfanos", []))
                alertas.extend(resultado_ia.get("alertas_fraude", []))
                
                # IDs que ya fueron procesados por la IA para no duplicar en huerfanos manuales
                ai_match_prov_ids = {m["proveedor_item_id"] for m in resultado_ia.get("matches", [])}
                ai_huerfano_prov_ids = {h["proveedor_item_id"] for h in resultado_ia.get("huerfanos", [])}
                
                # Filtrar lo que quede realmente solo del proveedor (no procesado por IA)
                final_orphans = pendientes_prov[
                    ~pendientes_prov['numero_boleto'].isin(ai_match_prov_ids) & 
                    ~pendientes_prov['numero_boleto'].isin(ai_huerfano_prov_ids)
                ]
                for _, row in final_orphans.iterrows():
                    huerfanos.append({
                        "proveedor_item_id": str(row['numero_boleto']),
                        "pasajero": str(row['pasajero']),
                        "monto": float(row['monto']),
                        "causa_probable": "No se encontró coincidencia ni determinística ni por IA."
                    })

            except Exception as e:
                logger.error(f"❌ Fallo en Auditoría IA: {e}")
                alertas.append(f"Error en motor de auditoría inteligente: {str(e)}")
                # Si falla la IA, todo lo pendiente es huérfano por ahora
                for _, row in pendientes_prov.iterrows():
                    huerfanos.append({
                        "proveedor_item_id": str(row['numero_boleto']),
                        "pasajero": str(row['pasajero']),
                        "monto": float(row['monto']),
                        "causa_probable": "Fallo de motor IA - Pendiente revisión anual."
                    })
        else:
            # Si no hay ventas locales contra las cuales comparar, todo lo del proveedor es huérfano
            for _, row in pendientes_prov.iterrows():
                huerfanos.append({
                    "proveedor_item_id": str(row['numero_boleto']),
                    "pasajero": str(row['pasajero']),
                    "monto": float(row['monto']),
                    "causa_probable": "No existen ventas locales cargadas para este período."
                })

        return {
            "success": True,
            "matches": matches_finales,
            "huerfanos": huerfanos,
            "alertas": alertas,
            "metricas": {
                "tasa_exito": len(matches_finales) / len(lote_proveedor) if lote_proveedor else 0,
                "items_conciliados": len(matches_finales),
                "items_huerfanos": len(huerfanos)
            }
        }
