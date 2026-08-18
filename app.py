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
    c.execute('''CREATE TABLE IF NOT EXISTS food_logs 
                 (user TEXT, date TEXT, items_json TEXT, total_calories INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inbody_logs 
                 (user TEXT, date TEXT, weight REAL, body_fat REAL, muscle REAL, bmr INTEGER)''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="Shing & Gloria 健康追蹤器", page_icon="⚖️", layout="centered")

# CSS 優化：放大字體
st.markdown("""<style>html, body, [class*="st-"] { font-size: 18px !important; }</style>""", unsafe_allow_html=True)

st.title("⚖️ 健康與體態追蹤系統")
user = st.radio("選擇使用者", ["Shing", "Gloria"], horizontal=True)

if "current_foods" not in st.session_state:
    st.session_state.current_foods = []

tab1, tab2, tab3 = st.tabs(["📝 紀錄", "📈 趨勢圖", "📊 InBody"])

with tab1:
    st.subheader(f"今日飲食紀錄 - {user}")
    date = st.date_input("日期")
    
    uploaded_file = st.file_uploader("拍照辨識飲食", type=["jpg", "png"])
    if uploaded_file and st.button("✨ 開始 AI 辨識"):
        with st.spinner("AI 正在分析食物..."):
            try:
                bytes_data = uploaded_file.getvalue()
                base64_image = base64.b64encode(bytes_data).decode("utf-8")
                api_key = st.secrets.get("OPENAI_API_KEY", "")
                client = OpenAI(api_key=api_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": '辨識食物與熱量，回傳JSON: {"items":[{"name":"名稱","portion":"份量","calories":100}]}'},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                    max_tokens=500
                )
                res = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(res)
                st.session_state.current_foods.extend(parsed["items"])
                st.success("辨識成功！")
            except Exception as e:
                st.error(f"辨識錯誤: {e}")

    # 顯示並儲存紀錄
    if st.button("💾 儲存今日飲食"):
        items_json = json.dumps(st.session_state.current_foods)
        total_cal = sum(f.get('calories', 0) for f in st.session_state.current_foods)
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute("INSERT INTO food_logs VALUES (?,?,?,?)", (user, str(date), items_json, total_cal))
        conn.commit()
        conn.close()
        st.session_state.current_foods = [] # 清空暫存
        st.success("飲食紀錄已永久儲存！")

    st.subheader("📋 飲食歷史紀錄")
    conn = sqlite3.connect('tracker.db')
    df = pd.read_sql_query(f"SELECT * FROM food_logs WHERE user='{user}' ORDER BY date DESC", conn)
    conn.close()
    for _, row in df.iterrows():
        with st.expander(f"{row['date']} - 總熱量: {row['total_calories']} kcal"):
            items = json.loads(row['items_json'])
            for item in items:
                st.write(f"- {item['name']} ({item.get('portion', '')}): {item['calories']} kcal")

with tab2:
    st.subheader("📈 熱量攝取趨勢")
    conn = sqlite3.connect('tracker.db')
    df = pd.read_sql_query(f"SELECT date, total_calories FROM food_logs WHERE user='{user}'", conn)
    conn.close()
    if not df.empty:
        st.line_chart(df.set_index('date')['total_calories'])

with tab3:
    st.subheader(f"📊 InBody 紀錄 - {user}")
    # (此處與之前的 InBody 邏輯一致，紀錄會自動綁定到 Shing 或 Gloria 名下)
