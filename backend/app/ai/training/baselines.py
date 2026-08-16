"""
CROWDSHIELD BASELINE MODELS (PHASE 4 - PARTS G, H)
===================================================
Provides deterministic physics rule-based baseline, Logistic Regression,
and Random Forest baseline implementations for Phase 4 model benchmarking.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    precision_recall_curve, auc, confusion_matrix, brier_score_loss
)

from app.ai.dataset.baseline_engine import baseline_risk
from app.ai.dataset.schema import CANDIDATE_MODEL_FEATURES


def evaluate_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
    """
    Computes standard evaluation metrics: Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, Confusion Matrix, Brier score.
    Handles single-class edge cases gracefully.
    """
    y_pred = (y_prob >= threshold).astype(int)

    acc = float((y_pred == y_true).mean()) if len(y_true) > 0 else 0.0
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # ROC-AUC (requires at least 2 classes in y_true)
    if len(np.unique(y_true)) > 1:
        roc_auc = float(roc_auc_score(y_true, y_prob))
        precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_prob)
        pr_auc = float(auc(recall_curve, precision_curve))
    else:
        roc_auc = float("nan")
        pr_auc = float("nan")

    # Confusion matrix & rates
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    brier = float(brier_score_loss(y_true, y_prob))

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4) if not np.isnan(roc_auc) else "UNDEFINED_SINGLE_CLASS",
        "pr_auc": round(pr_auc, 4) if not np.isnan(pr_auc) else "UNDEFINED_SINGLE_CLASS",
        "brier_score": round(brier, 4),
        "fpr": round(fpr, 4),
        "fnr": round(fnr, 4),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp)
        }
    }


def evaluate_rule_based_baseline(df: pd.DataFrame, target_col: str = "HIGH_RISK_WITHIN_5M") -> Dict[str, Any]:
    """
    Evaluates the deterministic physics momentum engine on dataframe rows.
    Assigns positive class 1 if baseline risk score >= 70.0 (HIGH/CRITICAL), else 0.
    """
    if df.empty or target_col not in df.columns:
        return {"error": "Invalid dataframe or target column."}

    scores = []
    for _, row in df.iterrows():
        feat_dict = {col: float(row[col]) for col in CANDIDATE_MODEL_FEATURES if col in df.columns}
        score_res = baseline_risk(feat_dict)
        if isinstance(score_res, dict):
            score_val = float(score_res.get("current_risk", 0.0))
        else:
            score_val = float(score_res)
        scores.append(score_val / 100.0)  # Normalize to [0, 1] probability range

    y_prob = np.array(scores)
    y_true = df[target_col].values.astype(int)

    metrics = evaluate_metrics(y_true, y_prob, threshold=0.70)
    metrics["model_name"] = "Rule-Based Physics Baseline"
    return metrics


def train_logistic_regression_baseline(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target_col: str = "HIGH_RISK_WITHIN_5M",
    random_seed: int = 42
) -> Tuple[LogisticRegression, Dict[str, Any]]:
    """
    Fits a Logistic Regression baseline model on CANDIDATE_MODEL_FEATURES.
    """
    feat_cols = [c for c in CANDIDATE_MODEL_FEATURES if c in train_df.columns]

    X_train, y_train = train_df[feat_cols].values, train_df[target_col].values
    X_val, y_val = val_df[feat_cols].values, val_df[target_col].values
    X_test, y_test = test_df[feat_cols].values, test_df[target_col].values

    model = LogisticRegression(max_iter=1000, random_state=random_seed, class_weight="balanced")
    model.fit(X_train, y_train)

    train_probs = model.predict_proba(X_train)[:, 1] if len(model.classes_) > 1 else np.zeros(len(X_train))
    val_probs = model.predict_proba(X_val)[:, 1] if len(model.classes_) > 1 else np.zeros(len(X_val))
    test_probs = model.predict_proba(X_test)[:, 1] if len(model.classes_) > 1 else np.zeros(len(X_test))

    results = {
        "model_name": "Logistic Regression Baseline",
        "train_metrics": evaluate_metrics(y_train, train_probs),
        "val_metrics": evaluate_metrics(y_val, val_probs),
        "test_metrics": evaluate_metrics(y_test, test_probs),
        "feature_cols": feat_cols
    }
    return model, results


def train_random_forest_baseline(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target_col: str = "HIGH_RISK_WITHIN_5M",
    random_seed: int = 42
) -> Tuple[RandomForestClassifier, Dict[str, Any]]:
    """
    Fits a Random Forest baseline model on CANDIDATE_MODEL_FEATURES.
    """
    feat_cols = [c for c in CANDIDATE_MODEL_FEATURES if c in train_df.columns]

    X_train, y_train = train_df[feat_cols].values, train_df[target_col].values
    X_val, y_val = val_df[feat_cols].values, val_df[target_col].values
    X_test, y_test = test_df[feat_cols].values, test_df[target_col].values

    model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=random_seed, class_weight="balanced")
    model.fit(X_train, y_train)

    train_probs = model.predict_proba(X_train)[:, 1] if len(model.classes_) > 1 else np.zeros(len(X_train))
    val_probs = model.predict_proba(X_val)[:, 1] if len(model.classes_) > 1 else np.zeros(len(X_val))
    test_probs = model.predict_proba(X_test)[:, 1] if len(model.classes_) > 1 else np.zeros(len(X_test))

    results = {
        "model_name": "Random Forest Baseline",
        "train_metrics": evaluate_metrics(y_train, train_probs),
        "val_metrics": evaluate_metrics(y_val, val_probs),
        "test_metrics": evaluate_metrics(y_test, test_probs),
        "feature_cols": feat_cols
    }
    return model, results
