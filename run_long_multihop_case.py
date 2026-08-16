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
    add_fact,
    close_mulval_rules,
    fact,
    serialize_facts,
)


QUERY_EXAMPLES = [
    ("direct", "host1", "vpn_user"),
    ("hop_2", "host2", "vpn_user"),
    ("hop_3", "host3", "vpn_user"),
    ("target_4_hops", "host4", "vpn_user"),
    ("blocked_control", "host_blocked", "vpn_user"),
]

MANUAL_BK_DIRECTIVES = [*BK_DIRECTIVES, "okIfUnknown: clientProgram/2."]


def add_remote_service_shape(facts, host):
    service = "vpnService"
    privilege = "vpn_user"
    cve = f"cve_{host}_vpn"
    add_fact(facts, "networkServiceInfo", host, service, "udp", "443", privilege)
    add_fact(facts, "installed", host, service)
    add_fact(facts, "hasAccount", f"user_{host}", host, privilege)
    add_fact(facts, "vulExists", host, cve, service)
    add_fact(facts, "vulProperty", cve, "remoteExploit", "privEscalation")


def build_long_multihop_facts():
    facts = defaultdict(set)
    add_fact(facts, "attackerLocated", "internet_1")

    for host in ["host1", "host2", "host3", "host4", "host_blocked"]:
        add_remote_service_shape(facts, host)

    add_fact(facts, "hacl", "internet_1", "host1", "udp", "443")

    for source, target in [("host1", "host2"), ("host2", "host3"), ("host3", "host4")]:
        add_fact(facts, "advances", source, target)
        add_fact(facts, "hacl", source, target, "udp", "443")

    # Same local service/vulnerability shape as the other hosts, but no incoming
    # direct or lateral path. This should stay negative under the MulVAL closure.
    return facts


def write_case_files(case_dir, facts):
    case_dir.mkdir(parents=True, exist_ok=True)
    closed_facts, exec_code_rules = close_mulval_rules(facts)
    positive_exec = set(closed_facts["execCode"])

    query_lines = [fact("execCode", host, privilege) for _label, host, privilege in QUERY_EXAMPLES]
    expected_lines = [
        fact("execCode", host, privilege)
        for _label, host, privilege in QUERY_EXAMPLES
        if (host, privilege) in positive_exec
    ]

    facts_lines = [
        "% --- Manual long multi-hop facts ---",
        *MANUAL_BK_DIRECTIVES,
        *serialize_facts(facts),
    ]
    (case_dir / "facts.pl").write_text("\n".join(facts_lines) + "\n")
    (case_dir / "query_pos.pl").write_text("\n".join(query_lines) + "\n")
    (case_dir / "query_neg.pl").write_text("% Empty on purpose: query_pos.pl contains all manual probes.\n")
    (case_dir / "expected_pos.pl").write_text("\n".join(expected_lines) + "\n")

    with (case_dir / "closure_summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case", "host", "derived", "rules"])
        for label, host, privilege in QUERY_EXAMPLES:
            key = (host, privilege)
            writer.writerow(
                [
                    label,
                    host,
                    int(key in positive_exec),
                    "|".join(sorted(exec_code_rules.get(key, []))),
                ]
            )

    return closed_facts, exec_code_rules


def read_model_tree_count(model_dir, target):
    trees_dir = model_dir / "train" / "models" / "bRDNs" / "Trees"
    return len(list(trees_dir.glob(f"{target}Tree*.tree")))


def load_fold_model(model_dir, n_estimators, max_depth, node_size):
    from srlearn import Background
    from srlearn.rdn import BoostedRDNClassifier

    ok_if_unknown = [
        directive.replace("okIfUnknown:", "").strip().rstrip(".")
        for directive in MANUAL_BK_DIRECTIVES
    ]
    background = Background(modes=MULVAL_MODES, ok_if_unknown=ok_if_unknown)
    clf = BoostedRDNClassifier(
        background=background,
        target="execCode",
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
        tree_path = clf.file_system.files.TREES_DIR / f"execCodeTree{tree_number}.tree"
        estimators.append(tree_path.read_text())
    clf.estimators_ = estimators
    return clf


def parse_results(results_path):
    values = {}
    pattern = re.compile(r"(!?execCode\(([^,]+),\s*([^)]+)\))\s+([0-9.eE+-]+)")
    for line in results_path.read_text().splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        host = match.group(2).strip()
        privilege = match.group(3).strip()
        probability = float(match.group(4))
        values[(host, privilege)] = probability
    return values


def run_predictions(case_dir, output_path, max_depth, node_size):
    from srlearn import Database

    db = Database.from_files(
        pos=str(case_dir / "query_pos.pl"),
        neg=str(case_dir / "query_neg.pl"),
        facts=str(case_dir / "facts.pl"),
    )

    fold_dirs = sorted(path for path in output_path.glob("fold_*") if path.is_dir())
    rows = []
    for fold_dir in fold_dirs:
        n_estimators = read_model_tree_count(fold_dir, "execCode")
        clf = load_fold_model(fold_dir, n_estimators, max_depth, node_size)
        probabilities = np.asarray(clf.predict_proba(db), dtype=float).tolist()

        results_dir = case_dir / f"results_latest_{fold_dir.name}_model"
        if results_dir.exists():
            shutil.rmtree(results_dir)
        shutil.copytree(clf.file_system.files.DIRECTORY, results_dir)

        parsed = parse_results(results_dir / "test" / "results_execCode.db")
        row = {"fold": fold_dir.name}
        for index, (label, host, privilege) in enumerate(QUERY_EXAMPLES):
            row[label] = parsed.get((host, privilege), probabilities[index])
        rows.append(row)

    return rows


def write_prediction_summary(case_dir, rows):
    summary_path = case_dir / "model_predictions_summary_latest.csv"
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["fold", *[item[0] for item in QUERY_EXAMPLES]])
        writer.writeheader()
        writer.writerows(rows)
    return summary_path


def print_summary(rows):
    headers = ["fold", *[item[0] for item in QUERY_EXAMPLES]]
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        values = [row["fold"], *[f"{row[label]:.4f}" for label, _host, _privilege in QUERY_EXAMPLES]]
        print("| " + " | ".join(values) + " |")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gera e testa um caso manual com caminho execCode multi-hop mais longo."
    )
    parser.add_argument("--case_dir", default="./manual_cases/long_multihop_exec_code")
    parser.add_argument("--output_path", default="./mulval_output")
    parser.add_argument("--max_depth", type=int, default=4)
    parser.add_argument("--node_size", type=int, default=2)
    parser.add_argument("--no_predict", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    case_dir = Path(args.case_dir)
    output_path = Path(args.output_path)

    facts = build_long_multihop_facts()
    write_case_files(case_dir, facts)

    print(f"Caso salvo em: {case_dir}")
    print(f"Fechamento salvo em: {case_dir / 'closure_summary.csv'}")

    if args.no_predict:
        return

    rows = run_predictions(case_dir, output_path, args.max_depth, args.node_size)
    summary_path = write_prediction_summary(case_dir, rows)
    print_summary(rows)
    print(f"Predicoes salvas em: {summary_path}")


if __name__ == "__main__":
    main()
