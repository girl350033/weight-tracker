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
                            result_text = result_text.split("```")[1].split("```")[0].strip()
                            
                        parsed = json.loads(result_text)
                        
                        for item in parsed.get("items", []):
                            st.session_state.current_foods.append({
                                "name": item.get("name", "未知食物"),
                                "portion": item.get("portion", ""),
                                "calories": int(item.get("calories", 0)),
                                "protein": int(item.get("protein", 0)),
                                "fat": int(item.get("fat", 0)),
                                "carbs": int(item.get("carbs", 0))
                            })
                        st.success("AI 辨識完成！已加入下方清單。")
                except Exception as e:
                    st.error(f"辨識解析失敗，請確認圖片清晰度或稍後再試。錯誤細節：{e}")

    if st.button("➕ 手動新增飲食項目"):
        st.session_state.current_foods.append({"name": "", "portion": "", "calories": 0, "protein": 0, "fat": 0, "carbs": 0})

    total_intake = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0
    
    for idx, food in enumerate(list(st.session_state.current_foods)):
        cols = st.columns([2, 2, 1, 1, 1])
        with cols[0]:
            st.session_state.current_foods[idx]["name"] = st.text_input(f"名稱 {idx+1}", value=food["name"], key=f"f_name_{idx}")
        with cols[1]:
            st.session_state.current_foods[idx]["portion"] = st.text_input(f"份量 {idx+1}", value=food["portion"], key=f"f_port_{idx}")
        with cols[2]:
            st.session_state.current_foods[idx]["calories"] = st.number_input(f"熱量 {idx+1}", value=int(food["calories"]), key=f"f_cal_{idx}")
        with cols[3]:
            st.session_state.current_foods[idx]["protein"] = st.number_input(f"蛋白 {idx+1}", value=int(food["protein"]), key=f"f_pro_{idx}")
        with cols[4]:
            if st.button("🗑️", key=f"del_f_{idx}"):
                st.session_state.current_foods.pop(idx)
                st.rerun()
                
        total_intake += food["calories"]
        total_protein += food["protein"]
        total_fat += food["fat"]
        total_carbs += food["carbs"]

    st.info(f"今日飲食總熱量：**{total_intake} kcal** （蛋白質 {total_protein}g · 脂肪 {total_fat}g · 碳水 {total_carbs}g）")

    st.markdown("---")
    st.markdown("### 🏋️ 運動消耗熱量")
    ex_name = st.text_input("運動項目 (例如 F45 訓練、跑步)", value="")
    ex_cal = st.number_input("消耗熱量 (kcal)", min_value=0, value=0, step=10)

    if st.button("💾 儲存今日紀錄", type="primary"):
        st.success("已成功儲存今日紀錄！")

with tab2:
    st.subheader("📊 數據趨勢圖表")
    st.write("這裡將會呈現您的體重變化與熱量攝取/消耗趨勢。")

with tab3:
    st.subheader("📈 InBody 身體組成與基礎代謝率紀錄")
    st.caption("建議每 1-2 個月測量一次並在此建檔")
    
    ib_date = st.date_input("InBody 量測日期", key="ib_date")
    ib_weight = st.number_input("InBody 體重 (kg)", min_value=30.0, max_value=200.0, value=60.0, step=0.1, key="ib_w")
    ib_bf = st.number_input("體脂率 (%)", min_value=1.0, max_value=70.0, value=20.0, step=0.1, key="ib_bf")
    ib_muscle = st.number_input("骨骼肌重 (kg)", min_value=10.0, max_value=100.0, value=25.0, step=0.1, key="ib_mu")
    ib_visceral = st.number_input("內臟脂肪等級", min_value=1, max_value=30, value=5, step=1, key="ib_vis")
    ib_bmr = st.number_input("基礎代謝率 BMR (kcal)", min_value=500, max_value=4000, value=1400, step=10, key="ib_bmr")
    
    if st.button("💾 儲存 InBody 紀錄", type="primary"):
        inbody_item = {
            "date": str(ib_date),
            "weight": ib_weight,
            "body_fat": ib_bf,
            "muscle": ib_muscle,
            "visceral_fat": ib_visceral,
            "bmr": ib_bmr
        }
        if user not in st.session_state.inbody:
            st.session_state.inbody[user] = []
        st.session_state.inbody[user].append(inbody_item)
        st.success("InBody 數據已成功儲存！")

    st.markdown("---")
    st.subheader("📋 InBody 歷史紀錄列表")
    user_inbody_list = st.session_state.inbody.get(user, [])
    if not user_inbody_list:
        st.info("尚無 InBody 紀錄。")
    else:
        for idx, item in enumerate(reversed(user_inbody_list)):
            st.markdown(f"**日期：{item['date']}**")
            st.write(f"體重: {item['weight']} kg | 體脂: {item['body_fat']}% | 骨骼肌: {item['muscle']} kg | 內臟脂肪: {item['visceral_fat']} | **BMR: {item['bmr']} kcal**")
            st.markdown("---")
