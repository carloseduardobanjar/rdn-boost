import argparse
import csv
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def read_experiment(manifest_path, job_id):
    with manifest_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["job_id"] == job_id:
                return row
    raise ValueError(f"job_id nao encontrado em {manifest_path}: {job_id}")


def find_repo_root():
    candidates = [Path.cwd(), Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
    for candidate in candidates:
        if (candidate / "train_mulval_exec_code.py").exists():
            return candidate
    raise FileNotFoundError("Nao encontrei train_mulval_exec_code.py para definir a raiz do projeto.")


def as_int(row, key):
    return int(row[key])


def as_float(row, key):
    return float(row[key])


def current_git_commit(repo_root):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def run_command(command, cwd, log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as log_file:
        log_file.write("$ " + " ".join(command) + "\n\n")
        log_file.flush()
        process = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    return process.returncode


def build_train_command(row, repo_root, result_dir):
    data_path = result_dir / "dataset"
    output_path = result_dir / "output"
    return [
        sys.executable,
        "-u",
        str(repo_root / "train_mulval_exec_code.py"),
        "--generate",
        "--folds",
        str(as_int(row, "folds")),
        "--instances_per_fold",
        str(as_int(row, "instances_per_fold")),
        "--data_path",
        str(data_path),
        "--output_path",
        str(output_path),
        "--density",
        str(as_float(row, "density")),
        "--background",
        row["background"],
        "--dataset_style",
        row.get("dataset_style") or "random",
        "--positives_per_fold",
        str(as_int(row, "positives_per_fold")),
        "--negatives_per_fold",
        str(as_int(row, "negatives_per_fold")),
        "--max_depth",
        str(as_int(row, "max_depth")),
        "--node_size",
        str(as_int(row, "node_size")),
        "--n_estimators",
        str(as_int(row, "n_estimators")),
        "--threshold",
        str(as_float(row, "threshold")),
        "--seed",
        str(as_int(row, "seed")),
        "--mode_profile",
        row.get("mode_profile") or "full",
    ]


def maybe_prefix_time(command):
    if platform.system() != "Linux":
        return command

    time_bin = shutil.which("time")
    if time_bin and Path(time_bin).name == "time":
        # On Linux clusters this is usually GNU time and supports -v. If the
        # option is unsupported, the command fails early and the log makes it clear.
        return [time_bin, "-v", *command]
    if Path("/usr/bin/time").exists():
        return ["/usr/bin/time", "-v", *command]
    return command


def write_metadata(path, row, repo_root, returncode):
    metadata = {
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "returncode": returncode,
        "git_commit": current_git_commit(repo_root),
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "cwd": str(repo_root),
        "condor_process": os.environ.get("PROCESS"),
        "condor_cluster": os.environ.get("CLUSTER"),
        "experiment": row,
    }
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def run_threshold_eval(row, repo_root, result_dir):
    output_path = result_dir / "output"
    threshold = as_float(row, "threshold")
    metrics_path = output_path / f"metrics_threshold_{threshold:.2f}.csv"
    command = [
        sys.executable,
        "-u",
        str(repo_root / "evaluate_threshold.py"),
        "--output_path",
        str(output_path),
        "--threshold",
        str(threshold),
        "--save_csv",
        str(metrics_path),
    ]
    return run_command(command, repo_root, result_dir / "evaluate_threshold.log")


def parse_args():
    parser = argparse.ArgumentParser(description="Executa um experimento RDN-Boost isolado.")
    parser.add_argument("--manifest", default="cluster/experiments.csv")
    parser.add_argument("--job_id", required=True)
    parser.add_argument("--results_root", default="cluster/results")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove resultado anterior do job antes de executar.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    repo_root = find_repo_root()
    manifest_path = (repo_root / args.manifest).resolve()
    results_root = (repo_root / args.results_root).resolve()
    row = read_experiment(manifest_path, args.job_id)

    result_dir = results_root / row["job_id"]
    if args.clean and result_dir.exists():
        shutil.rmtree(result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    (result_dir / "config.json").write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")

    train_command = maybe_prefix_time(build_train_command(row, repo_root, result_dir))
    returncode = run_command(train_command, repo_root, result_dir / "train.log")

    if returncode == 0:
        eval_returncode = run_threshold_eval(row, repo_root, result_dir)
        if eval_returncode != 0:
            returncode = eval_returncode

    write_metadata(result_dir / "metadata.json", row, repo_root, returncode)
    raise SystemExit(returncode)


if __name__ == "__main__":
    main()
