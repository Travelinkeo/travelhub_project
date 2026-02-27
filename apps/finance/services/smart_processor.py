import pandas as pd
import json
import logging
import os
import google.generativeai as genai
from decimal import Decimal
from django.conf import settings
from pydantic import BaseModel, Field
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# --- Esquema para el Mapeo de Columnas ---

class ColumnMappingSchema(BaseModel):
    numero_boleto: Optional[str] = Field(description="Column name for Ticket/Document number")
    pnr: Optional[str] = Field(description="Column name for PNR/Locator")
    pasajero: Optional[str] = Field(description="Column name for Passenger Name")
    monto_total: Optional[str] = Field(description="Column name for Total Amount")
    monto_neto: Optional[str] = Field(description="Column name for Fare/Net Amount")
    tax: Optional[str] = Field(description="Column name for Taxes")
    comision: Optional[str] = Field(description="Column name for Commission/Fee")
    fecha_emision: Optional[str] = Field(description="Column name for Issue Date")

class SmartReportProcessor:
    """
    Procesador universal de reportes que utiliza Gemini 2.0 Flash para:
    1. Detectar el formato y mapeo de columnas dinámicamente.
    2. Normalizar datos financieros de forma robusta.
    """

    @classmethod
    def parse(cls, file_path: str) -> list:
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Muestra de datos para la IA
            sample_data = df.head(5).to_json(orient='records')
            columns = list(df.columns)
            
            mapping = cls._get_smart_mapping(columns, sample_data)
            
            normalized_data = []
            for _, row in df.iterrows():
                item = {}
                for target_field, source_column in mapping.items():
                    if source_column and source_column in row:
                        val = row[source_column]
                        if target_field in ['monto_total', 'monto_neto', 'tax', 'comision']:
                            item[target_field] = cls._clean_decimal(val)
                        else:
                            item[target_field] = str(val).strip() if pd.notna(val) else None
                
                # Regla de Oro: Si falta el total pero tenemos net+tax, calculamos
                if not item.get('monto_total') and item.get('monto_neto'):
                    item['monto_total'] = item.get('monto_neto', Decimal(0)) + item.get('tax', Decimal(0))

                if item.get('numero_boleto'):
                    normalized_data.append(item)
            
            return normalized_data
        except Exception as e:
            logger.error(f"Error fatal en SmartReportProcessor: {e}")
            raise

    @classmethod
    def _get_smart_mapping(cls, columns: list, sample_json: str) -> Dict[str, Optional[str]]:
        api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            logger.warning("No API Key found for Smart Mapping, using fallback.")
            return cls._fallback_mapping(columns)

        try:
            genai.configure(api_key=api_key, transport="rest")
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": ColumnMappingSchema,
                }
            )

            prompt = f"""
            Identify which columns from the list match our standard schema based on the sample data.
            Columns: {columns}
            Sample Data: {sample_json}
            
            Schema targets:
            - numero_boleto (Ticket/Doc)
            - pnr (Locator/Record)
            - pasajero (Name)
            - monto_total (Final paid price)
            - monto_neto (Base fare)
            - tax (Taxes)
            - comision (Commission)
            - fecha_emision (Date)
            """
            
            response = model.generate_content(prompt)
            if response and response.text:
                mapping = json.loads(response.text)
                logger.info(f"AI Smart Mapping Success: {mapping}")
                return mapping
            
        except Exception as e:
            logger.error(f"AI Mapping failed: {e}. Falling back...")
        
        return cls._fallback_mapping(columns)

    @classmethod
    def _fallback_mapping(cls, columns):
        keywords = {
            'numero_boleto': ['boleto', 'ticket', 'doc', 'number', 'tkt'],
            'pnr': ['pnr', 'record', 'locator', 'resloc'],
            'pasajero': ['pasajero', 'passenger', 'name', 'nombre'],
            'monto_total': ['total', 'amount', 'cobrado'],
            'monto_neto': ['neto', 'fare', 'base'],
            'tax': ['tax', 'impuestos', 'tasa'],
            'comision': ['comision', 'comm', 'fee'],
            'fecha_emision': ['fecha', 'date', 'issue']
        }
        mapping = {}
        for field, keys in keywords.items():
            match = next((col for col in columns if any(k in col.lower() for k in keys)), None)
            mapping[field] = match
        return mapping

    @classmethod
    def _clean_decimal(cls, val):
        if pd.isna(val) or val == '': return Decimal(0)
        if isinstance(val, (int, float, Decimal)): return Decimal(str(val))
        try:
            s = str(val).split(' ')[-1] # Manejar "USD 100.00"
            s = s.replace('$', '').replace(',', '').strip()
            # Si el formato es europeo 1.000,00 -> lo detectamos si hay coma
            if ',' in str(val) and '.' not in str(val):
                s = str(val).replace(',', '.')
            return Decimal(s)
        except:
            return Decimal(0)
