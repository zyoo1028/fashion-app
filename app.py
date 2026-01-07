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
    page_title="IFUKUK 戰情中樞", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded" # 核心修復：強制展開側邊欄，避免手機找不到按鈕
)

# ==========================================
# 🛑 【MATRIX-V27 終極視覺引擎】
# 包含：強制白底(防隱形)、手機版面優化、Sticky Navbar
# ==========================================
st.markdown("""
    <style>
        /* --- Part A: 強制白底黑字 (解決手機深色模式看不見問題) --- */
        .stApp { background-color: #FFFFFF !important; }
        p, div, h1, h2, h3, h4, span, label, li { color: #000000 !important; }
        button[data-baseweb="tab"] div p { color: #555555 !important; font-weight: 600 !important; }
        button[data-baseweb="tab"][aria-selected="true"] div p { color: #FF4B4B !important; }
        input.st-ai, textarea, select { 
            color: #000000 !important; 
            background-color: #F3F4F6 !important;
            border-radius: 8px !important;
        }
        
        /* 強制顯示 Header (讓漢堡選單回來) */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            display: block !important;
            z-index: 9999 !important;
        }

        /* --- Part B: Mobile UI 優化 --- */
        .block-container {
            padding-top: 6rem !important; /* 避開 Navbar */
            padding-bottom: 5rem !important;
        }

        /* 自定義導航欄 (Sticky) */
        .navbar-container {
            position: fixed;
            top: 50px; /* 讓出空間給 Streamlit 的漢堡選單 */
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

        /* 卡片樣式 */
        .metric-card {
            background: white;
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            border: 1px solid #f3f4f6;
            text-align: center;
            margin-bottom: 12px;
        }
        .metric-value { font-size: 1.8rem; font-weight: 800; margin: 4px 0; color:#111 !important; }
        .metric-label { font-size: 0.8rem; letter-spacing: 1px; color:#666 !important; }
        
        /* 產品列表卡片 */
        .product-card {
            background: white; border-radius: 12px; padding: 12px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #eee;
        }
        
        /* 人員管理卡片 */
        .user-card { 
            background: white; border-radius: 10px; padding: 15px; 
            border: 1px solid #e0e0e0; margin-bottom: 10px; 
            display: flex; align-items: center; justify-content: space-between; 
        }
        .user-name { font-weight: bold; font-size: 1.1rem; color: #333 !important; }
        .status-active { color: #28a745 !important; font-weight: bold; }
        .status-inactive { color: #dc3545 !important; font-weight: bold; }

        /* 按鈕優化 */
        .stButton>button { border-radius: 12px; height: 3.2em; font-weight: 700; }
        
        /* 隱藏預設圖表選單 */
        .modebar { display: none !important; }

    </style>
""", unsafe_allow_html=True)

# --- ⚠️⚠️⚠️ 設定區 ⚠️⚠️⚠️ ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
LINE_CHANNEL_ACCESS_TOKEN = "IaGvcTOmbMFW8wKEJ5MamxfRx7QVo0kX1IyCqwKZw0WX2nxAVYY7SsSh5vAJ0r+WBNvyjjiU8G3eYkL1nozqIOjjWMOKr/4ZtzUMRRf7JNJkk5V6jLpWc/EOkzvNGVPMh0zwH+wQD51tR3XWipUULwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U55199b00fb78da85bb285db6d00b6ff5"
# ---------------------------------------------------

# --- 2. 核心連線邏輯 ---
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

# --- 3. 工具模組 ---
def render_image_url(url_input):
    if not url_input: return "https://i.ibb.co/W31w56W/placeholder.png"
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
    if not LINE_CHANNEL_ACCESS_TOKEN: return "ERROR_TOKEN"
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
    try: ws_logs.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, detail])
    except: pass

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
            st.markdown("<div style='text-align:center; font-weight:900; font-size:2.5rem; margin-bottom:20px;'>IFUKUK</div>", unsafe_allow_html=True)
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

    # --- 登入後畫面 ---
    user_initial = st.session_state['user_name'][0].upper() if st.session_state['user_name'] else "U"
    render_navbar(user_initial)

    # 數據讀取與處理
    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    # --- B. 側邊欄 (功能恢復) ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_label = "🔴 Admin" if st.session_state['user_role'] == 'Admin' else "🟢 Staff"
        st.caption(f"Role: {role_label}")
        
        with st.expander("⚙️ 個人設定"):
            with st.form("pwd"):
                old = st.text_input("舊密碼", type="password")
                new = st.text_input("新密碼", type="password")
                confirm = st.text_input("確認新密碼", type="password")
                if st.form_submit_button("修改"):
                    if not old or not new: st.error("欄位不可為空")
                    elif new != confirm: st.error("新密碼不一致")
                    else:
                        try:
                            raw_data = ws_users.get_all_values()
                            user_row_idx = -1
                            current_pwd_db = ""
                            for i, row in enumerate(raw_data):
                                if str(row[0]).strip() == st.session_state['user_name']:
                                    user_row_idx = i + 1 
                                    current_pwd_db = str(row[1]).strip()
                                    break
                            if user_row_idx != -1 and str(old).strip() == current_pwd_db:
                                ws_users.update_cell(user_row_idx, 2, str(new).strip())
                                log_event(ws_logs, st.session_state['user_name'], "Security", "修改密碼成功")
                                st.success("✅ 密碼修改成功！")
                            else: st.error("舊密碼錯誤")
                        except Exception as e: st.error(f"錯誤: {e}")
        st.markdown("---")
        if st.button("🚪 登出"):
            log_event(ws_logs, st.session_state['user_name'], "Logout", "登出系統")
            st.session_state['logged_in'] = False
            st.rerun()

    # --- C. 戰情儀表板 ---
    total_qty = df['Qty'].sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    total_rev = (df['Qty'] * df['Price']).sum()
    total_profit = total_rev - total_cost

    m1, m2 = st.columns(2)
    with m1:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>📦 總庫存</div>
                <div class='metric-value'>{total_qty:,}</div>
            </div>
            <div class='metric-card'>
                 <div class='metric-label'>💰 總成本</div>
                 <div class='metric-value'>${total_cost:,}</div>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>💎 預估營收</div>
                <div class='metric-value'>${total_rev:,}</div>
            </div>
            <div class='metric-card'>
                 <div class='metric-label'>📈 潛在毛利</div>
                 <div class='metric-value'>${total_profit:,}</div>
            </div>
        """, unsafe_allow_html=True)

    if not df.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        cc1, cc2 = st.columns([2, 1])
        with cc1:
            fashion_greys = ['#1a1a1a', '#4d4d4d', '#808080', '#b3b3b3', '#e6e6e6', '#000000']
            fig = px.pie(df, names='Category', values='Qty', hole=0.7, color_discrete_sequence=fashion_greys)
            fig.update_layout(height=220, margin=dict(t=20, b=20, l=20, r=20), showlegend=False, 
                              annotations=[dict(text='庫存', x=0.5, y=0.5, font_size=12, showarrow=False)])
            st.plotly_chart(fig, use_container_width=True)
        with cc2:
            st.caption("🚨 缺貨清單")
            low = df[df['Qty'] < 5][['SKU', 'Name', 'Qty']]
            low.columns = ['貨號', '品名', '數量']
            st.dataframe(low, hide_index=True, use_container_width=True)
    
    st.markdown("---")

    # --- D. 功能分頁 ---
    tabs = st.tabs(["🧥 樣品展示", "⚡ POS", "➕ 商品管理", "📝 全知後台"])

    # Tab 1: 樣品
    with tabs[0]:
        q = st.text_input("🔍 搜尋", placeholder="貨號 / 品名...")
        v_df = df.copy()
        if q: v_df = v_df[v_df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
        if not v_df.empty:
            # 採用 V26 的 Mobile-Friendly 條列式卡片
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
                                <b style="color:#000; font-size:16px;">${row['Price']}</b> 
                                <span style="background:#f3f4f6; padding:2px 8px; border-radius:4px; color:#000; font-size:11px;">Q:{row['Qty']}</span>
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)
        else: st.info("無商品")

    # Tab 2: POS
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
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
                    ws_items.update_cell(r, 5, int(target['Qty']) + qty)
                    ws_items.update_cell(r, 8, str(datetime.now()))
                    log_event(ws_logs, st.session_state['user_name'], "Restock", f"{target['SKU']} +{qty} | {note}")
                    st.success("成功")
                    time.sleep(1)
                    st.rerun()
                if b2.button("📤 銷售", type="primary"):
                    if int(target['Qty']) < qty: st.error("庫存不足")
                    else:
                        r = ws_items.find(target['SKU']).row
                        ws_items.update_cell(r, 5, int(target['Qty']) - qty)
                        ws_items.update_cell(r, 8, str(datetime.now()))
                        log_event(ws_logs, st.session_state['user_name'], "Sale", f"{target['SKU']} -{qty} | {note}")
                        if (int(target['Qty']) - qty) < 5: send_line_push(f"⚠️ 缺貨: {target['Name']}")
                        st.success("成功")
                        time.sleep(1)
                        st.rerun()

    # Tab 3: 商品管理
    with tabs[2]:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("新增商品")
            with st.form("new"):
                sku = st.text_input("商品貨號 (SKU)")
                name = st.text_input("商品名稱")
                cat = st.selectbox("分類", ["上衣", "褲子", "外套", "配件", "其他"])
                size = st.selectbox("尺寸", ["F","S","M","L","XL"])
                col_sub1, col_sub2 = st.columns(2)
                q = col_sub1.number_input("數量", 0)
                cost = col_sub2.number_input("成本", 0)
                price = st.number_input("售價", 0)
                img = st.file_uploader("圖片", type=['jpg','png'])
                if st.form_submit_button("建立"):
                    if sku and name:
                        if sku in df['SKU'].tolist(): st.error("商品貨號已存在")
                        else:
                            u = upload_image_to_imgbb(img) if img else ""
                            ws_items.append_row([sku, name, cat, size, q, price, cost, str(datetime.now()), u])
                            log_event(ws_logs, st.session_state['user_name'], "New_Item", f"新增: {sku}")
                            st.success("成功")
                            time.sleep(1)
                            st.rerun()
                    else: st.error("貨號與名稱為必填")
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
                        log_event(ws_logs, st.session_state['user_name'], "Import", f"匯入 {cnt} 筆")
                        st.success(f"匯入 {cnt} 筆")
                        time.sleep(1)
                        st.rerun()
                    except: st.error("格式錯誤")
            with st.expander("QR Code"):
                t = st.selectbox("選擇商品產生 QR", df['SKU'].tolist())
                if t: st.image(generate_qr(t), width=100)
            
            d_s = st.selectbox("刪除商品", ["..."]+df['SKU'].tolist())
            if d_s != "..." and st.button("確認刪除"):
                ws_items.delete_rows(ws_items.find(d_s).row)
                log_event(ws_logs, st.session_state['user_name'], "Del_Item", f"刪除: {d_s}")
                st.success("已刪除")
                time.sleep(1)
                st.rerun()

    # Tab 4: 全知後台 (核心功能復原！)
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

        # 🛑 管理者專屬區域 (完全復原)
        if st.session_state['user_role'] == 'Admin':
            st.markdown("---")
            st.subheader("👥 人員管理中心")
            
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
            
            # Sub-Tab 1: 新增修改
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

            # Sub-Tab 2: 刪除
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

            # Sub-Tab 3: 測試
            with manage_tabs[2]:
                if st.button("發送 LINE 測試"):
                    res = send_line_push("✅ V27.0 系統運作正常")
                    if res == "SUCCESS": st.success("發送成功")
                    else: st.error(res)

            st.markdown("---")
            # Danger Zone 復原
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
