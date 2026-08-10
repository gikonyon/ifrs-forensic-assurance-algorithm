from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_pdf_report(results: Dict[str, Any]) -> bytes:
    """Generates an IFRS Forensic Assurance Report as a PDF byte stream."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=12
    )
    story.append(Paragraph("IFRS Forensic Assurance Verification Report", title_style))
    story.append(Paragraph("<b>Standard Alignment:</b> IFRS S1 (Governance) & IFRS S2 (Climate)", styles['Normal']))
    story.append(Spacer(1, 12))

    # Summary Table Data
    data = [
        ["Metric / Indicator", "Forensic Result"],
        ["Entity Name", str(results.get("entity_name", "Unknown"))],
        ["Reporting Period", str(results.get("reporting_period", "N/A"))],
        ["Assurance Risk State", str(results.get("assurance_risk_state", "N/A"))],
        ["Recalculated GHG Intensity", f"{results.get('recalculated_ghg_intensity', 0):.4f}"],
        ["Governance HHI", f"{results.get('governance_hhi', 0):.4f}"],
        ["Data Quality Score (DQS)", f"{results.get('data_quality', {}).get('score', 0)} ({results.get('data_quality', {}).get('tier', 'N/A')})"],
        ["Exceptions Detected", ", ".join(results.get("exceptions_detected", [])) or "None"],
        ["SHA-256 Evidence Hash", str(results.get("data_lineage_sha256", "N/A"))[:32] + "..."]
    ]

    t = Table(data, colWidths=[200, 340])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Notice:</b> This document is an automated research prototype report generated for transaction-level disclosure verification.", styles['Italic']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
