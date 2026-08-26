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
    "positives_per_fold",
    "negatives_per_fold",
    "max_depth",
    "node_size",
    "n_estimators",
    "threshold",
    "request_memory",
]


STAGES = {
    "prior_intermediate_grid12": {
        "prefix": "prior_mid",
        "background": "closed",
        "memory_extra_mb": 600,
    },
    "prior_exec_closed_grid12": {
        "prefix": "prior_exec",
        "background": "closed_with_execCode",
        "memory_extra_mb": 800,
    },
}


def memory_for(max_depth, node_size, n_estimators, extra_mb):
    base = 1800
    if max_depth >= 5 or n_estimators >= 30:
        base = 2200
    if max_depth >= 5 and n_estimators >= 30:
        base = 2400
    if node_size >= 3:
        base += 200
    return f"{base + extra_mb}MB"


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
    selected_stages = args.stage or list(STAGES)
    for stage in selected_stages:
        config = STAGES[stage]
        for max_depth, n_estimators, node_size in product(
            args.depths,
            args.estimators,
            args.node_sizes,
        ):
            rows.append(
                {
                    "job_id": (
                        f"{config['prefix']}_d{max_depth}_e{n_estimators}_"
                        f"n{node_size}_s{args.seed}"
                    ),
                    "stage": stage,
                    "seed": args.seed,
                    "folds": args.folds,
                    "instances_per_fold": args.instances_per_fold,
                    "density": args.density,
                    "background": config["background"],
                    "dataset_style": "random",
                    "positives_per_fold": args.positives_per_fold,
                    "negatives_per_fold": args.negatives_per_fold,
                    "max_depth": max_depth,
                    "node_size": node_size,
                    "n_estimators": n_estimators,
                    "threshold": args.threshold,
                    "request_memory": memory_for(
                        max_depth,
                        node_size,
                        n_estimators,
                        config["memory_extra_mb"],
                    ),
                }
            )
    return rows


def parse_args():
    parser = argparse.ArgumentParser(
        description="Adiciona jobs com conhecimento a priori derivado pelo fechamento MulVAL-like."
    )
    parser.add_argument("--manifest", default="cluster/experiments.csv")
    parser.add_argument(
        "--stage",
        action="append",
        choices=sorted(STAGES),
        default=[],
        help="Se omitido, adiciona as duas stages de conhecimento a priori.",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--instances_per_fold", type=int, default=1500)
    parser.add_argument("--density", type=float, default=1.3)
    parser.add_argument("--positives_per_fold", type=int, default=75)
    parser.add_argument("--negatives_per_fold", type=int, default=75)
    parser.add_argument("--threshold", type=float, default=0.38)
    parser.add_argument("--depths", type=int, nargs="+", default=[3, 4, 5])
    parser.add_argument("--estimators", type=int, nargs="+", default=[20, 30])
    parser.add_argument("--node_sizes", type=int, nargs="+", default=[2, 3])
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
    print(f"Jobs definidos pelo comando: {len(new_rows)}")
    for stage in args.stage or list(STAGES):
        stage_count = sum(
            1 for row in [*existing_rows, *rows_to_add] if row["stage"] == stage
        )
        print(f"Jobs na stage {stage}: {stage_count}")


if __name__ == "__main__":
    main()
