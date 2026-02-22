import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("convergencia_hosts.csv")

plt.figure(figsize=(7, 5))
plt.plot(df["n_trees"], df["prob_82"], marker="o", label="prob_82")
plt.plot(df["n_trees"], df["prob_83"], marker="s", label="prob_83")
plt.xlabel("Number of Trees")
plt.ylabel("Predicted Probability of execCode")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
