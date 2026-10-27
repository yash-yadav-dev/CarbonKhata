from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# =========================================================
# CARBONKHATA - PROFESSIONAL PDF REPORT GENERATOR
# Uses Pillow only; no extra packages required.
# =========================================================

PAGE_W = 1240
PAGE_H = 1930

GREEN = "#123D32"
DARK_GREEN = "#0B2B24"
LIME = "#C5F36A"
WHITE = "#FFFFFF"
BG = "#F5F8F5"
TEXT = "#20352D"
MUTED = "#728078"
BORDER = "#E1E9E2"
PALE_GREEN = "#EAF3E9"
PALE_LIME = "#F2F9DF"
ORANGE = "#E6A44A"
BLUE = "#7FA9D9"


def generate_carbon_report(data, target=None):
    """
    Generate a branded, one-page CarbonKhata emissions report.

    Required data:
        electricity_kwh
        diesel_litres
        lpg_kg
        production_units

    Emission factors are illustrative prototype values only.
    """

    # ---------- Validate inputs ----------

    electricity = float(data["electricity_kwh"])
    diesel = float(data["diesel_litres"])
    lpg = float(data["lpg_kg"])
    production = float(data["production_units"])

    if any(v < 0 for v in [electricity, diesel, lpg]):
        raise ValueError("Consumption values cannot be negative.")

    if production <= 0:
        raise ValueError("Production units must be greater than zero.")

    # ---------- Calculate emissions ----------

    electricity_factor = 0.71
    diesel_factor = 2.68
    lpg_factor = 3.00

    diesel_emissions = diesel * diesel_factor
    lpg_emissions = lpg * lpg_factor
    scope_1 = diesel_emissions + lpg_emissions

    scope_2 = electricity * electricity_factor
    total = scope_1 + scope_2
    intensity = total / production

    generated = datetime.now().astimezone()
    report_date = generated.strftime("%d %B %Y")
    report_time = generated.strftime("%I:%M %p %Z").strip()

    # ---------- Create output directory ----------

    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "reports"
    output_dir.mkdir(exist_ok=True)

    filename = (
        f"CarbonKhata_Report_{generated.strftime('%Y%m%d_%H%M%S')}.pdf"
    )
    output_path = output_dir / filename

    # ---------- Create page ----------

    image = Image.new("RGB", (PAGE_W, PAGE_H), BG)
    draw = ImageDraw.Draw(image)

    # ---------- Fonts ----------

    font_dir = Path("C:/Windows/Fonts")

    font_options = [
        font_dir / "arial.ttf",
        font_dir / "segoeui.ttf",
        font_dir / "calibri.ttf",
    ]

    bold_options = [
        font_dir / "arialbd.ttf",
        font_dir / "segoeuib.ttf",
        font_dir / "calibrib.ttf",
    ]

    def load_font(options, size):
        for path in options:
            try:
                if path.exists():
                    return ImageFont.truetype(str(path), size)
            except OSError:
                pass
        return ImageFont.load_default()

    regular_fonts = font_options
    bold_fonts = bold_options

    def font(size, bold=False):
        return load_font(bold_fonts if bold else regular_fonts, size)

    # ---------- Drawing helpers ----------

    def rounded_box(box, radius=18, fill=WHITE, outline=None, width=1):
        draw.rounded_rectangle(
            box,
            radius=radius,
            fill=fill,
            outline=outline,
            width=width
        )

    def label(x, y, text, size=22, color=TEXT, bold=False):
        draw.text(
            (x, y),
            str(text),
            font=font(size, bold),
            fill=color
        )

    def right_label(right_x, y, text, size=22, color=TEXT, bold=False):
        f = font(size, bold)
        draw.text(
            (right_x, y),
            str(text),
            font=f,
            fill=color,
            anchor="ra"
        )

    def section_title(x, y, title, subtitle=None):
        label(x, y, title, 27, GREEN, True)
        if subtitle:
            label(x, y + 39, subtitle, 17, MUTED)

    def line(x1, y1, x2, y2, fill=BORDER, width=2):
        draw.line((x1, y1, x2, y2), fill=fill, width=width)

    # =====================================================
    # HEADER
    # =====================================================

    draw.rectangle((0, 0, PAGE_W, 220), fill=GREEN)

    # Simple original brand mark: leaf-like symbol.
    draw.ellipse((64, 48, 112, 96), fill=LIME)
    draw.ellipse((80, 37, 128, 85), fill=WHITE)
    draw.line((78, 89, 108, 56), fill=GREEN, width=4)

    label(145, 42, "CarbonKhata", 40, WHITE, True)
    label(66, 119, "CARBON EMISSIONS REPORT", 30, WHITE, True)
    label(66, 164, "Measure clearly. Reduce intelligently.", 20, "#D7E6D8")

    rounded_box(
        (900, 48, 1170, 92),
        radius=18,
        fill="#294E40"
    )
    label(923, 60, "PROTOTYPE ESTIMATE", 16, LIME, True)

    right_label(1167, 124, report_date, 19, WHITE, True)
    right_label(1167, 155, report_time, 16, "#D7E6D8")

    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================

    label(64, 249, "Your footprint, in focus.", 32, GREEN, True)
    label(
        64, 294,
        "Operational emissions calculated from the supplied consumption inputs.",
        18, MUTED
    )

    card_y = 344
    card_h = 155
    gap = 18
    card_w = (PAGE_W - 128 - 2 * gap) // 3

    cards = [
        (
            "TOTAL EMISSIONS",
            f"{total:,.1f}",
            "kg CO2e",
            GREEN,
            WHITE
        ),
        (
            "SCOPE 1",
            f"{scope_1:,.1f}",
            "kg CO2e | Direct",
            PALE_GREEN,
            GREEN
        ),
        (
            "SCOPE 2",
            f"{scope_2:,.1f}",
            "kg CO2e | Electricity",
            PALE_LIME,
            GREEN
        ),
    ]

    for i, (title, value, sub, fill, fg) in enumerate(cards):
        x = 64 + i * (card_w + gap)

        rounded_box(
            (x, card_y, x + card_w, card_y + card_h),
            radius=18,
            fill=fill
        )

        label(x + 22, card_y + 20, title, 16, fg, True)
        label(x + 22, card_y + 55, value, 34, fg, True)
        label(x + 22, card_y + 108, sub, 15, fg)

    # Product intensity strip.
    strip_y = 520
    rounded_box(
        (64, strip_y, 1176, strip_y + 77),
        radius=16,
        fill=WHITE,
        outline=BORDER
    )

    label(86, strip_y + 13, "PRODUCT INTENSITY", 15, MUTED, True)
    label(
        86, strip_y + 36,
        f"{intensity:,.3f} kg CO2e per production unit",
        22, GREEN, True
    )

    right_label(
        1150, strip_y + 29,
        f"{total / 1000:,.4f} tonnes CO2e",
        20, GREEN, True
    )

    # =====================================================
    # CHARTS
    # =====================================================

    chart_y = 630

    section_title(
        64, chart_y,
        "Emissions breakdown",
        "Estimated contribution by scope and energy source."
    )

    chart_top = 708
    chart_bottom = 1000

    # Left chart card: donut.
    left_box = (64, chart_top, 565, chart_bottom)
    rounded_box(left_box, 18, WHITE, BORDER)

    label(88, chart_top + 20, "SCOPE CONTRIBUTION", 17, MUTED, True)

    # Center the donut inside the left card and leave room for the legend.
    cx, cy = (left_box[0] + left_box[2]) // 2, chart_top + 120
    radius = 72
    inner = 46

    if total > 0:
        scope_1_angle = 360 * scope_1 / total

        draw.pieslice(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            start=270,
            end=270 + scope_1_angle,
            fill=GREEN
        )

        draw.pieslice(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            start=270 + scope_1_angle,
            end=630,
            fill=LIME
        )
    else:
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=BORDER
        )

    draw.ellipse(
        (cx - inner, cy - inner, cx + inner, cy + inner),
        fill=WHITE
    )

    draw.text(
        (cx, cy - 17),
        f"{total / 1000:.2f}",
        font=font(25, True),
        fill=GREEN,
        anchor="mm"
    )
    draw.text(
        (cx, cy + 15),
        "tonnes CO2e",
        font=font(13),
        fill=MUTED,
        anchor="mm"
    )

    # Donut legend: both rows stay fully inside the chart card.
    legend_y = chart_top + 205

    draw.rounded_rectangle(
        (92, legend_y + 4, 108, legend_y + 20),
        radius=4,
        fill=GREEN
    )
    label(120, legend_y, "Scope 1", 17, TEXT, True)
    right_label(
        545, legend_y,
        f"{scope_1:,.1f} kg ({scope_1 / total * 100:.1f}%)"
        if total else "0.0 kg (0.0%)",
        16, GREEN, True
    )

    draw.rounded_rectangle(
        (92, legend_y + 38, 108, legend_y + 54),
        radius=4,
        fill=LIME
    )
    label(120, legend_y + 34, "Scope 2", 17, TEXT, True)
    right_label(
        545, legend_y + 34,
        f"{scope_2:,.1f} kg ({scope_2 / total * 100:.1f}%)"
        if total else "0.0 kg (0.0%)",
        16, GREEN, True
    )

    # Right chart card: bar chart.
    right_box = (590, chart_top, 1176, chart_bottom)
    rounded_box(right_box, 18, WHITE, BORDER)

    label(614, chart_top + 20, "EMISSIONS BY SOURCE", 17, MUTED, True)

    bar_values = [
        ("Diesel", diesel_emissions, GREEN),
        ("LPG", lpg_emissions, ORANGE),
        ("Electricity", scope_2, "#91B94B"),
    ]

    plot_x = 730
    plot_right = 1138
    plot_top = chart_top + 75
    plot_bottom = chart_top + 235
    plot_h = plot_bottom - plot_top

    max_value = max([v for _, v, _ in bar_values] + [1])

    for i, (name, value, color) in enumerate(bar_values):
        y = plot_top + i * 56

        label(614, y + 2, name, 16, TEXT, True)

        draw.rounded_rectangle(
            (plot_x, y, plot_right, y + 23),
            radius=8,
            fill="#EDF2ED"
        )

        bar_width = int((plot_right - plot_x) * value / max_value)

        if value > 0:
            draw.rounded_rectangle(
                (plot_x, y, plot_x + max(1, bar_width), y + 23),
                radius=8,
                fill=color
            )

        label(
            plot_x, y + 27,
            f"{value:,.1f} kg CO2e",
            14, MUTED
        )

    label(
        614, chart_top + 253,
        "Source values use illustrative demo factors.",
        14, MUTED
    )

    # =====================================================
    # CONSUMPTION TABLE
    # =====================================================

    table_y = 1030

    section_title(
        64, table_y,
        "Energy consumption",
        "Inputs used for this report."
    )

    table_top = 1105
    table_bottom = 1354

    rounded_box(
        (64, table_top, 1176, table_bottom),
        radius=15,
        fill=WHITE,
        outline=BORDER
    )

    # Table header.
    draw.rounded_rectangle(
        (65, table_top + 1, 1175, table_top + 47),
        radius=14,
        fill=GREEN
    )
    draw.rectangle(
        (65, table_top + 25, 1175, table_top + 47),
        fill=GREEN
    )

    label(88, table_top + 12, "CONSUMPTION SOURCE", 15, WHITE, True)
    label(660, table_top + 12, "QUANTITY", 15, WHITE, True)
    label(930, table_top + 12, "EMISSIONS", 15, WHITE, True)

    table_rows = [
        ("Electricity", f"{electricity:,.2f} kWh", scope_2),
        ("Diesel", f"{diesel:,.2f} litres", diesel_emissions),
        ("LPG", f"{lpg:,.2f} kg", lpg_emissions),
        ("Production", f"{production:,.2f} units", None),
    ]

    row_h = 49

    for i, (name, quantity, emissions) in enumerate(table_rows):
        y = table_top + 48 + i * row_h

        if i % 2 == 1:
            draw.rectangle(
                (66, y, 1174, y + row_h),
                fill="#F7FAF7"
            )

        label(88, y + 13, name, 17, TEXT, i == 3)
        label(660, y + 13, quantity, 17, TEXT)

        if emissions is not None:
            right_label(
                1138, y + 13,
                f"{emissions:,.2f} kg",
                17, GREEN, True
            )
        else:
            right_label(1138, y + 13, "—", 17, MUTED)

    # =====================================================
    # FACTORS AND METHODOLOGY
    # =====================================================

    method_y = 1380

    section_title(
        64, method_y,
        "Methodology & emission factors",
        "Calculated as consumption multiplied by the corresponding factor."
    )

    method_top = 1450

    rounded_box(
        (64, method_top, 1176, 1570),
        radius=15,
        fill=PALE_GREEN
    )

    label(
        88, method_top + 18,
        "Electricity", 16, GREEN, True
    )
    label(
        88, method_top + 44,
        "0.71 kg CO2e/kWh", 16, TEXT
    )

    label(
        445, method_top + 18,
        "Diesel", 16, GREEN, True
    )
    label(
        445, method_top + 44,
        "2.68 kg CO2e/litre", 16, TEXT
    )

    label(
        790, method_top + 18,
        "LPG", 16, GREEN, True
    )
    label(
        790, method_top + 44,
        "3.00 kg CO2e/kg", 16, TEXT
    )

    # =====================================================
    # REDUCTION TARGET PROGRESS
    # =====================================================

    target_y = 1590

    section_title(
        64, target_y,
        "Reduction target progress",
        "Progress against the saved emissions-reduction goal."
    )

    rounded_box(
        (64, 1660, 1176, 1795),
        radius=15,
        fill=PALE_LIME if target else PALE_GREEN
    )

    if target and target.get("configured"):
        label(
            88, 1677,
            f"Baseline: {target['baseline_kg_co2e']:.2f} kg CO2e",
            16, GREEN, True
        )
        label(
            88, 1707,
            f"Target: {target['target_kg_co2e']:.2f} kg CO2e "
            f"({target['reduction_percent']:.1f}% reduction)",
            16, TEXT
        )
        current_value = target.get("current_kg_co2e")
        current_text = (
            f"Current: {current_value:.2f} kg CO2e"
            if current_value is not None
            else "Current emissions: unavailable"
        )
        label(650, 1677, current_text, 16, GREEN, True)
        label(
            650, 1707,
            f"Deadline: {target['deadline']}",
            16, TEXT
        )

        progress = target.get("progress_percent")
        if progress is not None:
            progress = max(0, min(100, float(progress)))
            label(
                88, 1744,
                f"Progress: {progress:.1f}%",
                15, GREEN, True
            )
            rounded_box(
                (270, 1748, 1135, 1765),
                radius=8,
                fill=BORDER
            )
            if progress > 0:
                rounded_box(
                    (270, 1748, 270 + 865 * progress / 100, 1765),
                    radius=8,
                    fill=GREEN
                )

        status_text = (
            "TARGET ACHIEVED"
            if target.get("target_reached")
            else "TARGET NOT YET ACHIEVED"
        )
        label(88, 1770, status_text, 13, GREEN, True)
    else:
        label(
            88, 1685,
            "No reduction target configured yet.",
            17, GREEN, True
        )
        label(
            88, 1720,
            "Set a baseline, reduction percentage, and deadline in the dashboard.",
            15, TEXT
        )

    # =====================================================
    # FOOTER
    # =====================================================

    line(64, 1875, 1176, 1875)

    label(
        64, 1890,
        "CarbonKhata | Measure clearly. Reduce intelligently.",
        13, GREEN, True
    )

    right_label(
        1176, 1890,
        "Generated report",
        13, MUTED
    )

    # ---------- Export as PDF ----------

    image.save(
        output_path,
        format="PDF",
        resolution=150.0,
        title="CarbonKhata Carbon Emissions Report",
        author="CarbonKhata"
    )

    return output_path