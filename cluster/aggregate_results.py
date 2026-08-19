import argparse
import csv
import json
import re
from pathlib import Path


def read_csv_rows(path):
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def parse_peak_memory_kb(train_log):
    if not train_log.exists():
        return ""
    text = train_log.read_text(errors="replace")
    match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", text)
    return match.group(1) if match else ""


def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def collect_result(result_dir):
    config = load_json(result_dir / "config.json")
    metadata = load_json(result_dir / "metadata.json")
    threshold = float(config.get("threshold", 0.50))
    metrics_path = result_dir / "output" / f"metrics_threshold_{threshold:.2f}.csv"
    rows = read_csv_rows(metrics_path)
    aggregate = next((row for row in rows if row["fold"] == "Agregado"), {})

    return {
        "job_id": config.get("job_id", result_dir.name),
        "stage": config.get("stage", ""),
        "seed": config.get("seed", ""),
        "returncode": metadata.get("returncode", ""),
        "instances_per_fold": config.get("instances_per_fold", ""),
        "positives_per_fold": config.get("positives_per_fold", ""),
        "negatives_per_fold": config.get("negatives_per_fold", ""),
        "density": config.get("density", ""),
        "background": config.get("background", ""),
        "max_depth": config.get("max_depth", ""),
        "node_size": config.get("node_size", ""),
        "n_estimators": config.get("n_estimators", ""),
        "threshold": config.get("threshold", ""),
        "total": aggregate.get("total", ""),
        "positives": aggregate.get("positives", ""),
        "negatives": aggregate.get("negatives", ""),
        "accuracy": aggregate.get("accuracy", ""),
        "precision": aggregate.get("precision", ""),
        "recall": aggregate.get("recall", ""),
        "f1": aggregate.get("f1", ""),
        "auc": aggregate.get("auc", ""),
        "tp": aggregate.get("tp", ""),
        "fp": aggregate.get("fp", ""),
        "tn": aggregate.get("tn", ""),
        "fn": aggregate.get("fn", ""),
        "max_rss_kb": parse_peak_memory_kb(result_dir / "train.log"),
        "finished_at_utc": metadata.get("finished_at_utc", ""),
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Agrega resultados dos experimentos do cluster.")
    parser.add_argument("--results_root", default="cluster/results")
    parser.add_argument("--output", default="cluster/results_summary.csv")
    return parser.parse_args()


def main():
    args = parse_args()
    results_root = Path(args.results_root)
    rows = [
        collect_result(path)
        for path in sorted(results_root.iterdir())
        if path.is_dir() and (path / "config.json").exists()
    ]
    if not rows:
        raise SystemExit(f"Nenhum resultado encontrado em {results_root}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Resumo salvo em: {output_path}")


if __name__ == "__main__":
    main()
