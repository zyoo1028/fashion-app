import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import requests
import plotly.express as px
import base64
import hashlib
import math
import re

# --- 1. 系統全域設定 (V103.0) ---
st.set_page_config(
    page_title="IFUKUK 企業資源中樞", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【V103.0 原始視覺核心】
# ==========================================
st.markdown("""
    <style>
        /* --- 1. 全局鎖定 --- */
        .stApp { background-color: #FFFFFF !important; }
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; border-right: 1px solid #E5E7EB; }
        h1, h2, h3, h4, h5, h6, p, span, div, label, li, .stMarkdown { color: #000000 !important; }
        
        /* --- 2. 輸入與選單 --- */
        input, textarea, .stTextInput > div > div, .stNumberInput > div > div {
            color: #000000 !important; background-color: #F3F4F6 !important; border-color: #D1D5DB !important;
            border-radius: 8px !important;
        }
        div[data-baseweb="select"] > div { background-color: #F3F4F6 !important; color: #000000 !important; border-color: #D1D5DB !important; border-radius: 8px !important; }
        
        /* --- 3. 戰情儀表板 --- */
        .metric-card { 
            background: linear-gradient(145deg, #ffffff, #f5f7fa); 
            border-radius: 16px; 
            padding: 15px; 
            border: 1px solid #e1e4e8; 
            text-align: center; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.02); 
            margin-bottom: 10px; 
            height: 100%;
        }
        .metric-value { font-size: 1.8rem; font-weight: 800; margin: 5px 0; color:#111 !important; }
        .metric-label { font-size: 0.8rem; letter-spacing: 1px; color:#666 !important; font-weight: 600; text-transform: uppercase;}
        .realized-card { border-bottom: 4px solid #10b981; }
        .profit-card { border-bottom: 4px solid #f59e0b; }

        /* --- 4. 庫存卡片 --- */
        .inv-card-container {
            border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; margin-bottom: 12px;
            background-color: #ffffff; transition: all 0.2s;
        }
        .inv-card-container:hover { border-color: #94a3b8; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .stock-pill-tw { background-color: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; margin-right: 5px; }
        .stock-pill-cn { background-color: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }

        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border:none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); background-color: #FFFFFF; color: #000000; border: 1px solid #E5E7EB; }
        [data-testid="stDataFrame"] { border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden; }
        
        /* --- 5. 功能區塊 --- */
        .cart-box { background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px; margin-bottom: 15px; }
        .cart-item { display: flex; justify-content: space-between; border-bottom: 1px dashed #cbd5e1; padding: 8px 0; font-size: 0.9rem; }
        .cart-total { font-size: 1.2rem; font-weight: 800; color: #0f172a; text-align: right; margin-top: 10px; }
        .final-price-display { font-size: 1.8rem; font-weight: 900; color: #16a34a; text-align: center; background: #dcfce7; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #86efac; }
        
        .audit-dashboard { background: linear-gradient(to right, #fff7ed, #fff); border: 1px solid #ffedd5; border-radius: 12px; padding: 15px; margin-bottom: 15px; }
        .audit-stat { font-size: 20px; font-weight: 800; color: #c2410c; }
        .audit-title { font-size: 11px; color: #9a3412; font-weight: 600; text-transform: uppercase; }

        .sku-wizard { background: linear-gradient(135deg, #f0f9ff 0%, #ffffff 100%); border: 1px solid #bae6fd; padding: 20px; border-radius: 16px; margin-bottom: 20px; }
        .transfer-zone { background: linear-gradient(135deg, #fff7ed 0%, #ffffff 100%); border: 1px solid #fdba74; padding: 20px; border-radius: 16px; margin-bottom: 20px; }
        .transfer-header { color: #c2410c !important; font-weight: 800; font-size: 1.1em; margin-bottom: 15px; display:flex; align-items:center; gap:8px;}
        .batch-grid { background-color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px dashed #cbd5e1; margin-top: 10px;}
        .batch-title { font-size: 0.9rem; font-weight: 700; color: #475569; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

# 🛑 [修復] 強力讀取器：解決 KeyError 與 系統無資料
# 如果讀取失敗或讀到空值，強制回傳一個帶有正確標頭的空 DataFrame，防止系統崩潰
def get_data_safe(ws, expected_headers=None):
    max_retries = 3
    for i in range(max_retries):
        try:
            if ws is None: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            raw_data = ws.get_all_values()
            
            # 如果讀不到資料，但我們知道應該要有什麼標頭，就回傳空表
            if not raw_data or len(raw_data) < 2: 
                return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            
            headers = raw_data[0]
            # V103: Deduplicate Headers
            seen = {}
            new_headers = []
            for h in headers:
                if h in seen:
                    seen[h] += 1
                    new_headers.append(f"{h}_{seen[h]}")
                else:
                    seen[h] = 0
                    new_headers.append(h)
            
            rows = raw_data[1:]
            
            # V103: Auto-Fix Headers
            if "Qty_CN" not in new_headers and expected_headers and "Qty_CN" in expected_headers:
                try:
                    ws.update_cell(1, len(new_headers)+1, "Qty_CN")
                    new_headers.append("Qty_CN")
                    raw_data = ws.get_all_values()
                    rows = raw_data[1:]
                except: pass

            df = pd.DataFrame(rows)
            if not df.empty:
                if len(df.columns) < len(new_headers):
                    for _ in range(len(new_headers) - len(df.columns)):
                        df[len(df.columns)] = ""
                df.columns = new_headers[:len(df.columns)]
                
            return df
        except Exception:
            time.sleep(1) # 等待 1 秒重試
            continue
            
    # 如果重試 3 次都失敗，回傳安全的空表，避免 KeyError
    return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()

# [強力寫入] 解決 Quota Exceeded
def update_cell_retry(ws, row, col, value, retries=3):
    for i in range(retries):
        try: ws.update_cell(row, col, value); return True
        except: time.sleep(1 + i); continue
    return False

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

# --- 工具模組 (V103 Original) ---

def get_taiwan_time_str():
    utc_now = datetime.utcnow()
    tw_time = utc_now + timedelta(hours=8)
    return tw_time.strftime("%Y-%m-%d %H:%M:%S")

@st.cache_data(ttl=3600)
def get_live_rate():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/CNY"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()['rates']['TWD'], True
    except: pass
    return 4.50, False

def make_hash(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def check_hash(password, hashed_text):
    return make_hash(password) == hashed_text

def render_image_url(url_input):
    if url_input is None: return "https://i.ibb.co/W31w56W/placeholder.png"
    if isinstance(url_input, float) and math.isnan(url_input): return "https://i.ibb.co/W31w56W/placeholder.png"
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

def log_event(ws_logs, user, action, detail):
    try: ws_logs.append_row([get_taiwan_time_str(), user, action, detail])
    except: pass

def render_navbar(user_initial):
    current_date = datetime.utcnow() + timedelta(hours=8)
    date_str = current_date.strftime("%Y/%m/%d")
    rate = st.session_state.get('exchange_rate', 4.5)
    st.markdown(f"""
        <div class="navbar-container">
            <div style="display:flex; flex-direction:column;">
                <span style="font-size:18px; font-weight:900; color:#111;">IFUKUK GLOBAL</span>
                <span style="font-size:11px; color:#666; font-family:monospace;">{date_str} • Live: {rate}</span>
            </div>
            <div style="width:36px; height:36px; background:#111; color:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold;">
                {user_initial}
            </div>
        </div>
    """, unsafe_allow_html=True)

# ----------------------------------------------------
# V103.0 核心邏輯
# ----------------------------------------------------
def get_style_code(sku):
    sku_str = str(sku).strip()
    if '-' in sku_str: return sku_str.rsplit('-', 1)[0]
    return sku_str

SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
def get_size_sort_key(size_str):
    if size_str in SIZE_ORDER: return SIZE_ORDER.index(size_str)
    return 99 

def generate_smart_style_code(category, existing_skus):
    prefix_map = {
        "上衣(Top)": "TOP", "褲子(Btm)": "BTM", "外套(Out)": "OUT", "套裝(Suit)": "SET",
        "鞋類(Shoe)": "SHOE", "包款(Bag)": "BAG", "帽子(Hat)": "HAT", "飾品(Acc)": "ACC", "其他(Misc)": "MSC"
    }
    prefix = prefix_map.get(category, "GEN")
    date_code = (datetime.utcnow() + timedelta(hours=8)).strftime("%y%m")
    prefix = f"{prefix}-{date_code}"
    
    current_prefix = f"{prefix}-"
    max_seq = 0
    for sku in existing_skus:
        if str(sku).startswith(current_prefix):
            try:
                rest = sku.replace(current_prefix, "")
                seq_part = rest.split("-")[0] 
                if seq_part.isdigit():
                    seq_num = int(seq_part)
                    if seq_num > max_seq: max_seq = seq_num
            except: pass
    next_seq = str(max_seq + 1).zfill(3)
    return f"{current_prefix}{next_seq}"

COLUMN_MAPPING = {
    "Style_Code": "款號(Style)", "Name": "商品名稱", "Category": "分類", "Size_Detail": "庫存分佈 (TW | CN)",
    "Total_Qty": "總庫存 (TW+CN)", "Price": "售價(NTD)", "Avg_Cost": "平均成本(NTD)", "Ref_Orig_Cost": "參考原幣(CNY)", "Last_Updated": "最後更新"
}

# 🛑 [修復] KeyError 防止機制：先檢查欄位是否存在
def calculate_realized_revenue(logs_df):
    total_revenue = 0
    if logs_df.empty or 'Action' not in logs_df.columns: return 0 # 安全返回
    
    sales_logs = logs_df[logs_df['Action'] == 'Sale']
    for _, row in sales_logs.iterrows():
        try:
            details = row['Details']
            match = re.search(r'Total:\$(\d+)', details)
            if match: total_revenue += int(match.group(1))
        except: pass
    return total_revenue

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
        
    if 'pos_cart' not in st.session_state:
        st.session_state['pos_cart'] = []

    sh = init_db()
    if not sh: st.error("Database Connection Failed"); st.stop()

    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    if not ws_items or not ws_logs or not ws_users: st.warning("Initializing..."); st.stop()

    # --- 登入頁面 ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-weight:900; font-size:2.5rem; margin-bottom:10px;'>IFUKUK</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>MATRIX ERP V103.0 (Fixed)</div>", unsafe_allow_html=True)
            with st.form("login"):
                user_input = st.text_input("帳號 (ID)")
                pass_input = st.text_input("密碼 (Password)", type="password")
                if st.form_submit_button("登入 (LOGIN)", type="primary"):
                    # 傳入預期標頭，防止讀到空表時報錯
                    users_df = get_data_safe(ws_users, ["Name", "Password", "Role", "Status", "Created_At"])
                    input_u = str(user_input).strip()
                    input_p = str(pass_input).strip()
                    
                    if users_df.empty and input_u == "Boss" and input_p == "1234":
                        hashed_pw = make_hash("1234")
                        ws_users.append_row(["Boss", hashed_pw, "Admin", "Active", get_taiwan_time_str()])
                        st.success("Boss Created"); time.sleep(1); st.rerun()

                    if not users_df.empty and 'Name' in users_df.columns:
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
                    else: st.error("系統連線忙碌，請等待 30 秒後再試 (Quota Exceeded Protect)")
        return

    # --- 主畫面 ---
    user_initial = st.session_state['user_name'][0].upper()
    render_navbar(user_initial)

    df = get_data_safe(ws_items, SHEET_HEADERS)
    logs_df = get_data_safe(ws_logs, ["Timestamp", "User", "Action", "Details"]) 
    users_df = get_data_safe(ws_users, ["Name", "Password", "Role", "Status", "Created_At"])
    staff_list = users_df['Name'].tolist() if not users_df.empty and 'Name' in users_df.columns else []

    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    
    for num in ['Qty', 'Price', 'Cost', 'Safety_Stock', 'Orig_Cost', 'Qty_CN']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    
    df['Safe_Level'] = df['Safety_Stock'].apply(lambda x: 5 if x == 0 else x)
    df['SKU'] = df['SKU'].astype(str)
    df['Style_Code'] = df['SKU'].apply(get_style_code)
    
    CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]
    SIZE_LIST = SIZE_ORDER

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
        if st.button("🚪 安全登出"):
            log_event(ws_logs, st.session_state['user_name'], "Logout", "登出")
            st.session_state['logged_in'] = False
            st.rerun()

    # --- Dashboard (V101) ---
    total_qty_tw = df['Qty'].sum()
    total_qty_cn = df['Qty_CN'].sum()
    total_qty = total_qty_tw + total_qty_cn
    
    total_cost = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum()
    total_rev = (df['Qty'] * df['Price']).sum()
    profit = total_rev - (df['Qty'] * df['Cost']).sum()
    
    realized_revenue = calculate_realized_revenue(logs_df)

    rmb_stock_value = 0
    if not df.empty and 'Orig_Currency' in df.columns:
        rmb_items = df[df['Orig_Currency'] == 'CNY']
        if not rmb_items.empty: rmb_stock_value = ((rmb_items['Qty'] + rmb_items['Qty_CN']) * rmb_items['Orig_Cost']).sum()

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.markdown(f"<div class='metric-card'><div class='metric-label'>📦 總庫存 (TW+CN)</div><div class='metric-value'>{total_qty:,}</div><div style='font-size:10px; color:#666;'>🇹🇼:{total_qty_tw} | 🇨🇳:{total_qty_cn}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='metric-card'><div class='metric-label'>💎 預估營收 (TW)</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='metric-card'><div class='metric-label'>💰 總資產成本</div><div class='metric-value'>${total_cost:,}</div><div style='font-size:11px;color:#888;'>含RMB原幣: ¥{rmb_stock_value:,}</div></div>", unsafe_allow_html=True)
    with m4: st.markdown(f"<div class='metric-card profit-card'><div class='metric-label'>📈 潛在毛利</div><div class='metric-value' style='color:#f59e0b !important'>${profit:,}</div></div>", unsafe_allow_html=True)
    with m5: st.markdown(f"<div class='metric-card realized-card'><div class='metric-label'>💵 實際營收 (已售)</div><div class='metric-value' style='color:#10b981 !important'>${realized_revenue:,}</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- Tabs ---
    tabs = st.tabs(["📊 視覺庫存", "🛒 POS (購物車)", "📈 銷售戰情", "🎁 內部領用/稽核", "👔 矩陣管理", "📝 日誌", "👥 Admin"])

    # Tab 1: 視覺總覽 (V101)
    with tabs[0]:
        if not df.empty:
            c_chart1, c_chart2 = st.columns([1, 1])
            with c_chart1:
                st.caption("📈 庫存分類佔比 (TW)")
                fig_pie = px.pie(df, names='Category', values='Qty', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
            with c_chart2:
                st.caption("📊 重點庫存 (Top 10 TW)")
                top_items = df.groupby(['Style_Code', 'Name']).agg({'Qty':'sum'}).reset_index().sort_values(by='Qty', ascending=False).head(10)
                fig_bar = px.bar(top_items, x='Qty', y='Name', orientation='h', text='Qty', color='Qty', color_continuous_scale='Bluered')
                fig_bar.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0), yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)
        
        st.divider()
        st.subheader("📦 庫存區 (Inventory Zone)")
        
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1: search_q = st.text_input("🔍 搜尋商品", placeholder="輸入貨號或品名...")
        with col_s2: filter_cat = st.selectbox("📂 分類篩選", ["全部"] + CAT_LIST)
        
        gallery_df = df.copy()
        if search_q: gallery_df = gallery_df[gallery_df.apply(lambda x: search_q.lower() in str(x.values).lower(), axis=1)]
        if filter_cat != "全部": gallery_df = gallery_df[gallery_df['Category'] == filter_cat]
        
        if not gallery_df.empty:
            grouped = gallery_df.groupby(['Style_Code', 'Name'])
            
            for (style_code, name), group in grouped:
                first_row = group.iloc[0] 
                img = render_image_url(first_row['Image_URL'])
                price = int(first_row['Price'])
                total_qty_tw = group['Qty'].sum()
                total_qty_cn = group['Qty_CN'].sum()
                
                group['size_sort'] = group['Size'].apply(get_size_sort_key)
                sorted_group = group.sort_values('size_sort')

                with st.container(border=True):
                    c_card_img, c_card_info = st.columns([1, 4]) 
                    with c_card_img:
                        st.image(img, use_column_width=True)
                    with c_card_info:
                        st.markdown(f"#### {name}")
                        st.caption(f"貨號: {style_code}")
                        st.markdown(f"🇹🇼 台灣: **{total_qty_tw}** | 🇨🇳 中國: **{total_qty_cn}** | 售價: ${price}")
                        preview_tags = ""
                        for _, row in sorted_group.iterrows():
                            if row['Qty'] > 0: preview_tags += f"<span class='stock-pill-tw'>{row['Size']}:{row['Qty']}</span> "
                            if row['Qty_CN'] > 0: preview_tags += f"<span class='stock-pill-cn'>{row['Size']}(CN):{row['Qty_CN']}</span> "
                        if preview_tags: st.markdown(preview_tags, unsafe_allow_html=True)

                    with st.expander("📝 管理庫存 / 詳細設定"):
                        with st.form(f"dyn_form_{style_code}_{name}"):
                            inputs_tw = {}
                            inputs_cn = {}
                            grid_cols = st.columns(4)
                            for idx, row in enumerate(sorted_group.iterrows()):
                                _, r_data = row
                                with grid_cols[idx % 4]: 
                                    count_of_this_size = sorted_group[sorted_group['Size'] == r_data['Size']].shape[0]
                                    label = f"{r_data['Size']}"
                                    if count_of_this_size > 1:
                                        suffix = r_data['SKU']
                                        st.markdown(f"<span class='sku-hint'>{suffix}</span>", unsafe_allow_html=True)
                                    inputs_tw[r_data['SKU']] = st.number_input(f"🇹🇼 {label} (TW)", value=int(r_data['Qty']), key=f"dtw_{r_data['SKU']}")
                                    inputs_cn[r_data['SKU']] = st.number_input(f"🇨🇳 {label} (CN)", value=int(r_data['Qty_CN']), key=f"dcn_{r_data['SKU']}")
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.form_submit_button("💾 更新庫存 (Update TW & CN)", use_container_width=True):
                                changes = []
                                for t_sku, new_q_tw in inputs_tw.items():
                                    if t_sku in df['SKU'].tolist():
                                        new_q_cn = inputs_cn[t_sku]
                                        r = ws_items.find(t_sku).row
                                        update_cell_retry(ws_items, r, 5, new_q_tw)
                                        update_cell_retry(ws_items, r, 13, new_q_cn)
                                        update_cell_retry(ws_items, r, 8, get_taiwan_time_str())
                                        changes.append(f"{t_sku.split('-')[-1]}: TW{new_q_tw}/CN{new_q_cn}")
                                log_event(ws_logs, st.session_state['user_name'], "Quick_Update", f"{style_code} | {', '.join(changes)}")
                                st.success("更新完成！"); time.sleep(1); st.rerun()
        else: st.info("無符合資料")

        st.markdown("##### 📦 庫存明細 (歸戶檢視)")
        if not gallery_df.empty:
            agg_df = gallery_df.groupby(['Style_Code', 'Name']).agg({
                'Category': 'first', 'Qty': 'sum',
