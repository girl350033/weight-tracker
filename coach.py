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
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    h1 {
        font-size: 28px !important;
        font-weight: 800 !important;
    }

    h2, h3 {
        font-size: 21px !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 23px !important;
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

        st.error("找不到 Supabase 設定")
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

        return int(
            round(
                float(value)
            )
        )

    except:
        return default


def simple_date(value):

    try:
        d = pd.to_datetime(value)

        return f"{d.month}/{d.day}"

    except:
        return str(value)


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
        -
        abs(actual - target)
        / target
        * 100
    )

    return max(
        0,
        min(100, score)
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
# Supabase：每日紀錄
# =========================================================

def get_daily_logs():

    try:

        response = (
            supabase
            .table("daily_logs")
            .select("*")
            .eq(
                "person",
                "Shing"
            )
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


# =========================================================
# Supabase：飲食目標
# =========================================================

def get_nutrition_targets():

    try:

        response = (
            supabase
            .table("nutrition_targets")
            .select("*")
            .eq(
                "person",
                "Shing"
            )
            .order("effective_date")
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


# =========================================================
# Supabase：InBody
# =========================================================

def get_inbody_logs():

    try:

        response = (
            supabase
            .table("inbody_logs")
            .select("*")
            .eq(
                "person",
                "Shing"
            )
            .order("date")
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


# =========================================================
# 取得某日期適用的飲食目標
# =========================================================

def get_target_for_date(
    target_df,
    selected_date
):

    if target_df.empty:
        return None

    temp = target_df.copy()

    temp["effective_date"] = (
        pd.to_datetime(
            temp["effective_date"]
        )
    )

    selected_date = pd.to_datetime(
        selected_date
    )

    valid = temp[
        temp["effective_date"]
        <= selected_date
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
# 標題
# =========================================================

st.title("Shing｜教練追蹤")

st.caption(
    "飲食・體重・運動・InBody 追蹤"
)


# =========================================================
# 讀取所有資料
# =========================================================

daily_df = get_daily_logs()

target_df = get_nutrition_targets()

inbody_df = get_inbody_logs()


# =========================================================
# 1. 目前飲食目標
# =========================================================


if not target_df.empty:

    target_temp = target_df.copy()

    target_temp["effective_date"] = pd.to_datetime(
        target_temp["effective_date"]
    )

    current_target = (
        target_temp
        .sort_values("effective_date")
        .iloc[-1]
    )

    st.info(
        f"🎯 **目前飲食目標**　"
        f"{safe_int(current_target['calories'])} kcal　｜　"
        f"碳水 {safe_float(current_target['carbs']):.0f} g　｜　"
        f"蛋白質 {safe_float(current_target['protein']):.0f} g　｜　"
        f"脂肪 {safe_float(current_target['fat']):.0f} g"
    )

else:

    st.info("🎯 目前尚未設定飲食目標")


# =========================================================
# 2. 每日追蹤表格
# =========================================================

st.markdown("---")

st.subheader("📋 每日追蹤")


if not daily_df.empty:

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


    coach_rows = []


    for _, row in (
        daily_df
        .sort_values(
            "date",
            ascending=False
        )
        .iterrows()
    ):

        row_date = row["date"]


        target = get_target_for_date(
            target_df,
            row_date
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
                (
                    f"{safe_int(row.get('ex_cal', 0))} kcal"
                )
            }
        )


    coach_df = pd.DataFrame(
        coach_rows
    )


    st.dataframe(
        coach_df,
        hide_index=True,
        use_container_width=True,
        height=420
    )


else:

    st.info(
        "目前尚無每日紀錄"
    )


# =========================================================
# 3. 體重變化
# =========================================================

st.markdown("---")

st.subheader("⚖️ 體重變化")


if not daily_df.empty:

    weight_df = daily_df.copy()


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
        .dropna(
            subset=[
                "weight"
            ]
        )
        .sort_values(
            "date"
        )
    )


    if not weight_df.empty:

        # =================================================
        # 最新體重 / 起始體重 / 變化
        # =================================================

        first_weight = safe_float(
            weight_df.iloc[0][
                "weight"
            ]
        )


        latest_weight = safe_float(
            weight_df.iloc[-1][
                "weight"
            ]
        )


        weight_change = (
            latest_weight
            - first_weight
        )


        c1, c2, c3 = st.columns(3)


        with c1:

            st.metric(
                "起始體重",
                f"{first_weight:.1f} kg"
            )


        with c2:

            st.metric(
                "目前體重",
                f"{latest_weight:.1f} kg"
            )


        with c3:

            st.metric(
                "體重變化",
                f"{weight_change:+.1f} kg"
            )


        # =================================================
        # 體重圖
        # =================================================

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


        fig_weight.update_yaxes(
            range=[
                lower,
                upper
            ],

            title="kg",

            tickformat=".1f"
        )


        fig_weight.update_xaxes(
            tickformat="%m/%d",
            title=""
        )


        fig_weight.update_layout(
            height=350,

            margin=dict(
                l=20,
                r=20,
                t=20,
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


    else:

        st.info(
            "目前尚無體重紀錄"
        )


else:

    st.info(
        "目前尚無體重紀錄"
    )


# =========================================================
# 4. InBody 紀錄變化
# =========================================================

st.markdown("---")

st.subheader("📊 InBody 紀錄變化")


if not inbody_df.empty:

    inbody_df[
        "date"
    ] = pd.to_datetime(
        inbody_df[
            "date"
        ]
    )


    inbody_df = (
        inbody_df
        .sort_values(
            "date"
        )
    )


    for col in [
        "weight",
        "body_fat",
        "muscle",
        "bmr"
    ]:

        inbody_df[
            col
        ] = pd.to_numeric(
            inbody_df[
                col
            ],
            errors="coerce"
        )


    # =====================================================
    # 最新 InBody
    # =====================================================

    latest_ib = (
        inbody_df
        .iloc[-1]
    )


    st.caption(
        "最近測量："
        f"{simple_date(latest_ib['date'])}"
    )


    c1, c2, c3, c4 = st.columns(4)


    with c1:

        st.metric(
            "體重",
            f"{safe_float(latest_ib['weight']):.1f} kg"
        )


    with c2:

        st.metric(
            "體脂率",
            f"{safe_float(latest_ib['body_fat']):.1f}%"
        )


    with c3:

        st.metric(
            "骨骼肌",
            f"{safe_float(latest_ib['muscle']):.1f} kg"
        )


    with c4:

        st.metric(
            "BMR",
            f"{safe_int(latest_ib['bmr'])} kcal"
        )


    # =====================================================
    # InBody 歷史表
    # =====================================================

    st.write("#### InBody 歷史紀錄")


    inbody_show = pd.DataFrame(
        {
            "日期":
            inbody_df[
                "date"
            ].apply(
                simple_date
            ),

            "體重":
            inbody_df[
                "weight"
            ].apply(
                lambda x:
                f"{safe_float(x):.1f} kg"
            ),

            "體脂率":
            inbody_df[
                "body_fat"
            ].apply(
                lambda x:
                f"{safe_float(x):.1f}%"
            ),

            "骨骼肌":
            inbody_df[
                "muscle"
            ].apply(
                lambda x:
                f"{safe_float(x):.1f} kg"
            ),

            "BMR":
            inbody_df[
                "bmr"
            ].apply(
                lambda x:
                f"{safe_int(x)} kcal"
            )
        }
    )


    inbody_show = (
        inbody_show
        .iloc[::-1]
        .reset_index(
            drop=True
        )
    )


    st.dataframe(
        inbody_show,
        hide_index=True,
        use_container_width=True
    )


    # =====================================================
    # 體脂變化
    # =====================================================

    st.write("#### 體脂率變化")


    fig_fat = go.Figure()


    fig_fat.add_trace(
        go.Scatter(
            x=inbody_df[
                "date"
            ],

            y=inbody_df[
                "body_fat"
            ],

            mode="lines+markers",

            hovertemplate=(
                "%{x|%m/%d}"
                "<br>"
                "%{y:.1f}%"
                "<extra></extra>"
            )
        )
    )


    fig_fat.update_xaxes(
        tickformat="%m/%d",
        title=""
    )


    fig_fat.update_yaxes(
        title="%",
        tickformat=".1f"
    )


    fig_fat.update_layout(
        height=320,

        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20
        ),

        showlegend=False
    )


    st.plotly_chart(
        fig_fat,
        use_container_width=True,

        config={
            "displayModeBar":
            False
        },

        key="coach_bodyfat_chart"
    )


    # =====================================================
    # 骨骼肌變化
    # =====================================================

    st.write("#### 骨骼肌變化")


    fig_muscle = go.Figure()


    fig_muscle.add_trace(
        go.Scatter(
            x=inbody_df[
                "date"
            ],

            y=inbody_df[
                "muscle"
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


    fig_muscle.update_xaxes(
        tickformat="%m/%d",
        title=""
    )


    fig_muscle.update_yaxes(
        title="kg",
        tickformat=".1f"
    )


    fig_muscle.update_layout(
        height=320,

        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20
        ),

        showlegend=False
    )


    st.plotly_chart(
        fig_muscle,
        use_container_width=True,

        config={
            "displayModeBar":
            False
        },

        key="coach_muscle_chart"
    )


else:

    st.info(
        "目前尚無 InBody 紀錄"
    )
