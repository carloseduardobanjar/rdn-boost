from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Configuração de estilo para publicações/papers
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    }
)


def plot_grid_heatmaps(csv_path="results_summary_th050.csv"):
    path = Path(csv_path)
    if not path.exists():
        print(f"Erro: Arquivo {csv_path} não encontrado.")
        return

    # Carregar dados
    df = pd.read_csv(path)

    # Converter colunas numéricas
    cols = ["max_depth", "n_estimators", "node_size", "f1", "auc"]
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Criar figura com subplots para cada node_size
    node_sizes = sorted(df["node_size"].unique())
    fig, axes = plt.subplots(
        1, len(node_sizes), figsize=(15, 4.5), sharey=True
    )

    for i, ns in enumerate(node_sizes):
        ax = axes[i]
        df_sub = df[df["node_size"] == ns]

        # Pivota os dados para o formato de matriz (max_depth x n_estimators)
        pivot = df_sub.pivot(
            index="max_depth", columns="n_estimators", values="f1"
        )

        # Plotar Heatmap
        sns.heatmap(
            pivot,
            annot=True,
            fmt=".4f",
            cmap="YlGnBu",
            cbar=(i == len(node_sizes) - 1),
            cbar_kws={"label": "F1-Score"},
            ax=ax,
            vmin=0.60,
            vmax=0.76,
        )

        ax.set_title(f"Node Size = {int(ns)}")
        ax.set_xlabel("N Estimators ($e$)")
        if i == 0:
            ax.set_ylabel("Max Depth ($d$)")
        else:
            ax.set_ylabel("")

    plt.suptitle(
        "F1-Score em função dos hiperparâmetros (Threshold = 0.50)",
        fontsize=14,
        y=1.03,
    )
    plt.tight_layout()

    output_fig = "grid_search_f1_heatmap.png"
    plt.savefig(output_fig, dpi=300, bbox_inches="tight")
    print(f"Gráfico salvo com sucesso em: {output_fig}")
    plt.show()


if __name__ == "__main__":
    plot_grid_heatmaps()