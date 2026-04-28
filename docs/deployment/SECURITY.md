# TravelHub Seguridad

Este documento resume controles actuales y hoja de ruta de endurecimiento.

## Estado Actual (Backend)
- Autenticación: Session + Token DRF (legacy) + JWT (access/refresh rotativos, blacklist logout).
- Permisos: CRUD protegido por `IsStaffOrGroupWrite` y object-level en ventas (`creado_por`).
- Auditoría: CREATE/UPDATE/DELETE/STATE con diffs + IP/User-Agent + hash chain (SHA-256) encadenando cada `AuditLog` (`previous_hash` y `record_hash`). Comando `python manage.py verify_audit_chain` valida integridad.
- CORS restrictivo aplicado (allowlist configurable por `.env`).
- Throttling: user/anon + scope `login` (rate limit específico).
- Healthcheck `/api/health/` para monitoreo.
- Cabeceras seguridad: X-Content-Type-Options, Referrer-Policy, Permissions-Policy, X-Frame-Options, CSP ENFORCE con nonce.
- Logout JWT implementado (blacklist refresh).
- Falta: scrubbing PII avanzado, métricas centralizadas, antivirus uploads.

## Próximos Controles (Prioridad Alta)
1. Integrar pipeline CI (pytest+coverage, lint, pip-audit, npm audit).
2. Scrubbing PII en logs (emails, docs) + logging estructurado JSON.
3. Hash chain en AuditLog + verificador integridad.
4. Antivirus / malware scan en uploads (ClamAV/opcional servicio SaaS).
5. Rate limit adaptativo + Redis backend multi-nodo.
6. Observabilidad: métricas (Prometheus) + alertas (latencia, 5xx, auth_fail).

## Frontend Seguridad Actual
- CSP enforce con nonce para scripts (sin `unsafe-inline` en scripts). Eliminación completa de inline styles y tests que aseguran: (a) no existen atributos style=, (b) todos los <script> inline tienen nonce, (c) el nonce del DOM coincide con la cabecera CSP.
- Headers server-side consistentes (no duplicar en reverse proxy).
- Roadmap: eliminar `unsafe-inline` en `style-src` (migrar a clases utilitarias / hashed styles).

## Roadmap Medio Plazo
- JWT corto + refresh cookie httpOnly o session backend + rotación.
- Content Security Policy estricta.
- Rate limit dinámico (Redis backend) + bloqueo temporal tras múltiples intentos.
- Escaneo SCA continuo (Dependabot / Renovate).
- Centralización de logs (ELK o Loki) con scrubbing de PII.
- Alertas anómalas (Sentry / Prometheus métricas auth).

## Buenas Prácticas Recomendadas
- Nunca subir secrets a VCS (usar .env + gestor de secretos en PROD).
- Revisar permisos de base de datos (principio de menor privilegio).
- Revisiones de código enfocadas en: inyección, exposición de datos, mass assignment.
- Tests automáticos para endpoints críticos (auth, creación de ventas, auditoría).

## Checklist Rápido (Tick al implementar)
- [x] CORS restrictivo
- [x] DRF throttling básico + scope login
- [x] Rate limit login
- [x] Headers seguridad backend (CSP enforce con nonce)
- [x] HTTPS forzado PROD (settings condicionales)
- [x] Object-level permisos ventas
- [x] IP + UA en AuditLog
- [x] JWT (short-lived + refresh rotativo + logout)
- [ ] Escaneo dependencias CI
- [x] Eliminación `unsafe-inline` en style-src (todas las plantillas sin atributos style=; test global lo garantiza)
- [ ] Antivirus uploads
- [x] Hash chain auditoría (verificación integridad y tests de detección tampering)
- [ ] Logging estructurado + scrubbing PII

## Contacto Seguridad
Reportes internos: security@travelhub.local (definir alias oficial).

## Notas Hash Chain Auditoría
Implementación: cada `AuditLog` almacena `previous_hash` (hash del registro anterior en orden cronológico) y `record_hash` calculado como SHA-256("{previous_hash}|{payload_json_canonico}"). El payload canónico incluye: modelo, object_id, accion, descripcion, datos_previos, datos_nuevos, metadata_extra y timestamp `creado` ISO8601.

Backfill: migración `0015_auditlog_hash_chain` calcula hashes para registros históricos en orden (creado, id). El primer bloque tiene `previous_hash = NULL` y su `record_hash` se deriva de la cadena vacía.

Verificación: comando `python manage.py verify_audit_chain` recorre la secuencia, recalcula y detecta (a) mismatch de `previous_hash` o (b) discrepancia de `record_hash`. Devuelve código de salida != 0 ante ruptura.

Limitaciones: no previene eliminación física de filas (rompería la cadena sin evidencia si se remueven también subsecuentes). Mitigaciones futuras: snapshot del último hash en almacenamiento WORM/externo, firma HMAC de cada `record_hash`, anclaje periódico (ej. publicar hash raíz en un canal externo).

Tests: `tests/test_audit_hash_chain.py` cubre creación secuencial y detección de tampering modificando descripción sin recalcular hash.
