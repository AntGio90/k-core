import json, xlsxwriter, zipfile
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from pdfkit import from_string
from typing import Dict, Any


def make_combined_report_package(item_id: str, report: Dict[str, Any]) -> str:
    export_dir = Path('exports')
    export_dir.mkdir(exist_ok=True)
    base = export_dir / f"{item_id}_review"

    # 1. JSON
    json_path = base.with_suffix('.json')
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2)

    # 2. XLSX: two sheets (checklist, hara)
    xlsx_path = base.with_suffix('.xlsx')
    workbook = xlsxwriter.Workbook(str(xlsx_path))
    # Checklist sheet
    ws1 = workbook.add_worksheet('Checklist')
    # ... write checklist results ...
    # HARA sheet
    ws2 = workbook.add_worksheet('HARA')
    hazards = report['hara']
    headers = list(hazards[0].keys())
    for col, h in enumerate(headers): ws2.write(0, col, h)
    for r, h in enumerate(hazards, start=1):
        for c, key in enumerate(headers): ws2.write(r, c, h.get(key, ''))
    workbook.close()

    # 3. PDF via HTML template
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('combined_report.html')
    html = template.render(item_id=item_id, report=report)
    pdf_path = base.with_suffix('.pdf')
    from_string(html, str(pdf_path))

    # 4. Zip all
    zip_path = export_dir / f"{item_id}_review.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for p in [json_path, xlsx_path, pdf_path]:
            zf.write(p, p.name)
    return str(zip_path)