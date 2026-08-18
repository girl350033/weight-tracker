import streamlit as st
import pandas as pd
import json
import base64

st.set_page_config(page_title="個人健康與體態追蹤器", page_icon="⚖️", layout="centered")

# 自訂放大字體與優化手機閱讀體驗的 CSS
st.markdown("""
    <style>
    /* 放大整體文字與表單標籤 */
    html, body, [class*="st-"] {
        font-size: 17px !important;
    }
    /* 放大標題 */
    h1 {
        font-size: 2.2rem !important;
    }
    h2 {
        font-size: 1.7rem !important;
    }
    h3 {
        font-size: 1.3rem !important;
    }
    /* 讓按鈕文字更大更易點擊 */
    .stButton button {
        font-size: 16px !important;
        font-weight: bold !important;
        padding: 0.5rem 1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚖️ 個人健康與體態追蹤系統")

# 使用者切換
user = st.radio("選擇使用者", ["Shing", "Gloria"], horizontal=True)

# 初始化 Session State 模擬資料儲存（加入完整防呆）
if "logs" not in st.session_state:
    st.session_state.logs = {}
if user not in st.session_state.logs:
    st.session_state.logs[user] = []

if "inbody" not in st.session_state:
    st.session_state.inbody = {}
if user not in st.session_state.inbody:
    st.session_state.inbody[user] = []

# 分頁籤
tab1, tab2, tab3 = st.tabs(["📝 每日紀錄", "📈 趨勢圖表", "📊 InBody 紀錄"])

with tab1:
    st.subheader("每日飲食與運動紀錄")
    
    date = st.date_input("日期")
    weight = st.number_input("今日體重 (kg)", min_value=30.0, max_value=200.0, value=60.0, step=0.1)
    
    st.markdown("---")
    st.markdown("### 🍔 飲食紀錄與 AI 拍照辨識")
    
    if "current_foods" not in st.session_state:
        st.session_state.current_foods = []

    uploaded_file = st.file_uploader("上傳食物照片進行 AI 辨識", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="上傳的食物照片", width=250)
        if st.button("✨ 開始 AI 辨識食物熱量"):
            with st.spinner("AI 正在分析食物與熱量中..."):
                try:
                    bytes_data = uploaded_file.getvalue()
                    base64_image = base64.b64encode(bytes_data).decode("utf-8")
                    
                    api_key = st.secrets.get("OPENAI_API_KEY", "")
                    if not api_key:
                        st.error("請先在 Streamlit Secrets 設定 OPENAI_API_KEY！")
                    else:
                        from openai import OpenAI
                        client = OpenAI(api_key=api_key)
                        
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": '你是營養估算助手。請觀察食物照片，辨識每一樣食物與熱量，務必只回傳標準 JSON 格式，不要包含任何額外文字或解釋，格式如下：\n{"items":[{"name":"食物名稱","portion":"份量","calories":100,"protein":10,"fat":5,"carbs":15}]}'},
                                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                    ]
                                }
                            ],
                            max_tokens=1000
                        )
                        
                        result_text = response.choices[0].message.content.strip()
                        
                        if "```json" in result_text:
                            result_text = result_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in result_text:
                            result_text = result_text.split("
