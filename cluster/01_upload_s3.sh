#!/usr/bin/env bash
#
# 01_upload_s3.sh
# Sube cada tabla .dat a su PROPIA carpeta en S3.
# Hive exige un directorio por tabla (LOCATION apunta a un dir, no a un archivo).
#
# Se ejecuta EN el master del cluster (tiene aws CLI + rol con acceso a S3).
#
set -euo pipefail

BUCKET="${BUCKET:-tpcds-bigdata-unsa-2026-lgaona}"
LOCAL_DIR="${LOCAL_DIR:-/home/hadoop/tpcds_data}"
S3_PREFIX="${S3_PREFIX:-s3://$BUCKET/tpcds/data}"

echo ">> Origen : $LOCAL_DIR/*.dat"
echo ">> Destino: $S3_PREFIX/<tabla>/<tabla>.dat"
echo ""

shopt -s nullglob
archivos=("$LOCAL_DIR"/*.dat)
if [ ${#archivos[@]} -eq 0 ]; then
  echo "ERROR: no hay archivos .dat en $LOCAL_DIR" >&2
  exit 1
fi

count=0
for f in "${archivos[@]}"; do
  t="$(basename "$f" .dat)"
  printf '   - %-26s' "$t"
  aws s3 cp "$f" "$S3_PREFIX/$t/$t.dat" --only-show-errors
  echo "ok"
  count=$((count + 1))
done

echo ""
echo ">> $count tablas subidas. Resumen en S3:"
aws s3 ls "$S3_PREFIX/" --recursive --summarize | tail -n 3
