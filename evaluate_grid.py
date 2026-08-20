import csv
import re
import shutil
from pathlib import Path
import numpy as np
from srlearn import Background, Database
from srlearn.rdn import BoostedRDNClassifier

# 1. Caminhos dos arquivos da pasta de teste
TEST_DIR = Path("~/rdn-boost/test").expanduser()
FACTS_FILE = str(TEST_DIR / "test_facts.txt")
POS_FILE = TEST_DIR / "test_pos.txt"
NEG_FILE = str(TEST_DIR / "test_neg.txt") if (TEST_DIR / "test_neg.txt").exists() else None
BK_FILE = TEST_DIR / "test_bk.txt"

# 2. Ler os alvos do test_pos.txt para manter a correspondencia de ordem
with open(POS_FILE, "r") as f:
    pos_targets = [line.strip() for line in f if line.strip() and not line.startswith("%")]

# Regex para extrair o host/entidade de um predicado como execCode(internet, host_a).
host_pattern = re.compile(r"\((?:[^,]+,\s*)?([^,\)]+)\)")

# 3. Carregar o Background
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

# 4. Inicializar o Database do teste
db = Database.from_files(
    facts=FACTS_FILE,
    pos=str(POS_FILE),
    neg=NEG_FILE
)

# 5. Mapear o Grid Search
RESULTS_DIR = Path("~/rdn-boost/results").expanduser()
grid_pattern = re.compile(r"grid_d(?P<depth>\d+)_e(?P<estimators>\d+)_n(?P<nodesize>\d+)_s(?P<seed>\d+)")

results_data = []

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

print(f"Iniciando avaliacao para {len(pos_targets)} alvo(s) em test_pos.txt...\n")

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
            clf = load_fold_model(fold_dir, "execCode", estimators, depth, node_size)
            probs = clf.predict_proba(db)
            probs_list = np.asarray(probs, dtype=float).flatten().tolist()

            # Mapeia cada consulta para a sua probabilidade individual
            for target_fact, prob in zip(pos_targets, probs_list):
                host_match = host_pattern.search(target_fact)
                host_name = host_match.group(1) if host_match else target_fact

                results_data.append({
                    "experiment": exp_folder.name,
                    "depth": depth,
                    "estimators": estimators,
                    "node_size": node_size,
                    "fold": fold_num,
                    "target_fact": target_fact,
                    "host": host_name,
                    "probability": float(prob)
                })

            print(f"[{exp_folder.name}] Fold {fold_num} processado ({len(probs_list)} alvos).")

        except Exception as e:
            print(f"[ERRO] {exp_folder.name} {fold_dir.name}: {e}")

# 6. Salvar relatorio detalhado em CSV
output_csv = RESULTS_DIR / "grid_test_individual_hosts.csv"
fieldnames = ["experiment", "depth", "estimators", "node_size", "fold", "target_fact", "host", "probability"]

with open(output_csv, mode="w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results_data)

print(f"\n[SUCESSO] Avaliacao individual concluida! Resultados salvos em: {output_csv}")