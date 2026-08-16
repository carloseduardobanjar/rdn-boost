# Experimentos RDN-Boost no HTCondor LAND

Este diretório empacota os experimentos para o cluster descrito no `manual_boas_praticas-1.pdf`.
O desenho segue a recomendação do manual: jobs independentes no estilo `bag of tasks`, logs separados e requisição explícita de memória.

## 1. Preparar ambiente no Zeus

No cluster, coloque o projeto em um diretório persistente, por exemplo:

```bash
cd /home/users/$USER
git clone <repo> rdn-boost
cd rdn-boost
```

Crie o virtualenv com Python 3.9, se disponível:

```bash
python3.9 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install numpy==1.22.0 scipy==1.11.4 scikit-learn==1.6.1 srlearn==0.5.5 matplotlib==3.9.4
```

Verifique também se `java` existe no nó:

```bash
java -version
```

## 2. Teste local antes do Condor

Ainda no Zeus, rode um job pequeno diretamente:

```bash
./cluster/run_condor_job.sh smoke_s7
```

Saídas esperadas:

```text
cluster/results/smoke_s7/train.log
cluster/results/smoke_s7/output/metrics_summary.csv
cluster/results/smoke_s7/output/metrics_threshold_0.38.csv
cluster/results/smoke_s7/metadata.json
```

## 3. Submeter primeiro apenas smoke

Gere um `.sub` só com os jobs de smoke:

```bash
python cluster/make_submit.py --stage smoke --output cluster/rdn_boost_smoke.sub
condor_submit cluster/rdn_boost_smoke.sub
```

Monitore:

```bash
condor_q -submitter $USER
condor_q -held
```

Logs:

```text
cluster/log/*.log
cluster/out/*.out
cluster/error/*.err
```

## 4. Agregar e checar memória

Depois que os jobs terminarem:

```bash
python cluster/aggregate_results.py
column -s, -t < cluster/results_summary.csv | less
```

Observe principalmente:

```text
returncode
accuracy, precision, recall, f1, auc
max_rss_kb
```

`max_rss_kb` vem de `/usr/bin/time -v`. Se estiver vazio, o `time -v` do nó não gerou essa linha.

## 5. Submeter rodada maior

Se o smoke não estourar memória, rode:

```bash
python cluster/make_submit.py --stage small --output cluster/rdn_boost_small.sub
condor_submit cluster/rdn_boost_small.sub
```

Depois, se ainda estiver saudável:

```bash
python cluster/make_submit.py --stage medium --output cluster/rdn_boost_medium.sub
condor_submit cluster/rdn_boost_medium.sub
```

## 5.1. Submeter grade de parametros

Para explorar parametros com uma seed, gere a grade:

```bash
python cluster/add_param_grid.py
```

Isso adiciona a stage `param_grid27` com:

```text
max_depth = 3, 4, 5
n_estimators = 10, 20, 30
node_size = 1, 2, 3
seed = 7
```

Como o LAND pode nao compartilhar o mesmo filesystem entre Zeus e os nós, use o modo com transferencia por arquivo compactado:

```bash
./cluster/make_condor_payload.sh

python cluster/make_submit.py \
  --stage param_grid27 \
  --transfer \
  --output cluster/rdn_boost_param_grid27_transfer.sub

condor_submit cluster/rdn_boost_param_grid27_transfer.sub
```

Quando terminar:

```bash
python cluster/aggregate_results.py \
  --results_root results \
  --output results_summary_param_grid27.csv
```

## 6. Configurações atuais

As configurações ficam em:

```text
cluster/experiments.csv
```

Plano inicial:

| stage | seeds | pos/fold | neg/fold | instances/fold | trees | depth | memória |
|---|---:|---:|---:|---:|---:|---:|---:|
| smoke | 2 | 20 | 20 | 500 | 5 | 3 | 2GB |
| small | 3 | 250 | 250 | 5000 | 20 | 4 | 4GB |
| medium | 3 | 500 | 500 | 10000 | 30 | 4 | 6GB |

Esse plano é propositalmente conservador porque o RDN-Boost pode consumir muita memória ao materializar literais relacionais.

## 7. Remover jobs se algo der errado

```bash
condor_rm <cluster_id>
```

Ou, com bastante cuidado:

```bash
condor_rm -user $USER
```
