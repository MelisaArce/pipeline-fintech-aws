#!/bin/bash
set -e

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
CHECK_SCRIPT="check_data.py"
LOCAL_DATA_PATH="./data/processed_local"
CONTAINER_IMAGE="python:3.10-slim"

echo "===================================================================="
echo "🔬 Iniciando Validación de Datos Parquet Procesados"
echo "===================================================================="

# 1. Ejecutar el script dentro de un contenedor Docker temporal
echo "1/2. Ejecutando la validación en un contenedor Docker ($CONTAINER_IMAGE)..."

# Comando Docker:
# --rm: elimina el contenedor al finalizar
# -v: monta la carpeta local con los Parquets en /data_to_check dentro del contenedor
# -w: establece el directorio de trabajo (donde está el script Python)
# bash -c: ejecuta comandos secuenciales: instala dependencias y luego ejecuta el script.
docker run --rm \
    -v "$(pwd)/$LOCAL_DATA_PATH:/data_to_check" \
    -v "$(pwd)/$CHECK_SCRIPT:/$CHECK_SCRIPT" \
    -w / \
    $CONTAINER_IMAGE \
    bash -c "pip install pandas pyarrow tabulate --break-system-packages && python3 $CHECK_SCRIPT"

# 2. Limpieza
echo "2/2. Eliminando script temporal."
rm $CHECK_SCRIPT

echo "===================================================================="
echo "✅ Validación Finalizada."
echo "===================================================================="