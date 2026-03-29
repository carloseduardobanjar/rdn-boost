#!/bin/bash
echo "==== INÍCIO ===="
date

# 1. Captura os argumentos posicionais
MISS_PROB=$1
D=$2
S=$3
E=$4
# O shift remove os 4 primeiros ($1 a $4). O que sobrar (ex: --output_path) fica em $@
shift 4

BASE_DIR="/home/users/cschuller/rdn-boost/experimentos_land3"
cd $BASE_DIR
source /home/users/cschuller/ambiente_land/bin/activate

# 2. Criação do diretório temporário no /tmp do nó de execução
# Adicionar o $RANDOM e o ID do processo ($$) evita qualquer colisão entre jobs
DATASET_TMP="/tmp/cschuller_p${MISS_PROB}_d${D}_s${S}_${RANDOM}_$$"
mkdir -p "$DATASET_TMP"

echo "Gerando folds em: $DATASET_TMP com missing_prob=${MISS_PROB}..."
# REMOVIDO o "./" antes de $DATASET_TMP pois ele já é um caminho absoluto
python3 generate_folds.py --folds 5 --instances 50 --output "$DATASET_TMP" --missing_prob "$MISS_PROB"

echo "Iniciando treinamento RDN-Boost..."
# 3. Execução do treino
# Passamos o caminho absoluto do dataset e as flags de hiperparâmetros
python3 -u run_rdn_cv_simplified.py \
    --data_path "$DATASET_TMP" \
    --max_depth "$D" \
    --node_size "$S" \
    --n_estimators "$E" \
    "$@"

# 4. Limpeza obrigatória para não lotar o /tmp dos nós
rm -rf "$DATASET_TMP"

echo "==== FIM ===="
date