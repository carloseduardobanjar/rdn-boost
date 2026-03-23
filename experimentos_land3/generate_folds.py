import os
import argparse
import random


def generate_balanced_dataset(
    num_instances=1000,
    start_index=1,
    missing_attacker_prob=0.2,
    missing_vulexists_prob=0.2,
    missing_vulproperty_prob=0.05
):
    facts = ["% --- Background Knowledge ---"]
    pos = ["% --- Positive Examples ---"]
    neg = ["% --- Negative Examples ---"]

    services = {
        "apache": {
            "ports": [80, 8080, 443],
            "protocols": ["tcp"],
            "cves": ["CVE-2019-0211", "CVE-2017-15715"],
            "default_priv": "www-data"
        },
        "nginx": {
            "ports": [80, 443],
            "protocols": ["tcp"],
            "cves": ["CVE-2013-2028"],
            "default_priv": "www-data"
        },
        "ssh": {
            "ports": [22],
            "protocols": ["tcp"],
            "cves": ["CVE-2018-15473"],
            "default_priv": "user"
        },
        "mysql": {
            "ports": [3306],
            "protocols": ["tcp"],
            "cves": ["CVE-2016-6662"],
            "default_priv": "mysql"
        },
        "vsftpd": {
            "ports": [21],
            "protocols": ["tcp"],
            "cves": ["CVE-2011-2523"],
            "default_priv": "ftp"
        }
    }

    end_index = start_index + num_instances

    for i in range(start_index, end_index):
        ws = f"webServer_{i}"
        zone = f"internet_{i}"
        unknown_zone = f"unknown_zone_{i}"

        facts.append(f"\n% --- Instance {i} ---")

        service = random.choice(list(services.keys()))
        port = random.choice(services[service]["ports"])
        protocol = random.choice(services[service]["protocols"])
        cve = random.choice(services[service]["cves"])
        service_priv = services[service]["default_priv"]

        is_positive = (i - start_index) < (num_instances // 2)

        # ================= POSITIVE =================
        if is_positive:
            missing_attacker = random.random() < missing_attacker_prob
            missing_vulexists = random.random() < missing_vulexists_prob
            missing_vulproperty = random.random() < missing_vulproperty_prob

            if not missing_attacker:
                facts.append(f"attackerLocated({zone}).")

            facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")
            facts.append(
                f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv})."
            )

            if not missing_vulexists:
                facts.append(f"vulExists({ws}, '{cve}', {service}).")

            if not missing_vulproperty:
                facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")

            pos.append(f"execCode({ws}, {service_priv}).")

        # ================= NEGATIVE =================
        else:
            failure_type = random.randint(1, 10)

            if failure_type == 1:
                facts.append(f"attackerLocated({unknown_zone}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")

            elif failure_type == 2:
                facts.append(f"attackerLocated({zone}).")

            elif failure_type == 3:
                wrong_port = port + 999
                facts.append(f"attackerLocated({zone}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {wrong_port}).")

            elif failure_type == 4:
                wrong_protocol = "udp"
                facts.append(f"attackerLocated({zone}).")
                facts.append(f"hacl({zone}, {ws}, {wrong_protocol}, {port}).")

            elif failure_type == 5:
                other_service = random.choice([s for s in services if s != service])
                wrong_cve = random.choice(services[other_service]["cves"])

                facts.append(f"attackerLocated({zone}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")
                facts.append(
                    f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv})."
                )
                facts.append(f"vulExists({ws}, '{wrong_cve}', {other_service}).")

                neg.append(f"execCode({ws}, {service_priv}).")
                continue

            elif failure_type == 6:
                facts.append(f"attackerLocated({zone}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")
                facts.append(
                    f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv})."
                )
                facts.append(f"vulExists({ws}, 'CVE-LOCAL-{i}', {service}).")
                facts.append(f"vulProperty('CVE-LOCAL-{i}', localExploit, privEscalation).")

                neg.append(f"execCode({ws}, {service_priv}).")
                continue

            elif failure_type == 7:
                wrong_port = port + 111

                facts.append(f"attackerLocated({zone}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")
                facts.append(
                    f"networkServiceInfo({ws}, {service}, {protocol}, {wrong_port}, {service_priv})."
                )
                facts.append(f"vulExists({ws}, '{cve}', {service}).")
                facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")

                neg.append(f"execCode({ws}, {service_priv}).")
                continue

            elif failure_type == 8:
                facts.append(f"attackerLocated({zone}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")
                facts.append(
                    f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv})."
                )
                facts.append(f"vulExists({ws}, '{cve}', {service}).")
                facts.append(f"vulProperty('{cve}', remoteExploit, denialOfService).")

                neg.append(f"execCode({ws}, {service_priv}).")
                continue

            elif failure_type == 9:
                facts.append(f"attackerLocated({zone}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")

                other_service = random.choice([s for s in services if s != service])
                other_port = random.choice(services[other_service]["ports"])
                other_cve = random.choice(services[other_service]["cves"])

                facts.append(
                    f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv})."
                )
                facts.append(
                    f"networkServiceInfo({ws}, {other_service}, {protocol}, {other_port}, {services[other_service]['default_priv']})."
                )
                facts.append(f"vulExists({ws}, '{other_cve}', {other_service}).")
                facts.append(f"vulProperty('{other_cve}', remoteExploit, privEscalation).")

                neg.append(f"execCode({ws}, {service_priv}).")
                continue

            else:
                facts.append(f"attackerLocated({zone}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")
                facts.append(
                    f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv})."
                )
                facts.append(f"vulExists({ws}, '{cve}', {service}).")
                facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")

                wrong_priv = "root" if service_priv != "root" else "user"
                neg.append(f"execCode({ws}, {wrong_priv}).")
                continue

            facts.append(
                f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv})."
            )
            facts.append(f"vulExists({ws}, '{cve}', {service}).")
            facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")

            neg.append(f"execCode({ws}, {service_priv}).")

    print(f"Instâncias: {num_instances} | Positivos: {len(pos)-1} | Negativos: {len(neg)-1}")

    return facts, pos, neg


def save_fold(output_dir, fold_number, facts, pos, neg):
    fold_path = os.path.join(output_dir, f"fold{fold_number:02d}")
    os.makedirs(fold_path, exist_ok=True)

    with open(os.path.join(fold_path, "facts.pl"), "w") as f:
        f.write("\n".join(facts))

    with open(os.path.join(fold_path, "pos.pl"), "w") as f:
        f.write("\n".join(pos))

    with open(os.path.join(fold_path, "neg.pl"), "w") as f:
        f.write("\n".join(neg))


def main():
    parser = argparse.ArgumentParser(description="Generate Direct Network relational dataset")

    parser.add_argument("--folds", type=int, required=True)
    parser.add_argument("--instances", type=int, required=True)
    parser.add_argument("--output", type=str, required=True)

    parser.add_argument(
        "--missing_attacker_prob",
        type=float,
        default=0.0,
        help="Probabilidade de omitir attackerLocated em exemplos positivos"
    )

    parser.add_argument(
        "--missing_vulexists_prob",
        type=float,
        default=0.0,
        help="Probabilidade de omitir vulExists em exemplos positivos"
    )

    parser.add_argument(
        "--missing_vulproperty_prob",
        type=float,
        default=0.0,
        help="Probabilidade de omitir vulProperty em exemplos positivos"
    )

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    current_index = 1

    for fold in range(1, args.folds + 1):
        facts, pos, neg = generate_balanced_dataset(
            num_instances=args.instances,
            start_index=current_index,
            missing_attacker_prob=args.missing_attacker_prob,
            missing_vulexists_prob=args.missing_vulexists_prob,
            missing_vulproperty_prob=args.missing_vulproperty_prob
        )

        save_fold(args.output, fold, facts, pos, neg)

        current_index += args.instances

        print(f"Fold {fold} gerado.")

    print("\nTodos os folds foram gerados com sucesso!")


if __name__ == "__main__":
    main()