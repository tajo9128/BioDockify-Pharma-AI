"""
3D-QSAR Model Builder
The main orchestrator combining MIF + PLS + Validation.

Merges Open3DQSAR's workflow with Py-CoMFA's Python implementation:
1. Parse dataset (SMILES/SDF + activity)
2. Generate 3D coordinates + alignment
3. Calculate MIF (steric + electrostatic)
4. Build PLS model with optimal components
5. Validate (LOO, L5O, Y-scrambling)
6. Store model for prediction
"""
import os
import pickle
import uuid
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("qsar3d.builder")


class QSAR3DBuilder:
    """
    Build a 3D-QSAR model from a molecular dataset.

    Full pipeline: dataset → 3D → align → MIF → PLS → validate → model
    """

    def __init__(self, grid_spacing: float = 2.0, grid_margin: float = 5.0,
                 max_components: int = 8, field_types: List[str] = None,
                 mode: str = '3d'):
        from .mif import MIFCalculator
        from .pls import PLSModel
        from .validation import ModelValidator
        from .alignment import MolecularAligner

        self.mode = mode  # '3d' or '2d'
        self.mif_calc = MIFCalculator(
            grid_spacing=grid_spacing,
            margin=grid_margin,
            field_types=field_types or ['steric', 'electrostatic'],
        )
        self.pls_model = PLSModel(max_components=max_components)
        self.validator = ModelValidator()
        self.aligner = MolecularAligner()
        self.standardizer = None
        self.descriptor_calc = None

        # Initialize 2D-QSAR components (OPERA-style)
        if mode == '2d':
            from .standardize import StructureStandardizer
            from .descriptors import DescriptorCalculator
            self.standardizer = StructureStandardizer()
            self.descriptor_calc = DescriptorCalculator()

        self.model_id = str(uuid.uuid4())[:8]
        self.field_types = field_types or ['steric', 'electrostatic']
        self.grid_info = None

    def build_2d_from_smiles(self, smiles_list: List[str],
                              activity_list: List[float],
                              test_fraction: float = 0.2) -> Dict:
        """
        Build a 2D-QSAR model using molecular descriptors (OPERA-style).
        No 3D alignment needed — works with SMILES directly.

        Pipeline: standardize → descriptors → PLS → validate
        """
        logger.info(f"[QSAR-2D] Building model from {len(smiles_list)} molecules...")

        # Step 1: Standardize molecules
        logger.info("[QSAR-2D] Step 1: Standardizing structures...")
        valid_mols, valid_idx = self.standardizer.prepare_dataset(smiles_list)
        activities = np.array([activity_list[i] for i in valid_idx])

        if len(valid_mols) < 8:
            raise ValueError(f"Need at least 8 valid molecules after standardization, got {len(valid_mols)}")

        # Step 2: Calculate descriptors
        logger.info("[QSAR-2D] Step 2: Calculating molecular descriptors...")
        X, desc_names = self.descriptor_calc.calculate_batch(valid_mols)
        Y = activities

        logger.info(f"[QSAR-2D] Descriptor matrix: {X.shape[0]} molecules × {X.shape[1]} descriptors")

        # Step 3: Split train/test
        n = len(Y)
        n_test = max(2, int(n * test_fraction))
        n_train = n - n_test
        indices = np.random.permutation(n)
        train_idx = indices[:n_train]
        test_idx = indices[n_train:]

        X_train, Y_train = X[train_idx], Y[train_idx]
        X_test, Y_test = X[test_idx], Y[test_idx]
        train_smiles = [smiles_list[valid_idx[i]] for i in train_idx]
        test_smiles = [smiles_list[valid_idx[i]] for i in test_idx]

        # Step 4: Train PLS model
        logger.info("[QSAR-2D] Step 3: Training PLS model...")
        stats = self.pls_model.fit(X_train, Y_train, X_test, Y_test)

        # Step 5: Validation
        logger.info("[QSAR-2D] Step 4: Cross-validation...")
        l5o = self.validator.l5o_cross_validation(X_train, Y_train,
            n_folds=min(5, n_train // 2), n_iterations=20)
        stats['l5o'] = l5o

        logger.info("[QSAR-2D] Step 5: Y-scrambling...")
        y_scram = self.validator.y_scrambling(X_train, Y_train,
            n_permutations=50, n_components=self.pls_model.n_components)
        stats['y_scrambling'] = y_scram

        # Applicability domain with confidence (OPERA-style)
        logger.info("[QSAR-2D] Step 6: Applicability domain...")
        domain = self.validator.applicability_domain_with_confidence(
            X_train, X_test, train_smiles, test_smiles)
        stats['applicability_domain'] = domain

        # Predictions for plotting
        Y_train_pred = self.pls_model.predict(X_train)
        Y_test_pred = self.pls_model.predict(X_test)
        stats['train_predictions'] = {'actual': Y_train.tolist(), 'predicted': Y_train_pred.tolist()}
        stats['test_predictions'] = {'actual': Y_test.tolist(), 'predicted': Y_test_pred.tolist()}

        # Descriptor importance (PLS coefficients)
        coef = np.abs(self.pls_model.coefficients)
        top_indices = np.argsort(coef)[-10:][::-1]  # Top 10 descriptors
        stats['top_descriptors'] = [
            {'name': desc_names[i], 'importance': round(float(coef[i]), 4)}
            for i in top_indices
        ]

        stats['model_id'] = self.model_id
        stats['mode'] = '2d'
        stats['n_descriptors'] = X.shape[1]
        stats['descriptor_names'] = desc_names
        stats['n_molecules'] = n
        stats['n_rejected'] = len(smiles_list) - len(valid_mols)

        logger.info(f"[QSAR-2D] Model {self.model_id}: r²={stats['r2']}, q²={stats['q2']}, "
                    f"{X.shape[1]} descriptors")

        return stats

    def build_from_smiles(self, smiles_list: List[str],
                          activity_list: List[float],
                          test_fraction: float = 0.2,
                          reference_smiles: str = None) -> Dict:
        """
        Build 3D-QSAR model from SMILES + activity data.

        Args:
            smiles_list: List of SMILES strings
            activity_list: Corresponding activity values (IC50, Ki, etc.)
            test_fraction: Fraction of data for external test set
            reference_smiles: Optional reference for alignment

        Returns: Model statistics (r², q², r²_pred, etc.)
        """
        # Step 1: Prepare dataset (3D generation + alignment)
        logger.info(f"[QSAR3D] Step 1: Preparing {len(smiles_list)} molecules...")
        mols, activities = self.aligner.prepare_dataset(
            smiles_list, activity_list, reference_smiles
        )

        if len(mols) < 10:
            raise ValueError(f"Need at least 10 molecules, got {len(mols)} after parsing")

        activities = np.array(activities)

        # Step 2: Determine grid encompassing all molecules
        logger.info("[QSAR3D] Step 2: Setting up MIF grid...")
        self.mif_calc.set_grid_from_molecules(mols)
        self.grid_info = self.mif_calc.get_grid_info()

        # Step 3: Calculate MIF for each molecule
        logger.info(f"[QSAR3D] Step 3: Calculating MIF ({self.grid_info['total_points']} grid points)...")
        all_fields = []
        for i, mol in enumerate(mols):
            fields = self.mif_calc.calculate(mol)
            all_fields.append(fields)

        # Step 4: Build design matrix
        logger.info("[QSAR3D] Step 4: Building design matrix...")
        X = self.pls_model.prepare_matrix(all_fields)
        Y = activities

        # Step 5: Split train/test
        n = len(Y)
        n_test = max(2, int(n * test_fraction))
        n_train = n - n_test

        indices = np.random.permutation(n)
        train_idx = indices[:n_train]
        test_idx = indices[n_train:]

        X_train, Y_train = X[train_idx], Y[train_idx]
        X_test, Y_test = X[test_idx], Y[test_idx]

        logger.info(f"[QSAR3D] Split: {n_train} train, {n_test} test")

        # Step 5: Train PLS model
        logger.info("[QSAR3D] Step 5: Training PLS model...")
        stats = self.pls_model.fit(X_train, Y_train, X_test, Y_test)

        # Step 6: Validation
        logger.info("[QSAR3D] Step 6: Cross-validation (L5O, 100 iterations)...")
        l5o = self.validator.l5o_cross_validation(
            X_train, Y_train,
            n_folds=min(5, n_train // 2),
            n_iterations=20,  # Reduced for speed
        )
        stats['l5o'] = l5o

        logger.info("[QSAR3D] Step 7: Y-scrambling (100 permutations)...")
        y_scram = self.validator.y_scrambling(
            X_train, Y_train,
            n_permutations=50,  # Reduced for speed
            n_components=self.pls_model.n_components,
        )
        stats['y_scrambling'] = y_scram

        # Applicability domain
        logger.info("[QSAR3D] Step 8: Applicability domain...")
        domain = self.validator.applicability_domain(X_train, X_test)
        stats['applicability_domain'] = domain

        # Predictions for plotting
        Y_train_pred = self.pls_model.predict(X_train)
        Y_test_pred = self.pls_model.predict(X_test)
        stats['train_predictions'] = {
            'actual': Y_train.tolist(),
            'predicted': Y_train_pred.tolist(),
        }
        stats['test_predictions'] = {
            'actual': Y_test.tolist(),
            'predicted': Y_test_pred.tolist(),
        }

        stats['model_id'] = self.model_id
        stats['field_types'] = self.field_types
        stats['grid_info'] = self.grid_info
        stats['n_molecules'] = n

        logger.info(f"[QSAR3D] Model {self.model_id} built: r²={stats['r2']}, q²={stats['q2']}, "
                    f"r²_pred={stats.get('r2_pred', 'N/A')}")

        return stats

    def predict(self, smiles_list: List[str]) -> Dict:
        """Predict activity for new molecules using trained model."""
        from rdkit import Chem

        mols = []
        for smi in smiles_list:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                continue
            mol = self.aligner.generate_3d(mol)
            mols.append(mol)

        if not mols:
            return {"error": "No valid molecules"}

        # Calculate MIF for each
        all_fields = []
        for mol in mols:
            fields = self.mif_calc.calculate(mol)
            all_fields.append(fields)

        # Build matrix and predict
        X = self.pls_model.prepare_matrix(all_fields)
        predictions = self.pls_model.predict(X)

        return {
            "predictions": predictions.tolist(),
            "smiles": smiles_list[:len(predictions)],
        }

    def save_model(self, path: str) -> str:
        """Save trained model to pickle file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        model_data = {
            'pls_model': self.pls_model,
            'grid_info': self.grid_info,
            'field_types': self.field_types,
            'model_id': self.model_id,
            'mif_grid_spacing': self.mif_calc.grid_spacing,
            'mif_margin': self.mif_calc.margin,
            'mif_grid_origin': self.mif_calc.grid_origin,
            'mif_grid_dims': self.mif_calc.grid_dims,
        }

        filepath = os.path.join(path, f"qsar3d_{self.model_id}.pkl")
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"[QSAR3D] Model saved to {filepath}")
        return filepath

    @staticmethod
    def load_model(filepath: str) -> 'QSAR3DBuilder':
        """Load a saved model."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        builder = QSAR3DBuilder()
        builder.pls_model = data['pls_model']
        builder.grid_info = data['grid_info']
        builder.field_types = data['field_types']
        builder.model_id = data['model_id']
        builder.mif_calc.grid_spacing = data['mif_grid_spacing']
        builder.mif_calc.margin = data['mif_margin']
        builder.mif_calc.grid_origin = data['mif_grid_origin']
        builder.mif_calc.grid_dims = data['mif_grid_dims']

        return builder
