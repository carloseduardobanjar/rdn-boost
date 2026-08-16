import argparse
import csv
from itertools import product
from pathlib import Path


FIELDNAMES = [
    "job_id",
    "stage",
    "seed",
    "folds",
    "instances_per_fold",
    "density",
    "background",
    "positives_per_fold",
    "negatives_per_fold",
    "max_depth",
    "node_size",
    "n_estimators",
    "threshold",
    "request_memory",
]


def memory_for(max_depth, node_size, n_estimators):
    if max_depth >= 5 or node_size == 1 or n_estimators >= 30:
        return "1800MB"
    return "1500MB"


def build_rows(args):
    rows = []
    for max_depth, n_estimators, node_size in product(args.depths, args.estimators, args.node_sizes):
        rows.append(
            {
                "job_id": f"grid_d{max_depth}_e{n_estimators}_n{node_size}_s{args.seed}",
                "stage": args.stage,
                "seed": args.seed,
                "folds": args.folds,
                "instances_per_fold": args.instances_per_fold,
                "density": args.density,
                "background": args.background,
                "positives_per_fold": args.positives_per_fold,
                "negatives_per_fold": args.negatives_per_fold,
                "max_depth": max_depth,
                "node_size": node_size,
                "n_estimators": n_estimators,
                "threshold": args.threshold,
                "request_memory": memory_for(max_depth, node_size, n_estimators),
            }
        )
    return rows


def read_existing(path):
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_manifest(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(description="Adiciona uma grade de parametros ao manifesto do cluster.")
    parser.add_argument("--manifest", default="cluster/experiments.csv")
    parser.add_argument("--stage", default="param_grid27")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--instances_per_fold", type=int, default=1500)
    parser.add_argument("--density", type=float, default=1.3)
    parser.add_argument("--background", default="primitive")
    parser.add_argument("--positives_per_fold", type=int, default=75)
    parser.add_argument("--negatives_per_fold", type=int, default=75)
    parser.add_argument("--threshold", type=float, default=0.38)
    parser.add_argument("--depths", type=int, nargs="+", default=[3, 4, 5])
    parser.add_argument("--estimators", type=int, nargs="+", default=[10, 20, 30])
    parser.add_argument("--node_sizes", type=int, nargs="+", default=[1, 2, 3])
    return parser.parse_args()


def main():
    args = parse_args()
    manifest_path = Path(args.manifest)
    existing_rows = read_existing(manifest_path)
    new_rows = build_rows(args)

    existing_ids = {row["job_id"] for row in existing_rows}
    rows_to_add = [row for row in new_rows if row["job_id"] not in existing_ids]
    write_manifest(manifest_path, [*existing_rows, *rows_to_add])

    print(f"Manifesto atualizado: {manifest_path}")
    print(f"Jobs novos: {len(rows_to_add)}")
    print(f"Jobs na stage {args.stage}: {len(new_rows)}")


if __name__ == "__main__":
    main()
