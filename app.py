import streamlit as st
import pandas as pd
import sqlite3
import json
import base64
from openai import OpenAI
import plotly.express as px

# 初始化資料庫
def init_db():
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_logs 
                 (user TEXT, date TEXT, weight REAL, ex_name TEXT, ex_cal INTEGER, items_json TEXT, total_calories INTEGER, total_protein INTEGER, total_fat INTEGER, total_carbs INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inbody_logs 
                 (user TEXT, date TEXT, weight REAL, body_fat REAL, muscle REAL, bmr INTEGER)''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="Shing & Gloria 健康追蹤器", page_icon="⚖️", layout="centered")

# CSS 優化：字體與排版
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 18px !important; }
    h1, h2, h3 { font-size: 18px !important; font-weight: bold !important; margin-bottom: 0.5rem !important; }
    </style>
""", unsafe_allow_html=True)

st.title("健康與體態追蹤系統")
user = st.radio("選擇使用者", ["Shing", "Gloria"], horizontal=True)

if "current_foods" not in st.session_state:
    st.session_state.current_foods = []

tab1, tab2, tab3 = st.tabs(["紀錄", "趨勢", "InBody"])

with tab1:
    st.write(f"今日紀錄 - {user}")
    date = st.date_input("日期")
    weight = st.number_input("今日體重 (kg)", value=60.0, step=0.1)
    
    st.markdown("---")
    st.write("🍔 飲食紀錄（AI 辨識或手動輸入）")
    
    # AI 拍照辨識
    uploaded_file = st.file_uploader("拍照辨識飲食", type=["jpg", "png"])
    if uploaded_file and st.button("✨ 開始 AI 辨識"):
        with st.spinner("AI 辨識中..."):
            try:
                bytes_data = uploaded_file.getvalue()
                base64_image = base64.b64encode(bytes_data).decode("utf-8")
                api_key = st.secrets.get("OPENAI_API_KEY", "")
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": '辨識食物與熱量、營養素，回傳JSON: {"items":[{"name":"名稱","portion":"份量","calories":100,"protein":10,"fat":5,"carbs":15}]}'},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                    max_tokens=500
                )
                res = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(res)
                st.session_state.current_foods.extend(parsed["items"])
                st.success("AI 辨識成功！")
            except Exception as e: st.error(f"錯誤: {e}")

    # 手動新增飲食
    with st.expander("➕ 手動新增食物項目"):
        m_name = st.text_input("食物名稱")
        m_cal = st.number_input("熱量 (kcal)", value=0, step=10)
        m_pro = st.number_input("蛋白質 (g)", value=0, step=1)
        m_fat = st.number_input("脂肪 (g)", value=0, step=1)
        m_carb = st.number_input("碳水化合物 (g)", value=0, step=1)
        if st.button("加入手動清單"):
            st.session_state.current_foods.append({
                "name": m_name if m_name else "手動自訂食物",
                "calories": m_cal, "protein": m_pro, "fat": m_fat, "carbs": m_carb
            })
            st.success("已加入清單！")

    # 顯示目前已加入的食物
    if st.session_state.current_foods:
        st.write("目前記錄的食物：")
        for i, f in enumerate(st.session_state.current_foods):
            st.write(f"- {f['name']} | 熱量: {f.get('calories',0)} kcal (蛋白質 {f.get('protein',0)}g / 脂肪 {f.get('fat',0)}g / 碳水 {f.get('carbs',0)}g)")
        if st.button("清空目前飲食清單"):
            st.session_state.current_foods = []
            st.rerun()

    st.markdown("---")
    st.write("🏋️ 運動紀錄")
    ex_name = st.text_input("運動項目")
    ex_cal = st.number_input("運動消耗 (kcal)", value=0, step=10)

    if st.button("💾 儲存今日所有紀錄", type="primary"):
        items_json = json.dumps(st.session_state.current_foods)
        total_cal = sum(f.get('calories', 0) for f in st.session_state.current_foods)
        total_pro = sum(f.get('protein', 0) for f in st.session_state.current_foods)
        total_fat = sum(f.get('fat', 0) for f in st.session_state.current_foods)
        total_carb = sum(f.get('carbs', 0) for f in st.session_state.current_foods)
        
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute("INSERT INTO daily_logs VALUES (?,?,?,?,?,?,?,?,?,?)", 
                  (user, str(date), weight, ex_name, ex_cal, items_json, total_cal, total_pro, total_fat, total_carb))
        conn.commit()
        conn.close()
        st.session_state.current_foods = []
        st.success("紀錄已永久儲存！")

with tab2:
    st.write("📈 歷史趨勢與營養分析")
    conn = sqlite3.connect('tracker.db')
    df = pd.read_sql_query(f"SELECT * FROM daily_logs WHERE user='{user}' ORDER BY date ASC", conn)
    conn.close()
    
    if not df.empty:
        st.write("體重變化 (45 - 90 kg)：")
        chart_weight = px.line(df, x='date', y='weight', markers=True)
        chart_weight.update_yaxes(range=[45, 90])
        st.plotly_chart(chart_weight, use_container_width=True)
        
        st.write("熱量攝取變化 (kcal)：")
        chart_cal = px.line(df, x='date', y='total_calories', markers=True)
        chart_cal.update_yaxes(tickformat="d") # 確保整數格式
        st.plotly_chart(chart_cal, use_container_width=True)
        
        st.markdown("---")
        st.write("🥧 最近一次紀錄的三大營養素比例")
        latest_row = df.iloc[-1]
        macro_data = {
            '營養素': ['蛋白質', '脂肪', '碳水化合物'],
            '克數 (g)': [latest_row['total_protein'], latest_row['total_fat'], latest_row['total_carbs']]
        }
        fig_pie = px.pie(macro_data, names='營養素', values='克數 (g)', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("尚無歷史數據，請先至「紀錄」分頁新增資料。")

with tab3:
    st.write(f"InBody 紀錄 - {user}")
    ib_date = st.date_input("測量日期", key="ib_d")
    ib_w = st.number_input("InBody 體重 (kg)", value=60.0, step=0.1)
    ib_bf = st.number_input("體脂率 (%)", value=20.0, step=0.1)
    ib_mu = st.number_input("骨骼肌 (kg)", value=25.0, step=0.1)
    ib_bmr = st.number_input("BMR (kcal)", value=1400, step=10)
    
    if st.button("💾 儲存 InBody"):
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute("INSERT INTO inbody_logs VALUES (?,?,?,?,?,?)", (user, str(ib_date), ib_w, ib_bf, ib_mu, ib_bmr))
        conn.commit()
        conn.close()
        st.success("InBody 紀錄已保存！")

    conn = sqlite3.connect('tracker.db')
    ib_df = pd.read_sql_query(f"SELECT * FROM inbody_logs WHERE user='{user}' ORDER BY date ASC", conn)
    conn.close()
    if not ib_df.empty:
        st.write("InBody 體重趨勢 (45 - 90 kg)：")
        ib_chart = px.line(ib_df, x='date', y='weight', markers=True)
        ib_chart.update_yaxes(range=[45, 90])
        st.plotly_chart(ib_chart, use_container_width=True)
