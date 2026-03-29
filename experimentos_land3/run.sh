#!/bin/bash
echo "==== INÍCIO ===="
date

# 1. Captura os argumentos
MISS_PROB=$1
D=$2
S=$3
E=$4
shift 4

BASE_DIR="/home/users/cschuller/rdn-boost/experimentos_land3"
cd $BASE_DIR

# 2. ISOLAMENTO DE AMBIENTE (O "Pulo do Gato")
# Criamos um diretório único para este processo no /tmp do nó
export JOB_UNIQUE_DIR="/tmp/cschuller_job_${MISS_PROB}_$$"
mkdir -p "$JOB_UNIQUE_DIR"

# Redirecionamos o HOME e TMP para este diretório único.
# O srlearn usará isso para criar as pastas 'bsrl_data' sem colidir com outros jobs.
export HOME="$JOB_UNIQUE_DIR"
export TMPDIR="$JOB_UNIQUE_DIR"

source /home/users/cschuller/ambiente_land/bin/activate

# 3. Execução
DATASET_TMP="$JOB_UNIQUE_DIR/dataset"
mkdir -p "$DATASET_TMP"

echo "Gerando dados em: $DATASET_TMP"
python3 generate_folds.py --folds 5 --instances 50 --output "$DATASET_TMP" --missing_prob "$MISS_PROB"

echo "Iniciando RDN-Boost..."
python3 -u run_rdn_cv_simplified.py \
    --data_path "$DATASET_TMP" \
    --max_depth "$D" \
    --node_size "$S" \
    --n_estimators "$E" \
    "$@"

# 4. LIMPEZA TOTAL
rm -rf "$JOB_UNIQUE_DIR"

echo "==== FIM ===="
date