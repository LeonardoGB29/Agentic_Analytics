#!/usr/bin/env bash
set -euo pipefail

SCALE=10
PARALLELISM=2
LOCAL_DIR="$HOME/tpcds_data"
S3_BUCKET="s3://tpcds-bigdata-unsa-2026/data"

echo "=========================================="
echo " TPC-DS paralelo en un solo nodo"
echo " Scale: $SCALE"
echo " Paralelismo: $PARALLELISM"
echo "=========================================="

sudo dnf install -y gcc make flex bison byacc git

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
    call_center catalog_page catalog_returns catalog_sales customer
    customer_address customer_demographics date_dim household_demographics
    income_band inventory item promotion reason ship_mode store
    store_returns store_sales time_dim warehouse web_page web_returns
    web_sales web_site
)

generate_table_parallel() {
    local table=$1

    echo ">> Generando tabla: $table en paralelo ($PARALLELISM procesos)"

    for i in $(seq 1 $PARALLELISM); do
        (
            ./dsdgen \
                -SCALE "$SCALE" \
                -TABLE "$table" \
                -DIR "$LOCAL_DIR" \
                -PARALLEL "$PARALLELISM" \
                -CHILD "$i" \
                -TERMINATE N \
                -FORCE
        ) &
    done

    wait
}

for tabla in "${TABLES[@]}"; do
    echo "========================================"
    echo " Procesando $tabla"
    echo "========================================"

    generate_table_parallel "$tabla"

    file_pattern="$LOCAL_DIR/${tabla}*.dat"

    shopt -s nullglob
    files=($file_pattern)

    if [ ${#files[@]} -gt 0 ]; then
        for f in "${files[@]}"; do
            echo ">> Subiendo $f a S3..."
            aws s3 cp "$f" "${S3_BUCKET}/${tabla}/"
            rm -f "$f"
        done
    else
        echo "No se generaron archivos para $tabla"
    fi
done

echo "=========================================="
echo " Listo"
echo "=========================================="