#!/usr/bin/env bash
set -euo pipefail

JOB_ID="${1:?uso: run_condor_archive_job.sh <job_id>}"

if [[ -f "condor_payload.tar.gz" ]]; then
  tar -xzf condor_payload.tar.gz
fi

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

if [[ -x ".venv/bin/python" ]]; then
  PYTHON="./.venv/bin/python"
else
  PYTHON="$(command -v python)"
fi

echo "==== INICIO ===="
date
echo "Host: $(hostname)"
echo "Workdir: $(pwd)"
echo "Job: $JOB_ID"
echo "Python: $PYTHON"

"$PYTHON" -u cluster/run_one_experiment.py \
  --manifest cluster/experiments.csv \
  --job_id "$JOB_ID" \
  --results_root results \
  --clean

echo "==== FIM ===="
date
