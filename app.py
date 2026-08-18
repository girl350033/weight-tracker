import streamlit as st

st.title("⚖️ 個人體重與 InBody 追蹤器")

# 側邊欄切換使用者
user = st.sidebar.selectbox("選擇使用者", ["使用者一", "使用者二"])

# 分頁籤
tab1, tab2, tab3 = st.tabs(["每日紀錄", "趨勢圖表", "InBody 數據"])

with tab1:
    st.subheader(f"[{user}] 每日紀錄表")
    date = st.date_input("日期")
    weight = st.number_input("今日體重 (kg)", value=60.0, step=0.1)
    
    if st.button("儲存紀錄"):
        st.success("已成功儲存！")

with tab2:
    st.subheader("📊 數據趨勢")
    st.line_chart([62, 61.8, 61.5, 61.2]) # 範例圖表

with tab3:
    st.subheader("📈 InBody 紀錄 (1-2個月測量一次)")
    ib_weight = st.number_input("InBody 體重", value=60.0)
    ib_bf = st.number_input("體脂率 (%)", value=20.0)
    ib_bmr = st.number_input("基礎代謝率 (BMR)", value=1400)
    
    if st.button("儲存 InBody"):
        st.success("InBody 數據已更新！")
