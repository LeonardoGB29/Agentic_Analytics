#!/usr/bin/env bash
#
# run_all.sh - Pipeline completo de carga de datos en el master EMR:
#   1. local -> S3
#   2. (opcional) borra el local para liberar disco  [DELETE_LOCAL=1]
#   3. S3 -> HDFS
#   4. crea las tablas externas en Hive
#
# Uso (EN el master):
#   bash run_all.sh                 # no borra el local
#   DELETE_LOCAL=1 bash run_all.sh  # borra el local tras subir a S3
#
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "########## 1/4  Subiendo a S3 ##########"
bash "$DIR/01_upload_s3.sh"

if [ "${DELETE_LOCAL:-0}" = "1" ]; then
  echo ""
  echo "########## (2/4) Liberando disco: borrando copia local ##########"
  rm -rf "${LOCAL_DIR:-/home/hadoop/tpcds_data}"
  echo ">> Local borrado."
fi

echo ""
echo "########## 3/4  S3 -> HDFS ##########"
bash "$DIR/02_s3_to_hdfs.sh"

echo ""
echo "########## 4/4  Creando tablas en Hive ##########"
hive -f "$DIR/03_create_tables.sql"

echo ""
echo ">> Pipeline completo."
