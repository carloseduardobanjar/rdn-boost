#!/usr/bin/env bash
set -euo pipefail

PAYLOAD="${1:-cluster/condor_payload.tar.gz}"

if [[ ! -d ".venv" ]]; then
  echo "Erro: .venv nao encontrado. Crie/instale o ambiente antes de empacotar." >&2
  exit 1
fi

mkdir -p "$(dirname "$PAYLOAD")"
rm -f "$PAYLOAD"

tar -czf "$PAYLOAD" \
  .venv \
  train_mulval_exec_code.py \
  evaluate_threshold.py \
  cluster/run_one_experiment.py \
  cluster/experiments.csv

ls -lh "$PAYLOAD"
