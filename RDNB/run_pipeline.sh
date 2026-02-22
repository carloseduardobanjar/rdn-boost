#!/bin/bash
# Recebe os parâmetros do Condor
DEPTH=$1
NODE=$2
TREES=$3
DATA_DIR="./dataset"
EXP_NAME="depth${DEPTH}_node${NODE}_trees${TREES}"

# 1. Gera o dataset (se necessário em cada nó, ou passe via transfer_input_files)
# Nota: Se o dataset for o mesmo para todos, é melhor gerá-lo uma vez na Zeus 
# e enviá-lo pronto para economizar tempo de CPU no cluster.

# 2. Roda o experimento específico
python run_rdn_cv.py \
    --data_path $DATA_DIR \
    --output_path "./${EXP_NAME}" \
    --folds 5 \
    --max_depth $DEPTH \
    --node_size $NODE \
    --n_estimators $TREES