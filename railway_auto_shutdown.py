#!/usr/bin/env python3
"""
Script para apagar/encender servicios de Railway automáticamente
Uso: python railway_auto_shutdown.py [stop|start]
"""
import subprocess
import sys

# IDs de tus servicios en Railway (obtener del dashboard)
SERVICES = {
    'web': 'SERVICE_ID_WEB',
    'worker': 'SERVICE_ID_WORKER', 
    'beat': 'SERVICE_ID_BEAT'
}

def stop_services():
    """Apagar todos los servicios"""
    print("🌙 Apagando servicios (11 PM - 7 AM)...")
    for name, service_id in SERVICES.items():
        try:
            subprocess.run(['railway', 'down', '--service', service_id], check=True)
            print(f"  ✅ {name} apagado")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Error apagando {name}: {e}")

def start_services():
    """Encender todos los servicios"""
    print("☀️ Encendiendo servicios (7 AM - 11 PM)...")
    for name, service_id in SERVICES.items():
        try:
            subprocess.run(['railway', 'up', '--service', service_id], check=True)
            print(f"  ✅ {name} encendido")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Error encendiendo {name}: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ['stop', 'start']:
        print("Uso: python railway_auto_shutdown.py [stop|start]")
        sys.exit(1)
    
    action = sys.argv[1]
    if action == 'stop':
        stop_services()
    else:
        start_services()
