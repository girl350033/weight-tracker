import streamlit as st
import pandas as pd
import json
import base64
from datetime import date, datetime

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

st.markdown(
    """
    <style>
    html, body, [class*="st-"] {
        font-size: 17px !important;
    }

    h1 {
        font-size: 25px !important;
        font-weight: 800 !important;
    }

    h2, h3 {
        font-size: 20px !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    button[data-baseweb="tab"] {
        font-size: 16px !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        width: 100%;
        border-radius: 10px;
    }

    [data-testid="stDataFrame"] {
        font-size: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


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

    return create_client(
        supabase_url,
        supabase_key
    )


supabase = get_supabase()


# =========================================================
# OpenAI
# =========================================================

@st.cache_resource
def get_openai_client():
    api_key = st.secrets.get(
        "OPENAI_API_KEY",
        ""
    )

    if not api_key:
        return None

    return OpenAI(
        api_key=api_key
    )


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


def calculate_exercise_calories(
    weight_kg,
    met,
    minutes
):
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

    score = (
        100
        - (
            abs(actual - target)
            / target
            * 100
        )
    )

    return max(
        0,
        min(
            100,
            score
        )
    )


def calculate_diet_adherence(
    actual_cal,
    actual_carbs,
    actual_protein,
    actual_fat,
    target_cal,
    target_carbs,
    target_protein,
    target_fat
):
    scores = [
        target_score(
            actual_cal,
            target_cal
        ),
        target_score(
            actual_carbs,
            target_carbs
        ),
        target_score(
            actual_protein,
            target_protein
        ),
        target_score(
            actual_fat,
            target_fat
        )
    ]

    return round(
        sum(scores)
        / len(scores)
    )


# =========================================================
# 每日紀錄
# =========================================================

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

        return pd.DataFrame(
            response.data or []
        )

    except Exception as e:
        st.error(
            f"讀取每日紀錄失敗：{e}"
        )
        return pd.DataFrame()


def get_daily_record(
    person,
    selected_date
):
    try:
        response = (
            supabase
            .table("daily_logs")
            .select("*")
            .eq("person", person)
            .eq(
                "date",
                str(selected_date)
            )
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    except Exception as e:
        st.error(
            f"讀取紀錄失敗：{e}"
        )
        return None


def save_daily_record(
    person,
    record_date,
    weight,
    measure_time,
    ex_name,
    ex_cal,
    foods
):
    total_cal = sum(
        safe_float(
            f.get(
                "calories",
                0
            )
        )
        for f in foods
    )

    total_pro = sum(
        safe_float(
            f.get(
                "protein",
                0
            )
        )
        for f in foods
    )

    total_fat = sum(
        safe_float(
            f.get(
                "fat",
                0
            )
        )
        for f in foods
    )

    total_carb = sum(
        safe_float(
            f.get(
                "carbs",
                0
            )
        )
        for f in foods
    )

    payload = {
        "person": person,
        "date": str(
            record_date
        ),
        "weight": round(
            float(weight),
            2
        ),
        "measure_time":
        measure_time or "",
        "ex_name":
        ex_name or "",
        "ex_cal":
        safe_int(
            ex_cal
        ),
        "items_json":
        foods,
        "total_calories":
        safe_int(
            total_cal
        ),
        "total_protein":
        round(
            total_pro,
            1
        ),
        "total_fat":
        round(
            total_fat,
            1
        ),
        "total_carbs":
        round(
            total_carb,
            1
        )
    }

    existing = get_daily_record(
        person,
        record_date
    )

    try:
        if existing:
            (
                supabase
                .table(
                    "daily_logs"
                )
                .update(
                    payload
                )
                .eq(
                    "id",
                    existing[
                        "id"
                    ]
                )
                .execute()
            )
        else:
            (
                supabase
                .table(
                    "daily_logs"
                )
                .insert(
                    payload
                )
                .execute()
            )

        return True

    except Exception as e:
        st.error(
            f"儲存失敗：{e}"
        )
        return False


def delete_daily_record(
    record_id
):
    try:
        (
            supabase
            .table(
                "daily_logs"
            )
            .delete()
            .eq(
                "id",
                record_id
            )
            .execute()
        )

        return True

    except Exception as e:
        st.error(
            f"刪除失敗：{e}"
        )
        return False


# =========================================================
# 飲食目標
# =========================================================

def get_nutrition_targets(
    person
):
    try:
        response = (
            supabase
            .table(
                "nutrition_targets"
            )
            .select("*")
            .eq(
                "person",
                person
            )
            .order(
                "effective_date"
            )
            .execute()
        )

        return pd.DataFrame(
            response.data or []
        )

    except Exception as e:
        st.error(
            f"讀取飲食目標失敗：{e}"
        )
        return pd.DataFrame()


def get_target_for_date(
    person,
    selected_date
):
    """
    找出 selected_date 當天適用的最新目標
    """

    try:
        response = (
            supabase
            .table(
                "nutrition_targets"
            )
            .select("*")
            .eq(
                "person",
                person
            )
            .lte(
                "effective_date",
                str(
                    selected_date
                )
            )
            .order(
                "effective_date",
                desc=True
            )
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    except Exception as e:
        st.error(
            f"讀取當日飲食目標失敗：{e}"
        )
        return None


def get_exact_target(
    person,
    effective_date
):
    try:
        response = (
            supabase
            .table(
                "nutrition_targets"
            )
            .select("*")
            .eq(
                "person",
                person
            )
            .eq(
                "effective_date",
                str(
                    effective_date
                )
            )
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    except:
        return None


def save_nutrition_target(
    person,
    effective_date,
    calories,
    carbs,
    protein,
    fat
):
    payload = {
        "person":
        person,
        "effective_date":
        str(
            effective_date
        ),
        "calories":
        safe_float(
            calories
        ),
        "carbs":
        safe_float(
            carbs
        ),
        "protein":
        safe_float(
            protein
        ),
        "fat":
        safe_float(
            fat
        )
    }

    existing = get_exact_target(
        person,
        effective_date
    )

    try:
        if existing:
            (
                supabase
                .table(
                    "nutrition_targets"
                )
                .update(
                    payload
                )
                .eq(
                    "id",
                    existing[
                        "id"
                    ]
                )
                .execute()
            )
        else:
            (
                supabase
                .table(
                    "nutrition_targets"
                )
                .insert(
                    payload
                )
                .execute()
            )

        return True

    except Exception as e:
        st.error(
            f"飲食目標儲存失敗：{e}"
        )
        return False


def delete_nutrition_target(
    target_id
):
    try:
        (
            supabase
            .table(
                "nutrition_targets"
            )
            .delete()
            .eq(
                "id",
                target_id
            )
            .execute()
        )

        return True

    except Exception as e:
        st.error(
            f"刪除飲食目標失敗：{e}"
        )
        return False


# =========================================================
# InBody
# =========================================================

def get_inbody_logs(
    person
):
    try:
        response = (
            supabase
            .table(
                "inbody_logs"
            )
            .select("*")
            .eq(
                "person",
                person
            )
            .order(
                "date"
            )
            .execute()
        )

        return pd.DataFrame(
            response.data or []
        )

    except Exception as e:
        st.error(
            f"讀取 InBody 失敗：{e}"
        )
        return pd.DataFrame()


def get_inbody_record(
    person,
    selected_date
):
    try:
        response = (
            supabase
            .table(
                "inbody_logs"
            )
            .select("*")
            .eq(
                "person",
                person
            )
            .eq(
                "date",
                str(
                    selected_date
                )
            )
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    except Exception as e:
        st.error(
            f"讀取 InBody 紀錄失敗：{e}"
        )
        return None


def save_inbody_record(
    person,
    record_date,
    weight,
    body_fat,
    muscle,
    bmr
):
    payload = {
        "person":
        person,
        "date":
        str(
            record_date
        ),
        "weight":
        round(
            float(
                weight
            ),
            2
        ),
        "body_fat":
        round(
            float(
                body_fat
            ),
            2
        ),
        "muscle":
        round(
            float(
                muscle
            ),
            2
        ),
        "bmr":
        safe_int(
            bmr
        )
    }

    existing = get_inbody_record(
        person,
        record_date
    )

    try:
        if existing:
            (
                supabase
                .table(
                    "inbody_logs"
                )
                .update(
                    payload
                )
                .eq(
                    "id",
                    existing[
                        "id"
                    ]
                )
                .execute()
            )
        else:
            (
                supabase
                .table(
                    "inbody_logs"
                )
                .insert(
                    payload
                )
                .execute()
            )

        return True

    except Exception as e:
        st.error(
            f"InBody 儲存失敗：{e}"
        )
        return False


def delete_inbody_record(
    record_id
):
    try:
        (
            supabase
            .table(
                "inbody_logs"
            )
            .delete()
            .eq(
                "id",
                record_id
            )
            .execute()
        )

        return True

    except Exception as e:
        st.error(
            f"InBody 刪除失敗：{e}"
        )
        return False


# =========================================================
# Session State
# =========================================================

if "current_foods" not in st.session_state:
    st.session_state.current_foods = []

if "loaded_food_key" not in st.session_state:
    st.session_state.loaded_food_key = ""

if "ai_exercise" not in st.session_state:
    st.session_state.ai_exercise = None


# =========================================================
# 標題
# =========================================================

st.title(
    "健康與體態追蹤系統"
)

person = st.radio(
    "選擇使用者",
    [
        "Shing",
        "Gloria"
    ],
    horizontal=True,
    label_visibility="collapsed"
)


tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "紀錄",
        "趨勢",
        "歷史紀錄",
        "飲食目標",
        "InBody"
    ]
)


# =========================================================
# TAB 1 每日紀錄
# =========================================================

with tab1:

    st.subheader(
        f"每日紀錄｜{person}"
    )

    record_date = st.date_input(
        "日期",
        value=date.today(),
        format="YYYY/MM/DD",
        key="record_date"
    )

    session_key = (
        f"{person}_"
        f"{record_date}"
    )

    old_record = get_daily_record(
        person,
        record_date
    )

    if (
        st.session_state.loaded_food_key
        != session_key
    ):
        if old_record:
            old_items = old_record.get(
                "items_json",
                []
            )

            if isinstance(
                old_items,
                str
            ):
                try:
                    old_items = json.loads(
                        old_items
                    )
                except:
                    old_items = []

            st.session_state.current_foods = (
                old_items
                or []
            )

        else:
            st.session_state.current_foods = []

        st.session_state.loaded_food_key = (
            session_key
        )

        st.session_state.ai_exercise = None


    # =====================================================
    # 體重 / 時間
    # =====================================================

    default_weight = (
        safe_float(
            old_record.get(
                "weight"
            ),
            60
        )
        if old_record
        else 60.0
    )

    weight = st.number_input(
        "體重 (kg)",
        min_value=30.0,
        max_value=200.0,
        value=float(
            default_weight
        ),
        step=0.1,
        format="%.1f"
    )

    default_measure_time = (
        old_record.get(
            "measure_time",
            ""
        )
        if old_record
        else ""
    )

    measure_time = st.text_input(
        "測量時間",
        value=(
            default_measure_time
            or ""
        ),
        placeholder="例如：09:00"
    )


    # =====================================================
    # 當日目標
    # =====================================================

    current_target = get_target_for_date(
        person,
        record_date
    )

    if current_target:
        st.info(
            "🎯 當日飲食目標："
            f"{safe_int(current_target['calories'])} kcal｜"
            f"碳水 {safe_float(current_target['carbs']):.0f}g｜"
            f"蛋白質 {safe_float(current_target['protein']):.0f}g｜"
            f"脂肪 {safe_float(current_target['fat']):.0f}g"
        )

    else:
        st.warning(
            "目前尚未設定這一天適用的飲食目標。"
        )


    # =====================================================
    # 飲食紀錄
    # =====================================================

    st.markdown("---")
    st.subheader(
        "🍱 飲食紀錄"
    )


    # =====================================================
    # AI文字輸入
    # =====================================================

    st.write(
        "### ✍️ 文字快速輸入"
    )

    food_text = st.text_area(
        "輸入食物與份量",
        placeholder=(
            "例如：\n"
            "茶葉蛋兩顆\n"
            "無糖豆漿400ml\n"
            "雞胸肉150g"
        ),
        height=110,
        key=(
            f"food_text_"
            f"{session_key}"
        )
    )

    if st.button(
        "✨ AI 分析文字食物",
        use_container_width=True,
        key=(
            f"food_text_ai_"
            f"{session_key}"
        )
    ):
        if not food_text.strip():
            st.warning(
                "請先輸入食物"
            )

        else:
            client = get_openai_client()

            if client is None:
                st.error(
                    "尚未設定 OPENAI_API_KEY"
                )

            else:
                with st.spinner(
                    "AI 正在分析營養素..."
                ):
                    try:
                        response = (
                            client
                            .chat
                            .completions
                            .create(
                                model="gpt-4o",
                                messages=[
                                    {
                                        "role":
                                        "system",
                                        "content":
                                        """
你是一個飲食營養分析助手。

根據使用者提供的食物名稱與份量，
估算每一項食物的：

食物名稱
份量
熱量 kcal
蛋白質 g
脂肪 g
碳水化合物 g

如果一次輸入多種食物，
拆成多個 items。

如果份量不明確，
使用合理常見份量估算。

只回傳 JSON。

格式：

{
  "items": [
    {
      "name": "茶葉蛋",
      "portion": "2顆",
      "calories": 150,
      "protein": 13,
      "fat": 10,
      "carbs": 3
    }
  ]
}
"""
                                    },
                                    {
                                        "role":
                                        "user",
                                        "content":
                                        food_text
                                    }
                                ],
                                max_tokens=700
                            )
                        )

                        res = (
                            response
                            .choices[0]
                            .message
                            .content
                        )

                        parsed = clean_ai_json(
                            res
                        )

                        new_items = parsed.get(
                            "items",
                            []
                        )

                        if new_items:
                            (
                                st.session_state
                                .current_foods
                                .extend(
                                    new_items
                                )
                            )

                            st.success(
                                f"已加入 {len(new_items)} 項食物"
                            )

                            st.rerun()

                        else:
                            st.warning(
                                "AI 沒有辨識到食物"
                            )

                    except Exception as e:
                        st.error(
                            f"文字辨識失敗：{e}"
                        )


    # =====================================================
    # AI照片辨識
    # =====================================================

    st.markdown("---")
    st.write(
        "### 📷 拍照辨識"
    )

    uploaded_file = st.file_uploader(
        "拍照或選擇餐點照片",
        type=[
            "jpg",
            "jpeg",
            "png"
        ],
        key=(
            f"food_photo_"
            f"{session_key}"
        )
    )

    if (
        uploaded_file
        and st.button(
            "✨ 開始 AI 辨識",
            use_container_width=True,
            key=(
                f"photo_ai_btn_"
                f"{session_key}"
            )
        )
    ):
        client = get_openai_client()

        if client is None:
            st.error(
                "尚未設定 OPENAI_API_KEY"
            )

        else:
            with st.spinner(
                "AI 正在辨識餐點..."
            ):
                try:
                    bytes_data = (
                        uploaded_file
                        .getvalue()
                    )

                    base64_image = (
                        base64
                        .b64encode(
                            bytes_data
                        )
                        .decode(
                            "utf-8"
                        )
                    )

                    response = (
                        client
                        .chat
                        .completions
                        .create(
                            model="gpt-4o",
                            messages=[
                                {
                                    "role":
                                    "user",
                                    "content":
                                    [
                                        {
                                            "type":
                                            "text",
                                            "text":
                                            """
請辨識照片中的食物。

估計每項食物：
名稱
份量
熱量 kcal
蛋白質 g
脂肪 g
碳水化合物 g

如果有多項食物，
拆成多個 items。

只回傳 JSON。

格式：
{
  "items": [
    {
      "name": "雞胸肉",
      "portion": "100g",
      "calories": 165,
      "protein": 31,
      "fat": 3.6,
      "carbs": 0
    }
  ]
}
"""
                                        },
                                        {
                                            "type":
                                            "image_url",
                                            "image_url":
                                            {
                                                "url":
                                                f"data:image/jpeg;base64,{base64_image}"
                                            }
                                        }
                                    ]
                                }
                            ],
                            max_tokens=700
                        )
                    )

                    res = (
                        response
                        .choices[0]
                        .message
                        .content
                    )

                    parsed = clean_ai_json(
                        res
                    )

                    new_items = parsed.get(
                        "items",
                        []
                    )

                    if new_items:
                        (
                            st.session_state
                            .current_foods
                            .extend(
                                new_items
                            )
                        )

                        st.success(
                            f"辨識完成，已加入 {len(new_items)} 項"
                        )

                        st.rerun()

                    else:
                        st.warning(
                            "AI 沒有辨識到食物"
                        )

                except Exception as e:
                    st.error(
                        f"AI 辨識失敗：{e}"
                    )


    # =====================================================
    # 手動新增
    # =====================================================

    with st.expander(
        "➕ 手動新增食物"
    ):
        m_name = st.text_input(
            "食物名稱",
            key=(
                f"m_name_"
                f"{session_key}"
            )
        )

        m_portion = st.text_input(
            "份量",
            placeholder="例如：100g、1碗、2顆",
            key=(
                f"m_portion_"
                f"{session_key}"
            )
        )

        m_cal = st.number_input(
            "熱量 kcal",
            min_value=0,
            value=0,
            step=10,
            key=(
                f"m_cal_"
                f"{session_key}"
            )
        )

        m_pro = st.number_input(
            "蛋白質 g",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key=(
                f"m_pro_"
                f"{session_key}"
            )
        )

        m_fat = st.number_input(
            "脂肪 g",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key=(
                f"m_fat_"
                f"{session_key}"
            )
        )

        m_carb = st.number_input(
            "碳水化合物 g",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key=(
                f"m_carb_"
                f"{session_key}"
            )
        )

        if st.button(
            "加入食物",
            key=(
                f"manual_food_"
                f"{session_key}"
            )
        ):
            (
                st.session_state
                .current_foods
                .append(
                    {
                        "name":
                        m_name
                        if m_name
                        else "自訂食物",
                        "portion":
                        m_portion,
                        "calories":
                        safe_int(
                            m_cal
                        ),
                        "protein":
                        safe_float(
                            m_pro
                        ),
                        "fat":
                        safe_float(
                            m_fat
                        ),
                        "carbs":
                        safe_float(
                            m_carb
                        )
                    }
                )
            )

            st.rerun()


    # =====================================================
    # 當日食物
    # =====================================================

    if st.session_state.current_foods:

        st.markdown("---")
        st.write(
            "### 當日食物"
        )

        food_df = pd.DataFrame(
            st.session_state.current_foods
        )

        required_cols = [
            "name",
            "portion",
            "calories",
            "protein",
            "fat",
            "carbs"
        ]

        for col in required_cols:
            if col not in food_df.columns:
                if col in [
                    "name",
                    "portion"
                ]:
                    food_df[col] = ""
                else:
                    food_df[col] = 0

        food_df = food_df[
            required_cols
        ]

        edited_food_df = st.data_editor(
            food_df,
            hide_index=True,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "name":
                st.column_config.TextColumn(
                    "食物"
                ),
                "portion":
                st.column_config.TextColumn(
                    "份量"
                ),
                "calories":
                st.column_config.NumberColumn(
                    "熱量",
                    format="%d kcal"
                ),
                "protein":
                st.column_config.NumberColumn(
                    "蛋白質",
                    format="%.1f g"
                ),
                "fat":
                st.column_config.NumberColumn(
                    "脂肪",
                    format="%.1f g"
                ),
                "carbs":
                st.column_config.NumberColumn(
                    "碳水",
                    format="%.1f g"
                )
            },
            key=(
                f"food_editor_"
                f"{session_key}"
            )
        )

        cleaned_foods = []

        for item in (
            edited_food_df
            .to_dict(
                "records"
            )
        ):
            cleaned_foods.append(
                {
                    "name":
                    str(
                        item.get(
                            "name",
                            ""
                        )
                    ),
                    "portion":
                    str(
                        item.get(
                            "portion",
                            ""
                        )
                    ),
                    "calories":
                    safe_int(
                        item.get(
                            "calories",
                            0
                        )
                    ),
                    "protein":
                    safe_float(
                        item.get(
                            "protein",
                            0
                        )
                    ),
                    "fat":
                    safe_float(
                        item.get(
                            "fat",
                            0
                        )
                    ),
                    "carbs":
                    safe_float(
                        item.get(
                            "carbs",
                            0
                        )
                    )
                }
            )

        st.session_state.current_foods = (
            cleaned_foods
        )

        total_cal = sum(
            x["calories"]
            for x in cleaned_foods
        )

        total_pro = sum(
            x["protein"]
            for x in cleaned_foods
        )

        total_fat = sum(
            x["fat"]
            for x in cleaned_foods
        )

        total_carb = sum(
            x["carbs"]
            for x in cleaned_foods
        )


        # =================================================
        # 今日營養
        # =================================================

        st.write(
            "### 今日營養"
        )

        if current_target:

            adherence = (
                calculate_diet_adherence(
                    total_cal,
                    total_carb,
                    total_pro,
                    total_fat,
                    current_target[
                        "calories"
                    ],
                    current_target[
                        "carbs"
                    ],
                    current_target[
                        "protein"
                    ],
                    current_target[
                        "fat"
                    ]
                )
            )

            st.metric(
                "🎯 飲食執行率",
                f"{adherence}%"
            )

            st.write(
                f"熱量：{total_cal:.0f} / "
                f"{safe_float(current_target['calories']):.0f} kcal"
            )

            st.write(
                f"碳水：{total_carb:.1f} / "
                f"{safe_float(current_target['carbs']):.0f} g"
            )

            st.write(
                f"蛋白質：{total_pro:.1f} / "
                f"{safe_float(current_target['protein']):.0f} g"
            )

            st.write(
                f"脂肪：{total_fat:.1f} / "
                f"{safe_float(current_target['fat']):.0f} g"
            )

        else:
            adherence = None

            c1, c2 = st.columns(
                2
            )

            with c1:
                st.metric(
                    "總熱量",
                    f"{total_cal:.0f} kcal"
                )

                st.metric(
                    "蛋白質",
                    f"{total_pro:.1f} g"
                )

            with c2:
                st.metric(
                    "脂肪",
                    f"{total_fat:.1f} g"
                )

                st.metric(
                    "碳水",
                    f"{total_carb:.1f} g"
                )


        # =================================================
        # 營養素圓餅圖
        # =================================================

        protein_kcal = (
            total_pro
            * 4
        )

        fat_kcal = (
            total_fat
            * 9
        )

        carb_kcal = (
            total_carb
            * 4
        )

        macro_total = (
            protein_kcal
            + fat_kcal
            + carb_kcal
        )

        if macro_total > 0:

            st.write(
                "### 三大營養素熱量占比"
            )

            macro_df = pd.DataFrame(
                {
                    "營養素":
                    [
                        "蛋白質",
                        "脂肪",
                        "碳水"
                    ],
                    "熱量":
                    [
                        protein_kcal,
                        fat_kcal,
                        carb_kcal
                    ]
                }
            )

            fig = px.pie(
                macro_df,
                names="營養素",
                values="熱量",
                hole=0.45
            )

            fig.update_traces(
                textposition="inside",
                textinfo=(
                    "percent+label"
                )
            )

            fig.update_layout(
                height=350,
                margin=dict(
                    l=10,
                    r=10,
                    t=10,
                    b=10
                ),
                legend=dict(
                    orientation="h",
                    y=-0.08
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "displayModeBar":
                    False
                },
                key=(
                    f"daily_macro_chart_"
                    f"{person}_"
                    f"{record_date}"
                )
            )

        if st.button(
            "清空當日食物",
            key=(
                f"clear_food_"
                f"{session_key}"
            )
        ):
            st.session_state.current_foods = []

            st.rerun()

    else:
        st.info(
            "這一天尚未加入食物"
        )


    # =====================================================
    # 運動
    # =====================================================

    st.markdown("---")
    st.subheader(
        "🏃 運動紀錄"
    )

    st.caption(
        f"目前使用體重："
        f"{weight:.1f} kg"
    )

    exercise_text = st.text_input(
        "輸入運動",
        placeholder=(
            "例如：慢跑20分鐘、"
            "快走40分鐘、重訓60分鐘、休息日"
        ),
        key=(
            f"exercise_text_"
            f"{session_key}"
        )
    )

    if st.button(
        "✨ AI 計算運動消耗",
        use_container_width=True,
        key=(
            f"exercise_ai_"
            f"{session_key}"
        )
    ):
        if not exercise_text.strip():
            st.warning(
                "請先輸入運動內容"
            )

        elif (
            exercise_text.strip()
            in [
                "休息日",
                "休息",
                "rest",
                "Rest"
            ]
        ):
            st.session_state.ai_exercise = {
                "name":
                "休息日",
                "minutes":
                0,
                "met":
                0,
                "intensity":
                "休息",
                "calories":
                0
            }

            st.rerun()

        else:
            client = get_openai_client()

            if client is None:
                st.error(
                    "尚未設定 OPENAI_API_KEY"
                )

            else:
                with st.spinner(
                    "AI 正在分析運動..."
                ):
                    try:
                        response = (
                            client
                            .chat
                            .completions
                            .create(
                                model="gpt-4o",
                                messages=[
                                    {
                                        "role":
                                        "system",
                                        "content":
                                        """
你是一個運動紀錄分析助手。

請從使用者輸入中判斷：

1. 運動名稱
2. 運動時間，單位分鐘
3. 運動強度
4. 合理 MET 值

如果資訊不完整，
使用一般合理強度估算。

只回傳 JSON：

{
  "exercise_name": "慢跑",
  "minutes": 20,
  "intensity": "一般",
  "met": 7.5
}

不要自己計算卡路里。
"""
                                    },
                                    {
                                        "role":
                                        "user",
                                        "content":
                                        exercise_text
                                    }
                                ],
                                max_tokens=300
                            )
                        )

                        res = (
                            response
                            .choices[0]
                            .message
                            .content
                        )

                        parsed = clean_ai_json(
                            res
                        )

                        ex_ai_name = parsed.get(
                            "exercise_name",
                            exercise_text
                        )

                        ex_ai_minutes = safe_float(
                            parsed.get(
                                "minutes",
                                0
                            )
                        )

                        ex_ai_met = safe_float(
                            parsed.get(
                                "met",
                                0
                            )
                        )

                        ex_ai_intensity = parsed.get(
                            "intensity",
                            ""
                        )

                        estimated_cal = (
                            calculate_exercise_calories(
                                weight,
                                ex_ai_met,
                                ex_ai_minutes
                            )
                        )

                        st.session_state.ai_exercise = {
                            "name":
                            ex_ai_name,
                            "minutes":
                            ex_ai_minutes,
                            "met":
                            ex_ai_met,
                            "intensity":
                            ex_ai_intensity,
                            "calories":
                            estimated_cal
                        }

                        st.rerun()

                    except Exception as e:
                        st.error(
                            f"運動辨識失敗：{e}"
                        )


    default_ex_name = (
        old_record.get(
            "ex_name",
            ""
        )
        if old_record
        else ""
    )

    default_ex_cal = (
        safe_int(
            old_record.get(
                "ex_cal",
                0
            )
        )
        if old_record
        else 0
    )

    if st.session_state.ai_exercise:

        ai_ex = (
            st.session_state.ai_exercise
        )

        st.success(
            "AI 運動分析完成"
        )

        st.write(
            f"**運動：** "
            f"{ai_ex['name']}"
        )

        if (
            ai_ex["minutes"]
            > 0
        ):
            st.write(
                f"**時間：** "
                f"{ai_ex['minutes']:.0f} 分鐘"
            )

            st.write(
                f"**強度：** "
                f"{ai_ex['intensity']}"
            )

            st.write(
                f"**MET：** "
                f"{ai_ex['met']:.1f}"
            )

        st.metric(
            "🔥 估計消耗",
            f"{ai_ex['calories']} kcal"
        )

        if ai_ex["minutes"] > 0:
            default_ex_name = (
                f"{ai_ex['name']} "
                f"{ai_ex['minutes']:.0f}分鐘"
            )
        else:
            default_ex_name = (
                ai_ex["name"]
            )

        default_ex_cal = (
            ai_ex[
                "calories"
            ]
        )


    ex_name = st.text_input(
        "運動內容",
        value=(
            default_ex_name
            or ""
        ),
        key=(
            f"exercise_final_"
            f"{session_key}"
        )
    )

    ex_cal = st.number_input(
        "運動消耗 kcal",
        min_value=0,
        value=safe_int(
            default_ex_cal
        ),
        step=10,
        key=(
            f"exercise_cal_"
            f"{session_key}"
        )
    )


    # =====================================================
    # 儲存每日紀錄
    # =====================================================

    if st.button(
        (
            "💾 更新這一天紀錄"
            if old_record
            else "💾 儲存這一天紀錄"
        ),
        type="primary",
        key=(
            f"save_daily_"
            f"{session_key}"
        )
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
            st.success(
                "紀錄已永久儲存！"
            )

            st.rerun()


# =========================================================
# TAB 2 趨勢
# =========================================================

with tab2:

    st.subheader(
        "📈 體重趨勢"
    )

    df = get_daily_logs(
        person
    )

    if not df.empty:

        df["date"] = pd.to_datetime(
            df["date"]
        )

        df["weight"] = pd.to_numeric(
            df["weight"],
            errors="coerce"
        )

        df = df.sort_values(
            "date"
        )

        fig_weight = go.Figure()

        fig_weight.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["weight"],
                mode="lines+markers",
                hovertemplate=(
                    "%{x|%m/%d}"
                    "<br>%{y:.1f} kg"
                    "<extra></extra>"
                )
            )
        )

        valid_weight = (
            df["weight"]
            .dropna()
        )

        if not valid_weight.empty:

            min_weight = (
                valid_weight
                .min()
            )

            max_weight = (
                valid_weight
                .max()
            )

            lower = max(
                30,
                min_weight - 2
            )

            upper = (
                max_weight
                + 2
            )

            if (
                upper
                - lower
                < 5
            ):
                upper = (
                    lower
                    + 5
                )

            fig_weight.update_yaxes(
                range=[
                    lower,
                    upper
                ],
                tickformat=".1f",
                title="kg"
            )

        fig_weight.update_xaxes(
            tickformat="%m/%d",
            nticks=6,
            title=""
        )

        fig_weight.update_layout(
            height=320,
            margin=dict(
                l=10,
                r=10,
                t=10,
                b=20
            ),
            showlegend=False
        )

        st.plotly_chart(
            fig_weight,
            use_container_width=True,
            config={
                "displayModeBar":
                False
            },
            key=(
                f"weight_chart_"
                f"{person}"
            )
        )

    else:
        st.info(
            "尚無歷史資料"
        )


# =========================================================
# TAB 3 教練版歷史紀錄
# =========================================================

with tab3:

    st.subheader(
        "📋 教練追蹤紀錄"
    )

    history_df = get_daily_logs(
        person
    )

    if not history_df.empty:

        history_df = (
            history_df
            .sort_values(
                "date",
                ascending=False
            )
        )

        coach_rows = []

        for _, row in (
            history_df
            .iterrows()
        ):

            row_date = (
                pd.to_datetime(
                    row[
                        "date"
                    ]
                )
                .date()
            )

            target = (
                get_target_for_date(
                    person,
                    row_date
                )
            )

            actual_cal = safe_float(
                row.get(
                    "total_calories",
                    0
                )
            )

            actual_carb = safe_float(
                row.get(
                    "total_carbs",
                    0
                )
            )

            actual_pro = safe_float(
                row.get(
                    "total_protein",
                    0
                )
            )

            actual_fat = safe_float(
                row.get(
                    "total_fat",
                    0
                )
            )

            if target:
                adherence = (
                    calculate_diet_adherence(
                        actual_cal,
                        actual_carb,
                        actual_pro,
                        actual_fat,
                        target[
                            "calories"
                        ],
                        target[
                            "carbs"
                        ],
                        target[
                            "protein"
                        ],
                        target[
                            "fat"
                        ]
                    )
                )

                adherence_text = (
                    f"{adherence}%"
                )

            else:
                adherence_text = "-"

            coach_rows.append(
                {
                    "日期":
                    simple_date(
                        row[
                            "date"
                        ]
                    ),
                    "體重":
                    round(
                        safe_float(
                            row.get(
                                "weight",
                                0
                            )
                        ),
                        1
                    ),
                    "幾點測量":
                    row.get(
                        "measure_time",
                        ""
                    )
                    or "",
                    "飲食執行率":
                    adherence_text,
                    "運動內容":
                    row.get(
                        "ex_name",
                        ""
                    )
                    or "",
                    "碳水":
                    round(
                        actual_carb,
                        1
                    ),
                    "蛋白質":
                    round(
                        actual_pro,
                        1
                    ),
                    "脂肪":
                    round(
                        actual_fat,
                        1
                    )
                }
            )

        coach_df = pd.DataFrame(
            coach_rows
        )

        st.dataframe(
            coach_df,
            hide_index=True,
            use_container_width=True
        )


        # =================================================
        # CSV下載
        # =================================================

        csv_data = (
            coach_df
            .to_csv(
                index=False
            )
            .encode(
                "utf-8-sig"
            )
        )

        st.download_button(
            "⬇️ 下載教練版紀錄 CSV",
            data=csv_data,
            file_name=(
                f"{person}_教練追蹤紀錄.csv"
            ),
            mime="text/csv",
            key=(
                f"coach_csv_"
                f"{person}"
            )
        )


        # =================================================
        # 編輯舊紀錄
        # =================================================

        st.markdown("---")
        st.write(
            "### 編輯過往紀錄"
        )

        edit_dates = (
            history_df[
                "date"
            ]
            .tolist()
        )

        selected_edit_date = (
            st.selectbox(
                "選擇日期",
                options=edit_dates,
                format_func=simple_date,
                key=(
                    f"history_edit_"
                    f"{person}"
                )
            )
        )

        selected_history = (
            history_df[
                history_df[
                    "date"
                ]
                == selected_edit_date
            ]
            .iloc[0]
        )

        edit_weight = (
            st.number_input(
                "體重",
                min_value=30.0,
                max_value=200.0,
                value=safe_float(
                    selected_history.get(
                        "weight",
                        60
                    )
                ),
                step=0.1,
                key=(
                    f"edit_weight_"
                    f"{person}_"
                    f"{selected_edit_date}"
                )
            )
        )

        edit_time = st.text_input(
            "測量時間",
            value=(
                selected_history.get(
                    "measure_time",
                    ""
                )
                or ""
            ),
            key=(
                f"edit_time_"
                f"{person}_"
                f"{selected_edit_date}"
            )
        )

        edit_ex_name = (
            st.text_input(
                "運動內容",
                value=(
                    selected_history.get(
                        "ex_name",
                        ""
                    )
                    or ""
                ),
                key=(
                    f"edit_ex_"
                    f"{person}_"
                    f"{selected_edit_date}"
                )
            )
        )

        edit_ex_cal = (
            st.number_input(
                "運動消耗",
                min_value=0,
                value=safe_int(
                    selected_history.get(
                        "ex_cal",
                        0
                    )
                ),
                step=10,
                key=(
                    f"edit_ex_cal_"
                    f"{person}_"
                    f"{selected_edit_date}"
                )
            )
        )

        raw_items = (
            selected_history.get(
                "items_json",
                []
            )
        )

        if isinstance(
            raw_items,
            str
        ):
            try:
                raw_items = json.loads(
                    raw_items
                )
            except:
                raw_items = []

        edit_food_df = pd.DataFrame(
            raw_items
        )

        for col in [
            "name",
            "portion",
            "calories",
            "protein",
            "fat",
            "carbs"
        ]:
            if col not in edit_food_df.columns:
                edit_food_df[col] = (
                    ""
                    if col
                    in [
                        "name",
                        "portion"
                    ]
                    else 0
                )

        edit_food_df = (
            edit_food_df[
                [
                    "name",
                    "portion",
                    "calories",
                    "protein",
                    "fat",
                    "carbs"
                ]
            ]
        )

        edited_history_foods = (
            st.data_editor(
                edit_food_df,
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True,
                key=(
                    f"history_food_editor_"
                    f"{person}_"
                    f"{selected_edit_date}"
                )
            )
        )

        col1, col2 = st.columns(
            2
        )

        with col1:
            if st.button(
                "💾 儲存修改",
                type="primary",
                key=(
                    f"update_history_"
                    f"{person}_"
                    f"{selected_edit_date}"
                )
            ):

                foods = []

                for item in (
                    edited_history_foods
                    .to_dict(
                        "records"
                    )
                ):
                    foods.append(
                        {
                            "name":
                            str(
                                item.get(
                                    "name",
                                    ""
                                )
                            ),
                            "portion":
                            str(
                                item.get(
                                    "portion",
                                    ""
                                )
                            ),
                            "calories":
                            safe_int(
                                item.get(
                                    "calories",
                                    0
                                )
                            ),
                            "protein":
                            safe_float(
                                item.get(
                                    "protein",
                                    0
                                )
                            ),
                            "fat":
                            safe_float(
                                item.get(
                                    "fat",
                                    0
                                )
                            ),
                            "carbs":
                            safe_float(
                                item.get(
                                    "carbs",
                                    0
                                )
                            )
                        }
                    )

                success = (
                    save_daily_record(
                        person,
                        selected_edit_date,
                        edit_weight,
                        edit_time,
                        edit_ex_name,
                        edit_ex_cal,
                        foods
                    )
                )

                if success:
                    st.success(
                        "修改完成"
                    )

                    st.rerun()

        with col2:
            if st.button(
                "🗑️ 刪除這筆",
                key=(
                    f"delete_history_"
                    f"{person}_"
                    f"{selected_edit_date}"
                )
            ):
                success = (
                    delete_daily_record(
                        selected_history[
                            "id"
                        ]
                    )
                )

                if success:
                    st.success(
                        "已刪除"
                    )

                    st.rerun()

    else:
        st.info(
            "尚無歷史紀錄"
        )


# =========================================================
# TAB 4 飲食目標
# =========================================================

with tab4:

    st.subheader(
        f"🎯 飲食目標｜{person}"
    )

    st.caption(
        "教練調整飲食目標時新增一筆即可。"
        "系統會依生效日期，自動套用到之後的每日紀錄。"
    )

    target_date = st.date_input(
        "生效日期",
        value=date.today(),
        format="YYYY/MM/DD",
        key=(
            f"target_date_"
            f"{person}"
        )
    )

    existing_target = (
        get_exact_target(
            person,
            target_date
        )
    )

    default_target_cal = (
        safe_float(
            existing_target.get(
                "calories",
                2400
            )
        )
        if existing_target
        else (
            2400
            if person
            == "Shing"
            else 1800
        )
    )

    default_target_carbs = (
        safe_float(
            existing_target.get(
                "carbs",
                280
            )
        )
        if existing_target
        else (
            280
            if person
            == "Shing"
            else 200
        )
    )

    default_target_protein = (
        safe_float(
            existing_target.get(
                "protein",
                170
            )
        )
        if existing_target
        else (
            170
            if person
            == "Shing"
            else 120
        )
    )

    default_target_fat = (
        safe_float(
            existing_target.get(
                "fat",
                60
            )
        )
        if existing_target
        else (
            60
            if person
            == "Shing"
            else 50
        )
    )

    target_calories = st.number_input(
        "每日熱量 kcal",
        min_value=0,
        value=int(
            default_target_cal
        ),
        step=50,
        key=(
            f"target_cal_"
            f"{person}_"
            f"{target_date}"
        )
    )

    target_carbs = st.number_input(
        "碳水 g",
        min_value=0.0,
        value=float(
            default_target_carbs
        ),
        step=5.0,
        key=(
            f"target_carbs_"
            f"{person}_"
            f"{target_date}"
        )
    )

    target_protein = st.number_input(
        "蛋白質 g",
        min_value=0.0,
        value=float(
            default_target_protein
        ),
        step=5.0,
        key=(
            f"target_protein_"
            f"{person}_"
            f"{target_date}"
        )
    )

    target_fat = st.number_input(
        "脂肪 g",
        min_value=0.0,
        value=float(
            default_target_fat
        ),
        step=5.0,
        key=(
            f"target_fat_"
            f"{person}_"
            f"{target_date}"
        )
    )

    if st.button(
        (
            "💾 更新飲食目標"
            if existing_target
            else "💾 新增飲食目標"
        ),
        type="primary",
        key=(
            f"save_target_"
            f"{person}_"
            f"{target_date}"
        )
    ):

        success = (
            save_nutrition_target(
                person,
                target_date,
                target_calories,
                target_carbs,
                target_protein,
                target_fat
            )
        )

        if success:
            st.success(
                "飲食目標已儲存！"
            )

            st.rerun()


    # =====================================================
    # 目標歷史
    # =====================================================

    targets_df = (
        get_nutrition_targets(
            person
        )
    )

    if not targets_df.empty:

        st.markdown("---")
        st.write(
            "### 飲食目標歷史"
        )

        targets_show = (
            targets_df
            .sort_values(
                "effective_date",
                ascending=False
            )
            .copy()
        )

        targets_show[
            "生效日期"
        ] = (
            targets_show[
                "effective_date"
            ]
            .apply(
                simple_date
            )
        )

        targets_show[
            "熱量"
        ] = (
            pd.to_numeric(
                targets_show[
                    "calories"
                ],
                errors="coerce"
            )
            .round(0)
            .astype(int)
        )

        targets_show[
            "碳水"
        ] = pd.to_numeric(
            targets_show[
                "carbs"
            ],
            errors="coerce"
        )

        targets_show[
            "蛋白質"
        ] = pd.to_numeric(
            targets_show[
                "protein"
            ],
            errors="coerce"
        )

        targets_show[
            "脂肪"
        ] = pd.to_numeric(
            targets_show[
                "fat"
            ],
            errors="coerce"
        )

        st.dataframe(
            targets_show[
                [
                    "生效日期",
                    "熱量",
                    "碳水",
                    "蛋白質",
                    "脂肪"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )

        delete_target_date = (
            st.selectbox(
                "刪除某一筆目標",
                options=(
                    targets_df[
                        "effective_date"
                    ]
                    .tolist()
                ),
                format_func=simple_date,
                key=(
                    f"delete_target_date_"
                    f"{person}"
                )
            )
        )

        selected_target_delete = (
            targets_df[
                targets_df[
                    "effective_date"
                ]
                == delete_target_date
            ]
            .iloc[0]
        )

        if st.button(
            "🗑️ 刪除這筆目標",
            key=(
                f"delete_target_"
                f"{person}_"
                f"{delete_target_date}"
            )
        ):
            success = (
                delete_nutrition_target(
                    selected_target_delete[
                        "id"
                    ]
                )
            )

            if success:
                st.success(
                    "飲食目標已刪除"
                )

                st.rerun()

    else:
        st.info(
            "尚未設定任何飲食目標"
        )


# =========================================================
# TAB 5 InBody
# =========================================================

with tab5:

    st.subheader(
        f"InBody｜{person}"
    )

    ib_date = st.date_input(
        "測量日期",
        value=date.today(),
        format="YYYY/MM/DD",
        key=(
            f"ib_date_"
            f"{person}"
        )
    )

    old_ib = get_inbody_record(
        person,
        ib_date
    )

    ib_weight = st.number_input(
        "InBody 體重 (kg)",
        min_value=30.0,
        max_value=200.0,
        value=(
            safe_float(
                old_ib.get(
                    "weight",
                    60
                )
            )
            if old_ib
            else 60.0
        ),
        step=0.1,
        key=(
            f"ib_weight_"
            f"{person}_"
            f"{ib_date}"
        )
    )

    ib_body_fat = st.number_input(
        "體脂率 (%)",
        min_value=1.0,
        max_value=70.0,
        value=(
            safe_float(
                old_ib.get(
                    "body_fat",
                    20
                )
            )
            if old_ib
            else 20.0
        ),
        step=0.1,
        key=(
            f"ib_bodyfat_"
            f"{person}_"
            f"{ib_date}"
        )
    )

    ib_muscle = st.number_input(
        "骨骼肌 (kg)",
        min_value=1.0,
        max_value=100.0,
        value=(
            safe_float(
                old_ib.get(
                    "muscle",
                    25
                )
            )
            if old_ib
            else 25.0
        ),
        step=0.1,
        key=(
            f"ib_muscle_"
            f"{person}_"
            f"{ib_date}"
        )
    )

    ib_bmr = st.number_input(
        "BMR (kcal)",
        min_value=500,
        max_value=5000,
        value=(
            safe_int(
                old_ib.get(
                    "bmr",
                    1400
                )
            )
            if old_ib
            else 1400
        ),
        step=10,
        key=(
            f"ib_bmr_"
            f"{person}_"
            f"{ib_date}"
        )
    )

    if st.button(
        (
            "💾 更新 InBody"
            if old_ib
            else "💾 儲存 InBody"
        ),
        type="primary",
        key=(
            f"save_ib_"
            f"{person}_"
            f"{ib_date}"
        )
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
            st.success(
                "InBody 已永久儲存！"
            )

            st.rerun()


    ib_df = get_inbody_logs(
        person
    )

    if not ib_df.empty:

        ib_df[
            "date"
        ] = pd.to_datetime(
            ib_df[
                "date"
            ]
        )

        ib_df = ib_df.sort_values(
            "date"
        )

        st.markdown("---")
        st.write(
            "### InBody 體重趨勢"
        )

        fig_ib = go.Figure()

        fig_ib.add_trace(
            go.Scatter(
                x=ib_df[
                    "date"
                ],
                y=pd.to_numeric(
                    ib_df[
                        "weight"
                    ],
                    errors="coerce"
                ),
                mode="lines+markers",
                hovertemplate=(
                    "%{x|%m/%d}"
                    "<br>%{y:.1f} kg"
                    "<extra></extra>"
                )
            )
        )

        fig_ib.update_xaxes(
            tickformat="%m/%d",
            nticks=6
        )

        fig_ib.update_yaxes(
            tickformat=".1f"
        )

        fig_ib.update_layout(
            height=300,
            margin=dict(
                l=10,
                r=10,
                t=10,
                b=20
            ),
            showlegend=False
        )

        st.plotly_chart(
            fig_ib,
            use_container_width=True,
            config={
                "displayModeBar":
                False
            },
            key=(
                f"inbody_chart_"
                f"{person}"
            )
        )

        show_ib = ib_df.copy()

        show_ib[
            "日期"
        ] = (
            show_ib[
                "date"
            ]
            .apply(
                simple_date
            )
        )

        show_ib[
            "體重"
        ] = (
            pd.to_numeric(
                show_ib[
                    "weight"
                ],
                errors="coerce"
            )
            .round(1)
        )

        show_ib[
            "體脂率"
        ] = (
            pd.to_numeric(
                show_ib[
                    "body_fat"
                ],
                errors="coerce"
            )
            .round(1)
        )

        show_ib[
            "骨骼肌"
        ] = (
            pd.to_numeric(
                show_ib[
                    "muscle"
                ],
                errors="coerce"
            )
            .round(1)
        )

        show_ib[
            "BMR"
        ] = (
            pd.to_numeric(
                show_ib[
                    "bmr"
                ],
                errors="coerce"
            )
            .fillna(0)
            .astype(int)
        )

        st.dataframe(
            show_ib[
                [
                    "日期",
                    "體重",
                    "體脂率",
                    "骨骼肌",
                    "BMR"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )

    else:
        st.info(
            "尚無 InBody 歷史紀錄"
        )
