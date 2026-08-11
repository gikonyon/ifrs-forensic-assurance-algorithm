# ==========================================
# Unified Application: app.py
# Combines Flask routing and the Advanced ESG Forensic Engine
# ==========================================

from flask import Flask, jsonify, render_template_string
import pandas as pd
import numpy as np

app = Flask(__name__)

class AdvancedESFForensicEngine:
    def __init__(self, custom_data: pd.DataFrame = None):
        """
        Advanced ESG Forensic & Star-Rating Evaluation Engine.
        Corrects public score compression, assigns star ratings, and tracks greenwashing variance.
        """
        if custom_data is not None:
            self.df = custom_data
        else:
            self.df = pd.DataFrame([
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
            ])

    def execute_forensic_evaluation(self) -> pd.DataFrame:
        df = self.df.copy()
        
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
        
        def map_star_rating(score):
            if score >= 8.5:
                return "5.0 Stars (Market Leader / Elite)"
            elif score >= 7.8:
                return "4.5 Stars (Advanced Performer)"
            else:
                return "4.0 Stars (Strong Contender)"
                
        df["star_rating"] = df["calibrated_composite_index"].apply(map_star_rating)
        
        def map_greenwashing_risk(variance):
            if variance <= -15.0:
                return "VERY LOW Risk (-18% to -22% Audited Asset Variance)"
            elif variance <= -8.0:
                return "LOW Risk (Moderate Assurance)"
            else:
                return "MODERATE Risk (Target-Dependent Baseline)"
                
        df["greenwashing_risk_status"] = df["greenwashing_risk_variance_pct"].apply(map_greenwashing_risk)
        return df

    def generate_gap_report(self, target: str, benchmark: str = "KCB Group Plc") -> dict:
        res_df = self.execute_forensic_evaluation()
        t_row = res_df[res_df["institution"] == target].iloc[0]
        b_row = res_df[res_df["institution"] == benchmark].iloc[0]
        
        return {
            "target_institution": target,
            "benchmark_institution": benchmark,
            "composite_index_gap": round(b_row["calibrated_composite_index"] - t_row["calibrated_composite_index"], 2),
            "green_financing_gap_KES_b": round(b_row["green_financing_KES_b"] - t_row["green_financing_KES_b"], 2),
            "portfolio_share_gap_pct": round(b_row["green_portfolio_share_pct"] - t_row["green_portfolio_share_pct"], 2),
            "esdd_screening_gap_KES_b": round(b_row["esdd_screened_KES_b"] - t_row["esdd_screened_KES_b"], 2)
        }

@app.route("/")
def index():
    engine = AdvancedESFForensicEngine()
    scorecard = engine.execute_forensic_evaluation()
    return render_template_string("""
        <html>
            <head><title>ESG Forensic Dashboard</title></head>
            <body style="font-family: Arial, sans-serif; margin: 40px; background-color: #f9f9f9;">
                <h2>Institutional ESG Forensic & Star-Rating Scorecard</h2>
                <p>Correcting public score compression and evaluating actual green financing realization.</p>
                <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; background: #fff; width: 100%;">
                    <tr style="background: #004d40; color: #fff;">
                        <th>Institution</th>
                        <th>Public Baseline</th>
                        <th>Calibrated Index</th>
                        <th>Star Rating</th>
                        <th>Greenwashing Risk Status</th>
                    </tr>
                    {% for row in data %}
                    <tr>
                        <td><b>{{ row.institution }}</b></td>
                        <td>{{ row.public_baseline_score }}</td>
                        <td>{{ row.calibrated_composite_index }}</td>
                        <td><span style="color: #d32f2f;"><b>{{ row.star_rating }}</b></span></td>
                        <td>{{ row.greenwashing_risk_status }}</td>
                    </tr>
                    {% endfor %}
                </table>
                <br>
                <h3>API Endpoints Available:</h3>
                <ul>
                    <li><code>GET /api/esg/scorecard</code> - JSON output of full institutional scorecard</li>
                    <li><code>GET /api/esg/gaps/NCBA%20Bank%20Kenya%20PLC</code> - JSON output of quantitative gaps vs benchmark</li>
                </ul>
            </body>
        </html>
    """, data=scorecard.to_dict(orient="records"))

@app.route("/api/esg/scorecard", methods=["GET"])
def api_scorecard():
    engine = AdvancedESFForensicEngine()
    return jsonify(engine.execute_forensic_evaluation().to_dict(orient="records"))

@app.route("/api/esg/gaps/<target_bank>", methods=["GET"])
def api_gaps(target_bank):
    engine = AdvancedESFForensicEngine()
    return jsonify(engine.generate_gap_report(target_bank))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
