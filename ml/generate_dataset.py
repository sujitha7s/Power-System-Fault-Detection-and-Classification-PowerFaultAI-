"""
===============================================================
  Power System Fault Dataset Generator
  Generates realistic synthetic data for 5 fault categories
===============================================================
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ──────────────────────────────────────────────────────────────
#  DATASET CONFIGURATION
# ──────────────────────────────────────────────────────────────
DATASET_CONFIG = {
    "n_samples": 5000,          # Total samples to generate
    "random_seed": 42,
    "output_file": "data/power_fault_dataset.csv",
    "class_distribution": {     # Relative weights per class
        "Normal":    0.30,
        "LG":        0.20,      # Line-to-Ground
        "LL":        0.18,      # Line-to-Line
        "LLG":       0.17,      # Double Line-to-Ground
        "LLL":       0.15,      # Three-Phase
    },
    "noise_level": 0.04,        # Gaussian noise fraction
}

# ──────────────────────────────────────────────────────────────
#  FAULT PHYSICS PARAMETERS
# ──────────────────────────────────────────────────────────────
FAULT_PARAMS = {
    # Each fault: (Va, Vb, Vc, Ia, Ib, Ic, freq_dev, thd, pf, temp)
    # Values are (mean, std) tuples representing per-unit quantities
    "Normal": {
        "Va": (1.00, 0.02), "Vb": (1.00, 0.02), "Vc": (1.00, 0.02),
        "Ia": (1.00, 0.05), "Ib": (1.00, 0.05), "Ic": (1.00, 0.05),
        "freq_dev": (0.00, 0.05), "thd": (2.0, 0.5),
        "power_factor": (0.95, 0.02), "temperature": (65, 5),
    },
    "LG": {  # Line-to-Ground: one voltage collapses, its current spikes
        "Va": (0.20, 0.08), "Vb": (1.05, 0.03), "Vc": (1.05, 0.03),
        "Ia": (3.50, 0.40), "Ib": (1.00, 0.08), "Ic": (1.00, 0.08),
        "freq_dev": (0.30, 0.10), "thd": (12.0, 2.0),
        "power_factor": (0.72, 0.05), "temperature": (95, 12),
    },
    "LL": {  # Line-to-Line: two voltages depressed, two currents rise
        "Va": (1.00, 0.03), "Vb": (0.35, 0.08), "Vc": (0.35, 0.08),
        "Ia": (1.05, 0.08), "Ib": (2.80, 0.35), "Ic": (2.80, 0.35),
        "freq_dev": (0.25, 0.10), "thd": (10.0, 2.0),
        "power_factor": (0.75, 0.05), "temperature": (90, 10),
    },
    "LLG": {  # Double Line-to-Ground: two voltages collapse
        "Va": (1.00, 0.03), "Vb": (0.15, 0.07), "Vc": (0.15, 0.07),
        "Ia": (1.05, 0.08), "Ib": (3.20, 0.40), "Ic": (3.20, 0.40),
        "freq_dev": (0.40, 0.12), "thd": (14.0, 2.5),
        "power_factor": (0.65, 0.06), "temperature": (105, 15),
    },
    "LLL": {  # Three-Phase: all voltages collapse, all currents spike
        "Va": (0.10, 0.05), "Vb": (0.10, 0.05), "Vc": (0.10, 0.05),
        "Ia": (4.20, 0.50), "Ib": (4.20, 0.50), "Ic": (4.20, 0.50),
        "freq_dev": (0.60, 0.15), "thd": (18.0, 3.0),
        "power_factor": (0.55, 0.07), "temperature": (125, 18),
    },
}

LABEL_MAP = {"Normal": 0, "LG": 1, "LL": 2, "LLG": 3, "LLL": 4}


def _sample_class(fault_type: str, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Draw n samples for a given fault class."""
    p = FAULT_PARAMS[fault_type]
    noise = DATASET_CONFIG["noise_level"]

    def g(key):
        mu, sigma = p[key]
        raw = rng.normal(mu, sigma, n)
        raw += rng.normal(0, abs(mu) * noise, n)   # add proportional noise
        return np.clip(raw, 0, None)

    Va, Vb, Vc = g("Va"), g("Vb"), g("Vc")
    Ia, Ib, Ic = g("Ia"), g("Ib"), g("Ic")

    # Derived features (physics-based)
    V_avg   = (Va + Vb + Vc) / 3
    I_avg   = (Ia + Ib + Ic) / 3
    V_imbal = np.std(np.stack([Va, Vb, Vc], axis=1), axis=1) / (V_avg + 1e-9)
    I_imbal = np.std(np.stack([Ia, Ib, Ic], axis=1), axis=1) / (I_avg + 1e-9)
    apparent_power = V_avg * I_avg * np.sqrt(3)
    V_neg_seq = V_imbal * 0.5 + rng.normal(0, 0.01, n)  # approximation
    I_neg_seq = I_imbal * 0.5 + rng.normal(0, 0.01, n)

    df = pd.DataFrame({
        "Va": Va, "Vb": Vb, "Vc": Vc,
        "Ia": Ia, "Ib": Ib, "Ic": Ic,
        "freq_deviation":  g("freq_dev"),
        "thd":             g("thd"),
        "power_factor":    np.clip(g("power_factor"), 0, 1),
        "temperature":     g("temperature"),
        "V_imbalance":     np.clip(V_imbal, 0, None),
        "I_imbalance":     np.clip(I_imbal, 0, None),
        "apparent_power":  apparent_power,
        "V_negative_seq":  np.clip(V_neg_seq, 0, None),
        "I_negative_seq":  np.clip(I_neg_seq, 0, None),
        "fault_type":      fault_type,
        "label":           LABEL_MAP[fault_type],
    })
    return df


def generate_dataset() -> pd.DataFrame:
    cfg  = DATASET_CONFIG
    rng  = np.random.default_rng(cfg["random_seed"])
    n    = cfg["n_samples"]
    dist = cfg["class_distribution"]

    frames = []
    for fault, weight in dist.items():
        n_class = int(round(n * weight))
        frames.append(_sample_class(fault, n_class, rng))

    df = pd.concat(frames, ignore_index=True)
    df = df.sample(frac=1, random_state=cfg["random_seed"]).reset_index(drop=True)
    return df


def save_dataset(df: pd.DataFrame, path: str):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"[Dataset]  Saved {len(df)} rows -> {out}")
    print(f"[Dataset]  Class distribution:\n{df['fault_type'].value_counts()}\n")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    df = generate_dataset()
    save_dataset(df, DATASET_CONFIG["output_file"])
