# PowerFault AI — Deployment & Project Guide

## Project Structure

```
PowerFaultDetector/
├── app.py                   ← Flask application (MODEL_CONFIG section at top)
├── requirements.txt
├── README.md
├── ml/
│   ├── generate_dataset.py  ← Synthetic dataset generator (DATASET_CONFIG)
│   ├── train_models.py      ← ML training pipeline (MODEL_CONFIG)
│   └── __init__.py
├── models/                  ← Auto-created after training
│   ├── best_model.pkl
│   ├── pipeline.pkl
│   ├── metrics.json
│   └── feature_names.json
├── data/                    ← Auto-created after dataset generation
│   └── power_fault_dataset.csv
├── templates/
│   ├── base.html
│   ├── index.html           ← Dashboard + prediction form
│   ├── analytics.html       ← Charts, metrics, confusion matrix
│   ├── history.html         ← Prediction history table
│   ├── about.html           ← Docs & API reference
│   └── error.html
└── static/
    ├── css/style.css
    └── js/
        ├── theme.js
        └── dashboard.js
```

---

## Quick Start (Local)

```bash
# 1. Navigate to project root
cd PowerFaultDetector

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Train all ML models
python ml/train_models.py

# 5. Start the application
python app.py
# → Open http://localhost:5000
```

---

## Customisation Guide

All configuration is in clearly marked `MODEL_CONFIG` / `DATASET_CONFIG` blocks at the top of each file. **No need to modify core logic.**

### Change the ML Algorithm

In `ml/train_models.py` → `MODEL_CONFIG`:
```python
"models_to_train": ["random_forest"],   # train only one model
"primary_metric":  "accuracy",          # optimise by accuracy instead of F1
```

### Tune Hyperparameters

In `ml/train_models.py` → `MODEL_CONFIG["hyperparams"]`:
```python
"random_forest": {
    "n_estimators": 500,
    "max_depth": 15,
    ...
}
```

### Change Preprocessing

```python
"scaler":            "robust",      # "standard" | "minmax" | "robust"
"handle_outliers":   True,
"feature_selection": "kbest",       # "variance" | "kbest" | "none"
"k_best_features":   10,
```

### Add/Rename Fault Categories

1. Update `FAULT_PARAMS` in `generate_dataset.py`
2. Update `LABEL_MAP` in `generate_dataset.py`
3. Update `MODEL_CONFIG["fault_classes"]` in `app.py` and `train_models.py`
4. Regenerate dataset and retrain

### Adjust Confidence Threshold

In `app.py` → `MODEL_CONFIG`:
```python
"confidence_threshold": 0.70   # Higher = more predictions flagged as uncertain
```

---

## Production Deployment

### Gunicorn (Linux/macOS)

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
docker run -p 8000:8000 powerfaultai
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | Set to `production` for deployment |
| `PORT` | `5000` | Application port |
| `SECRET_KEY` | random | Flask session key (set a fixed value in production) |

---

## API Usage

### POST /api/predict

**Request:**
```json
{
  "Va": 0.2, "Vb": 1.05, "Vc": 1.05,
  "Ia": 3.5, "Ib": 1.0,  "Ic": 1.0,
  "freq_deviation": 0.3,
  "thd": 12.0,
  "power_factor": 0.72,
  "temperature": 95.0
}
```

**Response:**
```json
{
  "predicted_class": "Line-to-Ground Fault",
  "predicted_label": 1,
  "confidence": 0.9712,
  "severity": "Moderate",
  "probable_cause": "Single conductor contact with ground...",
  "recommended_actions": ["Isolate affected phase..."],
  "preventive_suggestions": ["Install surge arresters..."],
  "class_probabilities": {
    "Normal Operation": 0.0012,
    "Line-to-Ground Fault": 0.9712,
    ...
  }
}
```

### POST /api/quick_predict

```json
{ "scenario": "lg" }   // "normal" | "lg" | "ll" | "llg" | "lll"
```

---

## Model Performance

After training, expected accuracy on the synthetic dataset:

| Model              | Accuracy | F1 (Weighted) |
|--------------------|----------|---------------|
| Random Forest      | ~99.2%   | ~99.2%        |
| XGBoost            | ~99.0%   | ~99.0%        |
| Decision Tree      | ~97.5%   | ~97.5%        |
| SVM                | ~98.5%   | ~98.5%        |
| Logistic Regression| ~96.0%   | ~96.0%        |

> Actual results vary by dataset. The best model is automatically selected and deployed.
