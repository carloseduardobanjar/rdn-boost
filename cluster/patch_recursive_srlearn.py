#!/usr/bin/env python3
"""Patch the local srlearn BoostSRL backend for recursive binary targets.

The BoostSRL/WILL jar used by srlearn can return a two-value probability
distribution during recursive target inference. Its original
ProbDistribution.getProbOfBeingTrue() aborts in that case, even for binary
targets. This patch makes binary distributions return the positive-class
probability and also makes srlearn's Python results parser independent from
NumPy's removed multi-character delimiter support.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


JAVA_SOURCE = r"""
package edu.wisc.cs.will.Utils;

import java.util.Arrays;

import edu.wisc.cs.will.Boosting.Utils.BoostingUtils;

public class ProbDistribution {
    private double probOfBeingTrue;
    private double[] probDistribution;
    private boolean hasDistribution;

    public ProbDistribution(double prob) {
        setProbOfBeingTrue(prob);
    }

    public ProbDistribution(double prob, boolean use) {
        setProbOfBeingTrue(prob, use);
    }

    public ProbDistribution(double[] distribution) {
        setProbDistribution(distribution);
    }

    public ProbDistribution(ProbDistribution other) {
        this.hasDistribution = other.hasDistribution;
        if (this.hasDistribution) {
            this.probDistribution = other.probDistribution.clone();
        } else {
            this.probOfBeingTrue = other.probOfBeingTrue;
        }
    }

    public ProbDistribution(RegressionValueOrVector value) {
        this(value, true);
    }

    public ProbDistribution(RegressionValueOrVector value, boolean useSigmoid) {
        if (useSigmoid) {
            initUsingSigmoid(value);
        } else {
            initAfterNormalizing(value);
        }
    }

    private void initAfterNormalizing(RegressionValueOrVector value) {
        if (value.isHasVector()) {
            double sum = VectorStatistics.sum(value.getRegressionVector());
            setProbDistribution(VectorStatistics.scalarProduct(value.getRegressionVector(), 1.0 / sum));
        } else {
            setProbOfBeingTrue(value.getSingleRegressionValue());
        }
    }

    private void initUsingSigmoid(RegressionValueOrVector value) {
        if (value.isHasVector()) {
            double[] exponentiated = VectorStatistics.exponentiate(value.getRegressionVector());
            double sum = VectorStatistics.sum(exponentiated);
            double[] normalized = VectorStatistics.scalarProduct(exponentiated, 1.0 / sum);
            for (int i = 0; i < normalized.length; i++) {
                if (Double.isNaN(normalized[i])) {
                    normalized[i] = 1.0;
                }
            }
            setProbDistribution(normalized);
        } else {
            setProbOfBeingTrue(BoostingUtils.sigmoid(value.getSingleRegressionValue(), 0.0));
        }
    }

    public void scaleDistribution(double scalar) {
        if (isHasDistribution()) {
            probDistribution = VectorStatistics.scalarProduct(probDistribution, scalar);
        } else {
            probOfBeingTrue *= scalar;
        }
    }

    public void addDistribution(ProbDistribution other) {
        if (other == null) {
            return;
        }
        if (isHasDistribution()) {
            probDistribution = VectorStatistics.addVectors(probDistribution, other.probDistribution);
        } else {
            probOfBeingTrue += other.probOfBeingTrue;
        }
    }

    public String toString() {
        if (isHasDistribution()) {
            return Arrays.toString(probDistribution);
        }
        return String.valueOf(probOfBeingTrue);
    }

    public double getProbOfBeingTrue() {
        if (isHasDistribution()) {
            if (probDistribution != null && probDistribution.length == 2) {
                return probDistribution[1];
            }
            Utils.error("Expected binary probability distribution but contains " + toString());
        }
        return probOfBeingTrue;
    }

    public void setProbOfBeingTrue(double prob) {
        if (prob > 1.0) {
            Utils.error("Probability greater than 1!!:" + prob);
        }
        setHasDistribution(false);
        probOfBeingTrue = prob;
    }

    public void setProbOfBeingTrue(double prob, boolean use) {
        if (use) {
            setHasDistribution(false);
            probOfBeingTrue = prob;
        }
    }

    public double[] getProbDistribution() {
        if (!isHasDistribution()) {
            Utils.error("Expected distribution but contains single probability value");
        }
        return probDistribution;
    }

    public void setProbDistribution(double[] distribution) {
        setHasDistribution(true);
        probDistribution = distribution;
    }

    public boolean isHasDistribution() {
        return hasDistribution;
    }

    public void setHasDistribution(boolean hasDistribution) {
        this.hasDistribution = hasDistribution;
    }

    public double norm() {
        if (isHasDistribution()) {
            return Math.sqrt(VectorStatistics.dotProduct(probDistribution, probDistribution));
        }
        return probOfBeingTrue;
    }

    public int randomlySelect() {
        if (!isHasDistribution()) {
            return Utils.random() < probOfBeingTrue ? 1 : 0;
        }
        double cumulative = 0.0;
        double sample = Utils.random();
        for (int i = 0; i < probDistribution.length; i++) {
            cumulative += probDistribution[i];
            if (sample < cumulative) {
                return i;
            }
        }
        Utils.error("Cumulative distribution doesn't sum to 1. Sum:" + cumulative);
        return 0;
    }

    public double probOfTakingValue(int value) {
        if (isHasDistribution()) {
            if (value >= probDistribution.length) {
                Utils.error("Cannot return probability of taking value ="
                        + value + ". Has to be less than" + probDistribution.length);
            }
            return probDistribution[value];
        }
        if (value == 1) {
            return getProbOfBeingTrue();
        }
        if (value == 0) {
            return 1.0 - getProbOfBeingTrue();
        }
        Utils.error("Cannot return probability of taking value =" + value + ". Has to be 0/1.");
        return -1.0;
    }
}
""".strip()


PARSER_HELPER = '''
def _parse_results_db(results_db):
    classes = []
    results = []

    with open(results_db, "r") as _fh:
        for raw_line in _fh:
            line = raw_line.strip()
            if not line or line.startswith("//") or ")" not in line:
                continue

            literal, probability_text = line.split(")", 1)
            is_negative_literal = literal.startswith("!")
            probability_text = probability_text.strip()
            if probability_text.startswith("."):
                probability_text = probability_text[1:].strip()

            if probability_text.startswith("["):
                values = [
                    float(value)
                    for value in re.findall(
                        r"[-+]?(?:\\\\d*\\\\.\\\\d+|\\\\d+)(?:[eE][-+]?\\\\d+)?",
                        probability_text,
                    )
                ]
                if len(values) < 2:
                    raise ValueError(
                        "Expected at least two values in probability distribution: "
                        + line
                    )
                probability = values[0] if is_negative_literal else values[-1]
            else:
                match = re.search(
                    r"[-+]?(?:\\\\d*\\\\.\\\\d+|\\\\d+)(?:[eE][-+]?\\\\d+)?",
                    probability_text,
                )
                if not match:
                    raise ValueError("Could not parse probability from line: " + line)
                probability = float(match.group(0))

            classes.append(0 if is_negative_literal else 1)
            results.append(probability)

    return np.asarray(classes), np.asarray(results)


'''


LOADTXT_BLOCK = '''        _classes, _results = np.loadtxt(
            _results_db,
            delimiter=") ",
            usecols=(0, 1),
            converters={0: lambda s: 0 if s[0] == 33 else 1},
            unpack=True,
        )
'''


def get_srlearn_dir() -> Path:
    spec = importlib.util.find_spec("srlearn")
    if spec is None or spec.origin is None:
        raise SystemExit("srlearn nao encontrado no Python atual.")
    return Path(spec.origin).resolve().parent


def patch_jar(srlearn_dir: Path) -> None:
    jar_path = srlearn_dir / "BoostSRL.jar"
    if not jar_path.exists():
        raise SystemExit(f"BoostSRL.jar nao encontrado em {jar_path}")

    backup = jar_path.with_suffix(".jar.before_recursive_prob_patch")
    if not backup.exists():
        shutil.copy2(jar_path, backup)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "edu/wisc/cs/will/Utils/ProbDistribution.java"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(JAVA_SOURCE + "\n")

        subprocess.run(
            ["javac", "-classpath", str(jar_path), "-d", str(tmp_path), str(source_path)],
            check=True,
        )
        subprocess.run(
            ["jar", "uf", str(jar_path), "edu/wisc/cs/will/Utils/ProbDistribution.class"],
            cwd=tmp_path,
            check=True,
        )

    print(f"JAR corrigido: {jar_path}")


def patch_rdn_py(srlearn_dir: Path) -> None:
    rdn_path = srlearn_dir / "rdn.py"
    text = rdn_path.read_text()

    backup = rdn_path.with_suffix(".py.before_recursive_parser_patch")
    if not backup.exists():
        backup.write_text(text)

    if "def _parse_results_db(results_db):" not in text:
        marker = "warnings.simplefilter(\"default\")\n\n\n"
        text = text.replace(marker, marker + PARSER_HELPER, 1)

    threshold_block = (
        '        # Read the threshold\n'
        '        with open(self.file_system.files.TEST_LOG, "r") as _fh:\n'
        '            _threshold = re.findall("% Threshold = \\\\d*.\\\\d*", _fh.read())\n'
        '        if _threshold:\n'
        '            self.threshold_ = float(_threshold[0].split(" = ")[1])\n'
        '        else:\n'
        '            self.threshold_ = 0.5'
    )
    text = re.sub(
        r"        # Read the threshold\n.*?\n(?=    def predict\(self, database\):)",
        threshold_block + "\n\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = text.replace(LOADTXT_BLOCK, "        _classes, _results = _parse_results_db(_results_db)\n")

    rdn_path.write_text(text)
    print(f"Parser Python corrigido: {rdn_path}")


def main() -> None:
    srlearn_dir = get_srlearn_dir()
    patch_jar(srlearn_dir)
    patch_rdn_py(srlearn_dir)


if __name__ == "__main__":
    main()
