# 📦 Inventory Manager PRO — Momentum Mind Store

A mobile-first **inventory, till and invoicing app built in Excel**. No macros required.
Excel 365 / 2021 / 2019, and Excel Mobile on iOS + Android.

| File | What it is |
|---|---|
| `Momentum-Mind-Inventory-Manager-PRO.xlsx` | The finished, sellable workbook |
| `BUILD_GUIDE.md` | Complete build spec — every cell, colour, formula and rule |
| `VBA_PRO_EDITION.bas` | Optional desktop macros: true one-click PDF + share |
| `build_template.py` | The generator that produces the `.xlsx` from scratch |

## Rebuild

```bash
pip install openpyxl
python3 build_template.py
```

## The eight screens

`Start Here` · `Dashboard` · `Item Master` · `Log Sale` · `Stock In` · `Sales Log` ·
`Invoice Generator` · `Settings` — all reachable in one tap from a frozen nav bar on every sheet.

## The idea

**The sale is logged the moment it is scanned.** A formula can only fill its own cell, so a
macro-free "press Generate and it writes the logs" is impossible — and macros don't run on
phones, which is where a small seller actually stands. So the entry screen *is* the SKU-level
log, and the header log is a live rollup of it. Nothing is posted, so nothing goes unposted.

```
Log Sale ──SUMIF/COUNTIF/MAXIFS──▶ Sales Log (header: date, invoice no, qty, amount)
   │                                     │
   └──INDEX/MATCH on Line Key──▶ Invoice ◀┘
   │
   └──SUMIF by SKU──▶ Dashboard ──▶ reorder alerts + WhatsApp / Email buttons
```

## Key mechanics

- **Scan, type or pick** — one `🔎 SKU / Scan` cell takes a barcode from any USB/Bluetooth
  scanner, a typed prefix, or the dropdown. A resolver formula turns a barcode into its SKU.
- **Auto invoice numbers** — tick `🆕` and `COUNTIF` over an expanding range mints the next
  number; leave it blank and the line joins the sale above.
- **Qty defaults to 1** — a hidden `_Qty` column means scan-and-go really is one action.
- **The invoice opens on your latest sale** — the picker ships set to `LATEST`, so zero taps.
- **One-tap send** — hidden helper cells assemble the whole invoice as a URL-encoded string
  behind `wa.me` and `mailto:` hyperlinks.
- **Buttons that appear on demand** — reorder cells are empty until stock drops, then
  conditional formatting fills them WhatsApp-green or indigo with white bold text.

See `BUILD_GUIDE.md` for the full specification, and §13.1 for the expected values that verify
a correct build.
