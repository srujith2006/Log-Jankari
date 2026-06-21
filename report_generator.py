from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.platypus import *
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from disaster_analysis import build_disaster_analysis, describe_area, describe_weather
from map_generator import choose_best_hospital

REPORT_DIR = Path("reports")
REPORT_PATH = REPORT_DIR / "survivor_report.pdf"
FALLBACK_IMAGE = Path("unknown.jpg")

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

        details = (
            f"<b>Position</b><br/>"
            f"Latitude: {s['latitude']}<br/>"
            f"Longitude: {s['longitude']}<br/><br/>"
            f"<b>Direction</b>: {s.get('direction', 'N/A')}<br/>"
            f"<b>Posture</b>: {s.get('posture', 'N/A')}<br/>"
            f"<b>Confidence</b>: {s.get('confidence', 'N/A')}"
        )

        survivor_table = Table(
            [
                [
                    Image(
                        get_report_image_path(s.get("image")),
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
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))

        elements.append(Paragraph(f"Survivor ID: {s.get('survivor_id', 'N/A')}", styles['Heading3']))
        elements.append(Spacer(1, 6))
        elements.append(survivor_table)
        elements.append(Spacer(1, 12))

    add_disaster_analysis(elements, styles, survivors)

    hospital_choice = choose_best_hospital(survivors)
    if hospital_choice:
        hospital = hospital_choice['hospital']
        summary = (
            f"The selected hospital for all confirmed survivors is <b>{hospital['name']}</b>. "
            f"It was chosen because it minimizes the farthest distance any survivor must travel. "
            f"The farthest survivor is {hospital_choice['max_distance_km']:.2f} km away, "
            f"with an average survivor distance of {hospital_choice['avg_distance_km']:.2f} km."
        )

        elements.append(PageBreak())
        elements.append(Paragraph("Hospital Selection Summary", styles['Heading2']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(summary, styles['Normal']))

    doc.build(elements)


def get_report_image_path(image_path):
    if image_path and Path(image_path).exists():
        return image_path

    return str(FALLBACK_IMAGE)


def add_disaster_analysis(elements, styles, survivors):
    analysis = build_disaster_analysis(survivors)

    elements.append(PageBreak())
    elements.append(Paragraph("Climate and Area Disaster Analysis", styles['Heading2']))
    elements.append(Spacer(1, 12))

    if not analysis.get("available"):
        elements.append(Paragraph(escape(analysis["summary"]), styles['Normal']))
        return

    location = (
        f"Analysis location: {analysis['latitude']:.6f}, {analysis['longitude']:.6f}. "
        "This is the average valid GPS position from detected survivor records."
    )

    rows = [
        ["Question", "PDF Summary"],
        ["1. Disastrous history", analysis["history"]],
        ["Area and soil context", analysis["soil_area_summary"]],
        [
            "2. Climate + area possibility",
            (
                f"{analysis['likely_event']} Weather: {describe_weather(analysis.get('weather'))} "
                f"Area: {describe_area(analysis.get('area'))}"
            ),
        ],
        ["3. Man-made prediction", analysis["man_made"]],
        ["Final prediction", analysis["disaster_type_prediction"]],
    ]
    if analysis.get("gemini_note"):
        rows.append(["Gemini source note", analysis["gemini_note"]])

    table = Table(
        [
            [
                Paragraph(f"<b>{escape(str(row[0]))}</b>", styles['Normal']),
                Paragraph(escape(str(row[1])), styles['Normal']),
            ]
            for row in rows
        ],
        colWidths=[150, 320],
        hAlign='LEFT',
    )
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
    ]))

    elements.append(Paragraph(escape(location), styles['Italic']))
    elements.append(Spacer(1, 8))
    elements.append(table)
