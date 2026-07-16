FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# نسخ جميع الملفات بما فيها مجلد models
COPY . .

# التحقق من وجود ملف النموذج في المسار الصحيح أثناء البناء
RUN ls -la models/ || echo "⚠️ مجلد models غير موجود"

# تعيين متغير البيئة لمسار النموذج
ENV MODEL_PATH=models/raseed_classifier.joblib

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
