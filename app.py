import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="ESG Forensic Dashboard", layout="wide")

st.title("Institutional ESG Forensic & Star-Rating Scorecard")
st.markdown("Correcting public score compression and evaluating actual green financing realization.")

# Data Engine Logic
data = [
    {
        "institution": "Standard Chartered Bank Kenya",
        "public_baseline_score": 8.5,
        "green_financing_KES_b": 55.0,
        "green_portfolio_share_pct": 28.0,
        "esdd_screened_KES_b": 620.0,
        "sdg_alignment_count": 14,
        "external_assurance_score": 9.5,
        "greenwashing_risk_variance_pct": -22.0
    },
    {
        "institution": "KCB Group Plc",
        "public_baseline_score": 8.2,
        "green_financing_KES_b": 48.8,
        "green_portfolio_share_pct": 25.84,
        "esdd_screened_KES_b": 587.7,
        "sdg_alignment_count": 14,
        "external_assurance_score": 9.2,
        "greenwashing_risk_variance_pct": -18.0
    },
    {
        "institution": "NCBA Bank Kenya PLC",
        "public_baseline_score": 8.2,
        "green_financing_KES_b": 12.0,
        "green_portfolio_share_pct": 12.0,
        "esdd_screened_KES_b": 150.0,
        "sdg_alignment_count": 9,
        "external_assurance_score": 8.0,
        "greenwashing_risk_variance_pct": -5.0
    }
]

df = pd.DataFrame(data)

# Scoring calculations
max_green_fin = df["green_financing_KES_b"].max()
max_share = df["green_portfolio_share_pct"].max()
max_esdd = df["esdd_screened_KES_b"].max()

df["pillar_green_finance"] = ((df["green_financing_KES_b"] / max_green_fin) * 0.5 + 
                               (df["green_portfolio_share_pct"] / max_share) * 0.5) * 10
df["pillar_esdd"] = (df["esdd_screened_KES_b"] / max_esdd) * 10
df["pillar_sdg"] = (df["sdg_alignment_count"] / 14.0) * 10
df["pillar_assurance"] = df["external_assurance_score"]

df["calibrated_composite_index"] = (
    (df["pillar_green_finance"] * 0.35) +
    (df["pillar_esdd"] * 0.30) +
    (df["pillar_sdg"] * 0.20) +
    (df["pillar_assurance"] * 0.15)
).round(2)

df["star_rating"] = df["calibrated_composite_index"].apply(
    lambda x: "5.0 Stars (Market Leader / Elite)" if x >= 8.5 else ("4.5 Stars (Advanced Performer)" if x >= 7.8 else "4.0 Stars (Strong Contender)")
)

df["greenwashing_risk_status"] = df["greenwashing_risk_variance_pct"].apply(
    lambda v: "VERY LOW Risk (-18% to -22% Audited Asset Variance)" if v <= -15.0 else "MODERATE Risk"
)

# Display table on Streamlit
st.dataframe(df[["institution", "public_baseline_score", "calibrated_composite_index", "star_rating", "greenwashing_risk_status"]], use_container_width=True)
