# Changelog

## 1.0.0 (2026-06-15)

- Initial release: TravelHub SaaS Platform
- Multi-GDS ticket parsing (Sabre, Amadeus, KIU, Copa, Wingo, TK Connect)
- VEN-NIF tax-compliant invoicing
- CRM with Kanban, marketing automation, CMS
- AI-powered ticket parsing with Google Gemini
- Stripe subscription billing (FREE/BASIC/PRO/ENTERPRISE)
- Multi-tenant architecture with Row-Level Security
- Real-time analytics and BI dashboards
- WhatsApp/Email/Telegram notifications
- Production-ready Docker, CI/CD, monitoring

## 1.0.1 (2026-06-15)

- Limpieza de archivos temporales y scripts de depuración
- Corrección de bloque HSTS duplicado en settings.py
- Nombres únicos para cookies de sesión/CSRF (th_sessionid, th_csrftoken)
- CSP tests actualizados
- Nuevo linter de dependencias (check_domain_imports.py)
- Configuración de ruff consolidada en .ruff.toml
- UNFOLD config extraído a settings_unfold.py
- Migraciones de core squashed (41 → 1)
- .gitignore ampliado para excluir scripts sensibles y artefactos
- CHANGELOG.md inicial
