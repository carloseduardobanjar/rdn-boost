#!/bin/bash
# Descompacta o ambiente e o dataset no nó escravo
tar -xzf projeto_rdn.tar.gz
tar -xzf dataset.tar.gz

# Executa o experimento
python3 run_rdn_cv.py --max_depth $1 --node_size $2 --n_estimators $3 --data_path ./dataset --output_path ./result_$1_$2_$3