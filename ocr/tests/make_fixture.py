"""Draw a synthetic itemized hospital bill (no real patient data)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def font(sz):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try: return ImageFont.truetype(f, sz)
        except OSError: pass
    return ImageFont.load_default()

ROWS = [
    ("09/14/2026", "0300", "85025", "CBC W/ AUTO DIFF", "1", "$84.00", "$84.00"),
    ("09/14/2026", "0300", "85025", "CBC W/ AUTO DIFF", "1", "$84.00", "$84.00"),
    ("09/14/2026", "0450", "99284", "ER VISIT LEVEL 4", "1", "$2,450.00", "$2,450.00"),
    ("09/14/2026", "0636", "J1885", "KETOROLAC INJ", "2", "$38.50", "$77.00"),
    ("09/14/2026", "0250", "", "PHARMACY GENERAL", "1", "$112.75", "$112.75"),
]

def make(path: Path, rows=ROWS, total="$2,807.75"):
    img = Image.new("RGB", (1700, 1100), "white"); d = ImageDraw.Draw(img)
    d.text((80, 60), "SUNRISE GENERAL HOSPITAL   NPI: 1234567893", font=font(34), fill="black")
    d.text((80, 120), "Itemized Statement  Patient: MAYA (SYNTHETIC)", font=font(28), fill="black")
    cols = [80, 300, 420, 560, 1060, 1180, 1420]
    for x, h in zip(cols, ["DATE", "REV", "CODE", "DESCRIPTION", "QTY", "UNIT", "TOTAL"]):
        d.text((x, 220), h, font=font(28), fill="black")
    y = 290
    for r in rows:
        for x, v in zip(cols, r):
            if v: d.text((x, y), v, font=font(28), fill="black")
        y += 70
    d.text((1060, y + 40), "TOTAL CHARGES", font=font(28), fill="black")
    d.text((1420, y + 40), total, font=font(28), fill="black")
    img.save(path)

if __name__ == "__main__":
    make(Path(__file__).parent / "fixtures" / "synthetic_bill.png")
