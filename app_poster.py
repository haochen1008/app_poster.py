import streamlit as st
import requests

# 页面配置
st.set_page_config(page_title="房源海报总结器", layout="wide", page_icon="🖼️")

# DeepSeek 配置
API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
API_URL = "https://api.deepseek.com/chat/completions"

def call_ai_poster(desc):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    # 针对发给客户的专业 Prompt
    prompt = f"""
    你是一个专业的英国房产中介。请根据以下房源描述，为客户写一份简洁、专业且美观的中文房源总结。
    
    【格式要求】：
    1. 🏠【房源概览】：一句话总结卖点。
    2. 📍【地理位置】：简述地段、邮编、最近地铁站及周边大学（如KCL, LSE, UCL等）。
    3. 🏡【内饰详情】：房型、家具情况、采光及公寓配套（如健身房、前台）。
    4. 💰【租金详情】：明确标注月租(PCM)并计算出周租(PW = 月租 / 4.33)。
    5. 📅【入住时间】：明确标出。
    
    禁止出现任何解释性字眼或原文中没有的虚假信息。
    
    描述原文：
    {desc}
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"生成失败，请检查余额或网络。错误信息：{str(e)}"

# --- 界面展示 ---
st.title("🖼️ 房源海报总结器")
st.markdown("---")
st.info("💡 操作指南：由于Rightmove限制自动抓取，请手动粘贴描述并上传图片，AI将为您生成专业的客户总结。")

# 左右布局
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("1️⃣ 基础素材")
    poster_desc = st.text_area("粘贴房源描述 (Description)", height=250, placeholder="从Rightmove复制Description到这里...")
    uploaded_pics = st.file_uploader("2️⃣ 上传房源照片 (可多选)", accept_multiple_files=True, type=['jpg', 'png', 'jpeg'])

with col_right:
    st.subheader("3️⃣ AI 总结结果")
    if st.button("✨ 生成总结文案"):
        if poster_desc:
            with st.spinner('AI 正在为您梳理房源要点...'):
                result = call_ai_poster(poster_desc)
                st.success("生成成功！")
                # 使用 code 组件方便一键复制
                st.code(result, language="text")
        else:
            st.warning("请先粘贴房源描述内容内容")

# 图片预览区
if uploaded_pics:
    st.markdown("---")
    st.subheader("📸 精选图片预览")
    img_cols = st.columns(3)
    for idx, file in enumerate(uploaded_pics):
        with img_cols[idx % 3]:
            st.image(file, use_container_width=True, caption=f"图片 {idx+1}")

st.markdown("---")
st.caption("建议：将此页面生成的文案配合上传的图片一起发送给客户。")
