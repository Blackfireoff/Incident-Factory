# services/pdf_service.py

import io
from typing import List, Dict, Any
import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
import re

# --- Fonction Header/Footer pour ReportLab ---
def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    
    # En-tête (TRADUIT)
    header_text = "Incident Report - FireTeams"
    canvas.drawString(inch, A4[1] - 0.5 * inch, header_text) # A4[1] est la hauteur
    
    # Pied de page (Numéro de page)
    page_num_text = f"Page {doc.page}"
    canvas.drawRightString(A4[0] - inch, 0.5 * inch, page_num_text) # A4[0] est la largeur
    canvas.restoreState()
# --- Fin de la fonction ---


def create_report_pdf(title: str, query: str, data: Dict[str, Any]) -> bytes:
    """
    Génère un rapport PDF (tableau) en utilisant ReportLab.
    """
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.75*inch, bottomMargin=0.75*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
    story = []
    
    # Configuration des styles (utilise les polices de base)
    styles = getSampleStyleSheet()
    styles['Title'].fontName = 'Helvetica-Bold'
    styles['Title'].fontSize = 16
    styles['Title'].spaceAfter = 12
    styles['Heading2'].fontName = 'Helvetica-Bold'
    styles['Heading2'].fontSize = 12
    styles['Heading2'].spaceAfter = 6
    styles['Heading2'].spaceBefore = 12
    styles['Code'].fontName = 'Courier'
    styles['Code'].fontSize = 8
    styles['Code'].borderWidth = 1
    styles['Code'].borderColor = colors.grey
    styles['Code'].padding = 5
    styles['Code'].spaceAfter = 12
    styles['BodyText'].fontName = 'Helvetica'
    styles['BodyText'].fontSize = 9
    styles.add(ParagraphStyle(name='SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.grey, spaceAfter=12))
    
    # Ajout du contenu (TRADUIT)
    story.append(Paragraph(title, styles['Title']))
    story.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['SubTitle']))
    story.append(Paragraph('Data Query', styles['Heading2']))
    story.append(Paragraph(query, styles['Code']))
    story.append(Paragraph('Results', styles['Heading2']))

    columns = data.get('columns', [])
    rows = data.get('rows', [])

    if not rows:
        story.append(Paragraph('No data found for this query.', styles['BodyText']))
    elif not columns:
        story.append(Paragraph('Data received but columns are undefined.', styles['BodyText']))
    else:
        # Construction du tableau
        table_data = [columns]
        for row in rows:
            row_data = []
            for col in columns:
                cell_value = str(row.get(col, ''))
                if col == 'description' and len(cell_value) > 100:
                    cell_value = cell_value[:100] + '...'
                row_data.append(cell_value)
            table_data.append(row_data)

        t = Table(table_data, repeatRows=1)
        
        # Style du tableau
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t)

    # Construire le PDF avec la fonction header/footer
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def create_text_report_pdf(title: str, content: str) -> bytes:
    """
    Génère un rapport PDF (texte) en utilisant ReportLab.
    """
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    story = []
    
    # Configuration des styles
    styles = getSampleStyleSheet()
    styles['Title'].fontName = 'Helvetica-Bold'
    styles['Title'].fontSize = 16
    styles['Title'].spaceAfter = 12
    styles['BodyText'].fontName = 'Helvetica'
    styles['BodyText'].fontSize = 10
    styles['BodyText'].spaceAfter = 6
    styles['BodyText'].leading = 14
    styles.add(ParagraphStyle(name='SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.grey, spaceAfter=12))
    
    # Ajout du contenu (TRADUIT)
    story.append(Paragraph(title, styles['Title']))
    story.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['SubTitle']))
    story.append(Spacer(1, 0.25*inch))
    
    # Nettoyage du Markdown pour ReportLab
    content_html = content.replace('\n\n', '<br/><br/>')
    content_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content_html)

    lines = content_html.split('<br/><br/>')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('* '):
            formatted_line = f"• {line.lstrip('* ')}"
            story.append(Paragraph(formatted_line, styles['BodyText']))
            story.append(Spacer(1, 2))
        else:
            story.append(Paragraph(line, styles['BodyText']))
            story.append(Spacer(1, 6))

    # Construire le PDF avec la fonction header/footer
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes