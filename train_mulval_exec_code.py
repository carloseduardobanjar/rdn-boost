import argparse
import csv
import random
import shutil
from collections import defaultdict
from pathlib import Path


MULVAL_MODES = [
    "execCode(+host, +privilege).",
    "recursive_execCode(`host, +privilege).",
    "principalCompromised(+principal).",
    "hasAccount(+principal, +host, -privilege).",
    "canAccessHost(+host).",
    "vulExists(+host, -vulID, -program).",
    "vulExists(+host, -vulID, -program, #range, #consequence).",
    "vulProperty(+vulID, #range, #consequence).",
    "networkServiceInfo(+host, -program, -protocol, -port, -privilege).",
    "netAccess(+host, -protocol, -port).",
    "hacl(+host, -host, -protocol, -port).",
    "hacl(+zone, -host, -protocol, -port).",
    "attackerLocated(-zone).",
    "attackerLocated(-host).",
    "accessMaliciousInput(+host, +principal, -program).",
    "accessFile(+host, #access, -path).",
    "canAccessFile(+host, +privilege, #access, -path).",
    "localFileProtection(+host, +privilege, #access, -path).",
    "logInService(+host, -protocol, -port).",
    "nfsExportInfo(+host, -path, #access, -host).",
    "nfsMounted(+host, -path, +host, -path, #access).",
    "installed(+host, -program).",
    "dependsOn(+host, -program, -program).",
    "clientProgram(+host, -program).",
    "bugHyp(+host, -program, #range, #consequence).",
    "inCompetent(+principal).",
    "competent(+principal).",
    "isWebServer(+host).",
    "advances(-host, +host).",
    "advances(+host, -host).",
    "advances(`host, +host).",
    "hacl(`host, +host, -protocol, -port).",
]


SERVICES = {
    "apache": {
        "ports": ["80", "8080", "443"],
        "protocols": ["tcp"],
        "cves": ["cve_2019_0211", "cve_2017_15715"],
        "default_priv": "www_data",
    },
    "nginx": {
        "ports": ["80", "443"],
        "protocols": ["tcp"],
        "cves": ["cve_2013_2028"],
        "default_priv": "www_data",
    },
    "sshd": {
        "ports": ["22"],
        "protocols": ["tcp"],
        "cves": ["cve_2018_15473"],
        "default_priv": "user",
    },
    "mysql": {
        "ports": ["3306"],
        "protocols": ["tcp"],
        "cves": ["cve_2016_6662"],
        "default_priv": "mysql",
    },
    "vpnService": {
        "ports": ["1194", "443"],
        "protocols": ["udp", "tcp"],
        "cves": ["cve_2020_15078"],
        "default_priv": "vpn_user",
    },
    "browser": {
        "ports": [],
        "protocols": [],
        "cves": ["cve_client_browser"],
        "default_priv": "user",
    },
    "libssl": {
        "ports": [],
        "protocols": [],
        "cves": ["cve_libssl"],
        "default_priv": "user",
    },
}

PRIVILEGES = ["root", "user", "www_data", "mysql", "ftp", "vpn_user"]
PATHS = ["bin_app", "startup_script", "web_root", "export_share", "mnt_share"]
RANGES = ["remoteExploit", "localExploit", "remoteClient"]
CONSEQUENCES = ["privEscalation", "denialOfService", "informationDisclosure"]
OK_IF_UNKNOWN_PREDICATES = [
    "recursive_execCode/2",
    "netAccess/3",
    "vulExists/5",
    "accessFile/3",
    "canAccessFile/4",
    "canAccessHost/1",
    "principalCompromised/1",
    "accessMaliciousInput/3",
    "logInService/3",
    "localFileProtection/4",
    "nfsMounted/5",
    "nfsExportInfo/4",
    "dependsOn/3",
    "clientProgram/2",
    "bugHyp/4",
    "inCompetent/1",
    "competent/1",
    "isWebServer/1",
    "advances/2",
]
BK_DIRECTIVES = [f"okIfUnknown: {predicate}." for predicate in OK_IF_UNKNOWN_PREDICATES]


def fact(name, *args):
    return f"{name}({', '.join(str(arg) for arg in args)})."


def add_fact(facts, name, *args):
    facts[name].add(tuple(str(arg) for arg in args))


def serialize_facts(facts, exclude=None):
    exclude = set(exclude or [])
    lines = []
    for name in sorted(facts):
        if name in exclude:
            continue
        for args in sorted(facts[name]):
            lines.append(fact(name, *args))
    return lines


def choose_service(include_clients=True):
    services = list(SERVICES)
    if not include_clients:
        services = [service for service in services if SERVICES[service]["ports"]]
    service = random.choice(services)
    info = SERVICES[service]
    return service, info


def generate_random_primitives(num_hosts, start_index, density):
    facts = defaultdict(set)
    hosts = [f"host_{index}" for index in range(start_index, start_index + num_hosts)]
    zones = [f"internet_{start_index}", f"dmz_{start_index}", f"corp_{start_index}"]
    principals = [f"user_{index}" for index in range(start_index, start_index + num_hosts)]
    malicious_hosts = [f"evil_{start_index}", f"evil_{start_index + 1}"]

    for zone in zones:
        if random.random() < 0.65:
            add_fact(facts, "attackerLocated", zone)

    for malicious_host in malicious_hosts:
        if random.random() < 0.75:
            add_fact(facts, "attackerLocated", malicious_host)

    for host in hosts:
        if random.random() < 0.08 * density:
            add_fact(facts, "attackerLocated", host)

        if random.random() < 0.25:
            add_fact(facts, "isWebServer", host)

        services_on_host = random.sample(
            [service for service in SERVICES if SERVICES[service]["ports"]],
            k=random.randint(1, 3),
        )

        for service in services_on_host:
            info = SERVICES[service]
            protocol = random.choice(info["protocols"])
            port = random.choice(info["ports"])
            privilege = info["default_priv"]
            add_fact(facts, "networkServiceInfo", host, service, protocol, port, privilege)
            add_fact(facts, "installed", host, service)

            for zone in zones:
                if random.random() < 0.22 * density:
                    add_fact(facts, "hacl", zone, host, protocol, port)

            if random.random() < 0.32 * density:
                cve = random.choice(info["cves"])
                vuln_range = random.choice(RANGES)
                consequence = random.choice(CONSEQUENCES)
                add_fact(facts, "vulExists", host, cve, service)
                add_fact(facts, "vulProperty", cve, vuln_range, consequence)

            if random.random() < 0.10 * density:
                add_fact(facts, "bugHyp", host, service, "remoteExploit", "privEscalation")

        if random.random() < 0.25 * density:
            add_fact(facts, "installed", host, "browser")
            add_fact(facts, "clientProgram", host, "browser")
            add_fact(facts, "vulExists", host, f"cve_client_{host}", "browser")
            add_fact(facts, "vulProperty", f"cve_client_{host}", "remoteClient", "privEscalation")

        if random.random() < 0.20 * density:
            add_fact(facts, "dependsOn", host, random.choice(services_on_host), "libssl")
            add_fact(facts, "vulExists", host, "cve_libssl", "libssl")
            add_fact(facts, "vulProperty", "cve_libssl", "remoteExploit", "privEscalation")

        for principal in random.sample(principals, k=random.randint(1, min(3, len(principals)))):
            if random.random() < 0.35 * density:
                add_fact(facts, "hasAccount", principal, host, random.choice(PRIVILEGES[1:]))
            if random.random() < 0.18 * density:
                if random.random() < 0.4:
                    add_fact(facts, "inCompetent", principal)
                else:
                    add_fact(facts, "competent", principal)

        for path in random.sample(PATHS, k=random.randint(1, 2)):
            if random.random() < 0.20 * density:
                add_fact(
                    facts,
                    "localFileProtection",
                    host,
                    random.choice(PRIVILEGES),
                    random.choice(["read", "write"]),
                    path,
                )

        for evil_host in malicious_hosts:
            if random.random() < 0.22 * density:
                add_fact(facts, "hacl", host, evil_host, "httpProtocol", "httpPort")

    for src in hosts:
        for dst in random.sample(hosts, k=min(3, len(hosts))):
            if src != dst and random.random() < 0.12 * density:
                add_fact(facts, "advances", src, dst)
                add_fact(facts, "hacl", src, dst, "tcp", random.choice(["22", "80", "443"]))

    for server in random.sample(hosts, k=max(1, len(hosts) // 5)):
        client = random.choice([host for host in hosts if host != server])
        access = random.choice(["read", "write"])
        add_fact(facts, "nfsMounted", client, "mnt_share", server, "export_share", access)
        add_fact(facts, "nfsExportInfo", server, "export_share", access, client)
        add_fact(facts, "hacl", client, server, "nfsProtocol", "nfsPort")

    return facts, hosts


def generate_attack_chain_primitives(num_hosts, start_index, positives_per_fold, negatives_per_fold):
    facts = defaultdict(set)
    target_positives = positives_per_fold or max(12, num_hosts // 10)
    target_negatives = negatives_per_fold or target_positives
    hosts = []
    positive_hosts = []
    negative_hosts = []
    host_index = start_index
    chain_index = 1
    chain_lengths = [3, 4, 5, 6, 7]

    def next_host(prefix):
        nonlocal host_index
        host = f"{prefix}_{host_index}"
        host_index += 1
        hosts.append(host)
        return host

    while len(positive_hosts) < target_positives:
        chain_len = min(
            random.choice(chain_lengths),
            target_positives - len(positive_hosts),
        )
        if chain_len <= 0:
            break

        zone = f"internet_chain_{start_index}_{chain_index}"
        add_fact(facts, "attackerLocated", zone)
        previous_host = None

        for step in range(1, chain_len + 1):
            host = next_host("chain_host")
            service = "apache"
            cve = f"cve_chain_{host}"
            add_fact(facts, "networkServiceInfo", host, service, "tcp", "80", "www_data")
            add_fact(facts, "installed", host, service)
            add_fact(facts, "vulExists", host, cve, service)
            add_fact(facts, "vulProperty", cve, "remoteExploit", "privEscalation")

            if previous_host is None:
                add_fact(facts, "hacl", zone, host, "tcp", "80")
            else:
                add_fact(facts, "advances", previous_host, host)
                add_fact(facts, "hacl", previous_host, host, "tcp", "80")

            previous_host = host
            positive_hosts.append(host)

        sink = next_host("chain_sink")
        add_fact(facts, "advances", previous_host, sink)
        add_fact(facts, "hacl", previous_host, sink, "tcp", "80")
        chain_index += 1

    while len(negative_hosts) < target_negatives:
        decoy = next_host("decoy_host")
        blocked_source = next_host("blocked_host")
        decoy_sink = next_host("decoy_sink")
        service = "apache"
        cve = f"cve_decoy_{decoy}"
        add_fact(facts, "networkServiceInfo", decoy, service, "tcp", "80", "www_data")
        add_fact(facts, "installed", decoy, service)
        add_fact(facts, "vulExists", decoy, cve, service)
        add_fact(facts, "vulProperty", cve, "remoteExploit", "privEscalation")
        add_fact(facts, "advances", blocked_source, decoy)
        add_fact(facts, "hacl", blocked_source, decoy, "tcp", "80")
        add_fact(facts, "advances", decoy, decoy_sink)
        add_fact(facts, "hacl", decoy, decoy_sink, "tcp", "80")
        negative_hosts.append(decoy)

    return facts, hosts, positive_hosts, negative_hosts


def close_mulval_rules(primitive_facts, max_iterations=80):
    facts = defaultdict(set)
    for name, values in primitive_facts.items():
        facts[name].update(values)

    exec_code_rules = defaultdict(set)

    def derive(name, *args, rule=None):
        before = len(facts[name])
        add_fact(facts, name, *args)
        added = len(facts[name]) > before
        if name == "execCode" and rule:
            exec_code_rules[tuple(str(arg) for arg in args)].add(rule)
        return added

    for _iteration in range(max_iterations):
        changed = False

        for vul_exists in list(facts["vulExists"]):
            if len(vul_exists) == 5:
                changed |= derive("vulExists5", *vul_exists)
                continue

            host, cve, software = vul_exists
            for prop_cve, vuln_range, consequence in list(facts["vulProperty"]):
                if cve == prop_cve:
                    changed |= derive("vulExists5", host, cve, software, vuln_range, consequence)

        for host, software, vuln_range, consequence in list(facts["bugHyp"]):
            changed |= derive("vulExists5", host, f"bug_{host}_{software}", software, vuln_range, consequence)

        for host, cve, library, vuln_range, consequence in list(facts["vulExists5"]):
            for dep_host, software, dep_library in list(facts["dependsOn"]):
                if host == dep_host and library == dep_library:
                    changed |= derive("vulExists5", host, cve, software, vuln_range, consequence)

        for host, software, protocol, port, _privilege in list(facts["networkServiceInfo"]):
            if software in {"sshd", "vpnService"}:
                changed |= derive("logInService", host, protocol, port)

        for located_item in list(facts["attackerLocated"]):
            located = located_item[0]
            for src, dst, protocol, port in list(facts["hacl"]):
                if located == src:
                    changed |= derive("netAccess", dst, protocol, port)

            for host, _software, protocol, port, _privilege in list(facts["networkServiceInfo"]):
                if located == host:
                    changed |= derive("netAccess", host, protocol, port)

        for src_host, _privilege in list(facts["execCode"]):
            for adv_src, dst in list(facts["advances"]):
                if src_host != adv_src:
                    continue
                for hacl_src, hacl_dst, protocol, port in list(facts["hacl"]):
                    if hacl_src == src_host and hacl_dst == dst:
                        changed |= derive("netAccess", dst, protocol, port)

        for host, protocol, port in list(facts["logInService"]):
            if (host, protocol, port) in facts["netAccess"]:
                changed |= derive("canAccessHost", host)

        for host, _privilege in list(facts["execCode"]):
            changed |= derive("canAccessHost", host)

        for host, user, access, path in list(facts["localFileProtection"]):
            changed |= derive("canAccessFile", host, user, access, path)

        for host, user in list(facts["execCode"]):
            for caf_host, caf_user, access, path in list(facts["canAccessFile"]):
                if host == caf_host and user == caf_user:
                    changed |= derive("accessFile", host, access, path)

        for client, client_path, server, server_path, access in list(facts["nfsMounted"]):
            if (client, access, client_path) in facts["accessFile"]:
                changed |= derive("accessFile", server, access, server_path)
            if access == "read":
                for srv, srv_access, srv_path in list(facts["accessFile"]):
                    if srv == server and srv_path == server_path:
                        changed |= derive("accessFile", client, srv_access, client_path)

        for client, _user in list(facts["execCode"]):
            for server, path, access, export_client in list(facts["nfsExportInfo"]):
                if client != export_client:
                    continue
                if (client, server, "nfsProtocol", "nfsPort") in facts["hacl"]:
                    changed |= derive("accessFile", server, access, path)

        for principal, host, _privilege in list(facts["hasAccount"]):
            if (host, "root") in facts["execCode"]:
                changed |= derive("principalCompromised", principal)
            if (host, _privilege) in facts["execCode"]:
                changed |= derive("principalCompromised", principal)

        for victim, host, privilege in list(facts["hasAccount"]):
            if victim in {item[0] for item in facts["principalCompromised"]}:
                if (host,) in facts["canAccessHost"]:
                    changed |= derive(
                        "execCode",
                        host,
                        privilege,
                        rule="compromised_principal_account",
                    )

        for host, cve, software, vuln_range, consequence in list(facts["vulExists5"]):
            if vuln_range == "localExploit" and consequence == "privEscalation":
                if any(exec_host == host for exec_host, _priv in facts["execCode"]):
                    changed |= derive("execCode", host, "root", rule="local_exploit")

            if vuln_range == "remoteExploit" and consequence == "privEscalation":
                for svc_host, svc, protocol, port, privilege in list(facts["networkServiceInfo"]):
                    if host == svc_host and software == svc:
                        if (host, protocol, port) in facts["netAccess"]:
                            changed |= derive(
                                "execCode",
                                host,
                                privilege,
                                rule="remote_service_exploit",
                            )

            if vuln_range == "remoteClient" and consequence == "privEscalation":
                for victim, acct_host, privilege in list(facts["hasAccount"]):
                    if host != acct_host:
                        continue
                    if (host, victim, software) in facts["accessMaliciousInput"]:
                        changed |= derive(
                            "execCode",
                            host,
                            privilege,
                            rule="remote_client_exploit",
                        )

        for host, access, _path in list(facts["accessFile"]):
            if access == "write":
                changed |= derive("execCode", host, "root", rule="trojan_write_access")

        for host, victim, software in build_malicious_input(facts):
            changed |= derive("accessMaliciousInput", host, victim, software)

        if not changed:
            break

    return facts, exec_code_rules


def build_malicious_input(facts):
    results = set()
    incompetent = {item[0] for item in facts["inCompetent"]}
    competent = {item[0] for item in facts["competent"]}
    principals = incompetent | competent

    remote_client_software = defaultdict(set)
    for host, _cve, software, vuln_range, consequence in facts["vulExists5"]:
        if vuln_range == "remoteClient" and consequence == "privEscalation":
            remote_client_software[host].add(software)

    for host, software in facts["clientProgram"]:
        remote_client_software[host].add(software)

    for victim in principals:
        for host, software_set in remote_client_software.items():
            for hacl_src, malicious_machine, protocol, port in facts["hacl"]:
                if hacl_src != host or protocol != "httpProtocol" or port != "httpPort":
                    continue

                if (malicious_machine,) in facts["attackerLocated"]:
                    for software in software_set:
                        results.add((host, victim, software))

                if victim in incompetent and (malicious_machine,) in facts["isWebServer"]:
                    if any(exec_host == malicious_machine for exec_host, _ in facts["execCode"]):
                        for software in software_set:
                            results.add((host, victim, software))

    return results


def build_examples(facts, hosts, negative_ratio, positives_per_fold=None, negatives_per_fold=None):
    positive_candidates = sorted(facts["execCode"])
    positives = list(positive_candidates)
    if positives_per_fold is not None:
        random.shuffle(positives)
        positives = sorted(positives[:positives_per_fold])

    observed_privileges = set(PRIVILEGES)

    for _host, _software, _protocol, _port, privilege in facts["networkServiceInfo"]:
        observed_privileges.add(privilege)
    for _principal, _host, privilege in facts["hasAccount"]:
        observed_privileges.add(privilege)

    candidates = {(host, privilege) for host in hosts for privilege in observed_privileges}
    negatives = sorted(candidates - set(positive_candidates))
    random.shuffle(negatives)

    if negatives_per_fold is not None:
        wanted_negatives = negatives_per_fold
    else:
        wanted_negatives = max(len(positives) * negative_ratio, 1)
    negatives = sorted(negatives[:wanted_negatives])

    return [fact("execCode", *item) for item in positives], [fact("execCode", *item) for item in negatives]


def build_attack_chain_examples(facts, positive_hosts, negative_hosts, positives_per_fold, negatives_per_fold):
    target_positives = positives_per_fold or len(positive_hosts)
    target_negatives = negatives_per_fold or len(negative_hosts)

    positive_examples = []
    for host in positive_hosts:
        example = (host, "www_data")
        if example in facts["execCode"]:
            positive_examples.append(fact("execCode", *example))
        if len(positive_examples) >= target_positives:
            break

    negative_examples = []
    for host in negative_hosts:
        example = (host, "www_data")
        if example not in facts["execCode"]:
            negative_examples.append(fact("execCode", *example))
        if len(negative_examples) >= target_negatives:
            break

    return positive_examples, negative_examples


def summarize_rule_coverage(positive_examples, exec_code_rules):
    def parse_exec_code_example(example):
        prefix = "execCode("
        suffix = ")."
        if not example.startswith(prefix) or not example.endswith(suffix):
            raise ValueError(f"Exemplo execCode invalido: {example}")
        return tuple(example[len(prefix) : -len(suffix)].split(", "))

    positive_tuples = {
        parse_exec_code_example(example)
        for example in positive_examples
    }
    coverage = defaultdict(int)

    for example in positive_tuples:
        rules = exec_code_rules.get(example, set())
        if not rules:
            coverage["unknown"] += 1
            continue
        for rule in rules:
            coverage[rule] += 1

    return dict(sorted(coverage.items()))


def print_rule_coverage(coverage):
    if not coverage:
        print("Cobertura execCode: nenhum positivo inferido")
        return

    formatted = " | ".join(f"{rule}={count}" for rule, count in coverage.items())
    print(f"Cobertura execCode por regra: {formatted}")


def write_rule_coverage_csv(path, rows):
    totals = defaultdict(int)
    for row in rows:
        totals[row["rule"]] += row["derivations"]

    with path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["fold", "rule", "derivations"])
        writer.writeheader()
        writer.writerows(rows)
        for rule, count in sorted(totals.items()):
            writer.writerow(
                {
                    "fold": "all",
                    "rule": rule,
                    "derivations": count,
                }
            )


def generate_dataset(
    num_instances,
    start_index,
    density,
    negative_ratio,
    min_positives,
    background,
    positives_per_fold=None,
    negatives_per_fold=None,
    dataset_style="random",
):
    required_positives = positives_per_fold if positives_per_fold is not None else min_positives
    required_negatives = negatives_per_fold

    for attempt in range(1, 31):
        print(
            f"Tentativa {attempt}: gerando {num_instances} hosts ({dataset_style}) "
            "e aplicando fechamento logico...",
            flush=True,
        )
        if dataset_style == "attack_chain":
            primitive_facts, hosts, chain_positive_hosts, chain_negative_hosts = (
                generate_attack_chain_primitives(
                    num_instances,
                    start_index,
                    positives_per_fold,
                    negatives_per_fold,
                )
            )
        else:
            primitive_facts, hosts = generate_random_primitives(num_instances, start_index, density)
            chain_positive_hosts = []
            chain_negative_hosts = []

        closed_facts, exec_code_rules = close_mulval_rules(primitive_facts)
        if dataset_style == "attack_chain":
            positives, negatives = build_attack_chain_examples(
                closed_facts,
                chain_positive_hosts,
                chain_negative_hosts,
                positives_per_fold,
                negatives_per_fold,
            )
        else:
            positives, negatives = build_examples(
                closed_facts,
                hosts,
                negative_ratio,
                positives_per_fold,
                negatives_per_fold,
            )

        has_enough_positives = len(positives) >= required_positives
        has_enough_negatives = (
            len(negatives) == required_negatives
            if required_negatives is not None
            else bool(negatives)
        )

        if has_enough_positives and has_enough_negatives:
            background_facts = defaultdict(set)
            for name, values in primitive_facts.items():
                background_facts[name].update(values)

            if background in {"closed", "closed_with_execCode"}:
                for name, values in closed_facts.items():
                    if name != "execCode" or background == "closed_with_execCode":
                        background_facts[name].update(values)
                if "vulExists5" in background_facts:
                    background_facts["vulExists"].update(background_facts.pop("vulExists5"))

            coverage = summarize_rule_coverage(positives, exec_code_rules)
            return serialize_facts(background_facts), positives, negatives, coverage

        print(
            f"Tentativa {attempt}: {len(positives)} positivos e {len(negatives)} negativos; "
            "gerando novos fatos."
        )

    raise RuntimeError("Nao foi possivel gerar exemplos suficientes com os parametros atuais.")


def write_lines(path, lines):
    path.write_text("\n".join(lines) + "\n")


def generate_folds(
    output_dir,
    folds,
    instances_per_fold,
    seed,
    density,
    negative_ratio,
    min_positives,
    background,
    positives_per_fold=None,
    negatives_per_fold=None,
    dataset_style="random",
):
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    current_index = 1
    coverage_rows = []
    for fold in range(1, folds + 1):
        fold_dir = output_dir / f"fold{fold:02d}"
        fold_dir.mkdir(parents=True, exist_ok=True)

        print(
            f"\nGerando fold{fold:02d}: hosts={instances_per_fold}, density={density}, "
            f"background={background}, dataset_style={dataset_style}",
            flush=True,
        )

        facts, positives, negatives, coverage = generate_dataset(
            instances_per_fold,
            current_index,
            density,
            negative_ratio,
            min_positives,
            background,
            positives_per_fold,
            negatives_per_fold,
            dataset_style,
        )
        facts_header = (
            "% --- Primitive MulVAL facts ---"
            if background == "primitive"
            else "% --- Primitive + derived MulVAL facts ---"
        )
        write_lines(
            fold_dir / "facts.pl",
            [facts_header, *BK_DIRECTIVES, *facts],
        )
        write_lines(fold_dir / "pos.pl", ["% --- Inferred positive execCode examples ---", *positives])
        write_lines(fold_dir / "neg.pl", ["% --- Sampled negative execCode examples ---", *negatives])

        current_index += instances_per_fold
        print(
            f"fold{fold:02d}: {len(facts)} facts, "
            f"{len(positives)} positivos inferidos, {len(negatives)} negativos amostrados"
        )
        print_rule_coverage(coverage)

        for rule, count in coverage.items():
            coverage_rows.append(
                {
                    "fold": f"fold{fold:02d}",
                    "rule": rule,
                    "derivations": count,
                }
            )

    coverage_path = output_dir / "exec_code_rule_coverage.csv"
    write_rule_coverage_csv(coverage_path, coverage_rows)
    print(f"Cobertura por regra salva em: {coverage_path}")


def merge_files(input_files, output_file):
    with output_file.open("w") as outfile:
        for input_file in input_files:
            outfile.write(input_file.read_text())
            outfile.write("\n")


def load_database(data_path, fold_names, tmp_dir, prefix):
    from srlearn import Database

    pos_files = [data_path / fold / "pos.pl" for fold in fold_names]
    neg_files = [data_path / fold / "neg.pl" for fold in fold_names]
    fact_files = [data_path / fold / "facts.pl" for fold in fold_names]

    merged_pos = tmp_dir / f"{prefix}_pos.pl"
    merged_neg = tmp_dir / f"{prefix}_neg.pl"
    merged_facts = tmp_dir / f"{prefix}_facts.pl"

    merge_files(pos_files, merged_pos)
    merge_files(neg_files, merged_neg)
    merge_files(fact_files, merged_facts)

    db = Database.from_files(str(merged_pos), str(merged_neg), str(merged_facts))
    db.modes = MULVAL_MODES
    return db


def read_examples(path):
    examples = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("%"):
            examples.append(line)
    return examples


def roc_auc_score(y_true, probabilities):
    positives = [score for label, score in zip(y_true, probabilities) if label == 1]
    negatives = [score for label, score in zip(y_true, probabilities) if label == 0]

    if not positives or not negatives:
        return None

    wins = 0.0
    total = len(positives) * len(negatives)
    for pos_score in positives:
        for neg_score in negatives:
            if pos_score > neg_score:
                wins += 1.0
            elif pos_score == neg_score:
                wins += 0.5
    return wins / total


def evaluate_predictions(y_true, probabilities, threshold):
    predicted = [1 if probability >= threshold else 0 for probability in probabilities]

    tp = sum(1 for actual, pred in zip(y_true, predicted) if actual == 1 and pred == 1)
    tn = sum(1 for actual, pred in zip(y_true, predicted) if actual == 0 and pred == 0)
    fp = sum(1 for actual, pred in zip(y_true, predicted) if actual == 0 and pred == 1)
    fn = sum(1 for actual, pred in zip(y_true, predicted) if actual == 1 and pred == 0)

    total = len(y_true)
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    auc = roc_auc_score(y_true, probabilities)

    positive_scores = [score for label, score in zip(y_true, probabilities) if label == 1]
    negative_scores = [score for label, score in zip(y_true, probabilities) if label == 0]

    return {
        "total": total,
        "positives": len(positive_scores),
        "negatives": len(negative_scores),
        "threshold": threshold,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc": auc,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "prob_min": min(probabilities) if probabilities else 0.0,
        "prob_mean": sum(probabilities) / total if total else 0.0,
        "prob_max": max(probabilities) if probabilities else 0.0,
        "pos_prob_mean": sum(positive_scores) / len(positive_scores) if positive_scores else 0.0,
        "neg_prob_mean": sum(negative_scores) / len(negative_scores) if negative_scores else 0.0,
    }


def find_best_threshold(y_true, probabilities):
    candidates = sorted(set(probabilities))
    if not candidates:
        return 0.5, evaluate_predictions(y_true, probabilities, 0.5)

    best_threshold = candidates[0]
    best_metrics = evaluate_predictions(y_true, probabilities, best_threshold)
    for threshold in candidates:
        metrics = evaluate_predictions(y_true, probabilities, threshold)
        if (
            metrics["f1"] > best_metrics["f1"]
            or (
                metrics["f1"] == best_metrics["f1"]
                and metrics["accuracy"] > best_metrics["accuracy"]
            )
        ):
            best_threshold = threshold
            best_metrics = metrics

    return best_threshold, best_metrics


def print_metrics(title, metrics):
    auc = "n/a" if metrics["auc"] is None else f"{metrics['auc']:.4f}"
    print(f"\n{title}")
    print(
        f"Exemplos: total={metrics['total']} | "
        f"pos={metrics['positives']} | neg={metrics['negatives']}"
    )
    print(
        f"Probabilidades: min={metrics['prob_min']:.4f} | "
        f"media={metrics['prob_mean']:.4f} | max={metrics['prob_max']:.4f}"
    )
    print(
        f"Media por classe: pos={metrics['pos_prob_mean']:.4f} | "
        f"neg={metrics['neg_prob_mean']:.4f}"
    )
    print(
        f"Metricas @{metrics['threshold']:.2f}: "
        f"acc={metrics['accuracy']:.4f} | precision={metrics['precision']:.4f} | "
        f"recall={metrics['recall']:.4f} | f1={metrics['f1']:.4f} | auc={auc}"
    )
    print(
        f"Matriz: TP={metrics['tp']} | FP={metrics['fp']} | "
        f"TN={metrics['tn']} | FN={metrics['fn']}"
    )


def write_metrics_csv(path, rows):
    fieldnames = [
        "fold",
        "train_folds",
        "test_fold",
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
        "prob_min",
        "prob_mean",
        "prob_max",
        "pos_prob_mean",
        "neg_prob_mean",
        "best_threshold",
        "best_accuracy",
        "best_precision",
        "best_recall",
        "best_f1",
    ]
    with path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_predictions_csv(path, examples, y_true, probabilities, threshold):
    with path.open("w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["example", "actual", "probability", "predicted"])
        for example, actual, probability in zip(examples, y_true, probabilities):
            writer.writerow([example, actual, f"{probability:.8f}", int(probability >= threshold)])


def train_cross_validation(args):
    import numpy as np
    from srlearn import Background
    from srlearn.rdn import BoostedRDNClassifier

    data_path = Path(args.data_path)
    output_path = Path(args.output_path)
    tmp_dir = output_path / "_tmp"

    output_path.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if args.generate:
        generate_folds(
            data_path,
            args.folds,
            args.instances_per_fold,
            args.seed,
            args.density,
            args.negative_ratio,
            args.min_positives,
            args.background,
            args.positives_per_fold,
            args.negatives_per_fold,
            args.dataset_style,
        )

    fold_names = [f"fold{i:02d}" for i in range(1, args.folds + 1)]
    results = []
    all_y_true = []
    metrics_rows = []

    for fold_index, test_fold in enumerate(fold_names):
        train_folds = [fold for fold in fold_names if fold != test_fold]
        print("\n==============================")
        print(f"Fold {fold_index + 1}/{args.folds}")
        print(f"Treino: {train_folds}")
        print(f"Teste : {test_fold}")

        train_db = load_database(data_path, train_folds, tmp_dir, f"train_{fold_index}")
        test_db = load_database(data_path, [test_fold], tmp_dir, f"test_{fold_index}")
        background = Background(
            modes=MULVAL_MODES,
            ok_if_unknown=OK_IF_UNKNOWN_PREDICATES,
            recursion=True,
        )

        clf = BoostedRDNClassifier(
            background=background,
            target="execCode",
            max_tree_depth=args.max_depth,
            node_size=args.node_size,
            n_estimators=args.n_estimators,
        )

        clf.fit(train_db)
        probabilities = np.asarray(clf.predict_proba(test_db), dtype=float)
        probabilities_list = probabilities.tolist()

        test_pos = read_examples(data_path / test_fold / "pos.pl")
        test_neg = read_examples(data_path / test_fold / "neg.pl")
        test_examples = test_pos + test_neg
        y_true = [1] * len(test_pos) + [0] * len(test_neg)

        if len(probabilities_list) != len(y_true):
            raise RuntimeError(
                f"O fold {test_fold} gerou {len(probabilities_list)} probabilidades, "
                f"mas possui {len(y_true)} exemplos em pos.pl/neg.pl."
            )

        results.extend(probabilities_list)
        all_y_true.extend(y_true)

        model_source = Path(clf.file_system.files.DIRECTORY)
        model_dest = output_path / f"fold_{fold_index + 1}"
        if model_dest.exists():
            shutil.rmtree(model_dest)
        shutil.copytree(model_source, model_dest)

        print(f"Modelo salvo em: {model_dest}")

        fold_metrics = evaluate_predictions(y_true, probabilities_list, args.threshold)
        print_metrics("Resultados do fold", fold_metrics)

        best_threshold, best_metrics = find_best_threshold(y_true, probabilities_list)
        print(
            f"Melhor threshold observado: {best_threshold:.4f} | "
            f"acc={best_metrics['accuracy']:.4f} | precision={best_metrics['precision']:.4f} | "
            f"recall={best_metrics['recall']:.4f} | f1={best_metrics['f1']:.4f}"
        )

        metrics_rows.append(
            {
                "fold": fold_index + 1,
                "train_folds": " ".join(train_folds),
                "test_fold": test_fold,
                **fold_metrics,
                "best_threshold": best_threshold,
                "best_accuracy": best_metrics["accuracy"],
                "best_precision": best_metrics["precision"],
                "best_recall": best_metrics["recall"],
                "best_f1": best_metrics["f1"],
            }
        )

        predictions_path = output_path / f"predictions_fold_{fold_index + 1}.csv"
        write_predictions_csv(predictions_path, test_examples, y_true, probabilities_list, args.threshold)
        print(f"Predicoes salvas em: {predictions_path}")

    if results:
        print("\nResumo CV")
        overall_metrics = evaluate_predictions(all_y_true, results, args.threshold)
        print_metrics("Resultados agregados", overall_metrics)
        best_threshold, best_metrics = find_best_threshold(all_y_true, results)
        print(
            f"Melhor threshold agregado: {best_threshold:.4f} | "
            f"acc={best_metrics['accuracy']:.4f} | precision={best_metrics['precision']:.4f} | "
            f"recall={best_metrics['recall']:.4f} | f1={best_metrics['f1']:.4f}"
        )

        metrics_path = output_path / "metrics_summary.csv"
        write_metrics_csv(metrics_path, metrics_rows)
        print(f"Metricas por fold salvas em: {metrics_path}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Treina RDN-Boost para execCode/2 usando fechamento logico MulVAL-like."
    )
    parser.add_argument("--data_path", default="./mulval_dataset")
    parser.add_argument("--output_path", default="./mulval_output")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--instances_per_fold", type=int, default=120)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--density", type=float, default=1.0)
    parser.add_argument("--negative_ratio", type=int, default=2)
    parser.add_argument("--min_positives", type=int, default=5)
    parser.add_argument(
        "--positives_per_fold",
        type=int,
        default=None,
        help="Quantidade exata de exemplos positivos execCode a salvar por fold. Se omitido, usa todos os positivos inferidos.",
    )
    parser.add_argument(
        "--negatives_per_fold",
        type=int,
        default=None,
        help="Quantidade exata de exemplos negativos execCode a salvar por fold. Se omitido, usa --negative_ratio.",
    )
    parser.add_argument(
        "--background",
        choices=["primitive", "closed", "closed_with_execCode"],
        default="primitive",
        help=(
            "primitive salva apenas fatos primitivos; closed inclui derivados "
            "intermediarios; closed_with_execCode inclui tambem execCode derivado."
        ),
    )
    parser.add_argument(
        "--dataset_style",
        choices=["random", "attack_chain"],
        default="random",
        help="random usa fatos sinteticos gerais; attack_chain gera cadeias multihop para testar recursao.",
    )
    parser.add_argument("--max_depth", type=int, default=5)
    parser.add_argument("--node_size", type=int, default=3)
    parser.add_argument("--n_estimators", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Gera os folds aleatorios e seus rotulos inferidos antes de treinar.",
    )
    parser.add_argument(
        "--generate_only",
        action="store_true",
        help="Gera os folds e encerra sem importar srlearn nem treinar.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.generate_only:
        generate_folds(
            Path(args.data_path),
            args.folds,
            args.instances_per_fold,
            args.seed,
            args.density,
            args.negative_ratio,
            args.min_positives,
            args.background,
            args.positives_per_fold,
            args.negatives_per_fold,
            args.dataset_style,
        )
        return
    train_cross_validation(args)


if __name__ == "__main__":
    main()
