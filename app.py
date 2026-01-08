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
# 🛑 【MATRIX-V32.3 視覺核心終極重塑補丁】
# 重點修復：手機深色模式下，下拉選單與日期選擇器「黑底黑字」無法觀看的問題。
# 採用更底層的 CSS 強制覆蓋策略。
# ==========================================
st.markdown("""
    <style>
        /* --- 1. 全局基礎鎖定 (白底黑字) --- */
        .stApp { background-color: #FFFFFF !important; }
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; border-right: 1px solid #E5E7EB; }
        h1, h2, h3, h4, h5, h6, p, span, div, label, li { color: #000000 !important; }
        
        /* --- 2. 輸入框與顯示框基礎樣式 --- */
        input, textarea, .stTextInput > div > div, .stNumberInput > div > div {
            color: #000000 !important;
            background-color: #F3F4F6 !important;
            border-color: #D1D5DB !important;
        }
        /* Selectbox 未展開時的顯示框 */
        div[data-baseweb="select"] > div {
            background-color: #F3F4F6 !important;
            color: #000000 !important;
            border-color: #D1D5DB !important;
        }

        /* ========================================================================
           3. [關鍵修復] 下拉選單 (Selectbox) 彈出視窗
           ======================================================================== */
        /* 強制所有彈出視窗容器為白底黑字 */
        div[data-baseweb="popover"], div[data-baseweb="menu"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #E5E7EB !important;
        }
        /* 選項列表容器 */
        ul[role="listbox"] {
            background-color: #FFFFFF !important;
        }
        /* 每一個選項 (Option) */
        li[role="option"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        /* 選項內的文字容器 */
        li[role="option"] div {
            color: #000000 !important;
        }
        /* 滑鼠滑過或選中時的狀態 (淺灰底黑字) */
        li[role="option"]:hover, li[role="option"][aria-selected="true"] {
            background-color: #F3F4F6 !important;
            color: #000000 !important;
        }

        /* ========================================================================
           4. [關鍵修復] 日期選擇器 (Date Picker) 彈出視窗
           ======================================================================== */
        /* 鎖定日期選擇器的彈出層容器 */
        div[data-testid="stDateInput"] > div:nth-of-type(2) > div {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #E5E7EB !important;
        }
        /* 日曆 Header (月份、年份顯示與切換按鈕) */
        div[data-testid="stDateInput"] div[class*="CalendarHeader"] {
            color: #000000 !important;
        }
        div[data-testid="stDateInput"] button[aria-label="Previous month"],
        div[data-testid="stDateInput"] button[aria-label="Next month"] {
             color: #000000 !important;
        }
        /* 星期幾的標題 (Su, Mo, Tu...) */
        div[data-testid="stDateInput"] div[class*="WeekDays"] {
            color: #666666 !important;
        }
        /* 日曆內的日期按鈕 */
        div[data-testid="stDateInput"] button[role="gridcell"] {
            color: #000000 !important;
            background-color: #FFFFFF !important;
        }
        /* 滑鼠滑過日期 */
        div[data-testid="stDateInput"] button[role="gridcell"]:hover {
             background-color: #F3F4F6 !important;
        }
        /* 被選中的日期 */
        div[data-testid="stDateInput"] button[role="gridcell"][aria-selected="true"] {
             background-color: #FF4B4B !important; /* Streamlit 預設紅 */
             color: #FFFFFF !important;
        }
        /* 今天日期 */
        div[data-testid="stDateInput"] button[role="gridcell"][tabindex="0"]:not([aria-selected="true"]) {
             color: #FF4B4B !important;
             font-weight: bold;
        }

        /* --- 5. 其他元件樣式 (保持不變) --- */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            display: block !important;
            z-index: 9999 !important;
        }
        .block-container {
            padding-top: 6rem !important; 
            padding-bottom: 5rem !important;
        }

        .navbar-container {
            position: fixed;
            top: 50px; left: 0; width: 100%; z-index: 99;
            background-color: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(12px);
            padding: 12px 24px;
            border-bottom: 1px solid #e0e0e0;
            display: flex; justify-content: space-between; align-items: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        }

        .metric-card {
            background: linear-gradient(145deg, #ffffff, #f5f7fa); 
            border-radius: 16px; padding: 20px;
            border: 1px solid #e1e4e8; text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 10px; transition: all 0.2s;
            position: relative; overflow: hidden;
        }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(0,0,0,0.06); }
        .metric-value { font-size: 2rem; font-weight: 800; margin: 8px 0; color:#111 !important; letter-spacing: -0.5px; }
        .metric-label { font-size: 0.85rem; letter-spacing: 1px; color:#666 !important; font-weight: 600; text-transform: uppercase; }
        
        .history-card {
            display: flex; align-items: center;
            background: #fff; border: 1px solid #eee; border-radius: 8px;
            padding: 10px; margin-bottom: 8px;
        }
        .history-img { width: 50px; height: 50px; border-radius: 5px; object-fit: cover; margin-right: 10px; }
        .history-tag { background: #ffe0b2; color: #e65100 !important; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; margin-left: auto; }

        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border:none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); background-color: #FFFFFF; color: #000000; border: 1px solid #E5E7EB; }
        
        .cost-tag {
            background-color: #f3f4f6; border: 1px solid #d1d5db;
            color: #374151 !important; padding: 2px 6px; border-radius: 4px;
            font-size: 0.75em; margin-left: 5px; font-weight: normal;
        }
        
        /* 確保 Expander 標題可見 */
        .streamlit-expanderHeader p { color: #000000 !important; font-weight: 600; }
        .streamlit-expanderHeader svg { color: #000000 !important; }
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

# --- V32 專業工具模組 ---

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

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue()

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

# V32 智能系列編碼器
def generate_smart_sku(category, existing_skus, custom_series=""):
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
                seq_part = sku.split("-")[-1]
                seq_num = int(seq_part)
                if seq_num > max_seq: max_seq = seq_num
            except: pass
    next_seq = str(max_seq + 1).zfill(3)
    return f"{current_prefix}{next_seq}"

# --- 主程式 ---
def main():
    if 'logged_in' not in session_state:
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
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>TEAMWORK ERP V32.3</div>", unsafe_allow_html=True)
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
    tabs = st.tabs(["⚡ POS", "🎁 內部領用", "📦 商品管理", "📝 日誌", "👥 Admin"])

    # Tab 1: POS
    with tabs[0]:
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
                        
                        log_msg = f"{target['SKU']} +{qty} | 均價:${new_avg} | {note_in}"
                        log_event(ws_logs, st.session_state['user_name'], "Restock", log_msg)
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

    # Tab 2: Internal
    with tabs[1]:
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
        st.markdown("#### 🖼️ 近期領用紀錄 (Visual History)")
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

    # Tab 3: Mgmt
    with tabs[2]:
        with st.expander("➕ 新增商品", expanded=False):
            with st.form("new_prod"):
                st.markdown("##### 1. 基本資料")
                c_a, c_b = st.columns([1, 2])
                cat = c_a.selectbox("分類", CAT_LIST)
                
                c_gen1, c_gen2 = st.columns([1, 2])
                series_code = c_gen1.text_input("系列代碼 (可選)", placeholder="Ex: SUIT-A")
                if c_gen1.form_submit_button("🎲 生成貨號"):
                    generated_sku = generate_smart_sku(cat, df['SKU'].tolist(), series_code)
                    st.session_state['temp_new_sku'] = generated_sku
                    st.info(f"建議: {generated_sku}")
                
                sku_val = st.session_state.get('temp_new_sku', "")
                sku = c_b.text_input("貨號 (SKU)", value=sku_val)
                name = st.text_input("商品名稱")
                
                c1, c2, c3, c4 = st.columns(4)
                size = c1.selectbox("尺寸", SIZE_LIST)
                price = c2.number_input("售價 (NTD)", 0)
                
                c_curr, c_val = c3.columns([1, 1])
                curr_sel = c_curr.selectbox("成本幣別", ["TWD", "CNY"])
                cost_in = c_val.number_input("成本金額", 0)
                
                q = c4.number_input("初始數量", 0)
                safe_s = st.number_input("安全庫存", 5)
                img = st.file_uploader("圖片", type=['jpg','png'])
                
                final_cost = int(cost_in * st.session_state['exchange_rate']) if curr_sel == "CNY" else int(cost_in)
                if curr_sel == "CNY": st.caption(f"預計存入: NT${final_cost}")

                if st.form_submit_button("確認上架"):
                    if sku and name:
                        if sku in df['SKU'].tolist(): st.error("SKU 重複")
                        else:
                            u = upload_image_to_imgbb(img) if img else ""
                            ocode = "CNY" if curr_sel == "CNY" else "TWD"
                            ws_items.append_row([sku, name, cat, size, q, price, final_cost, str(datetime.now()), u, safe_s, ocode, cost_in])
                            log_event(ws_logs, st.session_state['user_name'], "New_Item", f"新增: {sku}")
                            st.success("上架成功"); time.sleep(1); st.rerun()
                    else: st.error("缺資料")

        with st.expander("✏️ 修改商品資料", expanded=True):
            edit_target_sku = st.selectbox("選擇修改對象", ["..."] + opts, key="edit_sel")
            
            if edit_target_sku != "...":
                t_sku = edit_target_sku.split(" | ")[0]
                t_row = df[df['SKU'] == t_sku].iloc[0]
                st.info(f"編輯: {t_row['Name']} ({t_sku})")
                
                with st.form("edit_form"):
                    e_name = st.text_input("名稱", value=t_row['Name'])
                    c_e1, c_e2, c_e3 = st.columns(3)
                    e_price = c_e1.number_input("售價", value=int(t_row['Price']))
                    e_safe = c_e2.number_input("安全庫存", value=int(t_row['Safe_Level']))
                    curr_cat_idx = CAT_LIST.index(t_row['Category']) if t_row['Category'] in CAT_LIST else 0
                    e_cat = c_e3.selectbox("分類", CAT_LIST, index=curr_cat_idx)
                    e_img = st.file_uploader("更新圖片", type=['jpg','png'])
                    
                    if st.form_submit_button("💾 儲存修改"):
                        try:
                            r_idx = ws_items.find(t_sku).row
                            ws_items.update_cell(r_idx, 2, e_name); ws_items.update_cell(r_idx, 3, e_cat)
                            ws_items.update_cell(r_idx, 6, e_price); ws_items.update_cell(r_idx, 10, e_safe)
                            ws_items.update_cell(r_idx, 8, str(datetime.now()))
                            if e_img:
                                new_u = upload_image_to_imgbb(e_img)
                                if new_u: ws_items.update_cell(r_idx, 9, new_u)
                            log_event(ws_logs, st.session_state['user_name'], "Edit_Item", f"修改: {t_sku}")
                            st.success("修改完成！"); time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"失敗: {str(e)}")

        st.markdown("##### 📦 庫存總表")
        st.dataframe(df, use_container_width=True)

    # Tab 4: Log
    with tabs[3]:
        st.subheader("🕵️ 稽核日誌")
        c_f1, c_f2, c_f3 = st.columns([1, 1, 1])
        with c_f1: search_date = st.date_input("📅 日期", value=None)
        with c_f2:
            act_map = {"全部":"All", "修改":"Edit_Item", "內部領用":"Internal_Use", "銷售":"Sale", "進貨":"Restock", "登入":"Login", "新增":"New_Item", "人事":"HR"}
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

    # Tab 5: Admin
    with tabs[4]:
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
