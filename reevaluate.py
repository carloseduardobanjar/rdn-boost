import argparse
import csv
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score


def evaluate_predictions(csv_path, threshold):
    y_true, y_prob = [], []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Identifica as colunas de rótulo real e probabilidade predita
            target_col = "y_true" if "y_true" in row else "target"
            prob_col = "y_prob" if "y_prob" in row else "probability"

            y_true.append(float(row[target_col]))
            y_prob.append(float(row[prob_col]))

    y_true = np.array(y_true)
    y_prob = np.array(y_prob)
    y_pred = (y_prob >= threshold).astype(int)

    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))

    total = len(y_true)
    positives = int(np.sum(y_true == 1))
    negatives = int(np.sum(y_true == 0))

    acc = (tp + tn) / total if total > 0 else 0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0

    try:
        auc = roc_auc_score(y_true, y_prob)
    except Exception:
        auc = 0.0

    return {
        "total": total,
        "positives": positives,
        "negatives": negatives,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "auc": round(auc, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "y_true": y_true,
        "y_prob": y_prob,
    }


def process_experiment(exp_dir, threshold):
    output_dir = exp_dir / "output"
    pred_files = sorted(output_dir.glob("predictions_fold_*.csv"))

    if not pred_files:
        return

    all_y_true, all_y_prob = [], []
    rows_to_write = []

    for pred_file in pred_files:
        fold_name = pred_file.stem.replace("predictions_", "")
        res = evaluate_predictions(pred_file, threshold)

        all_y_true.extend(res["y_true"])
        all_y_prob.extend(res["y_prob"])

        row = {"fold": fold_name}
        row.update({k: v for k, v in res.items() if k not in ("y_true", "y_prob")})
        rows_to_write.append(row)

    # Métricas Globais Agregadas
    all_y_true = np.array(all_y_true)
    all_y_prob = np.array(all_y_prob)
    all_y_pred = (all_y_prob >= threshold).astype(int)

    tp = int(np.sum((all_y_pred == 1) & (all_y_true == 1)))
    fp = int(np.sum((all_y_pred == 1) & (all_y_true == 0)))
    tn = int(np.sum((all_y_pred == 0) & (all_y_true == 0)))
    fn = int(np.sum((all_y_pred == 0) & (all_y_true == 1)))

    total = len(all_y_true)
    acc = (tp + tn) / total
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0

    try:
        auc = roc_auc_score(all_y_true, all_y_prob)
    except Exception:
        auc = 0.0

    agg_row = {
        "fold": "Agregado",
        "total": total,
        "positives": int(np.sum(all_y_true == 1)),
        "negatives": int(np.sum(all_y_true == 0)),
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "auc": round(auc, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }
    rows_to_write.append(agg_row)

    # Escreve o novo arquivo de métricas
    out_csv = output_dir / f"metrics_threshold_{threshold:.2f}.csv"
    fieldnames = list(rows_to_write[0].keys())

    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_to_write)

    print(f"[OK] Gerado: {out_csv}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results_root", default="results", help="Caminho para a pasta results"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.50,
        help="Novo threshold a ser avaliado",
    )
    args = parser.parse_args()

    results_root = Path(args.results_root)
    exp_dirs = [
        d for d in sorted(results_root.iterdir()) if d.is_dir() and d.name.startswith("grid_")
    ]

    for exp_dir in exp_dirs:
        process_experiment(exp_dir, args.threshold)


if __name__ == "__main__":
    main()