from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap
from typing import List, Tuple

PAGE_W, PAGE_H = 612, 792  # US Letter
MARGIN = 54

PALETTE = {
    "bg": "#0b0b0f",
    "surface": "#121218",
    "surface_alt": "#171722",
    "ink": "#ffffff",
    "ink_muted": "#e5e5ef",
    "ink_soft": "#c9c9d9",
    "accent_red": "#dd2c00",
    "accent_orange": "#ff9100",
    "accent_green": "#34a853",
    "accent_yellow": "#fbbc04",
}


def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))


def escape_pdf_text(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("(", r"\(")
        .replace(")", r"\)")
        .replace("\n", " ")
    )


@dataclass
class PdfPage:
    ops: List[str]


class PdfBuilder:
    def __init__(self, page_size: Tuple[int, int] = (PAGE_W, PAGE_H)):
        self.page_w, self.page_h = page_size
        self.pages: List[PdfPage] = []

    def add_page(self, ops: List[str]):
        self.pages.append(PdfPage(ops=ops))

    def build(self, output_path: Path):
        objects = {}
        objects[1] = "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        objects[2] = (
            f"2 0 obj << /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in range(3, 3 + len(self.pages)))}] /Count {len(self.pages)} >> endobj\n"
        )

        page_objects_start = 3
        contents_objects_start = page_objects_start + len(self.pages)
        font_regular_id = contents_objects_start + len(self.pages)
        font_bold_id = font_regular_id + 1

        for i, page in enumerate(self.pages):
            page_obj_id = page_objects_start + i
            content_obj_id = contents_objects_start + i
            objects[page_obj_id] = (
                f"{page_obj_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.page_w} {self.page_h}] "
                f"/Contents {content_obj_id} 0 R /Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> >> endobj\n"
            )

        for i, page in enumerate(self.pages):
            content_obj_id = contents_objects_start + i
            content = "\n".join(page.ops) + "\n"
            objects[content_obj_id] = (
                f"{content_obj_id} 0 obj << /Length {len(content.encode('utf-8'))} >> stream\n{content}endstream endobj\n"
            )

        objects[font_regular_id] = (
            f"{font_regular_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        )
        objects[font_bold_id] = (
            f"{font_bold_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n"
        )

        pdf = "%PDF-1.4\n"
        offsets = {}
        max_id = max(objects.keys())
        for obj_id in range(1, max_id + 1):
            if obj_id in objects:
                offsets[obj_id] = len(pdf.encode("utf-8"))
                pdf += objects[obj_id]

        xref_offset = len(pdf.encode("utf-8"))
        pdf += f"xref\n0 {max_id + 1}\n"
        pdf += "0000000000 65535 f \n"
        for obj_id in range(1, max_id + 1):
            if obj_id in offsets:
                pdf += f"{offsets[obj_id]:010d} 00000 n \n"
            else:
                pdf += "0000000000 65535 f \n"
        pdf += f"trailer << /Size {max_id + 1} /Root 1 0 R >>\n"
        pdf += f"startxref\n{xref_offset}\n%%EOF\n"

        output_path.write_bytes(pdf.encode("utf-8"))


class PageBuilder:
    def __init__(self, accent: str):
        self.ops: List[str] = []
        self.cursor_y = PAGE_H - MARGIN
        self.accent = accent
        self.draw_rect(0, 0, PAGE_W, PAGE_H, fill=PALETTE["bg"])

    def set_fill(self, hex_color: str):
        r, g, b = hex_to_rgb(hex_color)
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg")

    def set_stroke(self, hex_color: str):
        r, g, b = hex_to_rgb(hex_color)
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} RG")

    def draw_rect(self, x, y, w, h, fill=None, stroke=None, width=1):
        if fill:
            self.set_fill(fill)
        if stroke:
            self.set_stroke(stroke)
            self.ops.append(f"{width} w")
        self.ops.append(f"{x} {y} {w} {h} re")
        if fill and stroke:
            self.ops.append("B")
        elif fill:
            self.ops.append("f")
        elif stroke:
            self.ops.append("S")

    def draw_line(self, x1, y1, x2, y2, color=None, width=1):
        if color:
            self.set_stroke(color)
        self.ops.append(f"{width} w")
        self.ops.append(f"{x1} {y1} m {x2} {y2} l S")

    def draw_text(self, x, y, text, size=12, color=None, bold=False):
        if color:
            self.set_fill(color)
        font = "/F2" if bold else "/F1"
        self.ops.append("BT")
        self.ops.append(f"{font} {size} Tf")
        self.ops.append(f"{x} {y} Td")
        self.ops.append(f"({escape_pdf_text(text)}) Tj")
        self.ops.append("ET")

    def add_section_header(self, title: str):
        bar_height = 24
        y = self.cursor_y - bar_height
        self.draw_rect(MARGIN, y, PAGE_W - 2 * MARGIN, bar_height, fill=self.accent)
        self.draw_text(MARGIN + 12, y + 6, title, size=12, color=PALETTE["ink"], bold=True)
        self.cursor_y = y - 18

    def add_paragraph(self, text: str, size=11, color=PALETTE["ink_muted"], max_width=None, leading=1.4):
        if max_width is None:
            max_width = PAGE_W - 2 * MARGIN
        max_chars = max(int(max_width / (size * 0.56)), 30)
        lines = textwrap.wrap(text, width=max_chars)
        for line in lines:
            self.draw_text(MARGIN, self.cursor_y, line, size=size, color=color)
            self.cursor_y -= size * leading
        self.cursor_y -= size * 0.4

    def add_bullets(self, items: List[str], size=11, color=PALETTE["ink_muted"], max_width=None):
        if max_width is None:
            max_width = PAGE_W - 2 * MARGIN
        max_chars = max(int(max_width / (size * 0.56)), 30)
        for item in items:
            wrapped = textwrap.wrap(f"• {item}", width=max_chars)
            for line in wrapped:
                self.draw_text(MARGIN, self.cursor_y, line, size=size, color=color)
                self.cursor_y -= size * 1.35
        self.cursor_y -= size * 0.3


def build_cover(ebook, accent):
    page = PageBuilder(accent)
    page.draw_rect(0, PAGE_H - 140, PAGE_W, 140, fill=PALETTE["surface"])
    page.draw_rect(0, PAGE_H - 30, PAGE_W, 30, fill=accent)
    page.draw_text(MARGIN, PAGE_H - 90, ebook["title"], size=24, color=PALETTE["ink"], bold=True)
    page.draw_text(MARGIN, PAGE_H - 120, ebook["subtitle"], size=12, color=PALETTE["ink_muted"])
    page.draw_text(MARGIN, PAGE_H - 160, f"{ebook['vendor']} | {ebook['industry']}", size=11, color=PALETTE["ink_soft"])

    page.cursor_y = PAGE_H - 210
    page.add_section_header("What you will gain")
    page.add_bullets(ebook["highlights"], size=11)

    page.draw_rect(MARGIN, 90, PAGE_W - 2 * MARGIN, 2, fill=accent)
    page.draw_text(MARGIN, 60, "The Learning Curve", size=12, color=PALETTE["ink"], bold=True)
    page.draw_text(MARGIN, 42, "Keep learning, keep growing.", size=10, color=PALETTE["ink_soft"])
    return page.ops


def build_exec_summary(ebook, accent):
    page = PageBuilder(accent)
    page.add_section_header("Executive summary")
    page.add_paragraph(ebook["exec_summary"][0])
    page.add_paragraph(ebook["exec_summary"][1])
    page.add_section_header("Outcome focus")
    page.add_bullets(ebook["outcomes"], size=11)
    return page.ops


def build_market_signals(ebook, accent, stats):
    page = PageBuilder(accent)
    page.add_section_header("Market signals")
    page.add_paragraph("Enterprise learning leaders are investing in AI fluency, cloud modernization, and governance readiness. These signals frame the urgency and scale of adoption across industries.")
    page.add_bullets([f"{s['value']} — {s['label']}" for s in stats], size=10)

    # Simple bar chart
    chart_x = MARGIN
    chart_y = 230
    chart_w = PAGE_W - 2 * MARGIN
    chart_h = 140
    page.draw_rect(chart_x, chart_y, chart_w, chart_h, fill=PALETTE["surface_alt"], stroke=PALETTE["surface_alt"])
    bar_values = [80, 68, 56, 44]
    bar_labels = ["AI", "Cloud", "Security", "Data"]
    bar_width = (chart_w - 80) / len(bar_values)
    for i, value in enumerate(bar_values):
        x = chart_x + 30 + i * bar_width
        height = chart_h * (value / 100)
        page.draw_rect(x, chart_y, bar_width * 0.5, height, fill=accent)
        page.draw_text(x, chart_y - 16, bar_labels[i], size=9, color=PALETTE["ink_soft"])
        page.draw_text(x, chart_y + height + 6, f"{value}%", size=9, color=PALETTE["ink_muted"])

    page.draw_text(MARGIN, 200, "Implication", size=11, color=PALETTE["ink"], bold=True)
    page.add_paragraph("Leadership teams need a measurable learning plan that balances speed, governance, and adoption across the enterprise.")
    return page.ops


def build_use_cases(ebook, accent):
    page = PageBuilder(accent)
    page.add_section_header("Strategic use cases")
    page.add_paragraph("We prioritize initiatives that deliver executive visibility, measurable value, and rapid adoption.")
    page.add_bullets(ebook["use_cases"], size=11)
    return page.ops


def build_capability_map(ebook, accent):
    page = PageBuilder(accent)
    page.add_section_header("Capability map")
    columns = [
        ("People", ebook["capability_people"]),
        ("Process", ebook["capability_process"]),
        ("Platform", ebook["capability_platform"]),
    ]
    col_w = (PAGE_W - 2 * MARGIN - 24) / 3
    top_y = page.cursor_y
    box_h = 220
    for idx, (title, items) in enumerate(columns):
        x = MARGIN + idx * (col_w + 12)
        y = top_y - box_h
        page.draw_rect(x, y, col_w, box_h, fill=PALETTE["surface"], stroke=PALETTE["surface_alt"])
        page.draw_text(x + 12, y + box_h - 24, title, size=11, color=PALETTE["ink"], bold=True)
        y_cursor = y + box_h - 46
        for item in items:
            page.draw_text(x + 12, y_cursor, f"• {item}", size=9.5, color=PALETTE["ink_muted"])
            y_cursor -= 14

    page.cursor_y = top_y - box_h - 24
    page.add_section_header("Vendor accelerators")
    page.add_bullets(ebook["accelerators"], size=10)
    return page.ops


def build_learning_path(ebook, accent):
    page = PageBuilder(accent)
    page.add_section_header("Learning pathway")
    page.add_paragraph("A structured pathway ensures executives, leaders, and practitioners move in lockstep.")

    y = page.cursor_y
    box_w = PAGE_W - 2 * MARGIN
    box_h = 80
    for phase in ebook["learning_path"]:
        page.draw_rect(MARGIN, y - box_h, box_w, box_h, fill=PALETTE["surface"], stroke=PALETTE["surface_alt"])
        page.draw_text(MARGIN + 14, y - 26, phase["title"], size=11, color=PALETTE["ink"], bold=True)
        page.draw_text(MARGIN + 14, y - 46, phase["focus"], size=10, color=PALETTE["ink_muted"])
        page.draw_text(MARGIN + 14, y - 66, phase["duration"], size=9.5, color=PALETTE["ink_soft"])
        y -= box_h + 14

    return page.ops


def build_cohort_design(ebook, accent):
    page = PageBuilder(accent)
    page.add_section_header("Cohort design")
    page.add_paragraph("Role-based tracks ensure that leaders, managers, and practitioners receive the right depth of enablement.")

    y = page.cursor_y
    box_h = 150
    for track in ebook["cohorts"]:
        page.draw_rect(MARGIN, y - box_h, PAGE_W - 2 * MARGIN, box_h, fill=PALETTE["surface"], stroke=PALETTE["surface_alt"])
        page.draw_text(MARGIN + 14, y - 28, track["title"], size=11, color=PALETTE["ink"], bold=True)
        page.draw_text(MARGIN + 14, y - 48, track["summary"], size=10, color=PALETTE["ink_muted"])
        y_cursor = y - 70
        for course in track["courses"]:
            page.draw_text(MARGIN + 22, y_cursor, f"• {course}", size=9.5, color=PALETTE["ink_soft"])
            y_cursor -= 14
        y -= box_h + 16

    return page.ops


def build_90_day_plan(ebook, accent):
    page = PageBuilder(accent)
    page.add_section_header("90-day activation plan")
    page.add_paragraph("A focused 90-day plan connects strategy, learning, and deployment milestones.")

    y = page.cursor_y
    for step in ebook["plan"]:
        page.draw_rect(MARGIN, y - 80, PAGE_W - 2 * MARGIN, 80, fill=PALETTE["surface"], stroke=PALETTE["surface_alt"])
        page.draw_text(MARGIN + 14, y - 26, step["title"], size=11, color=PALETTE["ink"], bold=True)
        page.draw_text(MARGIN + 14, y - 46, step["focus"], size=10, color=PALETTE["ink_muted"])
        page.draw_text(MARGIN + 14, y - 64, step["deliverables"], size=9.5, color=PALETTE["ink_soft"])
        y -= 92
    return page.ops


def build_kpi_scorecard(ebook, accent):
    page = PageBuilder(accent)
    page.add_section_header("KPI scorecard")
    page.add_paragraph("Track adoption, performance, and business impact with a consistent scorecard.")
    page.add_bullets(ebook["kpis"], size=10)
    return page.ops


def build_sources(ebook, accent, sources):
    page = PageBuilder(accent)
    page.add_section_header("Sources")
    page.add_bullets(sources, size=9.5)

    page.add_section_header("How The Learning Curve helps")
    page.add_paragraph(
        "The Learning Curve designs instructor-led programs that map directly to business outcomes. We blend vendor-authorized content with custom labs, coaching, and readiness metrics so your teams can adopt faster and scale safely."
    )
    page.add_paragraph("Ready to build a tailored learning journey? Contact us at thelearningcurve.ai or visit thelearningcurve.ai.", size=10)
    return page.ops


GLOBAL_STATS = [
    {
        "label": "of workers require training by 2027",
        "value": "60%",
        "source": "World Economic Forum Future of Jobs 2023",
    },
    {
        "label": "of worker skills will be disrupted in the next five years",
        "value": "44%",
        "source": "World Economic Forum Future of Jobs 2023",
    },
    {
        "label": "of organizations use AI in at least one function",
        "value": "78%",
        "source": "McKinsey State of AI 2024",
    },
    {
        "label": "of organizations use generative AI in at least one function",
        "value": "71%",
        "source": "McKinsey State of AI 2024",
    },
    {
        "label": "public cloud spend forecast in 2024",
        "value": "$675B",
        "source": "Gartner 2024 cloud spending forecast",
    },
    {
        "label": "average cost of a data breach",
        "value": "$4.88M",
        "source": "IBM Cost of a Data Breach 2024",
    },
]

SOURCES = [
    "World Economic Forum, Future of Jobs 2023: https://www.weforum.org/publications/the-future-of-jobs-report-2023/digest/",
    "McKinsey, State of AI 2024: https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai",
    "Gartner, Worldwide Public Cloud End-User Spending 2024-2025: https://www.gartner.com/en/newsroom/press-releases/2024-04-03-gartner-forecasts-worldwide-public-cloud-end-user-spending-to-reach-675-billion-in-2024",
    "IBM, Cost of a Data Breach 2024: https://www.ibm.com/reports/data-breach",
    "PwC, 2025 AI Jobs Barometer: https://www.pwc.com/gx/en/issues/artificial-intelligence/ai-jobs-barometer.html",
]

EBOOKS = [
    {
        "slug": "microsoft-healthcare-ai-playbook",
        "title": "Microsoft Cloud + AI in Healthcare",
        "subtitle": "Clinical workflows, secure data, and measurable patient outcomes",
        "vendor": "Microsoft",
        "industry": "Healthcare",
        "accent": PALETTE["accent_orange"],
        "highlights": [
            "Reduce clinical admin time with Power Platform automation",
            "Accelerate analytics with Azure data and AI services",
            "Embed responsible AI governance into care delivery",
        ],
        "exec_summary": [
            "Healthcare leaders are facing rising demand, tighter margins, and increasing data complexity. The most successful systems are investing in AI-enabled workflows that reduce administrative burden while improving patient outcomes.",
            "This playbook maps Microsoft cloud capabilities to healthcare priorities and outlines the learning pathway required to deliver measurable ROI within 90 days.",
        ],
        "outcomes": [
            "Shorter time-to-chart and faster care coordination",
            "Secure data sharing across clinics and partners",
            "AI-ready workforce with accountable governance",
        ],
        "use_cases": [
            "Clinical workflow automation with Power Platform",
            "Patient access and scheduling optimization",
            "Revenue cycle analytics and claims insights",
            "AI-powered triage and care navigation",
        ],
        "capability_people": ["Clinical operations leaders", "Data stewards", "IT security team"],
        "capability_process": ["Clinical workflow redesign", "Data governance", "Change management"],
        "capability_platform": ["Power Platform", "Azure AI", "Microsoft Fabric"],
        "accelerators": ["Healthcare data model", "Responsible AI labs", "Compliance mapping toolkit"],
        "learning_path": [
            {"title": "Phase 1: Executive alignment", "focus": "AI strategy, governance, KPI design", "duration": "Weeks 1-2"},
            {"title": "Phase 2: Skills build", "focus": "Power Platform + Azure AI practitioner labs", "duration": "Weeks 3-6"},
            {"title": "Phase 3: Deployment", "focus": "Pilot workflows, scale playbooks", "duration": "Weeks 7-12"},
        ],
        "cohorts": [
            {
                "title": "Executives",
                "summary": "Strategy, governance, and ROI alignment",
                "courses": ["AI leadership briefing", "Healthcare compliance for AI", "Azure strategy workshop"],
            },
            {
                "title": "Functional leaders",
                "summary": "Workflow redesign and data readiness",
                "courses": ["Power Platform automation", "Data stewardship", "AI risk management"],
            },
            {
                "title": "Practitioners",
                "summary": "Hands-on delivery labs",
                "courses": ["Power Apps labs", "Azure AI services", "Secure data pipelines"],
            },
        ],
        "plan": [
            {"title": "Weeks 1-2: Readiness", "focus": "Define priority workflows and success metrics", "deliverables": "Use-case shortlist, KPI baseline"},
            {"title": "Weeks 3-6: Enable", "focus": "Launch role-based learning cohorts", "deliverables": "Cohort completion, pilot backlog"},
            {"title": "Weeks 7-12: Launch", "focus": "Deploy pilot workflows and measure outcomes", "deliverables": "ROI dashboard, scale roadmap"},
        ],
        "kpis": [
            "Workflow cycle time reduction",
            "Patient throughput and satisfaction lift",
            "Security compliance score",
            "AI adoption rate by role",
            "Time-to-insight for clinical analytics",
        ],
    },
    {
        "slug": "aws-financial-services-modernization",
        "title": "AWS for Financial Services Modernization",
        "subtitle": "Risk-aware migration, data governance, and AI-led customer insight",
        "vendor": "AWS",
        "industry": "Financial Services",
        "accent": PALETTE["accent_red"],
        "highlights": [
            "Modernize core systems with regulated cloud playbooks",
            "Improve fraud and risk detection with AI-led analytics",
            "Enable secure data sharing across business units",
        ],
        "exec_summary": [
            "Financial institutions need modernization without compromising regulatory requirements. The most effective leaders pair cloud adoption with rigorous governance and role-based enablement.",
            "This playbook outlines the learning, security, and operational steps required to modernize at speed while maintaining compliance and trust.",
        ],
        "outcomes": [
            "Faster product release cycles",
            "Improved fraud detection and risk modeling",
            "Audit-ready cloud governance",
        ],
        "use_cases": [
            "Cloud-native data lake and analytics modernization",
            "Fraud detection and real-time risk scoring",
            "KYC automation and onboarding acceleration",
            "Regulatory reporting automation",
        ],
        "capability_people": ["Risk leaders", "Security architects", "Data engineering team"],
        "capability_process": ["Regulatory controls", "Model risk governance", "Cloud migration sprints"],
        "capability_platform": ["AWS security services", "AWS analytics", "ML foundations"],
        "accelerators": ["Financial services landing zone", "AI risk scorecards", "Security control library"],
        "learning_path": [
            {"title": "Phase 1: Governance", "focus": "Risk assessment and cloud control alignment", "duration": "Weeks 1-2"},
            {"title": "Phase 2: Build", "focus": "AWS analytics + security labs", "duration": "Weeks 3-6"},
            {"title": "Phase 3: Launch", "focus": "Pilot models and production readiness", "duration": "Weeks 7-12"},
        ],
        "cohorts": [
            {
                "title": "Executives",
                "summary": "Risk-aware modernization strategy",
                "courses": ["AWS executive briefing", "Regulatory readiness", "AI governance"],
            },
            {
                "title": "Risk & compliance",
                "summary": "Control mapping and audit readiness",
                "courses": ["Cloud risk management", "Security controls", "Model risk management"],
            },
            {
                "title": "Practitioners",
                "summary": "Hands-on modernization delivery",
                "courses": ["AWS data engineering", "Security automation", "ML practitioner labs"],
            },
        ],
        "plan": [
            {"title": "Weeks 1-2: Assess", "focus": "Risk baseline and priority workloads", "deliverables": "Risk register, migration roadmap"},
            {"title": "Weeks 3-6: Enable", "focus": "Cohort training and pilot build", "deliverables": "Data platform pilot, compliance sign-off"},
            {"title": "Weeks 7-12: Scale", "focus": "Launch use cases and measure impact", "deliverables": "Fraud KPI dashboard, scale plan"},
        ],
        "kpis": [
            "Fraud detection precision",
            "Customer onboarding time",
            "Audit readiness score",
            "Cloud cost-to-value ratio",
            "Model risk exception rate",
        ],
    },
    {
        "slug": "google-retail-growth",
        "title": "Google Cloud for Retail Growth",
        "subtitle": "Personalization, demand forecasting, and omnichannel acceleration",
        "vendor": "Google Cloud",
        "industry": "Retail",
        "accent": PALETTE["accent_orange"],
        "highlights": [
            "Increase conversion through AI personalization",
            "Improve demand forecasting and inventory turns",
            "Unify omnichannel customer journeys",
        ],
        "exec_summary": [
            "Retail leaders are balancing margin pressure with customer expectations for personalization. Modern analytics and AI enable smarter inventory planning and more relevant experiences.",
            "This playbook outlines the learning path required to scale Google Cloud analytics and AI across merchandising, supply chain, and customer experience teams.",
        ],
        "outcomes": [
            "Higher conversion and basket size",
            "Reduced stockouts and overstocks",
            "Improved omnichannel visibility",
        ],
        "use_cases": [
            "Demand forecasting with Vertex AI",
            "Personalized recommendations at scale",
            "Inventory optimization and markdown planning",
            "Customer segmentation and loyalty analytics",
        ],
        "capability_people": ["Merchandising leaders", "Data analysts", "Digital product owners"],
        "capability_process": ["Merchandising analytics", "Inventory governance", "Experimentation cadence"],
        "capability_platform": ["BigQuery", "Vertex AI", "Looker"],
        "accelerators": ["Retail data model", "Forecasting templates", "Experimentation playbooks"],
        "learning_path": [
            {"title": "Phase 1: Strategy", "focus": "Retail analytics roadmap", "duration": "Weeks 1-2"},
            {"title": "Phase 2: Build", "focus": "BigQuery + Looker enablement", "duration": "Weeks 3-6"},
            {"title": "Phase 3: Scale", "focus": "AI personalization pilots", "duration": "Weeks 7-12"},
        ],
        "cohorts": [
            {
                "title": "Executives",
                "summary": "Growth strategy and KPI alignment",
                "courses": ["AI retail strategy", "Data governance", "Customer analytics"],
            },
            {
                "title": "Functional leaders",
                "summary": "Merchandising and CX analytics",
                "courses": ["BigQuery analytics", "Looker storytelling", "Forecasting labs"],
            },
            {
                "title": "Practitioners",
                "summary": "Hands-on data and AI delivery",
                "courses": ["Vertex AI labs", "Data pipelines", "Experiment design"],
            },
        ],
        "plan": [
            {"title": "Weeks 1-2: Discover", "focus": "Map customer journeys and data gaps", "deliverables": "Use-case shortlist, data audit"},
            {"title": "Weeks 3-6: Enable", "focus": "Build analytics foundations", "deliverables": "Forecasting MVP, KPI baseline"},
            {"title": "Weeks 7-12: Launch", "focus": "Personalization pilot", "deliverables": "Revenue lift dashboard, scale plan"},
        ],
        "kpis": [
            "Conversion rate lift",
            "Inventory turnover",
            "Forecast accuracy",
            "Customer lifetime value",
            "Omnichannel fulfillment time",
        ],
    },
    {
        "slug": "cisco-public-sector",
        "title": "Cisco Secure Networks for Public Sector",
        "subtitle": "Resilient infrastructure, zero trust adoption, and mission readiness",
        "vendor": "Cisco",
        "industry": "Public Sector",
        "accent": PALETTE["accent_green"],
        "highlights": [
            "Establish zero trust access across agencies",
            "Improve resilience and uptime for mission-critical systems",
            "Scale secure remote workforce enablement",
        ],
        "exec_summary": [
            "Public sector agencies face rising security threats and a growing demand for digital services. Zero trust and resilient network operations are now critical for mission continuity.",
            "This playbook outlines how Cisco security and networking enablement can deliver measurable risk reduction within a single quarter.",
        ],
        "outcomes": [
            "Reduced incident response time",
            "Improved network uptime",
            "Standardized security governance",
        ],
        "use_cases": [
            "Zero trust access and identity governance",
            "Network segmentation for critical systems",
            "Secure remote workforce enablement",
            "SOC modernization and threat response",
        ],
        "capability_people": ["Security leaders", "Network operators", "Compliance officers"],
        "capability_process": ["Threat response playbooks", "Access governance", "Risk assessments"],
        "capability_platform": ["Cisco security", "Network automation", "SOC tooling"],
        "accelerators": ["Zero trust blueprint", "Incident response labs", "Compliance mapping"],
        "learning_path": [
            {"title": "Phase 1: Assess", "focus": "Risk posture and access control review", "duration": "Weeks 1-2"},
            {"title": "Phase 2: Enable", "focus": "Security + networking labs", "duration": "Weeks 3-6"},
            {"title": "Phase 3: Deploy", "focus": "Zero trust pilot rollout", "duration": "Weeks 7-12"},
        ],
        "cohorts": [
            {
                "title": "Executives",
                "summary": "Mission readiness and risk alignment",
                "courses": ["Cyber resilience briefing", "Zero trust leadership", "Public sector governance"],
            },
            {
                "title": "Security leaders",
                "summary": "Security operations and compliance",
                "courses": ["Cisco security labs", "Incident response", "Compliance reporting"],
            },
            {
                "title": "Practitioners",
                "summary": "Network operations enablement",
                "courses": ["Network automation", "Secure access labs", "Threat detection"],
            },
        ],
        "plan": [
            {"title": "Weeks 1-2: Baseline", "focus": "Security and network assessment", "deliverables": "Risk dashboard, access map"},
            {"title": "Weeks 3-6: Enable", "focus": "Cohort training and pilot security controls", "deliverables": "Pilot zero trust policies"},
            {"title": "Weeks 7-12: Rollout", "focus": "Scale secure access", "deliverables": "Operational KPIs, response plan"},
        ],
        "kpis": [
            "Mean time to detect",
            "Mean time to respond",
            "Zero trust policy coverage",
            "Network uptime",
            "Compliance audit score",
        ],
    },
    {
        "slug": "pmi-manufacturing-portfolio",
        "title": "PMI Portfolio Management in Manufacturing",
        "subtitle": "Capital efficiency, plant modernization, and delivery governance",
        "vendor": "PMI",
        "industry": "Manufacturing",
        "accent": PALETTE["accent_orange"],
        "highlights": [
            "Prioritize modernization investments with portfolio scoring",
            "Improve delivery governance across plants",
            "Align leadership on value-based initiatives",
        ],
        "exec_summary": [
            "Manufacturers face pressure to modernize plants while controlling capital spend. Portfolio management discipline ensures investments align to strategic outcomes.",
            "This playbook outlines how PMI-based governance and training helps leaders deliver modernization programs on time and on budget.",
        ],
        "outcomes": [
            "Higher ROI per modernization initiative",
            "Reduced delivery variance",
            "Improved resource utilization",
        ],
        "use_cases": [
            "Portfolio scoring for modernization initiatives",
            "Agile delivery for plant upgrades",
            "Risk mitigation for supply chain investments",
            "Operational readiness reviews",
        ],
        "capability_people": ["PMO leaders", "Plant managers", "Program directors"],
        "capability_process": ["Portfolio governance", "Stage gate reviews", "Change control"],
        "capability_platform": ["PMI standards", "Agile delivery", "Risk management"],
        "accelerators": ["Portfolio scorecards", "Agile governance toolkit", "Executive dashboards"],
        "learning_path": [
            {"title": "Phase 1: Align", "focus": "Portfolio assessment and prioritization", "duration": "Weeks 1-2"},
            {"title": "Phase 2: Enable", "focus": "PMI + agile delivery training", "duration": "Weeks 3-6"},
            {"title": "Phase 3: Execute", "focus": "Launch modernization programs", "duration": "Weeks 7-12"},
        ],
        "cohorts": [
            {
                "title": "Executives",
                "summary": "Capital allocation and governance",
                "courses": ["Portfolio strategy", "Value management", "Risk governance"],
            },
            {
                "title": "Program leaders",
                "summary": "Delivery and change management",
                "courses": ["PMI program management", "Agile plant upgrades", "Risk monitoring"],
            },
            {
                "title": "Practitioners",
                "summary": "Execution excellence",
                "courses": ["PMI basics", "Operational project tools", "Metrics reporting"],
            },
        ],
        "plan": [
            {"title": "Weeks 1-2: Diagnose", "focus": "Portfolio health and ROI baseline", "deliverables": "Portfolio map, value gaps"},
            {"title": "Weeks 3-6: Enable", "focus": "Train program leads and PMO", "deliverables": "Governance cadence, playbooks"},
            {"title": "Weeks 7-12: Deliver", "focus": "Execute top modernization programs", "deliverables": "Delivery dashboards, KPI tracking"},
        ],
        "kpis": [
            "Portfolio ROI",
            "Schedule variance",
            "Capital efficiency",
            "Resource utilization",
            "Risk exposure",
        ],
    },
    {
        "slug": "ai-certs-workforce-literacy",
        "title": "AI Certs for Workforce Literacy",
        "subtitle": "Enterprise-wide AI fluency for every business unit",
        "vendor": "AI Certs",
        "industry": "Enterprise Workforce",
        "accent": PALETTE["accent_red"],
        "highlights": [
            "Build AI fluency across the enterprise",
            "Accelerate adoption with role-based learning",
            "Reduce AI risk with responsible AI training",
        ],
        "exec_summary": [
            "AI is moving into every business function, but most employees lack shared language and confidence. AI Certs provides role-based learning to build workforce readiness quickly.",
            "This playbook outlines how to design a scalable AI literacy initiative that aligns with business priorities and governance expectations.",
        ],
        "outcomes": [
            "Higher AI adoption rates",
            "Reduced AI risk exposure",
            "Improved productivity in core workflows",
        ],
        "use_cases": [
            "AI literacy for sales, marketing, and ops",
            "Prompt engineering enablement",
            "Responsible AI policy awareness",
            "AI-assisted workflow automation",
        ],
        "capability_people": ["L&D leaders", "Business unit leaders", "AI champions"],
        "capability_process": ["Role-based learning", "AI usage guidelines", "Change communications"],
        "capability_platform": ["AI Certs curriculum", "Live instructor-led labs", "Assessment engine"],
        "accelerators": ["AI skills baseline", "Prompt libraries", "Responsible AI toolkits"],
        "learning_path": [
            {"title": "Phase 1: Baseline", "focus": "Assess AI fluency and gaps", "duration": "Weeks 1-2"},
            {"title": "Phase 2: Enable", "focus": "Role-based AI Certs cohorts", "duration": "Weeks 3-6"},
            {"title": "Phase 3: Adopt", "focus": "Embed AI in workflows", "duration": "Weeks 7-12"},
        ],
        "cohorts": [
            {
                "title": "Executives",
                "summary": "Governance, policy, and ROI",
                "courses": ["AI strategy", "Responsible AI", "KPI design"],
            },
            {
                "title": "Managers",
                "summary": "Workflow adoption and enablement",
                "courses": ["AI productivity", "Prompt engineering", "Change management"],
            },
            {
                "title": "Practitioners",
                "summary": "Hands-on AI usage",
                "courses": ["AI fundamentals", "Prompt labs", "AI safety"],
            },
        ],
        "plan": [
            {"title": "Weeks 1-2: Diagnose", "focus": "AI skills baseline and priority roles", "deliverables": "Skills heatmap"},
            {"title": "Weeks 3-6: Enable", "focus": "Cohort learning and labs", "deliverables": "Completion reports, prompts library"},
            {"title": "Weeks 7-12: Embed", "focus": "Workflow adoption and measurement", "deliverables": "Adoption dashboard, ROI story"},
        ],
        "kpis": [
            "AI literacy score",
            "Prompt usage rate",
            "Productivity lift",
            "Responsible AI compliance",
            "Adoption by business unit",
        ],
    },
    {
        "slug": "adoptify-ai-governance",
        "title": "Adoptify AI Governance Blueprint",
        "subtitle": "Policy, operating model, and safe AI scale-up",
        "vendor": "Adoptify AI",
        "industry": "Regulated Enterprises",
        "accent": PALETTE["accent_green"],
        "highlights": [
            "Establish enterprise AI governance",
            "Build model risk and approval workflows",
            "Align stakeholders on safe AI scale-up",
        ],
        "exec_summary": [
            "As AI adoption accelerates, leaders need a governance model that balances innovation with control. Adoptify AI provides the frameworks and training to scale safely.",
            "This playbook outlines the learning and operating model required to establish AI governance across regulated teams.",
        ],
        "outcomes": [
            "Clear AI approval workflows",
            "Reduced compliance risk",
            "Faster time-to-approval",
        ],
        "use_cases": [
            "AI policy and risk framework design",
            "Model registry and approval workflows",
            "Audit-ready AI documentation",
            "Cross-functional governance councils",
        ],
        "capability_people": ["Risk leaders", "Legal and compliance", "AI product owners"],
        "capability_process": ["AI policy governance", "Model risk management", "Approval workflows"],
        "capability_platform": ["Adoptify AI tooling", "Policy libraries", "Audit dashboards"],
        "accelerators": ["AI policy templates", "Risk scoring models", "Governance maturity assessments"],
        "learning_path": [
            {"title": "Phase 1: Align", "focus": "Define governance objectives", "duration": "Weeks 1-2"},
            {"title": "Phase 2: Build", "focus": "Policy and approval workflows", "duration": "Weeks 3-6"},
            {"title": "Phase 3: Scale", "focus": "Deploy governance across teams", "duration": "Weeks 7-12"},
        ],
        "cohorts": [
            {
                "title": "Executives",
                "summary": "Governance vision and policy",
                "courses": ["AI governance strategy", "Risk oversight", "Board reporting"],
            },
            {
                "title": "Compliance leaders",
                "summary": "Policy, audit, and controls",
                "courses": ["Model risk management", "AI audit readiness", "Policy workflows"],
            },
            {
                "title": "Practitioners",
                "summary": "Implementation enablement",
                "courses": ["Adoptify AI labs", "Policy documentation", "Governance tooling"],
            },
        ],
        "plan": [
            {"title": "Weeks 1-2: Design", "focus": "Governance charter and priorities", "deliverables": "Policy blueprint"},
            {"title": "Weeks 3-6: Build", "focus": "Approval workflow configuration", "deliverables": "Model registry, audit trail"},
            {"title": "Weeks 7-12: Scale", "focus": "Expand governance across teams", "deliverables": "Governance scorecard"},
        ],
        "kpis": [
            "Time-to-approval",
            "AI policy adherence",
            "Risk exception rate",
            "Audit readiness",
            "Governance maturity score",
        ],
    },
    {
        "slug": "microsoft-federal-hybrid",
        "title": "Microsoft Hybrid Cloud for Federal Missions",
        "subtitle": "Secure collaboration, data residency, and mission continuity",
        "vendor": "Microsoft",
        "industry": "Federal & Defense",
        "accent": PALETTE["accent_orange"],
        "highlights": [
            "Secure collaboration across agencies",
            "Data residency and compliance alignment",
            "Mission continuity with hybrid operations",
        ],
        "exec_summary": [
            "Federal agencies need secure collaboration while maintaining mission continuity. Hybrid cloud architectures help balance security, residency, and agility.",
            "This playbook outlines the learning and governance steps needed to deploy Microsoft hybrid solutions at scale.",
        ],
        "outcomes": [
            "Reduced collaboration friction",
            "Stronger compliance posture",
            "Faster mission delivery",
        ],
        "use_cases": [
            "Hybrid identity and access management",
            "Secure collaboration with M365",
            "Protected data sharing across agencies",
            "Mission-ready data analytics",
        ],
        "capability_people": ["CIO leadership", "Security teams", "Mission operations"],
        "capability_process": ["Identity governance", "Data residency controls", "Security operations"],
        "capability_platform": ["Azure Stack", "Microsoft 365", "Defender suite"],
        "accelerators": ["FedRAMP alignment", "Zero trust blueprint", "Secure collaboration playbooks"],
        "learning_path": [
            {"title": "Phase 1: Align", "focus": "Mission priorities and security alignment", "duration": "Weeks 1-2"},
            {"title": "Phase 2: Enable", "focus": "Hybrid identity + security labs", "duration": "Weeks 3-6"},
            {"title": "Phase 3: Deploy", "focus": "Pilot collaboration workloads", "duration": "Weeks 7-12"},
        ],
        "cohorts": [
            {
                "title": "Executives",
                "summary": "Mission alignment and governance",
                "courses": ["Hybrid strategy", "Security leadership", "Compliance briefing"],
            },
            {
                "title": "Security leaders",
                "summary": "Identity and access management",
                "courses": ["Zero trust labs", "Defender operations", "Compliance mapping"],
            },
            {
                "title": "Practitioners",
                "summary": "Hybrid cloud enablement",
                "courses": ["Azure Stack labs", "Secure collaboration", "Data residency controls"],
            },
        ],
        "plan": [
            {"title": "Weeks 1-2: Align", "focus": "Mission objectives and risk assessment", "deliverables": "Mission roadmap, KPI baseline"},
            {"title": "Weeks 3-6: Enable", "focus": "Training and pilot design", "deliverables": "Hybrid pilot plan"},
            {"title": "Weeks 7-12: Deploy", "focus": "Launch secure collaboration", "deliverables": "Operational scorecard"},
        ],
        "kpis": [
            "Collaboration latency",
            "Compliance coverage",
            "Incident reduction",
            "Mission readiness score",
            "User adoption rate",
        ],
    },
    {
        "slug": "aws-cyber-resilience",
        "title": "AWS Cyber Resilience for Enterprises",
        "subtitle": "Zero trust foundations, incident response, and resilience drills",
        "vendor": "AWS",
        "industry": "Enterprise Security",
        "accent": PALETTE["accent_red"],
        "highlights": [
            "Reduce breach impact with automated response",
            "Improve recovery with resilience drills",
            "Scale zero trust across cloud workloads",
        ],
        "exec_summary": [
            "Security leaders need to improve detection, response, and recovery in an environment of accelerating risk. AWS security services combined with consistent enablement deliver measurable resilience gains.",
            "This playbook maps the learning journey required to implement zero trust and incident response programs within 90 days.",
        ],
        "outcomes": [
            "Lower incident response time",
            "Improved recovery readiness",
            "Stronger security governance",
        ],
        "use_cases": [
            "Security automation and log analytics",
            "Threat detection and response orchestration",
            "Backup and recovery modernization",
            "Zero trust network segmentation",
        ],
        "capability_people": ["CISO org", "Security operations", "Cloud engineers"],
        "capability_process": ["Incident response", "Threat modeling", "Resilience drills"],
        "capability_platform": ["AWS security services", "CloudTrail", "Security Hub"],
        "accelerators": ["Incident response playbooks", "Security baseline templates", "Resilience scorecards"],
        "learning_path": [
            {"title": "Phase 1: Baseline", "focus": "Security posture assessment", "duration": "Weeks 1-2"},
            {"title": "Phase 2: Enable", "focus": "Security automation labs", "duration": "Weeks 3-6"},
            {"title": "Phase 3: Launch", "focus": "Response drills and recovery validation", "duration": "Weeks 7-12"},
        ],
        "cohorts": [
            {
                "title": "Executives",
                "summary": "Risk oversight and governance",
                "courses": ["Security leadership briefing", "Risk scorecards", "Board reporting"],
            },
            {
                "title": "Security leaders",
                "summary": "Operations and response readiness",
                "courses": ["AWS Security Hub", "Incident response", "Threat hunting"],
            },
            {
                "title": "Practitioners",
                "summary": "Hands-on security enablement",
                "courses": ["CloudTrail labs", "Security automation", "Recovery testing"],
            },
        ],
        "plan": [
            {"title": "Weeks 1-2: Assess", "focus": "Risk assessment and baseline controls", "deliverables": "Security posture report"},
            {"title": "Weeks 3-6: Enable", "focus": "Train and pilot automation", "deliverables": "Security automation MVP"},
            {"title": "Weeks 7-12: Validate", "focus": "Run response and recovery drills", "deliverables": "Resilience scorecard"},
        ],
        "kpis": [
            "Mean time to detect",
            "Mean time to respond",
            "Recovery time objective",
            "Security control coverage",
            "Incident closure rate",
        ],
    },
    {
        "slug": "google-supply-chain-analytics",
        "title": "Google Cloud Supply Chain Analytics",
        "subtitle": "Forecasting, visibility, and cost-to-serve optimization",
        "vendor": "Google Cloud",
        "industry": "Supply Chain",
        "accent": PALETTE["accent_orange"],
        "highlights": [
            "Improve forecasting accuracy",
            "Increase end-to-end visibility",
            "Reduce cost-to-serve",
        ],
        "exec_summary": [
            "Supply chain leaders are under pressure to increase resilience and reduce cost-to-serve. Data-driven analytics and AI forecasting provide the visibility needed for proactive decision-making.",
            "This playbook outlines the learning journey required to deploy Google Cloud analytics for supply chain teams.",
        ],
        "outcomes": [
            "Higher forecast accuracy",
            "Lower inventory costs",
            "Faster response to disruptions",
        ],
        "use_cases": [
            "Demand sensing and forecasting",
            "Logistics optimization",
            "Supplier risk monitoring",
            "Inventory and capacity planning",
        ],
        "capability_people": ["Supply chain leaders", "Data scientists", "Operations planners"],
        "capability_process": ["Planning cadence", "Supplier governance", "Scenario modeling"],
        "capability_platform": ["BigQuery", "Vertex AI", "Looker dashboards"],
        "accelerators": ["Supply chain data model", "Forecasting accelerators", "Scenario templates"],
        "learning_path": [
            {"title": "Phase 1: Align", "focus": "Data readiness and use-case selection", "duration": "Weeks 1-2"},
            {"title": "Phase 2: Build", "focus": "Analytics foundation and training", "duration": "Weeks 3-6"},
            {"title": "Phase 3: Scale", "focus": "Deploy forecasting pilots", "duration": "Weeks 7-12"},
        ],
        "cohorts": [
            {
                "title": "Executives",
                "summary": "Supply chain strategy and KPIs",
                "courses": ["Analytics strategy", "Risk oversight", "KPI governance"],
            },
            {
                "title": "Operations leaders",
                "summary": "Scenario planning and optimization",
                "courses": ["BigQuery analytics", "Forecasting labs", "Looker insights"],
            },
            {
                "title": "Practitioners",
                "summary": "Hands-on analytics delivery",
                "courses": ["Data pipelines", "Vertex AI labs", "Demand modeling"],
            },
        ],
        "plan": [
            {"title": "Weeks 1-2: Discover", "focus": "Data gaps and use-case selection", "deliverables": "Data audit, KPI baseline"},
            {"title": "Weeks 3-6: Enable", "focus": "Analytics training and pilot setup", "deliverables": "Forecasting MVP"},
            {"title": "Weeks 7-12: Launch", "focus": "Operational rollout", "deliverables": "Visibility dashboard"},
        ],
        "kpis": [
            "Forecast accuracy",
            "Inventory turns",
            "Order fulfillment time",
            "Cost-to-serve",
            "Supplier risk exposure",
        ],
    },
]


def generate():
    output_dir = Path("assets/ebooks")
    output_dir.mkdir(parents=True, exist_ok=True)

    for ebook in EBOOKS:
        pdf = PdfBuilder()
        accent = ebook["accent"]
        stats = GLOBAL_STATS

        pdf.add_page(build_cover(ebook, accent))
        pdf.add_page(build_exec_summary(ebook, accent))
        pdf.add_page(build_market_signals(ebook, accent, stats))
        pdf.add_page(build_use_cases(ebook, accent))
        pdf.add_page(build_capability_map(ebook, accent))
        pdf.add_page(build_learning_path(ebook, accent))
        pdf.add_page(build_cohort_design(ebook, accent))
        pdf.add_page(build_90_day_plan(ebook, accent))
        pdf.add_page(build_kpi_scorecard(ebook, accent))
        pdf.add_page(build_sources(ebook, accent, SOURCES))

        pdf.build(output_dir / f"{ebook['slug']}.pdf")


if __name__ == "__main__":
    generate()
    print("Generated ebooks.")
