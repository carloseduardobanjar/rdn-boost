import matplotlib.pyplot as plt

# ======== CURVA PRECISION-RECALL ========

recall = []
precision = []

with open("/Users/carlosesb/Documents/test/.venv/lib/python3.9/site-packages/srlearn/bsrl_data/data2/test/AUC/aucTemp.txt.pr", "r") as f:
    for line in f:
        values = line.strip().split()
        if len(values) == 2:
            r = float(values[0])
            p = float(values[1])
            recall.append(r)
            precision.append(p)

plt.figure()
plt.plot(recall, precision)
plt.xlabel("Recall")
plt.ylabel("Precisão")
# plt.title("Precision-Recall Curve")
plt.xlim([0, 1.05])
plt.ylim([0, 1.05])
plt.grid(True)
plt.tight_layout()
plt.savefig("precision_recall_curve.png")
plt.show()
