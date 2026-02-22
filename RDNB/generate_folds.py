import os
import argparse
import random

def add_access_path(facts, access_mode, zone, pivot, ws, protocol=None, port=None):
    """
    access_mode:
        1 -> Direct Network (attackerLocated + hacl zone->ws)
        2 -> Multi-hop (initialAccess + hacl pivot->ws)
        3 -> Direct On-host (attackerLocated(ws))
    """
    if access_mode == 1:
        facts.append(f"attackerLocated({zone}).")
        if protocol and port:
            facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")

    elif access_mode == 2:
        facts.append(f"initialAccess({pivot}, user).")
        if protocol and port:
            facts.append(f"hacl({pivot}, {ws}, {protocol}, {port}).")

    else:
        facts.append(f"attackerLocated({ws}).")


def generate_balanced_dataset(num_instances=1000):
    facts = ["% --- Background Knowledge ---"]
    pos = ["% --- Positive Examples ---"]
    neg = ["% --- Negative Examples ---"]

    for i in range(1, num_instances + 1):

        ws = f"webServer_{i}"
        pivot = f"workStation_{i}"
        zone = f"internet_{i}"
        unknown = f"unknown_zone_{i}"

        facts.append(f"\n% --- Instance {i} ---")

        is_positive = i <= (num_instances // 2)

        # =========================
        # ===== POSITIVE ==========
        # =========================
        if is_positive:

            sub_scenario = random.randint(1, 3)

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

            service = random.choice(list(services.keys()))
            port = random.choice(services[service]["ports"])
            protocol = random.choice(services[service]["protocols"])
            cve = random.choice(services[service]["cves"])
            service_priv = services[service]["default_priv"]

            access_mode = random.randint(1, 3)

            add_access_path(facts, access_mode, zone, pivot, ws, protocol, port)

            facts.append(f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv}).")
            facts.append(f"vulExists({ws}, '{cve}', {service}).")
            facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")

            pos.append(f"execCode({ws}, {service_priv}).")

        # =========================
        # ===== NEGATIVE ==========
        # =========================
        else:

            sub_scenario = random.randint(1, 9)

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

            service = random.choice(list(services.keys()))
            port = random.choice(services[service]["ports"])
            protocol = random.choice(services[service]["protocols"])
            cve = random.choice(services[service]["cves"])
            service_priv = services[service]["default_priv"]

            access_mode = random.randint(1, 3)

            # 1️⃣ Attacker Not Located
            if sub_scenario == 1:
                facts.append("% Failure: Attacker is in undefined zone")
                facts.append(f"attackerLocated({unknown}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")
                facts.append(f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv}).")
                facts.append(f"vulExists({ws}, '{cve}', {service}).")
                neg.append(f"execCode({ws}, {service_priv}).")

            # 2️⃣ No HACL
            elif sub_scenario == 2:
                facts.append("% Failure: No HACL")
                if access_mode == 1:
                    facts.append(f"attackerLocated({zone}).")
                elif access_mode == 2:
                    facts.append(f"initialAccess({pivot}, user).")
                else:
                    facts.append(f"attackerLocated({ws}).")

                facts.append(f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv}).")
                facts.append(f"vulExists({ws}, '{cve}', {service}).")
                neg.append(f"execCode({ws}, {service_priv}).")

            # 3️⃣ Multi-hop broken
            elif sub_scenario == 3:
                facts.append("% Failure: Multi-hop broken")
                facts.append(f"hacl({pivot}, {ws}, {protocol}, {port}).")
                facts.append(f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv}).")
                facts.append(f"vulExists({ws}, '{cve}', {service}).")
                neg.append(f"execCode({ws}, {service_priv}).")

            # 4️⃣ Local vuln attempted remotely
            elif sub_scenario == 4:
                facts.append("% Failure: Local vulnerability used remotely")
                add_access_path(facts, access_mode, zone, pivot, ws, protocol, port)

                facts.append(f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv}).")
                facts.append(f"vulExists({ws}, 'CVE-LOCAL-{i}', {service}).")
                facts.append(f"vulProperty('CVE-LOCAL-{i}', localExploit, privEscalation).")
                neg.append(f"execCode({ws}, {service_priv}).")

            # 5️⃣ Wrong Port
            elif sub_scenario == 5:
                facts.append("% Failure: Wrong Port")
                wrong_port = port + 999
                add_access_path(facts, access_mode, zone, pivot, ws, protocol, wrong_port)

                facts.append(f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv}).")
                facts.append(f"vulExists({ws}, '{cve}', {service}).")
                facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")
                neg.append(f"execCode({ws}, {service_priv}).")

            # 6️⃣ Wrong Protocol
            elif sub_scenario == 6:
                facts.append("% Failure: Wrong Protocol")
                wrong_protocol = "udp" if protocol == "tcp" else "tcp"
                add_access_path(facts, access_mode, zone, pivot, ws, wrong_protocol, port)

                facts.append(f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv}).")
                facts.append(f"vulExists({ws}, '{cve}', {service}).")
                facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")
                neg.append(f"execCode({ws}, {service_priv}).")

            # 7️⃣ Service on different port
            elif sub_scenario == 7:
                facts.append("% Failure: Service on different port")
                add_access_path(facts, access_mode, zone, pivot, ws, protocol, port)

                wrong_port = port + 111
                facts.append(f"networkServiceInfo({ws}, {service}, {protocol}, {wrong_port}, {service_priv}).")
                facts.append(f"vulExists({ws}, '{cve}', {service}).")
                facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")
                neg.append(f"execCode({ws}, {service_priv}).")

            # 8️⃣ Vulnerable software not exposed
            elif sub_scenario == 8:
                facts.append("% Failure: Vulnerable software not exposed")
                add_access_path(facts, access_mode, zone, pivot, ws, protocol, port)

                facts.append(f"vulExists({ws}, '{cve}', {service}).")
                facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")
                neg.append(f"execCode({ws}, {service_priv}).")

            # 9️⃣ CVE mismatch
            else:
                facts.append("% Failure: CVE mismatch")
                add_access_path(facts, access_mode, zone, pivot, ws, protocol, port)

                other_service = random.choice([s for s in services if s != service])
                wrong_cve = random.choice(services[other_service]["cves"])

                facts.append(f"networkServiceInfo({ws}, {service}, {protocol}, {port}, {service_priv}).")
                facts.append(f"vulExists({ws}, '{wrong_cve}', {other_service}).")
                neg.append(f"execCode({ws}, {service_priv}).")

    print(f"Total: {num_instances} | Positivos: {len(pos)-1} | Negativos: {len(neg)-1}")

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
    parser = argparse.ArgumentParser(description="Generate relational dataset folds")

    parser.add_argument(
        "--folds",
        type=int,
        required=True,
        help="Number of folds to generate"
    )

    parser.add_argument(
        "--instances",
        type=int,
        required=True,
        help="Number of instances per fold"
    )

    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory"
    )

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    for fold in range(1, args.folds + 1):

        facts, pos, neg = generate_balanced_dataset(num_instances=args.instances,)

        save_fold(args.output, fold, facts, pos, neg)

        print(f"Fold {fold} gerado com {args.instances} instâncias.")

    print("\nTodos os folds foram gerados com sucesso!")


if __name__ == "__main__":
    main()