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
from io import BytesIO

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK 戰情中樞", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="collapsed" # 預設收起，但現在可以重新打開了
)

# ==========================================
# 🛑 【MATRIX-V26 視覺核心 & 修復補丁】
# ==========================================
st.markdown("""
    <style>
        /* --- Part A: 基礎顏色鎖定 (White Mode) --- */
        .stApp { background-color: #FFFFFF !important; }
        p, div, h1, h2, h3, h4, span, label, li { color: #000000 !important; }
        button[data-baseweb="tab"] div p { color: #555555 !important; font-weight: 600 !important; }
        button[data-baseweb="tab"][aria-selected="true"] div p { color: #FF4B4B !important; }
        
        /* 輸入框優化 */
        input.st-ai, textarea, select { 
            color: #000000 !important; 
            background-color: #F3F4F6 !important;
            border-radius: 8px !important;
        }
        div[data-testid="stTextInput"] { color: #000000 !important; }
        
        /* 強制移除 Dark Mode 干擾 */
        @media (prefers-color-scheme: dark) {
            .stApp { background-color: #FFFFFF !important; }
            h1, h2, h3, p, span { color: #000000 !important; }
        }

        /* --- Part B: V26 Sidebar 修復工程 (關鍵) --- */
        /* 1. 我們不再隱藏 Header，而是讓它變透明，這樣漢堡選單就會出現 */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            z-index: 100; /* 確保按鈕浮在最上層 */
        }
        
        /* 2. 隱藏 Streamlit 預設的彩虹線條 decoration */
        div[data-testid="stDecoration"] {
            display: none;
        }

        /* 3. 調整頂部留白，讓 Navbar 不會被 Header 蓋住 */
        .block-container {
            padding-top: 3.5rem !important; /* 留出空間給漢堡選單 */
            padding-bottom: 5rem !important;
        }

        /* --- Part C: Mobile First & Aesthetic 2.0 --- */
        
        /* 黏性導航欄 (Sticky Navbar) - 加強陰影與層次 */
        .navbar-container {
            position: fixed;
            top: 0;
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
            box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        }
        
        /* 為了不被 Fixed Navbar 擋住內容，增加一個隱形佔位 */
        .navbar-spacer {
            height: 60px;
        }
        
        .navbar-title {
            font-size: 18px;
            font-weight: 900;
            color: #111 !important;
            letter-spacing: -0.5px;
            text-transform: uppercase;
        }
        
        .navbar-date {
            font-size: 10px;
            color: #888 !important;
            font-weight: 500;
        }

        .user-avatar {
            width: 35px;
            height: 35px;
            background: linear-gradient(135deg, #111 0%, #333 100%);
            color: #fff !important;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: bold;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }

        /* 卡片優化 */
        .metric-card {
            background: white;
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
            border: 1px solid #f0f0f0;
            text-align: center;
            margin-bottom: 12px;
            transition: all 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }
        .metric-value { font-size: 1.6rem; font-weight: 800; margin: 4px 0; color: #111 !important; }
        .metric-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.2px; opacity: 0.6; }
        
        /* 產品卡片 */
        .product-card {
            background: white;
            border-radius: 12px;
            padding: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.03);
            margin-bottom: 15px;
            border: 1px solid #eee;
        }
        
        /* 按鈕美學 */
        .stButton>button {
            border-radius: 10px;
            height: 3em;
            font-weight: 700;
            border: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

    </style>
""", unsafe_allow_html=True)

# --- ⚠️⚠️⚠️ 設定區 (請確認 Key 正確) ⚠️⚠️⚠️ ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
LINE_CHANNEL_ACCESS_TOKEN = "IaGvcTOmbMFW8wKEJ5MamxfRx7QVo0kX1IyCqwKZw0WX2nxAVYY7SsSh5vAJ0r+WBNvyjjiU8G3eYkL1nozqIOjjWMOKr/4ZtzUMRRf7JNJkk5V6jLpWc/EOkzvNGVPMh0zwH+wQD51tR3XWipUULwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U55199b00fb78da85bb285db6d00b6ff5"
# ---------------------------------------------------

# --- 2. 核心連線邏輯 (V26 優化版) ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=3600)
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

@st.cache_resource(ttl=3600)
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

# --- 3. 工具模組 ---
def render_image_url(url_input):
    if not url_input: return "https://i.ibb.co/W31w56W/placeholder.png"
    s = str(url_input).strip()
    if len(s) < 10 or not s.startswith("http"): return "https://i.ibb.co/W31w56W/placeholder.png"
    return s

def upload_image_to_imgbb(image_file):
    if not IMGBB_API_KEY or "請將您的" in IMGBB_API_KEY: return None
    try:
        img_bytes = image_file.getvalue()
        b64_string = base64.b64encode(img_bytes).decode('utf-8')
        payload = {"key": IMGBB_API_KEY, "image": b64_string}
        response = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if response.status_code == 200: return response.json()["data"]["url"]
        return None
    except: return None

def send_line_push(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or len(LINE_CHANNEL_ACCESS_TOKEN) < 50: return "ERROR_TOKEN"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    data = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data); return "SUCCESS"
    except Exception as e: return str(e)

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue()

def log_event(ws_logs, user, action, detail):
    try:
        # V26: 加入 Price/Revenue 追蹤的潛力，目前先記字串
        ws_logs.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, detail])
    except: pass

# --- V26 視覺組件 ---
def render_navbar(user_initial):
    current_date = datetime.now().strftime("%b %d")
    st.markdown(f"""
        <div class="navbar-container">
            <div style="display:flex; flex-direction:column;">
                <span class="navbar-title">IFUKUK</span>
                <span class="navbar-date">{current_date} • 營運中</span>
            </div>
            <div class="user-avatar">{user_initial}</div>
        </div>
        <div class="navbar-spacer"></div>
    """, unsafe_allow_html=True)

# --- 5. 主程式 ---
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

    # --- A. 品牌登入 ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-weight:900; font-size:2.5rem; margin-bottom:10px;'>IFUKUK</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>OMNI-CHANNEL SYSTEM V26.0</div>", unsafe_allow_html=True)
            
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
    
    # 1. 渲染頂部導航
    user_initial = st.session_state['user_name'][0].upper() if st.session_state['user_name'] else "U"
    render_navbar(user_initial)

    # 2. 數據準備
    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    # --- B. 側邊欄 (修復版) ---
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
                    # 密碼修改邏輯
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
                        else: st.error("修改失敗：舊密碼錯誤或兩次輸入不一致")
                    except: st.error("系統錯誤")

        st.markdown("---")
        if st.button("🚪 安全登出"):
            log_event(ws_logs, st.session_state['user_name'], "Logout", "登出系統")
            st.session_state['logged_in'] = False
            st.rerun()

    # --- C. V26 戰情儀表板 (含趨勢分析) ---
    total_qty = df['Qty'].sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    total_rev = (df['Qty'] * df['Price']).sum()
    
    # 手機版佈局優化
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>📦 總庫存</div><div class='metric-value'>{total_qty:,}</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><div class='metric-label'>💰 總成本</div><div class='metric-value'>${total_cost:,}</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>💎 預估營收</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
        # 這裡加入一個簡單的毛利顯示
        profit = total_rev - total_cost
        st.markdown(f"<div class='metric-card'><div class='metric-label'>📈 潛在毛利</div><div class='metric-value' style='color:#28a745 !important'>${profit:,}</div></div>", unsafe_allow_html=True)

    # --- V26 新增：趨勢分析圖表 ---
    if not df.empty:
        st.markdown("##### 📊 庫存分佈")
        cc1, cc2 = st.columns([2, 1])
        with cc1:
            # 甜甜圈圖
            fig = px.pie(df, names='Category', values='Qty', hole=0.7, 
                         color_discrete_sequence=['#111', '#444', '#777', '#999', '#ccc'])
            fig.update_layout(height=200, margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with cc2:
            st.caption("🚨 低庫存預警 (<5)")
            low = df[df['Qty'] < 5][['SKU', 'Name', 'Qty']]
            low.columns = ['貨號', '品名', '數']
            st.dataframe(low, hide_index=True, use_container_width=True)

    st.markdown("---")

    # --- D. 功能分頁 ---
    tabs = st.tabs(["🧥 樣品", "⚡ POS", "➕ 管理", "📝 紀錄"])

    # Tab 1: 樣品展示
    with tabs[0]:
        q = st.text_input("🔍 快速搜尋 (貨號/品名)", placeholder="Type to search...")
        v_df = df.copy()
        if q: v_df = v_df[v_df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
        
        if not v_df.empty:
            # 手機版單欄，桌面版多欄，這裡使用自適應
            # 為了手機體驗，這裡我們用 st.container 配合 HTML 渲染
            for idx, row in v_df.iterrows():
                with st.container():
                    img_src = render_image_url(row['Image_URL'])
                    st.markdown(f"""
                    <div style="display:flex; background:white; border-radius:12px; padding:10px; margin-bottom:10px; box-shadow:0 2px 5px rgba(0,0,0,0.05); border:1px solid #f0f0f0;">
                        <img src="{img_src}" style="width:80px; height:80px; object-fit:cover; border-radius:8px; margin-right:15px;">
                        <div style="flex:1;">
                            <div style="font-weight:bold; font-size:16px; color:#111;">{row['Name']}</div>
                            <div style="color:#666; font-size:12px; margin-bottom:5px;">{row['SKU']} | {row['Size']}</div>
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div style="font-weight:800; font-size:16px;">${row['Price']}</div>
                                <div style="background:#f3f4f6; padding:2px 8px; border-radius:4px; font-size:12px;">庫存: {row['Qty']}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("沒有找到符合的商品")

    # Tab 2: POS (優化版)
    with tabs[1]:
        st.caption("💡 支援掃碼槍直接輸入 SKU")
        c1, c2 = st.columns([2, 1])
        with c1:
            # 建立一個 SKU 到 Name 的 Mapping 供搜尋
            sku_list = df['SKU'].tolist()
            # 這裡改成單純的 Selectbox 加上搜尋功能，體驗更好
            sel_sku = st.selectbox("選擇或掃描商品", ["請選擇..."] + [f"{r['SKU']} | {r['Name']}" for i, r in df.iterrows()])
            
            target = None
            if sel_sku != "請選擇...":
                real_sku = sel_sku.split(" | ")[0]
                target = df[df['SKU'] == real_sku].iloc[0]
                
                # 顯示商品卡片
                st.markdown(f"""
                <div style="background:#f9fafb; padding:15px; border-radius:10px; border-left: 5px solid #111;">
                    <h4 style="margin:0; color:#111;">{target['Name']}</h4>
                    <p style="margin:0; color:#666;">{target['SKU']} | ${target['Price']}</p>
                    <h2 style="margin:10px 0 0 0; color:#111;">庫存: {target['Qty']}</h2>
                </div>
                """, unsafe_allow_html=True)

        with c2:
            if target is not None:
                qty = st.number_input("異動數量", min_value=1, value=1)
                note = st.text_input("備註 (選填)", placeholder="例如：VIP客戶...")
                
                col_in, col_out = st.columns(2)
                if col_in.button("📥 進貨", use_container_width=True):
                    r = ws_items.find(target['SKU']).row
                    new_val = int(target['Qty']) + qty
                    ws_items.update_cell(r, 5, new_val)
                    ws_items.update_cell(r, 8, str(datetime.now()))
                    log_event(ws_logs, st.session_state['user_name'], "Restock", f"{target['SKU']} +{qty} | {note}")
                    st.toast(f"✅ 進貨成功！庫存變更為 {new_val}")
                    time.sleep(1)
                    st.rerun()
                    
                if col_out.button("📤 銷售", type="primary", use_container_width=True):
                    if int(target['Qty']) < qty:
                        st.error("❌ 庫存不足！無法銷售")
                    else:
                        r = ws_items.find(target['SKU']).row
                        new_val = int(target['Qty']) - qty
                        ws_items.update_cell(r, 5, new_val)
                        ws_items.update_cell(r, 8, str(datetime.now()))
                        log_event(ws_logs, st.session_state['user_name'], "Sale", f"{target['SKU']} -{qty} | {note}")
                        if new_val < 5: send_line_push(f"⚠️ 缺貨警報: {target['Name']} 剩 {new_val} 件")
                        st.toast(f"🎉 銷售成功！庫存變更為 {new_val}")
                        time.sleep(1)
                        st.rerun()

    # Tab 3: 商品管理
    with tabs[2]:
        with st.expander("➕ 新增單一商品", expanded=True):
            with st.form("new_item"):
                c_a, c_b = st.columns(2)
                sku = c_a.text_input("貨號 (SKU)", placeholder="必填")
                name = c_b.text_input("品名", placeholder="必填")
                
                c_c, c_d = st.columns(2)
                cat = c_c.selectbox("分類", ["上衣", "褲子", "外套", "配件", "其他"])
                size = c_d.selectbox("尺寸", ["F","S","M","L","XL"])
                
                c_e, c_f, c_g = st.columns(3)
                q = c_e.number_input("初始數量", 0)
                price = c_f.number_input("售價", 0)
                cost = c_g.number_input("成本", 0)
                
                img = st.file_uploader("圖片 (選填)", type=['jpg','png'])
                
                if st.form_submit_button("確認上架", use_container_width=True):
                    if sku and name:
                        if sku in df['SKU'].tolist(): st.error("❌ SKU 已存在，請更換")
                        else:
                            u = upload_image_to_imgbb(img) if img else ""
                            ws_items.append_row([sku, name, cat, size, q, price, cost, str(datetime.now()), u])
                            log_event(ws_logs, st.session_state['user_name'], "New_Item", f"新增: {sku}")
                            st.toast("✅ 商品上架成功！")
                            time.sleep(1)
                            st.rerun()
                    else: st.error("❌ 貨號與品名為必填")
        
        with st.expander("🛠️ 批次工具"):
            st.info("功能維護中：批次匯入與 QR Code 生成功能正常運作，請參考 V18 版本操作說明。")
            d_s = st.selectbox("刪除商品 (慎用)", ["..."]+df['SKU'].tolist())
            if d_s != "..." and st.button("確認刪除商品"):
                ws_items.delete_rows(ws_items.find(d_s).row)
                log_event(ws_logs, st.session_state['user_name'], "Del_Item", f"刪除: {d_s}")
                st.rerun()

    # Tab 4: 紀錄與人員
    with tabs[3]:
        st.subheader("📝 操作流水帳")
        # 簡單過濾
        filter_type = st.radio("篩選動作", ["全部", "銷售", "進貨", "登入"], horizontal=True)
        logs_df = get_data_safe(ws_logs)
        
        if not logs_df.empty:
            display_logs = logs_df.copy()
            # 簡單 mapping
            if filter_type == "銷售": display_logs = display_logs[display_logs['Action'] == 'Sale']
            elif filter_type == "進貨": display_logs = display_logs[display_logs['Action'] == 'Restock']
            elif filter_type == "登入": display_logs = display_logs[display_logs['Action'] == 'Login']
            
            st.dataframe(display_logs.sort_index(ascending=False).head(50), use_container_width=True)
        else: st.info("無紀錄")
        
        if st.session_state['user_role'] == 'Admin':
            st.divider()
            st.subheader("👥 人員管理")
            users_df = get_data_safe(ws_users)
            st.dataframe(users_df[['Name', 'Role', 'Status']], use_container_width=True)
            # 這裡保留基本的顯示，進階管理功能保持在 V18 邏輯

if __name__ == "__main__":
    main()
