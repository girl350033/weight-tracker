import streamlit as st
import pandas as pd
import json
import base64
from datetime import date

import plotly.express as px
import plotly.graph_objects as go

from openai import OpenAI
from supabase import create_client


# =========================================================
# 頁面設定
# =========================================================

st.set_page_config(
    page_title="Shing & Gloria 健康追蹤器",
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
        font-size: 25px !important;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    button[data-baseweb="tab"] {
        font-size: 17px !important;
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
    """
    2026-08-18 -> 8/18
    """
    try:
        d = pd.to_datetime(value)
        return f"{d.month}/{d.day}"
    except:
        return str(value)


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


def save_daily_record(
    person,
    record_date,
    weight,
    ex_name,
    ex_cal,
    foods
):

    total_cal = sum(
        safe_float(f.get("calories", 0))
        for f in foods
    )

    total_pro = sum(
        safe_float(f.get("protein", 0))
        for f in foods
    )

    total_fat = sum(
        safe_float(f.get("fat", 0))
        for f in foods
    )

    total_carb = sum(
        safe_float(f.get("carbs", 0))
        for f in foods
    )

    payload = {
        "person": person,
        "date": str(record_date),
        "weight": round(float(weight), 2),
        "ex_name": ex_name or "",
        "ex_cal": safe_int(ex_cal),
        "items_json": foods,
        "total_calories": safe_int(total_cal),
        "total_protein": round(total_pro, 1),
        "total_fat": round(total_fat, 1),
        "total_carbs": round(total_carb, 1)
    }

    existing = get_daily_record(
        person,
        record_date
    )

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

        return True

    except Exception as e:
        st.error(f"刪除失敗：{e}")
        return False


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


def save_inbody_record(
    person,
    record_date,
    weight,
    body_fat,
    muscle,
    bmr
):

    payload = {
        "person": person,
        "date": str(record_date),
        "weight": round(float(weight), 2),
        "body_fat": round(float(body_fat), 2),
        "muscle": round(float(muscle), 2),
        "bmr": safe_int(bmr)
    }

    existing = get_inbody_record(
        person,
        record_date
    )

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


# =========================================================
# 標題 / 使用者
# =========================================================

st.title("健康與體態追蹤系統")

person = st.radio(
    ["Shing", "Gloria"],
    horizontal=True
)


tab1, tab2, tab3, tab4 = st.tabs(
    [
        "紀錄",
        "趨勢",
        "歷史紀錄",
        "InBody"
    ]
)


# =========================================================
# TAB 1 紀錄
# =========================================================

with tab1:

    st.subheader(f"每日紀錄｜{person}")

    record_date = st.date_input(
        "日期",
        value=date.today(),
        format="YYYY/MM/DD",
        key="record_date"
    )

    session_key = f"{person}_{record_date}"

    old_record = get_daily_record(
        person,
        record_date
    )

    # 日期切換時載入當天舊資料
    if st.session_state.loaded_food_key != session_key:

        if old_record:

            old_items = old_record.get(
                "items_json",
                []
            )

            if isinstance(old_items, str):
                try:
                    old_items = json.loads(old_items)
                except:
                    old_items = []

            st.session_state.current_foods = old_items or []

        else:
            st.session_state.current_foods = []

        st.session_state.loaded_food_key = session_key


    default_weight = (
        safe_float(
            old_record.get("weight"),
            60
        )
        if old_record
        else 60.0
    )

    weight = st.number_input(
        "體重 (kg)",
        min_value=30.0,
        max_value=200.0,
        value=float(default_weight),
        step=0.1,
        format="%.1f"
    )


    # =====================================================
    # 飲食
    # =====================================================

    st.markdown("---")
    st.subheader("🍱 飲食紀錄")

    uploaded_file = st.file_uploader(
        "拍照辨識飲食",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file and st.button(
        "✨ 開始 AI 辨識"
    ):

        with st.spinner("AI 正在辨識餐點..."):

            try:

                bytes_data = uploaded_file.getvalue()

                base64_image = base64.b64encode(
                    bytes_data
                ).decode("utf-8")

                api_key = st.secrets.get(
                    "OPENAI_API_KEY",
                    ""
                )

                if not api_key:
                    st.error("尚未設定 OPENAI_API_KEY")
                    st.stop()

                client = OpenAI(
                    api_key=api_key
                )

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """
請辨識照片中的食物。

估計每項食物：
名稱
份量
熱量 kcal
蛋白質 g
脂肪 g
碳水化合物 g

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
                                    "type": "image_url",
                                    "image_url": {
                                        "url":
                                        f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=700
                )

                res = (
                    response
                    .choices[0]
                    .message
                    .content
                )

                res = (
                    res
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

                parsed = json.loads(res)

                st.session_state.current_foods.extend(
                    parsed.get(
                        "items",
                        []
                    )
                )

                st.success("AI 辨識完成")
                st.rerun()

            except Exception as e:
                st.error(f"AI 辨識失敗：{e}")


    # =====================================================
    # 手動新增
    # =====================================================

    with st.expander("➕ 手動新增食物"):

        m_name = st.text_input(
            "食物名稱"
        )

        m_portion = st.text_input(
            "份量",
            placeholder="例如：100g、1碗、1份"
        )

        m_cal = st.number_input(
            "熱量 kcal",
            min_value=0,
            value=0,
            step=10
        )

        m_pro = st.number_input(
            "蛋白質 g",
            min_value=0.0,
            value=0.0,
            step=1.0
        )

        m_fat = st.number_input(
            "脂肪 g",
            min_value=0.0,
            value=0.0,
            step=1.0
        )

        m_carb = st.number_input(
            "碳水化合物 g",
            min_value=0.0,
            value=0.0,
            step=1.0
        )

        if st.button("加入食物"):

            st.session_state.current_foods.append(
                {
                    "name":
                    m_name if m_name else "自訂食物",

                    "portion":
                    m_portion,

                    "calories":
                    safe_int(m_cal),

                    "protein":
                    safe_float(m_pro),

                    "fat":
                    safe_float(m_fat),

                    "carbs":
                    safe_float(m_carb)
                }
            )

            st.rerun()


    # =====================================================
    # 當天食物可直接編輯
    # =====================================================

    if st.session_state.current_foods:

        st.write("### 當日食物")

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
            key=f"food_editor_{session_key}"
        )

        cleaned_foods = []

        for item in edited_food_df.to_dict("records"):

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

        st.session_state.current_foods = cleaned_foods


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
        # 今日總覽
        # =================================================

        st.write("### 今日營養")

        c1, c2 = st.columns(2)

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
        # 當天圓餅圖
        # =================================================

        protein_kcal = total_pro * 4
        fat_kcal = total_fat * 9
        carb_kcal = total_carb * 4

        macro_total = (
            protein_kcal
            + fat_kcal
            + carb_kcal
        )

        if macro_total > 0:

            macro_df = pd.DataFrame(
                {
                    "營養素": [
                        "蛋白質",
                        "脂肪",
                        "碳水"
                    ],
                    "熱量": [
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
                textinfo="percent+label",
                hovertemplate=(
                    "%{label}"
                    "<br>%{percent}"
                    "<extra></extra>"
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
                    "displayModeBar": False
                }
            )


        if st.button(
            "清空當日食物"
        ):
            st.session_state.current_foods = []
            st.rerun()


    else:
        st.info("這一天尚未加入食物")


    # =====================================================
    # 運動
    # =====================================================

    st.markdown("---")
    st.subheader("🏋️ 運動紀錄")

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

    ex_name = st.text_input(
        "運動項目",
        value=default_ex_name or ""
    )

    ex_cal = st.number_input(
        "運動消耗 kcal",
        min_value=0,
        value=default_ex_cal,
        step=10
    )


    # =====================================================
    # 儲存
    # =====================================================

    if st.button(
        "💾 更新這一天紀錄"
        if old_record
        else "💾 儲存這一天紀錄",
        type="primary"
    ):

        success = save_daily_record(
            person=person,
            record_date=record_date,
            weight=weight,
            ex_name=ex_name,
            ex_cal=ex_cal,
            foods=st.session_state.current_foods
        )

        if success:
            st.success("紀錄已永久儲存！")
            st.rerun()


# =========================================================
# TAB 2 趨勢
# =========================================================

with tab2:

    st.subheader("📈 體重與營養趨勢")

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


        # =================================================
        # 體重圖
        # =================================================

        st.write("### 體重變化")

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

        valid_weight = df["weight"].dropna()

        if not valid_weight.empty:

            min_weight = valid_weight.min()
            max_weight = valid_weight.max()

            lower = max(
                30,
                min_weight - 2
            )

            upper = max_weight + 2

            if upper - lower < 5:
                upper = lower + 5

            fig_weight.update_yaxes(
                range=[
                    lower,
                    upper
                ],
                tickformat=".1f",
                title="體重 kg"
            )

        fig_weight.update_xaxes(
            tickformat="%m/%d",
            tickangle=0,
            title="",
            nticks=6
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
                "displayModeBar": False
            }
        )


        # =================================================
        # 當日營養圓餅圖
        # =================================================

        st.markdown("---")
        st.write("### 單日營養比例")

        available_dates = (
            df["date"]
            .dt.date
            .tolist()
        )

        selected_macro_date = st.selectbox(
            "選擇日期",
            options=available_dates,
            index=len(available_dates) - 1,
            format_func=lambda x: f"{x.month}/{x.day}"
        )

        selected_row = df[
            df["date"].dt.date
            == selected_macro_date
        ].iloc[-1]

        pro = safe_float(
            selected_row.get(
                "total_protein",
                0
            )
        )

        fat = safe_float(
            selected_row.get(
                "total_fat",
                0
            )
        )

        carb = safe_float(
            selected_row.get(
                "total_carbs",
                0
            )
        )

        cal = safe_float(
            selected_row.get(
                "total_calories",
                0
            )
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "熱量",
            f"{cal:.0f}"
        )

        c2.metric(
            "蛋白",
            f"{pro:.1f}g"
        )

        c3.metric(
            "脂肪",
            f"{fat:.1f}g"
        )

        c4.metric(
            "碳水",
            f"{carb:.1f}g"
        )

        macro_df = pd.DataFrame(
            {
                "營養素": [
                    "蛋白質",
                    "脂肪",
                    "碳水"
                ],
                "熱量": [
                    pro * 4,
                    fat * 9,
                    carb * 4
                ]
            }
        )

        if macro_df["熱量"].sum() > 0:

            macro_chart = px.pie(
                macro_df,
                names="營養素",
                values="熱量",
                hole=0.45
            )

            macro_chart.update_traces(
                textinfo="percent+label",
                textposition="inside"
            )

            macro_chart.update_layout(
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
                macro_chart,
                use_container_width=True,
                config={
                    "displayModeBar": False
                }
            )

        else:
            st.info(
                "這一天沒有營養素資料"
            )

    else:
        st.info(
            "尚無歷史資料"
        )


# =========================================================
# TAB 3 歷史紀錄
# =========================================================

with tab3:

    st.subheader("📋 歷史紀錄")

    history_df = get_daily_logs(
        person
    )

    if not history_df.empty:

        history_df = history_df.sort_values(
            "date",
            ascending=False
        )

        display_df = history_df.copy()

        display_df["日期"] = display_df[
            "date"
        ].apply(
            simple_date
        )

        display_df["體重"] = pd.to_numeric(
            display_df["weight"],
            errors="coerce"
        ).round(1)

        display_df["熱量"] = pd.to_numeric(
            display_df["total_calories"],
            errors="coerce"
        ).fillna(0).astype(int)

        display_df["蛋白質"] = pd.to_numeric(
            display_df["total_protein"],
            errors="coerce"
        ).fillna(0).round(1)

        display_df["脂肪"] = pd.to_numeric(
            display_df["total_fat"],
            errors="coerce"
        ).fillna(0).round(1)

        display_df["碳水"] = pd.to_numeric(
            display_df["total_carbs"],
            errors="coerce"
        ).fillna(0).round(1)

        show_cols = [
            "日期",
            "體重",
            "熱量",
            "蛋白質",
            "脂肪",
            "碳水"
        ]

        st.dataframe(
            display_df[
                show_cols
            ],
            hide_index=True,
            use_container_width=True
        )


        # =================================================
        # 下載 CSV
        # =================================================

        download_df = display_df[
            show_cols
        ].copy()

        csv_data = download_df.to_csv(
            index=False
        ).encode(
            "utf-8-sig"
        )

        st.download_button(
            "⬇️ 下載歷史紀錄 CSV",
            data=csv_data,
            file_name=f"{person}_健康紀錄.csv",
            mime="text/csv"
        )


        # =================================================
        # 編輯指定舊紀錄
        # =================================================

        st.markdown("---")
        st.write("### 編輯過往紀錄")

        edit_dates = history_df[
            "date"
        ].tolist()

        selected_edit_date = st.selectbox(
            "選擇要編輯的日期",
            options=edit_dates,
            format_func=simple_date,
            key="history_edit_date"
        )

        selected_history = history_df[
            history_df["date"]
            == selected_edit_date
        ].iloc[0]

        edit_weight = st.number_input(
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
            key="edit_weight"
        )

        edit_ex_name = st.text_input(
            "運動項目",
            value=selected_history.get(
                "ex_name",
                ""
            ) or "",
            key="edit_ex_name"
        )

        edit_ex_cal = st.number_input(
            "運動消耗",
            min_value=0,
            value=safe_int(
                selected_history.get(
                    "ex_cal",
                    0
                )
            ),
            step=10,
            key="edit_ex_cal"
        )

        raw_items = selected_history.get(
            "items_json",
            []
        )

        if isinstance(raw_items, str):
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
                    if col in [
                        "name",
                        "portion"
                    ]
                    else 0
                )

        edit_food_df = edit_food_df[
            [
                "name",
                "portion",
                "calories",
                "protein",
                "fat",
                "carbs"
            ]
        ]

        edited_history_foods = st.data_editor(
            edit_food_df,
            hide_index=True,
            num_rows="dynamic",
            use_container_width=True,
            key=f"history_food_editor_{selected_edit_date}",
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
                    "熱量"
                ),

                "protein":
                st.column_config.NumberColumn(
                    "蛋白質"
                ),

                "fat":
                st.column_config.NumberColumn(
                    "脂肪"
                ),

                "carbs":
                st.column_config.NumberColumn(
                    "碳水"
                )
            }
        )


        col_update, col_delete = st.columns(2)

        with col_update:

            if st.button(
                "💾 儲存修改",
                type="primary"
            ):

                foods = []

                for item in edited_history_foods.to_dict(
                    "records"
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

                success = save_daily_record(
                    person=person,
                    record_date=selected_edit_date,
                    weight=edit_weight,
                    ex_name=edit_ex_name,
                    ex_cal=edit_ex_cal,
                    foods=foods
                )

                if success:
                    st.success("修改完成")
                    st.rerun()


        with col_delete:

            if st.button(
                "🗑️ 刪除這筆"
            ):

                success = delete_daily_record(
                    selected_history["id"]
                )

                if success:
                    st.success("已刪除")
                    st.rerun()


    else:
        st.info(
            "尚無歷史紀錄"
        )


# =========================================================
# TAB 4 InBody
# =========================================================

with tab4:

    st.subheader(
        f"InBody｜{person}"
    )

    ib_date = st.date_input(
        "測量日期",
        value=date.today(),
        format="YYYY/MM/DD",
        key="ib_date"
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
        step=0.1
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
        step=0.1
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
        step=0.1
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
        step=10
    )

    if st.button(
        "💾 更新 InBody"
        if old_ib
        else "💾 儲存 InBody",
        type="primary"
    ):

        success = save_inbody_record(
            person=person,
            record_date=ib_date,
            weight=ib_weight,
            body_fat=ib_body_fat,
            muscle=ib_muscle,
            bmr=ib_bmr
        )

        if success:
            st.success(
                "InBody 已永久儲存！"
            )
            st.rerun()


    # =====================================================
    # InBody 歷史
    # =====================================================

    ib_df = get_inbody_logs(
        person
    )

    if not ib_df.empty:

        ib_df["date"] = pd.to_datetime(
            ib_df["date"]
        )

        ib_df = ib_df.sort_values(
            "date"
        )

        st.markdown("---")
        st.write("### InBody 體重趨勢")

        fig_ib = go.Figure()

        fig_ib.add_trace(
            go.Scatter(
                x=ib_df["date"],
                y=pd.to_numeric(
                    ib_df["weight"],
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
                "displayModeBar": False
            }
        )


        # =================================================
        # InBody 表格
        # =================================================

        show_ib = ib_df.copy()

        show_ib["日期"] = show_ib[
            "date"
        ].apply(
            simple_date
        )

        show_ib["體重"] = pd.to_numeric(
            show_ib["weight"],
            errors="coerce"
        ).round(1)

        show_ib["體脂率"] = pd.to_numeric(
            show_ib["body_fat"],
            errors="coerce"
        ).round(1)

        show_ib["骨骼肌"] = pd.to_numeric(
            show_ib["muscle"],
            errors="coerce"
        ).round(1)

        show_ib["BMR"] = pd.to_numeric(
            show_ib["bmr"],
            errors="coerce"
        ).fillna(0).astype(int)

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


        # =================================================
        # InBody CSV
        # =================================================

        ib_csv = show_ib[
            [
                "日期",
                "體重",
                "體脂率",
                "骨骼肌",
                "BMR"
            ]
        ].to_csv(
            index=False
        ).encode(
            "utf-8-sig"
        )

        st.download_button(
            "⬇️ 下載 InBody CSV",
            data=ib_csv,
            file_name=f"{person}_InBody.csv",
            mime="text/csv"
        )


        # =================================================
        # 刪除 InBody
        # =================================================

        st.markdown("---")
        st.write("### 刪除 InBody 紀錄")

        delete_ib_dates = (
            ib_df
            .sort_values(
                "date",
                ascending=False
            )
        )

        delete_ib_date = st.selectbox(
            "選擇日期",
            options=delete_ib_dates["date"].tolist(),
            format_func=simple_date,
            key="delete_ib_date"
        )

        selected_ib_delete = delete_ib_dates[
            delete_ib_dates["date"]
            == delete_ib_date
        ].iloc[0]

        if st.button(
            "🗑️ 刪除這筆 InBody"
        ):

            success = delete_inbody_record(
                selected_ib_delete["id"]
            )

            if success:
                st.success(
                    "InBody 紀錄已刪除"
                )
                st.rerun()

    else:
        st.info(
            "尚無 InBody 歷史紀錄"
        )
