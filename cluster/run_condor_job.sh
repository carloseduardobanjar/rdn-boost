#!/usr/bin/env bash
set -euo pipefail

JOB_ID="${1:?uso: run_condor_job.sh <job_id>}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

echo "==== INICIO ===="
date
echo "Host: $(hostname)"
echo "Repo: $REPO_ROOT"
echo "Job: $JOB_ID"
echo "Python: $(command -v python)"

python -u cluster/run_one_experiment.py \
  --manifest cluster/experiments.csv \
  --job_id "$JOB_ID" \
  --results_root cluster/results \
  --clean

echo "==== FIM ===="
date
