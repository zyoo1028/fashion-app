import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import requests
import plotly.express as px  # 引入專業圖表庫

# --- 1. 系統全域設定 (System Config) ---
st.set_page_config(page_title="IFUKUK 企業核心系統", layout="wide", page_icon="🌐")

# --- ⚠️⚠️⚠️ 設定區 (請在此填入您的資料) ⚠️⚠️⚠️ ---

# 1. Google Sheet 網址 (請填入您原本那個成功的試算表網址)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"

# 2. ImgBB API Key (請填入剛剛搜尋並複製到的那串鑰匙)
IMGBB_API_KEY = "37c1f9eb05ec7d4e51c23849d6921298" 

# ---------------------------------------------------

# --- 自定義 CSS (旗艦級 UI) ---
st.markdown("""
    <style>
    /* 隱藏預設雜項 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 登入標題字體優化 */
    .brand-title {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-weight: 800;
        font-size: 3rem;
        color: #1E1E1E;
        text-align: center;
        letter-spacing: 2px;
    }
    
    /* 專業按鈕風格 */
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        height: 3em;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* 儀表板卡片 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #f0f0f0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* 產品卡片 */
    .product-card {
        background: white;
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線邏輯 (Brain) ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=3600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰，請檢查 Streamlit 設定。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def safe_api_call(func, *args, **kwargs):
    """企業級 API 防彈重試機制"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                st.error(f"連線異常 (Error: {e})，請檢查網路或稍後再試。")
                return None

@st.cache_resource(ttl=3600)
def init_db():
    client = get_connection()
    try:
        sh = client.open_by_url(GOOGLE_SHEET_URL)
        return sh
    except Exception as e:
        st.error(f"無法連結資料庫，請檢查網址是否正確。錯誤: {e}")
        return None

# --- 3. 圖片上傳模組 (ImgBB API) ---
def upload_image_to_imgbb(image_file):
    """將圖片上傳至 ImgBB 並取得網址"""
    if not IMGBB_API_KEY or "請將您的" in IMGBB_API_KEY:
        st.warning("⚠️ 請先在代碼中填入 ImgBB API Key 才能使用上傳功能。")
        return None
    
    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": IMGBB_API_KEY,
            "image": image_file.getvalue()
        }
        response = requests.post(url, payload)
        if response.status_code == 200:
            return response.json()["data"]["url"]
        else:
            st.error("圖片上傳失敗，請檢查 API Key 或網路。")
            return None
    except Exception as e:
        st.error(f"上傳錯誤: {e}")
        return None

# --- 4. 數據與日誌模組 ---
def get_data_safe(ws):
    data = safe_api_call(ws.get_all_records)
    if data is None: return pd.DataFrame()
    return pd.DataFrame(data)

def log_event(ws_logs, user, action, detail):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_api_call(ws_logs.append_row, [timestamp, user, action, detail])

# --- 5. 主程式 ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = ""

    sh = init_db()
    if not sh: st.stop()

    # 自動修復與建置資料表
    try:
        ws_items = sh.worksheet("Items")
        # 確保有 Cost (成本) 和 Category (分類) 等高階欄位
        headers = ws_items.row_values(1)
        required_headers = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
        if len(headers) < len(required_headers):
            for i, h in enumerate(required_headers):
                if i >= len(headers) or headers[i] != h:
                    ws_items.update_cell(1, i+1, h)
    except:
        ws_items = sh.add_worksheet(title="Items", rows="100", cols="20")
        ws_items.append_row(["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"])

    try:
        ws_logs = sh.worksheet("Logs")
    except:
        ws_logs = sh.add_worksheet(title="Logs", rows="1000", cols="5")
        ws_logs.append_row(["Timestamp", "User", "Action", "Details"])

    # --- A. 品牌登入入口 (IFUKUK BRAND PORTAL) ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 class='brand-title'>IFUKUK</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #666; font-size: 1.1em;'>Global Inventory Intelligence</p>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.form("login"):
                user = st.text_input("Access Identity", placeholder="輸入您的姓名...")
                if st.form_submit_button("ENTER SYSTEM", type="primary"):
                    if user:
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = user
                        log_event(ws_logs, user, "系統登入", "Session Started")
                        st.rerun()
                    else:
                        st.warning("Identification Required")
        return

    # --- B. 企業戰情中心 ---
    
    # 讀取資料
    df = get_data_safe(ws_items)
    
    # 資料清洗
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols:
        if c not in df.columns: df[c] = ""
    
    for num_col in ['Qty', 'Price', 'Cost']:
        df[num_col] = pd.to_numeric(df[num_col], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    # 側邊導航
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        st.caption("Administrator Access")
        st.divider()
        if st.button("🔒 安全登出"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        st.link_button("📊 原始資料庫 (Excel)", sh.url)

    # --- 1. 高階儀表板 (BI Dashboard) ---
    st.markdown("### 🚀 營運戰情室 (Dashboard)")
    
    # 核心指標
    total_rev = (df['Qty'] * df['Price']).sum()
    total_cost_val = (df['Qty'] * df['Cost']).sum()
    profit = total_rev - total_cost_val
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("📦 活躍款式", f"{len(df)} 款")
    kpi2.metric("👕 總庫存量", f"{df['Qty'].sum()} 件")
    kpi3.metric("💰 庫存總市值", f"${total_rev:,.0f}")
    kpi4.metric("📈 預估淨利", f"${profit:,.0f}", delta="Profit", delta_color="normal")
    
    # 圖表分析區 (V10 新功能)
    if not df.empty:
        with st.expander("📊 點此展開/收合 詳細庫存圖表分析", expanded=True):
            chart1, chart2 = st.columns(2)
            with chart1:
                # 庫存數量前 10 名
                top_stock = df.sort_values(by='Qty', ascending=False).head(10)
                fig_qty = px.bar(top_stock, x='Name', y='Qty', title='🔥 庫存數量 TOP 10', color='Qty', text='Qty')
                st.plotly_chart(fig_qty, use_container_width=True)
            
            with chart2:
                # 尺寸分佈
                size_dist = df.groupby('Size')['Qty'].sum().reset_index()
                fig_size = px.pie(size_dist, values='Qty', names='Size', title='📏 尺寸庫存佔比', hole=0.4)
                st.plotly_chart(fig_size, use_container_width=True)
    
    st.divider()

    # --- 2. 功能分頁系統 ---
    # 改名為更專業的稱呼
    tab_gallery, tab_pos, tab_admin, tab_logs = st.tabs([
        "🧥 數位樣品室 (Showroom)", 
        "⚡ 進銷存戰情 (POS & Ops)", 
        "🛠️ 商品與成本管理 (Admin)", 
        "📝 稽核日誌 (Audit)"
    ])

    # === Tab 1: 數位樣品室 (Showroom) ===
    with tab_gallery:
        c_search, c_sort = st.columns([3, 1])
        search_txt = c_search.text_input("🔍 關鍵字搜尋 (SKU/名稱)", placeholder="輸入...")
        filter_opt = c_sort.selectbox("庫存狀態", ["全部", "⚠️ 缺貨警示 (<5)", "✅ 充足"])
        
        show_df = df.copy()
        if search_txt:
            show_df = show_df[show_df.apply(lambda x: search_txt.lower() in str(x.values).lower(), axis=1)]
        if filter_opt == "⚠️ 缺貨警示 (<5)":
            show_df = show_df[show_df['Qty'] < 5]
        
        if show_df.empty:
            st.info("查無商品")
        else:
            # 專業網格顯示
            cols_count = 4
            rows = [show_df.iloc[i:i+cols_count] for i in range(0, len(show_df), cols_count)]
            for row in rows:
                cols = st.columns(cols_count)
                for idx, (col, item) in enumerate(zip(cols, row.iterrows())):
                    val = item[1]
                    with col:
                        img = val['Image_URL'] if str(val['Image_URL']).startswith('http') else "https://via.placeholder.com/300x300.png?text=No+Image"
                        status_color = "#ffebee" if val['Qty'] < 5 else "#e8f5e9"
                        st.markdown(f"""
                        <div class="product-card">
                            <div style="height:160px; overflow:hidden; border-radius:8px; margin-bottom:8px;">
                                <img src="{img}" style="width:100%; height:100%; object-fit:cover;">
                            </div>
                            <div style="font-weight:bold; font-size:1.1em; margin-bottom:4px;">{val['Name']}</div>
                            <div style="color:#666; font-size:0.9em; display:flex; justify-content:space-between;">
                                <span>{val['SKU']}</span>
                                <span style="background:#eee; padding:2px 6px; border-radius:4px;">{val['Size']}</span>
                            </div>
                            <div style="margin-top:8px; display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:1.2em; color:#d32f2f; font-weight:bold;">${val['Price']}</span>
                                <span style="background:{status_color}; padding:2px 8px; border-radius:4px; font-weight:bold;">Q: {val['Qty']}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    # === Tab 2: 進銷存戰情 (POS) ===
    with tab_pos:
        # 分割為左右戰區，避免混淆
        col_select, col_action = st.columns([1, 1.2])
        
        target_item = None
        curr_row = None
        
        with col_select:
            st.subheader("1. 鎖定商品")
            sku_list = df.apply(lambda x: f"{x['SKU']} | {x['Name']} ({x['Size']})", axis=1).tolist()
            select_sku = st.selectbox("請選擇或輸入搜尋...", ["請選擇..."] + sku_list)
            
            if select_sku != "請選擇...":
                real_sku = select_sku.split(" | ")[0]
                target_item = df[df['SKU'] == real_sku].iloc[0]
                curr_row = ws_items.find(real_sku).row
                
                # 顯示商品詳情卡
                st.success(f"已鎖定: {target_item['Name']}")
                st.info(f"當前庫存: {target_item['Qty']} | 售價: ${target_item['Price']}")
                if str(target_item['Image_URL']).startswith('http'):
                    st.image(target_item['Image_URL'], width=200)

        with col_action:
            st.subheader("2. 執行交易")
            
            if target_item is not None:
                op_qty = st.number_input("數量", min_value=1, value=1)
                note = st.text_input("交易備註 (選填)", placeholder="例如: VIP折扣, 補貨入庫...")
                
                # 使用 Tabs 分開 進貨與出貨，防止按錯
                action_tab1, action_tab2 = st.tabs(["📥 進貨入庫 (Inbound)", "📤 銷售出庫 (Sales)"])
                
                with action_tab1:
                    if st.button("確認進貨 (+)", type="secondary", use_container_width=True):
                        new_q = int(target_item['Qty']) + op_qty
                        safe_api_call(ws_items.update_cell, curr_row, 5, new_q) # 5=Qty
                        safe_api_call(ws_items.update_cell, curr_row, 8, str(datetime.now())) # 8=Time
                        log_event(ws_logs, st.session_state['user_name'], "進貨", f"{real_sku} +{op_qty} | {note}")
                        st.success(f"進貨成功！庫存更新為: {new_q}")
                        time.sleep(1)
                        st.rerun()
                        
                with action_tab2:
                    if st.button("確認銷售 (-)", type="primary", use_container_width=True):
                        if int(target_item['Qty']) < op_qty:
                            st.error("❌ 庫存不足，無法出貨！")
                        else:
                            new_q = int(target_item['Qty']) - op_qty
                            safe_api_call(ws_items.update_cell, curr_row, 5, new_q)
                            safe_api_call(ws_items.update_cell, curr_row, 8, str(datetime.now()))
                            log_event(ws_logs, st.session_state['user_name'], "銷售", f"{real_sku} -{op_qty} | {note}")
                            st.balloons() # 銷售成功放氣球慶祝
                            st.success(f"銷售成功！庫存更新為: {new_q}")
                            time.sleep(1)
                            st.rerun()
            else:
                st.caption("請先在左側選擇商品...")

    # === Tab 3: 商品管理 (Admin) ===
    with tab_admin:
        with st.expander("➕ 新增商品 (含圖片上傳)", expanded=True):
            with st.form("new_item"):
                c1, c2 = st.columns(2)
                n_sku = c1.text_input("SKU 編號", placeholder="例如: T-888")
                n_name = c2.text_input("商品名稱")
                
                c3, c4, c5 = st.columns(3)
                n_cat = c3.text_input("分類", placeholder="上衣/褲子/配件")
                n_size = c4.selectbox("尺寸", ["F", "XS", "S", "M", "L", "XL"])
                n_qty = c5.number_input("初始數量", 0)
                
                c6, c7 = st.columns(2)
                n_cost = c6.number_input("進貨成本 (Cost)", 0)
                n_price = c7.number_input("銷售單價 (Price)", 0)
                
                st.markdown("---")
                st.markdown("📷 **圖片設定** (二選一)")
                # V10 新功能：直接上傳
                up_file = st.file_uploader("直接上傳圖片 (推薦)", type=['png', 'jpg', 'jpeg'])
                n_url_manual = st.text_input("或是貼上圖片網址")
                
                if st.form_submit_button("建立商品資料"):
                    if n_sku and n_name:
                        if n_sku in df['SKU'].tolist():
                            st.error("SKU 已存在！")
                        else:
                            # 處理圖片
                            final_img_url = ""
                            if up_file:
                                with st.spinner("圖片上傳雲端中..."):
                                    final_img_url = upload_image_to_imgbb(up_file)
                                    if not final_img_url: st.stop()
                            elif n_url_manual:
                                final_img_url = n_url_manual
                            
                            # 寫入資料
                            new_row = [n_sku, n_name, n_cat, n_size, n_qty, n_price, n_cost, str(datetime.now()), final_img_url]
                            safe_api_call(ws_items.append_row, new_row)
                            log_event(ws_logs, st.session_state['user_name'], "建立新品", f"{n_sku} {n_name}")
                            st.success("✨ 商品建立成功！")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("SKU 和 名稱 為必填！")

        st.markdown("---")
        with st.expander("🗑️ 刪除商品 / 🛠️ 數據修正"):
            d_sku = st.selectbox("選擇要刪除或修正的商品", ["請選擇..."] + df['SKU'].tolist())
            if d_sku != "請選擇...":
                if st.button("確認永久刪除此商品", type="primary"):
                    r = ws_items.find(d_sku).row
                    safe_api_call(ws_items.delete_rows, r)
                    log_event(ws_logs, st.session_state['user_name'], "刪除商品", d_sku)
                    st.success("已刪除")
                    time.sleep(1)
                    st.rerun()

    # === Tab 4: 稽核日誌 ===
    with tab_logs:
        st.dataframe(get_data_safe(ws_logs), use_container_width=True)

if __name__ == "__main__":
    main()
