#!/bin/bash
# Ativa o venv usando o caminho completo
source /home/users/cschuller/rdn-boost/venv_land/bin/activate

# Executa o Python usando o caminho completo para o script
# E repassa todos os argumentos com "$@"
python3 /home/users/cschuller/rdn-boost/experimentos_land/run_rdn_cv_simplified.py "$@"