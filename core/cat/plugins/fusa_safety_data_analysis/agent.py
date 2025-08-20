"""
FuSa Safety Data Analysis Agent

Features:
- Load safety-related operational datasets (CSV/JSON content)
- Statistical summaries (distributions, correlations)
- Predictive analytics for failure mode risk (RandomForest/LogReg if label present)
- Interactive visualizations using Plotly; returned as HTML or JSON figure
- Encrypted storage of generated artifacts
- Tools for analysis and report generation
- REST endpoints to fetch latest figure/report
"""
import os
import io
import json
import base64
import hashlib
import datetime
from typing import Dict, Any, Optional, Tuple

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
from cryptography.fernet import Fernet

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

import plotly.express as px

from cat.mad_hatter.decorators import tool, endpoint, plugin
from cat.auth.permissions import check_permissions, AuthResource, AuthPermission
from cat.log import log


class AnalysisSettings(BaseModel):
    encryption_enabled: bool = True
    storage_dir: str = "storage"
    default_label_column: str = "failure"   # 0/1 for failure
    max_rows: int = 200000
    default_visualization: str = "trend"    # trend | histogram | box | scatter
    plot_width: int = 1100
    plot_height: int = 700
    retain_artifacts: int = 20
    reference_dir: str = "ISO26262"
    iso_edition: str = "2018"


@plugin
def settings_model():
    return AnalysisSettings


def _key() -> Optional[bytes]:
    raw = os.getenv("CCAT_FUSA_SECRET") or os.getenv("CCAT_JWT_SECRET")
    if not raw:
        return None
    return base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())


def _cipher(settings: AnalysisSettings) -> Optional[Fernet]:
    if not settings.encryption_enabled:
        return None
    key = _key()
    if not key:
        log.warning("fusa_safety_data_analysis: encryption enabled but no secret found; falling back to plaintext")
        return None
    return Fernet(key)


def _root(cat=None) -> str:
    if cat:
        return cat.mad_hatter.get_plugin().path
    from cat.looking_glass.cheshire_cat import CheshireCat
    return CheshireCat(None).mad_hatter.get_plugin().path


def _store(root: str, folder: str) -> str:
    p = os.path.join(root, folder)
    os.makedirs(p, exist_ok=True)
    return p


def _w_json(path: str, obj: Any, cipher: Optional[Fernet]):
    data = json.dumps(obj, indent=2).encode("utf-8")
    with open(path, "wb") as f:
        f.write(cipher.encrypt(data) if cipher else data)


def _r_json(path: str, cipher: Optional[Fernet]) -> Any:
    with open(path, "rb") as f:
        data = f.read()
    if cipher:
        data = cipher.decrypt(data)
    return json.loads(data.decode("utf-8"))


def _save_html(path: str, html: str, cipher: Optional[Fernet]):
    data = html.encode("utf-8")
    with open(path, "wb") as f:
        f.write(cipher.encrypt(data) if cipher else data)


def _load_dataframe(payload: Dict[str, Any], max_rows: int) -> Tuple[pd.DataFrame, str]:
    # Accept either 'csv_text', 'csv_path', or 'json_records'
    if "csv_text" in payload:
        df = pd.read_csv(io.StringIO(payload["csv_text"]))
        source = "csv_text"
    elif "json_records" in payload:
        df = pd.DataFrame(payload["json_records"])
        source = "json_records"
    elif "csv_path" in payload:
        df = pd.read_csv(payload["csv_path"])
        source = payload["csv_path"]
    else:
        df = pd.DataFrame()
        source = "empty"
    if len(df) > max_rows:
        df = df.head(max_rows)
    return df, source


def _make_figure(df: pd.DataFrame, viz: str, settings: AnalysisSettings) -> px.Figure:
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        # Try to coerce
        for c in df.columns:
            try:
                df[c] = pd.to_numeric(df[c])
            except Exception:
                pass
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        return px.scatter(title="No numeric columns available")
    first = num_cols[0]
    fig = None
    if viz == "histogram":
        fig = px.histogram(df, x=first, nbins=50, title=f"Histogram: {first}")
    elif viz == "box":
        fig = px.box(df, y=first, title=f"Box plot: {first}")
    elif viz == "scatter" and len(num_cols) > 1:
        fig = px.scatter(df, x=num_cols[0], y=num_cols[1], title=f"Scatter: {num_cols[0]} vs {num_cols[1]}")
    else:
        # Default: trend over index
        fig = px.line(df.reset_index(), x="index", y=first, title=f"Trend: {first}")
    fig.update_layout(width=settings.plot_width, height=settings.plot_height)
    return fig


@tool("analyze_safety_dataset", return_direct=False, examples=[
    "Analyze CSV text for safety metrics and build a predictive model if 'failure' label exists.",
])
def analyze_safety_dataset(input_by_llm: str, cat) -> str:
    """
    Analyze a dataset for safety metrics and potential failure prediction.
    Input JSON keys: csv_text | csv_path | json_records, options: {label_column, visualization}
    Output: summary, model report (if any), figure_path, report_path
    """
    try:
        payload = json.loads(input_by_llm)
    except Exception:
        payload = {}

    settings = AnalysisSettings(**(cat.mad_hatter.get_plugin().load_settings() or {}))
    cipher = _cipher(settings)
    root = _root(cat)
    storage = _store(root, settings.storage_dir)

    df, source = _load_dataframe(payload, settings.max_rows)
    if df.empty:
        return json.dumps({"error": "No data provided"}, indent=2)

    # Basic stats
    stats = {"rows": int(df.shape[0]), "cols": int(df.shape[1]), "columns": df.columns.tolist()}
    describe = json.loads(df.describe(include="all", datetime_is_numeric=True).fillna("").to_json())

    # Predictive if label present
    label_col = payload.get("options", {}).get("label_column", settings.default_label_column)
    model_report = None
    if label_col in df.columns:
        y = df[label_col].astype(int)
        X = df.drop(columns=[label_col])
        # keep numeric only
        X = X.select_dtypes(include=[np.number]).fillna(0)
        if not X.empty:
            Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y if len(np.unique(y)) > 1 else None)
            try:
                clf = RandomForestClassifier(n_estimators=150, random_state=42)
                clf.fit(Xtr, ytr)
                pred = clf.predict(Xte)
            except Exception:
                clf = LogisticRegression(max_iter=1000)
                clf.fit(Xtr, ytr)
                pred = clf.predict(Xte)
            model_report = classification_report(yte, pred, output_dict=True)
        else:
            model_report = {"message": "No numeric features available for model."}

    # Visualization
    viz = payload.get("options", {}).get("visualization", settings.default_visualization)
    fig = _make_figure(df, viz, settings)
    html = fig.to_html(full_html=True, include_plotlyjs="cdn")

    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    figure_path = os.path.join(storage, f"figure_{ts}.html" + (".enc" if cipher else ""))
    report_path = os.path.join(storage, f"report_{ts}.json" + (".enc" if cipher else ""))

    _save_html(figure_path, html, cipher)
    _w_json(report_path, {
        "stats": stats,
        "describe": describe,
        "model_report": model_report,
        "source": source,
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z"
    }, cipher)

    # Retention
    files = sorted([os.path.join(storage, f) for f in os.listdir(storage)], key=lambda x: os.path.getmtime(x), reverse=True)
    for f in files[settings.retain_artifacts:]:
        try: os.remove(f)
        except Exception: pass

    return json.dumps({
        "message": "analysis complete",
        "figure_path": figure_path,
        "report_path": report_path,
        "stats": stats,
        "has_model": model_report is not None
    }, indent=2)


@endpoint.get(
    path="/fusa/analysis/figure",
    tags=["FuSa Data Analysis"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def get_latest_figure():
    """
    Returns the path of the latest generated figure (HTML or encrypted HTML).
    """
    try:
        root = _root()
        from cat.looking_glass.cheshire_cat import CheshireCat
        settings = AnalysisSettings(**(CheshireCat(None).mad_hatter.get_plugin().load_settings() or {}))
        storage = _store(root, settings.storage_dir)
        candidates = sorted([os.path.join(storage, f) for f in os.listdir(storage) if "figure_" in f], key=lambda x: os.path.getmtime(x), reverse=True)
        if not candidates:
            return {"message": "no figures"}
        return {"figure_path": candidates[0]}
    except Exception as e:
        log.error(f"fusa_safety_data_analysis figure error: {e}")
        return {"error": "unable to get figure"}


@endpoint.get(
    path="/fusa/analysis/report",
    tags=["FuSa Data Analysis"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def get_latest_report():
    """
    Preview top-level information from the last report (decrypted).
    """
    try:
        from cat.looking_glass.cheshire_cat import CheshireCat
        cat = CheshireCat(None)
        settings = AnalysisSettings(**(cat.mad_hatter.get_plugin().load_settings() or {}))
        cipher = _cipher(settings)
        root = _root(cat)
        storage = _store(root, settings.storage_dir)
        candidates = sorted([os.path.join(storage, f) for f in os.listdir(storage) if "report_" in f], key=lambda x: os.path.getmtime(x), reverse=True)
        if not candidates:
            return {"message": "no reports"}
        path = candidates[0]
        obj = _r_json(path, cipher)
        # do not return entire describe/model, just meta
        return {"report_path": path, "generated_utc": obj.get("generated_utc"), "stats": obj.get("stats", {})}
    except Exception as e:
        log.error(f"fusa_safety_data_analysis report error: {e}")
        return {"error": "unable to read report"}


@endpoint.get(
    path="/fusa/analysis/references",
    tags=["FuSa Data Analysis"],
    dependencies=[check_permissions(AuthResource.PLUGINS, AuthPermission.READ)],
)
def list_analysis_references():
    """
    Lists available ISO 26262 PDFs detected for this plugin (for verification).
    """
    try:
        from cat.looking_glass.cheshire_cat import CheshireCat
        settings = AnalysisSettings(**(CheshireCat(None).mad_hatter.get_plugin().load_settings() or {}))
        root = _root()
        # Resolve directory similar to other plugins
        candidates = [
            os.path.join(root, settings.reference_dir),
            os.path.join(root, "reference", "ISO_26262", settings.iso_edition),
            os.path.join(root, "ISO_26262"),
            os.path.join(root, "ISO26262"),
        ]
        ref_dir = next((p for p in candidates if os.path.isdir(p)), None)
        if not ref_dir:
            return {"edition": settings.iso_edition, "directory": None, "files": [], "parts_detected": []}
        files = [f for f in os.listdir(ref_dir) if f.lower().endswith(".pdf")]
        import re as _re
        parts = sorted(list({int(m.group(1)) for f in files for m in [_re.search(r"26262-(\\d+)", f)] if m}))
        return {"edition": settings.iso_edition, "directory": ref_dir, "files": files, "parts_detected": parts}
    except Exception as e:
        log.error(f"fusa_safety_data_analysis references error: {e}")
        return {"error": "Unable to read references"}