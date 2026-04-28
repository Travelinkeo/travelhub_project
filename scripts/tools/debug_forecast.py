import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.marketing.services.forecast_service import AIForecastService

def test_forecast():
    print("Iniciando prueba de AI Forecast...")
    service = AIForecastService()
    
    print("1. Verificando datos históricos...")
    data = service.get_historical_data()
    print(f"   Mensajes de datos: {len(data)}")
    if data:
        print(f"   Ejemplo: {data[0]}")
    
    print("2. Verificando destinos top...")
    destinations = service.get_top_destinations_historical()
    print(f"   Destinos: {destinations}")
    
    print("3. Llamando a Gemini (Análisis predictivo)...")
    try:
        forecast = service.generate_forecast()
        if "error" in forecast:
            print(f"   ERROR IA: {forecast['error']}")
        else:
            print("   ÉXITO!")
            print(f"   Predicción: {forecast['predicted_sales_next_month']}")
            print(f"   Confianza: {forecast['confidence_level']}")
            print(f"   Insights: {len(forecast['strategic_insights'])}")
    except Exception as e:
        print(f"   EXCEPCIÓN: {e}")

if __name__ == "__main__":
    test_forecast()
