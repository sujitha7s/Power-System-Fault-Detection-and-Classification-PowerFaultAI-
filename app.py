"""
===============================================================
  Power System Fault Detection — Flask Application
  Real-time fault prediction API + IBM Cloud integration
===============================================================
  Run:  python app.py
  Env:  copy .env.example -> .env and fill in your values
===============================================================
"""

import os, sys, json, warnings, logging, time
from pathlib import Path
warnings.filterwarnings("ignore")

# ── Load .env FIRST, before any other config reads ────────────
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

# ──────────────────────────────────────────────────────────────
#  IBM CLOUD CONFIGURATION  (all values come from .env)
# ──────────────────────────────────────────────────────────────
IBM_CONFIG = {
    # ── Core credential (required for IBM Cloud features) ─────
    "api_key":              os.getenv("IBM_API_KEY", ""),

    # ── Watson Machine Learning (remote model serving) ────────
    "wml_url":              os.getenv("IBM_WML_URL", "https://us-south.ml.cloud.ibm.com"),
    "wml_instance_id":      os.getenv("IBM_WML_INSTANCE_ID", ""),

    # ── Watson Assistant (chatbot integration) ─────────────────
    "wa_api_key":           os.getenv("IBM_WA_API_KEY", ""),
    "wa_service_url":       os.getenv("IBM_WA_SERVICE_URL", ""),
    "wa_assistant_id":      os.getenv("IBM_WA_ASSISTANT_ID", ""),

    # ── Event Notifications (alert delivery) ──────────────────
    "en_guid":              os.getenv("IBM_EN_GUID", ""),
    "en_url":               os.getenv("IBM_EN_URL", ""),

    # ── Runtime flags ─────────────────────────────────────────
    # Set automatically — True when IBM_API_KEY is non-empty placeholder
    "features_enabled":     bool(os.getenv("IBM_API_KEY", "").strip()
                                  and os.getenv("IBM_API_KEY") != "your-ibm-cloud-api-key-here"),

    # ── Alert threshold ────────────────────────────────────────
    "alert_severity_threshold": os.getenv("ALERT_SEVERITY_THRESHOLD", "High"),

    # ── IAM token cache (internal) ────────────────────────────
    "_iam_token":           None,
    "_iam_expires":         0,
}

# ──────────────────────────────────────────────────────────────
#  MODEL CONFIGURATION  (edit here — no need to touch core code)
# ──────────────────────────────────────────────────────────────
MODEL_CONFIG = {
    # ── Paths ────────────────────────────────────────────────
    "best_model_file":     "models/best_model.pkl",
    "pipeline_file":       "models/pipeline.pkl",
    "metrics_file":        "models/metrics.json",
    "feature_names_file":  "models/feature_names.json",

    # ── Inference ────────────────────────────────────────────
    "confidence_threshold": float(os.getenv("CONFIDENCE_THRESHOLD", "0.55")),

    # ── Fault metadata ───────────────────────────────────────
    "fault_classes": {
        "0": "Normal Operation",
        "1": "Line-to-Ground Fault",
        "2": "Line-to-Line Fault",
        "3": "Double Line-to-Ground Fault",
        "4": "Three-Phase Fault",
    },
    "fault_severity": {
        "0": "None",
        "1": "Moderate",
        "2": "Moderate",
        "3": "High",
        "4": "Critical",
    },
    "fault_causes": {
        "0": "System operating within normal parameters",
        "1": "Single conductor contact with ground — insulation failure or lightning",
        "2": "Two conductors short-circuited — mechanical damage or high wind",
        "3": "Two conductors shorted to ground — cascaded insulation failure",
        "4": "All three conductors shorted — catastrophic equipment failure",
    },
    "fault_actions": {
        "0": [
            "Continue normal monitoring",
            "Schedule routine maintenance per calendar",
            "Log operational data for trend analysis",
        ],
        "1": [
            "Isolate affected phase immediately",
            "Deploy ground fault relay protection",
            "Inspect insulation resistance of phase A",
            "Check for moisture ingress or physical damage",
        ],
        "2": [
            "Activate line-to-line protection relays",
            "Inspect conductors for physical damage",
            "Review mechanical support structures",
            "Measure contact resistance between affected phases",
        ],
        "3": [
            "Initiate emergency shutdown sequence",
            "Isolate affected section from bus",
            "Dispatch maintenance crew immediately",
            "Perform full insulation resistance test after isolation",
        ],
        "4": [
            "EMERGENCY: Trip all circuit breakers immediately",
            "Activate backup power to critical loads",
            "Evacuate hazard zone — potential arc flash risk",
            "Notify grid operator and initiate incident report",
            "Full system inspection before re-energisation",
        ],
    },
    "preventive_suggestions": {
        "0": [
            "Maintain insulation test intervals",
            "Verify protection relay calibration quarterly",
            "Monitor load balancing across phases",
        ],
        "1": [
            "Install surge arresters on exposed lines",
            "Upgrade insulation on aging conductors",
            "Add ground fault indicators on feeders",
        ],
        "2": [
            "Increase conductor clearance spacing",
            "Install line guards in high-wind areas",
            "Deploy automatic reclosers on affected circuit",
        ],
        "3": [
            "Install differential protection systems",
            "Upgrade switchgear to SF6 technology",
            "Implement remote monitoring on critical nodes",
        ],
        "4": [
            "Install bus protection differential relays",
            "Upgrade to arc-flash-rated switchgear",
            "Implement predictive monitoring with AI analytics",
            "Establish N-1 redundancy for critical feeders",
        ],
    },
    "feature_ranges": {
        "Va":             {"min": 0.0,  "max": 2.0,   "unit": "p.u.",  "label": "Phase A Voltage"},
        "Vb":             {"min": 0.0,  "max": 2.0,   "unit": "p.u.",  "label": "Phase B Voltage"},
        "Vc":             {"min": 0.0,  "max": 2.0,   "unit": "p.u.",  "label": "Phase C Voltage"},
        "Ia":             {"min": 0.0,  "max": 8.0,   "unit": "p.u.",  "label": "Phase A Current"},
        "Ib":             {"min": 0.0,  "max": 8.0,   "unit": "p.u.",  "label": "Phase B Current"},
        "Ic":             {"min": 0.0,  "max": 8.0,   "unit": "p.u.",  "label": "Phase C Current"},
        "freq_deviation": {"min": -2.0, "max": 2.0,   "unit": "Hz",    "label": "Frequency Deviation"},
        "thd":            {"min": 0.0,  "max": 40.0,  "unit": "%",     "label": "Total Harmonic Distortion"},
        "power_factor":   {"min": 0.0,  "max": 1.0,   "unit": "",      "label": "Power Factor"},
        "temperature":    {"min": 20.0, "max": 180.0, "unit": "°C",    "label": "Equipment Temperature"},
    },
}

# ──────────────────────────────────────────────────────────────
#  IMPORTS (after dotenv so env vars are available)
# ──────────────────────────────────────────────────────────────
import requests
from flask import Flask, request, jsonify, render_template
import numpy  as np
import joblib
from datetime import datetime

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO"), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("PowerFaultAI")

# ── Flask app ─────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24).hex())

# ──────────────────────────────────────────────────────────────
#  MODEL LOADING
# ──────────────────────────────────────────────────────────────
_model      = None
_pipeline   = None
_metrics    = None
_feat_names = None


def load_models():
    global _model, _pipeline, _metrics, _feat_names
    cfg = MODEL_CONFIG
    try:
        _model    = joblib.load(cfg["best_model_file"])
        _pipeline = joblib.load(cfg["pipeline_file"])
        with open(cfg["metrics_file"])       as f: _metrics    = json.load(f)
        with open(cfg["feature_names_file"]) as f: _feat_names = json.load(f)
        log.info("ML models loaded successfully")
        return True
    except FileNotFoundError as e:
        log.warning("Models not found (%s) — run: python ml/train_models.py", e)
        return False


models_ready       = load_models()
prediction_history = []   # last 50 in-memory

# ──────────────────────────────────────────────────────────────
#  IBM CLOUD HELPERS
# ──────────────────────────────────────────────────────────────

def _get_iam_token() -> str | None:
    """Fetch / refresh IBM Cloud IAM bearer token (cached 55 min)."""
    cfg = IBM_CONFIG
    if not cfg["api_key"] or not cfg["features_enabled"]:
        return None
    if cfg["_iam_token"] and time.time() < cfg["_iam_expires"]:
        return cfg["_iam_token"]
    try:
        resp = requests.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                  "apikey": cfg["api_key"]},
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        cfg["_iam_token"]   = data["access_token"]
        cfg["_iam_expires"] = time.time() + data.get("expires_in", 3600) - 300
        log.info("IBM IAM token refreshed (expires in %ds)", data.get("expires_in", 3600))
        return cfg["_iam_token"]
    except Exception as exc:
        log.warning("IBM IAM token fetch failed: %s", exc)
        return None


def _ibm_ai_enhance(prediction: dict, features: dict) -> dict:
    """
    Call IBM Watson Machine Learning scoring endpoint (if configured).
    Falls back gracefully if WML is not set up — returns the original prediction
    augmented with a simple rule-based AI explanation.
    """
    cfg = IBM_CONFIG

    # ── Build rule-based AI insight (always available) ────────
    sev    = prediction.get("severity", "None")
    label  = prediction.get("predicted_label", 0)
    conf   = prediction.get("confidence", 0) or 0
    Va, Vb, Vc = features.get("Va",1), features.get("Vb",1), features.get("Vc",1)
    Ia, Ib, Ic = features.get("Ia",1), features.get("Ib",1), features.get("Ic",1)

    insights = []
    if abs(Va - 1.0) > 0.5:
        insights.append("Phase A voltage deviation exceeds 50% — possible insulation breakdown")
    if max(Ia, Ib, Ic) > 3.0:
        insights.append(f"Overcurrent detected (max={max(Ia,Ib,Ic):.1f} p.u.) — immediate protection relay check required")
    if features.get("thd", 0) > 10:
        insights.append(f"High THD ({features['thd']:.1f}%) — harmonics stress on transformer insulation")
    if features.get("temperature", 65) > 100:
        insights.append(f"Elevated equipment temperature ({features['temperature']:.0f} °C) — thermal protection may trigger")
    if features.get("power_factor", 0.95) < 0.7:
        insights.append("Low power factor — reactive power compensation recommended")
    if not insights:
        insights.append("All parameters within acceptable deviations — no additional warnings")

    enhancement = {
        "ai_insights":    insights,
        "risk_score":     min(100, int((1 - conf) * 40 + label * 15 + (max(Ia,Ib,Ic)-1)*8)),
        "ibm_enhanced":   False,
        "ibm_source":     "rule_engine",
    }

    # ── Optionally call WML scoring endpoint ──────────────────
    if cfg["features_enabled"] and cfg["wml_url"] and cfg["wml_instance_id"]:
        token = _get_iam_token()
        if token:
            try:
                wml_url = f"{cfg['wml_url']}/v4/deployments/{cfg['wml_instance_id']}/predictions"
                payload = {"input_data": [{"fields": list(features.keys()),
                                           "values": [list(features.values())]}]}
                resp = requests.post(
                    wml_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json"},
                    timeout=8,
                )
                if resp.ok:
                    wml_result = resp.json()
                    enhancement["ibm_enhanced"] = True
                    enhancement["ibm_source"]   = "watson_ml"
                    enhancement["wml_raw"]      = wml_result
                    log.info("WML scoring returned 200")
            except Exception as exc:
                log.warning("WML scoring call failed: %s", exc)

    return {**prediction, **enhancement}


def _ibm_send_alert(prediction: dict):
    """Send IBM Event Notifications alert for high-severity faults."""
    cfg = IBM_CONFIG
    if not cfg["features_enabled"] or not cfg["en_guid"]:
        return

    sev_order  = {"None": 0, "Moderate": 1, "High": 2, "Critical": 3}
    threshold  = cfg["alert_severity_threshold"]
    if sev_order.get(prediction["severity"], 0) < sev_order.get(threshold, 2):
        return

    token = _get_iam_token()
    if not token:
        return

    try:
        url     = f"{cfg['en_url']}/v1/instances/{cfg['en_guid']}/notifications"
        payload = {
            "ibmenseverity": "high" if prediction["severity"] == "Critical" else "medium",
            "ibmensourceid": "powerfaultai",
            "ibmendefaultshort": f"[FAULT ALERT] {prediction['predicted_class']}",
            "ibmendefaultlong": (
                f"Fault detected: {prediction['predicted_class']}\n"
                f"Severity: {prediction['severity']}\n"
                f"Confidence: {int((prediction.get('confidence') or 0)*100)}%\n"
                f"Cause: {prediction['probable_cause']}\n"
                f"Time: {prediction['timestamp']}"
            ),
        }
        requests.post(
            url, json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=6,
        )
        log.info("IBM EN alert dispatched for %s", prediction["predicted_class"])
    except Exception as exc:
        log.warning("IBM EN alert failed: %s", exc)


# ──────────────────────────────────────────────────────────────
#  PREDICTION CORE
# ──────────────────────────────────────────────────────────────

def _derive_features(raw: dict) -> dict:
    Va, Vb, Vc = raw["Va"], raw["Vb"], raw["Vc"]
    Ia, Ib, Ic = raw["Ia"], raw["Ib"], raw["Ic"]
    V_avg   = (Va + Vb + Vc) / 3
    I_avg   = (Ia + Ib + Ic) / 3
    V_imbal = float(np.std([Va, Vb, Vc])) / (V_avg + 1e-9)
    I_imbal = float(np.std([Ia, Ib, Ic])) / (I_avg + 1e-9)
    app_pwr = V_avg * I_avg * 1.7320508
    return {
        **raw,
        "V_imbalance":    round(V_imbal, 6),
        "I_imbalance":    round(I_imbal, 6),
        "apparent_power": round(app_pwr, 6),
        "V_negative_seq": round(V_imbal * 0.5, 6),
        "I_negative_seq": round(I_imbal * 0.5, 6),
    }


def _predict(feature_dict: dict) -> dict:
    cfg        = MODEL_CONFIG
    feat_order = _feat_names["feature_names"]
    X_raw      = np.array([[feature_dict[f] for f in feat_order]])
    X_pp       = _pipeline.transform(X_raw)
    pred_label = int(_model.predict(X_pp)[0])

    confidence, all_probs = None, {}
    if hasattr(_model, "predict_proba"):
        probs      = _model.predict_proba(X_pp)[0]
        confidence = float(np.max(probs))
        for i, p in enumerate(probs):
            all_probs[cfg["fault_classes"][str(i)]] = round(float(p), 4)

    key = str(pred_label)
    return {
        "predicted_label":         pred_label,
        "predicted_class":         cfg["fault_classes"][key],
        "confidence":              round(confidence, 4) if confidence else None,
        "is_uncertain":            (confidence is not None and confidence < cfg["confidence_threshold"]),
        "severity":                cfg["fault_severity"][key],
        "probable_cause":          cfg["fault_causes"][key],
        "recommended_actions":     cfg["fault_actions"][key],
        "preventive_suggestions":  cfg["preventive_suggestions"][key],
        "class_probabilities":     all_probs,
        "timestamp":               datetime.now().isoformat(),
        "ibm_features_enabled":    IBM_CONFIG["features_enabled"],
    }


# ──────────────────────────────────────────────────────────────
#  ROUTES — Pages
# ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template(
        "index.html",
        models_ready=models_ready,
        fault_classes=MODEL_CONFIG["fault_classes"],
        feature_ranges=MODEL_CONFIG["feature_ranges"],
        ibm_enabled=IBM_CONFIG["features_enabled"],
        app_org=os.getenv("APP_ORG", "IBM Power Systems Division"),
    )


@app.route("/analytics")
def analytics():
    if not models_ready:
        return render_template("error.html", message="Models not trained yet.")
    return render_template("analytics.html", metrics=_metrics,
                           ibm_enabled=IBM_CONFIG["features_enabled"])


@app.route("/history")
def history():
    return render_template("history.html",
                           history=list(reversed(prediction_history)),
                           ibm_enabled=IBM_CONFIG["features_enabled"])


@app.route("/about")
def about():
    return render_template("about.html",
                           ibm_enabled=IBM_CONFIG["features_enabled"],
                           app_org=os.getenv("APP_ORG", "IBM Power Systems Division"))


# ──────────────────────────────────────────────────────────────
#  ROUTES — API
# ──────────────────────────────────────────────────────────────

@app.route("/api/predict", methods=["POST"])
def api_predict():
    if not models_ready:
        return jsonify({"error": "Models not ready. Run: python ml/train_models.py"}), 503

    data = request.get_json(force=True)
    try:
        raw = {k: float(data[k]) for k in MODEL_CONFIG["feature_ranges"]}
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400

    full   = _derive_features(raw)
    result = _predict(full)

    # IBM AI enhancement
    result = _ibm_ai_enhance(result, {**raw,
                                       "V_imbalance":    full["V_imbalance"],
                                       "I_imbalance":    full["I_imbalance"],
                                       "apparent_power": full["apparent_power"],
                                       "thd":            raw["thd"],
                                       "temperature":    raw["temperature"],
                                       "power_factor":   raw["power_factor"]})

    result["input_features"] = {**raw,
                                  "V_imbalance":    full["V_imbalance"],
                                  "I_imbalance":    full["I_imbalance"],
                                  "apparent_power": full["apparent_power"]}
    # Alert
    _ibm_send_alert(result)

    entry = {**result, "raw_inputs": raw}
    prediction_history.append(entry)
    if len(prediction_history) > 50:
        prediction_history.pop(0)

    return jsonify(result)


@app.route("/api/metrics")
def api_metrics():
    if not models_ready:
        return jsonify({"error": "Models not ready"}), 503
    return jsonify(_metrics)


@app.route("/api/history")
def api_history():
    return jsonify(list(reversed(prediction_history[-50:])))


@app.route("/api/quick_predict", methods=["POST"])
def api_quick_predict():
    presets = {
        "normal": {"Va":1.0,"Vb":1.0,"Vc":1.0,"Ia":1.0,"Ib":1.0,"Ic":1.0,
                   "freq_deviation":0.0,"thd":2.0,"power_factor":0.95,"temperature":65.0},
        "lg":     {"Va":0.2,"Vb":1.05,"Vc":1.05,"Ia":3.5,"Ib":1.0,"Ic":1.0,
                   "freq_deviation":0.3,"thd":12.0,"power_factor":0.72,"temperature":95.0},
        "ll":     {"Va":1.0,"Vb":0.35,"Vc":0.35,"Ia":1.05,"Ib":2.8,"Ic":2.8,
                   "freq_deviation":0.25,"thd":10.0,"power_factor":0.75,"temperature":90.0},
        "llg":    {"Va":1.0,"Vb":0.15,"Vc":0.15,"Ia":1.05,"Ib":3.2,"Ic":3.2,
                   "freq_deviation":0.4,"thd":14.0,"power_factor":0.65,"temperature":105.0},
        "lll":    {"Va":0.1,"Vb":0.1,"Vc":0.1,"Ia":4.2,"Ib":4.2,"Ic":4.2,
                   "freq_deviation":0.6,"thd":18.0,"power_factor":0.55,"temperature":125.0},
    }
    scenario = request.get_json(force=True).get("scenario", "normal")
    if scenario not in presets:
        return jsonify({"error": "Unknown scenario"}), 400
    raw    = presets[scenario]
    full   = _derive_features(raw)
    result = _predict(full)
    result = _ibm_ai_enhance(result, {**raw, "thd": raw["thd"],
                                       "temperature": raw["temperature"],
                                       "power_factor": raw["power_factor"]})
    result["input_features"] = raw
    return jsonify(result)


@app.route("/api/ibm-status")
def api_ibm_status():
    """Return IBM Cloud connectivity status."""
    configured = IBM_CONFIG["features_enabled"]
    token_ok   = False
    if configured:
        token = _get_iam_token()
        token_ok = token is not None

    return jsonify({
        "configured":     configured,
        "token_ok":       token_ok,
        "wml_configured": bool(IBM_CONFIG["wml_instance_id"]),
        "en_configured":  bool(IBM_CONFIG["en_guid"]),
        "wa_configured":  bool(IBM_CONFIG["wa_api_key"]),
        "alert_threshold": IBM_CONFIG["alert_severity_threshold"],
    })


@app.route("/api/retrain", methods=["POST"])
def api_retrain():
    try:
        ml_dir = Path(__file__).parent / "ml"
        sys.path.insert(0, str(ml_dir))
        from train_models import run_pipeline
        summary = run_pipeline()
        global models_ready
        models_ready = load_models()
        return jsonify({"status": "success",
                        "best_model": summary["best_model"],
                        "score": summary["best_score"]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ──────────────────────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() in ("true", "1", "yes")
    log.info("Starting PowerFaultAI on port %d (debug=%s)", port, debug)
    log.info("IBM Cloud features: %s", "ENABLED" if IBM_CONFIG["features_enabled"] else "DISABLED (set IBM_API_KEY in .env)")
    app.run(debug=debug, host="0.0.0.0", port=port)
