#!/bin/bash

echo "==== INÍCIO ===="
date
echo "Args: $@"

cd /home/users/cschuller/rdn-boost/experimentos_land2

rm -rf output
mkdir output
chmod 777 output

source /home/users/cschuller/venv_land/bin/activate

python3 -u /home/users/cschuller/rdn-boost/experimentos_land2/run_rdn_cv_simplified.py "$@"

echo "==== FIM ===="
date