import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import requests
import plotly.express as px
import base64
import qrcode
from io import BytesIO

# --- 1. 系統全域設定 (修正點：改為 expanded 強制展開側邊欄) ---
st.set_page_config(
    page_title="IFUKUK 戰情中樞", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded"  # <--- 關鍵修改：強制打開，不再隱藏
)

# ==========================================
# 🛑 【MATRIX-V26.1 側邊欄救援補丁】
# ==========================================
st.markdown("""
    <style>
        /* --- Part A: 基礎顏色鎖定 --- */
        .stApp { background-color: #FFFFFF !important; }
        p, div, h1, h2, h3, h4, span, label, li { color: #000000 !important; }
        button[data-baseweb="tab"] div p { color: #555555 !important; font-weight: 600 !important; }
        button[data-baseweb="tab"][aria-selected="true"] div p { color: #FF4B4B !important; }
        input.st-ai, textarea, select { 
            color: #000000 !important; 
            background-color: #F3F4F6 !important;
            border-radius: 8px !important;
        }
        
        /* --- Part B: V26.1 Sidebar 按鈕救援 --- */
        /* 1. 讓 Streamlit 原本的 Header 回來，不要隱藏它 */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            display: block !important; /* 確保它顯示 */
            z-index: 9999 !important; /* 確保它在最上層，沒人能擋住它 */
        }

        /* 2. 把我們自製的導航欄往下推，避開左上角的箭頭/漢堡選單 */
        .navbar-container {
            position: fixed;
            top: 50px; /* <--- 下移，讓出頂部空間給系統選單 */
            left: 0;
            width: 100%;
            z-index: 99;
            background-color: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 10px 20px;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }
        
        /* 增加頂部留白，避免內容被雙重 Header 擋住 */
        .block-container {
            padding-top: 8rem !important; 
            padding-bottom: 5rem !important;
        }

        /* --- Part C: 視覺美化 --- */
        .metric-card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            border: 1px solid #f0f0f0;
            text-align: center;
            margin-bottom: 12px;
        }
        .metric-value { font-size: 2rem; font-weight: 800; margin: 4px 0; color: #111 !important; }
        .metric-label { font-size: 0.8rem; color: #666 !important; font-weight: 600; }
        
        .product-card {
            background: white; border-radius: 12px; padding: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #eee;
        }
        
        .stButton>button { border-radius: 10px; height: 3em; font-weight: 700; border: none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
LINE_CHANNEL_ACCESS_TOKEN = "IaGvcTOmbMFW8wKEJ5MamxfRx7QVo0kX1IyCqwKZw0WX2nxAVYY7SsSh5vAJ0r+WBNvyjjiU8G3eYkL1nozqIOjjWMOKr/4ZtzUMRRf7JNJkk5V6jLpWc/EOkzvNGVPMh0zwH+wQD51tR3XWipUULwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U55199b00fb78da85bb285db6d00b6ff5"

# --- 連線邏輯 ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=600) # 縮短緩存時間以便測試
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_data_safe(ws):
    try:
        if ws is None: return pd.DataFrame()
        raw_data = ws.get_all_values()
        if not raw_data or len(raw_data) < 2: return pd.DataFrame()
        headers = raw_data[0]
        rows = raw_data[1:]
        df = pd.DataFrame(rows, columns=headers)
        return df
    except: return pd.DataFrame()

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

# --- 工具 ---
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

# --- V26.1 Navbar ---
def render_navbar(user_initial):
    current_date = datetime.now().strftime("%b %d")
    st.markdown(f"""
        <div class="navbar-container">
            <div style="display:flex; flex-direction:column;">
                <span style="font-size:18px; font-weight:900; color:#111;">IFUKUK</span>
                <span style="font-size:10px; color:#888;">{current_date} • 營運中</span>
            </div>
            <div style="width:35px; height:35px; background:#111; color:#fff; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">
                {user_initial}
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = ""
        st.session_state['user_role'] = ""

    sh = init_db()
    if not sh: 
        st.error("無法連線至資料庫")
        st.stop()

    ws_items = get_worksheet_safe(sh, "Items", ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"])
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    if not ws_items or not ws_logs or not ws_users:
        st.warning("系統初始化中...")
        st.stop()

    # --- 登入頁面 ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-weight:900; font-size:2.5rem; margin-bottom:10px;'>IFUKUK</div>", unsafe_allow_html=True)
            with st.form("login"):
                user_input = st.text_input("帳號")
                pass_input = st.text_input("密碼", type="password")
                if st.form_submit_button("登入系統", type="primary"):
                    users_df = get_data_safe(ws_users)
                    if not users_df.empty:
                        users_df['Name'] = users_df['Name'].astype(str).str.strip()
                        users_df['Password'] = users_df['Password'].astype(str).str.strip()
                        input_u = str(user_input).strip()
                        input_p = str(pass_input).strip()
                        valid = users_df[(users_df['Name'] == input_u) & (users_df['Password'] == input_p) & (users_df['Status'] == 'Active')]
                        
                        if not valid.empty:
                            st.session_state['logged_in'] = True
                            st.session_state['user_name'] = input_u
                            st.session_state['user_role'] = valid.iloc[0]['Role']
                            log_event(ws_logs, input_u, "Login", "登入成功")
                            st.rerun()
                        else: st.error("帳號或密碼錯誤")
                    else:
                        if user_input == "Boss" and pass_input == "1234":
                            ws_users.append_row(["Boss", "1234", "Admin", "Active", str(datetime.now())])
                            st.success("初始化完成")
                            st.rerun()
                        else: st.error("登入失敗")
        return

    # --- 登入後 ---
    
    # 渲染導航
    user_initial = st.session_state['user_name'][0].upper() if st.session_state['user_name'] else "U"
    render_navbar(user_initial)

    # 數據處理
    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    # --- 側邊欄 (修復：現在應該看得到了) ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_label = "🔴 Admin" if st.session_state['user_role'] == 'Admin' else "🟢 Staff"
        st.caption(f"Role: {role_label}")
        
        with st.expander("⚙️ 個人設定"):
            with st.form("pwd"):
                old = st.text_input("舊密碼", type="password")
                new = st.text_input("新密碼", type="password")
                confirm = st.text_input("確認", type="password")
                if st.form_submit_button("修改"):
                    try:
                        raw_data = ws_users.get_all_values()
                        user_row_idx = -1
                        current_pwd_db = ""
                        for i, row in enumerate(raw_data):
                            if str(row[0]).strip() == st.session_state['user_name']:
                                user_row_idx = i + 1 
                                current_pwd_db = str(row[1]).strip()
                                break
                        if user_row_idx != -1 and str(old).strip() == current_pwd_db and new == confirm:
                            ws_users.update_cell(user_row_idx, 2, str(new).strip())
                            st.toast("✅ 密碼修改成功！")
                        else: st.error("修改失敗")
                    except: st.error("系統錯誤")

        st.markdown("---")
        if st.button("🚪 安全登出"):
            log_event(ws_logs, st.session_state['user_name'], "Logout", "登出系統")
            st.session_state['logged_in'] = False
            st.rerun()

    # --- 儀表板 ---
    total_qty = df['Qty'].sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    total_rev = (df['Qty'] * df['Price']).sum()
    profit = total_rev - total_cost

    m1, m2 = st.columns(2)
    with m1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>📦 總庫存</div><div class='metric-value'>{total_qty:,}</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><div class='metric-label'>💰 總成本</div><div class='metric-value'>${total_cost:,}</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>💎 預估營收</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><div class='metric-label'>📈 潛在毛利</div><div class='metric-value' style='color:#28a745 !important'>${profit:,}</div></div>", unsafe_allow_html=True)
    
    # 顯示 Google Sheet 原始資料狀態 (方便除錯)
    if total_qty == 0 and not df.empty:
         st.warning(f"⚠️ 系統讀到了 {len(df)} 筆資料，但加總為 0。請檢查 Google Sheet 的 'Qty', 'Price', 'Cost' 欄位是否包含非數字文字？")

    st.markdown("---")

    # --- 功能區 ---
    tabs = st.tabs(["🧥 樣品", "⚡ POS", "➕ 管理", "📝 紀錄"])

    with tabs[0]: # 樣品
        q = st.text_input("🔍 搜尋", placeholder="貨號/品名...")
        v_df = df.copy()
        if q: v_df = v_df[v_df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
        if not v_df.empty:
            for idx, row in v_df.iterrows():
                with st.container():
                    img_src = render_image_url(row['Image_URL'])
                    st.markdown(f"""
                    <div style="display:flex; background:white; border-radius:12px; padding:10px; margin-bottom:10px; box-shadow:0 2px 5px rgba(0,0,0,0.05); border:1px solid #f0f0f0;">
                        <img src="{img_src}" style="width:80px; height:80px; object-fit:cover; border-radius:8px; margin-right:15px;">
                        <div style="flex:1;">
                            <div style="font-weight:bold; font-size:16px; color:#111;">{row['Name']}</div>
                            <div style="color:#666; font-size:12px;">{row['SKU']} | {row['Size']}</div>
                            <div style="font-weight:800; font-size:16px; margin-top:5px;">${row['Price']} <span style="font-size:12px; font-weight:400; background:#eee; padding:2px 5px; border-radius:4px;">Q:{row['Qty']}</span></div>
                        </div>
                    </div>""", unsafe_allow_html=True)
        else: st.info("無商品")

    with tabs[1]: # POS
        c1, c2 = st.columns([2, 1])
        with c1:
            sel_sku = st.selectbox("選擇商品", ["請選擇..."] + [f"{r['SKU']} | {r['Name']}" for i, r in df.iterrows()])
            target = None
            if sel_sku != "請選擇...":
                real_sku = sel_sku.split(" | ")[0]
                target = df[df['SKU'] == real_sku].iloc[0]
                st.info(f"已選擇: {target['Name']} (庫存: {target['Qty']})")
        with c2:
            if target is not None:
                qty = st.number_input("數量", 1)
                note = st.text_input("備註")
                col_in, col_out = st.columns(2)
                if col_in.button("進貨"):
                    r = ws_items.find(target['SKU']).row
                    ws_items.update_cell(r, 5, int(target['Qty']) + qty)
                    log_event(ws_logs, st.session_state['user_name'], "Restock", f"{target['SKU']} +{qty}")
                    st.rerun()
                if col_out.button("銷售", type="primary"):
                    if int(target['Qty']) >= qty:
                        r = ws_items.find(target['SKU']).row
                        ws_items.update_cell(r, 5, int(target['Qty']) - qty)
                        log_event(ws_logs, st.session_state['user_name'], "Sale", f"{target['SKU']} -{qty}")
                        st.rerun()
                    else: st.error("庫存不足")

    with tabs[2]: # 管理
        with st.form("new_item"):
            sku = st.text_input("貨號 (SKU)")
            name = st.text_input("品名")
            c1, c2, c3, c4 = st.columns(4)
            cat = c1.selectbox("分類", ["上衣", "褲子", "外套", "配件"])
            size = c2.selectbox("尺寸", ["F","S","M","L","XL"])
            price = c3.number_input("售價", 0)
            cost = c4.number_input("成本", 0)
            q = st.number_input("數量", 0)
            img = st.file_uploader("圖片", type=['jpg','png'])
            if st.form_submit_button("上架"):
                if sku and name:
                    u = upload_image_to_imgbb(img) if img else ""
                    ws_items.append_row([sku, name, cat, size, q, price, cost, str(datetime.now()), u])
                    st.toast("上架成功")
                    time.sleep(1)
                    st.rerun()

    with tabs[3]: # 紀錄
        logs_df = get_data_safe(ws_logs)
        st.dataframe(logs_df.sort_index(ascending=False).head(50), use_container_width=True)

if __name__ == "__main__":
    main()
