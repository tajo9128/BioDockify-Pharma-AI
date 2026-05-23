"""Statistics Charts API — generates publication-quality charts (histogram, boxplot, scatter, ROC, etc.)."""
from helpers.api import ApiHandler, Request, Response
import os, io, base64, logging
import numpy as np

log = logging.getLogger("statistics_charts")

# Auto-detect matplotlib backend
try:
    import matplotlib
    matplotlib.use("Agg")  # Headless
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    import seaborn as sns
    HAS_SNS = True
except ImportError:
    HAS_SNS = False


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="#1a1a2e", edgecolor="none")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def _style_dark():
    if not HAS_MPL:
        return
    plt.style.use("dark_background")
    for param in ["text.color", "axes.labelcolor", "xtick.color", "ytick.color"]:
        plt.rcParams[param] = "#c0c0c0"
    plt.rcParams["axes.edgecolor"] = "#444"
    plt.rcParams["axes.facecolor"] = "#1a1a2e"
    plt.rcParams["figure.facecolor"] = "#1a1a2e"
    plt.rcParams["grid.color"] = "#333"
    plt.rcParams["grid.alpha"] = 0.4


def _safe_float_list(data):
    try:
        return [float(x) for x in data if x is not None]
    except (ValueError, TypeError):
        return []


def generate_histogram(values, title="Histogram", bins="auto"):
    if not HAS_MPL:
        return None
    _style_dark()
    vals = _safe_float_list(values)
    if len(vals) < 2:
        return None
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(vals, bins=bins, color="#00d4aa", edgecolor="#0a1929", alpha=0.85)
    ax.set_title(title, fontsize=12, fontweight="bold", color="#00d4aa")
    ax.set_xlabel("Value")
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.3)
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def generate_boxplot(groups: dict, title="Boxplot"):
    if not HAS_MPL:
        return None
    _style_dark()
    data = [v for v in groups.values() if len(v) > 1]
    if len(data) < 1:
        return None
    labels = [k for k, v in groups.items() if len(v) > 1]
    fig, ax = plt.subplots(figsize=(8, 4))
    bp = ax.boxplot(data, labels=labels, patch_artist=True,
                    medianprops={"color": "white", "linewidth": 1.5})
    for patch in bp["boxes"]:
        patch.set_facecolor("#00d4aa")
        patch.set_alpha(0.7)
    ax.set_title(title, fontsize=12, fontweight="bold", color="#00d4aa")
    ax.grid(axis="y", alpha=0.3)
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def generate_scatter(x_vals, y_vals, title="Scatter Plot", x_label="X", y_label="Y"):
    if not HAS_MPL:
        return None
    _style_dark()
    x = _safe_float_list(x_vals)
    y = _safe_float_list(y_vals)
    n = min(len(x), len(y))
    if n < 2:
        return None
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(x[:n], y[:n], c="#00d4aa", alpha=0.7, s=30, edgecolors="#0a1929")
    if n > 3:
        z = np.polyfit(x[:n], y[:n], 1)
        p = np.poly1d(z)
        ax.plot(sorted(x[:n]), p(sorted(x[:n])), "#ff6b6b", linewidth=1, linestyle="--", label="Trend")
        ax.legend()
    ax.set_title(title, fontsize=12, fontweight="bold", color="#00d4aa")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(alpha=0.3)
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def generate_qq_plot(values, title="Q-Q Plot"):
    if not HAS_MPL:
        return None
    _style_dark()
    vals = _safe_float_list(values)
    if len(vals) < 5:
        return None
    import scipy.stats as st
    fig, ax = plt.subplots(figsize=(6, 5))
    st.probplot(vals, dist="norm", plot=ax)
    ax.get_lines()[0].set_markerfacecolor("#00d4aa")
    ax.get_lines()[0].set_markeredgecolor("#0a1929")
    ax.get_lines()[1].set_color("#ff6b6b")
    ax.set_title(title, fontsize=12, fontweight="bold", color="#00d4aa")
    ax.grid(alpha=0.3)
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def generate_bar_chart(labels, values, title="Bar Chart", x_label="Category", y_label="Count"):
    if not HAS_MPL:
        return None
    _style_dark()
    n = min(len(labels), len(values))
    if n < 1:
        return None
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#00d4aa", "#4fc3f7", "#ffd93d", "#ff6b6b", "#9932cc", "#ff8c00"] * (n // 6 + 1)
    ax.bar(labels[:n], values[:n], color=colors[:n], edgecolor="#0a1929", alpha=0.85)
    ax.set_title(title, fontsize=12, fontweight="bold", color="#00d4aa")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(axis="y", alpha=0.3)
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def generate_roc_curve(fpr, tpr, auc_score=None, title="ROC Curve"):
    if not HAS_MPL:
        return None
    _style_dark()
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color="#00d4aa", linewidth=2, label=f"AUC = {auc_score:.3f}" if auc_score else "ROC")
    ax.plot([0, 1], [0, 1], color="#ff6b6b", linewidth=1, linestyle="--", label="Random")
    ax.set_xlim([0, 1]); ax.set_ylim([0, 1])
    ax.set_title(title, fontsize=12, fontweight="bold", color="#00d4aa")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def generate_survival_curve(times, survival, title="Survival Curve"):
    if not HAS_MPL:
        return None
    _style_dark()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.step(times, survival, where="post", color="#00d4aa", linewidth=2)
    ax.fill_between(times, 0, survival, step="post", color="#00d4aa", alpha=0.15)
    ax.set_ylim([0, 1.05])
    ax.set_title(title, fontsize=12, fontweight="bold", color="#00d4aa")
    ax.set_xlabel("Time")
    ax.set_ylabel("Survival Probability")
    ax.grid(alpha=0.3)
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def generate_correlation_heatmap(matrix, labels, title="Correlation Matrix"):
    if not HAS_MPL:
        return None
    _style_dark()
    n = min(len(matrix), len(labels))
    fig, ax = plt.subplots(figsize=(max(5, n * 1.2), max(4, n * 1)))
    im = ax.imshow(matrix[:n, :n], cmap="RdYlGn", aspect="auto", vmin=-1, vmax=1)
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels(labels[:n], fontsize=7, rotation=45, ha="right")
    ax.set_yticklabels(labels[:n], fontsize=7)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{matrix[i][j]:.2f}", ha="center", va="center", fontsize=6,
                    color="white" if abs(matrix[i][j]) > 0.5 else "#0a1929")
    ax.set_title(title, fontsize=12, fontweight="bold", color="#00d4aa")
    plt.colorbar(im, ax=ax, shrink=0.8)
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


class StatisticsCharts(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        if not HAS_MPL:
            return {"success": False, "error": "matplotlib not available. Install: pip install matplotlib seaborn scipy"}

        chart_type = input.get("chart_type", "histogram")

        if chart_type == "histogram":
            b64 = generate_histogram(
                input.get("values", []),
                input.get("title", "Histogram"),
            )
            return {"success": True, "chart": b64, "format": "png", "encoding": "base64"} if b64 else {"success": False, "error": "Insufficient data"}

        if chart_type == "boxplot":
            b64 = generate_boxplot(
                input.get("groups", {}),
                input.get("title", "Boxplot"),
            )
            return {"success": True, "chart": b64, "format": "png", "encoding": "base64"} if b64 else {"success": False, "error": "Insufficient data"}

        if chart_type == "scatter":
            b64 = generate_scatter(
                input.get("x", []), input.get("y", []),
                input.get("title", "Scatter Plot"),
                input.get("x_label", "X"), input.get("y_label", "Y"),
            )
            return {"success": True, "chart": b64, "format": "png", "encoding": "base64"} if b64 else {"success": False, "error": "Insufficient data"}

        if chart_type == "qq":
            b64 = generate_qq_plot(input.get("values", []), input.get("title", "Q-Q Plot"))
            return {"success": True, "chart": b64, "format": "png", "encoding": "base64"} if b64 else {"success": False, "error": "Insufficient data"}

        if chart_type == "bar":
            b64 = generate_bar_chart(
                input.get("labels", []), input.get("values", []),
                input.get("title", "Bar Chart"),
            )
            return {"success": True, "chart": b64, "format": "png", "encoding": "base64"} if b64 else {"success": False, "error": "Insufficient data"}

        if chart_type == "roc":
            b64 = generate_roc_curve(
                input.get("fpr", []), input.get("tpr", []),
                input.get("auc"),
                input.get("title", "ROC Curve"),
            )
            return {"success": True, "chart": b64, "format": "png", "encoding": "base64"} if b64 else {"success": False, "error": "Insufficient data"}

        if chart_type == "survival":
            b64 = generate_survival_curve(
                input.get("times", []), input.get("survival", []),
                input.get("title", "Survival Curve"),
            )
            return {"success": True, "chart": b64, "format": "png", "encoding": "base64"} if b64 else {"success": False, "error": "Insufficient data"}

        if chart_type == "correlation_heatmap":
            b64 = generate_correlation_heatmap(
                input.get("matrix", []), input.get("labels", []),
                input.get("title", "Correlation Matrix"),
            )
            return {"success": True, "chart": b64, "format": "png", "encoding": "base64"} if b64 else {"success": False, "error": "Insufficient data"}

        return {"success": False, "error": f"Unknown chart_type: {chart_type}. Available: histogram, boxplot, scatter, qq, bar, roc, survival, correlation_heatmap"}
