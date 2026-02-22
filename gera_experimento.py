from srlearn.rdn import BoostedRDNClassifier
from srlearn import Background, Database
import numpy as np
import csv

def get_mulval_like_data():

    train = Database.from_files('dataset/fold03/train/pos.pl', 'dataset/fold03/train/neg.pl', 'dataset/fold03/train/facts.pl')

    train.modes = [
        "execCode(+host, +privilege).", 
        
        "vulExists(+host, -cve, -software).",
        "vulProperty(+cve, #exploitType, #effect).",
        
        "networkServiceInfo(+host, +software, -protocol, +port, -privilege).",
        
        "hacl(+host, -host, -protocol, -port).",
        "hacl(+zone, -host, -protocol, -port).",
        
        "attackerLocated(-host).",
        "attackerLocated(-zone)."
    ]

    return train

# ==========================================
# TEST SET FIXO
# ==========================================
def build_test_set(train):

    test = Database()

    test.pos = ["execCode(146_164_34_82, root)."]
    test.neg = ["execCode(146_164_34_83, root)."]

    test.facts = [

        "attackerLocated(internet).",

        "hacl(internet, 146_164_34_82, tcp, 80).",
        "hacl(internet, 146_164_34_83, tcp, 80).",

        # HOST 82 (esperado HIGH)
        "networkServiceInfo(146_164_34_82, grafana_open_source_6_7_4, tcp, 80, root).",
        "vulExists(146_164_34_82, cve_2022_21703, grafana_open_source_6_7_4).",
        "vulProperty(cve_2022_21703, remoteExploit, privEscalation).",

        # HOST 83 (esperado LOW)
        "networkServiceInfo(146_164_34_83, apache_httpd_2_4_29, tcp, 80, root).",
        "vulExists(146_164_34_83, cve_2024_39573, apache_httpd_2_4_29).",
        "vulProperty(cve_2024_39573, remoteExploit, other)."
    ]

    test.modes = train.modes
    return test


# ==========================================
# TREINO BASE
# ==========================================
train = get_mulval_like_data()
bk = Background(modes=train.modes)
test = build_test_set(train)


# ==========================================
# GRADE DE PARÂMETROS (VOCÊ PODE ALTERAR)
# ==========================================
depth_values = [3, 4, 6]
node_sizes = [2, 3]
estimators_values = [5, 10, 20]


# ==========================================
# EXECUÇÃO DOS EXPERIMENTOS
# ==========================================
with open("analise_parametros.csv", "w", newline="") as f:

    writer = csv.writer(f)
    writer.writerow([
        "max_depth",
        "node_size",
        "n_estimators",
        "prob_82",
        "prob_83",
        "delta"
    ])

    for depth in depth_values:
        for node_size in node_sizes:
            for n_est in estimators_values:

                print(f"Treinando: depth={depth}, "
                      f"node_size={node_size}, "
                      f"n_estimators={n_est}")

                clf = BoostedRDNClassifier(
                    background=bk,
                    target="execCode",
                    max_tree_depth=depth,
                    node_size=node_size,
                    n_estimators=n_est,
                )

                clf.fit(train)

                probs = clf.predict_proba(test)

                prob_82 = probs[0]
                prob_83 = probs[1]
                delta = prob_82 - prob_83

                writer.writerow([
                    depth,
                    node_size,
                    n_est,
                    prob_82,
                    prob_83,
                    delta
                ])

print("Experimentos salvos em analise_parametros.csv")
