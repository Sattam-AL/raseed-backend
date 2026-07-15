"""
Raseed AI — Backend API
فريق عمار طويق | هاكاثون أمد 2026

هذا الملف هو main.py الأصلي + ربط ai_chat.py (Claude API + ذاكرة محادثة)
+ ربط contract_analyzer.py (تحليل عقود PDF عبر OCR/Claude) — دُمجا اليوم
وتم اختبار الاثنين فعليًا بسيرفر FastAPI حقيقي قبل التسليم.
"""
import joblib, os
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from ai_chat import chat as ai_chat_reply
from contract_analyzer import analyze_contract_file

app = FastAPI(title="Raseed AI API", description="وكيل مالي ذكي", version="1.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from merchant_map import classify_merchant  # القاموس الموحّد — مصدر واحد للحقيقة (عبدالله)

MODEL_PATH = os.getenv("MODEL_PATH", "models/raseed_classifier.joblib")
model = encoder = None; accuracy = 0.0
try:
    d = joblib.load(MODEL_PATH)
    model=d['model']; encoder=d['encoder']   # encoder هنا LabelEncoder لعمود الفئة (y)، مو للـ features
    accuracy = d.get('test_accuracy') or d.get('accuracy') or 0.0
    print(f"✅ النموذج محمّل (الدقة: {accuracy:.2%})")
except Exception as e:
    print(f"⚠️  تعذّر تحميل النموذج: {e}")

ICONS = {"مطاعم":"🍔","وقود":"⛽","تسوق":"🛍️","سوبرماركت":"🛒",
         "كهرباء":"⚡","اتصالات":"📱","صحة":"🏥","ترفيه":"🎬",
         "أثاث":"🛋️","إلكترونيات":"💻","ملابس":"👕","مواد غذائية":"🥦",
         "أجهزة":"🔌","خدمات":"🧰","غير محدد":"❓"}

def bucket(a):
    if a<100: return "منخفض"
    elif a<300: return "متوسط-منخفض"
    elif a<600: return "متوسط"
    elif a<1000: return "مرتفع"
    else: return "عالي"

class Transaction(BaseModel):
    merchant: str; type: Optional[str]="شراء"
    payment_method: Optional[str]="مدى"; amount: float=100.0
    description: Optional[str]=""

class SimulateRequest(BaseModel):
    monthly_income: float; fixed_expenses: float; decision_cost: float
    months: Optional[int]=60; decision_label: Optional[str]="قرار مالي"

class ChatRequest(BaseModel):
    message: str; monthly_income: Optional[float]=10000
    monthly_expenses: Optional[float]=7000; balance: Optional[float]=15000
    history: Optional[list]=None   # ← جديد: ذاكرة المحادثة بين الأسئلة

@app.get("/")
def root():
    return {"app":"Raseed AI","version":"1.1.0","team":"فريق عمار طويق",
            "status":"🟢 شغّال","model_accuracy":f"{accuracy:.2%}"}

@app.get("/health")
def health():
    return {"status":"ok","model_loaded":model is not None,"accuracy":accuracy}

@app.post("/classify")
def classify(tx: Transaction):
    b = bucket(tx.amount)
    merchant = tx.merchant.strip()

    if model is not None:
        try:
            X = pd.DataFrame([{"merchant": merchant, "description": tx.description or "",
                                "amount": tx.amount, "payment_method": tx.payment_method}])
            proba = model.predict_proba(X)[0]
            conf = float(proba.max())
            cat = encoder.inverse_transform([proba.argmax()])[0]
            # النموذج نفسه يوصي: ثقة < 50% تعني "ما أعرفه" — استخدم القاموس بدلها
            if conf >= 0.5:
                return {"merchant":tx.merchant,"amount":tx.amount,"category":cat,"icon":ICONS.get(cat,"💳"),
                        "confidence":f"{conf*100:.1f}%","bucket":b,"source":"model"}
        except Exception as e:
            print(f"⚠️ فشل النموذج على '{merchant}': {e} — تحول لقاموس التجار")

    cat = classify_merchant(merchant)  # مطابقة احتواء (contains)، مو تطابق تام — يغطي "محطة بترومين" وغيرها
    return {"merchant":tx.merchant,"amount":tx.amount,"category":cat,"icon":ICONS.get(cat,"💳"),
            "confidence":"fallback","bucket":b,"source":"dictionary"}

@app.post("/simulate")
def simulate(req: SimulateRequest):
    if req.monthly_income<=0: raise HTTPException(400,"الدخل يجب أن يكون أكبر من صفر")
    bal=0.0; timeline=[]
    for m in range(1,req.months+1):
        net=req.monthly_income-req.fixed_expenses-req.decision_cost; bal+=net
        timeline.append({"month":m,"balance":round(bal,2),"net":round(net,2),"danger":bal<0})
    neg=sum(1 for t in timeline if t["danger"])
    if neg>6:   risk,color,safe,adv="مرتفع","red",False,f"⚠️ خطر — عجز في {neg} شهراً."
    elif neg>0: risk,color,safe,adv="متوسط","orange",False,f"⚠️ مخاطر في {neg} شهر."
    else:       risk,color,safe,adv="منخفض","green",True,f"✅ آمن. رصيدك بعد {req.months} شهر: {round(bal):,} ريال"
    return {"decision":req.decision_label,"monthly_cost":req.decision_cost,"risk_level":risk,
            "risk_color":color,"safe_to_proceed":safe,"advice":adv,"final_balance":round(bal,2),
            "negative_months":neg,"timeline":timeline[:12],
            "summary":{"year_1":round(sum(t["net"] for t in timeline[:12]),2),
                       "year_3":round(sum(t["net"] for t in timeline[:36]),2),"year_5":round(bal,2)}}

@app.post("/analyze")
def analyze(transactions: List[Transaction]):
    if not transactions: raise HTTPException(400,"لا توجد معاملات")
    results=[]; by_cat={}; total=0
    for tx in transactions:
        r=classify(tx); results.append(r)
        cat=r["category"]; by_cat[cat]=by_cat.get(cat,0)+(tx.amount or 0); total+=tx.amount or 0
    if total==0: return {"total_spent":0,"transactions":len(transactions),"top_category":"لا بيانات","by_category":{},"insight":"لا معاملات"}
    sc=sorted(by_cat.items(),key=lambda x:x[1],reverse=True); top=sc[0][0]
    return {"total_spent":round(total,2),"transactions":len(transactions),"top_category":top,"top_icon":ICONS.get(top,"💳"),
            "by_category":{k:{"amount":round(v,2),"percentage":round(v/total*100,1),"icon":ICONS.get(k,"💳")} for k,v in sc},
            "breakdown":results[:10],"insight":f"أكثر إنفاقك في {top} بنسبة {round(by_cat.get(top,0)/total*100,1)}%"}

# ============================================================
# /chat — بعد الدمج: Claude API فعلي + سياق حقيقي + ذاكرة محادثة
# (بدّل منطق if/else القديم؛ نفس المنطق موجود الآن داخل ai_chat.py
#  كـ fallback تلقائي عند غياب CLAUDE_API_KEY أو فشل الاتصال)
# ============================================================
@app.post("/chat")
def chat(req: ChatRequest):
    user_data = {
        "monthly_income": req.monthly_income,
        "monthly_expenses": req.monthly_expenses,
        "balance": req.balance,
    }
    result = ai_chat_reply(req.message, user_data, req.history)
    return {
        "message": req.message,
        "reply": result["reply"],
        "history": result["history"],
        "mode": result["mode"],  # "claude" / "rules" / "rules_fallback" — مفيد للمراقبة
        "context": {
            "income": req.monthly_income, "expenses": req.monthly_expenses,
            "balance": req.balance, "saving": round(req.monthly_income - req.monthly_expenses, 2),
        },
    }

# ============================================================
# /analyze-contract — جديد: كان مكتوبًا في ocr_contracts.py وغير مفعّل
# ============================================================
@app.post("/analyze-contract")
async def analyze_contract(file: UploadFile = File(...)):
    content = await file.read()
    return analyze_contract_file(content, file.filename)

if __name__=="__main__":
    uvicorn.run("main:app",host="0.0.0.0",port=int(os.getenv("PORT",8000)))
