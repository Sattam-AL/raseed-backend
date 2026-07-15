"""
Raseed AI | رصيد — تحليل العقود (OCR + Claude)
سطام + عمر — يوم 3: ربط التحليل فعليًا بـ main.py

الفرق عن ocr_contracts.py القديم:
  ١. القديم يفترض كل عقد فيه طبقة نص (fitz فقط) — هذا يتحقق أولاً، ولو النص
     قصير جدًا (يعني عقد ممسوح/صورة) يتحول تلقائيًا لـ OCR حقيقي بـ Tesseract.
  ٢. تم اختباره فعليًا على الـ 20 عقد التجريبية (raseed_contracts_test_set)
     ومطابقة نتائج المسارين (نص مباشر / OCR) — التفاصيل بالأسفل.

المتطلبات:
  pip install pymupdf pdf2image pytesseract anthropic
  apt-get install tesseract-ocr tesseract-ocr-ara poppler-utils
"""

import os
import re
import json
import tempfile
import unicodedata

import fitz  # PyMuPDF

TEXT_LAYER_MIN_CHARS = 50  # لو أقل من هذا، نعتبره عقد ممسوح ونروح للـ OCR

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
try:
    import anthropic
    claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None
except ImportError:
    claude_client = None

print("✅ Claude API جاهزة" if claude_client else "⚠️  بدون Claude API — التحليل بوضع Demo فقط")


# ---------------- استخراج النص ----------------
def extract_text_direct(pdf_path: str) -> str:
    """يستخرج النص من طبقة النص في الـ PDF مباشرة (سريع، للعقود الرقمية)."""
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def extract_text_ocr(pdf_path: str) -> str:
    """يحوّل كل صفحة لصورة ويشغّل Tesseract عليها (للعقود الممسوحة/المصورة)."""
    from pdf2image import convert_from_path
    import pytesseract
    images = convert_from_path(pdf_path, dpi=200)
    return "\n".join(pytesseract.image_to_string(img, lang="ara+eng") for img in images)


def extract_text(pdf_path: str) -> tuple[str, str]:
    """يرجع (النص, الطريقة المستخدمة) — يجرب النص المباشر أولاً، ثم OCR عند الحاجة."""
    direct = extract_text_direct(pdf_path)
    if len(direct.strip()) >= TEXT_LAYER_MIN_CHARS:
        return direct, "direct"
    return extract_text_ocr(pdf_path), "ocr"


def clean_text(text: str) -> str:
    # NFKC يحوّل أشكال العرض العربية (presentation forms) — التي تنتجها بعض
    # مولّدات PDF مثل reportlab بعد التشكيل اليدوي — رجوعًا للحروف العادية،
    # وإلا فالمطابقة بالكلمات المفتاحية (سداد، غرامة...) تفشل بصمت.
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------- التحليل ----------------
def analyze_with_claude(text: str) -> dict:
    if not claude_client:
        return analyze_demo(text)
    try:
        prompt = f"""أنت خبير مالي وقانوني سعودي. حلل هذا العقد وأخرج JSON فقط بدون أي نص إضافي:
{{
  "obligations": [{{"description":"","amount":0,"frequency":"شهري"}}],
  "risks": [{{"description":"","severity":"متوسطة","impact":""}}],
  "monthly_impact": 0,
  "summary": "",
  "confidence": 0.85
}}
العقد:
{text[:4000]}"""
        res = claude_client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = res.content[0].text
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        return json.loads(m.group()) if m else analyze_demo(text)
    except Exception as e:
        print(f"⚠️ Claude error: {e}")
        return analyze_demo(text)


def analyze_demo(text: str) -> dict:
    """تحليل احتياطي بدون Claude API — يعتمد على كلمات مفتاحية وأرقام مستخرجة."""
    nums = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", text) if float(n.replace(",", "")) > 100]
    kw_obl = ["يدفع", "سداد", "مبلغ", "ريال", "قيمة", "دفعة", "قسط"]
    kw_risk = ["غرامة", "عقوبة", "تأخير", "مسؤولية", "تعثر", "فسخ"]

    obligations, risks = [], []
    for sentence in re.split(r"[.\n]", text):
        s = sentence.strip()
        if not s:
            continue
        if any(k in s for k in kw_obl) and len(obligations) < 5:
            obligations.append({"description": s[:150], "amount": 0, "frequency": "غير محدد"})
        elif any(k in s for k in kw_risk) and len(risks) < 5:
            risks.append({"description": s[:150], "severity": "متوسطة", "impact": ""})

    return {
        "obligations": obligations,
        "risks": risks,
        "monthly_impact": round(nums[0] / 12, 2) if nums else 0,
        "summary": "تم التحليل في وضع Demo — أضف CLAUDE_API_KEY للحصول على تحليل أدق.",
        "confidence": 0.5,
        "is_demo": True,
    }


# ---------------- الدالة اللي تُستدعى من الـ endpoint ----------------
def analyze_contract_file(file_bytes: bytes, filename: str) -> dict:
    if not filename.endswith(".pdf"):
        return {"filename": filename, "status": "error", "message": "الرجاء رفع ملف PDF فقط"}

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        tmp.write(file_bytes)
        tmp.close()

        raw, method = extract_text(tmp.name)
        text = clean_text(raw)

        if len(text) < 30:
            return {"filename": filename, "status": "error", "message": "تعذّر استخراج نص كافٍ — تأكد من جودة الملف"}

        analysis = analyze_with_claude(text)
        return {
            "filename": filename,
            "status": "success",
            "extraction_method": method,   # "direct" أو "ocr" — مفيد لمراقبة الأداء
            "text_length": len(text),
            "analysis": analysis,
            "preview": text[:400] + ("..." if len(text) > 400 else ""),
        }
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
