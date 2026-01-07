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
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【MATRIX-V28 視覺與體驗核心】
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

        /* 數據儀表板卡片 */
        .metric-card {
            background: white; border-radius: 12px; padding: 20px;
            border: 1px solid #f0f0f0; text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            margin-bottom: 10px; transition: all 0.2s;
        }
        .metric-card:hover { border-color: #000; transform: translateY(-2px); }
        .metric-value { font-size: 1.8rem; font-weight: 800; margin: 5px 0; color:#111 !important; }
        .metric-label { font-size: 0.85rem; letter-spacing: 1px; color:#555 !important; font-weight: 600; }
        
        /* 列表優化 */
        .list-card {
            background: #fff; border: 1px solid #eee; border-radius: 8px;
            padding: 12px; margin-bottom: 8px; display: flex; align-items: center;
        }
        
        /* 按鈕優化 */
        .stButton>button { border-radius: 8px; height: 3em; font-weight: 600; border:none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stButton>button:hover { box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
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

# --- V28 專業工具模組 ---

# 1. 密碼加密 (SHA-256)
def make_hash(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def check_hash(password, hashed_text):
    return make_hash(password) == hashed_text

# 2. 圖片與其他
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
    st.markdown(f"""
        <div class="navbar-container">
            <div style="display:flex; flex-direction:column;">
                <span style="font-size:18px; font-weight:900; color:#111;">IFUKUK SYSTEM</span>
                <span style="font-size:11px; color:#666; font-family:monospace;">{current_date} • ADMIN ACCESS</span>
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

    sh = init_db()
    if not sh: st.error("Database Connection Failed"); st.stop()

    # V28: 增加 Safety_Stock 欄位
    ws_items = get_worksheet_safe(sh, "Items", ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock"])
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    if not ws_items or not ws_logs or not ws_users: st.warning("Initializing..."); st.stop()

    # --- 登入頁面 (V28 加密版) ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-weight:900; font-size:2.5rem; margin-bottom:10px;'>IFUKUK</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>ENTERPRISE RESOURCE PLANNING V28</div>", unsafe_allow_html=True)
            
            with st.form("login"):
                user_input = st.text_input("帳號 (ID)")
                pass_input = st.text_input("密碼 (Password)", type="password")
                if st.form_submit_button("登入 (LOGIN)", type="primary"):
                    users_df = get_data_safe(ws_users)
                    input_u = str(user_input).strip()
                    input_p = str(pass_input).strip()
                    
                    # 1. 初始化老闆帳號 (如果沒有人)
                    if users_df.empty and input_u == "Boss" and input_p == "1234":
                        hashed_pw = make_hash("1234")
                        ws_users.append_row(["Boss", hashed_pw, "Admin", "Active", str(datetime.now())])
                        st.success("系統初始化完成：Boss 帳號已建立 (密碼已加密)")
                        time.sleep(1)
                        st.rerun()

                    # 2. 正常登入驗證
                    if not users_df.empty:
                        users_df['Name'] = users_df['Name'].astype(str).str.strip()
                        users_df['Password'] = users_df['Password'].astype(str).str.strip()
                        
                        target_user = users_df[(users_df['Name'] == input_u) & (users_df['Status'] == 'Active')]
                        
                        if not target_user.empty:
                            stored_hash = target_user.iloc[0]['Password']
                            # 支援舊明碼過渡期：如果資料庫是明碼，直接比對；如果是 hash，用 check_hash
                            is_valid = False
                            if len(stored_hash) == 64: # SHA256 長度通常是 64
                                is_valid = check_hash(input_p, stored_hash)
                            else:
                                is_valid = (input_p == stored_hash) # 舊明碼相容

                            if is_valid:
                                st.session_state['logged_in'] = True
                                st.session_state['user_name'] = input_u
                                st.session_state['user_role'] = target_user.iloc[0]['Role']
                                log_event(ws_logs, input_u, "Login", "登入成功")
                                st.rerun()
                            else: st.error("密碼錯誤")
                        else: st.error("帳號不存在或已停用")
                    else: st.error("系統無資料，請使用 Boss 初始化")
        return

    # --- 系統主畫面 ---
    user_initial = st.session_state['user_name'][0].upper()
    render_navbar(user_initial)

    # 資料準備
    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost', 'Safety_Stock']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    # 若 Safety_Stock 為 0 (未設定)，預設視為 5
    df['Safe_Level'] = df['Safety_Stock'].apply(lambda x: 5 if x == 0 else x)
    df['SKU'] = df['SKU'].astype(str)

    # --- 側邊欄 ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_label = "🔴 Admin" if st.session_state['user_role'] == 'Admin' else "🟢 Staff"
        st.caption(f"Role: {role_label}")
        
        with st.expander("⚙️ 安全設定 (Security)"):
            with st.form("pwd"):
                old = st.text_input("舊密碼", type="password")
                new = st.text_input("新密碼", type="password")
                confirm = st.text_input("確認新密碼", type="password")
                if st.form_submit_button("修改密碼"):
                    if not old or not new: st.error("請輸入完整")
                    elif new != confirm: st.error("新密碼不一致")
                    else:
                        try:
                            # 尋找使用者
                            raw_data = ws_users.get_all_values()
                            user_row_idx = -1
                            for i, row in enumerate(raw_data):
                                if str(row[0]).strip() == st.session_state['user_name']:
                                    user_row_idx = i + 1; stored_pwd = str(row[1]).strip(); break
                            
                            # 驗證舊密碼 (Hash or Plain)
                            is_valid = False
                            if len(stored_pwd) == 64: is_valid = check_hash(old, stored_pwd)
                            else: is_valid = (old == stored_pwd)

                            if is_valid:
                                new_hash = make_hash(new)
                                ws_users.update_cell(user_row_idx, 2, new_hash)
                                st.success("密碼已加密更新！")
                                log_event(ws_logs, st.session_state['user_name'], "Security", "Password Updated")
                            else: st.error("舊密碼錯誤")
                        except: st.error("系統錯誤")

        st.markdown("---")
        if st.button("🚪 安全登出"):
            log_event(ws_logs, st.session_state['user_name'], "Logout", "登出系統")
            st.session_state['logged_in'] = False
            st.rerun()

    # --- Dashboard ---
    total_qty = df['Qty'].sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    total_rev = (df['Qty'] * df['Price']).sum()
    profit = total_rev - total_cost

    m1, m2 = st.columns(2)
    with m1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>📦 總庫存資產</div><div class='metric-value'>{total_qty:,}</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><div class='metric-label'>💰 庫存總成本</div><div class='metric-value'>${total_cost:,}</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>💎 預估總營收</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><div class='metric-label'>📈 潛在毛利</div><div class='metric-value' style='color:#28a745 !important'>${profit:,}</div></div>", unsafe_allow_html=True)

    # 庫存健康度分析
    if not df.empty:
        # V28: 智慧缺貨邏輯 (庫存 < 安全水位)
        low_stock = df[df['Qty'] < df['Safe_Level']]
        
        cc1, cc2 = st.columns([2, 1])
        with cc1:
            st.caption("📊 庫存價值分佈 (按分類)")
            if total_qty > 0:
                fig = px.bar(df.groupby('Category')['Qty'].sum().reset_index(), x='Category', y='Qty', color='Category', color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
        with cc2:
            st.caption(f"🚨 缺貨警報 ({len(low_stock)} 項)")
            if not low_stock.empty:
                disp_low = low_stock[['SKU', 'Name', 'Qty', 'Safe_Level']]
                disp_low.columns = ['貨號', '品名', '現貨', '警戒線']
                st.dataframe(disp_low, hide_index=True, use_container_width=True)
            else:
                st.info("庫存健康，無缺貨")

    st.markdown("---")

    # --- 功能 Tabs ---
    tabs = st.tabs(["⚡ POS & 進貨", "📦 商品與庫存", "📝 稽核日誌", "👥 管理中心"])

    # Tab 1: POS & Restock (含加權平均成本算法)
    with tabs[0]:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("商品掃描 / 選擇")
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist()
            sel = st.selectbox("請選擇商品", ["..."] + opts)
            target = None
            if sel != "...":
                target = df[df['SKU'] == sel.split(" | ")[0]].iloc[0]
                img = render_image_url(target['Image_URL'])
                st.markdown(f"""
                <div style="display:flex; align-items:center; background:#f9f9f9; padding:15px; border-radius:10px;">
                    <img src="{img}" style="width:80px; height:80px; border-radius:8px; object-fit:cover; margin-right:15px;">
                    <div>
                        <div style="font-weight:bold; font-size:18px;">{target['Name']}</div>
                        <div style="color:#666;">{target['SKU']} | 成本: ${target['Cost']}</div>
                        <div style="font-weight:bold; color:#d32f2f; font-size:20px;">現有庫存: {target['Qty']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with c2:
            st.subheader("異動操作")
            if target is not None:
                qty = st.number_input("數量", 1)
                
                t1, t2 = st.tabs(["📥 進貨 (Restock)", "📤 銷售 (Sale)"])
                
                with t1:
                    new_cost_input = st.number_input("本次進貨單價 (成本)", value=int(target['Cost']))
                    note_in = st.text_input("進貨備註", placeholder="例：廠商A補貨")
                    if st.button("確認進貨", type="secondary", use_container_width=True):
                        # V28 核心演算法：加權平均成本 (Weighted Average Cost)
                        current_qty = int(target['Qty'])
                        current_cost = int(target['Cost'])
                        
                        # 避免除以零
                        total_new_qty = current_qty + qty
                        if total_new_qty > 0:
                            # 公式：(舊總值 + 新總值) / 總數量
                            new_avg_cost = int( ( (current_qty * current_cost) + (qty * new_cost_input) ) / total_new_qty )
                        else:
                            new_avg_cost = new_cost_input
                            
                        # 寫入
                        r = ws_items.find(target['SKU']).row
                        ws_items.update_cell(r, 5, total_new_qty)       # 更新數量
                        ws_items.update_cell(r, 7, new_avg_cost)        # 更新加權成本
                        ws_items.update_cell(r, 8, str(datetime.now())) # 更新時間
                        
                        log_msg = f"{target['SKU']} +{qty} | 成本變更: {current_cost}->{new_avg_cost} | {note_in}"
                        log_event(ws_logs, st.session_state['user_name'], "Restock", log_msg)
                        st.success(f"進貨成功！成本已加權平均為 ${new_avg_cost}")
                        time.sleep(2)
                        st.rerun()

                with t2:
                    note_out = st.text_input("銷售備註")
                    if st.button("確認銷售", type="primary", use_container_width=True):
                        if int(target['Qty']) >= qty:
                            r = ws_items.find(target['SKU']).row
                            new_q = int(target['Qty']) - qty
                            ws_items.update_cell(r, 5, new_q)
                            ws_items.update_cell(r, 8, str(datetime.now()))
                            
                            log_event(ws_logs, st.session_state['user_name'], "Sale", f"{target['SKU']} -{qty} | {note_out}")
                            
                            # 檢查安全庫存
                            safe_lv = int(target['Safe_Level'])
                            if new_q < safe_lv:
                                send_line_push(f"⚠️ 缺貨警報: {target['Name']} 剩 {new_q} (低於安全水位 {safe_lv})")
                            
                            st.success("銷售成功")
                            time.sleep(1)
                            st.rerun()
                        else: st.error("庫存不足！")

    # Tab 2: 商品管理
    with tabs[1]:
        with st.expander("➕ 新增商品 / 修改安全庫存", expanded=False):
            with st.form("new_prod"):
                sku = st.text_input("貨號 (SKU)")
                name = st.text_input("品名")
                c1, c2, c3, c4 = st.columns(4)
                cat = c1.selectbox("分類", ["上衣", "褲子", "外套", "配件", "其他"])
                size = c2.selectbox("尺寸", ["F","S","M","L","XL"])
                price = c3.number_input("售價", 0)
                cost = c4.number_input("成本", 0)
                
                c5, c6 = st.columns(2)
                q = c5.number_input("初始數量", 0)
                safe_s = c6.number_input("安全庫存水位 (預設5)", 5) # V28 新功能
                
                img = st.file_uploader("圖片", type=['jpg','png'])
                
                if st.form_submit_button("建立 / 上架"):
                    if sku and name:
                        if sku in df['SKU'].tolist(): 
                            st.error("SKU 已存在")
                        else:
                            u = upload_image_to_imgbb(img) if img else ""
                            # V28: 寫入包含 Safety_Stock
                            ws_items.append_row([sku, name, cat, size, q, price, cost, str(datetime.now()), u, safe_s])
                            log_event(ws_logs, st.session_state['user_name'], "New_Item", f"新增: {sku}")
                            st.success("上架成功")
                            time.sleep(1)
                            st.rerun()
                    else: st.error("必填欄位缺漏")

        st.markdown("##### 📦 庫存總表")
        st.dataframe(df, use_container_width=True)

    # Tab 3: Log
    with tabs[2]:
        st.subheader("稽核日誌")
        logs_df = get_data_safe(ws_logs)
        st.dataframe(logs_df.sort_index(ascending=False).head(100), use_container_width=True)

    # Tab 4: Admin
    with tabs[3]:
        if st.session_state['user_role'] == 'Admin':
            st.subheader("👥 人員權限管理 (加密版)")
            
            users_df = get_data_safe(ws_users)
            st.dataframe(users_df[['Name', 'Role', 'Status', 'Created_At']], use_container_width=True)
            
            st.divider()
            c_adm1, c_adm2 = st.columns(2)
            
            with c_adm1:
                st.markdown("#### 新增 / 修改員工")
                with st.form("hr_form"):
                    u_name = st.text_input("帳號")
                    u_pass = st.text_input("密碼 (將自動加密)", type="password")
                    u_role = st.selectbox("權限", ["Staff", "Admin"])
                    u_stat = st.selectbox("狀態", ["Active", "Inactive"])
                    
                    if st.form_submit_button("執行"):
                        if u_name and u_pass:
                            hashed = make_hash(u_pass) # 自動加密
                            try:
                                cell = ws_users.find(u_name, in_column=1)
                                r_idx = cell.row
                                ws_users.update_cell(r_idx, 2, hashed)
                                ws_users.update_cell(r_idx, 3, u_role)
                                ws_users.update_cell(r_idx, 4, u_stat)
                                st.success(f"已更新: {u_name}")
                            except:
                                ws_users.append_row([u_name, hashed, u_role, u_stat, str(datetime.now())])
                                st.success(f"已新增: {u_name}")
                            log_event(ws_logs, st.session_state['user_name'], "HR", f"Update User: {u_name}")
                            time.sleep(1); st.rerun()

            with c_adm2:
                st.markdown("#### 系統維護")
                if st.button("🗑️ 刪除員工 (需輸入帳號)"):
                   st.info("請使用左側表單直接修改狀態為 Inactive 即可停用，保留資料以供稽核。")
                
                st.markdown("---")
                if st.button("☢️ 清空所有日誌"):
                    ws_logs.clear()
                    ws_logs.append_row(["Timestamp", "User", "Action", "Details"])
                    log_event(ws_logs, st.session_state['user_name'], "Security", "Clear Logs")
                    st.rerun()
        else:
            st.error("權限不足")

if __name__ == "__main__":
    main()
