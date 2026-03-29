import os
import argparse
import random

def generate_balanced_dataset(
    num_instances=1000,
    start_index=1,
    missing_prob=0.0
):
    """
    Gera um dataset balanceado onde a probabilidade de omissão 
    é aplicada uniformemente aos fatos críticos de instâncias positivas.
    """
    facts = ["% --- Background Knowledge ---"]
    pos = ["% --- Positive Examples ---"]
    neg = ["% --- Negative Examples ---"]

    services = {
        "apache": {
            "ports": [80, 443],
            "protocols": ["tcp"],
            "cves": ["CVE-2019-0211"],
            "default_priv": "www-data"
        },
        "nginx": {
            "ports": [80],
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
        }
    }

    end_index = start_index + num_instances

    for i in range(start_index, end_index):
        ws = f"webServer_{i}"
        zone = f"internet_{i}"
        
        service_name = random.choice(list(services.keys()))
        svc = services[service_name]
        port = random.choice(svc["ports"])
        protocol = svc["protocols"][0]
        cve = random.choice(svc["cves"])
        service_priv = svc["default_priv"]

        is_positive = (i - start_index) < (num_instances // 2)

        # ================= POSITIVOS (Com Omissão Uniforme) =================
        if is_positive:
            facts.append(f"\n% --- Instance {i} (Positive) ---")
            
            # Fatos que sempre devem existir para manter a estrutura mínima do grafo
            facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")
            facts.append(f"networkServiceInfo({ws}, {service_name}, {protocol}, {port}, {service_priv}).")

            # Fatos críticos sujeitos à omissão (Stress Test) [cite: 278, 280]
            # 1. Localização do atacante
            if random.random() >= missing_prob:
                facts.append(f"attackerLocated({zone}).")
            
            # 2. Existência da vulnerabilidade
            if random.random() >= missing_prob:
                facts.append(f"vulExists({ws}, '{cve}', {service_name}).")
            
            # 3. Propriedade da vulnerabilidade
            if random.random() >= missing_prob:
                facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")

            pos.append(f"execCode({ws}, {service_priv}).")

        # ================= NEGATIVOS (Falhas Lógicas) =================
        else:
            facts.append(f"\n% --- Instance {i} (Negative) ---")
            # Negativos garantem que o modelo não aprenda apenas por presença de fatos [cite: 168]
            failure_type = random.randint(1, 3)

            if failure_type == 1: # Erro de Zona (Atacante em lugar errado)
                facts.append(f"attackerLocated(wrong_zone_{i}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")
            
            elif failure_type == 2: # Erro de Privilégio (Alvo errado) [cite: 171]
                facts.append(f"attackerLocated({zone}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port}).")
                wrong_priv = "root" if service_priv != "root" else "user"
                neg.append(f"execCode({ws}, {wrong_priv}).")
                # Adiciona o resto dos fatos para ser um negativo "difícil"
                facts.append(f"networkServiceInfo({ws}, {service_name}, {protocol}, {port}, {service_priv}).")
                facts.append(f"vulExists({ws}, '{cve}', {service_name}).")
                facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")
                continue

            else: # Erro de Conectividade (Porta errada) [cite: 170]
                facts.append(f"attackerLocated({zone}).")
                facts.append(f"hacl({zone}, {ws}, {protocol}, {port + 100}).")

            facts.append(f"networkServiceInfo({ws}, {service_name}, {protocol}, {port}, {service_priv}).")
            facts.append(f"vulExists({ws}, '{cve}', {service_name}).")
            facts.append(f"vulProperty('{cve}', remoteExploit, privEscalation).")
            neg.append(f"execCode({ws}, {service_priv}).")

    return facts, pos, neg

def save_fold(output_dir, fold_number, facts, pos, neg):
    fold_path = os.path.join(output_dir, f"fold{fold_number:02d}")
    os.makedirs(fold_path, exist_ok=True)
    with open(os.path.join(fold_path, "facts.pl"), "w") as f: f.write("\n".join(facts))
    with open(os.path.join(fold_path, "pos.pl"), "w") as f: f.write("\n".join(pos))
    with open(os.path.join(fold_path, "neg.pl"), "w") as f: f.write("\n".join(neg))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folds", type=int, required=True)
    parser.add_argument("--instances", type=int, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--missing_prob", type=float, default=0.0)
    args = parser.parse_args()

    current_index = 1
    for fold in range(1, args.folds + 1):
        facts, pos, neg = generate_balanced_dataset(args.instances, current_index, args.missing_prob)
        save_fold(args.output, fold, facts, pos, neg)
        current_index += args.instances
        print(f"Fold {fold} gerado com prob_omissao={args.missing_prob}.")

if __name__ == "__main__":
    main()