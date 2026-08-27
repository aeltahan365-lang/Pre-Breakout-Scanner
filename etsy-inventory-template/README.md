# 📦 Inventory Manager PRO — Momentum Mind Store

A premium, mobile-first **Inventory Management & Invoicing** template for Excel.
No VBA, no macros — advanced formulas only (`XLOOKUP`, `SUMIFS`, `INDEX`/`MATCH`,
`COUNTIFS`, `IF`, `HYPERLINK`).

| File | What it is |
|---|---|
| `Momentum-Mind-Inventory-Manager-PRO.xlsx` | The finished, sellable workbook |
| `BUILD_GUIDE.md` | The complete build specification — every cell, colour, formula and rule |
| `build_template.py` | The generator that produces the `.xlsx` from scratch |

## Rebuild

```bash
pip install openpyxl
python3 build_template.py
```

## Sheets

`Start Here` · `Dashboard` · `Item Master` · `Log Transaction` · `Invoice Generator` · `Settings`

## Key mechanics

- **App nav bar** — frozen row 1 of every sheet, five `HYPERLINK("#'Sheet'!A1", …)` buttons on `#0F172A`.
- **Live stock** — `SUMIFS` over `tbl_Log` by SKU and movement type; `OUT` + `SHRINKAGE` both decrement.
- **Reorder alert** — fires at `Current Stock <= Max Stock × 10%`, red conditional formatting.
- **One-tap reorder** — `HYPERLINK` to `wa.me` / `mailto:` with the message pre-written, styled
  as a WhatsApp-green or indigo button by conditional formatting, and invisible until needed.
- **Invoice engine** — a hidden `Line Key` column stamps each sold row `ID|1`, `ID|2`, …
  so `INDEX`/`MATCH` pulls line *n* for the entered Transaction ID. A 365-only `FILTER`
  variant is documented in `BUILD_GUIDE.md` §7.2b.

See `BUILD_GUIDE.md` for the full specification.
