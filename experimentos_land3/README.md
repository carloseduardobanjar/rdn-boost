# Simulações - Guia de Execução

Este repositório contém scripts para geração de folds de dataset e execução de simulações.

## 1. Criar ambiente virtual (Python 3.9.6)

Certifique-se de ter o Python **3.9.6** instalado.

```bash
python3.9 -m venv .venv
```

Ativar o ambiente virtual:

```bash
source .venv/bin/activate
```

## 2. Instalar dependências

Instale as dependências do projeto:
```bash
pip install -r requirements.txt
```

## 3. Gerar os folds do dataset

Execute o script generate_folds.py para gerar os folds utilizados nas simulações.

Para começar, recomendo:
```bash
python generate_folds.py --folds 5 --instances 200 --output dataset --missing_attacker_prob 0.2
```

Os datasets serão criados dentro do diretório dataset/.

## 4. Executar as simulações
Após gerar os folds, execute o script de experimentos:

```bash
./executar_grid.sh
```