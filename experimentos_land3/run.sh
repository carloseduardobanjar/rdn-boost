#!/bin/bash
echo "==== INÍCIO ===="
date

# Captura os argumentos posicionais vindos do grid.sub
MISS_PROB=$1
D=$2
S=$3
E=$4
# O shift remove os 4 primeiros e deixa o resto (como --output_path) em $@
shift 4

BASE_DIR="/home/users/cschuller/rdn-boost/experimentos_land3"
cd $BASE_DIR
source /home/users/cschuller/ambiente_land/bin/activate

# Usando um nome de diretório único para evitar conflitos entre jobs simultâneos
DATASET_TMP="/tmp/dataset_p${MISS_PROB}_d${D}_s${S}_${RANDOM}"
mkdir -p "$DATASET_TMP"

echo "Gerando folds com missing_prob=${MISS_PROB}..."
python3 generate_folds.py --folds 5 --instances 50 --output "./$DATASET_TMP" --missing_prob "$MISS_PROB"

echo "Iniciando treinamento RDN-Boost..."
# Aqui passamos as flags explicitamente como o seu main() exige
python3 -u run_rdn_cv_simplified.py \
    --data_path "./$DATASET_TMP" \
    --max_depth "$D" \
    --node_size "$S" \
    --n_estimators "$E" \
    "$@"

# Limpeza
rm -rf "./$DATASET_TMP"

echo "==== FIM ===="
date