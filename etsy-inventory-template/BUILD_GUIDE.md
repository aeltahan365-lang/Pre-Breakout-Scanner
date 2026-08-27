# 📦 Inventory Manager PRO — Build Specification (v2)
### Momentum Mind Store · A mobile-first inventory, till and invoicing app built in Excel
**No VBA required. Excel 365 / 2021 / 2019, and Excel Mobile on iOS + Android.**

---

## 0 · WHAT CHANGED IN v2, AND WHY

| You asked for | What v2 does |
|---|---|
| Start Here steps should jump straight to the page | Every step card **is** the hyperlink — one tap, no "open link" prompt |
| Add products manually **or by scanner** | New `📷 Barcode` column. Any USB/Bluetooth scanner types straight into it |
| Pick items by dropdown, by first letters, **or by scanning** | One `🔎 SKU / Scan` cell accepts all three, and resolves barcode → SKU automatically |
| Full description should appear | Product, price and line total fill themselves the instant the code lands |
| Sales should log automatically | **They do — there is no posting step at all.** See §0.1 |
| Two logs: SKU level and header level | `Log Sale` (line level) and `Sales Log` (header: date, invoice no, qty, amount) |
| A Generate button → PDF → WhatsApp/email | Real one-click button in the **Desktop PRO Edition** (`VBA_PRO_EDITION.bas`). In the macro-free file: one-tap WhatsApp and Email, two-tap PDF. See §0.2 |

### 0.1 The core design decision: the sale is logged when you scan it

A formula can only fill **its own cell**. It cannot write a row into another sheet. So a
macro-free "press Generate and it writes two log rows" is impossible — and macros do not run
in Excel for iOS, Android or the web, which is exactly where a market-stall seller is standing.

So the problem is inverted. **The entry screen *is* the SKU-level log**, and the header log is
a live formula rollup of it. Nothing is ever "posted", so nothing can ever go unposted:

```
   Log Sale  ──(SUMIF / COUNTIF / MAXIFS)──▶  Sales Log     (header, one row per invoice)
      │                                            │
      └──(INDEX/MATCH on Line Key)──▶  Invoice ◀───┘
      │
      └──(SUMIF by SKU)──▶  Dashboard  ──▶  reorder alerts + WhatsApp / Email buttons
```

That is fewer taps than a Generate button, and it survives on a phone.

### 0.2 Honest limits of a macro-free file

| Action | Macro-free `.xlsx` | Desktop PRO `.xlsm` |
|---|---|---|
| Log the sale | ✅ automatic on entry | ✅ automatic on entry |
| Send invoice on WhatsApp | ✅ **one tap** — whole invoice pre-typed | ✅ one tap |
| Email the invoice | ✅ **one tap** — whole invoice in the body | ✅ one tap, PDF attached |
| Save as PDF | ⚠️ two taps: `File ▸ Export ▸ PDF` | ✅ **one tap** |
| Start a new sale, date-stamped, cursor in the scan box | ⚠️ tick 🆕, type the date | ✅ **one tap** |
| Works on iPhone / Android / web | ✅ | ❌ macros never run there |

Ship both. The `.xlsx` is the product; the `.bas` is the bonus that makes desktop buyers happy.

---

## 1 · DESIGN SYSTEM — "Momentum Midnight"

### 1.1 Palette (exact HEX)

| Token | HEX | Used for |
|---|---|---|
| Ink | `#0F172A` | Nav bar row 1, every table header |
| Accent divider | `#4F46E5` | Row 2 — 6px strip under the nav |
| Primary Indigo | `#4F46E5` | Buttons, GRAND TOTAL bar, links |
| Indigo Deep | `#3730A3` | KPI figures, invoice numbers |
| Indigo Tint | `#EEF2FF` | KPI cards, **current-sale row highlight** |
| App Canvas | `#F1F5F9` | Every sheet background |
| Card White | `#FFFFFF` | Every calculated row |
| Border Hairline | `#E2E8F0` | All borders |
| Text | `#0F172A` / `#334155` / `#64748B` | Primary / body / muted |
| Success | `#047857` on `#ECFDF5` | ✅ IN STOCK, IN receipts, today's sales |
| Danger | `#B91C1C` on `#FEE2E2` | ⚠️ REORDER NOW, ⚠️ Unknown code |
| Warning | `#B45309` on `#FFFBEB` | SHRINKAGE |
| WhatsApp | `#25D366` | WhatsApp buttons |
| Input Yellow | `#FFF9DB` + border `#F59E0B` | **Every cell you type or scan into** |

> **The rule that carries the product:** 🟡 yellow = you type here · ⬜ white = never touch ·
> 🟩/🟪 coloured = a button that has switched itself on.

### 1.2 Typography & touch targets
**Segoe UI** throughout. Titles 22–26pt Bold · kickers 9pt Bold Indigo caps · headers 10pt Bold
white on Ink, wrapped · data 10–11pt · hero numbers 12–16pt Bold.

| Element | Row height |
|---|---|
| Nav bar (row 1) | **40** |
| Accent divider (row 2) | **6** |
| Table headers | **36–38**, Wrap ON |
| Data rows | **30–32 — never below 30** |
| KPI cards | **46** (row 7) / **38** (row 8) |
| Button row / GRAND TOTAL | **42–46** |

### 1.3 Chrome removal — every sheet
`View` → untick **Gridlines**, **Headings**, **Formula Bar**. Freeze at the cell in §2. Tab colour per §2.

---

## 2 · NAVIGATION — six screens, one tap, from anywhere

Row 1 = nav, row 2 = 6px indigo divider. Fill **all** of row 1 `#0F172A` and **all** of row 2 `#4F46E5`.

```excel
=HYPERLINK("#'Dashboard'!A1","🏠 Home")
=HYPERLINK("#'Item Master'!A1","📦 Items")
=HYPERLINK("#'Log Sale'!A1","🛒 New Sale")
=HYPERLINK("#'Stock In'!A1","📥 Stock In")
=HYPERLINK("#'Invoice Generator'!A1","🧾 Invoice")
=HYPERLINK("#'Sales Log'!A1","📊 Logs")
```
Bold 11pt, white, fill `#0F172A`, centred. `HYPERLINK()` results take no blue underline, so they
read as app buttons. Internal `#` links never raise Excel's "open this link?" prompt.

**Merge map & freeze points**

| Sheet | 🏠 | 📦 | 🛒 | 📥 | 🧾 | 📊 | Freeze | Tab |
|---|---|---|---|---|---|---|---|---|
| Start Here | `A1:B1` | `C1` | `D1` | `E1` | `F1` | `G1:H1` | `A3` | `#3730A3` |
| Dashboard | `A1` | `B1` | `C1:D1` | `E1` | `F1` | `G1:H1` | `A10` | `#4F46E5` |
| Item Master | `A1:B1` | `C1` | `D1:E1` | `F1:G1` | `H1:I1` | `J1:K1` | `A4` | `#4F46E5` |
| Log Sale | `A1:B1` | `C1` | `D1` | `E1` | `F1:G1` | `H1` | `A9` | `#047857` |
| Stock In | `A1` | `B1` | `C1` | `D1` | `E1` | `F1:G1` | `A8` | `#B45309` |
| Sales Log | `A1` | `B1:C1` | `D1` | `E1` | `F1:G1` | `H1:I1` | `A8` | `#3730A3` |
| Invoice Generator | `A1` | `B1` | `C1:D1` | `E1` | `F1` | `G1` | `A4` | `#B45309` |
| Settings | `A1:B1` | `C1` | `D1` | `E1` | `F1` | `G1:H1` | `A4` | `#334155` |

`Start Here` and `Settings` are reached from two buttons on the Dashboard (`E8`, `F8`).

---

## 3 · SHEET "Start Here" — every card is the link

Widths `A`=3, `B`–`G`=18, `H`=3. Freeze `A3`.
Seven step cards, each **two merged rows** (`B{r}:G{r}` heading h32 + `B{r+1}:G{r+1}` body h48
Wrap ON), white fill, hairline border, one blank canvas row between.

**The heading cell is a formula, not text** — that is the whole fix:

```excel
=HYPERLINK("#'Item Master'!A1","📦  STEP 1 — Add your products   ›")
=HYPERLINK("#'Settings'!A1","⚙️  STEP 2 — Set your business details   ›")
=HYPERLINK("#'Log Sale'!A1","🛒  STEP 3 — Sell (this IS your sales log)   ›")
=HYPERLINK("#'Stock In'!A1","📥  STEP 4 — Receive stock & record breakages   ›")
=HYPERLINK("#'Invoice Generator'!A1","🧾  STEP 5 — Send the invoice   ›")
=HYPERLINK("#'Sales Log'!A1","📊  STEP 6 — Read your two live logs   ›")
=HYPERLINK("#'Dashboard'!A1","🏠  STEP 7 — Watch the Dashboard   ›")
```
Format 12pt Bold `#3730A3`. The `›` is the affordance that says *tap me*.

Below: a colour key (4 rows) and a support block (5 rows) of `mailto:` / `https:` hyperlinks.

---

## 4 · SHEET "Item Master" — `tbl_Items`, scanner-ready

Header row 3 · data rows 4–53 · row height 32 · whole grid yellow `#FFF9DB` (it is all input).

| Col | Header | Width | Format |
|---|---|---|---|
| A | `SKU` | 12 | General, centre bold |
| **B** | **`📷 Barcode`** | **14** | **Text (`@`)** |
| C | `📦 Product Name` | 30 | General |
| D | `Category` | 14 | General |
| E | `Cost` | 11 | `$#,##0.00;[Red]($#,##0.00);"-"` |
| F | `Price` | 11 | same |
| G | `Max Stock` | 11 | `#,##0;[Red](#,##0);"-"` |
| H | `Reorder Point` | 12 | same |
| I | `Supplier Name` | 20 | General |
| J | `📞 Supp. Phone` | 16 | **Text (`@`)** |
| K | `✉️ Supp. Email` | 24 | General |

`Insert → Table` on `A3:K53` → name **`tbl_Items`** → **Table Style Light 9**.

**Adding products by scanner:** a USB or Bluetooth barcode scanner is a keyboard. Tap cell `B{n}`,
pull the trigger, the code lands, Enter moves on. Nothing to configure. Format column B as **Text**
first or long EAN-13 codes turn into `5.06E+12`.

**Searching the catalogue:** use the table's own header arrows (`Data → Filter`). Typing letters in
the filter box is the native, mobile-friendly search — no custom formula needed.

Cell comment on `A3`:
> SKU must be UNIQUE — it is the key linking every screen.
> 📷 Barcode: scan straight into this cell with any USB or Bluetooth scanner (they type like a keyboard). The Sell and Stock In screens accept EITHER the SKU or the barcode.
> 📞 Phone: digits only, country code first, no + or spaces (e.g. 15551234567).

---

## 5 · NAMED RANGES

| Name | Refers to |
|---|---|
| `SKU_List` | `='Item Master'!$A$4:$A$53` |
| `INV_PICK` | `='Sales Log'!$K$7:$K$107` |

> Data Validation will not accept a typed structured reference (`=tbl_Items[SKU]`). A defined
> name is the reliable route and is what makes the dropdown work on Excel Mobile.

---

## 6 · SHEET "Log Sale" — the till, and the SKU-level log

Title rows 4–6 · **live sale card row 7** · header row 8 · **data rows 9–308** · freeze `A9`.

| Col | Header | W | Type |
|---|---|---|---|
| A | `🆕` | 6 | 🟡 dropdown `x` |
| B | `📅 Date` | 13 | 🟡 date |
| C | `🧾 Invoice No` | 15 | ⬜ formula |
| D | `🔎 SKU / Scan` | 17 | 🟡 dropdown **+ typing + scanner** |
| E | `📦 Product` | 30 | ⬜ formula |
| F | `🔢 Qty` | 8 | 🟡 blank = 1 |
| G | `💲 Price` | 11 | ⬜ formula |
| H | `💵 Line Total` | 13 | ⬜ formula |
| I | `_SKU` | 12 | ⬜ **hidden** — resolved SKU |
| J | `_Key` | 16 | ⬜ **hidden** — invoice line key |
| K | `_Qty` | 8 | ⬜ **hidden** — qty with the blank→1 default |

### 6.1 Live sale card — row 7, height 46

`LATEST` is used all over the workbook; it is this expression:

```excel
IFERROR(INDEX('Sales Log'!$A$8:$A$107,MAX(1,COUNTIF('Sales Log'!$A$8:$A$107,"?*"))),"")
```

| Merge | Formula | Tooltip |
|---|---|---|
| `A7:C7` | `="🧾  "&IF(LATEST="","— no sales yet —",LATEST)` | Current sale |
| `D7:E7` | `=IF(LATEST="",0,COUNTIF('Log Sale'!$C$9:$C$308,LATEST))` | Lines on this sale |
| `F7:G7` | `=IF(LATEST="",0,SUMIF('Log Sale'!$C$9:$C$308,LATEST,'Log Sale'!$K$9:$K$308))` | Units on this sale |
| `H7` | `=IF(LATEST="",0,SUMIF('Log Sale'!$C$9:$C$308,LATEST,'Log Sale'!$H$9:$H$308))` | Running total |

### 6.2 The engine — paste into row 9, fill down to row 308

**C9 — Invoice No. Tick 🆕 and a fresh number is minted; leave it blank and the line joins the sale above.**
```excel
=IF($D9="","",IF(OR($A9="x",ROW()=9),Settings!$C$14&TEXT(1000+COUNTIF($A$9:$A9,"x")+IF($A$9<>"x",1,0),"0000"),$C8))
```
`COUNTIF($A$9:$A9,"x")` is an expanding range — it counts how many sales have started at or
above this row. The `IF($A$9<>"x",1,0)` term keeps the numbering correct when the very first
row has no tick. The prefix comes from `Settings!$C$14`, so changing it renumbers everything.

**I9 — resolved SKU. This is what makes "scan OR type OR pick" work from one cell.**
```excel
=IF($D9="","",IF(COUNTIF('Item Master'!$A$4:$A$53,$D9)>0,$D9,XLOOKUP($D9,'Item Master'!$B$4:$B$53,'Item Master'!$A$4:$A$53,"")))
```
If what landed in `D9` is already a SKU, use it. Otherwise treat it as a barcode and look the
SKU up. Anything unrecognised falls through to `""`, which lights up the warning below.

**E9 — Product (the full description the buyer asked for)**
```excel
=IF($D9="","",IF($I9="","⚠️ Unknown code",XLOOKUP($I9,'Item Master'!$A$4:$A$53,'Item Master'!$C$4:$C$53,"")))
```

**G9 — Price** `=IF($I9="","",XLOOKUP($I9,'Item Master'!$A$4:$A$53,'Item Master'!$F$4:$F$53,0))`

**K9 — Qty with a default of 1** — scan and walk away
```excel
=IF($I9="","",IF($F9="",1,$F9))
```

**H9 — Line Total** `=IF($I9="","",$K9*$G9)`

**J9 — Line Key** (the invoice engine — see §9)
```excel
=IF($I9="","",$C9&"|"&COUNTIFS($C$9:$C9,$C9,$I$9:$I9,"?*"))
```

### 6.3 Data validation

| Range | Allow | Source | Notes |
|---|---|---|---|
| `A9:A308` | List | `x` | Prompt: *Tap and choose x to start a NEW sale. Leave blank to add another line to the sale above.* |
| `D9:D308` | List | `=SKU_List` | **Untick "Show error alert"** — this is what lets a scanned barcode through while the dropdown still works |
| `F9:F308` | Whole number > 0 | | Ignore blank ✅ (blank means 1) |

> Unticking the error alert on `D` is the single most important setting on this sheet. Leave it
> ticked and every barcode scan is rejected.

**Typing to search:** in Excel 365 desktop, typing the first letters in a validated cell filters
the dropdown live. On mobile the dropdown has its own search field. Both work with this setup.

### 6.4 Conditional formatting

| Apply to | Formula | Format |
|---|---|---|
| `$E$9:$E$308` | `=$E9="⚠️ Unknown code"` | Fill `#FEE2E2`, Bold `#B91C1C` |
| `$A$9:$H$308` | `=AND($C9<>"",$C9=LATEST)` | Fill `#EEF2FF` — **highlights the sale in progress** |

---

## 7 · SHEET "Stock In" — receipts and shrinkage

Header row 7 · data rows 8–207 · freeze `A8`.
Cols: `A 📅 Date` · `B 🔖 Ref / PO` · `C 🔎 SKU / Scan` · `D 🔄 Type` · `E 📦 Product` ·
`F 🔢 Qty` · `G 💲 Unit Cost` · `H 💵 Total` · `I _SKU` **(hidden)**.

```excel
I8:  =IF($C8="","",IF(COUNTIF('Item Master'!$A$4:$A$53,$C8)>0,$C8,XLOOKUP($C8,'Item Master'!$B$4:$B$53,'Item Master'!$A$4:$A$53,"")))
E8:  =IF($C8="","",IF($I8="","⚠️ Unknown code",XLOOKUP($I8,'Item Master'!$A$4:$A$53,'Item Master'!$C$4:$C$53,"")))
G8:  =IF($I8="","",XLOOKUP($I8,'Item Master'!$A$4:$A$53,'Item Master'!$E$4:$E$53,0))
H8:  =IF($I8="","",$F8*$G8)
```
Validation: `C8:C207` list `=SKU_List` with the error alert **off** (scanner); `D8:D207` list
`IN,SHRINKAGE`. Conditional formatting: `=$D8="IN"` green pill, `=$D8="SHRINKAGE"` amber pill,
`=$E8="⚠️ Unknown code"` red.

Splitting purchases out of the sales log is what keeps the Sales Log clean: it contains sales
and only sales.

---

## 8 · SHEET "Sales Log" — the header-level log, written automatically

Header row 7 · data rows 8–107 · freeze `A8`.

| Col | Header | Source |
|---|---|---|
| A | `🧾 Invoice No` | ⬜ formula |
| B | `📅 Date` | ⬜ formula |
| C | `👤 Customer` | 🟡 optional |
| D | `📞 Phone` | 🟡 optional, Text |
| E | `✉️ Email` | 🟡 optional |
| F | `📦 Items` | ⬜ formula |
| G | `🔢 Qty` | ⬜ formula |
| H | `💵 Subtotal` | ⬜ formula |
| I | `🧾 Tax` | ⬜ formula |
| J | `💰 Amount` | ⬜ formula |
| K | `_pick` | ⬜ **hidden** — feeds the invoice picker |

Paste into row 8 and fill down to 107. `NUM` below is the candidate invoice number for that row —
row 8 is `INV-1001`, row 9 is `INV-1002`, and so on, because the Sell screen mints numbers in
exactly that sequence. **This is why no `UNIQUE()` is needed and why the sheet works in Excel 2019.**

```excel
NUM  =  Settings!$C$14&TEXT(1000+ROW()-7,"0000")

A8:  =IF(COUNTIF('Log Sale'!$C$9:$C$308,NUM)=0,"",NUM)
B8:  =IF($A8="","",MAXIFS('Log Sale'!$B$9:$B$308,'Log Sale'!$C$9:$C$308,$A8))
F8:  =IF($A8="","",COUNTIF('Log Sale'!$C$9:$C$308,$A8))
G8:  =IF($A8="","",SUMIF('Log Sale'!$C$9:$C$308,$A8,'Log Sale'!$K$9:$K$308))
H8:  =IF($A8="","",SUMIF('Log Sale'!$C$9:$C$308,$A8,'Log Sale'!$H$9:$H$308))
I8:  =IF($A8="","",$H8*Settings!$C$12)
J8:  =IF($A8="","",$H8+$I8)
K8:  =IF($A8="","",$A8)
```
`K7` holds the literal text `LATEST`, so `INV_PICK` = `LATEST` + every invoice number.

`MAXIFS` (not `MINIFS`) is deliberate: continuation lines of a sale may have a blank date, and a
blank reads as zero, which would win a MIN.

Conditional formatting on `$A$8:$J$107`: `=AND($A8<>"",$B8=TODAY())` → fill `#ECFDF5`.
Today's takings glow green.

---

## 9 · SHEET "Invoice Generator" — opens on your latest sale

Widths `A`=15, `B`=28, `C`=10, `D`=15, `E`=15, `F`=14, `G`=14 (nav, outside print),
`H`=40 **hidden**, `I`=60 **hidden**.

### 9.1 Header

| Cell | Content |
|---|---|
| `A4:C4` | `=Settings!$C$8` — 20pt Bold |
| `A5:C5` | `=Settings!$C$9&"  ·  "&Settings!$C$10` |
| `D4:E5` | `🧾 INVOICE` — 26pt Bold Indigo, right |
| `A6` | `🔎 SHOW INVOICE` |
| **`B6:C6`** | **`LATEST`** — 🟡 dropdown, source `=INV_PICK` |
| `D6:E6` | *Leave on LATEST and this screen always shows the sale you just made.* |
| `A7` / `B7:C7` | `🧾 INVOICE NO` / `=IF($B$6="LATEST",LATEST,$B$6)` — 15pt Bold |
| `D7` / `E7` | `📅 Date` / `=IFERROR(XLOOKUP($B$7,'Sales Log'!$A$8:$A$107,'Sales Log'!$B$8:$B$107,TODAY()),TODAY())` |
| `A8` / `B8:C8` | `👤 BILL TO` / `=IFERROR(XLOOKUP($B$7,'Sales Log'!$A$8:$A$107,'Sales Log'!$C$8:$C$107,""),"")` |
| `D8` / `E8` | `Due` / `=IF($E$7="","",$E$7+Settings!$C$15)` |
| `A9` / `B9:C9` | `📞 / ✉️` / phone from `'Sales Log'!$D` |
| `D9:E9` | email from `'Sales Log'!$E` |

**The zero-tap part:** `B6` ships set to `LATEST`, so the moment you finish a sale on the Sell
screen the invoice is already on screen. You only touch `B6` to reprint an old one.

### 9.2 Line items — headers row 11, lines rows 12–26

```excel
A12: =IFERROR(INDEX('Log Sale'!$I$9:$I$308,MATCH($B$7&"|"&ROW()-11,'Log Sale'!$J$9:$J$308,0)),"")
B12: =IF($A12="","",XLOOKUP($A12,'Item Master'!$A$4:$A$53,'Item Master'!$C$4:$C$53,""))
C12: =IFERROR(INDEX('Log Sale'!$K$9:$K$308,MATCH($B$7&"|"&ROW()-11,'Log Sale'!$J$9:$J$308,0)),"")
D12: =IF($A12="","",XLOOKUP($A12,'Item Master'!$A$4:$A$53,'Item Master'!$F$4:$F$53,0))
E12: =IF($A12="","",$C12*$D12)
H12: =IF($A12="","",$B12&"  x"&TEXT($C12,"0")&"  "&TEXT($E12,"0.00")&"%0A")     ← hidden
```
`ROW()-11` is the line counter that pairs with the Line Key from §6.2: line 1 fetches `INV-1005|1`.

> **Excel 365 alternative** — delete the fill-down and the `_Key` column, and use one spill
> formula: `A12: =IFERROR(FILTER('Log Sale'!$I$9:$I$308,'Log Sale'!$C$9:$C$308=$B$7),"")`,
> `C12: =IFERROR(FILTER('Log Sale'!$K$9:$K$308,'Log Sale'!$C$9:$C$308=$B$7),"")`, then
> `B12/D12` with `A12#`, `E12: =IFERROR(C12#*D12#,"")` and `E28: =SUM(E12#)`.
> Ship this as a bonus "365 Edition"; keep INDEX/MATCH as the file you sell.

### 9.3 Totals

| Row | `C:D` label | `E` |
|---|---|---|
| 28 | Subtotal | `=SUM($E$12:$E$26)` |
| 29 | Tax rate | `=Settings!$C$12` (`0.0%`) |
| 30 | Tax amount | `=$E$28*$E$29` |
| 31 | Discount | `0` ← 🟡 input |
| 32 | **GRAND TOTAL** | `=$E$28+$E$30-$E$31` — 15pt Bold white on `#4F46E5`, `C32:E32` all indigo, h42 |

### 9.4 The share message (hidden helpers)

`I7` assembles the entire invoice as one URL-encoded string by concatenating the fifteen hidden
line-text cells:

```excel
I7: ="*"&Settings!$C$8&"*%0AInvoice: "&$B$7&"%0ADate: "&TEXT($E$7,"dd-mmm-yyyy")
    &"%0A- - - - - - - - - -%0A"&$H$12&$H$13&$H$14&$H$15&$H$16&$H$17&$H$18&$H$19&$H$20
    &$H$21&$H$22&$H$23&$H$24&$H$25&$H$26
    &"- - - - - - - - - -%0ASubtotal: "&TEXT($E$28,"0.00")&"%0ATax: "&TEXT($E$30,"0.00")
    &"%0A*TOTAL: "&TEXT($E$32,"0.00")&"*%0A%0A"&Settings!$C$16&"%0AThank you!"

I8: =SUBSTITUTE(SUBSTITUTE($I$7,"%0A","%0D%0A"),"*","")
```
`%0A` is a WhatsApp line break and `*text*` is WhatsApp bold. `I8` re-encodes both for email.

> **Length limit:** a `HYPERLINK` URL tops out around 2,000 characters. Fifteen lines of
> ordinary product names sits near 900, so you have headroom — but a 15-line invoice of very
> long descriptions can truncate. Use the PDF route for those.

### 9.5 The button row — row 34, height 46

| Cell | Content | Style |
|---|---|---|
| `A34:B34` | `📄  SAVE AS PDF   ›   File ▸ Export ▸ PDF` | White bold on `#3730A3` |
| `C34:D34` | WhatsApp formula below | White bold on `#25D366` |
| `E34` | Email formula below | White bold on `#4F46E5` |

```excel
C34: =IF($B$7="","",HYPERLINK("https://wa.me/"&SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE($B$9,"+",""),"-","")," ",""),"(",""),")",""),".","")&"?text="&SUBSTITUTE($I$7," ","%20"),"💬  SEND ON WHATSAPP"))

E34: =IF($B$7="","",HYPERLINK("mailto:"&$D$9&"?subject="&SUBSTITUTE("Invoice "&$B$7&" from "&Settings!$C$8," ","%20")&"&body="&SUBSTITUTE($I$8," ","%20"),"✉️  EMAIL"))
```
The six nested `SUBSTITUTE`s strip `+ - space ( ) .` — `wa.me` accepts digits only.

`A34` is deliberately labelled with its own instruction rather than pretending to be a button
that runs code. Assign the `GenerateInvoice` macro to it in the PRO edition and it becomes real.

### 9.6 Print / PDF
**Print area `A4:E38`** · Portrait · Fit to 1 × 1 page · margins L/R `0.4"`, T/B `0.5"`.
Columns F–I sit outside the print area, so the nav button and the hidden helpers never print.

---

## 10 · SHEET "Dashboard"

Title 4–6 · KPI row 7 (h46) · KPI/button row 8 (h38) · header row 9 · data rows 10–59 · freeze `A10`.
Widths `A`=14, `B`=30, `C`=11, `D`=12, `E`=14, `F`=20, `G`=18, `H`=16, `I`=14 **hidden**.

### 10.1 KPI row 7

| Merge | Formula | Style |
|---|---|---|
| `A7:B7` | `=COUNTA('Item Master'!$A$4:$A$53)` | `#EEF2FF`/`#3730A3` |
| `C7:D7` | `=SUM($E$10:$E$59)` | `#EEF2FF`/`#3730A3` |
| `E7:F7` | `=SUMIF('Sales Log'!$B$8:$B$107,TODAY(),'Sales Log'!$J$8:$J$107)` | `#ECFDF5`/`#047857` |
| `G7:H7` | `=COUNTIF($F$10:$F$59,"⚠️ REORDER NOW")` | `#FEE2E2`/`#B91C1C` |

### 10.2 KPI / button row 8

| Cell | Content |
|---|---|
| `A8:B8` | `=SUM($I$10:$I$59)` — stock value at cost |
| `C8:D8` | `=SUM('Sales Log'!$J$8:$J$107)` — all-time sales |
| `E8` | `=HYPERLINK("#'Start Here'!A1","🚀  Start Here")` — white on `#334155` |
| `F8` | `=HYPERLINK("#'Settings'!A1","⚙️  Settings")` — white on `#334155` |
| `G8:H8` | `=HYPERLINK("#'Log Sale'!A1","🛒  START A NEW SALE")` — **12pt white bold on `#047857`** |

### 10.3 The engine — row 10, fill down to 59

```excel
A10: =IF(INDEX('Item Master'!$A$4:$A$53,ROW()-9)="","",INDEX('Item Master'!$A$4:$A$53,ROW()-9))
B10: =IF($A10="","",XLOOKUP($A10,'Item Master'!$A$4:$A$53,'Item Master'!$C$4:$C$53,""))
C10: =IF($A10="","",SUMIFS('Stock In'!$F$8:$F$207,'Stock In'!$I$8:$I$207,$A10,'Stock In'!$D$8:$D$207,"IN"))
D10: =IF($A10="","",SUMIF('Log Sale'!$I$9:$I$308,$A10,'Log Sale'!$K$9:$K$308)+SUMIFS('Stock In'!$F$8:$F$207,'Stock In'!$I$8:$I$207,$A10,'Stock In'!$D$8:$D$207,"SHRINKAGE"))
E10: =IF($A10="","",$C10-$D10)
F10: =IF($A10="","",IF($E10<=XLOOKUP($A10,'Item Master'!$A$4:$A$53,'Item Master'!$G$4:$G$53,0)*0.1,"⚠️ REORDER NOW","✅ IN STOCK"))
I10: =IF($A10="","",$E10*XLOOKUP($A10,'Item Master'!$A$4:$A$53,'Item Master'!$E$4:$E$53,0))
```
**Total OUT = sold + shrinkage.** Both leave the shelf.

*Variant honouring the Reorder Point column instead of a flat 10%:* replace the `F10` test with
`$E10<=MAX(XLOOKUP($A10,...,'Item Master'!$G$4:$G$53,0)*0.1,XLOOKUP($A10,...,'Item Master'!$H$4:$H$53,0))`

**G10 — WhatsApp reorder button**
```excel
=IF($A10="","",IF($F10="⚠️ REORDER NOW",HYPERLINK("https://wa.me/"&SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(XLOOKUP($A10,'Item Master'!$A$4:$A$53,'Item Master'!$J$4:$J$53,""),"+",""),"-","")," ",""),"(",""),")",""),".","")&"?text="&SUBSTITUTE("Hello "&XLOOKUP($A10,'Item Master'!$A$4:$A$53,'Item Master'!$I$4:$I$53,"Supplier")&", we urgently need more "&$B10&". Current stock is only "&TEXT($E10,"0")&" units. Please confirm availability and your fastest lead time. Thank you - Momentum Mind Store."," ","%20"),"💬  ORDER NOW"),""))
```

**H10 — Email reorder button**
```excel
=IF($A10="","",IF($F10="⚠️ REORDER NOW",HYPERLINK("mailto:"&XLOOKUP($A10,'Item Master'!$A$4:$A$53,'Item Master'!$K$4:$K$53,"")&"?subject="&SUBSTITUTE("URGENT restock request - "&$B10&" ("&$A10&")"," ","%20")&"&body="&SUBSTITUTE(SUBSTITUTE("Hello "&XLOOKUP($A10,'Item Master'!$A$4:$A$53,'Item Master'!$I$4:$I$53,"Supplier")&"," & CHAR(10) & "We urgently need to restock "&$B10&" (SKU "&$A10&"). Our current stock is "&TEXT($E10,"0")&" units, which is below our reorder threshold." & CHAR(10) & "Please confirm availability, unit price and lead time by return." & CHAR(10) & "Kind regards," & CHAR(10) & Settings!$C$8," ","%20"),CHAR(10),"%0D%0A"),"✉️  EMAIL"),""))
```

### 10.4 Conditional formatting — the button trick

| Apply to | Formula | Format |
|---|---|---|
| `$F$10:$F$59` | `=$F10="⚠️ REORDER NOW"` | `#FEE2E2` / Bold `#B91C1C` |
| `$F$10:$F$59` | `=$F10="✅ IN STOCK"` | `#ECFDF5` / Bold `#047857` |
| `$E$10:$E$59` | `=AND($A10<>"",$E10<=0)` | `#FEE2E2` / Bold `#B91C1C` |
| `$G$10:$G$59` | `=$G10<>""` | Fill **`#25D366`**, Bold white |
| `$H$10:$H$59` | `=$H10<>""` | Fill **`#4F46E5`**, Bold white |

The last two are the whole illusion: the cell is empty and invisible until stock drops, then it
fills with brand colour and white bold text — a button that appears exactly when it is needed.

---

## 11 · SHEET "Settings"

Labels in `B`, inputs merged `C:G`, yellow with a medium `#F59E0B` border, h34.

| Cell | Label | Default |
|---|---|---|
| `C8` | 🏪 Business name | `Momentum Mind Store` |
| `C9` | ✉️ Business email | `hello@momentummindstore.com` |
| `C10` | 📞 Business phone | `+1 555 010 2030` (Text) |
| `C11` | 🌐 Website / Etsy | `etsy.com/shop/MomentumMindStore` |
| `C12` | 🧾 Tax rate | `0.10` (`0.0%`) |
| `C13` | 💱 Currency symbol | `$` |
| `C14` | #️⃣ **Invoice prefix** | `INV-` |
| `C15` | 📆 Payment due (days) | `14` |
| `C16` | 💳 Payment terms | `Payment due within 14 days of invoice date.` |
| `C17` | 🏦 Payment details | `Bank: … · Acct: … · Ref: your invoice no.` |

`C14` drives the entire numbering scheme — change it and every invoice renumbers.
`C13` is documentation only; Excel number formats are static.

---

## 12 · DESKTOP PRO EDITION (optional macros)

`VBA_PRO_EDITION.bas` in your download. Install: Save As `.xlsm` → `ALT+F11` → `File ▸ Import
File…` → right-click the `SAVE AS PDF` cell → `Assign Macro` → `GenerateInvoice`; and the
Dashboard's `START A NEW SALE` cell → `NewSale`.

| Macro | One click does |
|---|---|
| `NewSale` | Opens the till, stamps today's date, ticks 🆕, drops the cursor in the scan box |
| `AddLine` | Same, but joins the sale already in progress |
| `GenerateInvoice` | Exports the invoice to `Invoice-INV-1005.pdf` beside the workbook, then asks WhatsApp / Email / just save |
| `SendWhatsApp` | Opens WhatsApp with the invoice pre-typed |
| `SendEmailWithPDF` | Outlook draft with the PDF attached (falls back to `mailto:` on Mac) |

**Macros never run on iOS, Android or Excel for the web.** Keep the `.xlsx` as the phone edition.

---

## 13 · FINAL CHECKLIST

- [ ] Every sheet: Gridlines / Headings / Formula Bar off; freeze points per §2; tab colours set
- [ ] Sheet order: Start Here → Dashboard → Item Master → Log Sale → Stock In → Sales Log → Invoice Generator → Settings
- [ ] Saved with **Start Here** active on `A1`
- [ ] Hidden: `Log Sale` I, J, K · `Stock In` I · `Sales Log` K · `Dashboard` I · `Invoice Generator` H, I
- [ ] `Log Sale!D` and `Stock In!C` validation has **"Show error alert" unticked** (scanner support)
- [ ] Tap all six nav buttons on all eight sheets, and all seven Start Here cards
- [ ] Scan or type a barcode into `Log Sale!D` — the product name should appear
- [ ] Check every number against §13.1
- [ ] Open in the Excel mobile app: no horizontal scrolling on Dashboard, Sell or Stock In

### 13.1 Expected values from the shipped seed data

**Sell screen → Log Sale (SKU-level log), auto-numbered from the 🆕 ticks**

| Invoice | SKU | Qty | Line total | Line Key |
|---|---|---|---|---|
| INV-1001 | LAV-001 | 2 | $36.00 | `INV-1001\|1` |
| INV-1001 | CER-014 | 3 | $42.00 | `INV-1001\|2` |
| INV-1001 | JRN-002 | 1 | $16.00 | `INV-1001\|3` |
| INV-1002 | TOT-007 | 4 | $50.00 | `INV-1002\|1` |
| INV-1002 | TEA-009 | 2 | $35.00 | `INV-1002\|2` |
| INV-1003 | SKN-021 | 55 | $1,320.00 | `INV-1003\|1` |
| INV-1004 | LAV-001 | 88 | $1,584.00 | `INV-1004\|1` |
| INV-1005 | CER-014 | 12 | $168.00 | `INV-1005\|1` |

**Sales Log (header-level log) — every row written automatically**

| Invoice | Date | Items | Qty | Subtotal | Tax | Amount |
|---|---|---|---|---|---|---|
| INV-1001 | 05-Aug-2026 | 3 | 6 | $94.00 | $9.40 | $103.40 |
| INV-1002 | 07-Aug-2026 | 2 | 6 | $85.00 | $8.50 | $93.50 |
| INV-1003 | 09-Aug-2026 | 1 | 55 | $1,320.00 | $132.00 | $1,452.00 |
| INV-1004 | 10-Aug-2026 | 1 | 88 | $1,584.00 | $158.40 | $1,742.40 |
| INV-1005 | 12-Aug-2026 | 1 | 12 | $168.00 | $16.80 | $184.80 |

**Dashboard**

| SKU | IN | OUT | Stock | Max | 10% | Status |
|---|---|---|---|---|---|---|
| LAV-001 | 100 | 90 | **10** | 120 | 12.0 | ⚠️ REORDER NOW |
| CER-014 | 150 | 15 | **135** | 200 | 20.0 | ✅ IN STOCK |
| TOT-007 | 120 | 4 | **116** | 150 | 15.0 | ✅ IN STOCK |
| JRN-002 | 80 | 1 | **79** | 100 | 10.0 | ✅ IN STOCK |
| SKN-021 | 60 | 55 | **5** | 80 | 8.0 | ⚠️ REORDER NOW |
| TEA-009 | 70 | 5 | **65** | 90 | 9.0 | ✅ IN STOCK |

`TEA-009`'s OUT of 5 is 2 sold + 3 shrinkage — proof both paths decrement stock.
KPIs: **6** SKUs · **410** units · **$1,879.20** stock value at cost · **2** needing reorder ·
all-time sales **$3,576.10**.

**Invoice screen** with `B6` on `LATEST` shows **INV-1005** — one line, `CER-014` × 12,
subtotal `$168.00`, tax `$16.80`, **GRAND TOTAL `$184.80`** — with no taps at all.

---

## 14 · ETSY DELIVERY NOTES

- **Don't zip a single file** — buyers open it on a phone, and mobile browsers handle a bare `.xlsx` far better than a `.zip`.
- Ship **four files**: the `.xlsx`, `VBA_PRO_EDITION.bas`, a 1-page PDF quick-start, and `LICENCE.txt`.
- Listing images in order: (1) the Dashboard with the red ⚠️ row and green WhatsApp button — the money shot, (2) the Sell screen mid-scan, (3) the Invoice, (4) the Sales Log.
- Lead the description with the promise: *"Scan an item. The sale is logged, the stock drops, and the invoice is ready to send on WhatsApp — before you've put your phone down."*
- Set expectations: *"Requires Excel 2019 or newer, or Excel 365 (desktop, web, iOS, Android). Barcode scanning uses any USB or Bluetooth scanner. The optional one-click PDF button is Windows/Mac desktop only. Not compatible with Numbers."*
- **Ship it unlocked.** Locked templates drive most digital-product refunds.
