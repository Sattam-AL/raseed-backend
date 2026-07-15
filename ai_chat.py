"""
Raseed AI — AI Chat Module
يدعم Claude API + Fallback محلي (عند غياب المفتاح أو فشل الاتصال)
"""

import os
import json
import httpx
from typing import Optional, List, Dict, Any

# ============================================================
# الإعدادات
# ============================================================
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

# ============================================================
# الدالة الرئيسية
# ============================================================
def chat(
    message: str,
    user_data: Dict[str, Any],
    history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    معالجة رسالة المستخدم وإرجاع الرد.

    Args:
        message: رسالة المستخدم
        user_data: بيانات المستخدم (الدخل، المصروفات، الرصيد)
        history: سجل المحادثة السابق

    Returns:
        Dict: {
            "reply": str,
            "history": list,
            "mode": "claude" | "rules" | "rules_fallback"
        }
    """
    if history is None:
        history = []

    # محاولة استخدام Claude API أولاً
    if CLAUDE_API_KEY and CLAUDE_API_KEY != "":
        try:
            return _claude_chat(message, user_data, history)
        except Exception as e:
            print(f"⚠️ Claude API فشل: {e} — التحول للـ Fallback")
            return _rules_chat(message, user_data, history, mode="rules_fallback")

    # إذا لم يوجد مفتاح، استخدم المنطق المحلي
    return _rules_chat(message, user_data, history, mode="rules")


# ============================================================
# Claude API
# ============================================================
def _claude_chat(
    message: str,
    user_data: Dict[str, Any],
    history: List[Dict[str, str]]
) -> Dict[str, Any]:
    """الاتصال بـ Claude API والحصول على رد."""

    # بناء الـ System Prompt
    system_prompt = _build_system_prompt(user_data)

    # بناء الـ Messages
    messages = _build_messages(history, message)

    # إرسال الطلب
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            CLAUDE_API_URL,
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": CLAUDE_MODEL,
                "system": system_prompt,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.7,
            },
        )
        response.raise_for_status()
        data = response.json()

    # استخراج الرد
    reply = data["content"][0]["text"]

    # تحديث السجل
    new_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]

    return {
        "reply": reply,
        "history": new_history,
        "mode": "claude",
    }


# ============================================================
# المنطق المحلي (Fallback)
# ============================================================
def _rules_chat(
    message: str,
    user_data: Dict[str, Any],
    history: List[Dict[str, str]],
    mode: str = "rules"
) -> Dict[str, Any]:
    """الرد باستخدام قواعد محلية (بدون Claude)."""

    msg = message.lower()
    income = user_data.get("monthly_income", 12000)
    expenses = user_data.get("monthly_expenses", 7200)
    balance = user_data.get("balance", 15400)
    saving = income - expenses

    # ------------------ سيارة ------------------
    if any(k in msg for k in ["سيارة", "سياره", "car", "سيارات"]):
        mp = 120000 / 60
        pct = (mp / income) * 100
        reply = (
            f"🚗 **تحليل شراء سيارة بـ 120,000 ريال:**\n\n"
            f"• راتبك: {income:,.0f} ريال\n"
            f"• القسط المتوقع (60 شهر): {mp:,.0f} ريال ({pct:.1f}% من راتبك)\n\n"
        )
        if pct < 25:
            reply += "✅ **القرار آمن.** القسط أقل من 25% من دخلك."
        else:
            reply += f"⚠️ **القسط مرتفع ({pct:.1f}%).** ننصح بدفعة أولى أكبر أو سيارة أقل سعراً."
        reply += "\n\n💡 *هذا تحليل مبدئي، استشر خبيراً مالياً قبل اتخاذ القرار.*"
        return _build_response(reply, history, message, mode)

    # ------------------ ادخار ------------------
    if any(k in msg for k in ["ادخار", "وفر", "توفير", "save", "saving"]):
        sp = saving * 0.2
        reply = (
            f"💰 **خطة الادخار:**\n\n"
            f"• الادخار المقترح (20% من صافي الدخل): {sp:,.0f} ريال/شهر\n"
            f"• بعد سنة: {sp*12:,.0f} ريال\n"
            f"• بعد 5 سنوات: {sp*60:,.0f} ريال\n\n"
            f"💡 *ابدأ بمبلغ صغير وزدّه تدريجياً.*"
        )
        return _build_response(reply, history, message, mode)

    # ------------------ قرض / تمويل ------------------
    if any(k in msg for k in ["قرض", "تمويل", "loan", "finance"]):
        max_loan = income * 0.33 * 60
        monthly = income * 0.33
        reply = (
            f"🏦 **الحد الآمن للقرض:**\n\n"
            f"• الحد الأقصى الآمن: {max_loan:,.0f} ريال\n"
            f"• القسط الشهري الآمن (33% من الدخل): {monthly:,.0f} ريال\n\n"
            f"⚠️ *لا تتجاوز 33% من دخلك للقسط الشهري.*"
        )
        return _build_response(reply, history, message, mode)

    # ------------------ رصيد ------------------
    if any(k in msg for k in ["رصيد", "حساب", "كم عندي", "balance"]):
        status = "✅ وضعك المالي جيد." if saving > 0 else "⚠️ مصاريفك تتجاوز دخلك!"
        reply = (
            f"💳 **رصيدك الحالي:**\n\n"
            f"• الرصيد: {balance:,.0f} ريال\n"
            f"• الدخل: {income:,.0f} ريال\n"
            f"• المصروفات: {expenses:,.0f} ريال\n"
            f"• صافي الشهر: {saving:,.0f} ريال\n\n"
            f"{status}"
        )
        return _build_response(reply, history, message, mode)

    # ------------------ مصاريف / إنفاق ------------------
    if any(k in msg for k in ["مصاريف", "انفاق", "إنفاق", "spending", "expenses"]):
        pct = (expenses / income) * 100
        status = "✅ في الحد المعقول (أقل من 70%)." if pct < 70 else "⚠️ مرتفع — حاول تقليل الكماليات."
        reply = (
            f"📊 **تحليل الإنفاق:**\n\n"
            f"• المصروفات: {expenses:,.0f} ريال\n"
            f"• نسبة الإنفاق من الدخل: {pct:.1f}%\n\n"
            f"{status}\n\n"
            f"💡 *ننصح بالالتزام بـ 50/30/20: 50% احتياجات، 30% رغبات، 20% ادخار.*"
        )
        return _build_response(reply, history, message, mode)

    # ------------------ افتراضي ------------------
    reply = (
        f"🤖 **أنا Raseed AI، مستشارك المالي الذكي.**\n\n"
        f"اسألني عن:\n"
        f"• 🚗 **شراء سيارة** (هل أقدر؟)\n"
        f"• 💰 **خطة ادخار** (كيف أوصل لهدفي؟)\n"
        f"• 🏦 **قرض أو تمويل** (هل هو آمن؟)\n"
        f"• 📊 **تحليل الإنفاق** (هل مصاريفي معقولة؟)\n"
        f"• 💳 **الرصيد** (كم معي؟)\n\n"
        f"*أنا هنا لمساعدتك في اتخاذ قرارات مالية أفضل.*"
    )
    return _build_response(reply, history, message, mode)


# ============================================================
# دوال مساعدة
# ============================================================
def _build_system_prompt(user_data: Dict[str, Any]) -> str:
    """بناء الـ System Prompt لـ Claude."""
    income = user_data.get("monthly_income", 12000)
    expenses = user_data.get("monthly_expenses", 7200)
    balance = user_data.get("balance", 15400)
    saving = income - expenses

    return f"""أنت **Raseed AI**، مستشار مالي ذكي باللغة العربية.

بيانات المستخدم:
- الدخل الشهري: {income:,.0f} ريال
- المصروفات الشهرية: {expenses:,.0f} ريال
- الرصيد الحالي: {balance:,.0f} ريال
- صافي الدخل الشهري: {saving:,.0f} ريال

تعليمات:
1. أجب بصراحة ووضوح.
2. استخدم أرقاماً دقيقة من بيانات المستخدم.
3. قدم نصائح عملية وقابلة للتنفيذ.
4. استخدم تنسيقاً جميلاً (نقاط، أقسام).
5. إذا كان السؤال خارج نطاق المالية، أعد توجيه المستخدم بلطف.
6. ابدأ الرد بـ "مرحباً! أنا Raseed 🤖"
7. لا تختلق معلومات، فقط حلل البيانات المتوفرة.

الهدف: مساعدة المستخدم على اتخاذ قرارات مالية أفضل."""


def _build_messages(history: List[Dict[str, str]], new_message: str) -> List[Dict[str, str]]:
    """بناء قائمة الرسائل لـ Claude."""
    messages = []
    for h in history[-10:]:  # آخر 10 رسائل فقط للحفاظ على السياق
        messages.append({
            "role": h.get("role", "user"),
            "content": h.get("content", ""),
        })
    messages.append({"role": "user", "content": new_message})
    return messages


def _build_response(
    reply: str,
    history: List[Dict[str, str]],
    message: str,
    mode: str
) -> Dict[str, Any]:
    """بناء كائن الرد الموحد."""
    new_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    return {
        "reply": reply,
        "history": new_history,
        "mode": mode,
    }
