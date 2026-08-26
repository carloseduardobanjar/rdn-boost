import argparse
import csv
import re
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np

from train_mulval_exec_code import (
    BK_DIRECTIVES,
    MULVAL_MODES,
    OK_IF_UNKNOWN_PREDICATES,
    add_fact,
    close_mulval_rules,
    fact,
    serialize_facts,
)


PRIVILEGE = "www_data"


def build_chain_facts(length):
    facts = defaultdict(set)
    add_fact(facts, "attackerLocated", "internet_1")

    for index in range(1, length + 1):
        host = f"target_host_{index:02d}"
        cve = f"cve_target_host_{index:02d}_apache"
        add_fact(facts, "networkServiceInfo", host, "apache", "tcp", "80", PRIVILEGE)
        add_fact(facts, "installed", host, "apache")
        add_fact(facts, "vulExists", host, cve, "apache")
        add_fact(facts, "vulProperty", cve, "remoteExploit", "privEscalation")

        if index == 1:
            add_fact(facts, "hacl", "internet_1", host, "tcp", "80")
        else:
            previous = f"target_host_{index - 1:02d}"
            add_fact(facts, "advances", previous, host)
            add_fact(facts, "hacl", previous, host, "tcp", "80")

    # Controle negativo com mesma forma local, mas sem predecessor comprometido.
    add_fact(facts, "networkServiceInfo", "blocked_target", "apache", "tcp", "80", PRIVILEGE)
    add_fact(facts, "installed", "blocked_target", "apache")
    add_fact(facts, "vulExists", "blocked_target", "cve_blocked_target_apache", "apache")
    add_fact(facts, "vulProperty", "cve_blocked_target_apache", "remoteExploit", "privEscalation")
    add_fact(facts, "advances", "blocked_source", "blocked_target")
    add_fact(facts, "hacl", "blocked_source", "blocked_target", "tcp", "80")

    return facts


def parse_positions(values):
    positions = set()
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if not item:
                continue
            if "-" in item:
                start, end = item.split("-", 1)
                positions.update(range(int(start), int(end) + 1))
            else:
                positions.add(int(item))
    return positions


def write_case_files(case_dir, facts, length, skip_positions=None):
    skip_positions = set(skip_positions or [])
    case_dir.mkdir(parents=True, exist_ok=True)
    closed_facts, exec_code_rules = close_mulval_rules(facts)

    facts_lines = [
        "% --- Single long attack chain facts ---",
        *BK_DIRECTIVES,
        *serialize_facts(facts),
    ]
    (case_dir / "facts.pl").write_text("\n".join(facts_lines) + "\n")

    query_lines = [
        fact("execCode", f"target_host_{index:02d}", PRIVILEGE)
        for index in range(1, length + 1)
        if index not in skip_positions
    ]
    query_lines.append(fact("execCode", "blocked_target", PRIVILEGE))
    (case_dir / "query_pos.pl").write_text("\n".join(query_lines) + "\n")
    (case_dir / "query_neg.pl").write_text("% Empty: query_pos.pl contains all probes.\n")

    with (case_dir / "query_examples.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["position", "host", "privilege", "queried"])
        for index in range(1, length + 1):
            writer.writerow(
                [
                    index,
                    f"target_host_{index:02d}",
                    PRIVILEGE,
                    int(index not in skip_positions),
                ]
            )
        writer.writerow(["blocked", "blocked_target", PRIVILEGE, 1])

    with (case_dir / "closure_summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["position", "host", "mulval_derived", "rules"])
        for index in range(1, length + 1):
            host = f"target_host_{index:02d}"
            key = (host, PRIVILEGE)
            writer.writerow(
                [
                    index,
                    host,
                    int(key in closed_facts["execCode"]),
                    "|".join(sorted(exec_code_rules.get(key, []))),
                ]
            )
        blocked_key = ("blocked_target", PRIVILEGE)
        writer.writerow(
            [
                "blocked",
                "blocked_target",
                int(blocked_key in closed_facts["execCode"]),
                "|".join(sorted(exec_code_rules.get(blocked_key, []))),
            ]
        )


def read_model_tree_count(fold_dir):
    trees_dir = fold_dir / "train" / "models" / "bRDNs" / "Trees"
    return len(list(trees_dir.glob("execCodeTree*.tree")))


def load_fold_model(fold_dir, max_depth, node_size):
    from srlearn import Background
    from srlearn.rdn import BoostedRDNClassifier

    n_estimators = read_model_tree_count(fold_dir)
    background = Background(
        modes=MULVAL_MODES,
        ok_if_unknown=OK_IF_UNKNOWN_PREDICATES,
        recursion=True,
    )
    clf = BoostedRDNClassifier(
        background=background,
        target="execCode",
        max_tree_depth=max_depth,
        node_size=node_size,
        n_estimators=n_estimators,
    )
    clf._check_params()

    source_models = fold_dir / "train" / "models"
    destination_models = clf.file_system.files.MODELS_DIR
    if destination_models.exists():
        shutil.rmtree(destination_models)
    shutil.copytree(source_models, destination_models)

    clf.estimators_ = [
        (clf.file_system.files.TREES_DIR / f"execCodeTree{index}.tree").read_text()
        for index in range(n_estimators)
    ]
    return clf


def parse_results(results_path):
    values = {}
    pattern = re.compile(r"execCode\(([^,]+),\s*([^)]+)\)\s+([0-9.eE+-]+)")
    for line in results_path.read_text().splitlines():
        match = pattern.match(line.strip())
        if match:
            values[(match.group(1), match.group(2))] = float(match.group(3))
    return values


def read_query_examples(case_dir):
    rows = []
    with (case_dir / "query_examples.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["queried"] == "1":
                rows.append(row)
    return rows


def run_predictions(case_dir, model_output, max_depth, node_size):
    from srlearn import Database

    db = Database.from_files(
        pos=str(case_dir / "query_pos.pl"),
        neg=str(case_dir / "query_neg.pl"),
        facts=str(case_dir / "facts.pl"),
    )

    fold_dirs = sorted(path for path in model_output.glob("fold_*") if path.is_dir())
    query_examples = read_query_examples(case_dir)
    rows = []
    for fold_dir in fold_dirs:
        clf = load_fold_model(fold_dir, max_depth, node_size)
        probabilities = np.asarray(clf.predict_proba(db), dtype=float).tolist()

        results_dir = case_dir / f"results_{fold_dir.name}"
        if results_dir.exists():
            shutil.rmtree(results_dir)
        shutil.copytree(clf.file_system.files.DIRECTORY, results_dir)
        parsed = parse_results(results_dir / "test" / "results_execCode.db")

        for query, probability in zip(query_examples, probabilities):
            host = query["host"]
            position = query["position"]

            rows.append(
                {
                    "fold": fold_dir.name,
                    "position": position,
                    "host": host,
                    "probability": parsed.get((host, PRIVILEGE), probability),
                }
            )

    return rows


def write_outputs(case_dir, rows):
    predictions_path = case_dir / "long_chain_predictions.csv"
    with predictions_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["fold", "position", "host", "probability"])
        writer.writeheader()
        writer.writerows(rows)

    summary_path = case_dir / "long_chain_position_summary.csv"
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["position"]].append(float(row["probability"]))

    def sort_key(position):
        return 10**9 if position == "blocked" else int(position)

    with summary_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["position", "mean_probability", "min_probability", "max_probability"])
        for position in sorted(grouped, key=sort_key):
            values = grouped[position]
            writer.writerow(
                [
                    position,
                    f"{sum(values) / len(values):.6f}",
                    f"{min(values):.6f}",
                    f"{max(values):.6f}",
                ]
            )

    return predictions_path, summary_path


def print_compact_summary(summary_path, length):
    with summary_path.open() as handle:
        rows = list(csv.DictReader(handle))
    interesting_positions = {1, 2, 3, 5, 10, 20, 30, 40, 50}
    print("| posicao | prob media | min | max |")
    print("|---:|---:|---:|---:|")
    for row in rows:
        position = row["position"]
        if position == "blocked" or int(position) in interesting_positions or int(position) == length:
            print(
                f"| {position} | {float(row['mean_probability']):.4f} | "
                f"{float(row['min_probability']):.4f} | {float(row['max_probability']):.4f} |"
            )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Testa um modelo recursivo em uma unica cadeia de ataque longa."
    )
    parser.add_argument("--length", type=int, default=50)
    parser.add_argument("--case_dir", default="./manual_cases/single_long_attack_chain_50")
    parser.add_argument(
        "--model_output",
        default="./land_results/results 2/rec_chain_d3_e20_n2_s7/output",
    )
    parser.add_argument("--max_depth", type=int, default=3)
    parser.add_argument("--node_size", type=int, default=2)
    parser.add_argument(
        "--skip_positions",
        action="append",
        default=[],
        help="Posicoes da cadeia a remover das consultas. Aceita valores como 13 ou 10-13.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    case_dir = Path(args.case_dir)
    model_output = Path(args.model_output)
    skip_positions = parse_positions(args.skip_positions)

    facts = build_chain_facts(args.length)
    write_case_files(case_dir, facts, args.length, skip_positions)
    rows = run_predictions(case_dir, model_output, args.max_depth, args.node_size)
    predictions_path, summary_path = write_outputs(case_dir, rows)

    print(f"Caso salvo em: {case_dir}")
    print(f"Predicoes salvas em: {predictions_path}")
    print(f"Resumo por posicao salvo em: {summary_path}")
    print_compact_summary(summary_path, args.length)


if __name__ == "__main__":
    main()
