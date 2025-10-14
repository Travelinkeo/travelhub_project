# core/throttling.py
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class DashboardRateThrottle(UserRateThrottle):
    """Rate limit específico para dashboard (más permisivo)"""
    scope = 'dashboard'
    rate = '100/hour'


class LiquidacionRateThrottle(UserRateThrottle):
    """Rate limit para operaciones de liquidación"""
    scope = 'liquidacion'
    rate = '50/hour'


class ReportesRateThrottle(UserRateThrottle):
    """Rate limit para generación de reportes (más restrictivo)"""
    scope = 'reportes'
    rate = '20/hour'


class UploadRateThrottle(UserRateThrottle):
    """Rate limit para uploads (pasaportes, boletos)"""
    scope = 'upload'
    rate = '30/hour'
