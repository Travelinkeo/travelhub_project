import re
import os
from datetime import datetime
from PIL import Image
from django.conf import settings

try:
    import cv2
    import numpy as np
    import pytesseract
    HAS_OCR_LIBS = True
except ImportError:
    HAS_OCR_LIBS = False

class PassportOCRService:
    """Servicio para procesamiento OCR de pasaportes"""
    
    def __init__(self):
        # Configurar path de Tesseract en Windows
        if os.name == 'nt':  # Windows
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        self.patterns = {
            'passport_number': r'[A-Z]{1,2}[0-9]{6,9}',
            'mrz_line': r'[A-Z0-9<]{44}',
            'names': r'([A-Z]{2,})[<]+([A-Z<]+)',
            'date': r'([0-9]{2})([0-9]{2})([0-9]{2})',
            'nationality': r'P<([A-Z]{3})',
        }
    
    def process_passport_image(self, image_file):
        """Procesa imagen de pasaporte y extrae datos"""
        if not HAS_OCR_LIBS:
            return {
                'success': False,
                'error': 'OCR libraries not installed. Install: pip install opencv-python pytesseract',
                'data': {'numero_pasaporte': 'DEMO123456'},
                'confidence': 'LOW'
            }
            
        try:
            # Convertir a imagen PIL
            image = Image.open(image_file)
            
            # Preprocesar imagen
            processed_image = self._preprocess_image(image)
            
            # Extraer texto con OCR
            ocr_text = self._extract_text_ocr(processed_image)
            
            # Parsear datos del pasaporte
            passport_data = self._parse_passport_data(ocr_text)
            
            # Calcular confianza
            confidence = self._calculate_confidence(passport_data)
            
            return {
                'success': True,
                'data': passport_data,
                'confidence': confidence,
                'raw_text': ocr_text,
                'errors': []
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': {'numero_pasaporte': f'ERROR_{str(e)[:10]}'},
                'confidence': 'LOW'
            }
    
    def _preprocess_image(self, pil_image):
        """Preprocesa imagen para mejorar OCR"""
        # Convertir PIL a OpenCV
        opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        # Redimensionar si es muy grande
        height, width = opencv_image.shape[:2]
        if width > 1200:
            scale = 1200 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            opencv_image = cv2.resize(opencv_image, (new_width, new_height))
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # Detectar y corregir rotación automáticamente
        gray = self._auto_rotate_image(gray)
        
        # Mejorar contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Reducir ruido
        denoised = cv2.medianBlur(enhanced, 3)
        
        return denoised
    
    def _auto_rotate_image(self, gray_image):
        """Detecta y corrige automáticamente la rotación de la imagen"""
        if not HAS_OCR_LIBS:
            return gray_image
            
        try:
            # Detectar líneas para determinar orientación
            edges = cv2.Canny(gray_image, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for rho, theta in lines[:10]:  # Solo primeras 10 líneas
                    angle = np.degrees(theta) - 90
                    angles.append(angle)
                
                # Calcular ángulo promedio
                median_angle = np.median(angles)
                
                # Solo rotar si el ángulo es significativo
                if abs(median_angle) > 5:
                    # Rotar imagen
                    (h, w) = gray_image.shape[:2]
                    center = (w // 2, h // 2)
                    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                    rotated = cv2.warpAffine(gray_image, rotation_matrix, (w, h), 
                                           flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                    return rotated
            
            return gray_image
        except Exception:
            # Si falla la detección, devolver imagen original
            return gray_image
    
    def _extract_text_ocr(self, processed_image):
        """Extrae texto usando Tesseract OCR"""
        # Configuración optimizada para pasaportes
        config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<'
        
        try:
            # Extraer texto
            text = pytesseract.image_to_string(processed_image, config=config, lang='eng')
            return text.upper().strip()
        except Exception as e:
            # Fallback sin configuración específica
            return pytesseract.image_to_string(processed_image, lang='eng').upper().strip()
    
    def _parse_passport_data(self, ocr_text):
        """Parsea datos del texto OCR"""
        lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        
        # Buscar líneas MRZ (Machine Readable Zone)
        mrz_lines = [line for line in lines if len(line) >= 40 and '<' in line]
        
        if len(mrz_lines) >= 2:
            return self._parse_mrz_data(mrz_lines)
        else:
            return self._parse_general_text(lines)
    
    def _parse_mrz_data(self, mrz_lines):
        """Parsea datos de la zona MRZ del pasaporte"""
        try:
            line1 = mrz_lines[0]  # P<COUNTRY<<<SURNAME<<GIVEN_NAMES
            line2 = mrz_lines[1]  # PASSPORT_NUMBER<NATIONALITY<BIRTH_DATE<SEX<EXPIRY_DATE
            
            # Extraer país y nombres de línea 1
            country_match = re.search(r'P<([A-Z]{3})', line1)
            nationality = country_match.group(1) if country_match else ''
            
            # Extraer nombres (después del país)
            names_part = line1[5:]  # Saltar "P<VEN"
            names_split = names_part.split('<<')
            surname = names_split[0].replace('<', ' ').strip() if names_split else ''
            given_names = names_split[1].replace('<', ' ').strip() if len(names_split) > 1 else ''
            
            # Extraer datos de línea 2
            passport_num = line2[:9].replace('<', '').strip()
            birth_date = self._parse_mrz_date(line2[13:19])
            sex = line2[20] if len(line2) > 20 else ''
            expiry_date = self._parse_mrz_date(line2[21:27])
            
            return {
                'numero_pasaporte': passport_num,
                'apellidos': surname,
                'nombres': given_names,
                'nacionalidad': nationality,
                'fecha_nacimiento': birth_date,
                'fecha_vencimiento': expiry_date,
                'sexo': sex,
                'texto_mrz': '\n'.join(mrz_lines)
            }
            
        except Exception as e:
            return {'error': f'Error parseando MRZ: {str(e)}'}
    
    def _parse_general_text(self, lines):
        """Parsea datos de texto general (fallback)"""
        data = {}
        
        # Buscar número de pasaporte
        for line in lines:
            passport_match = re.search(self.patterns['passport_number'], line)
            if passport_match:
                data['numero_pasaporte'] = passport_match.group(0)
                break
        
        # Buscar fechas (formato DDMMYY)
        dates_found = []
        for line in lines:
            date_matches = re.findall(r'\b([0-9]{2})([0-9]{2})([0-9]{2})\b', line)
            for match in date_matches:
                parsed_date = self._parse_mrz_date(''.join(match))
                if parsed_date:
                    dates_found.append(parsed_date)
        
        # Asignar fechas (primera = nacimiento, segunda = vencimiento)
        if len(dates_found) >= 2:
            data['fecha_nacimiento'] = dates_found[0]
            data['fecha_vencimiento'] = dates_found[1]
        
        return data
    
    def _parse_mrz_date(self, date_str):
        """Convierte fecha MRZ (YYMMDD) a fecha Python"""
        if len(date_str) != 6 or not date_str.isdigit():
            return None
        
        try:
            yy = int(date_str[:2])
            mm = int(date_str[2:4])
            dd = int(date_str[4:6])
            
            # Determinar siglo (asumiendo que años > 50 son 1900s, <= 50 son 2000s)
            year = 1900 + yy if yy > 50 else 2000 + yy
            
            return datetime(year, mm, dd).date()
        except ValueError:
            return None
    
    def _calculate_confidence(self, passport_data):
        """Calcula nivel de confianza basado en datos extraídos"""
        required_fields = ['numero_pasaporte', 'nombres', 'apellidos']
        found_fields = sum(1 for field in required_fields if passport_data.get(field))
        
        if found_fields == len(required_fields):
            return 'HIGH'
        elif found_fields >= 2:
            return 'MEDIUM'
        else:
            return 'LOW'