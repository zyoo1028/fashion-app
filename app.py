import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import random

# --- 1. 系統全域設定 (System Config) ---
st.set_page_config(page_title="Apex Fashion OS", layout="wide", page_icon="✨")

# --- 自定義 CSS (精品級 UI) ---
st.markdown("""
    <style>
    /* 隱藏雜項 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 按鈕風格優化 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* 儀表板卡片 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* 圖片卡片風格 */
    .product-card {
        background-color: white;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線邏輯 (API 防彈裝甲) ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=3600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到金鑰 (Secrets)。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

# 自動重試裝飾器 (Auto-Retry Decorator)
# 這是 V9.0 的核心：遇到錯誤會自動重試 3 次，防止紅字崩潰
def safe_api_call(func, *args, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1.5) # 等待 1.5 秒後重試
                continue
            else:
                st.error(f"連線不穩定，請稍後再試。錯誤代碼: {e}")
                return None

@st.cache_resource(ttl=3600)
def init_db():
    client = get_connection()
    try:
        # ⚠️⚠️⚠️ 主理人：請務必填入您的 Google 試算表網址 ⚠️⚠️⚠️
        sh = client.open_by_url("https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493")
        return sh
    except Exception as e:
        st.error(f"資料庫連線失敗: {e}")
        return None

# --- 3. 數據處理核心 ---
def get_data_safe(ws):
    data = safe_api_call(ws.get_all_records)
    if data is None: return pd.DataFrame()
    return pd.DataFrame(data)

def log_event(ws_logs, user, action, detail):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_api_call(ws_logs.append_row, [timestamp, user, action, detail])

# --- 4. 主程式 ---
def main():
    # Session State 初始化
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = ""

    sh = init_db()
    if not sh: st.stop()

    # 自動檢查並修復欄位 (加入 Cost 成本欄位)
    try:
        ws_items = sh.worksheet("Items")
        headers = ws_items.row_values(1)
        required_headers = ["SKU", "Name", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
        
        # 如果發現缺欄位，自動補上
        if len(headers) < len(required_headers):
            for i, h in enumerate(required_headers):
                if i >= len(headers) or headers[i] != h:
                    ws_items.update_cell(1, i+1, h)
    except:
        ws_items = sh.add_worksheet(title="Items", rows="100", cols="20")
        ws_items.append_row(["SKU", "Name", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"])

    try:
        ws_logs = sh.worksheet("Logs")
    except:
        ws_logs = sh.add_worksheet(title="Logs", rows="1000", cols="5")
        ws_logs.append_row(["Timestamp", "User", "Action", "Details"])

    # --- A. 登入介面 (時尚版) ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center;'>✨ APEX FASHION</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Professional Inventory Management</p>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                user_input = st.text_input("Access ID / Name")
                submit = st.form_submit_button("Log In", type="primary")
                
                if submit:
                    if user_input.strip():
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = user_input
                        log_event(ws_logs, user_input, "登入", "Session Start")
                        st.rerun()
                    else:
                        st.warning("請輸入姓名")
        return

    # --- B. 系統主介面 ---
    
    # 讀取數據
    df = get_data_safe(ws_items)
    
    # 資料清洗與防呆
    cols = ["SKU", "Name", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols:
        if c not in df.columns: df[c] = ""
    
    # 數值轉型
    for num_col in ['Qty', 'Price', 'Cost']:
        df[num_col] = pd.to_numeric(df[num_col], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    # 側邊欄
    with st.sidebar:
        st.markdown(f"### Hi, {st.session_state['user_name']}")
        st.write("身份: 管理員 (Admin)")
        if st.button("登出 (Logout)"):
            st.session_state['logged_in'] = False
            st.rerun()
        st.divider()
        st.link_button("📂 Google Database", sh.url)

    # --- 頂部儀表板 (Dashboard) ---
    # 計算利潤
    total_revenue = (df['Qty'] * df['Price']).sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    potential_profit = total_revenue - total_cost

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 總款式", f"{len(df)}", delta="Active")
    m2.metric("👕 總庫存", f"{df['Qty'].sum()}", delta="Units")
    m3.metric("💰 庫存市值", f"${total_revenue:,.0f}", help="所有商品以售價計算的總值")
    m4.metric("📈 潛在利潤", f"${potential_profit:,.0f}", delta_color="normal", help="售價 - 成本")
    
    st.markdown("---")

    # --- 功能分頁 ---
    tabs = st.tabs(["🖼️ 視覺畫廊 (Gallery)", "⚡ 快速作業 (POS)", "🛠️ 商品管理 (Admin)", "📝 紀錄 (Logs)"])

    # === Tab 1: 視覺畫廊 (V9.0 重點功能) ===
    with tabs[0]:
        c_search, c_filter = st.columns([3, 1])
        search = c_search.text_input("🔍 搜尋商品", placeholder="輸入名稱或編號...")
        stock_filter = c_filter.selectbox("篩選", ["全部顯示", "⚠️ 低庫存 (<5)", "✅ 庫存充足"])
        
        # 篩選邏輯
        display_df = df.copy()
        if search:
            display_df = display_df[display_df.apply(lambda x: search.lower() in str(x.values).lower(), axis=1)]
        if stock_filter == "⚠️ 低庫存 (<5)":
            display_df = display_df[display_df['Qty'] < 5]
        elif stock_filter == "✅ 庫存充足":
            display_df = display_df[display_df['Qty'] >= 5]

        # 畫廊顯示 (每行 4 張卡片)
        if display_df.empty:
            st.info("沒有符合的商品")
        else:
            # 遍歷商品顯示
            cols_per_row = 4
            rows = [display_df.iloc[i:i+cols_per_row] for i in range(0, len(display_df), cols_per_row)]
            
            for row in rows:
                cols = st.columns(cols_per_row)
                for index, (col, item) in enumerate(zip(cols, row.iterrows())):
                    item_data = item[1]
                    with col:
                        # 圖片處理
                        img_url = item_data['Image_URL'] if str(item_data['Image_URL']).startswith('http') else "https://via.placeholder.com/150?text=No+Image"
                        
                        st.markdown(f"""
                        <div class="product-card">
                            <img src="{img_url}" style="width:100%; height:150px; object-fit:cover; border-radius:5px;">
                            <h4 style="margin:10px 0 0 0;">{item_data['Name']}</h4>
                            <p style="color:gray; font-size:12px; margin:0;">{item_data['SKU']} ({item_data['Size']})</p>
                            <h3 style="color:#FF4B4B; margin:5px 0;">${item_data['Price']}</h3>
                            <div style="background-color:{'#ffebee' if item_data['Qty']<5 else '#e8f5e9'}; border-radius:4px; padding:2px;">
                                庫存: <b>{item_data['Qty']}</b>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    # === Tab 2: 快速作業 (POS 模式) ===
    with tabs[1]:
        c1, c2 = st.columns([1, 1])
        selected_item = None
        current_idx = None
        
        with c1:
            st.subheader("1. 掃描/選擇商品")
            # 建立選單標籤 (顯示 SKU + 名稱 + 尺寸)
            sku_options = df.apply(lambda x: f"{x['SKU']} | {x['Name']} ({x['Size']})", axis=1).tolist()
            select_label = st.selectbox("請選擇商品", ["請選擇..."] + sku_options)
            
            if select_label != "請選擇...":
                # 解析出 SKU
                target_sku = select_label.split(" | ")[0]
                selected_item = df[df['SKU'] == target_sku].iloc[0]
                current_idx = ws_items.find(target_sku).row
                
                # 顯示大圖與資訊
                img_url = selected_item['Image_URL'] if str(selected_item['Image_URL']).startswith('http') else ""
                if img_url: st.image(img_url, width=200)
                st.info(f"當前庫存: {selected_item['Qty']} 件")

        with c2:
            st.subheader("2. 執行變更")
            qty_change = st.number_input("數量", min_value=1, value=1)
            
            if selected_item is not None:
                col_in, col_out = st.columns(2)
                if col_in.button("📥 進貨入庫", type="secondary"):
                    new_q = int(selected_item['Qty']) + qty_change
                    safe_api_call(ws_items.update_cell, current_idx, 4, new_q) # 4=Qty
                    safe_api_call(ws_items.update_cell, current_idx, 7, str(datetime.now()))
                    log_event(ws_logs, st.session_state['user_name'], "進貨", f"{selected_item['SKU']} +{qty_change}")
                    st.success("入庫成功")
                    time.sleep(1)
                    st.rerun()

                if col_out.button("📤 銷售出庫", type="primary"):
                    if int(selected_item['Qty']) < qty_change:
                        st.error("庫存不足！")
                    else:
                        new_q = int(selected_item['Qty']) - qty_change
                        safe_api_call(ws_items.update_cell, current_idx, 4, new_q)
                        safe_api_call(ws_items.update_cell, current_idx, 7, str(datetime.now()))
                        log_event(ws_logs, st.session_state['user_name'], "銷售", f"{selected_item['SKU']} -{qty_change}")
                        st.success("出庫成功")
                        time.sleep(1)
                        st.rerun()

    # === Tab 3: 商品管理 (Excel 模式) ===
    with tabs[2]:
        st.info("💡 提示：在此頁面新增商品，支援成本設定。")
        
        with st.form("pro_add_form"):
            c1, c2, c3 = st.columns(3)
            n_sku = c1.text_input("SKU 編號", placeholder="T-001")
            n_name = c2.text_input("商品名稱", placeholder="經典白T")
            n_size = c3.selectbox("尺寸", ["F", "XS", "S", "M", "L", "XL"])
            
            c4, c5, c6 = st.columns(3)
            n_qty = c4.number_input("初始數量", 0)
            n_cost = c5.number_input("成本價 (Cost)", 0)
            n_price = c6.number_input("銷售價 (Price)", 0)
            
            n_img = st.text_input("圖片連結 (URL)")
            
            if st.form_submit_button("建立新商品"):
                if n_sku in df['SKU'].tolist():
                    st.error("SKU 已存在")
                elif n_sku and n_name:
                    # 寫入包含 Cost 的資料
                    new_row = [n_sku, n_name, n_size, n_qty, n_price, n_cost, str(datetime.now()), n_img]
                    safe_api_call(ws_items.append_row, new_row)
                    log_event(ws_logs, st.session_state['user_name'], "新增", n_sku)
                    st.success("建立成功")
                    time.sleep(1)
                    st.rerun()
        
        st.divider()
        st.markdown("### 🗑️ 商品刪除區")
        del_sku = st.selectbox("選擇要刪除的商品", ["請選擇..."] + df['SKU'].tolist())
        if del_sku != "請選擇...":
            if st.button("確認永久刪除"):
                r = ws_items.find(del_sku).row
                safe_api_call(ws_items.delete_rows, r)
                log_event(ws_logs, st.session_state['user_name'], "刪除", del_sku)
                st.success("已刪除")
                time.sleep(1)
                st.rerun()

    # === Tab 4: 紀錄 ===
    with tabs[3]:
        logs = get_data_safe(ws_logs)
        st.dataframe(logs, use_container_width=True)

if __name__ == "__main__":
    main()
