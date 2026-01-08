import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import requests
import plotly.express as px
import base64
import qrcode
import hashlib
from io import BytesIO

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK 企業資源中樞", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【MATRIX-V35.0 視覺核心與全能矩陣】
# ==========================================
st.markdown("""
    <style>
        /* --- 1. 全局基礎鎖定 (白底黑字) --- */
        .stApp { background-color: #FFFFFF !important; }
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; border-right: 1px solid #E5E7EB; }
        h1, h2, h3, h4, h5, h6, p, span, div, label, li { color: #000000 !important; }
        
        /* --- 2. 輸入框與顯示框 --- */
        input, textarea, .stTextInput > div > div, .stNumberInput > div > div {
            color: #000000 !important;
            background-color: #F3F4F6 !important;
            border-color: #D1D5DB !important;
        }
        div[data-baseweb="select"] > div {
            background-color: #F3F4F6 !important;
            color: #000000 !important;
            border-color: #D1D5DB !important;
        }

        /* --- 3. 彈出視窗修復 --- */
        div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #E5E7EB !important;
        }
        li[role="option"] { background-color: #FFFFFF !important; color: #000000 !important; }
        li[role="option"] div { color: #000000 !important; }
        li[role="option"]:hover, li[role="option"][aria-selected="true"] {
            background-color: #F3F4F6 !important; color: #000000 !important;
        }

        /* --- 4. 日期選擇器修復 --- */
        div[data-testid="stDateInput"] > div:nth-of-type(2) > div { background-color: #FFFFFF !important; }
        div[data-testid="stDateInput"] button[role="gridcell"] { color: #000000 !important; background-color: #FFFFFF !important; }
        div[data-testid="stDateInput"] button[role="gridcell"][aria-selected="true"] { background-color: #FF4B4B !important; color: #FFFFFF !important; }

        /* --- 5. Navbar & General --- */
        header[data-testid="stHeader"] { background-color: transparent !important; z-index: 9999; }
        .block-container { padding-top: 6rem !important; padding-bottom: 5rem !important; }

        .navbar-container {
            position: fixed; top: 50px; left: 0; width: 100%; z-index: 99;
            background-color: rgba(255, 255, 255, 0.98); backdrop-filter: blur(12px);
            padding: 12px 24px; border-bottom: 1px solid #e0e0e0;
            display: flex; justify-content: space-between; align-items: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        }

        /* --- 6. 卡片與按鈕 --- */
        .metric-card {
            background: linear-gradient(145deg, #ffffff, #f5f7fa); 
            border-radius: 16px; padding: 20px;
            border: 1px solid #e1e4e8; text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 10px;
        }
        .metric-value { font-size: 2rem; font-weight: 800; margin: 8px 0; color:#111 !important; }
        .metric-label { font-size: 0.85rem; letter-spacing: 1px; color:#666 !important; font-weight: 600; }
        
        .inv-card {
            background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px;
            padding: 10px; display: flex; flex-direction: column; align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: transform 0.2s;
        }
        .inv-card:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); border-color: #000; }
        .inv-img { width: 100%; height: 120px; object-fit: cover; border-radius: 8px; margin-bottom: 8px; }
        .inv-title { font-weight: bold; font-size: 14px; color: #111; margin-bottom: 4px; text-align: center; height: 2.4em; overflow: hidden; }
        .inv-sku { font-size: 11px; color: #666; margin-bottom: 4px; }
        .inv-price { font-weight: 800; color: #000; font-size: 15px; }
        .inv-qty { background: #F3F4F6; color: #000; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; margin-top: 4px; }
        .inv-badge-low { background: #FEE2E2; color: #991B1B; } 

        .history-card { display: flex; align-items: center; background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 10px; margin-bottom: 8px; }
        .history-img { width: 50px; height: 50px; border-radius: 5px; object-fit: cover; margin-right: 10px; }
        .history-tag { background: #ffe0b2; color: #e65100 !important; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; margin-left: auto; }

        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border:none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); background-color: #FFFFFF; color: #000000; border: 1px solid #E5E7EB; }
        .streamlit-expanderHeader p { color: #000000 !important; font-weight: 600; }
        .inventory-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 16px; padding: 10px 0; }
        
        [data-testid="stDataFrame"] { border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden; }
        
        /* 矩陣輸入區 */
        .batch-size-container {
            background-color: #f9fafb; padding: 15px; border-radius: 8px; border: 1px dashed #d1d5db; margin-bottom: 15px;
        }
        
        /* V35 提示 */
        .smart-detect {
            background-color: #d1fae5; color: #065f46; padding: 8px; border-radius: 6px; font-size: 0.85rem; margin-bottom: 10px;
            border: 1px solid #a7f3d0; display: flex; align-items: center;
        }
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
LINE_CHANNEL_ACCESS_TOKEN = "IaGvcTOmbMFW8wKEJ5MamxfRx7QVo0kX1IyCqwKZw0WX2nxAVYY7SsSh5vAJ0r+WBNvyjjiU8G3eYkL1nozqIOjjWMOKr/4ZtzUMRRf7JNJkk5V6jLpWc/EOkzvNGVPMh0zwH+wQD51tR3XWipUULwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U55199b00fb78da85bb285db6d00b6ff5"

# --- 核心連線 ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_data_safe(ws):
    max_retries = 3
    for i in range(max_retries):
        try:
            if ws is None: return pd.DataFrame()
            raw_data = ws.get_all_values()
            if not raw_data or len(raw_data) < 2: return pd.DataFrame()
            headers = raw_data[0]
            rows = raw_data[1:]
            df = pd.DataFrame(rows, columns=headers)
            return df
        except Exception:
            time.sleep(1)
            continue
    return pd.DataFrame()

@st.cache_resource(ttl=600)
def init_db():
    client = get_connection()
    try: return client.open_by_url(GOOGLE_SHEET_URL)
    except: return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title, rows=100, cols=20)
        ws.append_row(headers)
        return ws
    except: return None

# --- V35 專業工具模組 ---

@st.cache_data(ttl=3600)
def get_live_rate():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/CNY"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['rates']['TWD'], True
    except: pass
    return 4.50, False

def make_hash(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def check_hash(password, hashed_text):
    return make_hash(password) == hashed_text

def render_image_url(url_input):
    s = str(url_input).strip()
    if len(s) < 10 or not s.startswith("http"): return "https://i.ibb.co/W31w56W/placeholder.png"
    return s

def upload_image_to_imgbb(image_file):
    if not IMGBB_API_KEY: return None
    try:
        img_bytes = image_file.getvalue()
        b64_string = base64.b64encode(img_bytes).decode('utf-8')
        payload = {"key": IMGBB_API_KEY, "image": b64_string}
        response = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if response.status_code == 200: return response.json()["data"]["url"]
        return None
    except: return None

def send_line_push(message):
    if not LINE_CHANNEL_ACCESS_TOKEN: return "ERROR"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    data = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data); return "SUCCESS"
    except: return "ERROR"

def log_event(ws_logs, user, action, detail):
    try: ws_logs.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, detail])
    except: pass

def render_navbar(user_initial):
    current_date = datetime.now().strftime("%Y/%m/%d")
    rate = st.session_state.get('exchange_rate', 4.5)
    st.markdown(f"""
        <div class="navbar-container">
            <div style="display:flex; flex-direction:column;">
                <span style="font-size:18px; font-weight:900; color:#111;">IFUKUK GLOBAL</span>
                <span style="font-size:11px; color:#666; font-family:monospace;">{current_date} • Live: {rate}</span>
            </div>
            <div style="width:36px; height:36px; background:#111; color:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold;">
                {user_initial}
            </div>
        </div>
    """, unsafe_allow_html=True)

def generate_smart_style_code(category, existing_skus, custom_series=""):
    if custom_series:
        prefix = custom_series.upper().strip()
    else:
        prefix_map = {
            "上衣(Top)": "TOP", "褲子(Btm)": "BTM", "外套(Out)": "OUT", "套裝(Suit)": "SET",
            "鞋類(Shoe)": "SHOE", "包款(Bag)": "BAG", "帽子(Hat)": "HAT", "飾品(Acc)": "ACC", "其他(Misc)": "MSC"
        }
        prefix = prefix_map.get(category, "GEN")
        date_code = datetime.now().strftime("%y%m")
        prefix = f"{prefix}-{date_code}"
    
    current_prefix = f"{prefix}-"
    max_seq = 0
    for sku in existing_skus:
        if str(sku).startswith(current_prefix):
            try:
                rest = sku.replace(current_prefix, "") # 001-S or 001
                seq_part = rest.split("-")[0] 
                seq_num = int(seq_part)
                if seq_num > max_seq: max_seq = seq_num
            except: pass
    next_seq = str(max_seq + 1).zfill(3)
    return f"{current_prefix}{next_seq}"

# V33.2 漢化映射
COLUMN_MAPPING = {
    "SKU": "商品貨號", "Name": "商品名稱", "Category": "分類", "Size": "尺寸",
    "Qty": "庫存量", "Price": "售價(NTD)", "Cost": "成本(NTD)", "Last_Updated": "最後更新",
    "Safety_Stock": "安全庫存", "Orig_Currency": "原幣別", "Orig_Cost": "原幣成本", "Safe_Level": "警戒線"
}

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = ""
        st.session_state['user_role'] = ""
    
    if 'exchange_rate' not in st.session_state:
        live_rate, is_success = get_live_rate()
        st.session_state['exchange_rate'] = live_rate
        st.session_state['rate_source'] = "Live API" if is_success else "Manual/Default"

    sh = init_db()
    if not sh: st.error("Database Connection Failed"); st.stop()

    ws_items = get_worksheet_safe(sh, "Items", ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost"])
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    if not ws_items or not ws_logs or not ws_users: st.warning("Initializing..."); st.stop()

    # --- 登入頁面 ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-weight:900; font-size:2.5rem; margin-bottom:10px;'>IFUKUK</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>MATRIX ERP V35.0</div>", unsafe_allow_html=True)
            with st.form("login"):
                user_input = st.text_input("帳號 (ID)")
                pass_input = st.text_input("密碼 (Password)", type="password")
                if st.form_submit_button("登入 (LOGIN)", type="primary"):
                    users_df = get_data_safe(ws_users)
                    input_u = str(user_input).strip()
                    input_p = str(pass_input).strip()
                    
                    if users_df.empty and input_u == "Boss" and input_p == "1234":
                        hashed_pw = make_hash("1234")
                        ws_users.append_row(["Boss", hashed_pw, "Admin", "Active", str(datetime.now())])
                        st.success("Boss Created"); time.sleep(1); st.rerun()

                    if not users_df.empty:
                        users_df['Name'] = users_df['Name'].astype(str).str.strip()
                        target_user = users_df[(users_df['Name'] == input_u) & (users_df['Status'] == 'Active')]
                        if not target_user.empty:
                            stored_hash = target_user.iloc[0]['Password']
                            is_valid = check_hash(input_p, stored_hash) if len(stored_hash)==64 else (input_p == stored_hash)
                            if is_valid:
                                st.session_state['logged_in'] = True
                                st.session_state['user_name'] = input_u
                                st.session_state['user_role'] = target_user.iloc[0]['Role']
                                log_event(ws_logs, input_u, "Login", "登入成功")
                                st.rerun()
                            else: st.error("密碼錯誤")
                        else: st.error("帳號無效")
                    else: st.error("系統無資料")
        return

    # --- 主畫面 ---
    user_initial = st.session_state['user_name'][0].upper()
    render_navbar(user_initial)

    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost', 'Safety_Stock', 'Orig_Cost']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    df['Safe_Level'] = df['Safety_Stock'].apply(lambda x: 5 if x == 0 else x)
    df['SKU'] = df['SKU'].astype(str)
    
    users_df = get_data_safe(ws_users)
    staff_list = users_df['Name'].tolist() if not users_df.empty else []

    CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]
    SIZE_LIST = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL"]

    # --- 側邊欄 ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_label = "🔴 Admin" if st.session_state['user_role'] == 'Admin' else "🟢 Staff"
        st.caption(f"Role: {role_label}")
        
        st.markdown("---")
        with st.expander("💱 匯率監控", expanded=True):
            source = st.session_state.get('rate_source', 'Manual')
            status_color = "green" if "Live" in source else "orange"
            st.caption(f"Source: :{status_color}[{source}]")
            
            current_rate = st.session_state['exchange_rate']
            new_rate = st.number_input("RMB to TWD", value=current_rate, step=0.01, format="%.2f")
            
            if new_rate != current_rate:
                st.session_state['exchange_rate'] = new_rate
                st.session_state['rate_source'] = "Manual Override"
                st.toast(f"匯率已手動鎖定為: {new_rate}")

            if st.button("🔄 重抓 Live 匯率"):
                live_r, success = get_live_rate()
                st.session_state['exchange_rate'] = live_r
                st.session_state['rate_source'] = "Live API" if success else "Fetch Failed"
                st.rerun()

        st.markdown("---")
        with st.expander("⚙️ 安全設定"):
            with st.form("pwd"):
                old = st.text_input("舊密碼", type="password")
                new = st.text_input("新密碼", type="password")
                confirm = st.text_input("確認", type="password")
                if st.form_submit_button("修改"):
                    try:
                        raw_data = ws_users.get_all_values()
                        user_row_idx = -1
                        for i, row in enumerate(raw_data):
                            if str(row[0]).strip() == st.session_state['user_name']:
                                user_row_idx = i + 1; stored_pwd = str(row[1]).strip(); break
                        
                        is_valid = check_hash(old, stored_pwd) if len(stored_pwd)==64 else (old == stored_pwd)
                        if is_valid:
                            ws_users.update_cell(user_row_idx, 2, make_hash(new))
                            st.success("Updated!")
                        else: st.error("Error")
                    except: st.error("Error")

        if st.button("🚪 安全登出"):
            log_event(ws_logs, st.session_state['user_name'], "Logout", "登出")
            st.session_state['logged_in'] = False
            st.rerun()

    # --- Dashboard ---
    total_qty = df['Qty'].sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    total_rev = (df['Qty'] * df['Price']).sum()
    profit = total_rev - total_cost
    
    rmb_stock_value = 0
    if not df.empty and 'Orig_Currency' in df.columns:
        rmb_items = df[df['Orig_Currency'] == 'CNY']
        if not rmb_items.empty: rmb_stock_value = (rmb_items['Qty'] * rmb_items['Orig_Cost']).sum()

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f"<div class='metric-card'><div class='metric-label'>📦 總庫存</div><div class='metric-value'>{total_qty:,}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='metric-card'><div class='metric-label'>💎 預估營收</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='metric-card'><div class='metric-label'>💰 總成本 (TWD)</div><div class='metric-value'>${total_cost:,}</div><div style='font-size:11px;color:#888;'>含RMB原幣: ¥{rmb_stock_value:,}</div></div>", unsafe_allow_html=True)
    with m4: st.markdown(f"<div class='metric-card'><div class='metric-label'>📈 潛在毛利</div><div class='metric-value' style='color:#28a745 !important'>${profit:,}</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- Tabs ---
    tabs = st.tabs(["📊 總覽與庫存", "⚡ POS", "🎁 內部領用", "👔 款式矩陣管理", "📝 日誌", "👥 Admin"])

    # Tab 1: 視覺總覽
    with tabs[0]:
        if not df.empty:
            c_chart1, c_chart2 = st.columns([1, 1])
            with c_chart1:
                st.caption("📈 庫存分類佔比")
                fig_pie = px.pie(df, names='Category', values='Qty', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            with c_chart2:
                st.caption("📊 重點庫存 (Top 10)")
                top_items = df.sort_values(by='Qty', ascending=False).head(10)
                fig_bar = px.bar(top_items, x='Qty', y='Name', orientation='h', text='Qty', color='Qty', color_continuous_scale='Bluered')
                fig_bar.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0), yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)
        
        st.divider()
        st.subheader("🖼️ 庫存畫廊")
        
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1: search_q = st.text_input("🔍 搜尋商品", placeholder="輸入貨號或品名...")
        with col_s2: filter_cat = st.selectbox("📂 分類篩選", ["全部"] + CAT_LIST)
        
        gallery_df = df.copy()
        if search_q: gallery_df = gallery_df[gallery_df.apply(lambda x: search_q.lower() in str(x.values).lower(), axis=1)]
        if filter_cat != "全部": gallery_df = gallery_df[gallery_df['Category'] == filter_cat]
        
        if not gallery_df.empty:
            html_cards = ""
            for idx, row in gallery_df.iterrows():
                img = render_image_url(row['Image_URL'])
                qty_class = "inv-qty inv-badge-low" if row['Qty'] < row['Safe_Level'] else "inv-qty"
                html_cards += f"""
                <div class="inv-card">
                    <img src="{img}" class="inv-img">
                    <div class="inv-title" title="{row['Name']}">{row['Name']}</div>
                    <div class="inv-sku">{row['SKU']} | {row['Size']}</div>
                    <div class="inv-price">${row['Price']}</div>
                    <div class="{qty_class}">庫存: {row['Qty']}</div>
                </div>
                """
            st.markdown(f'<div class="inventory-grid">{html_cards}</div>', unsafe_allow_html=True)
        else: st.info("無符合資料")

        st.markdown("##### 📦 庫存明細 (雙幣檢視)")
        display_df = gallery_df.copy()
        display_df['原幣成本(CNY)'] = display_df.apply(lambda x: f"¥ {x['Orig_Cost']}" if x['Orig_Currency'] == 'CNY' else "-", axis=1)
        display_df = display_df.drop(columns=['Image_URL', 'Safety_Stock', 'Orig_Currency', 'Orig_Cost'], errors='ignore')
        display_df = display_df.rename(columns=COLUMN_MAPPING)
        final_cols = [c for c in ["商品貨號", "商品名稱", "分類", "尺寸", "庫存量", "售價(NTD)", "成本(NTD)", "原幣成本(CNY)", "最後更新"] if c in display_df.columns]
        st.dataframe(display_df[final_cols], use_container_width=True)

    # Tab 2: POS
    with tabs[1]:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("商品")
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist()
            sel = st.selectbox("選擇商品 (POS)", ["..."] + opts)
            target = None
            if sel != "...":
                target = df[df['SKU'] == sel.split(" | ")[0]].iloc[0]
                img = render_image_url(target['Image_URL'])
                orig_show = f"<span class='cost-tag'>原幣: ¥{target['Orig_Cost']}</span>" if target['Orig_Currency'] == 'CNY' else ""
                st.markdown(f"""
                <div style="display:flex; align-items:center; background:#f9f9f9; padding:15px; border-radius:10px;">
                    <img src="{img}" style="width:80px; height:80px; border-radius:8px; object-fit:cover; margin-right:15px;">
                    <div>
                        <div style="font-weight:bold; font-size:18px;">{target['Name']}</div>
                        <div style="color:#666;">{target['SKU']}</div>
                        <div style="margin-top:5px;">成本: <b>NT${target['Cost']}</b> {orig_show}</div>
                        <div style="font-weight:bold; color:#d32f2f; font-size:20px; margin-top:5px;">現貨: {target['Qty']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with c2:
            st.subheader("操作")
            if target is not None:
                qty = st.number_input("數量", 1)
                t1, t2 = st.tabs(["📥 進貨 (Restock)", "📤 銷售 (Sale)"])
                
                with t1:
                    st.markdown("###### 💰 進貨成本")
                    cost_currency = st.radio("幣別", ["NTD", "CNY"], horizontal=True)
                    input_unit_cost = st.number_input("單價", value=0.0)
                    final_cost_twd = int(input_unit_cost * st.session_state['exchange_rate']) if cost_currency == "CNY" else int(input_unit_cost)
                    if cost_currency == "CNY": st.info(f"換算: ¥{input_unit_cost} = NT${final_cost_twd}")
                    note_in = st.text_input("備註")
                    if st.button("確認進貨", type="secondary", use_container_width=True):
                        cur_qty = int(target['Qty']); cur_cost = int(target['Cost'])
                        tot_qty = cur_qty + qty
                        new_avg = int(((cur_qty * cur_cost) + (qty * (final_cost_twd if final_cost_twd>0 else cur_cost))) / tot_qty) if tot_qty > 0 else final_cost_twd
                        r = ws_items.find(target['SKU']).row
                        ws_items.update_cell(r, 5, tot_qty); ws_items.update_cell(r, 7, new_avg); ws_items.update_cell(r, 8, str(datetime.now()))
                        if cost_currency == "CNY":
                            ws_items.update_cell(r, 11, "CNY"); ws_items.update_cell(r, 12, int(input_unit_cost))
                        log_event(ws_logs, st.session_state['user_name'], "Restock", f"{target['SKU']} +{qty}")
                        st.success("成功"); time.sleep(1); st.rerun()

                with t2:
                    note_out = st.text_input("銷售備註")
                    if st.button("確認銷售", type="primary", use_container_width=True):
                        if int(target['Qty']) >= qty:
                            r = ws_items.find(target['SKU']).row
                            ws_items.update_cell(r, 5, int(target['Qty']) - qty); ws_items.update_cell(r, 8, str(datetime.now()))
                            log_event(ws_logs, st.session_state['user_name'], "Sale", f"{target['SKU']} -{qty} | {note_out}")
                            st.success("成功"); time.sleep(1); st.rerun()
                        else: st.error("庫存不足")

    # Tab 3: Internal
    with tabs[2]:
        st.subheader("🎁 內部領用中心")
        c_i1, c_i2 = st.columns([1, 1])
        with c_i1:
            sel_int = st.selectbox("選擇商品", ["..."] + opts, key="int_sel")
            t_int = None
            if sel_int != "...":
                t_int = df[df['SKU'] == sel_int.split(" | ")[0]].iloc[0]
                st.markdown(f"<div style='background:#fff3e0; padding:10px; border-radius:8px;'><b>{t_int['Name']}</b><br>庫存: {t_int['Qty']}</div>", unsafe_allow_html=True)
        with c_i2:
            if t_int is not None:
                with st.form("int_form"):
                    iq = st.number_input("數量", 1, max_value=int(t_int['Qty']))
                    who = st.selectbox("領用人", staff_list if staff_list else ["Boss"])
                    rsn = st.selectbox("原因", ["公務制服", "福利", "樣品", "報廢", "其他"])
                    int_note = st.text_input("備註 (Ex: 灰色M號一件)")
                    if st.form_submit_button("領用 (扣除庫存)"):
                        r = ws_items.find(t_int['SKU']).row
                        ws_items.update_cell(r, 5, int(t_int['Qty']) - iq)
                        total_cost_value = int(t_int['Cost']) * iq
                        log_msg = f"{t_int['SKU']} -{iq} | 領用:{who} | {rsn} | 成本:${total_cost_value} | {int_note}"
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", log_msg)
                        st.success(f"領用成功！"); time.sleep(2); st.rerun()
        
        st.divider()
        st.markdown("#### 🖼️ 近期領用紀錄")
        logs_df = get_data_safe(ws_logs)
        if not logs_df.empty:
            int_logs = logs_df[logs_df['Action'] == 'Internal_Use'].sort_index(ascending=False).head(5)
            if not int_logs.empty:
                for idx, log in int_logs.iterrows():
                    try:
                        log_sku = log['Details'].split(" ")[0]
                        img_row = df[df['SKU'] == log_sku]
                        img_url = "https://i.ibb.co/W31w56W/placeholder.png"
                        if not img_row.empty: img_url = render_image_url(img_row.iloc[0]['Image_URL'])
                        st.markdown(f"""
                        <div class="history-card">
                            <img src="{img_url}" class="history-img">
                            <div style="flex:1">
                                <div style="font-weight:bold; font-size:14px;">{log['User']}</div>
                                <div style="font-size:12px; color:#666;">{log['Details']}</div>
                                <div style="font-size:10px; color:#999;">{log['Timestamp']}</div>
                            </div>
                            <div class="history-tag">Internal</div>
                        </div>
                        """, unsafe_allow_html=True)
                    except: pass

    # Tab 4: 矩陣管理 (V35: 雙向矩陣引擎)
    with tabs[3]:
        st.markdown("### 👔 款式矩陣中樞 (Matrix Hub)")
        st.caption("在此輸入款號，系統將自動判斷是「新增」還是「編輯/追加」。")
        
        # 1. 選擇/輸入款號
        # 為了方便編輯，我們列出所有"款號" (去重後的 Prefix)
        # 假設 SKU 格式為 STYLE-SIZE (如 TOP-2601-S)
        all_skus = df['SKU'].tolist()
        existing_styles = sorted(list(set(["-".join(s.split("-")[:-1]) for s in all_skus if "-" in s])))
        
        c_style1, c_style2 = st.columns([1, 2])
        with c_style1:
            cat_batch = st.selectbox("分類", CAT_LIST, key="batch_cat")
            # 款號生成器
            if st.button("🎲 生成新款號"):
                new_style = generate_smart_style_code(cat_batch, all_skus)
                st.session_state['matrix_style_code'] = new_style
                st.toast(f"已生成: {new_style}")

        with c_style2:
            # 讓用戶可以從現有清單選，也可以手動打新的
            input_style = st.text_input("輸入或貼上款號 (Ex: TOP-2601)", value=st.session_state.get('matrix_style_code', ""), key="matrix_input")
            # 或者是下拉選單輔助
            sel_exist = st.selectbox("或是選擇現有款式來編輯:", ["..."] + existing_styles)
            if sel_exist != "...":
                input_style = sel_exist # 覆蓋輸入框 (邏輯上需用戶手動複製，Streamlit限制)
                st.info(f"您選擇了: {sel_exist}，請將其複製到上方輸入框以載入數據。")

        if input_style:
            # V35 核心邏輯: 檢查是否已存在
            # 找出所有屬於此款號的 SKU
            related_skus = df[df['SKU'].str.startswith(input_style + "-")]
            
            is_edit_mode = not related_skus.empty
            
            if is_edit_mode:
                st.markdown(f"<div class='smart-detect'>🟢 <b>系統偵測：款式 [{input_style}] 已存在。進入編輯/追加模式。</b></div>", unsafe_allow_html=True)
                # 抓取第一筆資料當作預設值
                first_row = related_skus.iloc[0]
                default_name = first_row['Name']
                default_price = int(first_row['Price'])
                default_cost = int(first_row['Cost'])
                default_img = first_row['Image_URL']
            else:
                st.markdown(f"<div class='smart-detect'>🔵 <b>系統偵測：款式 [{input_style}] 為新商品。進入新增模式。</b></div>", unsafe_allow_html=True)
                default_name = ""
                default_price = 0
                default_cost = 0
                default_img = ""

            with st.form("matrix_form"):
                st.markdown("#### 1. 款式參數")
                name_b = st.text_input("商品名稱", value=default_name)
                c_p1, c_p2 = st.columns(2)
                price_b = c_p1.number_input("售價 (NTD)", value=default_price)
                
                # 成本設定 (如果是新的一批貨，可能成本不同，這裡簡化為統一設定)
                c_curr_b, c_cost_b = c_p2.columns([1, 1])
                curr_sel_b = c_curr_b.selectbox("成本幣別", ["TWD", "CNY"])
                cost_in_b = c_cost_b.number_input("成本金額", value=default_cost if curr_sel_b == "TWD" else 0)
                
                final_cost_b = int(cost_in_b * st.session_state['exchange_rate']) if curr_sel_b == "CNY" else int(cost_in_b)
                if curr_sel_b == "CNY": st.caption(f"換算成本: NT${final_cost_b}")

                img_b = st.file_uploader("圖片 (若不修改請留空)", type=['jpg','png'])
                
                st.markdown("#### 2. 尺寸庫存矩陣")
                # 動態生成尺寸輸入框，若有現貨則預填
                size_cols1 = st.columns(5)
                size_inputs = {}
                
                for idx, size in enumerate(SIZE_LIST[:5]):
                    # 查找目前庫存
                    current_q = 0
                    if is_edit_mode:
                        target_sku = f"{input_style}-{size}"
                        match = related_skus[related_skus['SKU'] == target_sku]
                        if not match.empty: current_q = int(match.iloc[0]['Qty'])
                    
                    with size_cols1[idx]:
                        size_inputs[size] = st.number_input(f"{size}", min_value=0, value=current_q, key=f"mx_{size}")

                size_cols2 = st.columns(4)
                for idx, size in enumerate(SIZE_LIST[5:]):
                    current_q = 0
                    if is_edit_mode:
                        target_sku = f"{input_style}-{size}"
                        match = related_skus[related_skus['SKU'] == target_sku]
                        if not match.empty: current_q = int(match.iloc[0]['Qty'])
                    with size_cols2[idx]:
                        size_inputs[size] = st.number_input(f"{size}", min_value=0, value=current_q, key=f"mx_{size}")

                if st.form_submit_button("🚀 執行同步 (Save & Sync)"):
                    if name_b and input_style:
                        # 圖片處理
                        final_u = default_img
                        if img_b:
                            new_u = upload_image_to_imgbb(img_b)
                            if new_u: final_u = new_u
                        
                        ocode = "CNY" if curr_sel_b == "CNY" else "TWD"
                        
                        updated_count = 0
                        created_count = 0
                        
                        for size, new_q in size_inputs.items():
                            target_sku = f"{input_style}-{size}"
                            
                            # 檢查是否存在
                            if target_sku in df['SKU'].tolist():
                                # 存在 -> 更新 (Update)
                                # 只有當數據有變動才更新，節省資源 (這裡簡化為全更新以保證資料一致性)
                                r = ws_items.find(target_sku).row
                                ws_items.update_cell(r, 2, name_b) # Name
                                ws_items.update_cell(r, 3, cat_batch) # Category
                                ws_items.update_cell(r, 5, new_q) # Qty
                                ws_items.update_cell(r, 6, price_b) # Price
                                ws_items.update_cell(r, 7, final_cost_b) # Cost
                                ws_items.update_cell(r, 8, str(datetime.now())) # Time
                                if img_b: ws_items.update_cell(r, 9, final_u) # Image
                                
                                updated_count += 1
                            
                            elif new_q > 0:
                                # 不存在且數量>0 -> 新增 (Create)
                                ws_items.append_row([target_sku, name_b, cat_batch, size, new_q, price_b, final_cost_b, str(datetime.now()), final_u, 5, ocode, cost_in_b])
                                created_count += 1
                        
                        log_msg = f"矩陣操作: {input_style} | 更新:{updated_count}筆, 新增:{created_count}筆"
                        log_event(ws_logs, st.session_state['user_name'], "Matrix_Sync", log_msg)
                        st.success(f"完成！共更新 {updated_count} 個尺寸，新增 {created_count} 個尺寸。"); time.sleep(2); st.rerun()
                    else:
                        st.error("請填寫款號與名稱")

    # Tab 5: Log
    with tabs[4]:
        st.subheader("🕵️ 稽核日誌")
        c_f1, c_f2, c_f3 = st.columns([1, 1, 1])
        with c_f1: search_date = st.date_input("📅 日期", value=None)
        with c_f2:
            act_map = {"全部":"All", "修改":"Edit_Item", "內部領用":"Internal_Use", "銷售":"Sale", "進貨":"Restock", "登入":"Login", "新增":"New_Item", "矩陣":"Matrix_Sync", "人事":"HR"}
            s_act = st.selectbox("🔍 動作", list(act_map.keys()))
        with c_f3: kw = st.text_input("🔤 關鍵字")

        logs_df = get_data_safe(ws_logs)
        if not logs_df.empty:
            logs_df['Timestamp'] = pd.to_datetime(logs_df['Timestamp'], errors='coerce')
            logs_df['DateObj'] = logs_df['Timestamp'].dt.date
            disp = logs_df.copy()
            if search_date: disp = disp[disp['DateObj'] == search_date]
            if act_map[s_act] != "All": disp = disp[disp['Action'] == act_map[s_act]]
            if kw: disp = disp[disp.apply(lambda r: kw.lower() in str(r).lower(), axis=1)]
            
            if not disp.empty:
                disp['Timestamp'] = disp['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                st.dataframe(disp.drop(columns=['DateObj']).sort_index(ascending=False), use_container_width=True, height=500)
            else: st.info("無資料")
        else: st.warning("無紀錄")

    # Tab 6: Admin
    with tabs[5]:
        if st.session_state['user_role'] == 'Admin':
            st.subheader("👥 人員管理")
            users_df = get_data_safe(ws_users)
            st.dataframe(users_df[['Name', 'Role', 'Status', 'Created_At']], use_container_width=True)
            st.divider()
            c_a1, c_a2 = st.columns(2)
            with c_a1:
                with st.form("hr"):
                    un = st.text_input("帳號"); up = st.text_input("密碼", type="password")
                    ur = st.selectbox("權限", ["Staff", "Admin"]); us = st.selectbox("狀態", ["Active", "Inactive"])
                    if st.form_submit_button("執行"):
                        if un and up:
                            h = make_hash(up)
                            try:
                                cell = ws_users.find(un, in_column=1); r = cell.row
                                ws_users.update_cell(r, 2, h); ws_users.update_cell(r, 3, ur); ws_users.update_cell(r, 4, us)
                                st.success("Updated")
                            except:
                                ws_users.append_row([un, h, ur, us, str(datetime.now())])
                                st.success("Created")
                            log_event(ws_logs, st.session_state['user_name'], "HR", f"Upd: {un}"); time.sleep(1); st.rerun()
            with c_a2:
                if st.button("☢️ 清空日誌"):
                    ws_logs.clear(); ws_logs.append_row(["Timestamp", "User", "Action", "Details"])
                    log_event(ws_logs, st.session_state['user_name'], "Security", "Clear Logs"); st.rerun()
        else: st.error("權限不足")

if __name__ == "__main__":
    main()
