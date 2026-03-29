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
mkdir -p "$JOB_DIR"
cd "$JOB_DIR"

# 2. ISOLAMENTO DO AMBIENTE (Cria uma cópia leve do VENV)
# O parâmetro --system-site-packages com o virtualenv permite criar um venv 
# que aponta para o original, mas permite escrita local no site-packages.
python3 -m venv --system-site-packages ./temp_venv
source ./temp_venv/bin/activate

# Forçamos o PYTHONPATH para garantir que o job olhe para o diretório local primeiro
export PYTHONPATH="$JOB_DIR/temp_venv/lib/python3.8/site-packages:$PYTHONPATH"

# 3. Preparação dos Dados
mkdir -p ./dataset
echo "Gerando dados em: $JOB_DIR/dataset"
python3 "$BASE_DIR/generate_folds.py" --folds 5 --instances 50 --output "./dataset" --missing_prob "$MISS_PROB"

# 4. Execução do Treino
echo "Iniciando RDN-Boost no VENV isolado..."
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