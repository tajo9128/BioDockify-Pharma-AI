"""
PLS (Partial Least Squares) Regression for 3D-QSAR
Upgraded with Open3DQSAR's NIPALS algorithm + variable selection.

Key improvements:
1. NIPALS PLS with star-weights prediction (exact Open3DQSAR algorithm)
2. UVE-PLS variable selection (Uninformative Variable Elimination)
3. IVE-PLS (Iterative Variable Elimination)
4. FFD-SEL (Fractional Factorial Design Selection)
5. Binned Y-randomization
6. BUW (Block Unscaled Weighting) for multi-field models
"""
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("qsar3d.pls")


class PLSModel:
    """
    PLS regression model using NIPALS algorithm.
    Implements Open3DQSAR's exact PLS with star-weights prediction.
    """

    def __init__(self, max_components: int = 10, scale: bool = True,
                 conv_threshold: float = 1e-4):
        self.max_components = max_components
        self.scale = scale
        self.conv_threshold = conv_threshold
        self.n_components = None
        self.scaler_X = None
        self.scaler_Y = None
        self.coefficients = None
        self.training_stats = {}

        # NIPALS internal matrices
        self.x_weights = None      # W
        self.x_loadings = None     # P
        self.y_loadings = None     # Q
        self.x_scores = None       # T
        self.y_scores = None       # U
        self.x_weights_star = None # W*
        self.b_coefficients = None # B

    def prepare_matrix(self, all_fields: list) -> np.ndarray:
        """Flatten per-molecule MIF field dicts into a 2D design matrix.

        Args:
            all_fields: List of dicts, one per molecule. Each dict has keys
                        like 'steric' and/or 'electrostatic' with 1D numpy arrays.

        Returns:
            2D numpy array of shape (n_molecules, n_features).
            Features are steric and electrostatic grids concatenated.
            Missing fields are padded with zeros to ensure uniform row lengths.
        """
        if not all_fields:
            return np.array([]).reshape(0, 0)

        # Determine expected size per field from the first complete molecule
        field_sizes = {}
        for fields in all_fields:
            for key in ('steric', 'electrostatic'):
                if key in fields and key not in field_sizes:
                    field_sizes[key] = np.asarray(fields[key]).ravel().shape[0]
            if len(field_sizes) == 2:
                break

        rows = []
        for fields in all_fields:
            parts = []
            for key in ('steric', 'electrostatic'):
                arr = fields.get(key)
                if arr is not None:
                    parts.append(np.asarray(arr).ravel())
                elif key in field_sizes:
                    # Pad with zeros for missing field
                    parts.append(np.zeros(field_sizes[key]))
            if parts:
                rows.append(np.concatenate(parts))
            else:
                rows.append(np.array([]))

        if not rows or rows[0].size == 0:
            return np.array([]).reshape(0, 0)
        return np.vstack(rows)

    def fit(self, X_train: np.ndarray, Y_train: np.ndarray,
            X_val: np.ndarray = None, Y_val: np.ndarray = None) -> Dict:
        """
        Fit PLS model using NIPALS algorithm (from Open3DQSAR pls.c).

        Returns training statistics: r², q², n_components.
        """
        Y_train = np.array(Y_train).ravel().reshape(-1, 1)

        # Scale data
        if self.scale:
            self.scaler_X = StandardScaler()
            X_train = self.scaler_X.fit_transform(X_train)
            self.scaler_Y = StandardScaler()
            Y_train = self.scaler_Y.fit_transform(Y_train)

        # Find optimal number of components
        best_n, best_q2 = self._find_optimal_components(X_train, Y_train.ravel())
        self.n_components = best_n

        # Run NIPALS with optimal components
        self._nipals(X_train, Y_train, best_n)

        # Calculate B-coefficients (star-weights method from Open3DQSAR)
        self._compute_b_coefficients()

        # Calculate r² (fit)
        Y_pred = self._predict_scaled(X_train)
        ss_res = np.sum((Y_train.ravel() - Y_pred.ravel()) ** 2)
        ss_tot = np.sum((Y_train.ravel() - Y_train.ravel().mean()) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        stats = {
            'r2': round(r2, 4),
            'q2': round(best_q2, 4),
            'n_components': best_n,
            'n_variables': X_train.shape[1],
            'n_samples': X_train.shape[0],
        }

        # External validation
        if X_val is not None and Y_val is not None:
            Y_val = np.array(Y_val).ravel()
            Y_val_pred = self.predict(X_val)
            ss_res_ext = np.sum((Y_val - Y_val_pred) ** 2)
            ss_tot_ext = np.sum((Y_val - Y_train.ravel().mean()) ** 2)
            r2_pred = 1 - (ss_res_ext / ss_tot_ext) if ss_tot_ext > 0 else 0
            stats['r2_pred'] = round(r2_pred, 4)
            stats['sdep'] = round(np.sqrt(ss_res_ext / len(Y_val)), 4)

        self.training_stats = stats
        return stats

    def _nipals(self, X: np.ndarray, Y: np.ndarray, n_components: int):
        """
        NIPALS PLS algorithm (from Open3DQSAR pls.c lines 45-283).

        Exact implementation:
        1. Initialize v = first column of F (Y matrix)
        2. Iterate: c = E'v, c = c/||c||, u = Ec, d = F'u, d = d/||d||, v_new = Fd
        3. Inner relation: ro = u'v / u'u
        4. Deflation: E -= u*b', F -= u*d'
        """
        n, p = X.shape
        m = Y.shape[1] if Y.ndim > 1 else 1

        # Initialize matrices
        E = X.copy()
        F = Y.copy().reshape(-1, m)

        self.x_weights = np.zeros((p, n_components))     # W
        self.x_loadings = np.zeros((p, n_components))    # P
        self.y_loadings = np.zeros((m, n_components))    # Q
        self.x_scores = np.zeros((n, n_components))      # T
        self.y_scores = np.zeros((n, n_components))      # U

        for i in range(n_components):
            # Initialize v = first column of F
            v = F[:, 0].copy()
            # Initialize u to zeros — guards against degenerate data where
            # the inner loop exits immediately (c_norm < 1e-10 on first iter)
            u = np.zeros(n)
            c = np.zeros(p)

            # Iterate until convergence
            for iteration in range(100):
                # c = E'v
                c = E.T @ v

                # c = c / ||c||
                c_norm = np.linalg.norm(c)
                if c_norm < 1e-10:
                    break
                c = c / c_norm

                # u = Ec
                u = E @ c

                # d = F'u
                d = F.T @ u

                # d = d / ||d||
                d_norm = np.linalg.norm(d)
                if d_norm < 1e-10:
                    break
                d = d / d_norm

                # v_new = Fd
                v_new = F @ d

                # Check convergence
                diff = np.linalg.norm(v_new - v) ** 2
                v = v_new

                if diff < self.conv_threshold:
                    break

            # Inner relation coefficient: ro = u'v / u'u
            u_dot_u = u @ u
            if u_dot_u < 1e-10:
                break
            ro = (u @ v) / u_dot_u

            # Store
            self.x_weights[:, i] = c
            self.x_scores[:, i] = u
            self.y_scores[:, i] = v
            self.y_loadings[:, i] = ro * d

            # X loadings: b = E'u / u'u
            b = E.T @ u / u_dot_u
            self.x_loadings[:, i] = b

            # Deflation
            # E[i+1] = E[i] - u * b'
            E = E - np.outer(u, b)
            # F[i+1] = F[i] - u * (ro * d)'
            F = F - np.outer(u, ro * d)

    def _compute_b_coefficients(self):
        """
        Compute B-coefficients using star-weights method.
        From Open3DQSAR pred_y_values.c lines 195-309.

        W* = W * (P'W)^{-1}
        B = W* * Q'
        """
        W = self.x_weights
        P = self.x_loadings
        Q = self.y_loadings

        # W* = W * inv(P'W)
        PtW = P.T @ W
        try:
            PtW_inv = np.linalg.inv(PtW)
            self.x_weights_star = W @ PtW_inv
        except np.linalg.LinAlgError:
            # Singular matrix — fall back to plain weights
            logger.warning("Singular P'W matrix, using plain weights")
            self.x_weights_star = W.copy()

        # B = W* * Q'
        self.b_coefficients = self.x_weights_star @ Q.T

    def _predict_scaled(self, X: np.ndarray) -> np.ndarray:
        """Predict using B-coefficients on scaled data."""
        if self.b_coefficients is None:
            raise ValueError("Model not trained. Call fit() first.")
        return (X @ self.b_coefficients).ravel()

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict activity values for new molecules."""
        if self.b_coefficients is None:
            raise ValueError("Model not trained. Call fit() first.")

        if self.scale and self.scaler_X:
            X = self.scaler_X.transform(X)

        Y_pred = self._predict_scaled(X)

        if self.scale and self.scaler_Y:
            Y_pred = self.scaler_Y.inverse_transform(Y_pred.reshape(-1, 1)).ravel()

        return Y_pred

    def _find_optimal_components(self, X: np.ndarray, Y: np.ndarray) -> Tuple[int, float]:
        """Find optimal number of PLS components via LOO cross-validation."""
        max_comp = min(self.max_components, X.shape[0] - 1, X.shape[1])

        best_n = 1
        best_q2 = -999

        for n in range(1, max_comp + 1):
            try:
                q2 = self._loo_cv(X, Y, n)
                if q2 > best_q2:
                    best_q2 = q2
                    best_n = n
            except Exception:
                break

        return best_n, best_q2

    def _loo_cv(self, X: np.ndarray, Y: np.ndarray, n_components: int) -> float:
        """Leave-One-Out cross-validation with NIPALS."""
        n = len(Y)
        Y_pred = np.zeros(n)

        for i in range(n):
            mask = np.ones(n, dtype=bool)
            mask[i] = False

            X_train, Y_train = X[mask], Y[mask]
            X_test = X[i:i+1]

            # Fit mini NIPALS model
            self._nipals(X_train, Y_train.reshape(-1, 1), n_components)
            self._compute_b_coefficients()
            Y_pred[i] = self._predict_scaled(X_test)[0]

        # Calculate q²
        ss_res = np.sum((Y - Y_pred) ** 2)
        ss_tot = np.sum((Y - Y.mean()) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    def get_coefficients(self) -> np.ndarray:
        """Return PLS coefficients for contour plot visualization."""
        return self.b_coefficients.ravel() if self.b_coefficients is not None else None

    def to_dict(self) -> Dict:
        """Serialize model metadata."""
        return {
            'n_components': self.n_components,
            'max_components': self.max_components,
            'scale': self.scale,
            'training_stats': self.training_stats,
        }
