import streamlit as st
import pandas as pd
import json
import base64
import html
from datetime import timedelta
from datetime import date, datetime, time

import plotly.express as px
import plotly.graph_objects as go

from openai import OpenAI
from supabase import create_client


# =========================================================
# 頁面設定
# =========================================================

st.set_page_config(
    page_title="健康與體態追蹤器",
    page_icon="⚖️",
    layout="centered"
)


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>
/* 適度緊湊：保留 Streamlit 預設字體、標籤高度與文字行距，避免重疊 */
.block-container {
    padding-top: 1.15rem !important;
    padding-bottom: 2rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}
/* 只調整主要區塊的間隔，不覆寫內部元件的文字行距 */
div[data-testid="stVerticalBlock"] { gap: .85rem !important; }
div[data-testid="stHorizontalBlock"] { gap: .65rem !important; }
/* 標題保留足夠的行高，避免與標籤擠在一起 */
h1, h2, h3, h4 { line-height: 1.4 !important; }
/* 表單標籤、輸入框和按鈕維持正常字體與高度 */
.stButton > button, .stDownloadButton > button {
    width: 100%;
    border-radius: 9px;
    min-height: 2.5rem;
}
/* 分隔線與圖表稍微縮小空白 */
hr { margin: .65rem 0 !important; }
div[data-testid="stPlotlyChart"] { margin: .2rem 0 !important; }
/* 主標題固定一行，手機不再佔兩行 */
.stApp h1 {
    font-size: 25px !important;
    line-height: 1.35 !important;
    white-space: nowrap !important;
    letter-spacing: -.4px;
}
/* 當日食物、餐別明細等次級標題小一號 */
.stApp h3 { font-size: 19px !important; line-height: 1.4 !important; }
.stApp h4 { font-size: 16px !important; line-height: 1.4 !important; }
/* 日期、體重、餐別選擇等輸入欄位標籤大一號 */
.stApp [data-testid="stWidgetLabel"] p,
.stApp [data-testid="stWidgetLabel"] label,
.stApp .stSelectbox label p,
.stApp .stDateInput label p,
.stApp .stNumberInput label p,
.stApp .stTimeInput label p {
    font-size: 17px !important;
    line-height: 1.5 !important;
}
/* 餐別明細兩行，營養素小一號但仍清晰 */
.meal-food {
    padding: 7px 0;
    border-bottom: 1px solid rgba(128,128,128,.14);
}
.meal-food:last-child { border-bottom: none; }
.meal-food-title {
    font-size: 16px;
    font-weight: 600;
    line-height: 1.55;
    overflow-wrap: anywhere;
}
.meal-food-portion { font-size: 15px; font-weight: 400; opacity: .8; }
.meal-food-macros {
    font-size: 13px;
    opacity: .82;
    margin-top: 3px;
    line-height: 1.5;
    overflow-wrap: anywhere;
}

/* 今日營養：數值縮小至內文字級 */
div[data-testid="stMetricValue"] {
    font-size: 18px !important;
    line-height: 1.4 !important;
    font-weight: 500 !important;
}

/* 指標名稱 */
div[data-testid="stMetricLabel"] p {
    font-size: 16px !important;
    line-height: 1.4 !important;
}

/* 減少數值與標籤間距 */
div[data-testid="stMetric"] {
    padding: 2px 0 !important;
    gap: 2px !important;
}

/* =========================================================
   手機版響應式與底部浮動儲存列 (Sticky Bottom Bar)
   ========================================================= */
@media (max-width: 768px) {
    .block-container {
        padding-top: .9rem !important;
        padding-left: .75rem !important;
        padding-right: .75rem !important;
        padding-bottom: 6.5rem !important; /* 墊高底部，避免遮擋內容 */
    }
    .stApp h1 { font-size: 21px !important; letter-spacing: -.6px; }
    .stApp h3 { font-size: 18px !important; }
    .stApp h4 { font-size: 16px !important; }
    div[data-testid="stVerticalBlock"] { gap: .75rem !important; }
    div[data-testid="stHorizontalBlock"] { gap: .5rem !important; }

    /* 浮動儲存列 */
    div[data-testid="stVerticalBlock"]:has(> div.sticky-save-wrapper) {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        width: 100vw !important;
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(8px);
        padding: 10px 16px env(safe-area-inset-bottom, 12px) 16px !important;
        border-top: 1px solid rgba(0, 0, 0, 0.08);
        box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.08);
        z-index: 999999 !important;
    }

    @media (prefers-color-scheme: dark) {
        div[data-testid="stVerticalBlock"]:has(> div.sticky-save-wrapper) {
            background: rgba(14, 17, 23, 0.95) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
    }
}

/* 六個功能固定一列，可用手指左右滑動；只作用於功能選單 */
.st-key-selected_page {
    min-width: 0 !important;
    max-width: 100% !important;
    overflow: hidden !important;
}
.st-key-selected_page [role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
    touch-action: pan-x !important;
    gap: 22px !important;
    padding: 5px 2px 9px !important;
}
.st-key-selected_page [role="radiogroup"]::-webkit-scrollbar { display: none !important; }
.st-key-selected_page [role="radiogroup"] > label {
    display: inline-flex !important;
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: max-content !important;
    max-width: none !important;
    white-space: nowrap !important;
    padding: 6px 0 !important;
    margin: 0 !important;
    border-bottom: 3px solid transparent !important;
}
.st-key-selected_page [role="radiogroup"] > label:has(input:checked) {
    border-bottom-color: #ff4b4b !important;
}
.st-key-selected_page [role="radiogroup"] > label > div:first-child { display: none !important; }
.st-key-selected_page [role="radiogroup"] > label p,
.st-key-selected_page [role="radiogroup"] > label span {
    white-space: nowrap !important;
    word-break: normal !important;
    overflow-wrap: normal !important;
    font-size: 16px !important;
    line-height: 1.5 !important;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# Supabase
# =========================================================

@st.cache_resource
def get_supabase():
    supabase_url = st.secrets.get("SUPABASE_URL", "")
    supabase_key = st.secrets.get("SUPABASE_KEY", "")

    if not supabase_url or not supabase_key:
        st.error("找不到 SUPABASE_URL 或 SUPABASE_KEY")
        st.stop()

    return create_client(supabase_url, supabase_key)


supabase = get_supabase()


# =========================================================
# OpenAI
# =========================================================

@st.cache_resource
def get_openai_client():
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


# =========================================================
# 營養分析 System Prompt 常數
# =========================================================

NUTRITION_SYSTEM_PROMPT = """
你是一位專精「台灣外食習慣」與「運動營養學」的資深臨床營養師。
請根據使用者提供的餐點內容（文字描述或餐盤照片），精確、嚴謹地估算食物份量與巨量營養素。

【分析與換算標準】
1. 份量錨定標準：
   - 標準中碗白飯（熟重約 160g）：熱量 280 kcal，碳水 60g，蛋白質 6g，脂肪 0g。
   - 掌心大小肉類（一份蛋白質約 35g 熟重）：蛋白質 7g。
   - 一顆雞蛋：蛋白質 7g，脂肪 5g，熱量約 75 kcal。
2. 外食烹調隱藏油脂（重要）：
   - 外食炒青菜、熱炒類，每份蔬菜必須強制計入 5~8g 烹調吸附油（約 45~70 kcal 脂肪），不可僅算蔬菜生鮮熱量。
   - 炸排骨、炸雞腿等裹粉外皮，需計入麵衣吸油與澱粉。
3. 複合料理拆解：
   - 遇到便當、火鍋、合菜等複合餐點，必須自動拆解成多個 item（例如：白飯、炸排骨、炒高麗菜、番茄炒蛋），不可混為單一項。
4. 物理與數學一致性：
   - 每一項食物的熱量必須符合巨量營養素公式：Calories ≈ (Carbs * 4) + (Protein * 4) + (Fat * 9)，誤差不得超過 5%。

請只回傳標準 JSON 物件，格式如下：
{
  "items": [
    {
      "name": "食物名稱（含烹調方式，例如：外食炒高麗菜、炸排骨）",
      "portion": "預估份量與重量（如：1平碗約160g、1掌心大）",
      "calories": 150,
      "protein": 13.0,
      "fat": 10.0,
      "carbs": 3.0
    }
  ]
}
"""


# =========================================================
# 共用函式
# =========================================================

def safe_float(value, default=0):
    try:
        if value is None:
            return default
        return float(value)
    except:
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(round(float(value)))
    except:
        return default


def simple_date(value):
    try:
        d = pd.to_datetime(value)
        return f"{d.month}/{d.day}"
    except:
        return str(value)


def clean_ai_json(text):
    if not text:
        return {}
    text = (
        text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )
    return json.loads(text)


def parse_saved_time(saved_value, fallback=time(9, 0)):
    if not saved_value:
        return fallback
    try:
        return datetime.strptime(str(saved_value), "%H:%M").time()
    except:
        return fallback


MEAL_OPTIONS = ["早餐", "午餐", "晚餐", "點心", "宵夜"]

def normalize_meal(value):
    return value if value in MEAL_OPTIONS else "點心"

def normalize_foods(items):
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except (ValueError, TypeError):
            items = []
    if not isinstance(items, list):
        return []
    return [{**x, "meal": normalize_meal(x.get("meal"))}
            for x in items if isinstance(x, dict)]


# =========================================================
# 運動消耗計算
# =========================================================

def calculate_exercise_calories(weight_kg, met, minutes):
    calories = (
        safe_float(met)
        * 3.5
        * safe_float(weight_kg)
        / 200
        * safe_float(minutes)
    )
    return round(calories)


# =========================================================
# 飲食執行率
# =========================================================

def target_score(actual, target):
    actual = safe_float(actual)
    target = safe_float(target)

    if target <= 0:
        return 100

    score = 100 - (abs(actual - target) / target * 100)
    return max(0, min(100, score))


def calculate_diet_adherence(
    actual_cal, actual_carbs, actual_protein, actual_fat,
    target_cal, target_carbs, target_protein, target_fat
):
    scores = [
        target_score(actual_cal, target_cal),
        target_score(actual_carbs, target_carbs),
        target_score(actual_protein, target_protein),
        target_score(actual_fat, target_fat)
    ]
    return round(sum(scores) / len(scores))


# =========================================================
# 每日紀錄 Supabase
# =========================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_daily_logs(person):
    try:
        response = (
            supabase
            .table("daily_logs")
            .select("*")
            .eq("person", person)
            .order("date")
            .execute()
        )
        return pd.DataFrame(response.data or [])
    except Exception as e:
        st.error(f"讀取每日紀錄失敗：{e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_daily_record(person, selected_date):
    try:
        response = (
            supabase
            .table("daily_logs")
            .select("*")
            .eq("person", person)
            .eq("date", str(selected_date))
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        st.error(f"讀取紀錄失敗：{e}")
        return None


def save_daily_record(person, record_date, weight, measure_time, ex_name, ex_cal, foods):
    total_cal = sum(safe_float(f.get("calories", 0)) for f in foods)
    total_protein = sum(safe_float(f.get("protein", 0)) for f in foods)
    total_fat = sum(safe_float(f.get("fat", 0)) for f in foods)
    total_carbs = sum(safe_float(f.get("carbs", 0)) for f in foods)

    payload = {
        "person": person,
        "date": str(record_date),
        "weight": round(float(weight), 2),
        "measure_time": measure_time or "",
        "ex_name": ex_name or "",
        "ex_cal": safe_int(ex_cal),
        "items_json": foods,
        "total_calories": safe_int(total_cal),
        "total_protein": round(total_protein, 1),
        "total_fat": round(total_fat, 1),
        "total_carbs": round(total_carbs, 1)
    }

    existing = get_daily_record(person, record_date)

    try:
        if existing:
            (
                supabase
                .table("daily_logs")
                .update(payload)
                .eq("id", existing["id"])
                .execute()
            )
        else:
            (
                supabase
                .table("daily_logs")
                .insert(payload)
                .execute()
            )
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"儲存失敗：{e}")
        return False


def delete_daily_record(record_id):
    try:
        (
            supabase
            .table("daily_logs")
            .delete()
            .eq("id", record_id)
            .execute()
        )
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"刪除失敗：{e}")
        return False


# =========================================================
# 飲食目標 Supabase
# =========================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_nutrition_targets(person):
    try:
        response = (
            supabase
            .table("nutrition_targets")
            .select("*")
            .eq("person", person)
            .order("effective_date")
            .execute()
        )
        return pd.DataFrame(response.data or [])
    except Exception as e:
        st.error(f"讀取飲食目標失敗：{e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_target_for_date(person, selected_date):
    try:
        response = (
            supabase
            .table("nutrition_targets")
            .select("*")
            .eq("person", person)
            .lte("effective_date", str(selected_date))
            .order("effective_date", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        st.error(f"讀取飲食目標失敗：{e}")
        return None


@st.cache_data(ttl=60, show_spinner=False)
def get_exact_target(person, effective_date):
    try:
        response = (
            supabase
            .table("nutrition_targets")
            .select("*")
            .eq("person", person)
            .eq("effective_date", str(effective_date))
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except:
        return None


def save_nutrition_target(person, effective_date, calories, carbs, protein, fat):
    payload = {
        "person": person,
        "effective_date": str(effective_date),
        "calories": safe_float(calories),
        "carbs": safe_float(carbs),
        "protein": safe_float(protein),
        "fat": safe_float(fat)
    }

    existing = get_exact_target(person, effective_date)

    try:
        if existing:
            (
                supabase
                .table("nutrition_targets")
                .update(payload)
                .eq("id", existing["id"])
                .execute()
            )
        else:
            (
                supabase
                .table("nutrition_targets")
                .insert(payload)
                .execute()
            )
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"飲食目標儲存失敗：{e}")
        return False


def delete_nutrition_target(target_id):
    try:
        (
            supabase
            .table("nutrition_targets")
            .delete()
            .eq("id", target_id)
            .execute()
        )
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"刪除飲食目標失敗：{e}")
        return False


# =========================================================
# InBody Supabase
# =========================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_inbody_logs(person):
    try:
        response = (
            supabase
            .table("inbody_logs")
            .select("*")
            .eq("person", person)
            .order("date")
            .execute()
        )
        return pd.DataFrame(response.data or [])
    except Exception as e:
        st.error(f"讀取 InBody 失敗：{e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_inbody_record(person, selected_date):
    try:
        response = (
            supabase
            .table("inbody_logs")
            .select("*")
            .eq("person", person)
            .eq("date", str(selected_date))
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        st.error(f"讀取 InBody 紀錄失敗：{e}")
        return None


def save_inbody_record(person, record_date, weight, body_fat, muscle, bmr):
    payload = {
        "person": person,
        "date": str(record_date),
        "weight": round(float(weight), 2),
        "body_fat": round(float(body_fat), 2),
        "muscle": round(float(muscle), 2),
        "bmr": safe_int(bmr)
    }

    existing = get_inbody_record(person, record_date)

    try:
        if existing:
            (
                supabase
                .table("inbody_logs")
                .update(payload)
                .eq("id", existing["id"])
                .execute()
            )
        else:
            (
                supabase
                .table("inbody_logs")
                .insert(payload)
                .execute()
            )
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"InBody 儲存失敗：{e}")
        return False


def delete_inbody_record(record_id):
    try:
        (
            supabase
            .table("inbody_logs")
            .delete()
            .eq("id", record_id)
            .execute()
        )
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"InBody 刪除失敗：{e}")
        return False


# =========================================================
# Session State
# =========================================================

if "current_foods" not in st.session_state:
    st.session_state.current_foods = []

if "loaded_food_key" not in st.session_state:
    st.session_state.loaded_food_key = ""

if "ai_exercise_result_key" not in st.session_state:
    st.session_state.ai_exercise_result_key = ""

if "ai_exercise_result" not in st.session_state:
    st.session_state.ai_exercise_result = None


# =========================================================
# 標題
# =========================================================

st.title("健康與體態追蹤系統")

person = st.radio(
    "選擇使用者",
    ["Shing", "Gloria"],
    horizontal=True,
    label_visibility="collapsed"
)

PAGE_NAMES = ["紀錄", "趨勢", "歷史紀錄", "飲食目標", "InBody", "區間營養報表"]
# 使用舊版的橫向分頁外觀；只執行選取頁面，維持加速效果。
selected_page = st.radio(
    "功能頁面", PAGE_NAMES, horizontal=True,
    label_visibility="collapsed", key="selected_page"
)
# 僅執行選取的頁面，避免每次互動都重建所有圖表及查詢全部資料。


# =========================================================
# TAB 1 每日紀錄
# =========================================================

if selected_page == "紀錄":
    st.subheader(f"每日紀錄｜{person}")

    # =====================================================
    # 日期
    # =====================================================

    record_date = st.date_input(
        "日期",
        value=date.today(),
        format="YYYY/MM/DD",
        key=f"record_date_{person}"
    )

    session_key = f"{person}_{record_date}"
    old_record = get_daily_record(person, record_date)

    # =====================================================
    # 載入當日食物
    # =====================================================

    if st.session_state.loaded_food_key != session_key:
        if old_record:
            old_items = old_record.get("items_json", [])
            if isinstance(old_items, str):
                try:
                    old_items = json.loads(old_items)
                except:
                    old_items = []
            st.session_state.current_foods = normalize_foods(old_items)
        else:
            st.session_state.current_foods = []

        st.session_state.loaded_food_key = session_key

    # =====================================================
    # 運動欄位 Session State
    # =====================================================

    exercise_name_key = f"final_ex_name_{person}_{record_date}"
    exercise_cal_key = f"final_ex_cal_{person}_{record_date}"

    old_ex_name = old_record.get("ex_name", "") if old_record else ""
    old_ex_cal = safe_int(old_record.get("ex_cal", 0)) if old_record else 0

    if exercise_name_key not in st.session_state:
        st.session_state[exercise_name_key] = old_ex_name or ""

    if exercise_cal_key not in st.session_state:
        st.session_state[exercise_cal_key] = old_ex_cal

    # =====================================================
    # 體重
    # =====================================================

    default_weight = safe_float(old_record.get("weight", 60)) if old_record else 60.0

    weight = st.number_input(
        "體重 (kg)",
        min_value=30.0,
        max_value=200.0,
        value=float(default_weight),
        step=0.1,
        format="%.1f",
        key=f"daily_weight_{session_key}"
    )

    # =====================================================
    # 幾點測量
    # =====================================================

    default_measure_time = time(9, 0)
    if old_record:
        saved_measure_time = old_record.get("measure_time", "") or ""
        default_measure_time = parse_saved_time(saved_measure_time, time(9, 0))

    selected_measure_time = st.time_input(
        "幾點測量",
        value=default_measure_time,
        step=1800,
        key=f"measure_time_{session_key}"
    )
    measure_time = selected_measure_time.strftime("%H:%M")

    # =====================================================
    # 當日飲食目標
    # =====================================================

    current_target = get_target_for_date(person, record_date)

    if current_target:
        st.info(
            "🎯 今日飲食目標｜"
            f"{safe_int(current_target['calories'])} kcal｜"
            f"碳水 {safe_float(current_target['carbs']):.0f}g｜"
            f"蛋白質 {safe_float(current_target['protein']):.0f}g｜"
            f"脂肪 {safe_float(current_target['fat']):.0f}g"
        )
    else:
        st.warning("目前尚未設定這一天適用的飲食目標。")

    # =====================================================
    # 飲食紀錄
    # =====================================================

    st.markdown("---")
    st.subheader("🍱 飲食紀錄")

    selected_meal = st.selectbox(
        "新增餐點的餐別", MEAL_OPTIONS,
        key=f"meal_select_{session_key}"
    )

    # =====================================================
    # AI 文字食物
    # =====================================================

    st.write("### ✍️ 文字快速輸入")

    food_text = st.text_area(
        "輸入食物與份量",
        placeholder="例如：\n茶葉蛋兩顆\n無糖豆漿400ml\n排骨便當飯吃半碗",
        height=110,
        key=f"food_text_{session_key}"
    )

    if st.button("✨ AI 分析文字食物", use_container_width=True, key=f"food_text_ai_{session_key}"):
        if not food_text.strip():
            st.warning("請先輸入食物")
        else:
            client = get_openai_client()
            if client is None:
                st.error("尚未設定 OPENAI_API_KEY")
            else:
                with st.spinner("AI 正在分析營養素..."):
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            response_format={"type": "json_object"},
                            temperature=0.2,
                            messages=[
                                {"role": "system", "content": NUTRITION_SYSTEM_PROMPT},
                                {"role": "user", "content": f"使用者輸入的食物內容：\n{food_text}"}
                            ],
                            max_tokens=800
                        )

                        res = response.choices[0].message.content
                        parsed = clean_ai_json(res)
                        new_items = parsed.get("items", [])

                        if new_items:
                            st.session_state.current_foods.extend(
                                [{**item, "meal": selected_meal} for item in new_items]
                            )
                            st.success(f"已加入 {len(new_items)} 項食物")
                            st.rerun()
                        else:
                            st.warning("AI 沒有辨識到食物")

                    except Exception as e:
                        st.error(f"文字辨識失敗：{e}")

    # =====================================================
    # AI 照片食物
    # =====================================================

    st.markdown("---")
    st.write("### 📷 拍照辨識")

    uploaded_file = st.file_uploader(
        "拍照或選擇餐點照片",
        type=["jpg", "jpeg", "png"],
        key=f"food_photo_{session_key}"
    )

    photo_context = st.text_input(
        "💡 餐點補充說明（選填，填寫可大幅提升準確度）",
        placeholder="例如：便當飯吃半碗、外食熱炒偏油、無糖拿鐵",
        key=f"photo_context_{session_key}"
    )

    if uploaded_file and st.button("✨ 開始 AI 辨識", use_container_width=True, key=f"photo_ai_btn_{session_key}"):
        client = get_openai_client()
        if client is None:
            st.error("尚未設定 OPENAI_API_KEY")
        else:
            with st.spinner("AI 正在精準分析餐盤細節..."):
                try:
                    bytes_data = uploaded_file.getvalue()
                    base64_image = base64.b64encode(bytes_data).decode("utf-8")

                    user_prompt_text = "請辨識照片中的餐點並拆解估算營養素。"
                    if photo_context.strip():
                        user_prompt_text += f"\n【使用者重要備註】：{photo_context.strip()}，請務必依據此備註調整份量與吸附油估算！"

                    response = client.chat.completions.create(
                        model="gpt-4o",
                        response_format={"type": "json_object"},
                        temperature=0.2,
                        messages=[
                            {"role": "system", "content": NUTRITION_SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": user_prompt_text},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}",
                                            "detail": "high"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=1000
                    )

                    res = response.choices[0].message.content
                    parsed = clean_ai_json(res)
                    new_items = parsed.get("items", [])

                    if new_items:
                        st.session_state.current_foods.extend(
                            [{**item, "meal": selected_meal} for item in new_items]
                        )
                        st.success(f"辨識完成，已加入 {len(new_items)} 項食物")
                        st.rerun()
                    else:
                        st.warning("AI 沒有辨識到食物")

                except Exception as e:
                    st.error(f"AI 辨識失敗：{e}")

    # =====================================================
    # 手動新增食物
    # =====================================================

    with st.expander("➕ 手動新增食物"):
        m_name = st.text_input("食物名稱", key=f"m_name_{session_key}")
        m_portion = st.text_input("份量", placeholder="例如：100g、1碗、2顆", key=f"m_portion_{session_key}")
        m_cal = st.number_input("熱量 kcal", min_value=0, value=0, step=10, key=f"m_cal_{session_key}")
        m_pro = st.number_input("蛋白質 g", min_value=0.0, value=0.0, step=1.0, key=f"m_pro_{session_key}")
        m_fat = st.number_input("脂肪 g", min_value=0.0, value=0.0, step=1.0, key=f"m_fat_{session_key}")
        m_carb = st.number_input("碳水化合物 g", min_value=0.0, value=0.0, step=1.0, key=f"m_carb_{session_key}")

        if st.button("加入食物", key=f"manual_food_{session_key}"):
            st.session_state.current_foods.append(
                {
                    "meal": selected_meal,
                    "name": m_name if m_name else "自訂食物",
                    "portion": m_portion,
                    "calories": safe_int(m_cal),
                    "protein": safe_float(m_pro),
                    "fat": safe_float(m_fat),
                    "carbs": safe_float(m_carb)
                }
            )
            st.rerun()

    # =====================================================
    # 當日食物表與明細
    # =====================================================

    if st.session_state.current_foods:

        st.markdown("---")
        st.write("### 當日食物")

        food_df = pd.DataFrame(st.session_state.current_foods)
        required_cols = ["meal", "name", "portion", "calories", "protein", "fat", "carbs"]

        for col in required_cols:
            if col not in food_df.columns:
                food_df[col] = "" if col in ["name", "portion", "meal"] else 0

        food_df = food_df[required_cols]

        st.markdown("#### 🍽️ 餐別明細")
        for meal in MEAL_OPTIONS:
            meal_items = food_df[food_df["meal"] == meal]
            if meal_items.empty:
                continue
            meal_cal = sum(safe_float(v) for v in meal_items["calories"])
            meal_rows = []
            for _, food in meal_items.iterrows():
                name = html.escape(str(food.get("name", "")))
                portion = html.escape(str(food.get("portion", "")))
                meal_rows.append(
                    '<div class="meal-food">'
                    f'<div class="meal-food-title">{name} '
                    f'<span class="meal-food-portion">· {portion}</span></div>'
                    '<div class="meal-food-macros">'
                    f'{safe_float(food.get("calories")):.0f} kcal &nbsp;｜&nbsp; '
                    f'碳 {safe_float(food.get("carbs")):.1f}g &nbsp;·&nbsp; '
                    f'蛋 {safe_float(food.get("protein")):.1f}g &nbsp;·&nbsp; '
                    f'脂 {safe_float(food.get("fat")):.1f}g'
                    '</div></div>'
                )
            with st.container(border=True):
                st.markdown(f"**{meal}**　｜　**{meal_cal:,.0f} kcal**")
                st.markdown("".join(meal_rows), unsafe_allow_html=True)

        st.caption("下方表格可修改餐別、份量與營養素，也可新增或刪除食物。")

        edited_food_df = st.data_editor(
            food_df,
            hide_index=True,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "meal": st.column_config.SelectboxColumn("餐別", options=MEAL_OPTIONS, required=True),
                "name": st.column_config.TextColumn("食物"),
                "portion": st.column_config.TextColumn("份量"),
                "calories": st.column_config.NumberColumn("熱量", format="%d kcal"),
                "protein": st.column_config.NumberColumn("蛋白質", format="%.1f g"),
                "fat": st.column_config.NumberColumn("脂肪", format="%.1f g"),
                "carbs": st.column_config.NumberColumn("碳水", format="%.1f g")
            },
            key=f"food_editor_{session_key}"
        )

        cleaned_foods = []
        for item in edited_food_df.to_dict("records"):
            cleaned_foods.append(
                {
                    "meal": normalize_meal(item.get("meal")),
                    "name": str(item.get("name", "")),
                    "portion": str(item.get("portion", "")),
                    "calories": safe_int(item.get("calories", 0)),
                    "protein": safe_float(item.get("protein", 0)),
                    "fat": safe_float(item.get("fat", 0)),
                    "carbs": safe_float(item.get("carbs", 0))
                }
            )

        st.session_state.current_foods = cleaned_foods

        total_cal = sum(x["calories"] for x in cleaned_foods)
        total_pro = sum(x["protein"] for x in cleaned_foods)
        total_fat = sum(x["fat"] for x in cleaned_foods)
        total_carb = sum(x["carbs"] for x in cleaned_foods)

        # =================================================
        # 今日營養
        # =================================================

        st.write("### 今日營養")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("總熱量", f"{total_cal:.0f} kcal")
            st.metric("蛋白質", f"{total_pro:.1f} g")
        with c2:
            st.metric("脂肪", f"{total_fat:.1f} g")
            st.metric("碳水", f"{total_carb:.1f} g")

        # =================================================
        # 飲食執行率
        # =================================================

        if current_target:
            adherence = calculate_diet_adherence(
                total_cal, total_carb, total_pro, total_fat,
                current_target["calories"],
                current_target["carbs"],
                current_target["protein"],
                current_target["fat"]
            )

            st.markdown("---")
            st.metric("🎯 今日飲食執行率", f"{adherence}%")
            st.write(f"熱量：{total_cal:.0f} / {safe_float(current_target['calories']):.0f} kcal")
            st.write(f"碳水：{total_carb:.1f} / {safe_float(current_target['carbs']):.0f} g")
            st.write(f"蛋白質：{total_pro:.1f} / {safe_float(current_target['protein']):.0f} g")
            st.write(f"脂肪：{total_fat:.1f} / {safe_float(current_target['fat']):.0f} g")

        # =================================================
        # 三大營養素熱量比例
        # =================================================

        protein_kcal = total_pro * 4
        fat_kcal = total_fat * 9
        carb_kcal = total_carb * 4
        macro_total = protein_kcal + fat_kcal + carb_kcal

        if macro_total > 0:
            st.write("### 三大營養素熱量占比")
            macro_df = pd.DataFrame(
                {
                    "營養素": ["蛋白質", "脂肪", "碳水"],
                    "熱量": [protein_kcal, fat_kcal, carb_kcal]
                }
            )

            fig_macro = px.pie(
                macro_df,
                names="營養素",
                values="熱量",
                hole=0.45
            )
            fig_macro.update_traces(textposition="inside", textinfo="percent+label")
            fig_macro.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", y=-0.08)
            )
            st.plotly_chart(
                fig_macro,
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"daily_macro_chart_{person}_{record_date}"
            )

        # =================================================
        # 飲食下方快捷操作（含手機版浮動樣式標記）
        # =================================================

        st.markdown("---")
        with st.container():
            st.markdown('<div class="sticky-save-wrapper"></div>', unsafe_allow_html=True)
            btn_c1, btn_c2 = st.columns([2, 1])

            with btn_c1:
                save_food_label = "💾 儲存今日飲食與體態" if not old_record else "💾 更新今日飲食與體態"
                if st.button(save_food_label, type="primary", use_container_width=True, key=f"quick_save_food_{session_key}"):
                    cur_ex_name = st.session_state.get(exercise_name_key, "")
                    cur_ex_cal = st.session_state.get(exercise_cal_key, 0)
                    success = save_daily_record(
                        person,
                        record_date,
                        weight,
                        measure_time,
                        cur_ex_name,
                        cur_ex_cal,
                        st.session_state.current_foods
                    )
                    if success:
                        st.success("紀錄已成功儲存！")
                        st.rerun()

            with btn_c2:
                if st.button("🗑️ 清空食物", use_container_width=True, key=f"clear_food_{session_key}"):
                    st.session_state.current_foods = []
                    st.rerun()

    else:
        total_cal = 0
        total_pro = 0
        total_fat = 0
        total_carb = 0
        st.info("這一天尚未加入食物")

    # =====================================================
    # 運動
    # =====================================================

    st.markdown("---")
    st.subheader("🏃 運動紀錄")
    st.caption(f"目前使用體重：{weight:.1f} kg")

    exercise_text = st.text_input(
        "輸入運動",
        placeholder="例如：重訓60分鐘、慢跑20分鐘、上坡快走1小時、休息日",
        key=f"exercise_text_{session_key}"
    )

    if st.button("✨ AI 分析並自動填入", use_container_width=True, key=f"exercise_ai_{session_key}"):
        if not exercise_text.strip():
            st.warning("請先輸入運動內容")
        elif exercise_text.strip().lower() in ["休息日", "休息", "rest", "rest day"]:
            st.session_state[exercise_name_key] = "休息日"
            st.session_state[exercise_cal_key] = 0
            st.session_state.ai_exercise_result = {
                "name": "休息日",
                "minutes": 0,
                "met": 0,
                "intensity": "休息",
                "calories": 0
            }
            st.session_state.ai_exercise_result_key = session_key
            st.rerun()
        else:
            client = get_openai_client()
            if client is None:
                st.error("尚未設定 OPENAI_API_KEY")
            else:
                with st.spinner("AI 正在分析運動與估算消耗..."):
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            response_format={"type": "json_object"},
                            temperature=0.2,
                            messages=[
                                {
                                    "role": "system",
                                    "content": """
你是一個運動紀錄分析助手。
請根據使用者輸入判斷運動名稱、時間（分鐘）、運動強度與合理 MET 值。
只回傳 JSON 物件，格式如下：
{
  "exercise_name": "重量訓練",
  "minutes": 60,
  "intensity": "一般",
  "met": 5.0
}
不要自己計算卡路里。
"""
                                },
                                {
                                    "role": "user",
                                    "content": exercise_text
                                }
                            ],
                            max_tokens=300
                        )

                        res = response.choices[0].message.content
                        parsed = clean_ai_json(res)

                        ex_ai_name = parsed.get("exercise_name", exercise_text)
                        ex_ai_minutes = safe_float(parsed.get("minutes", 0))
                        ex_ai_met = safe_float(parsed.get("met", 0))
                        ex_ai_intensity = parsed.get("intensity", "")

                        estimated_cal = calculate_exercise_calories(
                            weight,
                            ex_ai_met,
                            ex_ai_minutes
                        )

                        final_name = f"{ex_ai_name} {ex_ai_minutes:.0f}分鐘" if ex_ai_minutes > 0 else ex_ai_name

                        st.session_state[exercise_name_key] = final_name
                        st.session_state[exercise_cal_key] = estimated_cal
                        st.session_state.ai_exercise_result = {
                            "name": ex_ai_name,
                            "minutes": ex_ai_minutes,
                            "met": ex_ai_met,
                            "intensity": ex_ai_intensity,
                            "calories": estimated_cal
                        }
                        st.session_state.ai_exercise_result_key = session_key
                        st.rerun()

                    except Exception as e:
                        st.error(f"運動辨識失敗：{e}")

    # =====================================================
    # AI 運動結果展示
    # =====================================================

    if st.session_state.ai_exercise_result and st.session_state.ai_exercise_result_key == session_key:
        ai_ex = st.session_state.ai_exercise_result
        st.success("✅ AI 已自動填入下方運動紀錄")
        if ai_ex["minutes"] > 0:
            ec1, ec2 = st.columns(2)
            with ec1:
                st.write(f"**運動：** {ai_ex['name']}")
                st.write(f"**時間：** {ai_ex['minutes']:.0f} 分鐘")
            with ec2:
                st.write(f"**強度：** {ai_ex['intensity']}")
        else:
            st.write("**運動：** 休息日")

        st.metric("🔥 估計運動消耗", f"{ai_ex['calories']} kcal")

    # =====================================================
    # 正式運動欄位
    # =====================================================

    ex_name = st.text_input("運動內容", key=exercise_name_key)
    ex_cal = st.number_input("運動消耗 kcal", min_value=0, step=10, key=exercise_cal_key)

    # =====================================================
    # 底部儲存每日紀錄
    # =====================================================

    if st.button(
        "💾 更新這一天紀錄" if old_record else "💾 儲存這一天紀錄",
        type="primary",
        key=f"save_daily_{session_key}"
    ):
        success = save_daily_record(
            person,
            record_date,
            weight,
            measure_time,
            ex_name,
            ex_cal,
            st.session_state.current_foods
        )
        if success:
            st.success("紀錄已永久儲存！")
            st.rerun()


# =========================================================
# TAB 2 趨勢
# =========================================================

if selected_page == "趨勢":
    st.subheader("📈 體重趨勢")

    df = get_daily_logs(person)

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
        df = df.sort_values("date")

        fig_weight = go.Figure()
        fig_weight.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["weight"],
                mode="lines+markers",
                hovertemplate="%{x|%m/%d}<br>%{y:.1f} kg<extra></extra>"
            )
        )

        valid_weight = df["weight"].dropna()
        if not valid_weight.empty:
            min_weight = valid_weight.min()
            max_weight = valid_weight.max()
            lower = max(30, min_weight - 2)
            upper = max_weight + 2
            if upper - lower < 5:
                upper = lower + 5

            fig_weight.update_yaxes(range=[lower, upper], tickformat=".1f", title="kg")

        fig_weight.update_xaxes(tickformat="%m/%d", nticks=6, title="")
        fig_weight.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=20),
            showlegend=False
        )

        st.plotly_chart(
            fig_weight,
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"weight_chart_{person}"
        )

        # =================================================
        # 單日營養
        # =================================================

        st.markdown("---")
        st.subheader("🍱 單日營養")

        date_options = df["date"].dt.date.tolist()
        selected_macro_date = st.selectbox(
            "選擇日期",
            options=date_options,
            format_func=lambda x: f"{x.month}/{x.day}",
            key=f"macro_date_{person}"
        )

        selected_row = df[df["date"].dt.date == selected_macro_date].iloc[0]

        pro = safe_float(selected_row.get("total_protein", 0))
        fat = safe_float(selected_row.get("total_fat", 0))
        carb = safe_float(selected_row.get("total_carbs", 0))
        calories = safe_float(selected_row.get("total_calories", 0))
        exercise_cal = safe_float(selected_row.get("ex_cal", 0))

        mc1, mc2 = st.columns(2)
        with mc1:
            st.metric("飲食熱量", f"{calories:.0f} kcal")
            st.metric("蛋白質", f"{pro:.1f} g")
        with mc2:
            st.metric("運動消耗", f"{exercise_cal:.0f} kcal")
            st.metric("碳水", f"{carb:.1f} g")

        protein_kcal = pro * 4
        fat_kcal = fat * 9
        carb_kcal = carb * 4

        if protein_kcal + fat_kcal + carb_kcal > 0:
            macro_df = pd.DataFrame(
                {
                    "營養素": ["蛋白質", "脂肪", "碳水"],
                    "熱量": [protein_kcal, fat_kcal, carb_kcal]
                }
            )

            fig_trend_macro = px.pie(
                macro_df,
                names="營養素",
                values="熱量",
                hole=0.45
            )
            fig_trend_macro.update_traces(textposition="inside", textinfo="percent+label")
            fig_trend_macro.update_layout(
                height=330,
                margin=dict(l=10, r=10, t=10, b=10)
            )

            st.plotly_chart(
                fig_trend_macro,
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"trend_macro_chart_{person}_{selected_macro_date}"
            )

    else:
        st.info("尚無歷史資料")


# =========================================================
# TAB 3 歷史紀錄
# =========================================================

if selected_page == "歷史紀錄":
    st.subheader("📋 教練追蹤紀錄")

    history_df = get_daily_logs(person)

    if not history_df.empty:
        history_df = history_df.sort_values("date", ascending=False)
        coach_rows = []

        # 一次讀取全部目標，避免每筆歷史紀錄都重新查詢 Supabase。
        history_targets = get_nutrition_targets(person)
        target_entries = []
        if not history_targets.empty:
            for target_item in history_targets.to_dict("records"):
                effective = pd.to_datetime(target_item.get("effective_date"), errors="coerce")
                if pd.notna(effective):
                    target_entries.append((effective.date(), target_item))
            target_entries.sort(key=lambda pair: pair[0], reverse=True)

        for _, row in history_df.iterrows():
            row_date = pd.to_datetime(row["date"]).date()
            target = next((entry for effective, entry in target_entries if effective <= row_date), None)

            actual_cal = safe_float(row.get("total_calories", 0))
            actual_carb = safe_float(row.get("total_carbs", 0))
            actual_pro = safe_float(row.get("total_protein", 0))
            actual_fat = safe_float(row.get("total_fat", 0))

            if target:
                adherence = calculate_diet_adherence(
                    actual_cal, actual_carb, actual_pro, actual_fat,
                    target["calories"], target["carbs"], target["protein"], target["fat"]
                )
                adherence_text = f"{adherence}%"
            else:
                adherence_text = "-"

            coach_rows.append(
                {
                    "日期": simple_date(row["date"]),
                    "體重": round(safe_float(row.get("weight", 0)), 1),
                    "幾點測量": row.get("measure_time", "") or "",
                    "飲食執行率": adherence_text,
                    "運動內容": row.get("ex_name", "") or "",
                    "碳水": round(actual_carb, 1),
                    "蛋白質": round(actual_pro, 1),
                    "脂肪": round(actual_fat, 1),
                    "運動消耗": f"{safe_int(row.get('ex_cal', 0))} kcal"
                }
            )

        coach_df = pd.DataFrame(coach_rows)
        st.dataframe(coach_df, hide_index=True, use_container_width=True)

        csv_data = coach_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ 下載教練版紀錄 CSV",
            data=csv_data,
            file_name=f"{person}_教練追蹤紀錄.csv",
            mime="text/csv",
            key=f"coach_csv_{person}"
        )

        st.markdown("---")
        st.write("### 編輯過往紀錄")

        edit_dates = history_df["date"].tolist()
        selected_edit_date = st.selectbox(
            "選擇日期",
            options=edit_dates,
            format_func=simple_date,
            key=f"history_edit_{person}"
        )

        selected_history = history_df[history_df["date"] == selected_edit_date].iloc[0]

        edit_weight = st.number_input(
            "體重",
            min_value=30.0,
            max_value=200.0,
            value=safe_float(selected_history.get("weight", 60)),
            step=0.1,
            key=f"edit_weight_{person}_{selected_edit_date}"
        )

        saved_edit_time = selected_history.get("measure_time", "") or ""
        edit_time_default = parse_saved_time(saved_edit_time, time(9, 0))

        edit_time_value = st.time_input(
            "幾點測量",
            value=edit_time_default,
            step=1800,
            key=f"edit_time_{person}_{selected_edit_date}"
        )
        edit_time = edit_time_value.strftime("%H:%M")

        edit_ex_name = st.text_input(
            "運動內容",
            value=selected_history.get("ex_name", "") or "",
            key=f"edit_ex_{person}_{selected_edit_date}"
        )

        edit_ex_cal = st.number_input(
            "運動消耗 kcal",
            min_value=0,
            value=safe_int(selected_history.get("ex_cal", 0)),
            step=10,
            key=f"edit_ex_cal_{person}_{selected_edit_date}"
        )

        raw_items = selected_history.get("items_json", [])
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except:
                raw_items = []

        edit_food_df = pd.DataFrame(raw_items)
        for col in ["meal", "name", "portion", "calories", "protein", "fat", "carbs"]:
            if col not in edit_food_df.columns:
                edit_food_df[col] = ("點心" if col == "meal" else "") if col in ["meal", "name", "portion"] else 0

        edit_food_df = edit_food_df[["meal", "name", "portion", "calories", "protein", "fat", "carbs"]]

        edited_history_foods = st.data_editor(
            edit_food_df,
            hide_index=True,
            num_rows="dynamic",
            use_container_width=True,
            key=f"history_food_editor_{person}_{selected_edit_date}"
        )

        ecol1, ecol2 = st.columns(2)
        with ecol1:
            if st.button("💾 儲存修改", type="primary", key=f"update_history_{person}_{selected_edit_date}"):
                foods = []
                for item in edited_history_foods.to_dict("records"):
                    foods.append(
                        {
                            "meal": normalize_meal(item.get("meal")),
                            "name": str(item.get("name", "")),
                            "portion": str(item.get("portion", "")),
                            "calories": safe_int(item.get("calories", 0)),
                            "protein": safe_float(item.get("protein", 0)),
                            "fat": safe_float(item.get("fat", 0)),
                            "carbs": safe_float(item.get("carbs", 0))
                        }
                    )

                success = save_daily_record(
                    person,
                    selected_edit_date,
                    edit_weight,
                    edit_time,
                    edit_ex_name,
                    edit_ex_cal,
                    foods
                )
                if success:
                    st.success("修改完成")
                    st.rerun()

        with ecol2:
            if st.button("🗑️ 刪除這筆", key=f"delete_history_{person}_{selected_edit_date}"):
                success = delete_daily_record(selected_history["id"])
                if success:
                    st.success("已刪除")
                    st.rerun()

    else:
        st.info("尚無歷史紀錄")


# =========================================================
# TAB 4 飲食目標
# =========================================================

if selected_page == "飲食目標":
    st.subheader(f"🎯 飲食目標｜{person}")
    st.caption("教練調整飲食目標時新增一筆即可。系統會依生效日期套用到之後的每日紀錄。")

    target_date = st.date_input(
        "生效日期",
        value=date.today(),
        format="YYYY/MM/DD",
        key=f"target_date_{person}"
    )

    existing_target = get_exact_target(person, target_date)

    if existing_target:
        default_target_cal = safe_float(existing_target.get("calories", 0))
        default_target_carbs = safe_float(existing_target.get("carbs", 0))
        default_target_protein = safe_float(existing_target.get("protein", 0))
        default_target_fat = safe_float(existing_target.get("fat", 0))
    else:
        if person == "Shing":
            default_target_cal = 2400
            default_target_carbs = 280
            default_target_protein = 170
            default_target_fat = 60
        else:
            default_target_cal = 1800
            default_target_carbs = 200
            default_target_protein = 120
            default_target_fat = 50

    target_calories = st.number_input(
        "每日熱量 kcal",
        min_value=0,
        value=int(default_target_cal),
        step=50,
        key=f"target_cal_{person}_{target_date}"
    )

    target_carbs = st.number_input(
        "碳水 g",
        min_value=0.0,
        value=float(default_target_carbs),
        step=5.0,
        key=f"target_carbs_{person}_{target_date}"
    )

    target_protein = st.number_input(
        "蛋白質 g",
        min_value=0.0,
        value=float(default_target_protein),
        step=5.0,
        key=f"target_protein_{person}_{target_date}"
    )

    target_fat = st.number_input(
        "脂肪 g",
        min_value=0.0,
        value=float(default_target_fat),
        step=5.0,
        key=f"target_fat_{person}_{target_date}"
    )

    if st.button(
        "💾 更新飲食目標" if existing_target else "💾 新增飲食目標",
        type="primary",
        key=f"save_target_{person}_{target_date}"
    ):
        success = save_nutrition_target(
            person,
            target_date,
            target_calories,
            target_carbs,
            target_protein,
            target_fat
        )
        if success:
            st.success("飲食目標已儲存！")
            st.rerun()

    targets_df = get_nutrition_targets(person)

    if not targets_df.empty:
        st.markdown("---")
        st.write("### 飲食目標歷史")

        targets_show = targets_df.sort_values("effective_date", ascending=False).copy()
        targets_show["生效日期"] = targets_show["effective_date"].apply(simple_date)
        targets_show["熱量"] = pd.to_numeric(targets_show["calories"], errors="coerce").fillna(0).round(0).astype(int)
        targets_show["碳水"] = pd.to_numeric(targets_show["carbs"], errors="coerce")
        targets_show["蛋白質"] = pd.to_numeric(targets_show["protein"], errors="coerce")
        targets_show["脂肪"] = pd.to_numeric(targets_show["fat"], errors="coerce")

        st.dataframe(
            targets_show[["生效日期", "熱量", "碳水", "蛋白質", "脂肪"]],
            hide_index=True,
            use_container_width=True
        )

        delete_target_date = st.selectbox(
            "刪除某一筆目標",
            options=targets_df["effective_date"].tolist(),
            format_func=simple_date,
            key=f"delete_target_date_{person}"
        )

        selected_target_delete = targets_df[targets_df["effective_date"] == delete_target_date].iloc[0]

        if st.button("🗑️ 刪除這筆目標", key=f"delete_target_{person}_{delete_target_date}"):
            success = delete_nutrition_target(selected_target_delete["id"])
            if success:
                st.success("飲食目標已刪除")
                st.rerun()
    else:
        st.info("尚未設定任何飲食目標")


# =========================================================
# TAB 5 InBody
# =========================================================

if selected_page == "InBody":
    st.subheader(f"InBody｜{person}")

    ib_date = st.date_input(
        "測量日期",
        value=date.today(),
        format="YYYY/MM/DD",
        key=f"ib_date_{person}"
    )

    old_ib = get_inbody_record(person, ib_date)

    ib_weight = st.number_input(
        "InBody 體重 (kg)",
        min_value=30.0,
        max_value=200.0,
        value=safe_float(old_ib.get("weight", 60)) if old_ib else 60.0,
        step=0.1,
        key=f"ib_weight_{person}_{ib_date}"
    )

    ib_body_fat = st.number_input(
        "體脂率 (%)",
        min_value=1.0,
        max_value=70.0,
        value=safe_float(old_ib.get("body_fat", 20)) if old_ib else 20.0,
        step=0.1,
        key=f"ib_bodyfat_{person}_{ib_date}"
    )

    ib_muscle = st.number_input(
        "骨骼肌 (kg)",
        min_value=1.0,
        max_value=100.0,
        value=safe_float(old_ib.get("muscle", 25)) if old_ib else 25.0,
        step=0.1,
        key=f"ib_muscle_{person}_{ib_date}"
    )

    ib_bmr = st.number_input(
        "BMR (kcal)",
        min_value=500,
        max_value=5000,
        value=safe_int(old_ib.get("bmr", 1400)) if old_ib else 1400,
        step=10,
        key=f"ib_bmr_{person}_{ib_date}"
    )

    if st.button(
        "💾 更新 InBody" if old_ib else "💾 儲存 InBody",
        type="primary",
        key=f"save_ib_{person}_{ib_date}"
    ):
        success = save_inbody_record(
            person,
            ib_date,
            ib_weight,
            ib_body_fat,
            ib_muscle,
            ib_bmr
        )
        if success:
            st.success("InBody 已永久儲存！")
            st.rerun()

    ib_df = get_inbody_logs(person)

    if not ib_df.empty:
        ib_df["date"] = pd.to_datetime(ib_df["date"])
        ib_df = ib_df.sort_values("date")

        st.markdown("---")
        st.write("### InBody 體重趨勢")

        fig_ib = go.Figure()
        fig_ib.add_trace(
            go.Scatter(
                x=ib_df["date"],
                y=pd.to_numeric(ib_df["weight"], errors="coerce"),
                mode="lines+markers",
                hovertemplate="%{x|%m/%d}<br>%{y:.1f} kg<extra></extra>"
            )
        )
        fig_ib.update_xaxes(tickformat="%m/%d", nticks=6)
        fig_ib.update_yaxes(tickformat=".1f")
        fig_ib.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=20),
            showlegend=False
        )

        st.plotly_chart(
            fig_ib,
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"inbody_chart_{person}"
        )

        show_ib = ib_df.copy()
        show_ib["日期"] = show_ib["date"].apply(simple_date)
        show_ib["體重"] = pd.to_numeric(show_ib["weight"], errors="coerce").round(1)
        show_ib["體脂率"] = pd.to_numeric(show_ib["body_fat"], errors="coerce").round(1)
        show_ib["骨骼肌"] = pd.to_numeric(show_ib["muscle"], errors="coerce").round(1)
        show_ib["BMR"] = pd.to_numeric(show_ib["bmr"], errors="coerce").fillna(0).astype(int)

        st.dataframe(
            show_ib[["日期", "體重", "體脂率", "骨骼肌", "BMR"]],
            hide_index=True,
            use_container_width=True
        )

        ib_csv = show_ib[["日期", "體重", "體脂率", "骨骼肌", "BMR"]].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ 下載 InBody CSV",
            data=ib_csv,
            file_name=f"{person}_InBody.csv",
            mime="text/csv",
            key=f"inbody_csv_{person}"
        )

        st.markdown("---")
        delete_ib_date = st.selectbox(
            "刪除某筆 InBody",
            options=ib_df["date"].tolist(),
            format_func=simple_date,
            key=f"delete_ib_date_{person}"
        )

        selected_ib_delete = ib_df[ib_df["date"] == delete_ib_date].iloc[0]

        if st.button("🗑️ 刪除這筆 InBody", key=f"delete_ib_{person}_{delete_ib_date}"):
            success = delete_inbody_record(selected_ib_delete["id"])
            if success:
                st.success("InBody 已刪除")
                st.rerun()
    else:
        st.info("尚無 InBody 歷史紀錄")


# =========================================================
# TAB 6 區間營養報表（圖表 + HTML 匯出）
# =========================================================

if selected_page == "區間營養報表":
    st.subheader("📊 區間卡路里與營養素")
    st.caption("每日熱量與三大營養素趨勢；僅統計已儲存的飲食紀錄。")
    today = date.today()
    c_start, c_end = st.columns(2)
    with c_start:
        report_start = st.date_input("開始日期", value=today - timedelta(days=6), key=f"report_start_{person}")
    with c_end:
        report_end = st.date_input("結束日期", value=today, key=f"report_end_{person}")

    if report_start > report_end:
        st.warning("開始日期不可晚於結束日期。")
    else:
        raw = get_daily_logs(person)
        if raw.empty:
            st.info("尚無已儲存的飲食紀錄。")
        else:
            raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
            period = raw.loc[
                raw["date"].between(pd.Timestamp(report_start), pd.Timestamp(report_end))
            ].copy().sort_values("date")
            if period.empty:
                st.info("選擇的日期區間內沒有紀錄。")
            else:
                for col in ["total_calories", "total_carbs", "total_protein", "total_fat", "ex_cal"]:
                    period[col] = pd.to_numeric(period.get(col, 0), errors="coerce").fillna(0)
                period["日期"] = period["date"].dt.strftime("%m/%d")
                period["淨熱量"] = period["total_calories"] - period["ex_cal"]
                period["碳水熱量"] = period["total_carbs"] * 4
                period["蛋白質熱量"] = period["total_protein"] * 4
                period["脂肪熱量"] = period["total_fat"] * 9

                target = get_target_for_date(person, report_end)
                target_cal = safe_float(target.get("calories")) if target else 0
                a, b, c = st.columns(3)
                a.metric("紀錄天數", f"{len(period)} 天")
                b.metric("平均飲食熱量", f"{period['total_calories'].mean():,.0f} kcal")
                c.metric("平均淨熱量", f"{period['淨熱量'].mean():,.0f} kcal")

                fig_cal = go.Figure()
                fig_cal.add_bar(x=period["日期"], y=period["total_calories"], name="飲食熱量", marker_color="#35be89")
                fig_cal.add_scatter(x=period["日期"], y=period["淨熱量"], mode="lines+markers", name="淨熱量", line=dict(color="#3c82f6"))
                if target_cal > 0:
                    fig_cal.add_hline(y=target_cal, line_dash="dash", line_color="#e8a14b", annotation_text=f"目前目標 {target_cal:.0f}")
                fig_cal.update_layout(title="卡路里（區間檢視）", height=370, xaxis_title="", yaxis_title="kcal", margin=dict(l=10,r=10,t=55,b=20), barmode="group")
                st.plotly_chart(fig_cal, use_container_width=True, key=f"report_cal_{person}")

                fig_macro = go.Figure()
                for col, name, color in [
                    ("碳水熱量", "碳水", "#25b5aa"),
                    ("脂肪熱量", "脂肪", "#bd76d8"),
                    ("蛋白質熱量", "蛋白質", "#ffb340")
                ]:
                    fig_macro.add_bar(x=period["日期"], y=period[col], name=name, marker_color=color)
                fig_macro.update_layout(title="主要營養素（區間檢視）", barmode="stack", height=370, xaxis_title="", yaxis_title="換算熱量 kcal", margin=dict(l=10,r=10,t=55,b=20))
                st.plotly_chart(fig_macro, use_container_width=True, key=f"report_macro_{person}")

                avg = period[["碳水熱量", "脂肪熱量", "蛋白質熱量"]].sum()
                macro_sum = avg.sum()
                if macro_sum > 0:
                    st.markdown("**區間營養素平均占比（依熱量換算）**")
                    st.write("　｜　".join(
                        f"{label} {avg[col] / macro_sum:.0%}"
                        for col, label in [("碳水熱量", "碳水"), ("脂肪熱量", "脂肪"), ("蛋白質熱量", "蛋白質")]
                    ))

                table = period[["date", "total_calories", "淨熱量", "total_carbs", "total_protein", "total_fat"]].copy()
                table.columns = ["日期", "飲食熱量(kcal)", "淨熱量(kcal)", "碳水(g)", "蛋白質(g)", "脂肪(g)"]
                table["日期"] = table["日期"].dt.strftime("%Y/%m/%d")
                st.dataframe(table, hide_index=True, use_container_width=True)

                html_cal = fig_cal.to_html(full_html=False, include_plotlyjs=True)
                html_macro = fig_macro.to_html(full_html=False, include_plotlyjs=False)
                document = (
                    '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>營養區間報表</title><style>body{font-family:system-ui,sans-serif;max-width:1100px;margin:30px auto;padding:16px}'
                    'h1{font-size:24px}table{border-collapse:collapse;width:100%}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:right}'
                    'td:first-child,th:first-child{text-align:left}</style></head><body>'
                    f'<h1>{html.escape(person)}｜區間營養報表</h1><p>{report_start} ～ {report_end}｜紀錄 {len(period)} 天</p>'
                    f'<p>平均飲食熱量：{period["total_calories"].mean():,.0f} kcal；平均淨熱量：{period["淨熱量"].mean():,.0f} kcal</p>'
                    + html_cal + html_macro + table.to_html(index=False, escape=True) + '</body></html>'
                )
                st.download_button(
                    "⬇️ 匯出完整圖表報告（HTML）", document,
                    file_name=f"{person}_營養報表_{report_start}_{report_end}.html",
                    mime="text/html", use_container_width=True, key=f"export_report_{person}"
                )
                st.download_button(
                    "⬇️ 匯出明細（CSV）", table.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"{person}_營養明細_{report_start}_{report_end}.csv",
                    mime="text/csv", use_container_width=True, key=f"export_csv_{person}"
                )
                st.caption("淨熱量＝飲食熱量－運動消耗。圖中營養素依碳水/蛋白質每克 4 kcal、脂肪每克 9 kcal 換算，與食物標示總熱量可能略有差異。")
