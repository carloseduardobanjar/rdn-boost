#!/bin/bash

echo "==== INÍCIO ===="
date
echo "Args: $@"

cd /home/users/cschuller/rdn-boost/experimentos_land2

source /home/users/cschuller/ambiente_land/bin/activate

export BSRL_DATA_DIR=/home/users/cschuller/tmp/bsrl_data
mkdir -p $BSRL_DATA_DIR

python3 -u /home/users/cschuller/rdn-boost/experimentos_land2/run_rdn_cv_simplified.py "$@"

echo "==== FIM ===="
date