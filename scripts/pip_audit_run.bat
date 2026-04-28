@echo off
REM Simple wrapper to run pip-audit (needs installation) and output report
pip install pip-audit >NUL
pip-audit -r requirements.txt --ignore-vuln PYSEC-0000
