#!/usr/bin/env bash
set -euo pipefail

# Cargar variables desde deploy.env si existe
DIR_ACTUAL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$DIR_ACTUAL/../../deploy.env" ]; then
    source "$DIR_ACTUAL/../../deploy.env"
fi

SCALE=${SCALE:-10}
LOCAL_DIR="${LOCAL_DIR:-$HOME/tpcds_data}"
S3_BUCKET="${S3_BUCKET:-s3://tpcds-bigdata-kevin-2026}"
S3_DATA_DIR="${S3_BUCKET}/data"

echo "=========================================="
echo " Generación de datos TPC-DS secuencial"
echo " Scale: $SCALE"
echo "=========================================="

if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y gcc make flex bison byacc git
else
    sudo yum install -y gcc make flex bison byacc git
fi

cd "$HOME"

if [ ! -d tpcds-kit ]; then
    git clone https://github.com/gregrahn/tpcds-kit.git
fi

cd "$HOME/tpcds-kit/tools"

make clean
make OS=LINUX CFLAGS="-D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -DLINUX -g -Wall -fcommon"

rm -rf "$LOCAL_DIR"
mkdir -p "$LOCAL_DIR"

TABLES=(
    call_center
    catalog_page
    catalog_sales
    customer
    customer_address
    customer_demographics
    date_dim
    household_demographics
    income_band
    inventory
    item
    promotion
    reason
    ship_mode
    store
    store_sales
    time_dim
    warehouse
    web_page
    web_sales
    web_site
)

for tabla in "${TABLES[@]}"; do
    echo "========================================"
    echo " Procesando $tabla"
    echo "========================================"

    # Generar tabla secuencialmente
    ./dsdgen \
        -SCALE "$SCALE" \
        -TABLE "$tabla" \
        -DIR "$LOCAL_DIR" \
        -TERMINATE N \
        -FORCE

    file_path="$LOCAL_DIR/${tabla}.dat"

    if [ -f "$file_path" ]; then
        echo ">> Subiendo $file_path a S3..."
        aws s3 cp "$file_path" "${S3_DATA_DIR}/${tabla}/"
        rm -f "$file_path"
    else
        echo "No se generó el archivo para $tabla"
    fi
done

echo "=========================================="
echo " Listo"
echo "=========================================="
