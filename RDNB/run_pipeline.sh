#!/bin/bash
# Descompacta o ambiente virtual enviado pelo Condor [cite: 409, 410]
tar -xzf projeto_rdn.tar.gz

# Executa o Python usando o interpretador do nó, mas com as libs do venv injetadas
python3 run_rdn_cv.py --max_depth $1 --node_size $2 --n_estimators $3 --data_path ./dataset --output_path ./result_$1_$2_$3