# -*- coding: utf-8 -*-
"""
Momentum Mind Store - "Inventory Manager PRO"
Builds a no-VBA, mobile-app-styled Inventory Management & Invoicing workbook.

Run:  python3 build_template.py
Out:  Momentum-Mind-Inventory-Manager-PRO.xlsx
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.comments import Comment

# ── 1. DESIGN TOKENS — the "Momentum Midnight" palette ───────────────────────
INK, SLATE, MUTED, BORDER = "0F172A", "334155", "64748B", "E2E8F0"
BG, CARD, WHITE = "F1F5F9", "FFFFFF", "FFFFFF"
INDIGO, INDIGO_DK, INDIGO_LT = "4F46E5", "3730A3", "EEF2FF"
GREEN, GREEN_BG = "047857", "ECFDF5"
RED, RED_BG = "B91C1C", "FEE2E2"
AMBER, AMBER_BG = "B45309", "FFFBEB"
WA_GREEN, INPUT_BG, INPUT_BRD = "25D366", "FFF9DB", "F59E0B"
FONT = "Segoe UI"

def fnt(sz=11, b=False, c=INK, i=False):
    return Font(name=FONT, size=sz, bold=b, color=c, italic=i)

def fill(hexcol):
    return PatternFill("solid", fgColor=hexcol)

def align(h="left", v="center", wrap=False, indent=0):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap, indent=indent)

HAIR = Side(style="thin", color=BORDER)
BOX = Border(left=HAIR, right=HAIR, top=HAIR, bottom=HAIR)
def gold_box():
    s = Side(style="medium", color=INPUT_BRD)
    return Border(left=s, right=s, top=s, bottom=s)

MONEY = '$#,##0.00;[Red]($#,##0.00);"-"'
INT   = '#,##0;[Red](#,##0);"-"'
PCT   = '0.0%'
DATE  = 'dd-mmm-yyyy'

# ── 2. WORKBOOK-WIDE HELPERS ─────────────────────────────────────────────────
NAV_TARGETS = {
    "dash":  ("🏠 Dashboard",   "Dashboard"),
    "items": ("📦 Products",    "Item Master"),
    "log":   ("✍️ Log Sale",    "Log Transaction"),
    "inv":   ("🧾 Invoice",     "Invoice Generator"),
    "start": ("🚀 Start Here",  "Start Here"),
}

def app_shell(ws, last_col, nav_slots, freeze="A4", tab=INDIGO):
    """Paint the app chrome: hide gridlines/headings, nav bar, divider, canvas."""
    ws.sheet_view.showGridLines = False
    ws.sheet_view.showRowColHeaders = False
    ws.sheet_properties.tabColor = tab
    ws.freeze_panes = freeze
    ws.row_dimensions[1].height = 40
    ws.row_dimensions[2].height = 6

    # canvas background
    for r in range(1, 320):
        for c in range(1, last_col + 1):
            ws.cell(r, c).fill = fill(BG)

    # nav bar (row 1) + accent divider (row 2)
    for c in range(1, last_col + 1):
        ws.cell(1, c).fill = fill(INK)
        ws.cell(2, c).fill = fill(INDIGO)
    for rng, key in nav_slots:
        label, target = NAV_TARGETS[key]
        if ":" in rng:
            ws.merge_cells(rng)
        cell = ws[rng.split(":")[0]]
        cell.value = '=HYPERLINK("#\'{}\'!A1","{}")'.format(target, label)
        cell.font = fnt(11, True, WHITE)
        cell.fill = fill(INK)
        cell.alignment = align("center", "center")

def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w

def heights(ws, first, last, h):
    for r in range(first, last + 1):
        ws.row_dimensions[r].height = h

def put(ws, ref, value, font=None, bg=None, al=None, numfmt=None, border=None):
    c = ws[ref]
    c.value = value
    if font: c.font = font
    if bg: c.fill = fill(bg)
    if al: c.alignment = al
    if numfmt: c.number_format = numfmt
    if border: c.border = border
    return c

def title_block(ws, span, kicker, headline, sub):
    """Big app-style screen title. span = ('A4','J4') style column letters."""
    a, b = span
    ws.merge_cells(f"{a}4:{b}4"); ws.merge_cells(f"{a}5:{b}5"); ws.merge_cells(f"{a}6:{b}6")
    put(ws, f"{a}4", kicker, fnt(9, True, INDIGO), BG, align("left", "bottom", indent=1))
    put(ws, f"{a}5", headline, fnt(22, True, INK), BG, align("left", "center", indent=1))
    put(ws, f"{a}6", sub, fnt(10, False, MUTED), BG, align("left", "top", indent=1))
    ws.row_dimensions[4].height = 20
    ws.row_dimensions[5].height = 34
    ws.row_dimensions[6].height = 20

# Absolute ranges reused across sheets
IM   = "'Item Master'"
LG   = "'Log Transaction'"
R_SKU   = f"{IM}!$A$4:$A$53"
R_NAME  = f"{IM}!$B$4:$B$53"
R_COST  = f"{IM}!$D$4:$D$53"
R_PRICE = f"{IM}!$E$4:$E$53"
R_MAX   = f"{IM}!$F$4:$F$53"
R_RPT   = f"{IM}!$G$4:$G$53"
R_SUPP  = f"{IM}!$H$4:$H$53"
R_PHONE = f"{IM}!$I$4:$I$53"
R_MAIL  = f"{IM}!$J$4:$J$53"
L_DATE  = f"{LG}!$A$4:$A$303"
L_ID    = f"{LG}!$B$4:$B$303"
L_SKU   = f"{LG}!$C$4:$C$303"
L_TYPE  = f"{LG}!$D$4:$D$303"
L_QTY   = f"{LG}!$E$4:$E$303"
L_KEY   = f"{LG}!$G$4:$G$303"

def XL(lookup, arr, ret, notfound='""'):
    return f'_xlfn.XLOOKUP({lookup},{arr},{ret},{notfound})'

wb = openpyxl.Workbook()
wb.remove(wb.active)

# ═════════════════════════════════════════════════════════════════════════════
# SHEET 1 — START HERE
# ═════════════════════════════════════════════════════════════════════════════
sh = wb.create_sheet("Start Here")
widths(sh, {"A": 3, "B": 20, "C": 20, "D": 20, "E": 20, "F": 20, "G": 3})
app_shell(sh, 7, [("A1:B1", "dash"), ("C1", "items"), ("D1", "log"),
                  ("E1", "inv"), ("F1:G1", "start")], freeze="A3", tab=INDIGO_DK)

sh.merge_cells("B4:F4"); sh.merge_cells("B5:F5"); sh.merge_cells("B6:F6")
put(sh, "B4", "MOMENTUM MIND STORE", fnt(9, True, INDIGO), BG, align("left", "bottom"))
put(sh, "B5", "📦 Inventory Manager PRO", fnt(24, True, INK), BG, align("left", "center"))
put(sh, "B6", "Track stock, log every sale, and send invoices — from your phone.", fnt(10, False, MUTED), BG, align("left", "top"))
sh.row_dimensions[4].height = 20; sh.row_dimensions[5].height = 38; sh.row_dimensions[6].height = 22

STEPS = [
    ("1", "📦", "Add your products", "Open the Products screen and fill one row per item. SKU must be unique — it is the key that powers everything else."),
    ("2", "⚙️", "Set your business details", "Open Settings and enter your shop name, contact details, tax rate and invoice prefix. Every invoice reads from there."),
    ("3", "✍️", "Log every movement", "On the Log Sale screen, tap a new row. Pick the SKU from the dropdown, choose IN (stock received), OUT (sold) or SHRINKAGE (damaged/lost), and enter the quantity. The Total fills itself."),
    ("4", "🧾", "Generate an invoice", "Type or pick a Transaction ID at the top of the Invoice screen. Every line for that ID appears instantly. Share ▸ Export as PDF."),
    ("5", "🏠", "Watch the Dashboard", "Live stock levels, low-stock alerts, and one-tap WhatsApp / Email reorder buttons that write the message for you."),
]
row = 8
for num, icon, head, body in STEPS:
    sh.merge_cells(f"B{row}:F{row}")
    sh.merge_cells(f"B{row+1}:F{row+1}")
    put(sh, f"B{row}", f"{icon}  STEP {num} — {head}", fnt(12, True, INK), CARD, align("left", "center", indent=1))
    put(sh, f"B{row+1}", body, fnt(10, False, SLATE), CARD, align("left", "top", wrap=True, indent=1))
    for c in range(2, 7):
        sh.cell(row, c).fill = fill(CARD); sh.cell(row, c).border = BOX
        sh.cell(row + 1, c).fill = fill(CARD); sh.cell(row + 1, c).border = BOX
    sh.row_dimensions[row].height = 32
    sh.row_dimensions[row + 1].height = 46
    row += 3

sh.merge_cells(f"B{row}:F{row}")
put(sh, f"B{row}", "🎨 COLOUR KEY", fnt(11, True, INDIGO), BG, align("left", "center"))
row += 1
LEGEND = [("🟡  Yellow cells", "You type here."),
          ("⬜  White cells", "Calculated automatically — do not overwrite."),
          ("🟦  Dark bar (top)", "Tap any label to jump between screens.")]
for lab, desc in LEGEND:
    put(sh, f"B{row}", lab, fnt(10, True, INK), CARD, align("left", "center", indent=1))
    sh.merge_cells(f"C{row}:F{row}")
    put(sh, f"C{row}", desc, fnt(10, False, SLATE), CARD, align("left", "center", indent=1))
    for c in range(2, 7):
        sh.cell(row, c).fill = fill(CARD); sh.cell(row, c).border = BOX
    sh.row_dimensions[row].height = 30
    row += 1

row += 1
sh.merge_cells(f"B{row}:F{row}")
put(sh, f"B{row}", "💬 NEED HELP?", fnt(11, True, INDIGO), BG, align("left", "center"))
row += 1
SUPPORT = [
    ("✉️  Support email", '=HYPERLINK("mailto:support@momentummindstore.com?subject=Inventory%20Manager%20PRO%20-%20Support","support@momentummindstore.com")'),
    ("🛍️  Etsy shop", '=HYPERLINK("https://www.etsy.com/shop/MomentumMindStore","etsy.com/shop/MomentumMindStore")'),
    ("📖  Video walkthrough", '=HYPERLINK("https://www.momentummindstore.com/inventory-pro-guide","Watch the 4-minute setup video")'),
    ("⭐  Loved it?", '=HYPERLINK("https://www.etsy.com/your/purchases","Leave a review — it genuinely helps a small shop")'),
]
for lab, formula in SUPPORT:
    put(sh, f"B{row}", lab, fnt(10, True, INK), CARD, align("left", "center", indent=1))
    sh.merge_cells(f"C{row}:F{row}")
    put(sh, f"C{row}", formula, fnt(10, True, INDIGO), CARD, align("left", "center", indent=1))
    for c in range(2, 7):
        sh.cell(row, c).fill = fill(CARD); sh.cell(row, c).border = BOX
    sh.row_dimensions[row].height = 30
    row += 1

row += 1
sh.merge_cells(f"B{row}:F{row}")
put(sh, f"B{row}", "© Momentum Mind Store — single-shop licence. No resale or redistribution of this file.",
    fnt(9, False, MUTED, i=True), BG, align("left", "center"))

# ═════════════════════════════════════════════════════════════════════════════
# SHEET 2 — DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
db = wb.create_sheet("Dashboard")
widths(db, {"A": 14, "B": 30, "C": 11, "D": 12, "E": 14, "F": 20, "G": 18, "H": 16, "I": 14})
db.column_dimensions["I"].hidden = True
app_shell(db, 9, [("A1:B1", "dash"), ("C1:D1", "items"), ("E1", "log"),
                  ("F1", "inv"), ("G1:H1", "start")], freeze="A8", tab=INDIGO)
title_block(db, ("A", "H"), "LIVE OVERVIEW", "🏠 Dashboard",
            "Stock recalculates the moment you log a transaction.")

# KPI strip (row 7)
db.row_dimensions[7].height = 46
KPIS = [
    ("A7:B7", "🏷️  ACTIVE SKUs", "=COUNTA(" + R_SKU + ")", INT, INDIGO_LT, INDIGO_DK),
    ("C7:D7", "📦  UNITS IN STOCK", "=SUM($E$9:$E$58)", INT, INDIGO_LT, INDIGO_DK),
    ("E7:F7", "💰  STOCK VALUE (COST)", "=SUM($I$9:$I$58)", MONEY, GREEN_BG, GREEN),
    ("G7:H7", "⚠️  NEEDS REORDER", '=COUNTIF($F$9:$F$58,"⚠️ REORDER NOW")', INT, RED_BG, RED),
]
for rng, label, formula, nf, bgc, txt in KPIS:
    db.merge_cells(rng)
    a = rng.split(":")[0]
    put(db, a, formula, fnt(16, True, txt), bgc, align("center", "center"), nf, BOX)
    db[a].comment = Comment(label, "Momentum Mind Store")
    for col in range(openpyxl.utils.column_index_from_string(a[0]),
                     openpyxl.utils.column_index_from_string(rng.split(":")[1][0]) + 1):
        db.cell(7, col).fill = fill(bgc); db.cell(7, col).border = BOX

# Header row 8
DB_HEAD = ["SKU", "📦 Product", "⬇ Total IN", "⬆ Total OUT", "📊 Current Stock",
           "🚦 Stock Status", "💬 WhatsApp Order", "✉️ Email Order", "Value"]
db.row_dimensions[8].height = 36
for i, h in enumerate(DB_HEAD, start=1):
    put(db, f"{openpyxl.utils.get_column_letter(i)}8", h, fnt(10, True, WHITE), INK,
        align("center", "center", wrap=True), border=BOX)

FIRST, LAST = 9, 58
heights(db, FIRST, LAST, 32)

WA_MSG = ('"Hello "&' + XL("$A9", R_SKU, R_SUPP, '"Supplier"') +
          '&", we urgently need more "&$B9&". Current stock is only "&TEXT($E9,"0")&'
          '" units. Please confirm availability and your fastest lead time. Thank you - Momentum Mind Store."')
MAIL_BODY = ('"Hello "&' + XL("$A9", R_SKU, R_SUPP, '"Supplier"') +
             '&"," & CHAR(10) & "We urgently need to restock "&$B9&" (SKU "&$A9&'
             '"). Our current stock is "&TEXT($E9,"0")&" units, which is below our reorder threshold." & CHAR(10) & '
             '"Please confirm availability, unit price and lead time by return." & CHAR(10) & '
             '"Kind regards," & CHAR(10) & "Momentum Mind Store"')

PHONE = XL("$A9", R_SKU, R_PHONE, '""')
PHONE_CLEAN = ('SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE('
               + PHONE + ',"+",""),"-","")," ",""),"(",""),")",""),".","")')

for r in range(FIRST, LAST + 1):
    n = r - FIRST + 1
    a = lambda ref: ref.replace("9", str(r)) if False else ref
    put(db, f"A{r}", f'=IF(INDEX({R_SKU},{n})="","",INDEX({R_SKU},{n}))',
        fnt(10, True, SLATE), CARD, align("left", "center", indent=1), border=BOX)
    put(db, f"B{r}", f'=IF($A{r}="","",{XL(f"$A{r}", R_SKU, R_NAME, chr(34)+chr(34))})',
        fnt(10, False, INK), CARD, align("left", "center", indent=1), border=BOX)
    put(db, f"C{r}", f'=IF($A{r}="","",SUMIFS({L_QTY},{L_SKU},$A{r},{L_TYPE},"IN"))',
        fnt(10, False, MUTED), CARD, align("center", "center"), INT, BOX)
    put(db, f"D{r}", f'=IF($A{r}="","",SUMIFS({L_QTY},{L_SKU},$A{r},{L_TYPE},"OUT")'
                     f'+SUMIFS({L_QTY},{L_SKU},$A{r},{L_TYPE},"SHRINKAGE"))',
        fnt(10, False, MUTED), CARD, align("center", "center"), INT, BOX)
    put(db, f"E{r}", f'=IF($A{r}="","",$C{r}-$D{r})',
        fnt(12, True, INK), CARD, align("center", "center"), INT, BOX)
    put(db, f"F{r}", f'=IF($A{r}="","",IF($E{r}<={XL(f"$A{r}", R_SKU, R_MAX, "0")}*0.1,'
                     f'"⚠️ REORDER NOW","✅ IN STOCK"))',
        fnt(10, True, INK), CARD, align("center", "center"), border=BOX)
    wa = WA_MSG.replace("$A9", f"$A{r}").replace("$B9", f"$B{r}").replace("$E9", f"$E{r}")
    ph = PHONE_CLEAN.replace("$A9", f"$A{r}")
    put(db, f"G{r}",
        f'=IF($A{r}="","",IF($F{r}="⚠️ REORDER NOW",'
        f'HYPERLINK("https://wa.me/"&{ph}&"?text="&SUBSTITUTE({wa}," ","%20"),"💬  ORDER NOW"),""))',
        fnt(10, True, WHITE), CARD, align("center", "center"), border=BOX)
    mb = MAIL_BODY.replace("$A9", f"$A{r}").replace("$B9", f"$B{r}").replace("$E9", f"$E{r}")
    mail = XL(f"$A{r}", R_SKU, R_MAIL, '""')
    put(db, f"H{r}",
        f'=IF($A{r}="","",IF($F{r}="⚠️ REORDER NOW",'
        f'HYPERLINK("mailto:"&{mail}&"?subject="&SUBSTITUTE("URGENT restock request - "&$B{r}&" ("&$A{r}&")"," ","%20")'
        f'&"&body="&SUBSTITUTE(SUBSTITUTE({mb}," ","%20"),CHAR(10),"%0D%0A"),"✉️  EMAIL"),""))',
        fnt(10, True, WHITE), CARD, align("center", "center"), border=BOX)
    put(db, f"I{r}", f'=IF($A{r}="","",$E{r}*{XL(f"$A{r}", R_SKU, R_COST, "0")})',
        fnt(10, False, MUTED), CARD, align("center", "center"), MONEY, BOX)

rng_status = f"F{FIRST}:F{LAST}"
db.conditional_formatting.add(rng_status, FormulaRule(
    formula=[f'$F{FIRST}="⚠️ REORDER NOW"'], fill=fill(RED_BG),
    font=Font(name=FONT, size=10, bold=True, color=RED), stopIfTrue=False))
db.conditional_formatting.add(rng_status, FormulaRule(
    formula=[f'$F{FIRST}="✅ IN STOCK"'], fill=fill(GREEN_BG),
    font=Font(name=FONT, size=10, bold=True, color=GREEN), stopIfTrue=False))
db.conditional_formatting.add(f"E{FIRST}:E{LAST}", FormulaRule(
    formula=[f'AND($A{FIRST}<>"",$E{FIRST}<=0)'], fill=fill(RED_BG),
    font=Font(name=FONT, size=12, bold=True, color=RED), stopIfTrue=False))
db.conditional_formatting.add(f"G{FIRST}:G{LAST}", FormulaRule(
    formula=[f'$G{FIRST}<>""'], fill=fill(WA_GREEN),
    font=Font(name=FONT, size=10, bold=True, color=WHITE), stopIfTrue=True))
db.conditional_formatting.add(f"H{FIRST}:H{LAST}", FormulaRule(
    formula=[f'$H{FIRST}<>""'], fill=fill(INDIGO),
    font=Font(name=FONT, size=10, bold=True, color=WHITE), stopIfTrue=True))

# ═════════════════════════════════════════════════════════════════════════════
# SHEET 3 — ITEM MASTER
# ═════════════════════════════════════════════════════════════════════════════
im = wb.create_sheet("Item Master")
widths(im, {"A": 14, "B": 32, "C": 16, "D": 12, "E": 12, "F": 12, "G": 14,
            "H": 22, "I": 18, "J": 28})
app_shell(im, 10, [("A1:B1", "dash"), ("C1:D1", "items"), ("E1:F1", "log"),
                   ("G1:H1", "inv"), ("I1:J1", "start")], freeze="A4", tab=INDIGO)

IM_HEAD = ["SKU", "📦 Product Name", "Category", "Cost", "Price", "Max Stock",
           "Reorder Point", "Supplier Name", "📞 Supp. Phone", "✉️ Supp. Email"]
im.row_dimensions[3].height = 38
for i, h in enumerate(IM_HEAD, start=1):
    put(im, f"{openpyxl.utils.get_column_letter(i)}3", h, fnt(10, True, WHITE), INK,
        align("center", "center", wrap=True))

PRODUCTS = [
    ("LAV-001", "🕯️ Lavender Soy Candle 220g", "Home Fragrance", 6.50, 18.00, 120, 25,
     "Aurora Wax Co.", "15551234567", "orders@aurorawax.com"),
    ("CER-014", "☕ Ceramic Mug — Sand", "Drinkware", 4.20, 14.00, 200, 40,
     "Kiln & Clay Ltd", "15559876543", "sales@kilnclay.com"),
    ("TOT-007", "👜 Canvas Tote Bag — Natural", "Bags", 3.80, 12.50, 150, 30,
     "NorthLoom Textiles", "15554567890", "hello@northloom.com"),
    ("JRN-002", "📓 Linen Journal A5", "Stationery", 5.10, 16.00, 100, 20,
     "PaperFold Studio", "15553216549", "supply@paperfold.com"),
    ("SKN-021", "🧴 Botanical Body Oil 100ml", "Skincare", 7.90, 24.00, 80, 16,
     "Botanica Labs", "15557778888", "orders@botanicalabs.com"),
    ("TEA-009", "🍵 Loose Leaf Tea 200g", "Pantry", 5.60, 17.50, 90, 18,
     "Verde Leaf Imports", "15552223333", "buy@verdeleaf.com"),
]
heights(im, 4, 53, 32)
for idx, p in enumerate(PRODUCTS):
    r = 4 + idx
    for cidx, val in enumerate(p, start=1):
        cell = im.cell(r, cidx, val)
        cell.font = fnt(10, cidx == 1, INK)
        cell.alignment = align("center" if cidx in (1, 4, 5, 6, 7) else "left", "center",
                               indent=0 if cidx in (1, 4, 5, 6, 7) else 1)
        if cidx in (4, 5): cell.number_format = MONEY
        if cidx in (6, 7): cell.number_format = INT
        if cidx in (9,): cell.number_format = "@"
for r in range(4, 54):
    for c in range(1, 11):
        cell = im.cell(r, c)
        cell.fill = fill(INPUT_BG); cell.border = BOX
        if cell.font.name != FONT:
            cell.font = fnt(10)
        if c in (4, 5): cell.number_format = MONEY
        if c in (6, 7): cell.number_format = INT
        if c == 9: cell.number_format = "@"

tbl_items = Table(displayName="tbl_Items", ref="A3:J53")
tbl_items.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True,
                                          showColumnStripes=False, showFirstColumn=False,
                                          showLastColumn=False)
im.add_table(tbl_items)
im["A3"].comment = Comment(
    "SKU must be UNIQUE — it is the key linking Products, Log and Dashboard.\n"
    "Phone: digits only, country code first, no + or spaces (e.g. 15551234567).",
    "Momentum Mind Store")

# ═════════════════════════════════════════════════════════════════════════════
# SHEET 4 — LOG TRANSACTION
# ═════════════════════════════════════════════════════════════════════════════
lg = wb.create_sheet("Log Transaction")
widths(lg, {"A": 14, "B": 16, "C": 18, "D": 14, "E": 10, "F": 14, "G": 22})
lg.column_dimensions["G"].hidden = True
app_shell(lg, 7, [("A1", "dash"), ("B1", "items"), ("C1", "log"),
                  ("D1:E1", "inv"), ("F1:G1", "start")], freeze="A4", tab=GREEN)

LG_HEAD = ["📅 Date", "🆔 ID", "🏷️ SKU", "🔄 Type", "🔢 Qty", "💵 Total", "Line Key"]
lg.row_dimensions[3].height = 38
for i, h in enumerate(LG_HEAD, start=1):
    put(lg, f"{openpyxl.utils.get_column_letter(i)}3", h, fnt(10, True, WHITE), INK,
        align("center", "center", wrap=True))

import datetime as _dt
TXNS = [
    ("2026-08-01", "PO-2001", "LAV-001", "IN", 100),
    ("2026-08-01", "PO-2001", "CER-014", "IN", 150),
    ("2026-08-01", "PO-2002", "TOT-007", "IN", 120),
    ("2026-08-02", "PO-2002", "JRN-002", "IN", 80),
    ("2026-08-02", "PO-2003", "SKN-021", "IN", 60),
    ("2026-08-02", "PO-2003", "TEA-009", "IN", 70),
    ("2026-08-05", "INV-1001", "LAV-001", "OUT", 2),
    ("2026-08-05", "INV-1001", "CER-014", "OUT", 3),
    ("2026-08-05", "INV-1001", "JRN-002", "OUT", 1),
    ("2026-08-07", "INV-1002", "TOT-007", "OUT", 4),
    ("2026-08-07", "INV-1002", "TEA-009", "OUT", 2),
    ("2026-08-09", "INV-1003", "SKN-021", "OUT", 55),
    ("2026-08-10", "INV-1004", "LAV-001", "OUT", 88),
    ("2026-08-11", "ADJ-3001", "TEA-009", "SHRINKAGE", 3),
    ("2026-08-12", "INV-1005", "CER-014", "OUT", 12),
]
heights(lg, 4, 303, 32)
for r in range(4, 304):
    i = r - 4
    if i < len(TXNS):
        d, tid, sku, typ, qty = TXNS[i]
        lg.cell(r, 1, _dt.date(*[int(x) for x in d.split("-")]))
        lg.cell(r, 2, tid); lg.cell(r, 3, sku); lg.cell(r, 4, typ); lg.cell(r, 5, qty)
    # F — Total (cost for IN, price for OUT/SHRINKAGE)
    put(lg, f"F{r}",
        f'=IF($C{r}="","",IF($D{r}="IN",$E{r}*{XL(f"$C{r}", R_SKU, R_COST, "0")},'
        f'$E{r}*{XL(f"$C{r}", R_SKU, R_PRICE, "0")}))',
        fnt(10, True, INK), CARD, align("center", "center"), MONEY, BOX)
    # G — Line Key (invoice engine)
    put(lg, f"G{r}",
        f'=IF($B{r}="","",IF($D{r}="OUT",$B{r}&"|"&COUNTIFS($B$4:$B{r},$B{r},$D$4:$D{r},"OUT"),""))',
        fnt(9, False, MUTED), CARD, align("center", "center"), border=BOX)
    for c in (1, 2, 3, 4, 5):
        cell = lg.cell(r, c)
        cell.fill = fill(INPUT_BG); cell.border = BOX
        cell.font = fnt(11, c in (2, 3), INK)
        cell.alignment = align("center", "center")
    lg.cell(r, 1).number_format = DATE
    lg.cell(r, 5).number_format = INT

tbl_log = Table(displayName="tbl_Log", ref="A3:G303")
tbl_log.tableStyleInfo = TableStyleInfo(name="TableStyleLight11", showRowStripes=True,
                                        showColumnStripes=False, showFirstColumn=False,
                                        showLastColumn=False)
lg.add_table(tbl_log)

dv_sku = DataValidation(type="list", formula1="SKU_List", allow_blank=True, showDropDown=False)
dv_sku.error = "Pick an existing SKU. Add new products on the Products screen first."
dv_sku.errorTitle = "Unknown SKU"
dv_sku.prompt = "Tap the arrow and choose a product."
dv_sku.promptTitle = "🏷️ Select SKU"
lg.add_data_validation(dv_sku); dv_sku.add("C4:C303")

dv_type = DataValidation(type="list", formula1='"IN,OUT,SHRINKAGE"', allow_blank=True, showDropDown=False)
dv_type.error = "Choose IN, OUT or SHRINKAGE."
dv_type.errorTitle = "Invalid type"
dv_type.prompt = "IN = stock received · OUT = sold · SHRINKAGE = damaged/lost"
dv_type.promptTitle = "🔄 Movement type"
lg.add_data_validation(dv_type); dv_type.add("D4:D303")

dv_qty = DataValidation(type="whole", operator="greaterThan", formula1="0", allow_blank=True)
dv_qty.error = "Quantity must be a whole number above zero."
dv_qty.errorTitle = "Invalid quantity"
lg.add_data_validation(dv_qty); dv_qty.add("E4:E303")

lg.conditional_formatting.add("D4:D303", FormulaRule(
    formula=['$D4="IN"'], fill=fill(GREEN_BG),
    font=Font(name=FONT, size=11, bold=True, color=GREEN)))
lg.conditional_formatting.add("D4:D303", FormulaRule(
    formula=['$D4="OUT"'], fill=fill(INDIGO_LT),
    font=Font(name=FONT, size=11, bold=True, color=INDIGO_DK)))
lg.conditional_formatting.add("D4:D303", FormulaRule(
    formula=['$D4="SHRINKAGE"'], fill=fill(AMBER_BG),
    font=Font(name=FONT, size=11, bold=True, color=AMBER)))

# ═════════════════════════════════════════════════════════════════════════════
# SHEET 5 — INVOICE GENERATOR
# ═════════════════════════════════════════════════════════════════════════════
iv = wb.create_sheet("Invoice Generator")
widths(iv, {"A": 15, "B": 28, "C": 10, "D": 15, "E": 15, "F": 15})
app_shell(iv, 6, [("A1", "dash"), ("B1", "items"), ("C1:D1", "log"),
                  ("E1", "inv"), ("F1", "start")], freeze="A4", tab=AMBER)

iv.merge_cells("A4:C4"); iv.merge_cells("A5:C5")
put(iv, "A4", "=Settings!$C$8", fnt(20, True, INK), BG, align("left", "center"))
put(iv, "A5", '=Settings!$C$9&"  ·  "&Settings!$C$10', fnt(10, False, MUTED), BG, align("left", "center"))
iv.merge_cells("D4:E5")
put(iv, "D4", "🧾 INVOICE", fnt(26, True, INDIGO), BG, align("right", "center"))
iv.row_dimensions[4].height = 30; iv.row_dimensions[5].height = 24
iv.row_dimensions[6].height = 10

put(iv, "A7", "🔎 TRANSACTION ID", fnt(10, True, WHITE), INK, align("center", "center"), border=BOX)
iv.merge_cells("B7:C7")
put(iv, "B7", "INV-1001", fnt(14, True, INK), INPUT_BG, align("center", "center"), border=gold_box())
put(iv, "D7", "Invoice No.", fnt(10, True, SLATE), BG, align("right", "center"))
put(iv, "E7", '=IF($B$7="","",Settings!$C$14&$B$7)', fnt(12, True, INDIGO), CARD, align("center", "center"), border=BOX)
iv.row_dimensions[7].height = 36

put(iv, "A8", "📅 DATE", fnt(10, True, WHITE), INK, align("center", "center"), border=BOX)
iv.merge_cells("B8:C8")
put(iv, "B8", f'=IFERROR(INDEX({L_DATE},MATCH($B$7,{L_ID},0)),TODAY())',
    fnt(11, False, INK), CARD, align("center", "center"), DATE, BOX)
put(iv, "D8", "Due", fnt(10, True, SLATE), BG, align("right", "center"))
put(iv, "E8", '=IF($B$8="","",$B$8+Settings!$C$15)', fnt(11, False, INK), CARD, align("center", "center"), DATE, BOX)
iv.row_dimensions[8].height = 32

put(iv, "A9", "👤 BILL TO", fnt(10, True, WHITE), INK, align("center", "center"), border=BOX)
iv.merge_cells("B9:E9")
put(iv, "B9", "Customer name · email · address", fnt(11, False, MUTED, i=True), INPUT_BG,
    align("left", "center", indent=1), border=gold_box())
iv.row_dimensions[9].height = 34
iv.row_dimensions[10].height = 12

IV_HEAD = [("A11", "SKU"), ("B11", "📦 Description"), ("C11", "Qty"),
           ("D11", "Unit Price"), ("E11", "Line Total")]
iv.row_dimensions[11].height = 34
for ref, h in IV_HEAD:
    put(iv, ref, h, fnt(10, True, WHITE), INK, align("center", "center"), border=BOX)

IV_FIRST, IV_LAST = 12, 26
heights(iv, IV_FIRST, IV_LAST, 30)
for r in range(IV_FIRST, IV_LAST + 1):
    n = r - IV_FIRST + 1
    key = f'$B$7&"|"&{n}'
    put(iv, f"A{r}", f'=IFERROR(INDEX({L_SKU},MATCH({key},{L_KEY},0)),"")',
        fnt(10, True, SLATE), CARD, align("center", "center"), border=BOX)
    put(iv, f"B{r}", f'=IF($A{r}="","",{XL(f"$A{r}", R_SKU, R_NAME, chr(34)+chr(34))})',
        fnt(10, False, INK), CARD, align("left", "center", indent=1), border=BOX)
    put(iv, f"C{r}", f'=IFERROR(INDEX({L_QTY},MATCH({key},{L_KEY},0)),"")',
        fnt(10, False, INK), CARD, align("center", "center"), INT, BOX)
    put(iv, f"D{r}", f'=IF($A{r}="","",{XL(f"$A{r}", R_SKU, R_PRICE, "0")})',
        fnt(10, False, INK), CARD, align("center", "center"), MONEY, BOX)
    put(iv, f"E{r}", f'=IF($A{r}="","",$C{r}*$D{r})',
        fnt(10, True, INK), CARD, align("center", "center"), MONEY, BOX)

iv.row_dimensions[27].height = 10
TOTALS = [
    (28, "Subtotal", f"=SUM($E${IV_FIRST}:$E${IV_LAST})", MONEY, CARD, INK, 11, False),
    (29, "Tax rate", "=Settings!$C$12", PCT, CARD, MUTED, 11, False),
    (30, "Tax amount", "=$E$28*$E$29", MONEY, CARD, INK, 11, False),
    (31, "Discount", 0, MONEY, INPUT_BG, INK, 11, False),
    (32, "GRAND TOTAL", "=$E$28+$E$30-$E$31", MONEY, INDIGO, WHITE, 15, True),
]
for r, label, val, nf, bgc, txt, sz, bold in TOTALS:
    iv.row_dimensions[r].height = 34 if r != 32 else 42
    iv.merge_cells(f"C{r}:D{r}")
    put(iv, f"C{r}", label, fnt(sz - 1, True, txt if r == 32 else SLATE),
        bgc if r == 32 else BG, align("right", "center"), border=BOX if r == 32 else None)
    put(iv, f"E{r}", val, fnt(sz, bold or r in (28, 30), txt), bgc,
        align("center", "center"), nf,
        gold_box() if r == 31 else BOX)
    if r == 32:
        for c in (3, 4, 5):
            iv.cell(r, c).fill = fill(INDIGO); iv.cell(r, c).border = BOX

iv.row_dimensions[33].height = 12
iv.merge_cells("A34:E34"); iv.merge_cells("A35:E35"); iv.merge_cells("A36:E36")
put(iv, "A34", '="Payment terms: "&Settings!$C$16', fnt(10, True, SLATE), BG, align("left", "center"))
put(iv, "A35", "=Settings!$C$17", fnt(10, False, MUTED), BG, align("left", "center"))
put(iv, "A36", '="Thank you for supporting "&Settings!$C$8&" 💛"', fnt(11, True, INDIGO), BG, align("center", "center"))
iv.row_dimensions[34].height = 26; iv.row_dimensions[35].height = 26; iv.row_dimensions[36].height = 34

dv_txn = DataValidation(type="list", formula1="TXN_List", allow_blank=True, showDropDown=False)
dv_txn.prompt = "Tap the arrow to pick a Transaction ID you already logged."
dv_txn.promptTitle = "🔎 Transaction ID"
iv.add_data_validation(dv_txn); dv_txn.add("B7")

iv.print_area = "A4:E36"
iv.page_setup.orientation = "portrait"
iv.page_setup.fitToWidth = 1
iv.page_setup.fitToHeight = 1
iv.sheet_properties.pageSetUpPr.fitToPage = True
iv.page_margins.left = iv.page_margins.right = 0.4
iv.page_margins.top = iv.page_margins.bottom = 0.5

# ═════════════════════════════════════════════════════════════════════════════
# SHEET 6 — SETTINGS
# ═════════════════════════════════════════════════════════════════════════════
st = wb.create_sheet("Settings")
widths(st, {"A": 3, "B": 24, "C": 22, "D": 18, "E": 18, "F": 18, "G": 3})
app_shell(st, 7, [("A1:B1", "dash"), ("C1", "items"), ("D1", "log"),
                  ("E1", "inv"), ("F1:G1", "start")], freeze="A4", tab=SLATE)
title_block(st, ("B", "F"), "CONFIGURATION", "⚙️ Settings",
            "Fill these once. Every invoice and message reads from here.")

SETTINGS = [
    (8,  "🏪 Business name", "Momentum Mind Store", None),
    (9,  "✉️ Business email", "hello@momentummindstore.com", None),
    (10, "📞 Business phone", "+1 555 010 2030", "@"),
    (11, "🌐 Website / Etsy", "etsy.com/shop/MomentumMindStore", None),
    (12, "🧾 Tax rate", 0.10, PCT),
    (13, "💱 Currency symbol", "$", None),
    (14, "#️⃣ Invoice prefix", "MMS-", None),
    (15, "📆 Payment due (days)", 14, INT),
    (16, "💳 Payment terms", "Payment due within 14 days of invoice date.", None),
    (17, "🏦 Payment details", "Bank: Example Bank · Acct: 0000 0000 · Ref: your invoice no.", None),
]
for r, label, val, nf in SETTINGS:
    st.row_dimensions[r].height = 34
    put(st, f"B{r}", label, fnt(10, True, INK), CARD, align("left", "center", indent=1), border=BOX)
    st.merge_cells(f"C{r}:F{r}")
    put(st, f"C{r}", val, fnt(11, False, INK), INPUT_BG, align("left", "center", indent=1), nf, gold_box())
    for c in range(4, 7):
        st.cell(r, c).fill = fill(INPUT_BG); st.cell(r, c).border = gold_box()

st.row_dimensions[19].height = 30
st.merge_cells("B19:F19")
put(st, "B19", "🔒 Rows 8–17 are the only cells you edit here. Everything else is automatic.",
    fnt(9, False, MUTED, i=True), BG, align("left", "center"))


# ═════════════════════════════════════════════════════════════════════════════
# NAMES, ORDER, FINAL VIEW STATE
# ═════════════════════════════════════════════════════════════════════════════
wb.defined_names.add(DefinedName("SKU_List", attr_text=f"{IM}!$A$4:$A$53"))
wb.defined_names.add(DefinedName("TXN_List", attr_text=f"{LG}!$B$4:$B$303"))

wb.move_sheet("Start Here", offset=-5)
wb.active = wb.sheetnames.index("Start Here")
for ws in wb.worksheets:
    ws.sheet_view.zoomScale = 100
    ws.sheet_view.showGridLines = False
    ws.sheet_view.showRowColHeaders = False
wb["Dashboard"].sheet_view.tabSelected = False

OUT = "Momentum-Mind-Inventory-Manager-PRO.xlsx"
wb.save(OUT)
print("Built:", OUT)
print("Sheets:", wb.sheetnames)
