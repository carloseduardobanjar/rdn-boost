#!/bin/bash

# Vai para a pasta do experimento
cd /home/users/cschuller/rdn-boost/experimentos_land

# Garante que a pasta output exista
mkdir -p output

# Ativa o venv
source /home/users/cschuller/venv_land/bin/activate

# Roda o python usando caminhos absolutos para não ter erro
python3 /home/users/cschuller/rdn-boost/experimentos_land/run_rdn_cv_simplified.py "$@"