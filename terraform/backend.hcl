# Backend de estado de Terraform para TravelHub.
#
# Uso: terraform init -backend-config=backend.hcl
#
# Este archivo usa un bucket de ejemplo. Para producción crea/reutiliza un
# bucket GCS dedicado (p.ej. travelhub-terraform-state) y ajústalo aquí o
# pásalo vía -backend-config a un archivo gitignoreado por entorno.
bucket = "travelhub-terraform-state"
prefix = "terraform/state"
