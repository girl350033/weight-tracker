import streamlit as st
import pandas as pd

import plotly.graph_objects as go
from supabase import create_client


# =========================================================
# 頁面設定
# =========================================================

st.set_page_config(
    page_title="Shing 教練追蹤",
    page_icon="📊",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>
    html, body, [class*="st-"] {
        font-size: 16px !important;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    h1 {
        font-size: 28px !important;
        font-weight: 800 !important;
    }

    h2, h3 {
        font-size: 20px !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
    }

    [data-testid="stSidebar"] {
        display: none;
    }

    [data-testid="collapsedControl"] {
        display: none;
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

    supabase_url = st.secrets.get(
        "SUPABASE_URL",
        ""
    )

    supabase_key = st.secrets.get(
        "SUPABASE_KEY",
        ""
    )

    if not supabase_url or not supabase_key:

        st.error(
            "找不到 Supabase 設定"
        )

        st.stop()

    return create_client(
        supabase_url,
        supabase_key
    )


supabase = get_supabase()


# =========================================================
# 共用函式
# =========================================================

def safe_float(
    value,
    default=0
):
    try:

        if value is None:
            return default

        return float(value)

    except:

        return default


def safe_int(
    value,
    default=0
):
    try:

        if value is None:
            return default

        return int(
            round(
                float(value)
            )
        )

    except:

        return default


def simple_date(value):

    try:

        d = pd.to_datetime(
            value
        )

        return f"{d.month}/{d.day}"

    except:

        return str(value)


# =========================================================
# 飲食執行率
# =========================================================

def target_score(
    actual,
    target
):

    actual = safe_float(
        actual
    )

    target = safe_float(
        target
    )

    if target <= 0:
        return 100

    score = (
        100
        -
        (
            abs(
                actual - target
            )
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
# Supabase 讀取
# =========================================================

def get_daily_logs():

    try:

        response = (
            supabase
            .table(
                "daily_logs"
            )
            .select("*")
            .eq(
                "person",
                "Shing"
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
            f"讀取每日紀錄失敗：{e}"
        )

        return pd.DataFrame()


def get_nutrition_targets():

    try:

        response = (
            supabase
            .table(
                "nutrition_targets"
            )
            .select("*")
            .eq(
                "person",
                "Shing"
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
    target_df,
    selected_date
):

    if target_df.empty:
        return None

    target_df = target_df.copy()

    target_df[
        "effective_date"
    ] = pd.to_datetime(
        target_df[
            "effective_date"
        ]
    )

    selected_date = pd.to_datetime(
        selected_date
    )

    valid_targets = target_df[
        target_df[
            "effective_date"
        ]
        <= selected_date
    ]

    if valid_targets.empty:
        return None

    valid_targets = (
        valid_targets
        .sort_values(
            "effective_date",
            ascending=False
        )
    )

    return (
        valid_targets
        .iloc[0]
        .to_dict()
    )


# =========================================================
# 標題
# =========================================================

st.title(
    "Shing｜教練追蹤"
)

st.caption(
    "飲食、體重與運動紀錄"
)


# =========================================================
# 讀取資料
# =========================================================

daily_df = get_daily_logs()

target_df = get_nutrition_targets()


# =========================================================
# 沒有資料
# =========================================================

if daily_df.empty:

    st.info(
        "目前尚無紀錄"
    )

    st.stop()


# =========================================================
# 日期處理
# =========================================================

daily_df[
    "date"
] = pd.to_datetime(
    daily_df[
        "date"
    ]
)

daily_df = (
    daily_df
    .sort_values(
        "date"
    )
)


# =========================================================
# 最新紀錄
# =========================================================

latest = (
    daily_df
    .iloc[-1]
)


latest_date = (
    latest[
        "date"
    ]
)

latest_target = (
    get_target_for_date(
        target_df,
        latest_date
    )
)


# =========================================================
# 最新飲食執行率
# =========================================================

if latest_target:

    latest_adherence = (
        calculate_diet_adherence(
            latest.get(
                "total_calories",
                0
            ),

            latest.get(
                "total_carbs",
                0
            ),

            latest.get(
                "total_protein",
                0
            ),

            latest.get(
                "total_fat",
                0
            ),

            latest_target.get(
                "calories",
                0
            ),

            latest_target.get(
                "carbs",
                0
            ),

            latest_target.get(
                "protein",
                0
            ),

            latest_target.get(
                "fat",
                0
            )
        )
    )

else:

    latest_adherence = None


# =========================================================
# 最新摘要
# =========================================================

st.subheader(
    "最新紀錄"
)


c1, c2, c3, c4 = st.columns(
    4
)


with c1:

    st.metric(
        "日期",
        simple_date(
            latest_date
        )
    )


with c2:

    st.metric(
        "體重",
        f"{safe_float(latest.get('weight', 0)):.1f} kg"
    )


with c3:

    st.metric(
        "飲食執行率",
        (
            f"{latest_adherence}%"
            if latest_adherence is not None
            else "-"
        )
    )


with c4:

    st.metric(
        "運動消耗",
        f"{safe_int(latest.get('ex_cal', 0))} kcal"
    )


# =========================================================
# 目前飲食目標
# =========================================================

if latest_target:

    st.info(
        "目前飲食目標｜"
        f"{safe_int(latest_target.get('calories', 0))} kcal｜"
        f"碳水 {safe_float(latest_target.get('carbs', 0)):.0f}g｜"
        f"蛋白質 {safe_float(latest_target.get('protein', 0)):.0f}g｜"
        f"脂肪 {safe_float(latest_target.get('fat', 0)):.0f}g"
    )


# =========================================================
# 體重趨勢
# =========================================================

st.markdown("---")

st.subheader(
    "體重趨勢"
)


weight_df = daily_df.copy()

weight_df[
    "weight"
] = pd.to_numeric(
    weight_df[
        "weight"
    ],
    errors="coerce"
)


weight_df = weight_df.dropna(
    subset=[
        "weight"
    ]
)


if not weight_df.empty:

    fig = go.Figure()


    fig.add_trace(
        go.Scatter(
            x=weight_df[
                "date"
            ],

            y=weight_df[
                "weight"
            ],

            mode="lines+markers",

            hovertemplate=(
                "%{x|%m/%d}"
                "<br>"
                "%{y:.1f} kg"
                "<extra></extra>"
            )
        )
    )


    min_weight = (
        weight_df[
            "weight"
        ]
        .min()
    )


    max_weight = (
        weight_df[
            "weight"
        ]
        .max()
    )


    lower = max(
        30,
        min_weight - 2
    )


    upper = (
        max_weight + 2
    )


    if (
        upper - lower
        < 5
    ):

        upper = (
            lower + 5
        )


    fig.update_yaxes(
        range=[
            lower,
            upper
        ],

        title="kg",

        tickformat=".1f"
    )


    fig.update_xaxes(
        tickformat="%m/%d",
        title=""
    )


    fig.update_layout(
        height=340,

        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20
        ),

        showlegend=False
    )


    st.plotly_chart(
        fig,
        use_container_width=True,

        config={
            "displayModeBar":
            False
        }
    )


# =========================================================
# 教練表格
# =========================================================

st.markdown("---")

st.subheader(
    "每日追蹤"
)


coach_rows = []


for _, row in (
    daily_df
    .sort_values(
        "date",
        ascending=False
    )
    .iterrows()
):

    row_date = (
        row[
            "date"
        ]
    )


    target = (
        get_target_for_date(
            target_df,
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

                target.get(
                    "calories",
                    0
                ),

                target.get(
                    "carbs",
                    0
                ),

                target.get(
                    "protein",
                    0
                ),

                target.get(
                    "fat",
                    0
                )
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
                row_date
            ),

            "體重":
            f"{safe_float(row.get('weight', 0)):.1f} kg",

            "幾點測量":
            (
                row.get(
                    "measure_time",
                    ""
                )
                or ""
            ),

            "飲食執行率":
            adherence_text,

            "運動內容":
            (
                row.get(
                    "ex_name",
                    ""
                )
                or ""
            ),

            "碳水":
            f"{actual_carb:.1f} g",

            "蛋白質":
            f"{actual_pro:.1f} g",

            "脂肪":
            f"{actual_fat:.1f} g",

            "運動消耗":
            f"{safe_int(row.get('ex_cal', 0))} kcal"
        }
    )


coach_df = pd.DataFrame(
    coach_rows
)


st.dataframe(
    coach_df,
    hide_index=True,
    use_container_width=True,
    height=520
)


# =========================================================
# CSV
# =========================================================

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
    "下載追蹤紀錄 CSV",
    data=csv_data,
    file_name="Shing_教練追蹤紀錄.csv",
    mime="text/csv"
)


# =========================================================
# 頁尾
# =========================================================

st.caption(
    "資料會隨每日紀錄更新。"
)
