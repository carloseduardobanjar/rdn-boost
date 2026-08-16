import argparse
import csv
from pathlib import Path


TEMPLATE = """universe = vanilla
executable = cluster/run_condor_job.sh
initialdir = .

arguments = $(job_id)

log = cluster/log/$(job_id).log
output = cluster/out/$(job_id).out
error = cluster/error/$(job_id).err

request_cpus = 1
request_memory = $(request_memory)
request_disk = 4GB
rank = Memory
should_transfer_files = NO

queue job_id, request_memory from (
{queue_lines}
)
"""

TRANSFER_TEMPLATE = """universe = vanilla
executable = cluster/run_condor_job.sh
initialdir = .

arguments = $(job_id)

log = cluster/log/$(job_id).log
output = cluster/out/$(job_id).out
error = cluster/error/$(job_id).err

request_cpus = 1
request_memory = $(request_memory)
request_disk = 2GB
rank = Memory

should_transfer_files = YES
when_to_transfer_output = ON_EXIT
transfer_input_files = .venv, train_mulval_exec_code.py, evaluate_threshold.py, cluster/run_one_experiment.py, cluster/experiments.csv
transfer_output_files = results

queue job_id, request_memory from (
{queue_lines}
)
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Gera arquivo .sub para um subconjunto dos experimentos.")
    parser.add_argument("--manifest", default="cluster/experiments.csv")
    parser.add_argument("--stage", action="append", default=[])
    parser.add_argument("--job_id", action="append", default=[])
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--transfer",
        action="store_true",
        help="Gera .sub com transferencia de arquivos, evitando dependencia de filesystem compartilhado.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    manifest_path = Path(args.manifest)
    rows = list(csv.DictReader(manifest_path.open()))

    if args.stage:
        rows = [row for row in rows if row["stage"] in set(args.stage)]
    if args.job_id:
        rows = [row for row in rows if row["job_id"] in set(args.job_id)]
    if not rows:
        raise SystemExit("Nenhum experimento selecionado.")

    queue_lines = "\n".join(f"  {row['job_id']}, {row['request_memory']}" for row in rows)
    output_path = Path(args.output or f"cluster/rdn_boost_{'_'.join(args.stage or ['selected'])}.sub")
    template = TRANSFER_TEMPLATE if args.transfer else TEMPLATE
    output_path.write_text(template.format(queue_lines=queue_lines))
    print(f"Arquivo criado: {output_path}")
    print(f"Jobs: {len(rows)}")


if __name__ == "__main__":
    main()
