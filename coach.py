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
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    /* 隱藏側邊欄 */
    [data-testid="stSidebar"] {
        display: none;
    }

    [data-testid="collapsedControl"] {
        display: none;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
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
        font-size: 26px !important;
    }

    [data-testid="stDataFrame"] {
        font-size: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 登入
# =========================================================

def coach_login():

    if "coach_authenticated" not in st.session_state:
        st.session_state.coach_authenticated = False

    if st.session_state.coach_authenticated:
        return True

    st.title("📊 Shing 教練追蹤")

    st.write("請輸入查看密碼")

    password = st.text_input(
        "密碼",
        type="password",
        label_visibility="collapsed"
    )

    if st.button(
        "登入",
        type="primary",
        use_container_width=True
    ):

        correct_password = st.secrets.get(
            "COACH_PASSWORD",
            ""
        )

        if (
            correct_password
            and password == correct_password
        ):

            st.session_state.coach_authenticated = True
            st.rerun()

        else:

            st.error("密碼錯誤")

    return False


if not coach_login():
    st.stop()


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
            "Supabase 尚未設定"
        )

        st.stop()

    return create_client(
        supabase_url,
        supabase_key
    )


supabase = get_supabase()


# =========================================================
# 基本函式
# =========================================================

PERSON = "Shing"


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


def simple_date(
    value
):

    try:

        d = pd.to_datetime(
            value
        )

        return (
            f"{d.month}/{d.day}"
        )

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
                actual
                - target
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
# Supabase 查詢
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
                PERSON
            )
            .order(
                "date"
            )
            .execute()
        )

        return pd.DataFrame(
            response.data
            or []
        )

    except Exception as e:

        st.error(
            f"讀取紀錄失敗：{e}"
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
                PERSON
            )
            .order(
                "effective_date"
            )
            .execute()
        )

        return pd.DataFrame(
            response.data
            or []
        )

    except Exception as e:

        st.error(
            f"讀取飲食目標失敗：{e}"
        )

        return pd.DataFrame()


def get_target_for_date(
    selected_date,
    targets_df
):

    if targets_df.empty:
        return None

    temp = targets_df.copy()

    temp[
        "effective_date"
    ] = pd.to_datetime(
        temp[
            "effective_date"
        ]
    )

    target_date = pd.Timestamp(
        selected_date
    )

    valid = temp[
        temp[
            "effective_date"
        ]
        <= target_date
    ]

    if valid.empty:
        return None

    valid = valid.sort_values(
        "effective_date",
        ascending=False
    )

    return (
        valid
        .iloc[0]
        .to_dict()
    )


# =========================================================
# 取得資料
# =========================================================

daily_df = get_daily_logs()

targets_df = get_nutrition_targets()


# =========================================================
# 標題
# =========================================================

col_title, col_logout = st.columns(
    [5, 1]
)

with col_title:

    st.title(
        "📊 Shing 教練追蹤"
    )

with col_logout:

    if st.button(
        "登出"
    ):

        st.session_state.coach_authenticated = False

        st.rerun()


# =========================================================
# 目前飲食目標
# =========================================================

st.subheader(
    "🎯 目前飲食目標"
)

if not targets_df.empty:

    current_target = (
        targets_df
        .sort_values(
            "effective_date",
            ascending=False
        )
        .iloc[0]
    )

    c1, c2, c3, c4 = st.columns(
        4
    )

    c1.metric(
        "熱量",
        f"{safe_int(current_target['calories'])} kcal"
    )

    c2.metric(
        "碳水",
        f"{safe_float(current_target['carbs']):.0f} g"
    )

    c3.metric(
        "蛋白質",
        f"{safe_float(current_target['protein']):.0f} g"
    )

    c4.metric(
        "脂肪",
        f"{safe_float(current_target['fat']):.0f} g"
    )

    st.caption(
        "生效日期："
        + simple_date(
            current_target[
                "effective_date"
            ]
        )
    )

else:

    st.info(
        "目前尚未設定飲食目標"
    )


# =========================================================
# 體重趨勢
# =========================================================

if not daily_df.empty:

    st.markdown("---")

    st.subheader(
        "⚖️ 體重趨勢"
    )

    weight_df = (
        daily_df.copy()
    )

    weight_df[
        "date"
    ] = pd.to_datetime(
        weight_df[
            "date"
        ]
    )

    weight_df[
        "weight"
    ] = pd.to_numeric(
        weight_df[
            "weight"
        ],
        errors="coerce"
    )

    weight_df = (
        weight_df
        .sort_values(
            "date"
        )
    )

    fig_weight = go.Figure()

    fig_weight.add_trace(
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

    valid_weights = (
        weight_df[
            "weight"
        ]
        .dropna()
    )

    if not valid_weights.empty:

        minimum = (
            valid_weights
            .min()
        )

        maximum = (
            valid_weights
            .max()
        )

        lower = (
            minimum
            - 2
        )

        upper = (
            maximum
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
        title="",
        nticks=8
    )

    fig_weight.update_layout(
        height=330,
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
        key="coach_weight_chart"
    )


# =========================================================
# 教練追蹤表
# =========================================================

st.markdown("---")

st.subheader(
    "📋 每日追蹤紀錄"
)


if not daily_df.empty:

    display_df = (
        daily_df
        .sort_values(
            "date",
            ascending=False
        )
        .copy()
    )

    coach_rows = []

    for _, row in (
        display_df
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
                row_date,
                targets_df
            )
        )

        actual_cal = (
            safe_float(
                row.get(
                    "total_calories",
                    0
                )
            )
        )

        actual_carbs = (
            safe_float(
                row.get(
                    "total_carbs",
                    0
                )
            )
        )

        actual_protein = (
            safe_float(
                row.get(
                    "total_protein",
                    0
                )
            )
        )

        actual_fat = (
            safe_float(
                row.get(
                    "total_fat",
                    0
                )
            )
        )


        if target:

            adherence = (
                calculate_diet_adherence(
                    actual_cal,
                    actual_carbs,
                    actual_protein,
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
                f"{safe_float(row.get('weight', 0)):.1f}",

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
                f"{actual_carbs:.1f}",

                "蛋白質":
                f"{actual_protein:.1f}",

                "脂肪":
                f"{actual_fat:.1f}",

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
        height=500
    )


else:

    st.info(
        "目前尚無每日紀錄"
    )
