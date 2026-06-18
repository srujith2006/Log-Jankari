from pathlib import Path

from reportlab.platypus import *
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from map_generator import choose_best_hospital

REPORT_DIR = Path("reports")
REPORT_PATH = REPORT_DIR / "survivor_report.pdf"

def generate_report(survivors):

    REPORT_DIR.mkdir(exist_ok=True)

    doc = SimpleDocTemplate(
        str(REPORT_PATH)
    )

    styles = getSampleStyleSheet()

    elements = []
    
    elements.append(Paragraph("Survivor Detection Report", styles['Heading1']))
    elements.append(Paragraph("Images Enhanced for Clarity", styles['Italic']))
    elements.append(Spacer(1, 12))

    for s in survivors:

        voice_only = s.get("voice_detected", False)
        details = (
            f"<b>Position</b><br/>"
            f"Latitude: {s['latitude']}<br/>"
            f"Longitude: {s['longitude']}<br/><br/>"
            f"<b>Direction</b>: {s.get('direction', 'N/A')}<br/>"
            f"<b>Posture</b>: {s.get('posture', 'N/A')}<br/>"
            f"<b>Confidence</b>: {s.get('confidence', 'N/A')}"
        )

        if voice_only:
            details += (
                "<br/><br/><b>Note:</b> Voice-only detection. "
                "This entry is highlighted separately and is excluded from hospital selection."
            )

        survivor_table = Table(
            [
                [
                    Image(
                        s["image"],
                        width=200,
                        height=200
                    ),
                    Paragraph(details, styles['Normal'])
                ]
            ],
            colWidths=[210, 260],
            hAlign='LEFT'
        )

        survivor_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke if voice_only else colors.white),
        ]))

        elements.append(Paragraph(f"Survivor ID: {s.get('survivor_id', 'N/A')}", styles['Heading3']))
        elements.append(Spacer(1, 6))
        elements.append(survivor_table)
        elements.append(Spacer(1, 12))

    confirmed_survivors = [s for s in survivors if not s.get("voice_detected")]
    hospital_choice = choose_best_hospital(confirmed_survivors)
    if hospital_choice:
        hospital = hospital_choice['hospital']
        summary = (
            f"The selected hospital for all confirmed survivors is <b>{hospital['name']}</b>. "
            f"This selected hospital ignores voice-only detections, and was chosen because it minimizes the farthest distance any "
            f"confirmed survivor must travel. The farthest confirmed survivor is {hospital_choice['max_distance_km']:.2f} km away, "
            f"with an average confirmed survivor distance of {hospital_choice['avg_distance_km']:.2f} km."
        )

        elements.append(PageBreak())
        elements.append(Paragraph("Hospital Selection Summary", styles['Heading2']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(summary, styles['Normal']))

    doc.build(elements)
