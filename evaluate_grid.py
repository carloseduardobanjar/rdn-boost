import os
import re
import csv
from pathlib import Path
from srlearn.rdn import BoostedRDNClassifier
from srlearn.database import Database

# 1. Diretorio onde estao os arquivos do seu teste
TEST_DIR = Path("~/rdn-boost/test").expanduser()
FACTS_FILE = str(TEST_DIR / "test_facts.txt")
POS_FILE = str(TEST_DIR / "test_pos.txt")
BK_FILE = str(TEST_DIR / "test_bk.txt")

# Carregar os dados de teste usando a estrutura Database do srlearn
test_data = Database.from_files(
    facts=FACTS_FILE,
    pos=POS_FILE,
    bk=BK_FILE
)

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

        clf = BoostedRDNClassifier(
            max_tree_depth=depth,
            n_estimators=estimators,
            node_size=node_size
        )
        clf.model_dir_ = str(bRDNs_dir)

        try:
            probs = clf.predict_proba(test_data)
            
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

# Salvar consolidado via modulo padrao csv
output_csv = RESULTS_DIR / "grid_test_evaluation.csv"
fieldnames = ["experiment", "depth", "estimators", "node_size", "fold", "mean_probability"]

with open(output_csv, mode="w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results_data)

print(f"\n[SUCESSO] Avaliacao concluida! Resultados salvos em: {output_csv}")