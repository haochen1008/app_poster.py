import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import io
import base64 # 用于图片展示

st.set_page_config(page_title="房源海报生成器", layout="wide", page_icon="🖼️")

# --- DeepSeek API 配置 ---
API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
API_URL = "https://api.deepseek.com/chat/completions"

def summarize_property_with_ai(en_desc, url, image_urls):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    # 构建 AI 指令：总结并生成海报内容
    prompt = f"""
    你是一个专业的英国房产中介。请根据以下Rightmove房源信息，为客户生成一份精美、简洁的“房源海报文案”。
    
    【输出格式要求 - 非常重要】：
    请严格按照以下结构输出，并在每个模块前加上对应的Emoji。
    
    🏠【房源概览】:
    用一句话总结房源最大亮点。

    📍【地理位置】:
    简述地段优势、附近地标、交通。

    🏡【房源详情】:
    包括房型、装修、采光、主要设施。

    💰【租金/售价】:
    明确标示租金（自动换算周租PW和月租PCM），或其他价格信息。

    📅【入住时间】:
    明确标示。

    🔗【Rightmove链接】:
    {url}
    
    [精选图片说明]: (请在下方自行选择3-5张图片发送给客户)
    
    原始英文描述：
    {en_desc}
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5, # 总结性任务，降低temperature提高稳定性
        "max_tokens": 1000
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content']

def fetch_rightmove_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=20) # 增加超时时间
        res.raise_for_status() # 检查HTTP错误
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 提取描述
        desc_tag = soup.find('div', {'class': 're-feeds-description'}) or soup.find('div', {'itemprop': 'description'})
        description = desc_tag.get_text(separator="\n").strip() if desc_tag else "未能自动抓取到描述，请手动复制粘贴。"
        
        # 提取图片：优先找高分辨率图
        # Rightmove 图片通常在一个JS对象里，或者通过data-src加载
        # 这里尝试抓取常见的'img'标签，并优化路径
        img_tags = soup.find_all('img', {'itemprop': 'contentUrl'}) # 尝试抓取大图
        if not img_tags: # 如果没有 itemprop='contentUrl'，尝试其他常见的图片类名
            img_tags = soup.find_all('img', class_=lambda x: x and ('_image_' in x or 'PhotoView' in x))
        
        images = []
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src and "rightmove.co.uk/property-images" in src:
                # 尝试获取更高分辨率的图片
                src = src.replace("/24_16_IMG_00_", "/1024x768_IMG_00_") # 常见替换规则
                images.append(src)
        
        # 进一步过滤重复和太小的图片
        unique_images = list(dict.fromkeys(images)) # 去重
        final_images = [img for img in unique_images if "1024x768" in img or "800x600" in img or "480x320" in img]
        
        # 如果还是没抓到，尝试找脚本里的JSON数据
        if not final_images and description == "未能自动抓取到描述，请手动复制粘贴。":
            script_tag = soup.find('script', string=lambda text: text and 'window.__INITIAL_STATE__' in text)
            if script_tag:
                json_data = script_tag.string.split('window.__INITIAL_STATE__ = ')[1].split(';\n')[0]
                state = json.loads(json_data)
                # 尝试从 state 中提取描述和图片
                if 'propertyData' in state and 'property' in state['propertyData']:
                    description = state['propertyData']['property'].get('description', description)
                    if 'photos' in state['propertyData']['property']:
                        for photo in state['propertyData']['property']['photos']:
                            if 'url' in photo:
                                final_images.append(photo['url'])

        return description, final_images, "" # 返回描述, 图片列表, 错误信息
    
    except requests.exceptions.RequestException as e:
        return "抓取失败", [], f"网络错误或Rightmove拒绝访问，请稍后再试或手动复制描述。"
    except Exception as e:
        return "抓取失败", [], f"解析网页内容失败，可能是Rightmove页面结构有变。"

# --- 页面 UI ---
st.title("🖼️ 房源海报生成器")
st.info("💡 输入Rightmove链接，AI自动总结要点，并推荐精选图片。")

# 第一步：输入链接
rm_url = st.text_input("粘贴 Rightmove 房源链接：", placeholder="https://www.rightmove.co.uk/properties/...")

# 第二步：抓取信息
if st.button("🔍 抓取并生成海报"):
    if not rm_url:
        st.error("请输入 Rightmove 链接！")
    else:
        with st.spinner("正在从 Rightmove 抓取数据并交给 AI 总结..."):
            desc_from_rm, images_from_rm, error_message = fetch_rightmove_data(rm_url)
            
            if error_message:
                st.error(f"❌ 抓取失败：{error_message}")
                st.text_area("您也可以手动粘贴描述内容：", value=desc_from_rm, height=150)
                st.session_state['processed_desc'] = desc_from_rm
                st.session_state['processed_images'] = []
            else:
                st.success("✅ 房源信息抓取成功！")
                st.session_state['processed_desc'] = desc_from_rm
                st.session_state['processed_images'] = images_from_rm

# --- 显示抓取结果和 AI 总结 ---
if 'processed_desc' in st.session_state and st.session_state['processed_desc']:
    st.markdown("---")
    st.subheader("📝 AI 总结与推荐文案")
    
    # 防止因抓取失败导致AI处理空字符串
    if st.session_state['processed_desc'] == "未能自动抓取到描述，请手动复制粘贴。":
        st.warning("⚠️ 描述未能自动抓取，请手动粘贴到下方文本框中，再点击生成。")
        final_desc_for_ai = st.text_area("手动粘贴 Rightmove 描述：", value="", height=150, key="manual_desc")
    else:
        final_desc_for_ai = st.session_state['processed_desc']
        st.text_area("已自动提取的描述（可在此修改）：", value=final_desc_for_ai, height=150, key="auto_desc")

    if st.button("✨ 生成海报文案"):
        if not final_desc_for_ai or final_desc_for_ai == "未能自动抓取到描述，请手动复制粘贴。":
            st.error("请先提供房源描述内容！")
        else:
            with st.spinner("AI 正在提炼海报内容..."):
                try:
                    poster_content = summarize_property_with_ai(final_desc_for_ai, rm_url, st.session_state.get('processed_images', []))
                    st.session_state['poster_text'] = poster_content
                    st.success("海报文案生成成功！")
                except Exception as e:
                    st.error(f"AI 生成失败：{str(e)}。请检查 DeepSeek 余额或 Key 是否正确。")

    if 'poster_text' in st.session_state and st.session_state['poster_text']:
        st.markdown("---")
        st.subheader("💌 发送给客户的文案（可一键复制）")
        st.info("点击下方文本框右上角按钮即可复制，建议配合下方精选图片发送。")
        st.code(st.session_state['poster_text'], language="text")

    # --- 图片选择区 ---
    st.markdown("---")
    st.subheader("📸 精选图片 (建议选3-5张)")
    
    if 'processed_images' in st.session_state and st.session_state['processed_images']:
        num_images = len(st.session_state['processed_images'])
        st.write(f"共检测到 {num_images} 张图片。")
        
        # 显示图片，并提供下载选项
        cols = st.columns(3) # 每行显示3张
        for i, img_url in enumerate(st.session_state['processed_images'][:12]): # 最多展示前12张
            with cols[i % 3]:
                st.image(img_url, use_column_width=True)
                # st.download_button(
                #     label="下载此图",
                #     data=requests.get(img_url).content,
                #     file_name=f"property_image_{i+1}.jpg",
                #     mime="image/jpeg"
                # )
    else:
        st.warning("未抓取到图片，或图片加载失败。")
