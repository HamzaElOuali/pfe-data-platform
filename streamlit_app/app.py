"""
Interface de demonstration Streamlit pour la plateforme E-Commerce Intelligence.

Pages :
    1. Order Scoring     — formulaire + resultats de la cascade M1->M2->M3
    2. Segment Analytics — distribution des segments depuis PostgreSQL
    3. Platform Status   — etat de sante des services

Toutes les interactions passent par l'API FastAPI via HTTP.
"""

import math
import os
from datetime import datetime

import requests
import streamlit as st
import sys

# Add project root to path for local imports
sys.path.append(os.getcwd())

API_URL = os.getenv("API_URL", "http://localhost:8090")

# --- Local Fallback Support ---
try:
    from src.ml.scoring_pipeline import ScoringPipeline
    PIPELINE_INSTANCE = None
    HAS_LOCAL_PIPELINE = True
except ImportError:
    HAS_LOCAL_PIPELINE = False

# ------------------------------------------------------------------
# CSS — Design System
# ------------------------------------------------------------------
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #0F1117;
    --surface: #1A1D2E;
    --border: #2D3154;
    --accent: #4F6EF7;
    --success: #10B981;
    --warning: #F59E0B;
    --danger: #EF4444;
    --text-primary: #F1F5F9;
    --text-secondary: #94A3B8;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--text-primary);
}

[data-testid="stSidebar"] {
    background-color: var(--surface);
    border-right: 1px solid var(--border);
}

.kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 16px;
    transition: border-color 0.2s ease;
}
.kpi-card:hover {
    border-color: var(--accent);
}
.kpi-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.1;
}
.kpi-unit {
    font-size: 14px;
    font-weight: 400;
    color: var(--text-secondary);
    margin-left: 4px;
}

.segment-card {
    border-radius: 8px;
    padding: 24px;
    text-align: center;
    border: 1px solid var(--border);
    margin-bottom: 16px;
}
.segment-name {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 8px;
}
.segment-desc {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.4;
}

.badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.badge-low    { background: rgba(16,185,129,0.15); color: var(--success); }
.badge-medium { background: rgba(245,158,11,0.15); color: var(--warning); }
.badge-high   { background: rgba(239,68,68,0.15);  color: var(--danger);  }

.cascade-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Courier New', monospace;
    font-size: 13px;
}
.cascade-table td {
    padding: 8px 12px;
    border: 1px solid var(--border);
    color: var(--text-primary);
}
.cascade-table td:first-child {
    color: var(--text-secondary);
    font-weight: 600;
    width: 80px;
}

.progress-bar-bg {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    height: 8px;
    width: 100%;
    overflow: hidden;
    margin-top: 8px;
}
.progress-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
}

.status-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}
.status-dot-ok   { background: var(--success); }
.status-dot-fail { background: var(--danger);  }

.section-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    margin-bottom: 12px;
    margin-top: 24px;
}
</style>
"""


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def api_call(method: str, path: str, json_data=None, timeout: int = 1):
    """Appel HTTP vers l'API FastAPI avec gestion d'erreur."""
    url = f"{API_URL}{path}"
    try:
        if method == "POST":
            resp = requests.post(url, json=json_data, timeout=timeout)
        else:
            resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Service unavailable — API is not reachable."
    except requests.exceptions.Timeout:
        return None, "Request timed out."
    except requests.exceptions.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            pass
        return None, f"HTTP {exc.response.status_code} : {detail}"
    except Exception as exc:
        return None, str(exc)


def risk_color(level: str) -> str:
    colors = {"Low": "#10B981", "Medium": "#F59E0B", "High": "#EF4444"}
    return colors.get(level, "#94A3B8")


def segment_color(seg: str) -> str:
    colors = {"VIP": "#10B981", "Loyal": "#10B981", "At Risk": "#F59E0B", "Lost": "#EF4444"}
    return colors.get(seg, "#4F6EF7")


def segment_description(seg: str) -> str:
    descs = {
        "VIP": "High value customer — priority retention",
        "Loyal": "Satisfied customer — maintain engagement",
        "At Risk": "Negative experience detected — immediate action required",
        "Lost": "Poor experience, low value — recovery campaign",
    }
    return descs.get(seg, "")


def render_gauge_svg(value: float, color: str, size: int = 130) -> str:
    """Genere un gauge circulaire en SVG pur."""
    radius = 50
    circumference = 2 * math.pi * radius
    offset = circumference * (1 - value)
    pct = int(value * 100)
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="{radius}" fill="none"
                stroke="#2D3154" stroke-width="10"/>
        <circle cx="60" cy="60" r="{radius}" fill="none"
                stroke="{color}" stroke-width="10"
                stroke-dasharray="{circumference}"
                stroke-dashoffset="{offset}"
                stroke-linecap="round"
                transform="rotate(-90 60 60)"/>
        <text x="60" y="58" text-anchor="middle" fill="#F1F5F9"
              font-size="22" font-weight="700" font-family="Inter, system-ui">{pct}%</text>
        <text x="60" y="76" text-anchor="middle" fill="#94A3B8"
              font-size="10" font-family="Inter, system-ui">RISK</text>
    </svg>
    """


MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# --- Direct Database Support (Fallback) ---
def get_stats_direct():
    """Lit les stats directement depuis PostgreSQL si l'API est offline."""
    import os
    from sqlalchemy import create_engine, text
    from dotenv import load_dotenv
    load_dotenv()
    
    host = os.getenv("POSTGRES_DWH_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_DWH_PORT", "5433")
    user = os.getenv("POSTGRES_DWH_USER", "admin")
    password = os.getenv("POSTGRES_DWH_PASSWORD", "admin")
    dbname = os.getenv("POSTGRES_DWH_DB", "dwh_db")
    
    try:
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Distribution
            dist_rows = conn.execute(text("SELECT customer_segment, COUNT(*) FROM quality.ml_predictions GROUP BY 1")).fetchall()
            distribution = {row[0]: row[1] for row in dist_rows}
            
            # Recent
            recent_rows = conn.execute(text("SELECT order_key, predicted_delay_days, churn_probability, customer_segment FROM quality.ml_predictions ORDER BY order_key DESC LIMIT 10")).fetchall()
            recent = [{"order_key": r[0], "predicted_delay_days": r[1], "risk_proba": r[2], "segment": r[3]} for r in recent_rows]
            
            return {"distribution": distribution, "recent_predictions": recent}, None
    except Exception as e:
        return None, f"Local DB Fallback failed: {e}"


# ------------------------------------------------------------------
# PAGE 1 — Order Scoring
# ------------------------------------------------------------------

def page_order_scoring():
    st.markdown('<h2 style="margin-bottom:4px;">Order Scoring</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94A3B8;margin-top:0;">Run the cascade scoring pipeline on a single order.</p>',
                unsafe_allow_html=True)

    col_form, col_spacer, col_results = st.columns([4, 0.5, 5.5])

    with col_form:
        # --- Logistics ---
        st.markdown('<div class="section-title">Logistics</div>', unsafe_allow_html=True)
        distance_km = st.slider("Distance (km)", 0, 3000, 450, key="dist")
        total_freight = st.number_input("Freight cost (BRL)", min_value=0.0, max_value=2000.0, value=25.0, step=1.0)
        order_month = st.selectbox("Month", MONTHS, index=5)
        order_day = st.selectbox("Day of week", DAYS, index=2)

        # --- Order ---
        st.markdown('<div class="section-title">Order Details</div>', unsafe_allow_html=True)
        total_items_price = st.number_input("Total price (BRL)", min_value=0.0, max_value=15000.0, value=185.0, step=5.0)
        nb_items = st.slider("Number of items", 1, 20, 2, key="items")

        # --- Feedback ---
        st.markdown('<div class="section-title">Customer Feedback</div>', unsafe_allow_html=True)
        review_score = st.slider("Review score", 1.0, 5.0, 4.0, step=0.5, key="review")
        if review_score <= 2:
            fb_label, fb_color = "Negative", "#EF4444"
        elif review_score <= 3:
            fb_label, fb_color = "Neutral", "#F59E0B"
        else:
            fb_label, fb_color = "Positive", "#10B981"
        st.markdown(f'<span style="font-size:12px;color:{fb_color};font-weight:600;">{fb_label}</span>',
                    unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("Run Scoring", use_container_width=True, type="primary")

    # --- Scoring ---
    if run_btn:
        payload = {
            "distance_km": float(distance_km),
            "total_freight": float(total_freight),
            "order_month": MONTHS.index(order_month) + 1,
            "order_day_of_week": DAYS.index(order_day),
            "review_score": float(review_score),
            "total_items_price": float(total_items_price),
            "nb_items": int(nb_items),
        }
        data, err = api_call("POST", "/predict", json_data=payload)
        
        # --- Local Fallback ---
        if err and HAS_LOCAL_PIPELINE:
            global PIPELINE_INSTANCE
            try:
                if PIPELINE_INSTANCE is None:
                    models_dir = os.path.join(os.getcwd(), "models")
                    PIPELINE_INSTANCE = ScoringPipeline(models_dir)
                data = PIPELINE_INSTANCE.predict(payload)
                err = None
                st.toast("Using Local Scoring (API Offline)", icon="🔌")
            except Exception as e:
                err = f"API Offline & Local Fallback failed: {e}"

        if err:
            st.session_state["scoring_result"] = None
            st.session_state["scoring_error"] = err
        else:
            st.session_state["scoring_result"] = data
            st.session_state["scoring_error"] = None

    # --- Results ---
    with col_results:
        error = st.session_state.get("scoring_error")
        result = st.session_state.get("scoring_result")

        if error:
            st.markdown(f"""
            <div class="kpi-card" style="border-color:var(--danger);">
                <div class="kpi-label">ERROR</div>
                <div style="color:var(--danger);font-size:14px;">{error}</div>
            </div>
            """, unsafe_allow_html=True)

        elif result:
            delay = result["predicted_delay_days"]
            rp = result["risk_proba"]
            rl = result["risk_level"]
            seg = result["segment"]
            conf = result["confidence_score"]

            # -- Delivery Forecast --
            if delay < 10:
                bar_color = "#10B981"
            elif delay < 20:
                bar_color = "#F59E0B"
            else:
                bar_color = "#EF4444"
            bar_pct = min(delay / 30 * 100, 100)

            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Delivery Forecast</div>
                <div class="kpi-value">{delay:.1f}<span class="kpi-unit">days</span></div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:{bar_pct:.0f}%;background:{bar_color};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # -- Risk Assessment --
            rc = risk_color(rl)
            badge_class = {"Low": "badge-low", "Medium": "badge-medium", "High": "badge-high"}.get(rl, "badge-low")
            gauge_html = render_gauge_svg(rp, rc)

            st.markdown(f"""
            <div class="kpi-card" style="text-align:center;">
                <div class="kpi-label">Risk Assessment</div>
                {gauge_html}
                <div style="margin-top:8px;">
                    <span class="badge {badge_class}">{rl}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # -- Customer Segment --
            sc = segment_color(seg)
            sd = segment_description(seg)
            st.markdown(f"""
            <div class="segment-card" style="background:rgba({int(sc[1:3],16)},{int(sc[3:5],16)},{int(sc[5:7],16)},0.08);border-color:{sc}40;">
                <div class="segment-name" style="color:{sc};">{seg}</div>
                <div class="segment-desc">{sd}</div>
            </div>
            """, unsafe_allow_html=True)

            # -- Cascade Trace --
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Cascade Trace</div>
                <table class="cascade-table">
                    <tr><td>M1</td><td>predicted_delay</td><td>{delay:.1f} days</td></tr>
                    <tr><td>M2</td><td>risk_proba</td><td>{rp*100:.1f}%</td></tr>
                    <tr><td>M3</td><td>segment</td><td>{seg}</td></tr>
                </table>
                <div style="margin-top:8px;font-size:11px;color:#94A3B8;">
                    confidence: {conf:.1%} | scored at: {result['scored_at'][:19]}
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown("""
            <div class="kpi-card" style="text-align:center;padding:48px;">
                <div style="color:#94A3B8;font-size:14px;">
                    Configure the order parameters and click <b>Run Scoring</b>.
                </div>
            </div>
            """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# PAGE 2 — Segment Analytics
# ------------------------------------------------------------------

def page_segment_analytics():
    st.markdown('<h2 style="margin-bottom:4px;">Segment Analytics</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94A3B8;margin-top:0;">Real-time distribution from scored predictions.</p>',
                unsafe_allow_html=True)

    data, err = api_call("GET", "/predict/segments/stats")
    
    if err:
        # Tentative de lecture directe en DB
        data, db_err = get_stats_direct()
        if db_err:
            st.error(f"API Offline & {db_err}")
            return
        else:
            st.toast("Using Direct DB Access (API Offline)", icon="🗄️")
            err = None

    if err:
        st.error(err)
        return

    if not data:
        st.info("No segment data available.")
        return

    distribution = data.get("distribution", {})
    recent = data.get("recent_predictions", [])

    # -- KPI Cards --
    if distribution:
        seg_order = ["VIP", "Loyal", "At Risk", "Lost"]
        cols = st.columns(len(seg_order))
        for i, seg_name in enumerate(seg_order):
            count = distribution.get(seg_name, 0)
            sc = segment_color(seg_name)
            with cols[i]:
                st.markdown(f"""
                <div class="kpi-card" style="text-align:center;border-color:{sc}40;">
                    <div class="kpi-label">{seg_name}</div>
                    <div class="kpi-value" style="color:{sc};">{count:,}</div>
                    <div class="kpi-unit">orders</div>
                </div>
                """, unsafe_allow_html=True)

    # -- Charts --
    if distribution:
        try:
            import plotly.graph_objects as go

            seg_labels = list(distribution.keys())
            seg_values = list(distribution.values())
            seg_colors = [segment_color(s) for s in seg_labels]

            col_donut, col_bar = st.columns(2)

            with col_donut:
                fig_donut = go.Figure(data=[go.Pie(
                    labels=seg_labels, values=seg_values,
                    hole=0.55, marker=dict(colors=seg_colors),
                    textinfo="label+percent", textfont=dict(size=12, color="#F1F5F9"),
                )])
                fig_donut.update_layout(
                    paper_bgcolor="#0F1117", plot_bgcolor="#0F1117",
                    font=dict(family="Inter", color="#F1F5F9"),
                    showlegend=False, margin=dict(t=20, b=20, l=20, r=20),
                    height=320,
                )
                st.plotly_chart(fig_donut, use_container_width=True)

            with col_bar:
                fig_bar = go.Figure(data=[go.Bar(
                    y=seg_labels, x=seg_values, orientation="h",
                    marker=dict(color=seg_colors),
                    text=seg_values, textposition="auto",
                    textfont=dict(color="#F1F5F9"),
                )])
                fig_bar.update_layout(
                    paper_bgcolor="#0F1117", plot_bgcolor="#0F1117",
                    font=dict(family="Inter", color="#F1F5F9"),
                    xaxis=dict(showgrid=False, color="#94A3B8"),
                    yaxis=dict(showgrid=False, color="#94A3B8"),
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=320,
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        except ImportError:
            st.warning("Plotly is required for charts.")

    # -- Recent predictions table --
    if recent:
        st.markdown('<div class="section-title">Recent Predictions</div>', unsafe_allow_html=True)
        import pandas as pd
        df_recent = pd.DataFrame(recent)
        st.dataframe(df_recent, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------
# PAGE 3 — Platform Status
# ------------------------------------------------------------------

def page_platform_status():
    st.markdown('<h2 style="margin-bottom:4px;">Platform Status</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94A3B8;margin-top:0;">Service health and connectivity.</p>',
                unsafe_allow_html=True)

    # -- ML Health --
    data, err = api_call("GET", "/predict/health")

    st.markdown('<div class="section-title">ML Pipeline</div>', unsafe_allow_html=True)
    if err:
        st.markdown(f"""
        <div class="status-card">
            <div class="status-dot status-dot-fail"></div>
            <div>
                <div style="font-weight:600;">Scoring API</div>
                <div style="font-size:12px;color:#94A3B8;">{err}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        models = data.get("model_versions", {})
        loaded = data.get("models_loaded", False)
        dot_class = "status-dot-ok" if loaded else "status-dot-fail"
        for key, version in models.items():
            label = {"m1": "Delay Regressor", "m2": "Risk Classifier", "m3": "Segment Clustering"}.get(key, key)
            st.markdown(f"""
            <div class="status-card">
                <div class="status-dot {dot_class}"></div>
                <div>
                    <div style="font-weight:600;">{label}</div>
                    <div style="font-size:12px;color:#94A3B8;">{version}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        ts = data.get("timestamp", "")[:19]
        st.markdown(f'<p style="font-size:12px;color:#94A3B8;margin-top:8px;">Last check: {ts}</p>',
                    unsafe_allow_html=True)
    
    # -- Local Fallback Status --
    st.markdown('<div class="section-title">Local Fallback Mode</div>', unsafe_allow_html=True)
    status_dot = "status-dot-ok" if HAS_LOCAL_PIPELINE else "status-dot-fail"
    status_text = "Available (Ready to bypass API)" if HAS_LOCAL_PIPELINE else "Unavailable (Source code not found)"
    st.markdown(f"""
    <div class="status-card">
        <div class="status-dot {status_dot}"></div>
        <div>
            <div style="font-weight:600;">Direct Scoring</div>
            <div style="font-size:12px;color:#94A3B8;">{status_text}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -- Infrastructure Links --
    st.markdown('<div class="section-title">Infrastructure Services</div>', unsafe_allow_html=True)
    services = [
        ("Apache Airflow", "Orchestration", "http://localhost:8080"),
        ("dbt Docs", "Data Catalog", "http://localhost:8085"),
        ("Grafana", "Monitoring", "http://localhost:3000"),
        ("pgAdmin", "Database Admin", "http://localhost:5050"),
    ]
    for name, desc, url in services:
        st.markdown(f"""
        <div class="status-card">
            <div class="status-dot status-dot-ok"></div>
            <div style="flex:1;">
                <div style="font-weight:600;">{name}</div>
                <div style="font-size:12px;color:#94A3B8;">{desc}</div>
            </div>
            <a href="{url}" target="_blank" style="color:#4F6EF7;font-size:13px;text-decoration:none;">
                Open
            </a>
        </div>
        """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="E-Commerce Intelligence Platform",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("""
        <div style="padding:12px 0;">
            <div style="font-size:16px;font-weight:700;color:#F1F5F9;">E-Commerce Intelligence</div>
            <div style="font-size:12px;color:#94A3B8;margin-top:2px;">ML Scoring Platform</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        page = st.radio(
            "Navigation",
            ["Order Scoring", "Segment Analytics", "Platform Status"],
            label_visibility="collapsed",
        )

    if page == "Order Scoring":
        page_order_scoring()
    elif page == "Segment Analytics":
        page_segment_analytics()
    elif page == "Platform Status":
        page_platform_status()


if __name__ == "__main__":
    main()
