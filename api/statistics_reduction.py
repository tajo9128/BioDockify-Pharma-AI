"""Data Reduction API — PCA, Factor Analysis, Reliability, Clustering."""
from helpers.api import ApiHandler, Request, Response
import logging, io, base64, numpy as np

log = logging.getLogger("statistics_reduction")

try:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
    from scipy.spatial.distance import pdist
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="#1a1a2e")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# ─── Factor Analysis (PCA) ───────────────────────────────
def _pca_analysis(data: list, columns: list, n_components: int = None):
    if not HAS_SKLEARN:
        return {"error": "scikit-learn not available"}
    try:
        X = np.array(data, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.shape[0] < 3 or X.shape[1] < 1:
            return {"error": "Need at least 3 rows and 1 column"}
        # Handle NaN
        X = X[~np.isnan(X).any(axis=1)]
        if len(X) < 3:
            return {"error": "Too many NaN values"}
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        max_pc = min(X.shape[0], X.shape[1])
        if n_components is None:
            n_components = max_pc
        else:
            n_components = min(n_components, max_pc)

        pca = PCA(n_components=n_components)
        pca.fit(X_scaled)

        # Eigenvalues / explained variance
        eigenvalues = pca.explained_variance_.tolist()
        ev_ratio = pca.explained_variance_ratio_.tolist()
        ev_cumulative = np.cumsum(ev_ratio).tolist()

        # Component loadings (eigenvectors scaled)
        loadings = []
        for i in range(n_components):
            comp = {}
            for j, col in enumerate(columns[:X.shape[1]]):
                comp[col] = round(float(pca.components_[i][j]), 4)
            loadings.append({"component": i + 1, "loadings": comp,
                             "eigenvalue": round(eigenvalues[i], 4),
                             "variance_pct": round(ev_ratio[i] * 100, 2)})

        # Scree plot
        scree_b64 = None
        if HAS_MPL:
            try:
                plt.style.use("dark_background")
                plt.rcParams["axes.facecolor"] = "#1a1a2e"
                plt.rcParams["figure.facecolor"] = "#1a1a2e"
                fig, ax = plt.subplots(figsize=(7, 4))
                ax.plot(range(1, len(eigenvalues) + 1), eigenvalues, "o-", color="#00d4aa", markersize=6)
                ax.axhline(y=1.0, color="#ff6b6b", linestyle="--", linewidth=1, label="Kaiser criterion (λ=1)")
                ax.set_title("Scree Plot", fontsize=12, fontweight="bold", color="#00d4aa")
                ax.set_xlabel("Principal Component"); ax.set_ylabel("Eigenvalue")
                ax.legend(); ax.grid(alpha=0.3)
                scree_b64 = _fig_to_base64(fig)
                plt.close(fig)
            except Exception as e:
                log.debug(f"Scree plot generation failed: {e}")

        return {
            "success": True,
            "method": "PCA",
            "n_components": n_components,
            "n_samples": int(X.shape[0]),
            "n_features": int(X.shape[1]),
            "eigenvalues": eigenvalues,
            "variance_explained": ev_ratio,
            "variance_cumulative": ev_cumulative,
            "loadings": loadings[:6],  # Top 6 components
            "scree_plot": scree_b64,
            "kaiser_components": sum(1 for e in eigenvalues if e >= 1.0),
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Reliability (Cronbach's alpha) ──────────────────────
def _cronbach_alpha(data: list, columns: list):
    """Calculate Cronbach's alpha for scale reliability."""
    try:
        X = np.array(data, dtype=float)
        if X.ndim == 1:
            return {"error": "Need multiple columns for reliability analysis"}
        if X.shape[1] < 2:
            return {"error": "Need at least 2 items (columns) for Cronbach's alpha"}
        if X.shape[0] < 3:
            return {"error": "Need at least 3 observations"}

        X = X[~np.isnan(X).any(axis=1)]
        if len(X) < 3:
            return {"error": "Too many NaN values"}

        k = X.shape[1]
        # Item variances
        item_variances = np.var(X, axis=0, ddof=1)
        # Total score variance
        total_variance = np.var(X.sum(axis=1), ddof=1)

        if total_variance == 0:
            return {"error": "Zero variance — all items identical"}

        alpha = (k / (k - 1)) * (1 - sum(item_variances) / total_variance)

        # Item-total statistics
        item_stats = []
        for i in range(k):
            col_name = columns[i] if i < len(columns) else f"Item_{i+1}"
            # Alpha if item deleted
            mask = np.ones(k, dtype=bool)
            mask[i] = False
            remaining = X[:, mask]
            var_remain = np.var(remaining, axis=0, ddof=1)
            total_remain = np.var(remaining.sum(axis=1), ddof=1)
            alpha_dropped = (k - 1) / (k - 2) * (1 - sum(var_remain) / total_remain) if k > 2 and total_remain > 0 else None

            # Corrected item-total correlation: exclude item from the rest-score
            # (including the item inflates the correlation artificially)
            rest_score = X.sum(axis=1) - X[:, i]
            item_total_corr = np.corrcoef(X[:, i], rest_score)[0, 1] if total_variance > 0 else 0

            item_stats.append({
                "item": col_name,
                "mean": round(float(np.mean(X[:, i])), 3),
                "std": round(float(np.std(X[:, i], ddof=1)), 3),
                "item_total_correlation": round(float(item_total_corr), 4),
                "alpha_if_deleted": round(float(alpha_dropped), 4) if alpha_dropped is not None else None,
            })

        # Interpretation
        if alpha >= 0.9: quality = "Excellent"
        elif alpha >= 0.8: quality = "Good"
        elif alpha >= 0.7: quality = "Acceptable"
        elif alpha >= 0.6: quality = "Questionable"
        elif alpha >= 0.5: quality = "Poor"
        else: quality = "Unacceptable"

        return {
            "success": True,
            "cronbach_alpha": round(float(alpha), 4),
            "n_items": k,
            "n_observations": int(len(X)),
            "quality": quality,
            "item_statistics": item_stats,
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Cluster Analysis (K-Means + Hierarchical) ───────────
def _kmeans_cluster(data: list, columns: list, n_clusters: int = 3):
    if not HAS_SKLEARN:
        return {"error": "scikit-learn not available"}
    try:
        X = np.array(data, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.shape[0] < n_clusters:
            return {"error": f"Need at least {n_clusters} observations"}
        X = X[~np.isnan(X).any(axis=1)]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)

        cluster_sizes = {}
        for i in range(n_clusters):
            cluster_sizes[f"Cluster_{i+1}"] = int(np.sum(labels == i))

        # Inertia (within-cluster sum of squares)
        inertia = float(km.inertia_)

        # Elbow scores for k=1 to min(10, n)
        elbow = []
        max_k = min(10, X.shape[0])
        for k in range(1, max_k + 1):
            km2 = KMeans(n_clusters=k, random_state=42, n_init=10)
            km2.fit(X_scaled)
            elbow.append({"k": k, "inertia": float(km2.inertia_)})

        return {
            "success": True,
            "method": "K-Means",
            "n_clusters": n_clusters,
            "cluster_sizes": cluster_sizes,
            "inertia": inertia,
            "labels": labels.tolist(),
            "elbow_curve": elbow,
        }
    except Exception as e:
        return {"error": str(e)}


def _hierarchical_cluster(data: list, columns: list, n_clusters: int = 3, method: str = "ward"):
    if not HAS_SCIPY:
        return {"error": "scipy not available"}
    try:
        X = np.array(data, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.shape[0] < 3:
            return {"error": "Need at least 3 observations"}
        X = X[~np.isnan(X).any(axis=1)]

        Z = linkage(X, method=method)
        labels = fcluster(Z, n_clusters, criterion="maxclust")

        cluster_sizes = {}
        for i in range(1, n_clusters + 1):
            cluster_sizes[f"Cluster_{i}"] = int(np.sum(labels == i))

        # Dendrogram
        dendro_b64 = None
        if HAS_MPL:
            try:
                plt.style.use("dark_background")
                plt.rcParams["axes.facecolor"] = "#1a1a2e"
                plt.rcParams["figure.facecolor"] = "#1a1a2e"
                fig, ax = plt.subplots(figsize=(8, 5))
                dendrogram(Z, labels=columns[:len(X)] if len(columns) >= len(X) else None,
                           leaf_font_size=8, color_threshold=1.15 * max(Z[:, 2]))
                ax.set_title("Hierarchical Clustering Dendrogram", fontsize=12, fontweight="bold", color="#00d4aa")
                ax.set_xlabel("Sample / Feature"); ax.set_ylabel("Distance")
                dendro_b64 = _fig_to_base64(fig)
                plt.close(fig)
            except Exception as e:
                log.debug(f"Dendrogram generation failed: {e}")

        return {
            "success": True,
            "method": f"Hierarchical ({method})",
            "n_clusters": n_clusters,
            "cluster_sizes": cluster_sizes,
            "labels": labels.tolist(),
            "dendrogram": dendro_b64,
        }
    except Exception as e:
        return {"error": str(e)}


class StatisticsReduction(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "factor")

        data = input.get("data", [])
        columns = input.get("columns", [])

        if action == "factor":
            return _pca_analysis(data, columns, input.get("n_components"))

        if action == "reliability":
            return _cronbach_alpha(data, columns)

        if action == "cluster_kmeans":
            return _kmeans_cluster(data, columns, int(input.get("n_clusters", 3)))

        if action == "cluster_hierarchical":
            return _hierarchical_cluster(data, columns, int(input.get("n_clusters", 3)),
                                         input.get("method", "ward"))

        return {"error": f"Unknown action: {action}. Available: factor, reliability, cluster_kmeans, cluster_hierarchical"}
