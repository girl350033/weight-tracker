import streamlit as st
import pandas as pd
import sqlite3
import json
import base64
from openai import OpenAI

# 初始化資料庫
def init_db():
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_logs 
                 (user TEXT, date TEXT, weight REAL, ex_name TEXT, ex_cal INTEGER, items_json TEXT, total_calories INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inbody_logs 
                 (user TEXT, date TEXT, weight REAL, body_fat REAL, muscle REAL, bmr INTEGER)''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="Shing & Gloria 健康追蹤器", page_icon="⚖️", layout="centered")

# CSS 優化：將標題大小設為與內文一致 (18px)
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
    st.write("飲食紀錄與 AI 辨識")
    uploaded_file = st.file_uploader("拍照辨識", type=["jpg", "png"])
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
                        {"type": "text", "text": '辨識 JSON: {"items":[{"name":"名稱","portion":"份量","calories":100}]}'},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                    max_tokens=500
                )
                res = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(res)
                st.session_state.current_foods.extend(parsed["items"])
                st.success("辨識成功！")
            except Exception as e: st.error(f"錯誤: {e}")

    st.write("運動紀錄")
    ex_name = st.text_input("運動項目")
    ex_cal = st.number_input("運動消耗 (kcal)", value=0)

    if st.button("💾 儲存今日所有紀錄", type="primary"):
        items_json = json.dumps(st.session_state.current_foods)
        total_cal = sum(f.get('calories', 0) for f in st.session_state.current_foods)
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute("INSERT INTO daily_logs VALUES (?,?,?,?,?,?,?)", 
                  (user, str(date), weight, ex_name, ex_cal, items_json, total_cal))
        conn.commit()
        conn.close()
        st.session_state.current_foods = []
        st.success("紀錄已永久儲存！")

with tab2:
    st.write("歷史趨勢圖")
    conn = sqlite3.connect('tracker.db')
    df = pd.read_sql_query(f"SELECT * FROM daily_logs WHERE user='{user}' ORDER BY date DESC", conn)
    conn.close()
    if not df.empty:
        st.write("體重變化：")
        st.line_chart(df.set_index('date')['weight'])
        st.write("熱量攝取變化：")
        st.line_chart(df.set_index('date')['total_calories'])
        
        st.write("詳細紀錄表")
        st.dataframe(df)

with tab3:
    st.write(f"InBody 紀錄 - {user}")
    # ... (InBody 邏輯保持不變)
