# CONTEXT_MAP.md -- Mapa Cerebral de TravelHub

> Ultima verificacion contra codigo real: 2026-07-26
> Rama/commit revisado: hardening/operational-risks @ 7bd8fae6
> Verificado por: IA -- Antigravity -- lectura directa de archivos en sesion activa

---

## PROTOCOLO DE LECTURA PARA OTRA IA

Este documento describe codigo real verificado en esta sesion. Cada afirmacion esta respaldada por lectura directa de archivos. Donde hay incertidumbre, se usa [VERIFICAR].

Regla de uso: Si vas a modificar algo descrito aqui, lee el archivo original antes. Los archivos siempre son la fuente de verdad.

---

## 1. PROPOSITO DEL SISTEMA

TravelHub es un CRM/ERP SaaS B2B multi-tenant para agencias de viajes venezolanas. Cada instancia de cliente (agencia) corre en el mismo servidor Django pero con datos 100% aislados mediante Row-Level Security (RLS) a nivel de ORM y PostgreSQL.

## PLANES SAAS (verificado en travelhub/settings/base.py:527-537 -- SAAS_PLAN_LIMITS)

FREE: 1 usuario, 20 ventas/mes, 100 MB storage
BASIC: 2 usuarios, 50 ventas/mes, 500 MB storage
PRO: 10 usuarios, 500 ventas/mes, 5 GB storage
ENTERPRISE: 999 usuarios, ilimitado, ilimitado
