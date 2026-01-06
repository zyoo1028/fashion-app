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

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK 核心戰情", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【MATRIX-V11 視覺強制修復補丁】開始
# 說明：此區塊強制鎖定手機版顏色，解決隱形文字問題
# ==========================================
st.markdown("""
    <style>
        /* 1. 全局強制：所有背景鎖死為白色 */
        .stApp {
            background-color: #FFFFFF !important;
        }
        
        /* 2. 暴力修正所有普通文字顏色為深黑色 */
        p, div, h1, h2, h3, h4, span, label, li {
            color: #000000 !important;
        }
        
        /* 3. 特別修復：Tab 選項卡 (解決看不見的問題) */
        /* 未選中的 Tab：深灰色 */
        button[data-baseweb="tab"] div p {
            color: #555555 !important;
            font-weight: 600 !important;
        }
        /* 被選中的 Tab：紅色高亮 */
        button[data-baseweb="tab"][aria-selected="true"] div p {
            color: #FF4B4B !important;
        }

        /* 4. 特別修復：輸入框與搜尋欄 */
        /* 輸入框背景淺灰，文字黑色 */
        input.st-ai, textarea, select {
            color: #000000 !important;
            background-color: #F0F2F6 !important;
        }
        /* 修正輸入框外圍容器 */
        div[data-testid="stTextInput"] {
            color: #000000 !important;
        }
        
        /* 5. 修正指標卡片 (Metrics) 文字 */
        div[data-testid="stMetricValue"] {
            color: #000000 !important;
        }
        div[data-testid="stMetricLabel"] {
            color: #666666 !important;
        }

        /* 6. 強制移除深色模式 (Dark Mode) 干擾 */
        @media (prefers-color-scheme: dark) {
            .stApp {
                background-color: #FFFFFF !important;
            }
            h1, h2, h3, p, span {
                color: #000000 !important;
            }
        }
    </style>
""", unsafe_allow_html=True)
# ==========================================
# 🛑 【MATRIX-V11 視覺強制修復補丁】結束
# ==========================================

# --- ⚠️⚠️⚠️ 設定區 (請填入您的 4 把鑰匙) ⚠️⚠️⚠️ ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
LINE_CHANNEL_ACCESS_TOKEN = "IaGvcTOmbMFW8wKEJ5MamxfRx7QVo0kX1IyCqwKZw0WX2nxAVYY7SsSh5vAJ0r+WBNvyjjiU8G3eYkL1nozqIOjjWMOKr/4ZtzUMRRf7JNJkk5V6jLpWc/EOkzvNGVPMh0zwH+wQD51tR3XWipUULwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U55199b00fb78da85bb285db6d00b6ff5"
# ---------------------------------------------------

# --- 自定義 CSS (用於卡片樣式) ---
st.markdown("""
    <style>
    .brand-title { font-weight: 900; font-size: 2.5rem; color: #1a1a1a !important; text-align: center; letter-spacing: 2px; margin-bottom: 20px; text-transform: uppercase; }
    .metric-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-left: 6px solid #1a1a1a; text-align: center; margin-bottom: 10px; transition: transform 0.2s; }
    .metric-value { font-size: 2rem; color: #1a1a1a !important; font-weight: 700; margin: 5px 0; }
    .metric-label { font-size: 0.85rem; color: #666 !important; font-weight: 600; letter-spacing: 1px; }
    .product-card { background: white; border-radius: 12px; padding: 10px; box-shadow: 0 3px 8px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #eee; }
    .product-card img { border-radius: 8px; width: 100%; height: 150px; object-fit: cover; }
    .user-card { background: white; border-radius: 10px; padding: 15px; border: 1px solid #e0e0e0; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; }
    .user-info { display: flex; flex-direction: column; }
    .user-name { font-weight: bold; font-size: 1.1rem; color: #333 !important; }
    .user-role { font-size: 0.8rem; color: #666 !important; background: #f0f0f0; padding: 2px 8px; border-radius: 10px; width: fit-content; margin-top: 5px; }
    .status-active { color: #28a745 !important; font-weight: bold; font-size: 0.8rem; }
    .status-inactive { color: #dc3545 !important; font-weight: bold; font-size: 0.8rem; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; height: 3em; border: none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: all 0.2s; }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 5px 10px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線邏輯 ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=3600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

# V18.0 核心升級：強制純文字讀取模式 (解決 0 vs 0000 問題)
def get_data_safe(ws):
    max_retries = 3
    for i in range(max_retries):
        try:
            if ws is None: return pd.DataFrame()
            # 關鍵修改：使用 get_all_values() 而不是 get_all_records()
            # 這會將所有內容作為字串列表返回，不進行數字轉換
            raw_data = ws.get_all_values()
            
            if not raw_data or len(raw_data) < 2: return pd.DataFrame()
            
            # 手動將第一行設為標題
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
    if not LINE_USER_ID or not LINE_USER_ID.startswith("U"): return "ERROR_ID"
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
        ws_logs.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, detail])
    except: pass

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
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<div class='brand-title'>IFUKUK</div>", unsafe_allow_html=True)
            with st.form("login"):
                user_input = st.text_input("帳號")
                pass_input = st.text_input("密碼", type="password")
                if st.form_submit_button("登入系統", type="primary"):
                    users_df = get_data_safe(ws_users)
                    if not users_df.empty:
                        # V18.0: 確保所有資料都是字串，去除前後空白
                        users_df['Name'] = users_df['Name'].astype(str).str.strip()
                        users_df['Password'] = users_df['Password'].astype(str).str.strip()
                        
                        input_u = str(user_input).strip()
                        input_p = str(pass_input).strip()
                        
                        # 嚴格比對
                        valid = users_df[(users_df['Name'] == input_u) & (users_df['Password'] == input_p) & (users_df['Status'] == 'Active')]
                        
                        if not valid.empty:
                            st.session_state['logged_in'] = True
                            st.session_state['user_name'] = input_u
                            st.session_state['user_role'] = valid.iloc[0]['Role']
                            log_event(ws_logs, input_u, "Login", "登入成功")
                            st.rerun()
                        else: st.error("帳號或密碼錯誤 (或帳號已停用)")
                    else:
                        if user_input == "Boss" and pass_input == "1234":
                            ws_users.append_row(["Boss", "1234", "Admin", "Active", str(datetime.now())])
                            st.success("初始化完成")
                        else: st.error("登入失敗")
        return

    # --- B. 數據讀取 ---
    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    # V18.0: 只對數量金額轉數字，SKU 保持字串
    for num in ['Qty', 'Price', 'Cost']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    # --- C. 側邊欄 ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_label = "🔴 Admin" if st.session_state['user_role'] == 'Admin' else "🟢 Staff"
        st.caption(f"Role: {role_label}")
        
        with st.expander("⚙️ 個人設定 (修改密碼)"):
            with st.form("pwd"):
                old = st.text_input("舊密碼", type="password")
                new = st.text_input("新密碼", type="password")
                confirm = st.text_input("確認新密碼", type="password")
                if st.form_submit_button("修改"):
                    if not old or not new: st.error("欄位不可為空")
                    elif new != confirm: st.error("新密碼不一致")
                    else:
                        try:
                            # V18.0: 徹底解決密碼比對問題
                            # 重新讀取整張表 (純文字模式)
                            raw_data = ws_users.get_all_values()
                            headers = raw_data[0]
                            # 找到 User Name 所在的 Row Index
                            user_row_idx = -1
                            current_pwd_db = ""
                            
                            for i, row in enumerate(raw_data):
                                if str(row[0]).strip() == st.session_state['user_name']:
                                    user_row_idx = i + 1 # Google Sheet 是從 1 開始，列表是從 0 開始
                                    current_pwd_db = str(row[1]).strip() # 第二欄是密碼
                                    break
                            
                            if user_row_idx == -1:
                                st.error("找不到使用者資料")
                            else:
                                input_old = str(old).strip()
                                if input_old == current_pwd_db:
                                    ws_users.update_cell(user_row_idx, 2, str(new).strip())
                                    log_event(ws_logs, st.session_state['user_name'], "Security", "修改密碼成功")
                                    st.success("✅ 密碼修改成功！")
                                    time.sleep(1)
                                else:
                                    # V18.0: 除錯模式，顯示系統讀到了什麼
                                    st.error(f"❌ 舊密碼錯誤。")
                                    st.caption(f"系統讀取: [{current_pwd_db}] vs 您輸入: [{input_old}]")
                                    st.caption("若兩者看起來一樣但失敗，請確認 Google Sheet 欄位格式是否為「純文字」。")

                        except Exception as e: st.error(f"錯誤: {e}")
        st.markdown("---")
        if st.button("🚪 登出"):
            log_event(ws_logs, st.session_state['user_name'], "Logout", "登出系統")
            st.session_state['logged_in'] = False
            st.rerun()

    # --- D. 戰情儀表板 ---
    st.markdown("<div class='brand-title' style='font-size:1.8rem;text-align:left;margin-bottom:10px;'>DASHBOARD</div>", unsafe_allow_html=True)
    total_qty = df['Qty'].sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    total_rev = (df['Qty'] * df['Price']).sum()
    total_profit = total_rev - total_cost

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>📦 總庫存</div><div class='metric-value'>{total_qty:,}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card' style='border-left-color:#d32f2f;'><div class='metric-label'>💰 總成本</div><div class='metric-value'>${total_cost:,}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card' style='border-left-color:#f1c40f;'><div class='metric-label'>💎 預估營收</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card' style='border-left-color:#28a745;'><div class='metric-label'>📈 潛在毛利</div><div class='metric-value'>${total_profit:,}</div></div>", unsafe_allow_html=True)

    if not df.empty:
        cc1, cc2 = st.columns([2, 1])
        with cc1:
            fashion_greys = ['#1a1a1a', '#4d4d4d', '#808080', '#b3b3b3', '#e6e6e6', '#000000']
            fig = px.pie(df, names='Category', values='Qty', hole=0.4, color_discrete_sequence=fashion_greys)
            fig.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        with cc2:
            st.caption("🚨 缺貨清單")
            low = df[df['Qty'] < 5][['SKU', 'Name', 'Qty']]
            st.dataframe(low, hide_index=True, use_container_width=True)
    st.markdown("---")

    # --- E. 功能分頁 ---
    tabs = st.tabs(["🧥 樣品展示", "⚡ POS", "➕ 商品管理", "📝 全知後台"])

    # Tab 1
    with tabs[0]:
        q = st.text_input("🔍 搜尋", placeholder="SKU / Name...")
        v_df = df.copy()
        if q: v_df = v_df[v_df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
        if not v_df.empty:
            rows = [v_df.iloc[i:i+4] for i in range(0, len(v_df), 4)]
            for row in rows:
                cols = st.columns(4)
                for idx, (col, item) in enumerate(zip(cols, row.iterrows())):
                    val = item[1]
                    with col:
                        img = render_image_url(val['Image_URL'])
                        st.markdown(f"""
                        <div class='product-card'>
                            <img src='{img}'>
                            <div style='font-weight:bold;margin-top:5px;height:2.4em;overflow:hidden;color:#000;'>{val['Name']}</div>
                            <small style='color:#888'>{val['SKU']}</small>
                            <div style='display:flex;justify-content:space-between;margin-top:5px;'>
                                <b style='color:#000'>${val['Price']}</b> <span style='background:#f0f0f0;padding:2px 6px;border-radius:4px;color:#000'>Q:{val['Qty']}</span>
                            </div>
                        </div>""", unsafe_allow_html=True)

    # Tab 2
    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist()
            sel = st.selectbox("選擇商品 (支援掃碼)", ["..."] + opts)
            target = None
            if sel != "...":
                target = df[df['SKU'] == sel.split(" | ")[0]].iloc[0]
                img = render_image_url(target['Image_URL'])
                st.image(img, width=150)
                st.markdown(f"**{target['Name']}**")
                st.markdown(f"庫存: `{target['Qty']}` | 售價: `${target['Price']}`")
        with c2:
            if target is not None:
                qty = st.number_input("數量", 1)
                note = st.text_input("備註")
                b1, b2 = st.columns(2)
                if b1.button("📥 進貨", type="secondary"):
                    r = ws_items.find(target['SKU']).row
                    new_val = int(target['Qty']) + qty
                    ws_items.update_cell(r, 5, new_val)
                    ws_items.update_cell(r, 8, str(datetime.now()))
                    log_event(ws_logs, st.session_state['user_name'], "Restock", f"{target['SKU']} +{qty} | {note}")
                    st.success("成功")
                    time.sleep(1.5)
                    st.rerun()
                if b2.button("📤 銷售", type="primary"):
                    if int(target['Qty']) < qty: st.error("庫存不足")
                    else:
                        r = ws_items.find(target['SKU']).row
                        new_val = int(target['Qty']) - qty
                        ws_items.update_cell(r, 5, new_val)
                        ws_items.update_cell(r, 8, str(datetime.now()))
                        log_event(ws_logs, st.session_state['user_name'], "Sale", f"{target['SKU']} -{qty} | {note}")
                        if new_val < 5: send_line_push(f"⚠️ 缺貨警報: {target['Name']} 剩 {new_val} 件")
                        st.success("成功")
                        time.sleep(1.5)
                        st.rerun()

    # Tab 3
    with tabs[2]:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("新增商品")
            with st.form("new"):
                sku = st.text_input("SKU")
                name = st.text_input("名稱")
                cat = st.selectbox("分類", ["上衣", "褲子", "外套", "配件", "其他"])
                size = st.selectbox("尺寸", ["F","S","M","L","XL"])
                col_sub1, col_sub2 = st.columns(2)
                q = col_sub1.number_input("數量", 0)
                cost = col_sub2.number_input("成本", 0)
                price = st.number_input("售價", 0)
                img = st.file_uploader("圖片", type=['jpg','png'])
                if st.form_submit_button("建立"):
                    if sku and name:
                        if sku in df['SKU'].tolist(): st.error("SKU 已存在")
                        else:
                            u = upload_image_to_imgbb(img) if img else ""
                            ws_items.append_row([sku, name, cat, size, q, price, cost, str(datetime.now()), u])
                            log_event(ws_logs, st.session_state['user_name'], "New_Item", f"新增: {sku}")
                            st.success("成功")
                            time.sleep(1.5)
                            st.rerun()
        with c2:
            st.subheader("工具箱")
            with st.expander("批量匯入"):
                up = st.file_uploader("CSV/Excel", type=['csv','xlsx'])
                if up and st.button("匯入"):
                    try:
                        d = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
                        cnt = 0
                        for _, r in d.iterrows():
                            s = str(r['SKU']).strip()
                            if s not in df['SKU'].tolist():
                                ws_items.append_row([s, r['Name'], r['Category'], r['Size'], r['Qty'], r['Price'], r['Cost'], str(datetime.now()), ""])
                                cnt+=1
                                time.sleep(0.5)
                        log_event(ws_logs, st.session_state['user_name'], "Import", f"匯入 {cnt} 筆")
                        st.success(f"匯入 {cnt} 筆")
                        time.sleep(1)
                        st.rerun()
                    except: st.error("格式錯誤")
            with st.expander("QR Code"):
                t = st.selectbox("商品", df['SKU'].tolist())
                if t: st.image(generate_qr(t), width=100)
            d_s = st.selectbox("刪除商品", ["..."]+df['SKU'].tolist())
            if d_s != "..." and st.button("確認刪除"):
                ws_items.delete_rows(ws_items.find(d_s).row)
                log_event(ws_logs, st.session_state['user_name'], "Del_Item", f"刪除: {d_s}")
                st.success("已刪除")
                time.sleep(1.5)
                st.rerun()

    # Tab 4: 全知後台
    with tabs[3]:
        st.subheader("🕵️ 歷史操作回朔 (Audit Log)")
        f_col1, f_col2 = st.columns(2)
        with f_col1: search_date = st.date_input("📅 選擇日期", value=None)
        with f_col2:
            action_map = {
                "全部": "All", "登入": "Login", "登出": "Logout", "銷售": "Sale", 
                "進貨": "Restock", "新增商品": "New_Item", "刪除商品": "Del_Item", 
                "人員異動": "HR_Update", "批量匯入": "Import", "安全操作": "Security"
            }
            selected_action_zh = st.selectbox("🔍 動作篩選", list(action_map.keys()))
            search_action_en = action_map[selected_action_zh]

        logs_df = get_data_safe(ws_logs)
        if not logs_df.empty:
            logs_df['DateObj'] = pd.to_datetime(logs_df['Timestamp'], errors='coerce').dt.date
            display_logs = logs_df.copy()
            if search_date: display_logs = display_logs[display_logs['DateObj'] == search_date]
            if search_action_en != "All": display_logs = display_logs[display_logs['Action'] == search_action_en]
            st.dataframe(display_logs.drop(columns=['DateObj']).sort_index(ascending=False), use_container_width=True, height=400)
        else: st.info("尚無紀錄")

        if st.session_state['user_role'] == 'Admin':
            st.markdown("---")
            st.subheader("👥 人員管理中心")
            st.caption("🟢 Active = 帳號啟用中 (可登入) | 🔴 Inactive = 帳號停用 (無法登入)")
            
            users_df = get_data_safe(ws_users)
            if not users_df.empty:
                users_df['Name'] = users_df['Name'].astype(str)
                u_rows = [users_df.iloc[i:i+3] for i in range(0, len(users_df), 3)]
                for row in u_rows:
                    cols = st.columns(3)
                    for idx, (col, user) in enumerate(zip(cols, row.iterrows())):
                        u_data = user[1]
                        status_class = "status-active" if u_data['Status'] == 'Active' else "status-inactive"
                        status_icon = "🟢" if u_data['Status'] == 'Active' else "🔴"
                        with col:
                            st.markdown(f"""
                            <div class="user-card">
                                <div class="user-info">
                                    <div class="user-name">{u_data['Name']}</div>
                                    <div class="user-role">{u_data['Role']}</div>
                                </div>
                                <div class="{status_class}">{status_icon} {u_data['Status']}</div>
                            </div>
                            """, unsafe_allow_html=True)

            st.divider()
            manage_tabs = st.tabs(["➕ 新增/修改員工", "🗑️ 刪除員工", "📡 系統測試"])
            with manage_tabs[0]:
                c_edit1, c_edit2 = st.columns([1, 2])
                with c_edit1: st.info("💡 輸入現有帳號即為修改，輸入新帳號即為新增。")
                with c_edit2:
                    n = st.text_input("帳號", key="hr_name")
                    p = st.text_input("密碼", key="hr_pass")
                    r = st.selectbox("權限", ["Staff", "Admin"], key="hr_role")
                    s = st.selectbox("狀態", ["Active", "Inactive"], key="hr_status")
                    if st.button("💾 儲存設定", type="primary"):
                        if n and p:
                            try:
                                cell = ws_users.find(n, in_column=1)
                                r_idx = cell.row
                                ws_users.update_cell(r_idx, 2, str(p).strip())
                                ws_users.update_cell(r_idx, 3, r)
                                ws_users.update_cell(r_idx, 4, s)
                                log_event(ws_logs, st.session_state['user_name'], "HR_Update", f"修改: {n}")
                                st.toast(f"✅ 已更新: {n}")
                            except:
                                ws_users.append_row([n, str(p).strip(), r, s, str(datetime.now())])
                                log_event(ws_logs, st.session_state['user_name'], "HR_Update", f"新增: {n}")
                                st.toast(f"✅ 已新增: {n}")
                            time.sleep(2)
                            st.rerun()
                        else: st.error("帳號密碼不可為空")

            with manage_tabs[1]:
                del_n = st.selectbox("選擇要刪除的員工", ["..."] + users_df['Name'].tolist())
                if del_n != "..." and st.button("❌ 確認刪除"):
                    if del_n == "Boss" or del_n == st.session_state['user_name']: st.error("無法刪除老闆或自己")
                    else:
                        ws_users.delete_rows(ws_users.find(del_n).row)
                        log_event(ws_logs, st.session_state['user_name'], "HR_Update", f"刪除: {del_n}")
                        st.success("已刪除")
                        time.sleep(2)
                        st.rerun()

            with manage_tabs[2]:
                if st.button("發送 LINE 測試"):
                    res = send_line_push("✅ V18.0 系統運作正常")
                    if res == "SUCCESS": st.success("發送成功")
                    else: st.error(res)

            st.markdown("---")
            with st.expander("🔴 危險區域"):
                st.warning("⚠️ 警告：此操作將永久刪除所有歷史操作紀錄。")
                if st.button("☢️ 確認清空所有紀錄"):
                    ws_logs.clear()
                    ws_logs.append_row(["Timestamp", "User", "Action", "Details"])
                    log_event(ws_logs, st.session_state['user_name'], "Security", "執行紀錄清空")
                    st.success("紀錄已清空")
                    time.sleep(2)
                    st.rerun()

if __name__ == "__main__":
    main()
