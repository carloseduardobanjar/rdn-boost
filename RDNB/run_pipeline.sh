#!/bin/bash
# O Condor passa os argumentos $1 (depth), $2 (node), $3 (trees)
python3 run_rdn_cv.py --max_depth $1 --node_size $2 --n_estimators $3 --data_path ./dataset --output_path ./result_$1_$2_$3