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
# 🛑 【MATRIX-V30.1 視覺與金融核心】
# ==========================================
st.markdown("""
    <style>
        /* 強制白底黑字 */
        .stApp { background-color: #FFFFFF !important; }
        p, div, h1, h2, h3, h4, span, label, li { color: #000000 !important; }
        input.st-ai, textarea, select { 
            color: #000000 !important; 
            background-color: #F3F4F6 !important;
            border-radius: 8px !important;
        }
        
        /* Header 修正 */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            display: block !important;
            z-index: 9999 !important;
        }
        .block-container {
            padding-top: 6rem !important; 
            padding-bottom: 5rem !important;
        }

        /* 專業級 Navbar */
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

        /* 數據儀表板卡片 (優化版) */
        .metric-card {
            background: linear-gradient(145deg, #ffffff, #f5f7fa); 
            border-radius: 16px; padding: 20px;
            border: 1px solid #e1e4e8; text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 10px; transition: all 0.2s;
            position: relative; overflow: hidden;
        }
        .metric-card::before {
            content: ""; position: absolute; top: 0; left: 0; width: 4px; height: 100%;
            background: #212121;
        }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(0,0,0,0.06); }
        .metric-value { font-size: 2rem; font-weight: 800; margin: 8px 0; color:#111 !important; letter-spacing: -0.5px; }
        .metric-label { font-size: 0.85rem; letter-spacing: 1px; color:#666 !important; font-weight: 600; text-transform: uppercase; }
        
        /* 匯率資訊卡 (Live) */
        .rate-info {
            background-color: #e8f5e9; border-left: 5px solid #4caf50;
            padding: 12px; border-radius: 4px; font-size: 0.9rem; margin-bottom: 10px;
            color: #1b5e20;
        }
        .rate-warning {
            background-color: #fff3e0; border-left: 5px solid #ff9800;
            padding: 12px; border-radius: 4px; font-size: 0.9rem; margin-bottom: 10px;
            color: #e65100;
        }

        /* 按鈕優化 */
        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border:none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        
        /* 成本標記標籤 */
        .cost-tag {
            background-color: #f3f4f6; border: 1px solid #d1d5db;
            color: #374151; padding: 2px 6px; border-radius: 4px;
            font-size: 0.75em; margin-left: 5px; font-weight: normal;
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

# --- V30.1 專業工具模組 ---

# 1. 自動抓取匯率 (Live Forex API)
@st.cache_data(ttl=3600) # 每小時更新一次，避免太頻繁
def get_live_rate():
    try:
        # 使用公開免費的匯率 API
        url = "https://api.exchangerate-api.com/v4/latest/CNY"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['rates']['TWD'], True # 回傳匯率, 成功狀態
    except:
        pass
    return 4.50, False # 失敗則回傳預設值 4.5

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
                <span style="font-size:11px; color:#666; font-family:monospace;">{current_date} • Live Rate: {rate}</span>
            </div>
            <div style="width:36px; height:36px; background:#111; color:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold;">
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
    
    # 2. 自動匯率初始化 (Auto Forex)
    if 'exchange_rate' not in st.session_state:
        live_rate, is_success = get_live_rate()
        st.session_state['exchange_rate'] = live_rate
        st.session_state['rate_source'] = "Live API" if is_success else "Manual/Default"

    sh = init_db()
    if not sh: st.error("Database Connection Failed"); st.stop()

    # V30.1: 新增 Orig_Currency, Orig_Cost 欄位
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
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>CROSS-BORDER ERP V30.1</div>", unsafe_allow_html=True)
            
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
                        st.success("Init Success: Boss Created")
                        time.sleep(1); st.rerun()

                    if not users_df.empty:
                        users_df['Name'] = users_df['Name'].astype(str).str.strip()
                        users_df['Password'] = users_df['Password'].astype(str).str.strip()
                        target_user = users_df[(users_df['Name'] == input_u) & (users_df['Status'] == 'Active')]
                        
                        if not target_user.empty:
                            stored_hash = target_user.iloc[0]['Password']
                            is_valid = False
                            if len(stored_hash) == 64: is_valid = check_hash(input_p, stored_hash)
                            else: is_valid = (input_p == stored_hash)

                            if is_valid:
                                st.session_state['logged_in'] = True
                                st.session_state['user_name'] = input_u
                                st.session_state['user_role'] = target_user.iloc[0]['Role']
                                log_event(ws_logs, input_u, "Login", "登入成功")
                                st.rerun()
                            else: st.error("密碼錯誤")
                        else: st.error("帳號不存在或已停用")
                    else: st.error("系統無資料")
        return

    # --- 系統主畫面 ---
    user_initial = st.session_state['user_name'][0].upper()
    render_navbar(user_initial)

    # 資料準備
    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost', 'Safety_Stock', 'Orig_Cost']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    df['Safe_Level'] = df['Safety_Stock'].apply(lambda x: 5 if x == 0 else x)
    df['SKU'] = df['SKU'].astype(str)
    
    # 準備員工名單
    users_df = get_data_safe(ws_users)
    staff_list = []
    if not users_df.empty:
        staff_list = users_df['Name'].tolist()

    # --- 側邊欄 ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_label = "🔴 Admin" if st.session_state['user_role'] == 'Admin' else "🟢 Staff"
        st.caption(f"Role: {role_label}")
        
        st.markdown("---")
        # 匯率中心 (自動/手動)
        with st.expander("💱 匯率監控 (Forex)", expanded=True):
            source = st.session_state.get('rate_source', 'Manual')
            if source == "Live API":
                st.markdown("<div class='rate-info'>🟢 <b>Live API 連線中</b><br>已自動抓取國際即時匯率</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='rate-warning'>🟠 <b>手動 / 離線模式</b><br>請手動校正或檢查網路</div>", unsafe_allow_html=True)
            
            # 即使是自動抓取，也允許手動覆寫 (Override)
            current_rate = st.session_state['exchange_rate']
            new_rate = st.number_input("RMB to TWD", value=current_rate, step=0.01, format="%.2f")
            
            if new_rate != current_rate:
                st.session_state['exchange_rate'] = new_rate
                st.session_state['rate_source'] = "Manual Override"
                st.toast(f"匯率已手動鎖定為: {new_rate}")

            if st.button("🔄 重新抓取 Live 匯率"):
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
                if st.form_submit_button("修改密碼"):
                    try:
                        raw_data = ws_users.get_all_values()
                        user_row_idx = -1
                        for i, row in enumerate(raw_data):
                            if str(row[0]).strip() == st.session_state['user_name']:
                                user_row_idx = i + 1; stored_pwd = str(row[1]).strip(); break
                        
                        is_valid = False
                        if len(stored_pwd) == 64: is_valid = check_hash(old, stored_pwd)
                        else: is_valid = (old == stored_pwd)

                        if is_valid:
                            new_hash = make_hash(new)
                            ws_users.update_cell(user_row_idx, 2, new_hash)
                            st.success("Updated!")
                        else: st.error("Error")
                    except: st.error("Error")

        if st.button("🚪 安全登出"):
            log_event(ws_logs, st.session_state['user_name'], "Logout", "登出")
            st.session_state['logged_in'] = False
            st.rerun()

    # --- Dashboard (V30.1: 精細排版與雙幣顯示) ---
    total_qty = df['Qty'].sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    total_rev = (df['Qty'] * df['Price']).sum()
    profit = total_rev - total_cost
    
    # 計算 RMB 壓貨成本 (Audit)
    rmb_stock_value = 0
    if not df.empty and 'Orig_Currency' in df.columns:
        # 只計算標記為 CNY 的庫存總值 (原幣)
        rmb_items = df[df['Orig_Currency'] == 'CNY']
        if not rmb_items.empty:
            rmb_stock_value = (rmb_items['Qty'] * rmb_items['Orig_Cost']).sum()

    st.markdown("#### 📊 營運戰情室")
    
    # 手機版 2x2, 電腦版 4x1 (響應式由 Streamlit 處理，但我們用 columns 控制)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>📦 總庫存資產</div><div class='metric-value'>{total_qty:,}</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>💎 預估總營收</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
    with m3:
        # 這裡加上 RMB 備註
        rmb_note = f"<div style='font-size:11px; color:#888;'>其中包含人民幣庫存:<br>¥ {rmb_stock_value:,}</div>"
        st.markdown(f"<div class='metric-card'><div class='metric-label'>💰 庫存總成本 (TWD)</div><div class='metric-value'>${total_cost:,}</div>{rmb_note}</div>", unsafe_allow_html=True)
    with m4:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>📈 潛在毛利</div><div class='metric-value' style='color:#28a745 !important'>${profit:,}</div></div>", unsafe_allow_html=True)

    if not df.empty:
        low_stock = df[df['Qty'] < df['Safe_Level']]
        cc1, cc2 = st.columns([2, 1])
        with cc1:
            st.caption("📊 庫存價值分佈")
            if total_qty > 0:
                fig = px.bar(df.groupby('Category')['Qty'].sum().reset_index(), x='Category', y='Qty', color='Category', color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
        with cc2:
            st.caption(f"🚨 缺貨預警 ({len(low_stock)})")
            if not low_stock.empty:
                disp_low = low_stock[['SKU', 'Name', 'Qty', 'Safe_Level']]
                st.dataframe(disp_low, hide_index=True, use_container_width=True)
            else: st.info("庫存健康")

    st.markdown("---")

    # --- Tabs ---
    tabs = st.tabs(["⚡ POS & 進貨", "🎁 內部領用", "📦 商品管理", "📝 日誌", "👥 Admin"])

    # Tab 1: POS & Restock
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
                
                # 雙幣顯示
                orig_cost_display = ""
                if target['Orig_Currency'] == 'CNY':
                    orig_cost_display = f"<span class='cost-tag'>原幣: ¥{target['Orig_Cost']}</span>"
                
                st.markdown(f"""
                <div style="display:flex; align-items:center; background:#f9f9f9; padding:15px; border-radius:10px;">
                    <img src="{img}" style="width:80px; height:80px; border-radius:8px; object-fit:cover; margin-right:15px;">
                    <div>
                        <div style="font-weight:bold; font-size:18px;">{target['Name']}</div>
                        <div style="color:#666;">{target['SKU']}</div>
                        <div style="color:#333; margin-top:5px;">成本: <b>NT${target['Cost']}</b> {orig_cost_display}</div>
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
                    st.markdown("###### 💰 進貨成本設定")
                    cost_currency = st.radio("計價幣別", ["NTD (台幣)", "CNY (人民幣)"], horizontal=True)
                    input_unit_cost = st.number_input("單價", value=0.0)
                    
                    final_cost_twd = 0
                    if cost_currency == "CNY (人民幣)":
                        rate = st.session_state['exchange_rate']
                        final_cost_twd = int(input_unit_cost * rate)
                        st.info(f"💱 ¥{input_unit_cost} x {rate} = NT${final_cost_twd}")
                    else:
                        final_cost_twd = int(input_unit_cost)
                    
                    note_in = st.text_input("進貨備註")
                    
                    if st.button("確認進貨", type="secondary", use_container_width=True):
                        current_qty = int(target['Qty']); current_cost = int(target['Cost'])
                        total_new_qty = current_qty + qty
                        
                        if total_new_qty > 0:
                            cost_to_calc = final_cost_twd if final_cost_twd > 0 else current_cost
                            new_avg_cost = int( ( (current_qty * current_cost) + (qty * cost_to_calc) ) / total_new_qty )
                        else: new_avg_cost = final_cost_twd
                        
                        r = ws_items.find(target['SKU']).row
                        ws_items.update_cell(r, 5, total_new_qty)
                        ws_items.update_cell(r, 7, new_avg_cost)
                        ws_items.update_cell(r, 8, str(datetime.now()))
                        
                        # V30.1: 更新原始幣別資訊 (如果這次進貨是 CNY，就更新這件商品的來源紀錄)
                        if cost_currency == "CNY (人民幣)":
                            ws_items.update_cell(r, 11, "CNY") # Orig_Currency
                            ws_items.update_cell(r, 12, int(input_unit_cost)) # Orig_Cost

                        log_detail = f"{target['SKU']} +{qty} | "
                        if cost_currency == "CNY (人民幣)": log_detail += f"原幣:¥{input_unit_cost} -> "
                        log_detail += f"均價:${new_avg_cost} | {note_in}"

                        log_event(ws_logs, st.session_state['user_name'], "Restock", log_detail)
                        st.success(f"進貨成功！新成本 NT${new_avg_cost}"); time.sleep(1); st.rerun()

                with t2:
                    note_out = st.text_input("銷售備註")
                    if st.button("確認銷售", type="primary", use_container_width=True):
                        if int(target['Qty']) >= qty:
                            r = ws_items.find(target['SKU']).row
                            new_q = int(target['Qty']) - qty
                            ws_items.update_cell(r, 5, new_q)
                            ws_items.update_cell(r, 8, str(datetime.now()))
                            log_event(ws_logs, st.session_state['user_name'], "Sale", f"{target['SKU']} -{qty} | {note_out}")
                            if new_q < int(target['Safe_Level']): send_line_push(f"缺貨: {target['Name']}")
                            st.success("銷售成功"); time.sleep(1); st.rerun()
                        else: st.error("庫存不足")

    # Tab 2: 內部領用
    with tabs[1]:
        st.subheader("🎁 內部領用中心")
        c_int1, c_int2 = st.columns([1, 1])
        with c_int1:
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist()
            sel_int = st.selectbox("選擇領用商品", ["..."] + opts, key="internal_sel")
            target_int = None
            if sel_int != "...":
                target_int = df[df['SKU'] == sel_int.split(" | ")[0]].iloc[0]
                img = render_image_url(target_int['Image_URL'])
                
                orig_show = ""
                if target_int['Orig_Currency'] == 'CNY':
                    orig_show = f"(原幣: ¥{target_int['Orig_Cost']})"

                st.markdown(f"""
                <div style="background:#fff3e0; padding:15px; border-radius:10px; border:1px solid #ffe0b2;">
                    <div style="font-weight:bold; color:#e65100;">{target_int['Name']}</div>
                    <div>SKU: {target_int['SKU']}</div>
                    <div>當前庫存: {target_int['Qty']}</div>
                    <div style="font-size:12px; color:#666;">單位成本: NT${target_int['Cost']} {orig_show}</div>
                </div>
                """, unsafe_allow_html=True)

        with c_int2:
            if target_int is not None:
                with st.form("internal_use_form"):
                    int_qty = st.number_input("領用數量", 1, max_value=int(target_int['Qty']))
                    staff_sel = st.selectbox("領用人", staff_list if staff_list else ["Boss"])
                    reason = st.selectbox("領用類別", ["公務制服", "員工福利", "樣品借出", "瑕疵報廢", "其他"])
                    int_note = st.text_input("備註 (可選)")
                    
                    if st.form_submit_button("確認領用 (扣除庫存)", type="primary"):
                        r = ws_items.find(target_int['SKU']).row
                        new_q = int(target_int['Qty']) - int_qty
                        ws_items.update_cell(r, 5, new_q)
                        ws_items.update_cell(r, 8, str(datetime.now()))
                        total_cost_value = int(target_int['Cost']) * int_qty
                        log_msg = f"{target_int['SKU']} -{int_qty} | 領用:{staff_sel} | {reason} | 成本總值:${total_cost_value} | {int_note}"
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", log_msg)
                        st.success(f"領用成功！扣除成本價值 NT${total_cost_value}"); time.sleep(2); st.rerun()

    # Tab 3: 商品管理
    with tabs[2]:
        with st.expander("➕ 新增商品", expanded=False):
            with st.form("new_prod"):
                sku = st.text_input("貨號 (SKU)")
                name = st.text_input("品名")
                c1, c2, c3, c4 = st.columns(4)
                cat = c1.selectbox("分類", ["上衣", "褲子", "外套", "配件", "其他"])
                size = c2.selectbox("尺寸", ["F","S","M","L","XL"])
                price = c3.number_input("售價 (NTD)", 0)
                
                c_cost_curr, c_cost_val = c4.columns([1, 1])
                curr_sel = c_cost_curr.selectbox("成本幣別", ["TWD", "CNY"])
                cost_input = c_cost_val.number_input("成本金額", 0)

                c5, c6 = st.columns(2)
                q = c5.number_input("初始數量", 0)
                safe_s = c6.number_input("安全庫存", 5)
                img = st.file_uploader("圖片", type=['jpg','png'])
                
                final_cost_db = cost_input
                if curr_sel == "CNY":
                    final_cost_db = int(cost_input * st.session_state['exchange_rate'])
                    st.markdown(f"<div class='rate-info'>💱 自動存入: <b>NT$ {final_cost_db}</b> (匯率 {st.session_state['exchange_rate']})</div>", unsafe_allow_html=True)
                
                if st.form_submit_button("上架"):
                    if sku and name:
                        if sku in df['SKU'].tolist(): st.error("SKU 已存在")
                        else:
                            u = upload_image_to_imgbb(img) if img else ""
                            # V30.1: 寫入 Orig_Currency 和 Orig_Cost
                            orig_cur_code = "CNY" if curr_sel == "CNY" else "TWD"
                            ws_items.append_row([sku, name, cat, size, q, price, final_cost_db, str(datetime.now()), u, safe_s, orig_cur_code, cost_input])
                            
                            log_msg = f"新增: {sku}"
                            if curr_sel == "CNY": log_msg += f" (原幣: ¥{cost_input})"
                            log_event(ws_logs, st.session_state['user_name'], "New_Item", log_msg)
                            st.success("成功"); time.sleep(1); st.rerun()
                    else: st.error("缺漏必填")

        st.dataframe(df, use_container_width=True)

    # Tab 4: Log
    with tabs[3]:
        st.subheader("🕵️ 稽核日誌")
        col_filter1, col_filter2, col_filter3 = st.columns([1, 1, 1])
        with col_filter1: search_date = st.date_input("📅 日期", value=None)
        with col_filter2:
            action_map = {"全部": "All", "內部領用": "Internal_Use", "銷售": "Sale", "進貨": "Restock", "登入": "Login", "新增": "New_Item", "人事": "HR", "安全": "Security"}
            s_act = st.selectbox("🔍 動作", list(action_map.keys()))
        with col_filter3: search_keyword = st.text_input("🔤 關鍵字")

        logs_df = get_data_safe(ws_logs)
        if not logs_df.empty:
            logs_df['Timestamp'] = pd.to_datetime(logs_df['Timestamp'], errors='coerce')
            logs_df['DateObj'] = logs_df['Timestamp'].dt.date
            display_logs = logs_df.copy()
            if search_date: display_logs = display_logs[display_logs['DateObj'] == search_date]
            if action_map[s_act] != "All": display_logs = display_logs[display_logs['Action'] == action_map[s_act]]
            if search_keyword: display_logs = display_logs[display_logs.apply(lambda row: search_keyword.lower() in str(row).lower(), axis=1)]
            
            if not display_logs.empty:
                display_logs['Timestamp'] = display_logs['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                st.dataframe(display_logs.drop(columns=['DateObj']).sort_index(ascending=False), use_container_width=True, height=500)
            else: st.info("無資料")
        else: st.warning("無紀錄")

    # Tab 5: Admin
    with tabs[4]:
        if st.session_state['user_role'] == 'Admin':
            st.subheader("👥 人員管理")
            users_df = get_data_safe(ws_users)
            st.dataframe(users_df[['Name', 'Role', 'Status', 'Created_At']], use_container_width=True)
            st.divider()
            c_adm1, c_adm2 = st.columns(2)
            with c_adm1:
                with st.form("hr_form"):
                    u_name = st.text_input("帳號"); u_pass = st.text_input("密碼", type="password")
                    u_role = st.selectbox("權限", ["Staff", "Admin"]); u_stat = st.selectbox("狀態", ["Active", "Inactive"])
                    if st.form_submit_button("執行"):
                        if u_name and u_pass:
                            hashed = make_hash(u_pass)
                            try:
                                cell = ws_users.find(u_name, in_column=1)
                                r = cell.row
                                ws_users.update_cell(r, 2, hashed); ws_users.update_cell(r, 3, u_role); ws_users.update_cell(r, 4, u_stat)
                                st.success(f"已更新: {u_name}")
                            except:
                                ws_users.append_row([u_name, hashed, u_role, u_stat, str(datetime.now())])
                                st.success(f"已新增: {u_name}")
                            log_event(ws_logs, st.session_state['user_name'], "HR", f"Update: {u_name}"); time.sleep(1); st.rerun()

            with c_adm2:
                if st.button("☢️ 清空日誌"):
                    ws_logs.clear(); ws_logs.append_row(["Timestamp", "User", "Action", "Details"])
                    log_event(ws_logs, st.session_state['user_name'], "Security", "Clear Logs"); st.rerun()
        else: st.error("權限不足")

if __name__ == "__main__":
    main()
