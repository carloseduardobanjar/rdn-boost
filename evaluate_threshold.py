import argparse
import csv
import glob
from pathlib import Path


def roc_auc_score(y_true, probabilities):
    positives = [score for label, score in zip(y_true, probabilities) if label == 1]
    negatives = [score for label, score in zip(y_true, probabilities) if label == 0]

    if not positives or not negatives:
        return None

    wins = 0.0
    for pos_score in positives:
        for neg_score in negatives:
            if pos_score > neg_score:
                wins += 1.0
            elif pos_score == neg_score:
                wins += 0.5

    return wins / (len(positives) * len(negatives))


def evaluate(y_true, probabilities, threshold):
    tp = sum(1 for actual, prob in zip(y_true, probabilities) if actual == 1 and prob >= threshold)
    fp = sum(1 for actual, prob in zip(y_true, probabilities) if actual == 0 and prob >= threshold)
    tn = sum(1 for actual, prob in zip(y_true, probabilities) if actual == 0 and prob < threshold)
    fn = sum(1 for actual, prob in zip(y_true, probabilities) if actual == 1 and prob < threshold)

    total = len(y_true)
    positives = sum(y_true)
    negatives = total - positives
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    auc = roc_auc_score(y_true, probabilities)

    return {
        "total": total,
        "positives": positives,
        "negatives": negatives,
        "threshold": threshold,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc": auc,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def read_predictions(path):
    y_true = []
    probabilities = []
    with path.open() as csvfile:
        for row in csv.DictReader(csvfile):
            y_true.append(int(row["actual"]))
            probabilities.append(float(row["probability"]))
    return y_true, probabilities


def print_markdown(rows):
    threshold = rows[0]["threshold"] if rows else 0.0
    print(
        f"| Fold | Total | Pos | Neg | Acc@{threshold:.2f} | Prec | Rec | F1 | "
        "AUC | TP | FP | TN | FN |"
    )
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        auc = "n/a" if row["auc"] is None else f"{row['auc']:.4f}"
        print(
            f"| {row['fold']} | {row['total']} | {row['positives']} | {row['negatives']} | "
            f"{row['accuracy']:.4f} | {row['precision']:.4f} | {row['recall']:.4f} | "
            f"{row['f1']:.4f} | {auc} | {row['tp']} | {row['fp']} | {row['tn']} | {row['fn']} |"
        )


def write_csv(path, rows):
    fieldnames = [
        "fold",
        "total",
        "positives",
        "negatives",
        "threshold",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "auc",
        "tp",
        "fp",
        "tn",
        "fn",
    ]
    with path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Recalcula metricas dos predictions_fold_*.csv usando um threshold informado."
    )
    parser.add_argument("--output_path", default="./mulval_output")
    parser.add_argument("--threshold", type=float, default=0.38)
    parser.add_argument("--save_csv", default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    output_path = Path(args.output_path)
    prediction_paths = sorted(output_path.glob("predictions_fold_*.csv"))

    if not prediction_paths:
        raise FileNotFoundError(f"Nenhum predictions_fold_*.csv encontrado em {output_path}")

    rows = []
    all_y_true = []
    all_probabilities = []

    for prediction_path in prediction_paths:
        fold = prediction_path.stem.rsplit("_", 1)[-1]
        y_true, probabilities = read_predictions(prediction_path)
        all_y_true.extend(y_true)
        all_probabilities.extend(probabilities)
        rows.append({"fold": fold, **evaluate(y_true, probabilities, args.threshold)})

    rows.append({"fold": "Agregado", **evaluate(all_y_true, all_probabilities, args.threshold)})

    print_markdown(rows)

    save_path = Path(args.save_csv) if args.save_csv else output_path / f"metrics_threshold_{args.threshold:.2f}.csv"
    write_csv(save_path, rows)
    print(f"\nMetricas salvas em: {save_path}")


if __name__ == "__main__":
    main()
