#!/bin/bash

# O script agora espera que o primeiro argumento seja a probabilidade de dados faltantes (0.0 a 1.0)
# Os argumentos subsequentes serão repassados para o treino (depth, size, etc.)

MISSING_PROB=$1
shift 1 # Remove a probabilidade da lista de argumentos para não confundir o python do treino

echo "==== INÍCIO DO JOB ===="
date
echo "Probabilidade de dados faltantes: $MISSING_PROB"
echo "Argumentos de treino: $@"

# Define o diretório base do projeto [cite: 30]
BASE_DIR="/home/users/cschuller/rdn-boost/experimentos_land3"
cd $BASE_DIR

# Ativa o ambiente virtual
source /home/users/cschuller/ambiente_land/bin/activate

# 1. GERAÇÃO DO DATASET
# Criamos um diretório temporário único para este nível de ruído para evitar conflitos
DATASET_TMP="dataset_p${MISSING_PROB}"
mkdir -p $DATASET_TMP

echo "--- Gerando folds com missing_prob=$MISSING_PROB ---"
python3 generate_folds.py \
    --folds 5 \
    --instances 50 \
    --output "./$DATASET_TMP" \
    --missing_prob $MISSING_PROB

# 2. EXECUÇÃO DO TREINAMENTO (Cross-Validation)
# O parâmetro --data_path é forçado para o diretório que acabamos de criar [cite: 96, 110]
echo "--- Iniciando treinamento RDN-Boost ---"
python3 -u run_rdn_cv_simplified.py \
    "$@" \
    --data_path "./$DATASET_TMP"

# 3. LIMPEZA
# Remove o dataset temporário após o treino para economizar espaço em disco
rm -rf "./$DATASET_TMP"

echo "==== FIM DO JOB ===="
date