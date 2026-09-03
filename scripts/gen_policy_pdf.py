import csv
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER

OUT_PATH = "/Users/asmitha/Downloads/expense_compliance_project/data/raw/policies/Corporate_Expense_Policy.pdf"
CSV_PATH = "/Users/asmitha/Downloads/expense_compliance_project/data/processed/expense_policies.csv"

with open(CSV_PATH) as f:
    rows = list(csv.DictReader(f))

# group by (source_section major number rounded to section, source_heading) preserving order
sections = []
seen_headings = []
for r in rows:
    heading = r["source_heading"]
    if heading not in seen_headings:
        seen_headings.append(heading)
        sections.append({"heading": heading, "items": []})
    for s in sections:
        if s["heading"] == heading:
            s["items"].append(r)
            break

styles = getSampleStyleSheet()
title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], alignment=TA_CENTER)
subtitle_style = ParagraphStyle("SubtitleStyle", parent=styles["Normal"], alignment=TA_CENTER, fontSize=11, textColor="#444444")
h1 = ParagraphStyle("H1", parent=styles["Heading1"], spaceBefore=14, spaceAfter=6)
h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=10, spaceAfter=4, fontSize=12)
body = ParagraphStyle("Body", parent=styles["BodyText"], spaceAfter=10, leading=15)

doc = SimpleDocTemplate(OUT_PATH, pagesize=A4, topMargin=2.2 * cm, bottomMargin=2.2 * cm,
                         leftMargin=2.2 * cm, rightMargin=2.2 * cm)
story = []

story.append(Spacer(1, 3 * cm))
story.append(Paragraph("Meridian Holdings Pte. Ltd.", title_style))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph("Corporate Expense Reimbursement Policy", title_style))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph("Effective 1 September 2026 &nbsp;|&nbsp; Singapore Operations &nbsp;|&nbsp; Version 2.0", subtitle_style))
story.append(PageBreak())

story.append(Paragraph("1. Purpose and Scope", h1))
story.append(Paragraph(
    "This document sets out the standards under which Meridian Holdings Pte. Ltd. repays staff for "
    "costs reasonably incurred in the course of their duties. It applies to all employees of the "
    "Singapore operating entity. Claims are assessed against the sections below; where a cost is not "
    "addressed by any section, the claim is referred to Finance Review for a manual determination. "
    "This document is reviewed periodically by the Finance function and supersedes all prior versions "
    "of the corporate expense policy from its stated effective date.",
    body))

story.append(Paragraph("2. Definitions", h1))
story.append(Paragraph(
    "For the purposes of this document, the following terms carry the meanings set out below "
    "wherever they appear, unless the context plainly requires otherwise.",
    body))
definitions = [
    ("Claimant", "The employee of the Singapore operating entity submitting a request for reimbursement under this document."),
    ("Sanctioned", "Approved in advance, or otherwise falling within a category of activity this document treats as approved by default, in connection with the Claimant's duties."),
    ("Supervisor", "The Claimant's direct line manager, or another individual holding equivalent authorisation authority for the Claimant at the relevant time."),
    ("Finance", "The Finance function of Meridian Holdings Pte. Ltd., responsible for processing, reviewing, and where necessary escalating claims made under this document."),
    ("Finance Review", "The manual review process conducted by Finance for a claim that cannot be reliably resolved by reference to this document alone."),
    ("Home Currency", "Singapore Dollars (SGD), the currency in which Meridian Holdings Pte. Ltd. reports and reimburses claims by default."),
    ("Repayable / Repayment", "Eligible for reimbursement to the Claimant, subject to satisfying the applicable conditions set out in this document."),
]
for term, definition in definitions:
    story.append(Paragraph(f"<b>{term}.</b> {definition}", body))

story.append(Paragraph("3. Submission Standards and Evidence", h1))
for r in [r for r in rows if r["source_heading"] == "Submission standards and evidence"]:
    story.append(Paragraph(f"{r['source_section']} {r['title']}", h2))
    story.append(Paragraph(r["policy_text"], body))

section_order = [
    "Meals, client hospitality and entertainment",
    "Air travel",
    "Hotels and accommodation",
    "Ground transport and local travel",
    "Client entertainment",
    "Training, conferences and professional development",
    "Parking, tolls and related road charges",
    "Office equipment and workplace purchases",
    "Software and digital services",
    "Business gifts and promotional items",
    "Foreign currency and exchange-rate handling",
    "Weekend, public-holiday and after-hours claims",
    "Mixed business and personal receipts",
    "Missing, unreadable, duplicate and altered receipts",
    "Relocation and mobility",
    "Staff benefits and wellbeing",
    "Community and charitable contributions",
]

for heading in section_order:
    items = [r for r in rows if r["source_heading"] == heading]
    if not items:
        continue
    story.append(Paragraph(heading, h1))
    for r in items:
        story.append(Paragraph(f"{r['source_section']} {r['title']}", h2))
        story.append(Paragraph(r["policy_text"], body))

story.append(Paragraph("17. Escalation and Exceptions", h1))
story.append(Paragraph(
    "Where the available evidence or the sections above do not support a reliable determination, or "
    "where two sections of this policy appear to conflict for the same claim, the claim is escalated "
    "to Finance Review for a manual decision. No section of this policy may be applied by inference "
    "to a cost it does not address.",
    body))

doc.build(story)
print("wrote", OUT_PATH)
