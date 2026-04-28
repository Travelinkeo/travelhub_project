"""
Script de prueba para verificar la configuración de email
Uso: python test_email.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email():
    print("Probando configuración de email...")
    print(f"Backend: {settings.EMAIL_BACKEND}")
    print(f"Host: {settings.EMAIL_HOST}")
    print(f"Port: {settings.EMAIL_PORT}")
    print(f"User: {settings.EMAIL_HOST_USER}")
    print(f"From: {settings.DEFAULT_FROM_EMAIL}")
    print("-" * 50)
    
    try:
        send_mail(
            'Test TravelHub - Sistema de Notificaciones',
            'Este es un email de prueba del sistema de notificaciones de TravelHub.',
            settings.DEFAULT_FROM_EMAIL,
            [settings.EMAIL_HOST_USER],  # Enviar a ti mismo
            fail_silently=False,
        )
        print("✓ Email enviado exitosamente!")
        print(f"Revisa tu bandeja de entrada: {settings.EMAIL_HOST_USER}")
    except Exception as e:
        print(f"✗ Error al enviar email: {e}")

if __name__ == '__main__':
    test_email()
