import io
import qrcode
from reportlab.lib.pagesizes import A5
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas


def render_poster(cupom: str, desconto: float, parceiro: str, influencer: str, link: str, cidade: str = "") -> bytes:
    W, H = A5
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A5)
    purple, night = HexColor("#5B21B6"), HexColor("#08061A")
    steps = 60
    for i in range(steps):
        t = i / steps
        col = HexColor("#%02x%02x%02x" % tuple(int(a + (b - a) * t) for a, b in zip((0x5B, 0x21, 0xB6), (0x08, 0x06, 0x1A))))
        c.setFillColor(col)
        c.rect(0, H - (i + 1) * H / steps, W, H / steps + 1, stroke=0, fill=1)
    c.setFillColor(white)
    from brand import brand_mark
    c.drawImage(ImageReader(brand_mark(256)), W / 2 - 24 * mm, H - 27 * mm, 13 * mm, 13 * mm, mask="auto")
    c.setFont("Helvetica-Bold", 30)
    c.drawString(W / 2 - 9 * mm, H - 23.5 * mm, "RRclub")
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(HexColor("#DDD6FE"))
    c.drawCentredString(W / 2, H - 28 * mm, "EXPERIÊNCIAS PREMIUM  ·  THECLUB.PT")

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(W / 2, H - 46 * mm, f"{desconto:g}% OFF")
    c.setFont("Helvetica", 12)
    c.setFillColor(HexColor("#EDE9FE"))
    c.drawCentredString(W / 2, H - 54 * mm, f"em {parceiro}" + (f" · {cidade}" if cidade else ""))

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=1, box_size=10)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#3B0764", back_color="white").convert("RGB")
    size = 78 * mm
    x, y = (W - size) / 2, H - 62 * mm - size
    c.setFillColor(white)
    c.roundRect(x - 5 * mm, y - 5 * mm, size + 10 * mm, size + 10 * mm, 5 * mm, stroke=0, fill=1)
    c.drawImage(ImageReader(img), x, y, size, size)

    c.setFillColor(HexColor("#7C3AED"))
    c.roundRect(W / 2 - 40 * mm, y - 20 * mm, 80 * mm, 12 * mm, 4 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Courier-Bold", 18)
    c.drawCentredString(W / 2, y - 16 * mm, cupom)

    c.setFont("Helvetica", 9.5)
    c.setFillColor(HexColor("#EDE9FE"))
    c.drawCentredString(W / 2, y - 28 * mm, "Aponte a câmara para o QR, pague com desconto ou mostre o código ao balcão")
    if influencer:
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(W / 2, y - 34 * mm, f"Cupão de {influencer}")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(HexColor("#A78BFA"))
    c.drawCentredString(W / 2, 8 * mm, link.replace("https://", "").replace("http://", ""))
    c.showPage()
    c.save()
    return buf.getvalue()
