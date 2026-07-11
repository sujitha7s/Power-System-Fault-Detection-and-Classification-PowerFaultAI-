"""
===============================================================
  Power System Fault Detection — ML Training Pipeline
  Trains, evaluates, and serializes the best classifier
===============================================================
  Run:  python ml/train_models.py
===============================================================
"""

# ──────────────────────────────────────────────────────────────
#  MODEL CONFIGURATION  (edit here — do NOT touch core logic)
# ──────────────────────────────────────────────────────────────
MODEL_CONFIG = {
    # ── Data ────────────────────────────────────────────────
    "dataset_path":        "data/power_fault_dataset.csv",
    "test_size":           0.20,
    "val_size":            0.10,         # fraction of train used for validation
    "random_seed":         42,
    "stratify":            True,

    # ── Preprocessing ────────────────────────────────────────
    "scaler":              "standard",   # "standard" | "minmax" | "robust"
    "handle_outliers":     True,         # IQR-based winsorization
    "outlier_iqr_factor":  3.0,

    # ── Feature engineering ──────────────────────────────────
    "use_polynomial":      False,        # quadratic feature expansion
    "poly_degree":         2,
    "feature_selection":   "variance",   # "variance" | "kbest" | "none"
    "variance_threshold":  0.01,
    "k_best_features":     12,

    # ── Confidence ───────────────────────────────────────────
    "confidence_threshold": 0.55,        # below this → "uncertain"

    # ── Fault categories (must match dataset labels) ─────────
    "fault_classes": {
        0: "Normal Operation",
        1: "Line-to-Ground Fault",
        2: "Line-to-Line Fault",
        3: "Double Line-to-Ground Fault",
        4: "Three-Phase Fault",
    },
    "fault_short": {0: "Normal", 1: "LG", 2: "LL", 3: "LLG", 4: "LLL"},

    # ── Models to compare ────────────────────────────────────
    "models_to_train": [
        "random_forest", "xgboost", "decision_tree",
        "svm", "logistic_regression",
    ],
    "primary_metric": "f1_weighted",     # metric used to pick best model

    # ── Hyperparameters (per model) ──────────────────────────
    "hyperparams": {
        "random_forest": {
            "n_estimators": 200,
            "max_depth": None,
            "min_samples_split": 4,
            "min_samples_leaf": 2,
            "n_jobs": -1,
        },
        "xgboost": {
            "n_estimators": 200,
            "max_depth": 6,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "use_label_encoder": False,
            "eval_metric": "mlogloss",
        },
        "decision_tree": {
            "max_depth": 12,
            "min_samples_split": 5,
            "min_samples_leaf": 3,
            "criterion": "gini",
        },
        "svm": {
            "C": 10.0,
            "kernel": "rbf",
            "probability": True,
            "cache_size": 400,
        },
        "logistic_regression": {
            "C": 1.0,
            "max_iter": 1000,
            "solver": "lbfgs",
        },
    },

    # ── Output ───────────────────────────────────────────────
    "model_dir":           "models/",
    "best_model_file":     "models/best_model.pkl",
    "pipeline_file":       "models/pipeline.pkl",
    "metrics_file":        "models/metrics.json",
    "feature_names_file":  "models/feature_names.json",
}

# ──────────────────────────────────────────────────────────────
#  IMPORTS
# ──────────────────────────────────────────────────────────────
import sys, os, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy  as np
import pandas as pd
import joblib

from pathlib import Path

from sklearn.model_selection        import train_test_split, cross_val_score
from sklearn.preprocessing         import StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder
from sklearn.feature_selection      import VarianceThreshold, SelectKBest, f_classif
from sklearn.pipeline               import Pipeline
from sklearn.metrics                import (accuracy_score, f1_score,
                                            precision_score, recall_score,
                                            confusion_matrix, classification_report,
                                            roc_auc_score)
from sklearn.ensemble               import RandomForestClassifier
from sklearn.tree                   import DecisionTreeClassifier
from sklearn.svm                    import SVC
from sklearn.linear_model           import LogisticRegression
from sklearn.preprocessing          import PolynomialFeatures

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("[WARN] xgboost not installed — skipping XGBoost")

from generate_dataset import generate_dataset, LABEL_MAP

# ──────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────

def _make_scaler():
    s = MODEL_CONFIG["scaler"]
    if s == "minmax":  return MinMaxScaler()
    if s == "robust":  return RobustScaler()
    return StandardScaler()


def _winsorize(df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    """IQR-based winsorization (clip outliers)."""
    factor = MODEL_CONFIG["outlier_iqr_factor"]
    for col in feature_cols:
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        df[col] = df[col].clip(lower=q1 - factor * iqr,
                                upper=q3 + factor * iqr)
    return df


def _build_classifier(name: str):
    hp = MODEL_CONFIG["hyperparams"].get(name, {})
    if name == "random_forest":
        return RandomForestClassifier(**hp, random_state=MODEL_CONFIG["random_seed"])
    if name == "xgboost":
        if not XGBOOST_AVAILABLE:
            return None
        return XGBClassifier(**hp, random_state=MODEL_CONFIG["random_seed"],
                             verbosity=0)
    if name == "decision_tree":
        return DecisionTreeClassifier(**hp, random_state=MODEL_CONFIG["random_seed"])
    if name == "svm":
        return SVC(**hp, random_state=MODEL_CONFIG["random_seed"])
    if name == "logistic_regression":
        return LogisticRegression(**hp, random_state=MODEL_CONFIG["random_seed"])
    raise ValueError(f"Unknown model: {name}")


def _compute_metrics(model, X_test, y_test, name: str) -> dict:
    y_pred = model.predict(X_test)
    acc  = accuracy_score(y_test, y_pred)
    f1   = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rec  = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    cm   = confusion_matrix(y_test, y_pred).tolist()
    report = classification_report(
        y_test, y_pred,
        target_names=list(MODEL_CONFIG["fault_classes"].values()),
        output_dict=True, zero_division=0)

    # ROC AUC (one-vs-rest)
    try:
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X_test)
            auc = roc_auc_score(y_test, proba, multi_class="ovr",
                                average="weighted")
        else:
            auc = None
    except Exception:
        auc = None

    return {
        "model_name":        name,
        "accuracy":          round(acc,  4),
        "f1_weighted":       round(f1,   4),
        "precision_weighted": round(prec, 4),
        "recall_weighted":   round(rec,  4),
        "roc_auc_weighted":  round(auc, 4) if auc else None,
        "confusion_matrix":  cm,
        "classification_report": report,
    }


# ──────────────────────────────────────────────────────────────
#  MAIN PIPELINE
# ──────────────────────────────────────────────────────────────

def run_pipeline():
    cfg = MODEL_CONFIG
    Path(cfg["model_dir"]).mkdir(parents=True, exist_ok=True)

    # ── 1. Load / generate data ───────────────────────────────
    data_path = Path(cfg["dataset_path"])
    if not data_path.exists():
        print("[Pipeline] Dataset not found — generating …")
        from generate_dataset import save_dataset
        df = generate_dataset()
        save_dataset(df, str(data_path))
    else:
        df = pd.read_csv(data_path)
        print(f"[Pipeline] Loaded dataset: {len(df)} rows")

    FEATURE_COLS = [c for c in df.columns if c not in ("fault_type", "label")]
    X = df[FEATURE_COLS].copy()
    y = df["label"].values

    # ── 2. Outlier handling ───────────────────────────────────
    if cfg["handle_outliers"]:
        X = _winsorize(X, FEATURE_COLS)
        print("[Pipeline] Outlier winsorization applied")

    # ── 3. Train / test split ─────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X.values, y,
        test_size=cfg["test_size"],
        random_state=cfg["random_seed"],
        stratify=y if cfg["stratify"] else None,
    )
    print(f"[Pipeline] Train: {len(X_train)}  Test: {len(X_test)}")

    # ── 4. Preprocessing pipeline ─────────────────────────────
    steps = [("scaler", _make_scaler())]

    if cfg["use_polynomial"]:
        steps.append(("poly", PolynomialFeatures(
            degree=cfg["poly_degree"], include_bias=False)))

    if cfg["feature_selection"] == "variance":
        steps.append(("vt", VarianceThreshold(
            threshold=cfg["variance_threshold"])))
    elif cfg["feature_selection"] == "kbest":
        steps.append(("kb", SelectKBest(
            f_classif, k=cfg["k_best_features"])))

    preprocessor = Pipeline(steps)
    X_train_pp = preprocessor.fit_transform(X_train, y_train)
    X_test_pp  = preprocessor.transform(X_test)
    print(f"[Pipeline] Feature shape after preprocessing: {X_train_pp.shape}")

    # Derive feature names after preprocessing
    feature_names = FEATURE_COLS[:]
    if cfg["feature_selection"] == "variance":
        mask = preprocessor.named_steps["vt"].get_support()
        feature_names = [f for f, m in zip(feature_names, mask) if m]
    elif cfg["feature_selection"] == "kbest":
        mask = preprocessor.named_steps["kb"].get_support()
        feature_names = [f for f, m in zip(feature_names, mask) if m]

    # ── 5. Train & evaluate each model ────────────────────────
    all_metrics = {}
    trained_models = {}

    for mname in cfg["models_to_train"]:
        clf = _build_classifier(mname)
        if clf is None:
            continue
        print(f"[Training] {mname} …", end=" ")
        clf.fit(X_train_pp, y_train)
        m = _compute_metrics(clf, X_test_pp, y_test, mname)
        all_metrics[mname] = m
        trained_models[mname] = clf
        print(f"Acc={m['accuracy']:.4f}  F1={m['f1_weighted']:.4f}")

    # ── 6. Pick best model ────────────────────────────────────
    metric = cfg["primary_metric"]
    best_name = max(all_metrics, key=lambda k: all_metrics[k].get(metric, 0))
    best_clf  = trained_models[best_name]
    print(f"\n[Best]     {best_name}  ({metric}={all_metrics[best_name][metric]:.4f})")

    # ── 7. Feature importance ─────────────────────────────────
    feat_imp = {}
    if hasattr(best_clf, "feature_importances_"):
        imp = best_clf.feature_importances_
        for fname, val in zip(feature_names, imp):
            feat_imp[fname] = round(float(val), 6)
        feat_imp = dict(sorted(feat_imp.items(), key=lambda x: x[1], reverse=True))

    # ── 8. Serialize ──────────────────────────────────────────
    joblib.dump(best_clf,      cfg["best_model_file"])
    joblib.dump(preprocessor,  cfg["pipeline_file"])

    with open(cfg["feature_names_file"], "w") as f:
        json.dump({"feature_names": FEATURE_COLS,
                   "selected_features": feature_names}, f, indent=2)

    # Build full metrics payload
    summary = {
        "best_model":       best_name,
        "primary_metric":   metric,
        "best_score":       all_metrics[best_name][metric],
        "feature_importance": feat_imp,
        "models":           all_metrics,
        "dataset_info": {
            "total_samples":  len(df),
            "train_samples":  len(X_train),
            "test_samples":   len(X_test),
            "n_features":     len(FEATURE_COLS),
            "selected_features": len(feature_names),
            "class_counts":   df["fault_type"].value_counts().to_dict(),
        },
    }
    with open(cfg["metrics_file"], "w") as f:
        json.dump(summary, f, indent=2)

    print(f"[Saved]    {cfg['best_model_file']}")
    print(f"[Saved]    {cfg['pipeline_file']}")
    print(f"[Saved]    {cfg['metrics_file']}")
    print("\n[Pipeline] Training complete - done!")
    return summary


if __name__ == "__main__":
    run_pipeline()
