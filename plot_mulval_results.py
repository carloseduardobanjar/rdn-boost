import argparse
import csv
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib-cache"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "font-cache"))

import matplotlib.pyplot as plt


METRIC_NAMES = ["accuracy", "precision", "recall", "f1", "auc"]
CLASS_COLORS = {0: "#d95f02", 1: "#1b9e77"}


def read_csv(path):
    with path.open(newline="") as csvfile:
        return list(csv.DictReader(csvfile))


def as_float(row, key):
    value = row.get(key, "")
    return None if value in {"", "None", "n/a"} else float(value)


def read_predictions(output_dir):
    rows = []
    for path in sorted(output_dir.glob("predictions_fold_*.csv")):
        fold = path.stem.replace("predictions_fold_", "fold")
        for row in read_csv(path):
            rows.append(
                {
                    "fold": fold,
                    "example": row["example"],
                    "actual": int(row["actual"]),
                    "predicted": int(row["predicted"]),
                    "probability": float(row["probability"]),
                }
            )
    return rows


def save_current_figure(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    print(f"salvo: {path}")


def plot_metrics_by_fold(metrics_rows, plots_dir):
    folds = [f"fold{row['fold']}" for row in metrics_rows]
    x = range(len(folds))

    plt.figure(figsize=(9, 5))
    for metric in METRIC_NAMES:
        plt.plot(x, [as_float(row, metric) for row in metrics_rows], marker="o", label=metric)

    plt.xticks(list(x), folds)
    plt.ylim(0, 1.05)
    plt.xlabel("Fold")
    plt.ylabel("Score")
    plt.title("Metricas por fold")
    plt.grid(axis="y", alpha=0.25)
    plt.legend(ncol=3)
    save_current_figure(plots_dir / "metrics_by_fold.png")


def plot_confusion_by_fold(metrics_rows, plots_dir):
    folds = [f"fold{row['fold']}" for row in metrics_rows]
    x = list(range(len(folds)))
    width = 0.2
    series = [
        ("tp", "#1b9e77"),
        ("fp", "#d95f02"),
        ("tn", "#7570b3"),
        ("fn", "#e7298a"),
    ]

    plt.figure(figsize=(9, 5))
    for index, (key, color) in enumerate(series):
        values = [int(row[key]) for row in metrics_rows]
        offsets = [item + (index - 1.5) * width for item in x]
        plt.bar(offsets, values, width=width, label=key.upper(), color=color)

    plt.xticks(x, folds)
    plt.xlabel("Fold")
    plt.ylabel("Quantidade")
    plt.title("Matriz de confusao por fold")
    plt.grid(axis="y", alpha=0.25)
    plt.legend()
    save_current_figure(plots_dir / "confusion_by_fold.png")


def plot_probability_distribution(prediction_rows, plots_dir):
    positives = [row["probability"] for row in prediction_rows if row["actual"] == 1]
    negatives = [row["probability"] for row in prediction_rows if row["actual"] == 0]

    plt.figure(figsize=(9, 5))
    bins = [i / 20 for i in range(21)]
    plt.hist(negatives, bins=bins, alpha=0.75, label="negativos", color=CLASS_COLORS[0])
    plt.hist(positives, bins=bins, alpha=0.75, label="positivos", color=CLASS_COLORS[1])
    plt.xlabel("Probabilidade predita")
    plt.ylabel("Quantidade")
    plt.title("Distribuicao das probabilidades")
    plt.grid(axis="y", alpha=0.25)
    plt.legend()
    save_current_figure(plots_dir / "probability_distribution.png")


def plot_probability_strip(prediction_rows, plots_dir):
    plt.figure(figsize=(9, 5))
    for actual in [0, 1]:
        values = [row["probability"] for row in prediction_rows if row["actual"] == actual]
        xs = [actual + (index % 7 - 3) * 0.012 for index, _ in enumerate(values)]
        plt.scatter(xs, values, alpha=0.8, s=48, color=CLASS_COLORS[actual])

    plt.xticks([0, 1], ["negativo", "positivo"])
    plt.ylim(0, 1.05)
    plt.ylabel("Probabilidade predita")
    plt.title("Separacao entre classes")
    plt.grid(axis="y", alpha=0.25)
    save_current_figure(plots_dir / "class_probability_strip.png")


def plot_rule_coverage(coverage_rows, plots_dir):
    per_rule = {}
    for row in coverage_rows:
        if row["fold"] == "all":
            per_rule[row["rule"]] = int(row["derivations"])

    rules = sorted(per_rule, key=per_rule.get, reverse=True)
    values = [per_rule[rule] for rule in rules]

    plt.figure(figsize=(9, 5))
    plt.bar(rules, values, color="#386cb0")
    plt.xlabel("Regra")
    plt.ylabel("Derivacoes")
    plt.title("Cobertura das regras de execCode")
    plt.xticks(rotation=25, ha="right")
    plt.grid(axis="y", alpha=0.25)
    save_current_figure(plots_dir / "exec_code_rule_coverage.png")


def plot_threshold_comparison(metrics_rows, plots_dir):
    folds = [f"fold{row['fold']}" for row in metrics_rows]
    x = range(len(folds))

    plt.figure(figsize=(9, 5))
    plt.plot(x, [as_float(row, "f1") for row in metrics_rows], marker="o", label="F1 no threshold usado")
    plt.plot(x, [as_float(row, "best_f1") for row in metrics_rows], marker="o", label="Melhor F1 observado")
    plt.xticks(list(x), folds)
    plt.ylim(0, 1.05)
    plt.xlabel("Fold")
    plt.ylabel("F1")
    plt.title("Impacto do threshold")
    plt.grid(axis="y", alpha=0.25)
    plt.legend()
    save_current_figure(plots_dir / "threshold_f1_comparison.png")


def main():
    parser = argparse.ArgumentParser(description="Gera graficos dos resultados MulVAL/RDN.")
    parser.add_argument("--output_path", default="./mulval_output")
    parser.add_argument("--dataset_path", default="./mulval_dataset")
    parser.add_argument("--plots_path", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_path)
    dataset_dir = Path(args.dataset_path)
    plots_dir = Path(args.plots_path) if args.plots_path else output_dir / "plots"

    metrics_path = output_dir / "metrics_summary.csv"
    coverage_path = dataset_dir / "exec_code_rule_coverage.csv"

    metrics_rows = read_csv(metrics_path)
    prediction_rows = read_predictions(output_dir)

    plot_metrics_by_fold(metrics_rows, plots_dir)
    plot_confusion_by_fold(metrics_rows, plots_dir)
    plot_probability_distribution(prediction_rows, plots_dir)
    plot_probability_strip(prediction_rows, plots_dir)
    plot_threshold_comparison(metrics_rows, plots_dir)

    if coverage_path.exists():
        plot_rule_coverage(read_csv(coverage_path), plots_dir)
    else:
        print(f"aviso: cobertura nao encontrada em {coverage_path}")


if __name__ == "__main__":
    main()
