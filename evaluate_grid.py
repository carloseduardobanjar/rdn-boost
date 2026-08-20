import csv
import re
import shutil
from pathlib import Path
import numpy as np
from srlearn import Background, Database
from srlearn.rdn import BoostedRDNClassifier

# 1. Diretorio onde estao os arquivos do seu teste
TEST_DIR = Path("~/rdn-boost/test").expanduser()
FACTS_FILE = str(TEST_DIR / "test_facts.txt")
POS_FILE = str(TEST_DIR / "test_pos.txt")
NEG_FILE = str(TEST_DIR / "test_neg.txt") if (TEST_DIR / "test_neg.txt").exists() else None
BK_FILE = TEST_DIR / "test_bk.txt"

# 2. Carregar o Background a partir do arquivo test_bk.txt (se existir)
modes = []
ok_if_unknown = []
if BK_FILE.exists():
    for line in BK_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("mode:"):
            modes.append(line.replace("mode:", "").strip())
        elif "okIfUnknown" in line:
            clean = line.replace("okIfUnknown:", "").strip().rstrip(".")
            ok_if_unknown.append(clean)

background = Background(modes=modes if modes else None, ok_if_unknown=ok_if_unknown)

# 3. Inicializar a estrutura de banco de dados do teste
db = Database.from_files(
    facts=FACTS_FILE,
    pos=POS_FILE,
    neg=NEG_FILE
)

# 4. Diretorio raiz com os resultados do Grid Search
RESULTS_DIR = Path("~/rdn-boost/results").expanduser()
grid_pattern = re.compile(r"grid_d(?P<depth>\d+)_e(?P<estimators>\d+)_n(?P<nodesize>\d+)_s(?P<seed>\d+)")

results_data = []

# Funcao para carregar o modelo de cada fold (identica ao seu script anterior)
def load_fold_model(model_dir, target, n_estimators, max_depth, node_size):
    clf = BoostedRDNClassifier(
        background=background,
        target=target,
        max_tree_depth=max_depth,
        node_size=node_size,
        n_estimators=n_estimators,
    )
    clf._check_params()

    source_models = model_dir / "train" / "models"
    destination_models = clf.file_system.files.MODELS_DIR
    
    if destination_models.exists():
        shutil.rmtree(destination_models)
    shutil.copytree(source_models, destination_models)

    estimators = []
    for tree_number in range(n_estimators):
        tree_path = clf.file_system.files.TREES_DIR / f"{target}Tree{tree_number}.tree"
        if tree_path.exists():
            estimators.append(tree_path.read_text())
    
    clf.estimators_ = estimators
    return clf

# Iterar pelas pastas do Grid Search
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

    for fold_dir in sorted(output_dir.glob("fold_*")):
        if not fold_dir.is_dir():
            continue

        fold_num = fold_dir.name.replace("fold_", "")
        
        try:
            # Carrega o classificador e copia as arvores para o file_system local do srlearn
            clf = load_fold_model(fold_dir, "execCode", estimators, depth, node_size)
            
            # Executa a predicao
            probs = clf.predict_proba(db)
            mean_prob = float(np.mean(probs))

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
            print(f"[ERRO] {exp_folder.name} {fold_dir.name}: {e}")

# 5. Salvar consolidado em CSV
output_csv = RESULTS_DIR / "grid_test_evaluation.csv"
fieldnames = ["experiment", "depth", "estimators", "node_size", "fold", "mean_probability"]

with open(output_csv, mode="w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results_data)

print(f"\n[SUCESSO] Avaliacao concluida! Resultados salvos em: {output_csv}")