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
    "dataset_style",
    "mode_profile",
    "positives_per_fold",
    "negatives_per_fold",
    "max_depth",
    "node_size",
    "n_estimators",
    "threshold",
    "request_memory",
]


def memory_for(max_depth, node_size, n_estimators):
    if max_depth >= 5 or node_size >= 3 or n_estimators >= 30:
        return "2200MB"
    return "1800MB"


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


def build_rows(args):
    rows = []
    for max_depth, n_estimators, node_size in product(
        args.depths,
        args.estimators,
        args.node_sizes,
    ):
        rows.append(
            {
                "job_id": (
                    f"{args.job_prefix}_d{max_depth}_e{n_estimators}_"
                    f"n{node_size}_s{args.seed}"
                ),
                "stage": args.stage,
                "seed": args.seed,
                "folds": args.folds,
                "instances_per_fold": args.instances_per_fold,
                "density": args.density,
                "background": "primitive",
                "dataset_style": "attack_chain",
                "mode_profile": args.mode_profile,
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Adiciona jobs focados em cadeias multihop para testar recursao."
    )
    parser.add_argument("--manifest", default="cluster/experiments.csv")
    parser.add_argument("--stage", default="recursive_attack_chain")
    parser.add_argument("--job_prefix", default="rec_chain")
    parser.add_argument(
        "--mode_profile",
        choices=["full", "no_successor_evidence"],
        default="full",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--instances_per_fold", type=int, default=500)
    parser.add_argument("--density", type=float, default=1.0)
    parser.add_argument("--positives_per_fold", type=int, default=120)
    parser.add_argument("--negatives_per_fold", type=int, default=120)
    parser.add_argument("--threshold", type=float, default=0.38)
    parser.add_argument("--depths", type=int, nargs="+", default=[3, 4])
    parser.add_argument("--estimators", type=int, nargs="+", default=[20, 30])
    parser.add_argument("--node_sizes", type=int, nargs="+", default=[2])
    return parser.parse_args()


def main():
    args = parse_args()
    manifest_path = Path(args.manifest)
    existing_rows = read_existing(manifest_path)
    new_rows = build_rows(args)
    existing_ids = {row["job_id"] for row in existing_rows}
    rows_to_add = [row for row in new_rows if row["job_id"] not in existing_ids]

    write_manifest(manifest_path, [*existing_rows, *rows_to_add])
    stage_count = sum(
        1 for row in [*existing_rows, *rows_to_add] if row["stage"] == args.stage
    )

    print(f"Manifesto atualizado: {manifest_path}")
    print(f"Jobs novos: {len(rows_to_add)}")
    print(f"Jobs definidos pelo comando: {len(new_rows)}")
    print(f"Jobs na stage {args.stage}: {stage_count}")


if __name__ == "__main__":
    main()
