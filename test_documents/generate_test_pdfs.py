import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

os.makedirs(r"d:\c drive\OneDrive\Desktop\Avtaar\test_documents", exist_ok=True)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontSize=20,
    leading=24,
    textColor=colors.HexColor('#1E293B'),
    spaceAfter=12
)

h2_style = ParagraphStyle(
    'DocH2',
    parent=styles['Heading2'],
    fontSize=14,
    leading=18,
    textColor=colors.HexColor('#0F172A'),
    spaceBefore=10,
    spaceAfter=6
)

body_style = ParagraphStyle(
    'DocBody',
    parent=styles['Normal'],
    fontSize=10,
    leading=14,
    textColor=colors.HexColor('#334155'),
    spaceAfter=6
)

# 1. HR Employee Handbook
doc1 = SimpleDocTemplate(
    r"d:\c drive\OneDrive\Desktop\Avtaar\test_documents\HR_Employee_Handbook_2026.pdf",
    pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
)
story1 = []
story1.append(Paragraph("Acme Corp — Global Employee Handbook & Benefits Guide (2026)", title_style))
story1.append(Spacer(1, 10))

story1.append(Paragraph("1. Paid Time Off (PTO) & Leave Policy", h2_style))
story1.append(Paragraph("Full-time employees accrue <b>24 days of Paid Time Off (PTO)</b> per calendar year, accrued at 2.0 days per month. Up to 5 unused PTO days can be rolled over to the subsequent calendar year. PTO requests exceeding 3 consecutive business days must be submitted at least 14 days in advance via the HR Portal.", body_style))
story1.append(Paragraph("<b>Sick Leave:</b> Employees receive 10 paid sick days per year. For absences exceeding 3 consecutive business days, a verified medical certificate from a licensed physician is required.", body_style))
story1.append(Paragraph("<b>Parental Leave:</b> Primary caregivers are eligible for 16 weeks of 100% paid parental leave. Secondary caregivers receive 6 weeks of 100% paid leave, applicable within the first 12 months of birth or adoption.", body_style))

story1.append(Paragraph("2. Remote Work & Flexible Hours", h2_style))
story1.append(Paragraph("Acme Corp operates on a hybrid model. Core collaboration hours are <b>10:00 AM to 4:00 PM EST</b>. Full-time remote employees receive a one-time home-office setup stipend of <b>$750 USD</b> and a monthly internet reimbursement of <b>$60 USD</b> submitted via Expensify.", body_style))

story1.append(Paragraph("3. Health Benefits & Wellness Stipend", h2_style))
story1.append(Paragraph("Comprehensive health, dental, and vision insurance begins on the first day of the calendar month following employment. Employees are also eligible for an annual <b>$500 USD wellness reimbursement</b> covering gym memberships, mental health counseling, fitness equipment, or ergonomic gear.", body_style))

story1.append(Paragraph("4. Travel & Expense Reimbursement Policy", h2_style))
story1.append(Paragraph("Business travel meals are reimbursed up to a per diem maximum of <b>$75 USD per day</b>. Flights exceeding 6 hours in duration are eligible for Premium Economy upgrades. Expense receipts must be submitted within 30 days of expense incurring.", body_style))

doc1.build(story1)

# 2. Cloud API Technical Specification
doc2 = SimpleDocTemplate(
    r"d:\c drive\OneDrive\Desktop\Avtaar\test_documents\Cloud_API_Technical_Specification.pdf",
    pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
)
story2 = []
story2.append(Paragraph("ApexCloud REST API v3 — Developer Integration Guide", title_style))
story2.append(Spacer(1, 10))

story2.append(Paragraph("1. Authentication & API Keys", h2_style))
story2.append(Paragraph("All API requests must include a Bearer token in the HTTP Authorization header: <code>Authorization: Bearer apex_live_key_xyz</code>. API keys must never be exposed on client-side frontend code. Requests without valid tokens return HTTP 401 with error code <b>ERR-401-AUTH</b>.", body_style))

story2.append(Paragraph("2. Rate Limits & Quotas", h2_style))
story2.append(Paragraph("Standard Developer Tier is rate-limited to <b>100 requests per minute</b> and 10,000 requests per calendar day. Enterprise Tier accounts have a dedicated limit of <b>1,000 requests per minute</b>. When limits are exceeded, the API responds with HTTP 429 and includes a <code>Retry-After</code> response header.", body_style))

story2.append(Paragraph("3. Diagnostic Error Code Catalog", h2_style))
table_data = [
    ["Error Code", "HTTP Status", "Trigger Condition", "Recommended Resolution"],
    ["ERR-401-AUTH", "401", "Missing or expired API token", "Regenerate token in Developer Console"],
    ["ERR-904-SYNTAX", "422", "Invalid JSON payload structure", "Validate request body against OpenAPI spec"],
    ["ERR-904-TIMEOUT", "504", "Downstream microservice timeout", "Implement exponential backoff retry (3x)"],
    ["ERR-503-MAINT", "503", "Scheduled system maintenance window", "Check status.apexcloud.io for live updates"]
]
t = Table(table_data, colWidths=[110, 70, 180, 170])
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,0), 9),
    ('BOTTOMPADDING', (0,0), (-1,0), 6),
    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ('FONTSIZE', (0,1), (-1,-1), 8),
]))
story2.append(t)
story2.append(Spacer(1, 10))

story2.append(Paragraph("4. Webhook Event Notifications", h2_style))
story2.append(Paragraph("ApexCloud delivers asynchronous event notifications for <code>order.created</code>, <code>payment.succeeded</code>, and <code>ticket.resolved</code>. Webhook signatures must be verified using HMAC-SHA256 with your endpoint secret header <code>X-Apex-Signature</code>.", body_style))

doc2.build(story2)

# 3. Customer Support & Refund Policy
doc3 = SimpleDocTemplate(
    r"d:\c drive\OneDrive\Desktop\Avtaar\test_documents\Customer_Support_Refund_Policy.pdf",
    pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
)
story3 = []
story3.append(Paragraph("Global Retail Solutions — Customer Support & Refund Policy", title_style))
story3.append(Spacer(1, 10))

story3.append(Paragraph("1. 30-Day Return & Refund Guarantee", h2_style))
story3.append(Paragraph("Customers may initiate a return for any unopened or undamaged item within <b>30 days of confirmed delivery</b>. Return shipping labels are provided free of charge for domestic orders. Once the returned item is inspected at our fulfillment center, refunds are processed within <b>3 to 5 business days</b> back to the original payment method.", body_style))

story3.append(Paragraph("2. Damaged or Defective Deliveries", h2_style))
story3.append(Paragraph("If an order arrives damaged, defective, or incorrect, customers must report the issue within <b>7 days of delivery</b> with photo evidence. Customer support agents will immediately dispatch a priority replacement order at zero extra charge, or issue a 100% store credit voucher.", body_style))

story3.append(Paragraph("3. Support Ticket Escalation Tiers & SLA", h2_style))
story3.append(Paragraph("<b>Tier 1 (Standard General Inquiries):</b> First response SLA within 4 hours.<br/><b>Tier 2 (Billing & Order Disputes):</b> Resolution SLA within 24 hours.<br/><b>Tier 3 (Enterprise Critical Escalations):</b> Dedicated account manager SLA within 1 hour.", body_style))

story3.append(Paragraph("4. Order Tracking & Cancellation Window", h2_style))
story3.append(Paragraph("Orders may be cancelled free of charge within <b>60 minutes of placement</b> before the fulfillment warehouse begins picking. After 60 minutes, orders cannot be cancelled and must follow the standard return process upon delivery.", body_style))

doc3.build(story3)

print("All 3 test PDFs successfully generated in d:\\c drive\\OneDrive\\Desktop\\Avtaar\\test_documents")
