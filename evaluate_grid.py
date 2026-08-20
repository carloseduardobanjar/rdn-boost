import os
import re
import pandas as pd
from pathlib import Path
from srlearn.rdn import BoostedRDN

# 1. Diretorio onde estao os arquivos do seu teste
TEST_DIR = Path("~/rdn-boost/test").expanduser()
FACTS_FILE = str(TEST_DIR / "test_facts.txt")
POS_FILE = str(TEST_DIR / "test_pos.txt")
BK_FILE = str(TEST_DIR / "test_bk.txt")

# Diretorio raiz com os resultados do Grid Search
RESULTS_DIR = Path("~/rdn-boost/results").expanduser()

results_data = []

# Regex para extrair os hiperparametros das pastas (ex: grid_d3_e10_n1_s7)
grid_pattern = re.compile(r"grid_d(?P<depth>\d+)_e(?P<estimators>\d+)_n(?P<nodesize>\d+)_s(?P<seed>\d+)")

# Iterar sobre todas as pastas do Grid Search
for exp_folder in sorted(RESULTS_DIR.glob("grid_*")):
    if not exp_folder.is_dir():
        continue

    match = grid_pattern.match(exp_folder.name)
    if not match:
        continue

    depth = int(match.group("depth"))
    estimators = int(match.group("estimators"))
    node_size = int(match.group("nodesize"))

    output_dir = exp_folder / "output"
    if not output_dir.exists():
        continue

    # Iterar pelos 5 Folds do experimento
    for fold_num in range(1, 6):
        bRDNs_dir = output_dir / f"fold_{fold_num}" / "train" / "models" / "bRDNs"
        
        if not bRDNs_dir.exists():
            print(f"[AVISO] Pasta bRDNs nao encontrada em: {bRDNs_dir}")
            continue

        # Configura o estimador apontando para os modelos aprendidos
        clf = BoostedRDN(
            max_tree_depth=depth,
            n_estimators=estimators,
            node_size=node_size
        )
        clf.model_dir_ = str(bRDNs_dir)

        try:
            # Executa a inferencia usando os arquivos da pasta test/
            # Nota: O srlearn carrega background, facts e exemplos de teste
            probs = clf.predict_proba(
                test_facts=FACTS_FILE,
                test_pos=POS_FILE,
                background=BK_FILE
            )
            
            # Registra o resultado medio de probabilidade para este fold/experimento
            mean_prob = float(probs.mean())
            
            results_data.append({
                "experiment": exp_folder.name,
                "depth": depth,
                "estimators": estimators,
                "node_size": node_size,
                "fold": fold_num,
                "mean_probability": mean_prob
            })
            
            print(f"[{exp_folder.name}] Fold {fold_num} -> Prob Media: {mean_prob:.4f}")

        except Exception as e:
            print(f"[ERRO] Falha ao processar {exp_folder.name} Fold {fold_num}: {e}")

# Salva a consolidacao em CSV
df_results = pd.DataFrame(results_data)
output_csv = RESULTS_DIR / "grid_test_evaluation.csv"
df_results.to_csv(output_csv, index=False)

print(f"\n[SUCESSO] Avaliacao concluida! Resultados salvos em: {output_csv}")