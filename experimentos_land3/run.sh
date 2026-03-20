#!/bin/bash

echo "==== INÍCIO ===="
date
echo "Args: $@"

cd /home/users/cschuller/rdn-boost/experimentos_land3

source /home/users/cschuller/novo_venv/bin/activate

python3 -u /home/users/cschuller/rdn-boost/experimentos_land3/run_rdn_cv_simplified.py "$@"

echo "==== FIM ===="
date