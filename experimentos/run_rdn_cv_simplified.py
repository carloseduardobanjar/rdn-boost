import os
import argparse
import shutil
from pathlib import Path

import numpy as np
from srlearn.rdn import BoostedRDNClassifier
from srlearn import Background, Database


# ==========================================
# UTILIDADES
# ==========================================

def merge_files(file_list, output_file):
    with open(output_file, "w") as outfile:
        for fname in file_list:
            with open(fname) as infile:
                outfile.write(infile.read())
                outfile.write("\n")


def load_database(base_path, folds, prefix):

    global TMP_DIR

    pos_files = []
    neg_files = []
    fact_files = []

    for fold in folds:
        base = os.path.join(base_path, fold)
        pos_files.append(os.path.join(base, "pos.pl"))
        neg_files.append(os.path.join(base, "neg.pl"))
        fact_files.append(os.path.join(base, "facts.pl"))

    merged_pos = os.path.join(TMP_DIR, f"{prefix}_pos.pl")
    merged_neg = os.path.join(TMP_DIR, f"{prefix}_neg.pl")
    merged_facts = os.path.join(TMP_DIR, f"{prefix}_facts.pl")

    merge_files(pos_files, merged_pos)
    merge_files(neg_files, merged_neg)
    merge_files(fact_files, merged_facts)

    db = Database.from_files(merged_pos, merged_neg, merged_facts)

    db.modes = [
        "execCode(+host, +privilege).",

        "attackerLocated(-zone).",

        "hacl(+zone, -host, -protocol, -port).",

        "networkServiceInfo(+host, -software, +protocol, +port, -privilege).",

        "vulExists(+host, -cve, -software).",

        "vulProperty(+cve, #exploitType, #effect)."
    ]

    return db


# ==========================================
# MAIN
# ==========================================

def main():

    parser = argparse.ArgumentParser(description="RDN-Boost 5-Fold Cross Validation")

    parser.add_argument("--data_path", type=str, required=True,
                        help="Path to dataset folds (e.g., ./dataset2)")
    
    parser.add_argument("--output_path", type=str, required=True,
                        help="Path to save results")
    
    parser.add_argument("--folds", type=int, default=5,
                        help="Number of folds")
    
    parser.add_argument("--max_depth", type=int, default=4,
                        help="Max tree depth")
    
    parser.add_argument("--node_size", type=int, default=5,
                        help="Minimum node size")
    
    parser.add_argument("--n_estimators", type=int, default=75,
                        help="Number of boosting trees")

    args = parser.parse_args()

    print("Configurações:")
    print(f"Data path: {args.data_path}")
    print(f"Output path: {args.output_path}")
    print(f"Folds: {args.folds}")
    print(f"Max tree depth: {args.max_depth}")
    print(f"Node size: {args.node_size}")
    print(f"Number of estimators: {args.n_estimators}")

    base_path = args.data_path
    folds = [f"fold{i:02d}" for i in range(1, args.folds + 1)]

    save_root = Path(args.output_path)
    save_root.mkdir(parents=True, exist_ok=True)

    global TMP_DIR

    TMP_DIR = save_root / "_tmp"
    TMP_DIR.mkdir(exist_ok=True)

    results = []

    for i in range(args.folds):

        test_fold = folds[i]
        train_folds = [f for j, f in enumerate(folds) if j != i]

        print("\n==============================")
        print(f"Fold {i+1}")
        print(f"Treino: {train_folds}")
        print(f"Teste : {test_fold}")

        train_db = load_database(base_path, train_folds, prefix=f"train_tmp_{i}")
        test_db = load_database(base_path, [test_fold], prefix=f"test_tmp_{i}")

        bk = Background(modes=train_db.modes)

        clf = BoostedRDNClassifier(
            background=bk,
            target="execCode",
            max_tree_depth=args.max_depth,
            node_size=args.node_size,
            n_estimators=args.n_estimators,
        )

        print("\nTreinando modelo BoostSRL...")

        clf.fit(train_db)

        print("Realizando predições no conjunto de teste...")

        probs = clf.predict_proba(test_db)

        # =============================
        # Salvar modelo BoostSRL
        # =============================

        print("\nSalvando modelo BoostSRL...")

        data_dir = Path(clf.file_system.files.DIRECTORY)
        save_dir = save_root / f"fold_{i+1}"

        if save_dir.exists():
            shutil.rmtree(save_dir)

        shutil.copytree(data_dir, save_dir)

        print(f"Modelo salvo em: {save_dir}")

        print("\n=== TEST RESULTS ===")
        print(f"t1 probability: {probs[0]:.4f}")
        print(f"t2 probability: {probs[1]:.4f}")

        results.append(probs)

    print("\nCross-validation finalizada com sucesso.")


if __name__ == "__main__":
    main()