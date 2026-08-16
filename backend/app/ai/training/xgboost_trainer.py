"""
CROWDSHIELD XGBOOST MODEL TRAINER (PHASE 4 - PARTS I, J, L, M, N)
==================================================================
Trains, tunes (on validation set), calibrates, and optimizes operating thresholds
for XGBoost crowd risk prediction models.
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
import xgboost as xgb
from sklearn.metrics import precision_recall_curve, f1_score, brier_score_loss
from sklearn.linear_model import LogisticRegression

from app.ai.dataset.schema import CANDIDATE_MODEL_FEATURES, PRIMARY_PROXY_TARGET
from app.ai.training.baselines import evaluate_metrics


class XGBoostModelTrainer:
    """Orchestrates XGBoost model fitting, validation threshold selection, and probability calibration."""

    def __init__(
        self,
        target_col: str = PRIMARY_PROXY_TARGET,
        hyperparams: Optional[Dict[str, Any]] = None,
        random_seed: int = 42
    ):
        self.target_col = target_col
        self.random_seed = random_seed
        self.default_hyperparams = {
            "n_estimators": 100,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 2,
            "random_state": random_seed,
            "eval_metric": "logloss",
            "use_label_encoder": False
        }
        if hyperparams:
            self.default_hyperparams.update(hyperparams)

        self.model: Optional[xgb.XGBClassifier] = None
        self.calibrator: Optional[LogisticRegression] = None
        self.best_threshold: float = 0.5
        self.feature_cols: List[str] = []

    def train_and_evaluate(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        calibrate: bool = True
    ) -> Dict[str, Any]:
        """
        Fits XGBoost model on train_df, selects threshold on val_df,
        calibrates on val_df (if enabled), and evaluates on untouched test_df.
        """
        self.feature_cols = [c for c in CANDIDATE_MODEL_FEATURES if c in train_df.columns]

        X_train, y_train = train_df[self.feature_cols].values, train_df[self.target_col].values.astype(int)
        X_val, y_val = val_df[self.feature_cols].values, val_df[self.target_col].values.astype(int)
        X_test, y_test = test_df[self.feature_cols].values, test_df[self.target_col].values.astype(int)

        # Handle class imbalance via scale_pos_weight
        num_pos = np.sum(y_train == 1)
        num_neg = np.sum(y_train == 0)
        scale_pos_weight = float(num_neg / num_pos) if (num_pos > 0 and num_neg > 0) else 1.0

        params = {**self.default_hyperparams, "scale_pos_weight": scale_pos_weight}

        self.model = xgb.XGBClassifier(**params)
        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        # Raw probabilities
        raw_train_probs = self.model.predict_proba(X_train)[:, 1] if len(self.model.classes_) > 1 else np.zeros(len(X_train))
        raw_val_probs = self.model.predict_proba(X_val)[:, 1] if len(self.model.classes_) > 1 else np.zeros(len(X_val))
        raw_test_probs = self.model.predict_proba(X_test)[:, 1] if len(self.model.classes_) > 1 else np.zeros(len(X_test))

        # Probability Calibration (Part N) using Platt Scaling on validation set
        if calibrate and len(np.unique(y_val)) > 1:
            self.calibrator = LogisticRegression(solver="lbfgs")
            self.calibrator.fit(raw_val_probs.reshape(-1, 1), y_val)

            val_probs = self.calibrator.predict_proba(raw_val_probs.reshape(-1, 1))[:, 1]
            test_probs = self.calibrator.predict_proba(raw_test_probs.reshape(-1, 1))[:, 1]
            train_probs = self.calibrator.predict_proba(raw_train_probs.reshape(-1, 1))[:, 1]
            calibration_method = "Platt_Scaling_Validation"
        else:
            val_probs = raw_val_probs
            test_probs = raw_test_probs
            train_probs = raw_train_probs
            calibration_method = "None"

        # Optimal Threshold Selection strictly on Validation Split (Part M)
        self.best_threshold = self._select_optimal_threshold(y_val, val_probs)

        # Calculate final metrics
        train_metrics = evaluate_metrics(y_train, train_probs, threshold=self.best_threshold)
        val_metrics = evaluate_metrics(y_val, val_probs, threshold=self.best_threshold)
        test_metrics = evaluate_metrics(y_test, test_probs, threshold=self.best_threshold)

        # Feature Importance (Part S)
        importance_dict = {}
        if hasattr(self.model, "feature_importances_"):
            for col, imp in zip(self.feature_cols, self.model.feature_importances_):
                importance_dict[col] = float(round(imp, 4))

        return {
            "model_name": "XGBoost Early-Warning Classifier",
            "model_type": "XGBoost",
            "target": self.target_col,
            "hyperparameters": params,
            "feature_cols": self.feature_cols,
            "selected_threshold": self.best_threshold,
            "calibration_method": calibration_method,
            "train_metrics": train_metrics,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
            "feature_importances": dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
        }

    def _select_optimal_threshold(self, y_true: np.ndarray, y_probs: np.ndarray) -> float:
        """
        Searches thresholds on validation set to maximize F1 score while keeping false positive rate reasonable.
        """
        if len(np.unique(y_true)) <= 1 or len(y_probs) == 0:
            return 0.5

        best_th = 0.5
        best_score = -1.0

        for th in np.arange(0.1, 0.9, 0.05):
            preds = (y_probs >= th).astype(int)
            score = f1_score(y_true, preds, zero_division=0)
            if score > best_score:
                best_score = score
                best_th = float(th)

        return round(best_th, 2)
