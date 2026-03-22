#!/bin/bash

DEPTHS=(3)
NODE_SIZES=(2)
ESTIMATORS=(5)

COUNT=1
TOTAL_COMB=$((${#DEPTHS[@]} * ${#NODE_SIZES[@]} * ${#ESTIMATORS[@]}))

echo "Iniciando Grid Search: $TOTAL_COMB combinações encontradas."

for d in "${DEPTHS[@]}"; do
    for s in "${NODE_SIZES[@]}"; do
        for e in "${ESTIMATORS[@]}"; do
            
            # Criar um nome de pasta único para esta combinação
            # Exemplo: result_d4_s3_e100
            OUTPUT_DIR="./output/result_d${d}_s${s}_e${e}"
            
            echo "[$COUNT/$TOTAL_COMB] Rodando: Depth=$d, Size=$s, Trees=$e"
            echo "Pasta de saída: $OUTPUT_DIR"
            
            # Executa o seu script Python com os parâmetros da vez
            time python3 run_rdn_cv_simplified.py \
                --max_depth "$d" \
                --node_size "$s" \
                --n_estimators "$e" \
                --data_path "./dataset" \
                --output_path "$OUTPUT_DIR"
            
            echo "----------------------------------------------------"
            COUNT=$((COUNT + 1))
            
        done
    done
done

echo "Todos os experimentos foram concluídos!"