import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.finance.services.ai_accounting_service import AIAccountingService
import json

def test_tools():
    print("🚀 Iniciando prueba de herramientas del Asistente Contable AI...")
    
    try:
        service = AIAccountingService()
    except Exception as e:
        print(f"❌ Error inicializando servicio: {e}")
        return

    # 1. Profitability Summary
    print("\n--- [1] Resumen de Rentabilidad ---")
    res = service.get_profitability_summary()
    print(json.dumps(json.loads(res), indent=2))

    # 2. Monthly Trends
    print("\n--- [2] Tendencias Mensuales ---")
    trends = service.get_monthly_trends()
    print(trends[:200] + "..." if len(trends) > 200 else trends)

    # 3. Category Performance
    print("\n--- [3] Rendimiento por Categoría ---")
    perf = service.get_category_performance()
    print(perf)

    # 4. Unpaid Invoices
    print("\n--- [4] Facturas Pendientes ---")
    unpaid = service.get_unpaid_invoices_summary()
    print(unpaid)

    # 5. Expenses
    print("\n--- [5] Gastos Operativos ---")
    expenses = service.get_expense_summary()
    print(expenses)

    print("\n✅ Todas las herramientas retornaron datos.")

if __name__ == "__main__":
    test_tools()
