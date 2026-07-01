#!/usr/bin/env bash
#
# 02_s3_to_hdfs.sh
# Copia los datos de S3 a HDFS con s3-dist-cp (copia distribuida via MapReduce,
# la herramienta optimizada de EMR). Preserva la estructura <tabla>/<tabla>.dat.
#
# Se ejecuta EN el master del cluster.
#
set -euo pipefail

# Cargar variables desde deploy.env si existe
DIR_ACTUAL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$DIR_ACTUAL/../deploy.env" ]; then
    source "$DIR_ACTUAL/../deploy.env"
fi

# Si se definió S3_BUCKET, extraer el nombre del bucket limpiando s3://
if [ -n "${S3_BUCKET:-}" ]; then
    BUCKET="$(echo "$S3_BUCKET" | sed 's#s3://##')"
else
    BUCKET="${BUCKET:-tpcds-bigdata-unsa-2026-lgaona}"
fi

S3_PREFIX="${S3_PREFIX:-s3://$BUCKET/tpcds/data}"
HDFS_DIR="${HDFS_DIR:-/user/hadoop/tpcds/data}"

echo ">> Preparando HDFS: $HDFS_DIR"
hdfs dfs -mkdir -p "$HDFS_DIR"

echo ">> Copiando  $S3_PREFIX/  ->  hdfs://$HDFS_DIR/  (s3-dist-cp)"
s3-dist-cp --src "$S3_PREFIX/" --dest "hdfs://$HDFS_DIR/"

echo ""
echo ">> Contenido en HDFS:"
hdfs dfs -du -h "$HDFS_DIR/"
