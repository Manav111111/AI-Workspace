import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

os.makedirs(r"d:\c drive\OneDrive\Desktop\Avtaar\test_documents", exist_ok=True)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontSize=18,
    leading=22,
    textColor=colors.HexColor('#0F172A'),
    spaceAfter=8
)

subtitle_style = ParagraphStyle(
    'DocSubTitle',
    parent=styles['Normal'],
    fontSize=10,
    leading=13,
    textColor=colors.HexColor('#64748B'),
    spaceAfter=14
)

h1_style = ParagraphStyle(
    'DocH1',
    parent=styles['Heading2'],
    fontSize=13,
    leading=16,
    textColor=colors.HexColor('#1E293B'),
    spaceBefore=12,
    spaceAfter=4
)

h2_style = ParagraphStyle(
    'DocH2',
    parent=styles['Heading3'],
    fontSize=10,
    leading=13,
    textColor=colors.HexColor('#334155'),
    spaceBefore=8,
    spaceAfter=3
)

body_style = ParagraphStyle(
    'DocBody',
    parent=styles['Normal'],
    fontSize=8.5,
    leading=11.5,
    textColor=colors.HexColor('#334155'),
    spaceAfter=4
)

bullet_style = ParagraphStyle(
    'DocBullet',
    parent=styles['Normal'],
    fontSize=8.5,
    leading=11.5,
    textColor=colors.HexColor('#334155'),
    leftIndent=12,
    spaceAfter=3
)

def make_table(data, col_widths, bg_header='#0F172A'):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(bg_header)),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 4),
        ('TOPPADDING', (0,0), (-1,0), 4),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTSIZE', (0,1), (-1,-1), 7.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,1), (-1,-1), 3),
        ('TOPPADDING', (0,1), (-1,-1), 3),
    ]))
    return t

# =========================================================================
# 1. HR & People Operations Comprehensive Manual (Multi-Page)
# =========================================================================
doc1 = SimpleDocTemplate(
    r"d:\c drive\OneDrive\Desktop\Avtaar\test_documents\HR_Employee_Handbook_2026.pdf",
    pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
)
s1 = []
s1.append(Paragraph("Acme Global Technologies — Comprehensive People Operations & HR Policy Manual (2026)", title_style))
s1.append(Paragraph("Version 4.2 • Effective Date: January 1, 2026 • Applies to all Full-Time, Part-Time, and Contract Employees", subtitle_style))

# Chapter 1: Compensation & Payroll
s1.append(Paragraph("Chapter 1: Compensation, Payroll & Performance Bonuses", h1_style))
s1.append(Paragraph("<b>1.1 Payroll Schedule & Direct Deposit:</b> Salaries are disbursed semi-monthly on the 15th and the final business day of each month. If a pay date falls on a weekend or federal holiday, disbursement occurs on the preceding business day.", body_style))
s1.append(Paragraph("<b>1.2 Performance Review Cycle & Merit Increases:</b> Formal performance reviews take place bi-annually in June and December. Merit salary increases range from 3.0% to 9.5% based on employee rating (Exceeds Expectations, Consistently Meets, Needs Improvement).", body_style))
s1.append(Paragraph("<b>1.3 Annual Discretionary Bonus Tiers:</b> Bonus targets are tied to individual performance and company ARR growth:", body_style))

bonus_data = [
    ["Level / Role", "Target Bonus (% of Base)", "Eligibility Window", "Payout Date"],
    ["L1–L3 (Associate / Mid-Level)", "10% – 15%", "Completed 6 months continuous tenure", "March 15th"],
    ["L4–L6 (Senior / Staff / Lead)", "18% – 25%", "Completed 6 months continuous tenure", "March 15th"],
    ["L7+ (Director / VP / Exec)", "30% – 50% + Equity Grant", "Annual performance milestone review", "March 15th"]
]
s1.append(make_table(bonus_data, [130, 130, 160, 100]))
s1.append(Spacer(1, 6))

# Chapter 2: Leaves, PTO & Public Holidays
s1.append(Paragraph("Chapter 2: Leaves, Paid Time Off (PTO) & Holiday Calendar", h1_style))
s1.append(Paragraph("<b>2.1 Annual PTO Accrual:</b> Full-time employees accrue <b>24 days of Paid Time Off (PTO)</b> per year (2.0 days per completed month). Part-time employees accrue 12 days prorated. Employees can carry over up to <b>5 unused PTO days</b> into the next calendar year; remaining days expire on Dec 31st.", body_style))
s1.append(Paragraph("<b>2.2 PTO Request Lead Times:</b> Requests for 1–2 consecutive days require 48 hours notice. Requests for 3+ consecutive days must be submitted 14 calendar days in advance in BambooHR.", body_style))
s1.append(Paragraph("<b>2.3 Sick Leave & Medical Certificates:</b> Employees receive <b>10 paid sick days</b> annually (allotted Jan 1). For consecutive medical absences exceeding 3 business days, a signed medical certificate from a licensed doctor must be submitted to <code>hr-medical@acmeglobal.com</code> within 5 days of returning to work.", body_style))
s1.append(Paragraph("<b>2.4 Parental Leave:</b> Primary caregivers receive <b>16 weeks of 100% paid parental leave</b>. Secondary caregivers receive <b>6 weeks of 100% paid parental leave</b>. Applicable for birth, legal adoption, or long-term foster placement within the child's first 12 months.", body_style))
s1.append(Paragraph("<b>2.5 Bereavement Leave:</b> 5 consecutive paid days for immediate family members (spouse, child, parent, sibling); 3 consecutive paid days for extended family (grandparent, in-law).", body_style))
s1.append(Paragraph("<b>2.6 Sabbatical Leave:</b> Employees with 5+ years of continuous tenure are eligible to apply for an unpaid sabbatical of 1 to 3 months with guaranteed job preservation.", body_style))
s1.append(Paragraph("<b>2.7 Official Company Holidays (11 Days):</b> New Year's Day, Martin Luther King Jr. Day, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving Day, Day after Thanksgiving, Christmas Eve, Christmas Day, and 1 Floating Cultural Holiday.", body_style))

# Chapter 3: Remote Work & Stipends
s1.append(Paragraph("Chapter 3: Remote Work, Home Office & Equipment Stipends", h1_style))
s1.append(Paragraph("<b>3.1 Core Working Hours:</b> Core synchronous collaboration hours are <b>10:00 AM to 4:00 PM EST</b> (or local equivalent). All team members must be responsive on Slack during these hours.", body_style))
s1.append(Paragraph("<b>3.2 Home Office Setup Stipend:</b> Full-time remote employees receive a one-time non-taxable stipend of <b>$1,000 USD</b> on their first paycheck for ergonomic desks, monitors, and chairs. Receipts must be uploaded within 60 days.", body_style))
s1.append(Paragraph("<b>3.3 Monthly Internet & Mobile Reimbursement:</b> Remote employees are entitled to a monthly internet stipend of <b>$80 USD</b> and a mobile phone reimbursement of <b>$50 USD</b> for on-call personnel.", body_style))
s1.append(Paragraph("<b>3.4 Coworking Pass:</b> If an employee prefers a coworking space, the company provides a monthly WeWork / Regus hot-desk membership reimbursement up to <b>$250 USD per month</b>.", body_style))

# Chapter 4: Health Benefits & Wellness
s1.append(Paragraph("Chapter 4: Health, Dental, Vision & Wellness Benefits", h1_style))
s1.append(Paragraph("<b>4.1 Coverage Start Date:</b> Health benefits take effect on the 1st day of the calendar month following employment commencement (e.g., hire date Sept 15 ➔ coverage starts Oct 1).", body_style))
s1.append(Paragraph("<b>4.2 Plans Offered:</b> Cigna Premium PPO (80/20 in-network, $500 deductible) and Kaiser HDHP with $1,500 HSA company contribution.", body_style))
s1.append(Paragraph("<b>4.3 Annual Wellness Stipend:</b> Each employee receives a <b>$600 USD annual wellness allowance</b>. Reimbursable categories: gym memberships, yoga/Pilates classes, personal training, running shoes, mental health counseling apps (Headspace, BetterHelp), and massage therapy.", body_style))

# Chapter 5: Travel & Expense Reimbursement
s1.append(Paragraph("Chapter 5: Business Travel & Expense Policy", h1_style))
s1.append(Paragraph("<b>5.1 Daily Meal Per Diem:</b> Business travel meals are reimbursed up to <b>$85 USD per day</b> (Breakfast: $20, Lunch: $25, Dinner: $40). Alcohol is non-reimbursable unless client entertainment is pre-approved in writing by a VP.", body_style))
s1.append(Paragraph("<b>5.2 Flight & Accommodation Rules:</b> Domestic flights under 5 hours must be Economy class. International flights exceeding 6 continuous hours are eligible for Premium Economy or Business Class with VP approval. Hotels are capped at $250/night (Standard Tier cities) and $380/night (Tier 1 cities: NYC, SF, London, Tokyo).", body_style))
s1.append(Paragraph("<b>5.3 Expense Filing Deadline:</b> All expense reports must be submitted via Expensify within <b>30 days</b> of transaction incurrence. Receipts required for all expenses over $25.", body_style))

# Chapter 6: Resignation, Notice Periods & Offboarding
s1.append(Paragraph("Chapter 6: Resignation, Notice Periods & Offboarding", h1_style))
s1.append(Paragraph("<b>6.1 Notice Periods:</b> Standard employees (L1–L4) are required to provide <b>2 weeks (14 calendar days)</b> written notice. Senior staff, Managers, and Directors (L5+) must provide <b>4 weeks (30 calendar days)</b> notice.", body_style))
s1.append(Paragraph("<b>6.2 Payout of Accrued PTO:</b> All unused accrued PTO (up to the 24-day cap) is paid out on the final paycheck. Sick leave is non-compensable upon separation.", body_style))
s1.append(Paragraph("<b>6.3 Asset Return:</b> Company laptops (MacBook Pro/Dell XPS), security badges, and company credit cards must be returned via prepaid shipping box within <b>7 business days</b> of the last working day.", body_style))

doc1.build(s1)

# =========================================================================
# 2. Cloud API & Technical Specification Manual (Multi-Page)
# =========================================================================
doc2 = SimpleDocTemplate(
    r"d:\c drive\OneDrive\Desktop\Avtaar\test_documents\Cloud_API_Technical_Specification.pdf",
    pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
)
s2 = []
s2.append(Paragraph("ApexCloud REST API v3 & Enterprise Microservices Integration Guide", title_style))
s2.append(Paragraph("Technical Specification Document • API Version: 3.4.0 • Protocols: HTTPS / JSON / WebSockets / gRPC", subtitle_style))

s2.append(Paragraph("1. Authentication, Tokens & Key Rotation", h1_style))
s2.append(Paragraph("<b>1.1 Bearer Token Authorization:</b> All REST requests must supply a valid API key in the Authorization header: <code>Authorization: Bearer apex_live_sec_9941a...</code>. Requests omitting this header fail immediately with HTTP 401 Unauthorized.", body_style))
s2.append(Paragraph("<b>1.2 JWT Token Lifetime:</b> User session JWT tokens have a maximum validity window of <b>1,440 minutes (24 hours)</b>. Refresh tokens rotate every 7 days.", body_style))
s2.append(Paragraph("<b>1.3 Key Rotation Policy:</b> Enterprise API keys must be rotated at least once every 90 days. During key rotation, ApexCloud supports a 48-hour grace period where both the old and new API keys are accepted simultaneously.", body_style))

s2.append(Paragraph("2. Rate Limits, Bursting & Concurrency Quotas", h1_style))
s2.append(Paragraph("Rate limiting is enforced globally using a Redis token-bucket algorithm partitioned by API Key and Client IP:", body_style))

rate_data = [
    ["Tier", "Rate Limit (Req/Min)", "Burst Allowance", "Daily Max Limit", "Concurrent WS Conns"],
    ["Developer (Free)", "60 req/min", "10 requests", "5,000 req/day", "2 connections"],
    ["Professional Tier", "300 req/min", "50 requests", "50,000 req/day", "10 connections"],
    ["Enterprise Dedicated", "2,000 req/min", "250 requests", "1,000,000 req/day", "100 connections"]
]
s2.append(make_table(rate_data, [100, 100, 100, 110, 110]))
s2.append(Spacer(1, 6))
s2.append(Paragraph("When rate limits are exceeded, the server returns HTTP 429 Too Many Requests with headers: <code>X-RateLimit-Limit</code>, <code>X-RateLimit-Remaining: 0</code>, and <code>Retry-After: <seconds></code>.", body_style))

s2.append(Paragraph("3. Master Diagnostic Error Code Catalog", h1_style))
error_data = [
    ["Error Code", "HTTP Status", "Root Cause Trigger", "Corrective Action & Resolution"],
    ["ERR-401-AUTH", "401", "Missing, expired, or revoked API Bearer token", "Generate a new API key in ApexCloud Console."],
    ["ERR-403-TENANT", "403", "Cross-tenant resource access violation attempt", "Verify resource ID belongs to your authenticated company_id."],
    ["ERR-422-SCHEMA", "422", "Pydantic payload schema validation failure", "Inspect request JSON body against OpenAPI required fields."],
    ["ERR-904-SYNTAX", "422", "Malformed JSON syntax or invalid UTF-8 encoding", "Ensure body is valid JSON with application/json header."],
    ["ERR-904-TIMEOUT", "504", "Upstream vector/LLM microservice timeout (>60s)", "Retry with exponential backoff; reduce context top_k."],
    ["ERR-503-MAINT", "503", "Scheduled platform database maintenance window", "Check https://status.apexcloud.io for live updates."],
    ["ERR-808-BUDGET", "429", "Tenant monthly token budget hard limit reached", "Upgrade monthly budget cap in Usage & Budgets panel."]
]
s2.append(make_table(error_data, [85, 55, 180, 200]))
s2.append(Spacer(1, 6))

s2.append(Paragraph("4. Idempotency & Safe Request Retries", h1_style))
s2.append(Paragraph("For all state-mutating POST/PUT requests (e.g. <code>/orders/create</code>, <code>/tickets/submit</code>), clients must pass an <code>Idempotency-Key: <UUIDv4></code> header. ApexCloud caches idempotency responses for <b>24 hours</b>. Retrying a request with the identical key returns the cached response without creating duplicate database records.", body_style))

s2.append(Paragraph("5. Webhooks & Asynchronous Event Subscriptions", h1_style))
s2.append(Paragraph("ApexCloud delivers webhooks for events: <code>order.created</code>, <code>order.delivered</code>, <code>ticket.escalated</code>, <code>payment.succeeded</code>. Webhooks retry with exponential backoff (5 attempts over 2 hours). Clients must verify the HMAC-SHA256 signature in the <code>X-Apex-Signature</code> header using their webhook signing secret.", body_style))

doc2.build(s2)

# =========================================================================
# 3. Customer Support, Order Processing & Return SLA Manual (Multi-Page)
# =========================================================================
doc3 = SimpleDocTemplate(
    r"d:\c drive\OneDrive\Desktop\Avtaar\test_documents\Customer_Support_Refund_Policy.pdf",
    pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
)
s3 = []
s3.append(Paragraph("Global Retail Solutions — Customer Support, Order Management & Refund SLA Manual", title_style))
s3.append(Paragraph("Standard Operating Procedures (SOP) • Customer Care Operations Guide 2026", subtitle_style))

s3.append(Paragraph("1. Order Lifecycles & State Transitions", h1_style))
s3.append(Paragraph("Every order transitions through defined states: <b>PENDING</b> ➔ <b>PROCESSING</b> (warehouse picking) ➔ <b>SHIPPED</b> ➔ <b>IN_TRANSIT</b> ➔ <b>OUT_FOR_DELIVERY</b> ➔ <b>DELIVERED</b>.", body_style))
s3.append(Paragraph("<b>1.1 Cancellation Window:</b> Customers can cancel an order free of charge within <b>60 minutes of placement</b> while in PENDING status. Once status changes to PROCESSING, cancellation is locked and the customer must initiate a return post-delivery.", body_style))
s3.append(Paragraph("<b>1.2 Address Modification:</b> Shipping address changes are only permitted within <b>30 minutes of placement</b>. Support agents cannot modify addresses once tracking numbers are generated.", body_style))

s3.append(Paragraph("2. 30-Day Return & Refund Guarantee Policy", h1_style))
s3.append(Paragraph("<b>2.1 Return Window:</b> Customers can initiate a return for eligible items within <b>30 calendar days of confirmed delivery</b>. Items must be in original packaging with tags intact.", body_style))
s3.append(Paragraph("<b>2.2 Return Shipping Costs:</b> Free domestic returns within the continental US. International returns incur a flat <b>$15 USD return shipping fee</b> deducted from the final refund.", body_style))
s3.append(Paragraph("<b>2.3 Non-Returnable Items:</b> Personalized/custom-engraved items, clearance items marked Final Sale, gift cards, and opened consumable/software products.", body_style))
s3.append(Paragraph("<b>2.4 Refund Processing Timelines:</b> Once returned goods arrive at our warehouse, inspection takes 1–2 business days. Refunds are issued based on payment method:", body_style))

refund_data = [
    ["Original Payment Method", "Processing SLA", "Financial Institution Settlement", "Notes"],
    ["Credit / Debit Card (Visa, MC, Amex)", "2–3 business days", "3–5 additional business days", "Appears on card statement"],
    ["PayPal / Apple Pay / Google Pay", "24 hours", "Instant to 1 business day", "Direct balance refund"],
    ["Store Credit Voucher", "Instantaneous", "Available immediately", "+10% bonus credit applied"],
    ["Direct Bank Wire / ACH", "3–5 business days", "5–7 business days", "Requires verified bank info"]
]
s3.append(make_table(refund_data, [130, 90, 140, 160]))
s3.append(Spacer(1, 6))

s3.append(Paragraph("3. Damaged, Lost, or Defective Shipments", h1_style))
s3.append(Paragraph("<b>3.1 Damaged Upon Arrival:</b> Customers must report damaged shipments within <b>7 calendar days of delivery</b> by submitting clear photos of the damaged packaging and product. Support agents will immediately dispatch a priority replacement order at no charge.", body_style))
s3.append(Paragraph("<b>3.2 Lost in Transit Protocols:</b> If tracking has not updated for <b>7 consecutive days (domestic)</b> or <b>14 days (international)</b>, the shipment is classified as Lost in Transit. Support agents can issue an immediate full refund or priority reshipment.", body_style))

s3.append(Paragraph("4. Customer Support Escalation Tiers & Response SLAs", h1_style))
support_data = [
    ["Support Tier", "Scope of Inquiries", "First Response SLA", "Resolution SLA Target"],
    ["Tier 1 (General Customer Care)", "Order tracking, return label generation, FAQ answers", "< 2 hours (Chat: < 2 mins)", "Within 12 hours"],
    ["Tier 2 (Billing & Escalations)", "Damaged goods, refund disputes, lost shipment claims", "< 4 hours", "Within 24 hours"],
    ["Tier 3 (Enterprise & VIP Clients)", "B2B bulk orders, custom SLAs, contract compliance", "< 30 minutes", "Within 4 hours"]
]
s3.append(make_table(support_data, [110, 190, 110, 110]))

doc3.build(s3)

print("Generated comprehensive 3 multi-page enterprise PDFs with rich tables and complete policies!")
