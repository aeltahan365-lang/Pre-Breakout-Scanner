# 📦 Inventory Manager PRO — Complete Build Specification
### Momentum Mind Store · Mobile-First Inventory Management & Invoicing for Excel
**No VBA. No macros. Excel 365 / Excel 2021 / Excel Mobile (iOS + Android).**

---

## 0. THE DESIGN SYSTEM — "Momentum Midnight"

### 0.1 Colour palette (exact HEX)

| Token | HEX | Where it is used |
|---|---|---|
| Ink (nav bar) | `#0F172A` | Navigation bar row 1, all table header rows |
| Accent divider | `#4F46E5` | Row 2 — 6px indigo strip under the nav |
| Primary Indigo | `#4F46E5` | Buttons, GRAND TOTAL bar, kickers, links |
| Indigo Deep | `#3730A3` | KPI figures, pressed-state text |
| Indigo Tint | `#EEF2FF` | KPI card backgrounds, "OUT" transaction pills |
| App Canvas | `#F1F5F9` | Every sheet background (replaces white gridlines) |
| Card White | `#FFFFFF` | Every calculated data row |
| Border Hairline | `#E2E8F0` | All cell borders — thin, never black |
| Text Primary | `#0F172A` | Values, product names |
| Text Secondary | `#334155` | Body copy |
| Text Muted | `#64748B` | Captions, helper text, sub-labels |
| Success | `#047857` on `#ECFDF5` | ✅ IN STOCK, "IN" pills |
| Danger | `#B91C1C` on `#FEE2E2` | ⚠️ REORDER NOW, negative stock |
| Warning | `#B45309` on `#FFFBEB` | SHRINKAGE pills |
| WhatsApp | `#25D366` | WhatsApp button fill (white bold text) |
| Input Yellow | `#FFF9DB` + border `#F59E0B` | **Every cell the user types into** |

> **The single most important UX rule:** yellow = you type here, white = do not touch.
> State it on the Start Here sheet and never break it.

### 0.2 Typography
- Font: **Segoe UI** throughout (ships on Windows, degrades gracefully on Mac/iOS/Android).
  Premium upgrade if you embed: **Poppins** for headings, **Inter** for data.
- Screen title: 22–26 pt Bold, Ink.
- Kicker (above title): 9 pt Bold, Indigo, ALL CAPS.
- Table headers: 10 pt Bold, White on Ink, wrapped, centred.
- Data: 10–11 pt. Key numbers (Current Stock, Grand Total): 12–15 pt Bold.

### 0.3 Touch targets (the mobile-first rule)
| Element | Setting |
|---|---|
| Nav bar (row 1) | **Row height 40** |
| Accent divider (row 2) | **Row height 6** |
| Table header row | **Row height 36–38**, Wrap Text ON |
| All data rows | **Row height 30–32** — never below 30 |
| KPI card row | **Row height 46** |
| GRAND TOTAL row | **Row height 42** |

Set them in bulk: select the row numbers → right-click → **Row Height…** → type the number.

### 0.4 Chrome removal — do this on EVERY sheet
`View` ribbon → untick **Gridlines**, **Headings**, **Formula Bar**.
Then `View → Freeze Panes → Freeze Panes` at the cell listed per sheet below.
Finally right-click each tab → **Tab Color** and apply the colour listed per sheet.

### 0.5 Vertical-only layout rule
No sheet exceeds ~8 visible columns. Nothing scrolls sideways on a phone except the
Invoice, which is deliberately page-width because it must print. Everything else
grows **downward**, which is the direction a thumb naturally scrolls.

---

## 1. NAVIGATION BAR — the app chrome

Row 1 on every sheet is the nav bar; row 2 is a 6px indigo divider. Merge the
ranges listed per sheet, then paste these five formulas.

```excel
=HYPERLINK("#'Dashboard'!A1","🏠 Dashboard")
=HYPERLINK("#'Item Master'!A1","📦 Products")
=HYPERLINK("#'Log Transaction'!A1","✍️ Log Sale")
=HYPERLINK("#'Invoice Generator'!A1","🧾 Invoice")
=HYPERLINK("#'Start Here'!A1","🚀 Start Here")
```

Format all five: **Bold, 11 pt, font colour `#FFFFFF`, fill `#0F172A`, centred both ways.**
(Excel's default blue underline does not apply to `HYPERLINK()` results, so they stay
looking like app buttons.)

Fill **every** cell of row 1 across the sheet with `#0F172A` and **every** cell of row 2
with `#4F46E5`, so the bar reads as one solid element edge-to-edge.

**Exact merge map**

| Sheet | 🏠 Dashboard | 📦 Products | ✍️ Log Sale | 🧾 Invoice | 🚀 Start Here | Freeze at |
|---|---|---|---|---|---|---|
| Start Here | `A1:B1` | `C1` | `D1` | `E1` | `F1:G1` | `A3` |
| Dashboard | `A1:B1` | `C1:D1` | `E1` | `F1` | `G1:H1` | `A8` |
| Item Master | `A1:B1` | `C1:D1` | `E1:F1` | `G1:H1` | `I1:J1` | `A4` |
| Log Transaction | `A1` | `B1` | `C1` | `D1:E1` | `F1:G1` | `A4` |
| Invoice Generator | `A1` | `B1` | `C1:D1` | `E1` | `F1` | `A4` |
| Settings | `A1:B1` | `C1` | `D1` | `E1` | `F1:G1` | `A4` |

Freezing at those cells keeps the nav bar **and** the column headers pinned while the
user thumb-scrolls hundreds of rows.

---

## 2. SHEET: "Start Here"

**Tab colour** `#3730A3` · **Freeze** `A3` · Column widths: `A`=3, `B`–`F`=20, `G`=3.

| Cell | Content | Format |
|---|---|---|
| `B4:F4` merged | `MOMENTUM MIND STORE` | 9 pt Bold, `#4F46E5` |
| `B5:F5` merged | `📦 Inventory Manager PRO` | 24 pt Bold, `#0F172A`, row height 38 |
| `B6:F6` merged | `Track stock, log every sale, and send invoices — from your phone.` | 10 pt, `#64748B` |

Then five step cards. Each card = **two merged rows** (`B{r}:F{r}` heading, height 32 +
`B{r+1}:F{r+1}` body, height 46, Wrap Text ON), fill `#FFFFFF`, hairline border `#E2E8F0`,
one blank canvas row between cards.

| Row | Heading (12 pt Bold) | Body (10 pt, `#334155`) |
|---|---|---|
| 8 / 9 | `📦  STEP 1 — Add your products` | Open the Products screen and fill one row per item. SKU must be unique — it is the key that powers everything else. |
| 11 / 12 | `⚙️  STEP 2 — Set your business details` | Open Settings and enter your shop name, contact details, tax rate and invoice prefix. Every invoice reads from there. |
| 14 / 15 | `✍️  STEP 3 — Log every movement` | On the Log Sale screen, tap a new row. Pick the SKU from the dropdown, choose IN (stock received), OUT (sold) or SHRINKAGE (damaged/lost), and enter the quantity. The Total fills itself. |
| 17 / 18 | `🧾  STEP 4 — Generate an invoice` | Type or pick a Transaction ID at the top of the Invoice screen. Every line for that ID appears instantly. Share ▸ Export as PDF. |
| 20 / 21 | `🏠  STEP 5 — Watch the Dashboard` | Live stock levels, low-stock alerts, and one-tap WhatsApp / Email reorder buttons that write the message for you. |

**Colour key block** (row 23 header `🎨 COLOUR KEY`, then rows 24–26, white cards):
`🟡  Yellow cells` → *You type here.* · `⬜  White cells` → *Calculated automatically — do not overwrite.* · `🟦  Dark bar (top)` → *Tap any label to jump between screens.*

**Support block** — replace the placeholders with your real details:

```excel
=HYPERLINK("mailto:support@momentummindstore.com?subject=Inventory%20Manager%20PRO%20-%20Support","support@momentummindstore.com")
=HYPERLINK("https://www.etsy.com/shop/MomentumMindStore","etsy.com/shop/MomentumMindStore")
=HYPERLINK("https://www.momentummindstore.com/inventory-pro-guide","Watch the 4-minute setup video")
=HYPERLINK("https://www.etsy.com/your/purchases","Leave a review — it genuinely helps a small shop")
```

Close with a 9 pt italic muted line:
`© Momentum Mind Store — single-shop licence. No resale or redistribution of this file.`

---

## 3. SHEET: "Item Master" (product database)

**Tab colour** `#4F46E5` · **Freeze** `A4` · **Header row = 3** · **Data rows 4–53**

| Col | Header (row 3) | Width | Number format | Align |
|---|---|---|---|---|
| A | `SKU` | 14 | General | Centre, Bold |
| B | `📦 Product Name` | 32 | General | Left |
| C | `Category` | 16 | General | Left |
| D | `Cost` | 12 | `$#,##0.00;[Red]($#,##0.00);"-"` | Centre |
| E | `Price` | 12 | `$#,##0.00;[Red]($#,##0.00);"-"` | Centre |
| F | `Max Stock` | 12 | `#,##0;[Red](#,##0);"-"` | Centre |
| G | `Reorder Point` | 14 | `#,##0;[Red](#,##0);"-"` | Centre |
| H | `Supplier Name` | 22 | General | Left |
| I | `📞 Supp. Phone` | 18 | **Text (`@`)** | Left |
| J | `✉️ Supp. Email` | 28 | General | Left |

**Create the table:** select `A3:J53` → `Insert → Table` → tick *My table has headers* →
`Table Design → Table Name:` **`tbl_Items`** → style **Table Style Light 9**.

**Formatting:** header row 3 = white bold on `#0F172A`, height 38, Wrap Text ON.
All of `A4:J53` = fill `#FFF9DB`, hairline border `#E2E8F0`, row height **32** — this whole
sheet is an input surface, so the whole grid is yellow.

**Phone-number rule (critical for the WhatsApp button):** format column I as **Text**
and enter **digits only, country code first, no `+`, no spaces** — e.g. `15551234567`.
Add this as a cell comment on `A3`:

> SKU must be UNIQUE — it is the key linking Products, Log and Dashboard.
> Phone: digits only, country code first, no + or spaces (e.g. 15551234567).

**Seed data** (ship the template with these six so buyers see it working):

| SKU | Product Name | Category | Cost | Price | Max | Reorder | Supplier | Phone | Email |
|---|---|---|---|---|---|---|---|---|---|
| LAV-001 | 🕯️ Lavender Soy Candle 220g | Home Fragrance | 6.50 | 18.00 | 120 | 25 | Aurora Wax Co. | 15551234567 | orders@aurorawax.com |
| CER-014 | ☕ Ceramic Mug — Sand | Drinkware | 4.20 | 14.00 | 200 | 40 | Kiln & Clay Ltd | 15559876543 | sales@kilnclay.com |
| TOT-007 | 👜 Canvas Tote Bag — Natural | Bags | 3.80 | 12.50 | 150 | 30 | NorthLoom Textiles | 15554567890 | hello@northloom.com |
| JRN-002 | 📓 Linen Journal A5 | Stationery | 5.10 | 16.00 | 100 | 20 | PaperFold Studio | 15553216549 | supply@paperfold.com |
| SKN-021 | 🧴 Botanical Body Oil 100ml | Skincare | 7.90 | 24.00 | 80 | 16 | Botanica Labs | 15557778888 | orders@botanicalabs.com |
| TEA-009 | 🍵 Loose Leaf Tea 200g | Pantry | 5.60 | 17.50 | 90 | 18 | Verde Leaf Imports | 15552223333 | buy@verdeleaf.com |

---

## 4. NAMED RANGES (build these before the dropdowns)

`Formulas → Name Manager → New`:

| Name | Refers to |
|---|---|
| `SKU_List` | `='Item Master'!$A$4:$A$53` |
| `TXN_List` | `='Log Transaction'!$B$4:$B$303` |

> Excel's Data Validation dialog will not accept a structured reference such as
> `=tbl_Items[SKU]` typed directly. A defined name is the reliable route, and it is what
> makes the dropdown work on **Excel Mobile** too.

---

## 5. SHEET: "Log Transaction" (the entry screen)

**Tab colour** `#047857` · **Freeze** `A4` · **Header row = 3** · **Data rows 4–303**

| Col | Header (row 3) | Width | Format | Notes |
|---|---|---|---|---|
| A | `📅 Date` | 14 | `dd-mmm-yyyy` | Yellow input |
| B | `🆔 ID` | 16 | General | Yellow input, Bold — one ID per sale |
| C | `🏷️ SKU` | 18 | General | Yellow input, Bold, **dropdown** |
| D | `🔄 Type` | 14 | General | Yellow input, **dropdown** |
| E | `🔢 Qty` | 10 | `#,##0` | Yellow input |
| F | `💵 Total` | 14 | `$#,##0.00…` | **White — formula** |
| G | `Line Key` | 22 | General | **White — formula, then HIDE the column** |

Table name: **`tbl_Log`**, range `A3:G303`, style **Table Style Light 11**.
Row height **32** on rows 4–303. Header row height 38, wrapped.

### 5.1 Column F — Total (paste into `F4`, fills down the table)

```excel
=IF($C4="","",IF($D4="IN",$E4*XLOOKUP($C4,'Item Master'!$A$4:$A$53,'Item Master'!$D$4:$D$53,0),$E4*XLOOKUP($C4,'Item Master'!$A$4:$A$53,'Item Master'!$E$4:$E$53,0)))
```

Reads **Cost** for `IN` (what you paid) and **Price** for `OUT`/`SHRINKAGE` (what it was
worth). Structured-reference equivalent, if you prefer it:

```excel
=IF([@SKU]="","",IF([@Type]="IN",[@Qty]*XLOOKUP([@SKU],tbl_Items[SKU],tbl_Items[Cost],0),[@Qty]*XLOOKUP([@SKU],tbl_Items[SKU],tbl_Items[Price],0)))
```

### 5.2 Column G — Line Key (paste into `G4`) — this is the invoice engine

```excel
=IF($B4="","",IF($D4="OUT",$B4&"|"&COUNTIFS($B$4:$B4,$B4,$D$4:$D4,"OUT"),""))
```

It stamps every **sold** line with `TransactionID|1`, `TransactionID|2`, … The expanding
range `$B$4:$B4` is what makes the counter increment. The Invoice sheet then pulls line *n*
by looking up `ID|n`. **Hide column G** (right-click header → Hide) — the buyer never sees it.

### 5.3 Data validation (touch-friendly dropdowns)

Select `C4:C303` → `Data → Data Validation`:
- **Allow:** List · **Source:** `=SKU_List` · **In-cell dropdown:** ✅ · **Ignore blank:** ✅
- *Input Message* — Title `🏷️ Select SKU`, Message `Tap the arrow and choose a product.`
- *Error Alert* — Style **Stop**, Title `Unknown SKU`, Message `Pick an existing SKU. Add new products on the Products screen first.`

Select `D4:D303`:
- **Allow:** List · **Source:** `IN,OUT,SHRINKAGE` (typed literally, commas, no `=`)
- *Input Message* — Title `🔄 Movement type`, Message `IN = stock received · OUT = sold · SHRINKAGE = damaged/lost`
- *Error Alert* — Stop · `Invalid type` · `Choose IN, OUT or SHRINKAGE.`

Select `E4:E303`:
- **Allow:** Whole number · **Data:** greater than · **Minimum:** `0`
- *Error Alert* — Stop · `Invalid quantity` · `Quantity must be a whole number above zero.`

### 5.4 Conditional formatting — Type "pills"

Select `D4:D303` → `Conditional Formatting → New Rule → Use a formula`:

| Formula | Fill | Font |
|---|---|---|
| `=$D4="IN"` | `#ECFDF5` | Bold `#047857` |
| `=$D4="OUT"` | `#EEF2FF` | Bold `#3730A3` |
| `=$D4="SHRINKAGE"` | `#FFFBEB` | Bold `#B45309` |

---

## 6. SHEET: "Dashboard" (real-time hub)

**Tab colour** `#4F46E5` · **Freeze `A8`** · **KPI row 7** · **Header row 8** · **Data rows 9–58**

Widths: `A`=14, `B`=30, `C`=11, `D`=12, `E`=14, `F`=20, `G`=18, `H`=16, `I`=14 **(hidden)**.

### 6.1 Title block
`A4:H4` = `LIVE OVERVIEW` (9 pt Bold `#4F46E5`) · `A5:H5` = `🏠 Dashboard` (22 pt Bold, height 34)
`A6:H6` = `Stock recalculates the moment you log a transaction.` (10 pt `#64748B`)

### 6.2 KPI cards — row 7, height 46, hairline border, 16 pt Bold, centred

| Merge | Label (set as a cell comment) | Formula | Fill / Font |
|---|---|---|---|
| `A7:B7` | 🏷️ ACTIVE SKUs | `=COUNTA('Item Master'!$A$4:$A$53)` | `#EEF2FF` / `#3730A3` |
| `C7:D7` | 📦 UNITS IN STOCK | `=SUM($E$9:$E$58)` | `#EEF2FF` / `#3730A3` |
| `E7:F7` | 💰 STOCK VALUE (COST) | `=SUM($I$9:$I$58)` | `#ECFDF5` / `#047857` |
| `G7:H7` | ⚠️ NEEDS REORDER | `=COUNTIF($F$9:$F$58,"⚠️ REORDER NOW")` | `#FEE2E2` / `#B91C1C` |

### 6.3 Header row 8 — white bold on `#0F172A`, height 36, wrapped, centred

`SKU` · `📦 Product` · `⬇ Total IN` · `⬆ Total OUT` · `📊 Current Stock` · `🚦 Stock Status` · `💬 WhatsApp Order` · `✉️ Email Order` · `Value` *(col I, hidden)*

### 6.4 The engine — paste into row 9, then fill down to row 58

All eight formulas are written for row 9. Select `A9:I9`, copy, select `A10:I58`, paste.

**A9 — SKU**
```excel
=IF(INDEX('Item Master'!$A$4:$A$53,ROW()-8)="","",INDEX('Item Master'!$A$4:$A$53,ROW()-8))
```

**B9 — Product**
```excel
=IF($A9="","",XLOOKUP($A9,'Item Master'!$A$4:$A$53,'Item Master'!$B$4:$B$53,""))
```

**C9 — Total IN**
```excel
=IF($A9="","",SUMIFS('Log Transaction'!$E$4:$E$303,'Log Transaction'!$C$4:$C$303,$A9,'Log Transaction'!$D$4:$D$303,"IN"))
```

**D9 — Total OUT** *(sales **and** shrinkage both leave the shelf)*
```excel
=IF($A9="","",SUMIFS('Log Transaction'!$E$4:$E$303,'Log Transaction'!$C$4:$C$303,$A9,'Log Transaction'!$D$4:$D$303,"OUT")+SUMIFS('Log Transaction'!$E$4:$E$303,'Log Transaction'!$C$4:$C$303,$A9,'Log Transaction'!$D$4:$D$303,"SHRINKAGE"))
```

**E9 — Current Stock** *(12 pt Bold — this is the hero number)*
```excel
=IF($A9="","",$C9-$D9)
```

**F9 — Stock Status**
```excel
=IF($A9="","",IF($E9<=XLOOKUP($A9,'Item Master'!$A$4:$A$53,'Item Master'!$F$4:$F$53,0)*0.1,"⚠️ REORDER NOW","✅ IN STOCK"))
```

> *Variant:* to honour the **Reorder Point** column instead of a flat 10 %, swap the test for
> `$E9<=MAX(XLOOKUP($A9,'Item Master'!$A$4:$A$53,'Item Master'!$F$4:$F$53,0)*0.1,XLOOKUP($A9,'Item Master'!$A$4:$A$53,'Item Master'!$G$4:$G$53,0))`

**G9 — WhatsApp Order button** *(appears only when the item is low)*
```excel
=IF($A9="","",IF($F9="⚠️ REORDER NOW",HYPERLINK("https://wa.me/"&SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(XLOOKUP($A9,'Item Master'!$A$4:$A$53,'Item Master'!$I$4:$I$53,""),"+",""),"-","")," ",""),"(",""),")",""),".","")&"?text="&SUBSTITUTE("Hello "&XLOOKUP($A9,'Item Master'!$A$4:$A$53,'Item Master'!$H$4:$H$53,"Supplier")&", we urgently need more "&$B9&". Current stock is only "&TEXT($E9,"0")&" units. Please confirm availability and your fastest lead time. Thank you - Momentum Mind Store."," ","%20"),"💬  ORDER NOW"),""))
```
The six nested `SUBSTITUTE`s strip `+ - space ( ) .` from the phone number, because
`wa.me` accepts **digits only**. The message text is URL-encoded by turning spaces into `%20`.

**H9 — Email Order button**
```excel
=IF($A9="","",IF($F9="⚠️ REORDER NOW",HYPERLINK("mailto:"&XLOOKUP($A9,'Item Master'!$A$4:$A$53,'Item Master'!$J$4:$J$53,"")&"?subject="&SUBSTITUTE("URGENT restock request - "&$B9&" ("&$A9&")"," ","%20")&"&body="&SUBSTITUTE(SUBSTITUTE("Hello "&XLOOKUP($A9,'Item Master'!$A$4:$A$53,'Item Master'!$H$4:$H$53,"Supplier")&"," & CHAR(10) & "We urgently need to restock "&$B9&" (SKU "&$A9&"). Our current stock is "&TEXT($E9,"0")&" units, which is below our reorder threshold." & CHAR(10) & "Please confirm availability, unit price and lead time by return." & CHAR(10) & "Kind regards," & CHAR(10) & "Momentum Mind Store"," ","%20"),CHAR(10),"%0D%0A"),"✉️  EMAIL"),""))
```
`CHAR(10)` gives real line breaks in the drafted email; the outer `SUBSTITUTE` converts
them to `%0D%0A` so every mail client renders them.

**I9 — Stock Value (hidden helper, feeds the KPI card)**
```excel
=IF($A9="","",$E9*XLOOKUP($A9,'Item Master'!$A$4:$A$53,'Item Master'!$D$4:$D$53,0))
```

### 6.5 Conditional formatting — this is what makes the buttons look like buttons

`Conditional Formatting → New Rule → Use a formula`. **Apply to** must be the range shown.

| Apply to | Formula | Format |
|---|---|---|
| `$F$9:$F$58` | `=$F9="⚠️ REORDER NOW"` | Fill `#FEE2E2`, Bold `#B91C1C` |
| `$F$9:$F$58` | `=$F9="✅ IN STOCK"` | Fill `#ECFDF5`, Bold `#047857` |
| `$E$9:$E$58` | `=AND($A9<>"",$E9<=0)` | Fill `#FEE2E2`, Bold `#B91C1C` |
| `$G$9:$G$58` | `=$G9<>""` | Fill **`#25D366`**, Bold **white** ← WhatsApp button |
| `$H$9:$H$58` | `=$H9<>""` | Fill **`#4F46E5`**, Bold **white** ← Email button |

The last two are the trick: the cell is empty (invisible) until the item is low, then it
fills with brand colour and white bold text — an app button that materialises on demand.

---

## 7. SHEET: "Invoice Generator"

**Tab colour** `#B45309` · **Freeze `A4`** · Widths `A`=15, `B`=28, `C`=10, `D`=15, `E`=15, `F`=15 *(F carries the Start Here nav button and sits outside the print area)*.

### 7.1 Header block

| Cell | Content | Format |
|---|---|---|
| `A4:C4` | `=Settings!$C$8` | 20 pt Bold Ink (your shop name) |
| `A5:C5` | `=Settings!$C$9&"  ·  "&Settings!$C$10` | 10 pt `#64748B` |
| `D4:E5` | `🧾 INVOICE` | 26 pt Bold `#4F46E5`, right-aligned |
| `A7` | `🔎 TRANSACTION ID` | White bold on `#0F172A` |
| **`B7:C7`** | **← the one input. Seed it with `INV-1001`** | 14 pt Bold, fill `#FFF9DB`, **medium `#F59E0B` border**, dropdown = `=TXN_List` |
| `D7` | `Invoice No.` | 10 pt Bold `#334155`, right |
| `E7` | `=IF($B$7="","",Settings!$C$14&$B$7)` | 12 pt Bold `#4F46E5` |
| `A8` | `📅 DATE` | White bold on Ink |
| `B8:C8` | `=IFERROR(INDEX('Log Transaction'!$A$4:$A$303,MATCH($B$7,'Log Transaction'!$B$4:$B$303,0)),TODAY())` | `dd-mmm-yyyy` |
| `D8` | `Due` | right |
| `E8` | `=IF($B$8="","",$B$8+Settings!$C$15)` | `dd-mmm-yyyy` |
| `A9` | `👤 BILL TO` | White bold on Ink |
| `B9:E9` | *(free text)* `Customer name · email · address` | Yellow input, gold border |

### 7.2 Line-item table — headers row 11, lines rows 12–26

Headers (white bold on `#0F172A`, height 34): `SKU` · `📦 Description` · `Qty` · `Unit Price` · `Line Total`.

**Paste into row 12, then fill down to row 26.** The `ROW()-11` term is the line counter that
pairs with the Line Key you built in §5.2 — line 1 of the invoice fetches `ID|1`, line 2 fetches
`ID|2`, and so on.

**A12 — SKU**
```excel
=IFERROR(INDEX('Log Transaction'!$C$4:$C$303,MATCH($B$7&"|"&ROW()-11,'Log Transaction'!$G$4:$G$303,0)),"")
```

**B12 — Description**
```excel
=IF($A12="","",XLOOKUP($A12,'Item Master'!$A$4:$A$53,'Item Master'!$B$4:$B$53,""))
```

**C12 — Qty**
```excel
=IFERROR(INDEX('Log Transaction'!$E$4:$E$303,MATCH($B$7&"|"&ROW()-11,'Log Transaction'!$G$4:$G$303,0)),"")
```

**D12 — Unit Price**
```excel
=IF($A12="","",XLOOKUP($A12,'Item Master'!$A$4:$A$53,'Item Master'!$E$4:$E$53,0))
```

**E12 — Line Total**
```excel
=IF($A12="","",$C12*$D12)
```

#### 7.2b The single-formula `FILTER` alternative (Excel 365 only)

If you are shipping a 365-only edition, delete the fill-down block, hide nothing, and put
these four spill formulas in `A12`, `C12`, plus the two lookups. They need **no** Line Key
column at all:

```excel
A12:  =IFERROR(FILTER(tbl_Log[SKU],(tbl_Log[ID]=$B$7)*(tbl_Log[Type]="OUT")),"— No transaction found —")
B12:  =IFERROR(XLOOKUP(A12#,tbl_Items[SKU],tbl_Items[📦 Product Name]),"")
C12:  =IFERROR(FILTER(tbl_Log[Qty],(tbl_Log[ID]=$B$7)*(tbl_Log[Type]="OUT")),"")
D12:  =IFERROR(XLOOKUP(A12#,tbl_Items[SKU],tbl_Items[Price]),"")
E12:  =IFERROR(C12#*D12#,"")
```
and change the Subtotal to `=SUM(E12#)`.

> **Which to ship?** The `INDEX`/`MATCH` + Line Key version is what the supplied `.xlsx`
> uses, because it also runs on Excel 2019, Excel Mobile and Google Sheets — fewer refund
> requests. Offer the `FILTER` build as a bonus "365 Edition" file in the same download.

### 7.3 Totals block

| Row | `C:D` merged label | `E` formula | Format |
|---|---|---|---|
| 28 | `Subtotal` | `=SUM($E$12:$E$26)` | Bold, money, white card |
| 29 | `Tax rate` | `=Settings!$C$12` | `0.0%`, muted |
| 30 | `Tax amount` | `=$E$28*$E$29` | Bold, money |
| 31 | `Discount` | `0` ← **yellow input, gold border** | money |
| 32 | **`GRAND TOTAL`** | `=$E$28+$E$30-$E$31` | **15 pt Bold white on `#4F46E5`, row height 42, `C32:E32` all indigo** |

### 7.4 Footer
- `A34:E34` → `="Payment terms: "&Settings!$C$16`
- `A35:E35` → `=Settings!$C$17`
- `A36:E36` → `="Thank you for supporting "&Settings!$C$8&" 💛"` (11 pt Bold `#4F46E5`, centred)

### 7.5 Print / PDF setup (the mobile-share path)
`Page Layout` → **Print Area = `A4:E36`** · Orientation **Portrait** ·
**Fit Sheet on One Page** (`Width: 1 page`, `Height: 1 page`) · Margins L/R `0.4"`, T/B `0.5"`.

On a phone: **⋯ → Export → PDF** (iOS) or **File → Print → Save as PDF** (Android), then
share straight into WhatsApp or email. Column F is outside the print area, so the nav
button never appears on the invoice.

---

## 8. SHEET: "Settings"

**Tab colour** `#334155` · **Freeze `A4`** · Widths `A`=3, `B`=24, `C`=22, `D`–`F`=18, `G`=3.
Labels in `B`, inputs in `C:F` merged — yellow fill `#FFF9DB` with a medium `#F59E0B` border,
row height 34.

| Cell | Label (col B) | Default value (col C) | Format |
|---|---|---|---|
| `C8` | `🏪 Business name` | `Momentum Mind Store` | General |
| `C9` | `✉️ Business email` | `hello@momentummindstore.com` | General |
| `C10` | `📞 Business phone` | `+1 555 010 2030` | Text (`@`) |
| `C11` | `🌐 Website / Etsy` | `etsy.com/shop/MomentumMindStore` | General |
| `C12` | `🧾 Tax rate` | `0.10` | `0.0%` |
| `C13` | `💱 Currency symbol` | `$` | General |
| `C14` | `#️⃣ Invoice prefix` | `MMS-` | General |
| `C15` | `📆 Payment due (days)` | `14` | `#,##0` |
| `C16` | `💳 Payment terms` | `Payment due within 14 days of invoice date.` | General |
| `C17` | `🏦 Payment details` | `Bank: Example Bank · Acct: 0000 0000 · Ref: your invoice no.` | General |

`B19:F19` → `🔒 Rows 8–17 are the only cells you edit here. Everything else is automatic.` (9 pt italic muted)

> `C13` is documentation only — Excel number formats are static. To change currency,
> select the money columns and apply e.g. `£#,##0.00;[Red](£#,##0.00);"-"`.

---

## 9. FINAL POLISH CHECKLIST

- [ ] Every sheet: Gridlines, Headings, Formula Bar **off**.
- [ ] Every sheet: Freeze Panes set per the table in §1.
- [ ] Tab colours applied; sheet order: Start Here → Dashboard → Item Master → Log Transaction → Invoice Generator → Settings.
- [ ] Save with **Start Here** as the active sheet, cursor on `A1`, so it opens on the welcome screen.
- [ ] `Log Transaction` column **G hidden**; `Dashboard` column **I hidden**.
- [ ] Test the nav: tap each of the five buttons on all six sheets.
- [ ] Test the alert: set `SKN-021` Max Stock to `80`, log `OUT 55` → Dashboard shows `⚠️ REORDER NOW` + both buttons.
- [ ] Tap the WhatsApp button — it should open a chat with the message pre-typed.
- [ ] Type `INV-1001` in `Invoice Generator!B7` → three lines appear, Grand Total ≈ `$76.00 + tax`.
- [ ] Open the file in the **Excel mobile app** and confirm no horizontal scrolling on Dashboard or Log Transaction.
- [ ] *(Optional)* `Review → Protect Sheet`, leaving only the yellow ranges unlocked. Leave the password **blank** so buyers can unlock it.

---

## 10. ETSY DELIVERY NOTES

- **Do not zip a single file** — Etsy buyers open it on a phone, and mobile browsers handle
  a bare `.xlsx` far better than a `.zip`.
- Ship **three files**: the `.xlsx`, a 1-page **PDF quick-start**, and a `LICENCE.txt`.
- Listing images: mock the Dashboard on a phone frame (the ⚠️ red row + green WhatsApp
  button is the money shot), then the Invoice, then the Log screen.
- Set expectations in the description: *"Requires Microsoft Excel 2019 or newer, or Excel
  365 (desktop, web, iOS, Android). Not compatible with Numbers. Google Sheets: works with
  reduced formatting."*
- Ship an unlocked file. Locked templates generate the majority of digital-product refund
  requests, and buyers reliably want to add a column.
