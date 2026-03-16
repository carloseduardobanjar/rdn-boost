#!/bin/bash

# O venv está na home
source /home/users/cschuller/venv_land/bin/activate

# O script python está dentro de rdn-boost/experimentos_land
python3 /home/users/cschuller/rdn-boost/experimentos_land/run_rdn_cv_simplified.py "$@"