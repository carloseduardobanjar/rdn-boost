#!/usr/bin/env bash
set -euo pipefail

JOB_ID="${1:?uso: run_condor_job.sh <job_id>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/../train_mulval_exec_code.py" ]]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  REPO_ROOT="$(pwd)"
fi
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

if [[ -f "cluster/run_one_experiment.py" ]]; then
  RUNNER="cluster/run_one_experiment.py"
  MANIFEST="cluster/experiments.csv"
  RESULTS_ROOT="cluster/results"
else
  RUNNER="run_one_experiment.py"
  MANIFEST="experiments.csv"
  RESULTS_ROOT="results"
fi

python -u "$RUNNER" \
  --manifest "$MANIFEST" \
  --job_id "$JOB_ID" \
  --results_root "$RESULTS_ROOT" \
  --clean

echo "==== FIM ===="
date
