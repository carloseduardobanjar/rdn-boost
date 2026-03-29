#!/bin/bash
echo "==== INÍCIO ===="
date

MISS_PROB=$1
D=$2
S=$3
E=$4
shift 4

BASE_DIR="/home/users/cschuller/rdn-boost/experimentos_land3"
ORIGINAL_VENV="/home/users/cschuller/ambiente_land"

# 1. Cria um diretório único no /tmp do nó
JOB_DIR="/tmp/cschuller_job_${MISS_PROB}_${RANDOM}_$$"
mkdir -p "$JOB_DIR/pkgs"
cd "$JOB_DIR"

# 2. ISOLAMENTO DA BIBLIOTECA SRLEARN
# Copiamos apenas a pasta da biblioteca para o /tmp do job
# Isso garante que o srlearn escreva no bsrl_data local deste job
cp -r "$ORIGINAL_VENV/lib/python3.8/site-packages/srlearn" "$JOB_DIR/pkgs/"

# Ativamos o ambiente original
source "$ORIGINAL_VENV/bin/activate"

# FORÇAMOS o Python a usar a cópia local do srlearn que está no /tmp
export PYTHONPATH="$JOB_DIR/pkgs:$PYTHONPATH"

# 3. Preparação dos Dados
mkdir -p ./dataset
echo "Gerando dados em: $JOB_DIR/dataset"
python3 "$BASE_DIR/generate_folds.py" --folds 5 --instances 50 --output "./dataset" --missing_prob "$MISS_PROB"

# 4. Execução do Treino
echo "Iniciando RDN-Boost com SRLEARN isolado..."
# O PYTHONPATH agora garante que o 'import srlearn' pegue a cópia do /tmp
python3 -u "$BASE_DIR/run_rdn_cv_simplified.py" \
    --data_path "./dataset" \
    --max_depth "$D" \
    --node_size "$S" \
    --n_estimators "$E" \
    "$@"

# 5. Limpeza
rm -rf "$JOB_DIR"

echo "==== FIM ===="
date