# ⚡ PowerFaultAI — Power System Fault Detection & Classification

> **IBM-enhanced ML web application** that detects and classifies power system faults in real time using Flask + Scikit-learn. Supports 5 fault categories, 15 electrical features, multi-model comparison, and IBM Cloud integration.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start — Step by Step](#quick-start--step-by-step)
3. [Project Structure](#project-structure)
4. [IBM Cloud Setup (Optional)](#ibm-cloud-setup-optional)
5. [Pages & Features](#pages--features)
6. [Customisation Guide](#customisation-guide)
7. [API Reference](#api-reference)
8. [Model Performance](#model-performance)
9. [Production Deployment](#production-deployment)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Make sure the following are installed on your machine before you begin:

| Requirement | Minimum Version | Check command |
|---|---|---|
| Python | 3.8+ | `python --version` |
| pip | 21+ | `pip --version` |
| Git (optional) | any | `git --version` |

> **Windows users:** all commands below use PowerShell syntax. Replace `\` with `/` on Linux/macOS.

---

## Quick Start — Step by Step

### Step 1 — Open the project folder

Open a terminal (PowerShell on Windows, Terminal on macOS/Linux) and navigate **into** the `PowerFaultDetector` folder:

```powershell
cd "PowerFaultDetector"
```

> ⚠️ **Important:** Every command in this guide must be run from inside `PowerFaultDetector/`.  
> Running from the parent folder will cause `requirements.txt not found` errors.

---

### Step 2 — Create a virtual environment

Creating a virtual environment keeps dependencies isolated from your system Python:

```powershell
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal prompt, confirming the environment is active.

---

### Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

This installs all required packages:

| Package | Purpose |
|---|---|
| `flask` | Web framework |
| `scikit-learn` | ML algorithms & preprocessing |
| `xgboost` | XGBoost classifier |
| `numpy` / `pandas` | Numerical computing & data handling |
| `joblib` | Model serialization |
| `python-dotenv` | Load secrets from `.env` file |
| `requests` | IBM Cloud API calls |
| `gunicorn` | Production WSGI server |

Expected output ends with: `Successfully installed ...`

---

### Step 4 — Configure environment variables

Copy the example file to create your own `.env`:

```powershell
# Windows PowerShell
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` in any text editor. The **minimum required** change is the `SECRET_KEY`:

```ini
# .env
FLASK_ENV=development
FLASK_DEBUG=true
SECRET_KEY=replace-this-with-any-long-random-string

# IBM Cloud (optional — leave as-is if not using IBM features)
IBM_API_KEY=your-ibm-cloud-api-key-here
```

> 🔒 `.env` is listed in `.gitignore` and will **never** be committed to version control.  
> To enable IBM Cloud features (AI insights, Watson ML, Event Notifications), replace `IBM_API_KEY` with your real key from [cloud.ibm.com/iam/apikeys](https://cloud.ibm.com/iam/apikeys).

---

### Step 5 — Generate dataset & train models

This single command generates a 5,000-sample synthetic dataset and trains 5 ML models, then automatically picks the best one:

```powershell
python ml/train_models.py
```

**What you will see:**

```
[Pipeline] Dataset not found — generating ...
[Dataset]  Saved 5000 rows -> data/power_fault_dataset.csv
[Dataset]  Class distribution: ...
[Pipeline] Outlier winsorization applied
[Pipeline] Train: 4000  Test: 1000
[Pipeline] Feature shape after preprocessing: (4000, 15)
[Training] random_forest    Acc=0.9900  F1=0.9900
[Training] xgboost          Acc=0.9960  F1=0.9960
[Training] decision_tree    Acc=0.9820  F1=0.9820
[Training] svm              Acc=0.9970  F1=0.9970
[Training] logistic_regression  Acc=0.9960  F1=0.9960

[Best]     svm  (f1_weighted=0.9970)
[Saved]    models/best_model.pkl
[Saved]    models/pipeline.pkl
[Saved]    models/metrics.json
[Pipeline] Training complete - done!
```

**Files created after this step:**

```
models/
├── best_model.pkl       ← Trained best classifier
├── pipeline.pkl         ← Preprocessing pipeline (scaler + feature selector)
├── metrics.json         ← All model evaluation metrics
└── feature_names.json   ← Feature order used during training

data/
└── power_fault_dataset.csv   ← 5,000-row synthetic training dataset
```

> ⏱️ Training takes about **30–90 seconds** depending on your machine.

---

### Step 6 — Start the application

```powershell
python app.py
```

**Expected output:**

```
22:30:01 [INFO] PowerFaultAI — Starting PowerFaultAI on port 5000 (debug=True)
22:30:01 [INFO] PowerFaultAI — IBM Cloud features: DISABLED (set IBM_API_KEY in .env)
22:30:01 [INFO] PowerFaultAI — ML models loaded successfully
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

---

### Step 7 — Open the application

Open your browser and go to:

```
http://localhost:5000
```

You should see the **PowerFaultAI dashboard** with the prediction form, quick scenario buttons, and the IBM Cloud status pill in the navbar.

---

### Step 8 — Make your first prediction

**Option A — Quick scenario (easiest):**
Click any of the coloured buttons on the dashboard — **Normal**, **L-G Fault**, **L-L Fault**, **DLG Fault**, or **3-Phase Fault** — to auto-fill the form and run a prediction instantly.

**Option B — Enter custom values:**
Fill in the electrical parameters in the form:

| Field | Normal value | Fault example (L-G) |
|---|---|---|
| Va / Vb / Vc | `1.0 / 1.0 / 1.0` | `0.2 / 1.05 / 1.05` |
| Ia / Ib / Ic | `1.0 / 1.0 / 1.0` | `3.5 / 1.0 / 1.0` |
| Frequency Deviation | `0.0` | `0.3` |
| THD | `2.0` | `12.0` |
| Power Factor | `0.95` | `0.72` |
| Temperature | `65.0` | `95.0` |

Click **Analyse Fault** — the result panel on the right shows:
- Detected fault type + severity badge
- Confidence score with animated bar
- IBM AI Risk Score (0–100)
- Class probabilities for all 5 categories
- IBM AI Insights (rule-based warnings)
- Recommended actions + preventive suggestions

---

### Complete command summary

```powershell
# Run all steps in order (copy-paste into terminal)

cd "PowerFaultDetector"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
python ml/train_models.py
python app.py
# Open http://localhost:5000
```

---

## Project Structure

```
PowerFaultDetector/
├── app.py                    ← Flask app — IBM_CONFIG + MODEL_CONFIG at top
├── requirements.txt          ← Python dependencies
├── .env                      ← Your secrets (gitignored)
├── .env.example              ← Template — copy to .env
├── .gitignore
├── README.md
│
├── ml/
│   ├── generate_dataset.py   ← Synthetic data generator (DATASET_CONFIG)
│   ├── train_models.py       ← ML pipeline — 5 models (MODEL_CONFIG)
│   └── __init__.py
│
├── models/                   ← Created automatically after Step 5
│   ├── best_model.pkl
│   ├── pipeline.pkl
│   ├── metrics.json
│   └── feature_names.json
│
├── data/                     ← Created automatically after Step 5
│   └── power_fault_dataset.csv
│
├── templates/
│   ├── base.html             ← Shared navbar, footer, IBM status pill
│   ├── index.html            ← Dashboard + prediction form
│   ├── analytics.html        ← Charts, confusion matrix, feature importance
│   ├── history.html          ← Session prediction history
│   ├── about.html            ← Docs & API reference
│   └── error.html
│
└── static/
    ├── css/style.css         ← IBM Carbon-inspired design system
    └── js/
        ├── ibm.js            ← IBM Cloud status polling + shared utilities
        ├── dashboard.js      ← Prediction form, result rendering
        └── theme.js          ← Light/dark theme toggle
```

---

## IBM Cloud Setup (Optional)

IBM Cloud features are **fully optional** — the app works completely without them. When you add your API key, these features activate automatically:

| Feature | What it does | Required .env key |
|---|---|---|
| **AI Insights** | Rule-based + Watson ML analysis on every prediction | `IBM_API_KEY` |
| **Watson ML scoring** | Routes predictions through remote WML endpoint | `IBM_API_KEY` + `IBM_WML_INSTANCE_ID` |
| **Event Notifications** | Sends alerts for High/Critical severity faults | `IBM_API_KEY` + `IBM_EN_GUID` + `IBM_EN_URL` |
| **Navbar status pill** | Shows green "IBM Connected" when auth succeeds | `IBM_API_KEY` |

**To activate:**

1. Get your API key at [cloud.ibm.com/iam/apikeys](https://cloud.ibm.com/iam/apikeys)
2. Open `.env` and replace the placeholder:
   ```ini
   IBM_API_KEY=your-actual-key-here
   ```
3. Restart `python app.py` — the navbar pill will turn green.

---

## Pages & Features

| URL | Page | What you can do |
|---|---|---|
| `/` | **Dashboard** | Enter sensor readings, run predictions, view AI insights |
| `/analytics` | **Analytics** | Model accuracy charts, confusion matrix, feature importance, radar chart, classification report |
| `/history` | **History** | Table of all predictions made this session, confidence timeline chart |
| `/about` | **About** | Feature documentation, API reference, quick start guide |

---

## Customisation Guide

All settings are in `MODEL_CONFIG` / `DATASET_CONFIG` / `IBM_CONFIG` blocks at the top of each file. No need to touch the core logic below them.

### Change which ML algorithm is used

In [`ml/train_models.py`](ml/train_models.py) → `MODEL_CONFIG`:

```python
"models_to_train": ["random_forest"],    # train only one model
"primary_metric":  "accuracy",           # select best by accuracy instead of F1
```

### Tune hyperparameters

```python
"hyperparams": {
    "random_forest": {
        "n_estimators": 500,    # more trees = higher accuracy, slower training
        "max_depth": 15,
    },
    "svm": {
        "C": 50.0,              # higher C = less regularisation
        "kernel": "rbf",
    },
}
```

### Change preprocessing

```python
"scaler":            "robust",      # "standard" | "minmax" | "robust"
"handle_outliers":   True,
"feature_selection": "kbest",       # "variance" | "kbest" | "none"
"k_best_features":   10,
```

### Adjust confidence threshold

In [`.env`](.env):

```ini
CONFIDENCE_THRESHOLD=0.70   # predictions below this are flagged as uncertain
```

### Change the alert severity level

```ini
ALERT_SEVERITY_THRESHOLD=Critical   # only fire IBM EN alerts for Critical faults
```

### Add or rename fault categories

1. Add new physics parameters to `FAULT_PARAMS` in [`ml/generate_dataset.py`](ml/generate_dataset.py)
2. Add the new label to `LABEL_MAP` in the same file
3. Update `MODEL_CONFIG["fault_classes"]` in both [`app.py`](app.py) and [`ml/train_models.py`](ml/train_models.py)
4. Re-run `python ml/train_models.py` to regenerate dataset and retrain

---

## API Reference

### `POST /api/predict`

Submit raw sensor readings and get a full fault analysis.

**Request body:**
```json
{
  "Va": 0.2,  "Vb": 1.05, "Vc": 1.05,
  "Ia": 3.5,  "Ib": 1.0,  "Ic": 1.0,
  "freq_deviation": 0.3,
  "thd": 12.0,
  "power_factor": 0.72,
  "temperature": 95.0
}
```

**Response:**
```json
{
  "predicted_class":        "Line-to-Ground Fault",
  "predicted_label":        1,
  "confidence":             0.9986,
  "severity":               "Moderate",
  "is_uncertain":           false,
  "probable_cause":         "Single conductor contact with ground...",
  "recommended_actions":    ["Isolate affected phase immediately", "..."],
  "preventive_suggestions": ["Install surge arresters on exposed lines", "..."],
  "class_probabilities":    { "Normal Operation": 0.0002, "Line-to-Ground Fault": 0.9986, "...": "..." },
  "ai_insights":            ["Overcurrent detected (max=3.5 p.u.)...", "..."],
  "risk_score":             42,
  "ibm_source":             "rule_engine",
  "ibm_enhanced":           false,
  "timestamp":              "2025-07-08T22:30:01.123456"
}
```

### `POST /api/quick_predict`

Load a preset scenario.

```json
{ "scenario": "lg" }
```

Valid values: `"normal"` | `"lg"` | `"ll"` | `"llg"` | `"lll"`

### `GET /api/metrics`

Returns full training metrics — model accuracies, confusion matrices, feature importance, dataset stats.

### `GET /api/history`

Returns the last 50 predictions made in the current session.

### `GET /api/ibm-status`

Returns IBM Cloud connectivity status.

```json
{
  "configured":     false,
  "token_ok":       false,
  "wml_configured": false,
  "en_configured":  false,
  "alert_threshold": "High"
}
```

### `POST /api/retrain`

Triggers a full model retrain in-process (blocking). Returns the best model name and score on completion.

---

## Model Performance

After running `python ml/train_models.py`, expected results on the 1,000-sample test set:

| Model | Accuracy | F1 (Weighted) | ROC AUC |
|---|---|---|---|
| **SVM** *(auto-selected)* | ~99.7% | ~99.7% | ~99.9% |
| XGBoost | ~99.6% | ~99.6% | ~99.9% |
| Logistic Regression | ~99.6% | ~99.6% | ~99.9% |
| Random Forest | ~99.0% | ~99.0% | ~99.9% |
| Decision Tree | ~98.2% | ~98.2% | — |

> The model with the highest `f1_weighted` is automatically selected and saved to `models/best_model.pkl`.  
> Actual values vary slightly due to random noise in the generated dataset.

---

## Production Deployment

### Gunicorn (Linux / macOS)

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN python ml/train_models.py
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

```bash
docker build -t powerfaultai .
docker run -p 8000:8000 --env-file .env powerfaultai
```

### Environment variables for production

| Variable | Recommended value |
|---|---|
| `FLASK_ENV` | `production` |
| `FLASK_DEBUG` | `false` |
| `SECRET_KEY` | Long random string (minimum 32 chars) |
| `PORT` | `8000` |

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `No such file or directory: 'requirements.txt'` | Running pip from wrong folder | `cd PowerFaultDetector` first |
| `Models not found` banner on dashboard | Step 5 not run yet | Run `python ml/train_models.py` |
| `ModuleNotFoundError: No module named 'dotenv'` | python-dotenv not installed | Run `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'xgboost'` | xgboost not installed | Run `pip install -r requirements.txt` |
| IBM pill shows grey "IBM Offline" | `IBM_API_KEY` not set or placeholder | Edit `.env` and set real API key, restart app |
| IBM pill shows amber "IBM Auth Failed" | Real key set but IAM request failed | Check key is active at cloud.ibm.com/iam/apikeys |
| Port 5000 already in use | Another process on port 5000 | Set `PORT=5001` in `.env` |
| `UnicodeEncodeError` in terminal | Windows CP1252 console encoding | Run `chcp 65001` in PowerShell first |
