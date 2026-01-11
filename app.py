import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone
import time
import requests
import plotly.express as px
import base64
import hashlib
import math
import re

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK 企業資源中樞", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【MATRIX-V57.0 商業定價引擎與時空校正核心】
# ==========================================
st.markdown("""
    <style>
        /* --- 1. 全局鎖定 (強制白底黑字) --- */
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
        div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
            background-color: #FFFFFF !important; color: #000000 !important; border: 1px solid #E5E7EB !important;
        }
        li[role="option"] { background-color: #FFFFFF !important; color: #000000 !important; display: flex !important; }
        li[role="option"] div { color: #000000 !important; }
        li[role="option"]:hover, li[role="option"][aria-selected="true"] { background-color: #F3F4F6 !important; color: #000000 !important; }

        /* --- 3. 卡片樣式 --- */
        .metric-card { background: linear-gradient(145deg, #ffffff, #f5f7fa); border-radius: 16px; padding: 20px; border: 1px solid #e1e4e8; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 10px; }
        .metric-value { font-size: 2rem; font-weight: 800; margin: 8px 0; color:#111 !important; }
        .metric-label { font-size: 0.85rem; letter-spacing: 1px; color:#666 !important; font-weight: 600; }
        
        .inv-card {
            background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px;
            padding: 12px; margin-bottom: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .size-tag { 
            font-size: 11px; background: #fff; color: #333; 
            padding: 3px 6px; border-radius: 4px; border: 1px solid #ddd;
            margin-right: 4px; display: inline-block;
        }
        .size-tag.no-stock { background: #fee2e2; color: #991b1b; border-color: #fecaca; } 

        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border:none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); background-color: #FFFFFF; color: #000000; border: 1px solid #E5E7EB; }
        [data-testid="stDataFrame"] { border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden; }
        
        /* --- 4. 區塊樣式 --- */
        .sku-wizard { background: linear-gradient(135deg, #f0f9ff 0%, #ffffff 100%); border: 1px solid #bae6fd; padding: 20px; border-radius: 16px; margin-bottom: 20px; }
        .refactor-zone { background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%); border: 1px solid #fcd34d; padding: 20px; border-radius: 16px; margin-bottom: 20px; }
        .delete-zone { background: linear-gradient(135deg, #fef2f2 0%, #fff1f2 100%); border: 1px solid #fecaca; padding: 20px; border-radius: 16px; margin-bottom: 20px; }
        
        .audit-dashboard { background: linear-gradient(to right, #fff7ed, #fff); border: 1px solid #ffedd5; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .audit-stat { font-size: 24px; font-weight: 800; color: #c2410c; }
        .audit-title { font-size: 12px; color: #9a3412; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
        
        /* POS Pricing Engine */
        .pricing-box { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; margin-bottom: 10px; }
        .final-price-tag { font-size: 1.5rem; font-weight: 900; color: #16a34a; text-align: center; display: block; }
        
        .wizard-header { color: #0369a1 !important; font-weight: 800; font-size: 1.1em; margin-bottom: 15px; display:flex; align-items:center; gap:8px;}
        .refactor-header { color: #b45309 !important; font-weight: 800; font-size: 1.1em; margin-bottom: 15px; display:flex; align-items:center; gap:8px;}
        .delete-header { color: #991b1b !important; font-weight: 800; font-size: 1.1em; margin-bottom: 15px; display:flex; align-items:center; gap:8px;}
        
        .stNumberInput label { font-size: 0.85rem; font-weight: 700; color: #444; }
        .sku-hint { font-size: 0.7rem; color: #94a3b8; margin-top: -15px; margin-bottom: 10px; display: block; font-family: monospace; }
        .batch-grid { background-color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px dashed #cbd5e1; margin-top: 10px;}
        .batch-title { font-size: 0.9rem; font-weight: 700; color: #475569; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
LINE_CHANNEL_ACCESS_TOKEN = "IaGvcTOmbMFW8wKEJ5MamxfRx7QVo0kX1IyCqwKZw0WX2nxAVYY7SsSh5vAJ0r+WBNvyjjiU8G3eYkL1nozqIOjjWMOKr/4ZtzUMRRf7JNJkk5V6jLpWc/EOkzvNGVPMh0zwH+wQD51tR3XWipUULwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U55199b00fb78da85bb285db6d00b6ff5"

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

# --- 工具模組 (V57: Timezone Fix) ---

def get_taiwan_time_str():
    """
    獲取台灣時間 (UTC+8) 的字串格式。
    解決伺服器位於 UTC 導致的時間誤差。
    """
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

# V57: Log uses Taiwan Time
def log_event(ws_logs, user, action, detail):
    try: ws_logs.append_row([get_taiwan_time_str(), user, action, detail])
    except: pass

def render_navbar(user_initial):
    current_date = datetime.utcnow() + timedelta(hours=8) # Display Taiwan Date
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
# 🛑 V57.0 核心邏輯
# ----------------------------------------------------
def get_style_code(sku):
    sku_str = str(sku).strip()
    if '-' in sku_str:
        return sku_str.rsplit('-', 1)[0]
    return sku_str

SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
def get_size_sort_key(size_str):
    if size_str in SIZE_ORDER:
        return SIZE_ORDER.index(size_str)
    return 99 

def generate_smart_style_code(category, existing_skus):
    prefix_map = {
        "上衣(Top)": "TOP", "褲子(Btm)": "BTM", "外套(Out)": "OUT", "套裝(Suit)": "SET",
        "鞋類(Shoe)": "SHOE", "包款(Bag)": "BAG", "帽子(Hat)": "HAT", "飾品(Acc)": "ACC", "其他(Misc)": "MSC"
    }
    prefix = prefix_map.get(category, "GEN")
    date_code = (datetime.utcnow() + timedelta(hours=8)).strftime("%y%m") # Taiwan Time
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
    "Style_Code": "款號(Style)", "Name": "商品名稱", "Category": "分類", "Size_Detail": "庫存分佈",
    "Total_Qty": "總庫存", "Price": "售價(NTD)", "Avg_Cost": "平均成本(NTD)", "Ref_Orig_Cost": "參考原幣(CNY)", "Last_Updated": "最後更新"
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
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>MATRIX ERP V57.0</div>", unsafe_allow_html=True)
            with st.form("login"):
                user_input = st.text_input("帳號 (ID)")
                pass_input = st.text_input("密碼 (Password)", type="password")
                if st.form_submit_button("登入 (LOGIN)", type="primary"):
                    users_df = get_data_safe(ws_users)
                    input_u = str(user_input).strip()
                    input_p = str(pass_input).strip()
                    
                    if users_df.empty and input_u == "Boss" and input_p == "1234":
                        hashed_pw = make_hash("1234")
                        ws_users.append_row(["Boss", hashed_pw, "Admin", "Active", get_taiwan_time_str()])
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
    df['Style_Code'] = df['SKU'].apply(get_style_code)
    
    users_df = get_data_safe(ws_users)
    staff_list = users_df['Name'].tolist() if not users_df.empty else []

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
    tabs = st.tabs(["📊 視覺庫存", "⚡ POS (精準版)", "🎁 內部領用/稽核", "👔 矩陣管理", "📝 日誌", "👥 Admin"])

    # Tab 1: 視覺總覽 (V50)
    with tabs[0]:
        if not df.empty:
            c_chart1, c_chart2 = st.columns([1, 1])
            with c_chart1:
                st.caption("📈 庫存分類佔比")
                fig_pie = px.pie(df, names='Category', values='Qty', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
            with c_chart2:
                st.caption("📊 重點庫存 (Top 10)")
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
                total_qty = group['Qty'].sum()
                
                group['size_sort'] = group['Size'].apply(get_size_sort_key)
                sorted_group = group.sort_values('size_sort')

                with st.container(border=True):
                    c_card_img, c_card_info = st.columns([1, 3])
                    with c_card_img:
                        st.image(img, use_column_width=True)
                    with c_card_info:
                        st.markdown(f"#### {name}")
                        st.caption(f"貨號: {style_code}")
                        st.markdown(f"**庫存: {total_qty}** | 售價: ${price}")
                        preview_tags = ""
                        for _, row in sorted_group.iterrows():
                            if row['Qty'] > 0: preview_tags += f"`{row['Size']}:{row['Qty']}` "
                        if preview_tags: st.markdown(preview_tags)

                    with st.expander("📝 管理庫存 / 詳細設定"):
                        with st.form(f"dyn_form_{style_code}_{name}"):
                            inputs = {}
                            grid_cols = st.columns(4)
                            for idx, row in enumerate(sorted_group.iterrows()):
                                _, r_data = row
                                with grid_cols[idx % 4]: 
                                    count_of_this_size = sorted_group[sorted_group['Size'] == r_data['Size']].shape[0]
                                    label = f"{r_data['Size']}"
                                    if count_of_this_size > 1:
                                        suffix = r_data['SKU']
                                        st.markdown(f"<span class='sku-hint'>{suffix}</span>", unsafe_allow_html=True)
                                    inputs[r_data['SKU']] = st.number_input(label, value=int(r_data['Qty']), key=f"d_{r_data['SKU']}")
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.form_submit_button("💾 更新此款庫存", use_container_width=True):
                                changes = []
                                for t_sku, new_q in inputs.items():
                                    if t_sku in df['SKU'].tolist():
                                        r = ws_items.find(t_sku).row
                                        ws_items.update_cell(r, 5, new_q)
                                        ws_items.update_cell(r, 8, get_taiwan_time_str())
                                        changes.append(f"{t_sku.split('-')[-1]}:{new_q}")
                                log_event(ws_logs, st.session_state['user_name'], "Quick_Update", f"{style_code} | {', '.join(changes)}")
                                st.success("更新完成！"); time.sleep(1); st.rerun()
        else: st.info("無符合資料")

        st.markdown("##### 📦 庫存明細 (歸戶檢視)")
        if not gallery_df.empty:
            agg_df = gallery_df.groupby(['Style_Code', 'Name']).agg({
                'Category': 'first', 'Qty': 'sum', 'Price': 'max', 'Cost': 'mean', 'Orig_Cost': 'first',
                'Orig_Currency': 'first', 'Last_Updated': 'max'
            }).reset_index()
            def get_stock_dist(row):
                grp = gallery_df[(gallery_df['Style_Code'] == row['Style_Code']) & (gallery_df['Name'] == row['Name'])]
                grp['s_sort'] = grp['Size'].apply(get_size_sort_key)
                grp = grp.sort_values('s_sort')
                return " | ".join([f"{r['Size']}:{r['Qty']}" for _, r in grp.iterrows()])
            agg_df['Size_Detail'] = agg_df.apply(get_stock_dist, axis=1)
            agg_df['Total_Qty'] = agg_df['Qty']
            agg_df['Avg_Cost'] = agg_df['Cost'].astype(int)
            agg_df['Ref_Orig_Cost'] = agg_df.apply(lambda x: f"¥{x['Orig_Cost']}" if x['Orig_Currency'] == 'CNY' else "-", axis=1)
            agg_df = agg_df.rename(columns=COLUMN_MAPPING)
            show_cols = ["款號(Style)", "商品名稱", "分類", "庫存分佈", "總庫存", "售價(NTD)", "平均成本(NTD)", "參考原幣(CNY)", "最後更新"]
            st.dataframe(agg_df[show_cols], use_container_width=True)

    # Tab 2: POS (V57.0 商業定價引擎)
    with tabs[1]:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("1. 選擇商品 (精準 SKU)")
            if not df.empty:
                sku_opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} ({x['Size']}) | 現貨:{x['Qty']}", axis=1).tolist()
            else: sku_opts = []
            sel_sku = st.selectbox("搜尋商品", ["..."] + sku_opts, key="pos_sku_sel")
            target = None
            if sel_sku != "...":
                target_sku = sel_sku.split(" | ")[0]
                target = df[df['SKU'] == target_sku].iloc[0]
                img = render_image_url(target['Image_URL'])
                st.markdown(f"""
                <div style="border:1px solid #e5e7eb; border-radius:12px; padding:15px; display:flex; align-items:center; background:#f9fafb;">
                    <img src="{img}" style="width:100px; height:100px; object-fit:cover; border-radius:8px; margin-right:20px;">
                    <div>
                        <div style="font-weight:900; font-size:20px;">{target['Name']}</div>
                        <div style="color:#666; font-family:monospace; margin-bottom:5px;">{target['SKU']}</div>
                        <div style="font-size:14px;">尺寸: <b style="background:#e5e7eb; padding:2px 6px; border-radius:4px;">{target['Size']}</b></div>
                        <div style="margin-top:8px; font-weight:bold; color:#059669;">售價: NT${target['Price']}</div>
                        <div style="color:#d32f2f; font-weight:bold;">現貨: {target['Qty']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with c2:
            st.subheader("2. 交易結算")
            if target is not None:
                qty = st.number_input("數量", 1)
                t1, t2 = st.tabs(["📤 銷售 (Sell)", "📥 進貨 (Restock)"])
                
                # --- V57.0 商業定價引擎 (POS) ---
                with t1:
                    st.markdown("###### 💰 智慧改價中心 (Pricing Engine)")
                    
                    base_price = int(target['Price'])
                    discount_mode = st.radio("折扣模式", ["原價", "員工價 (7折)", "員工價 (8折)", "員工價 (9折)", "自訂折扣 (%)", "直接改價 (組合/贈品)"], horizontal=False)
                    
                    final_unit_price = base_price
                    discount_note = ""
                    
                    if "7折" in discount_mode:
                        final_unit_price = int(base_price * 0.7)
                        discount_note = "(7折)"
                    elif "8折" in discount_mode:
                        final_unit_price = int(base_price * 0.8)
                        discount_note = "(8折)"
                    elif "9折" in discount_mode:
                        final_unit_price = int(base_price * 0.9)
                        discount_note = "(9折)"
                    elif "自訂折扣" in discount_mode:
                        cust_off = st.number_input("輸入折數 (例如 85 代表 85折)", min_value=1, max_value=100, value=95)
                        final_unit_price = int(base_price * (cust_off / 100))
                        discount_note = f"({cust_off}折)"
                    elif "直接改價" in discount_mode:
                        final_unit_price = st.number_input("輸入最終單價 (NTD)", value=base_price)
                        discount_note = "(改價)"
                    
                    total_sale_amt = final_unit_price * qty
                    
                    # 顯示計算結果
                    st.markdown(f"""
                    <div class="pricing-box">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="color:#666;">原價單價: ${base_price}</span>
                            <span style="font-weight:bold;">折扣後單價: ${final_unit_price}</span>
                        </div>
                        <hr style="margin:8px 0;">
                        <span class="final-price-tag">總金額: ${total_sale_amt}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    note_out = st.text_input("銷售備註 (客戶/原因)")
                    
                    if st.button("確認銷售 (結帳)", type="primary", use_container_width=True):
                        if int(target['Qty']) >= qty:
                            r = ws_items.find(target['SKU']).row
                            ws_items.update_cell(r, 5, int(target['Qty']) - qty)
                            ws_items.update_cell(r, 8, get_taiwan_time_str()) # V57 Time
                            
                            # Log 包含詳細金額資訊
                            log_detail = f"{target['SKU']} -{qty} | 售:${final_unit_price} {discount_note} | 總:${total_sale_amt} | {note_out}"
                            log_event(ws_logs, st.session_state['user_name'], "Sale", log_detail)
                            st.success(f"✅ 銷售成功！實收 ${total_sale_amt}"); time.sleep(2); st.rerun()
                        else: st.error("庫存不足！")

                with t2:
                    st.markdown("###### 💰 進貨成本")
                    cost_currency = st.radio("幣別", ["NTD", "CNY"], horizontal=True)
                    input_unit_cost = st.number_input("單價", value=0.0)
                    final_cost_twd = int(input_unit_cost * st.session_state['exchange_rate']) if cost_currency == "CNY" else int(input_unit_cost)
                    if cost_currency == "CNY": st.info(f"換算: ¥{input_unit_cost} = NT${final_cost_twd}")
                    note_in = st.text_input("進貨備註")
                    
                    if st.button("確認進貨", type="secondary", use_container_width=True):
                        cur_qty = int(target['Qty']); cur_cost = int(target['Cost'])
                        tot_qty = cur_qty + qty
                        new_avg = int(((cur_qty * cur_cost) + (qty * (final_cost_twd if final_cost_twd>0 else cur_cost))) / tot_qty) if tot_qty > 0 else final_cost_twd
                        
                        r = ws_items.find(target['SKU']).row
                        ws_items.update_cell(r, 5, tot_qty)
                        ws_items.update_cell(r, 7, new_avg)
                        ws_items.update_cell(r, 8, get_taiwan_time_str()) # V57 Time
                        if cost_currency == "CNY":
                            ws_items.update_cell(r, 11, "CNY"); ws_items.update_cell(r, 12, int(input_unit_cost))
                        
                        log_event(ws_logs, st.session_state['user_name'], "Restock", f"{target['SKU']} +{qty}")
                        st.success("成功！數據已同步。"); time.sleep(1); st.rerun()

    # Tab 3: Internal (V56.0+V57.0)
    with tabs[2]:
        st.subheader("🎁 內部領用/稽核中心")
        logs_df = get_data_safe(ws_logs)
        audit_data = []
        sku_to_name = dict(zip(df['SKU'], df['Name'])) if not df.empty else {}
        
        if not logs_df.empty:
            int_logs = logs_df[logs_df['Action'] == 'Internal_Use'].copy()
            for i, row in int_logs.iterrows():
                try:
                    details = row['Details']; parts = details.split(' | ')
                    sku_qty = parts[0]; user_log = parts[1] if len(parts) > 1 else row['User']; reason_log = parts[2] if len(parts) > 2 else "-"
                    note_log = parts[3] if len(parts) > 3 else "-"
                    sku_pure = sku_qty.split(' ')[0]; name_pure = sku_to_name.get(sku_pure, "(商品已刪除/未知)")
                    qty_matches = re.findall(r'-?\d+', sku_qty); qty_pure = "?"; qty_val = 0
                    for n in qty_matches:
                        if n.startswith('-'): qty_pure = n; qty_val = abs(int(n))
                    audit_data.append({"日期時間": row['Timestamp'], "貨號": sku_pure, "品名": name_pure, "數量": qty_val, "數量(顯示)": qty_pure, "經手人": user_log, "用途": reason_log, "備註": note_log})
                except: pass
        
        audit_df = pd.DataFrame(audit_data)
        with st.expander("🕵️‍♀️ 進階篩選", expanded=False):
            c_f1, c_f2 = st.columns(2)
            user_filter = []
            if not audit_df.empty: user_filter = c_f1.multiselect("經手人篩選", list(audit_df['經手人'].unique()))
        display_df = audit_df.copy()
        if user_filter: display_df = display_df[display_df['經手人'].isin(user_filter)]
        
        total_items = display_df['數量'].sum() if not display_df.empty else 0
        st.markdown(f"""<div class="audit-dashboard"><div style="display:flex; justify-content:space-around;"><div style="text-align:center;"><div class="audit-title">篩選後筆數</div><div class="audit-stat">{len(display_df)}</div></div><div style="text-align:center;"><div class="audit-title">篩選後總件數</div><div class="audit-stat">{total_items}</div></div></div></div>""", unsafe_allow_html=True)
        if not display_df.empty: st.markdown("##### 👥 人員領用統計"); st.dataframe(display_df.groupby('經手人')['數量'].sum().reset_index().sort_values('數量', ascending=False), use_container_width=True)

        st.divider()
        with st.expander("➕ 新增領用單", expanded=True):
            c_i1, c_i2 = st.columns([1, 1])
            with c_i1:
                if not df.empty: sku_opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} ({x['Size']}) | 現貨:{x['Qty']}", axis=1).tolist()
                else: sku_opts = []
                sel_int_sku = st.selectbox("搜尋具體款式", ["..."] + sku_opts, key="int_sel_v55")
                t_int = None
                if sel_int_sku != "...":
                    target_sku = sel_int_sku.split(" | ")[0]; t_int = df[df['SKU'] == target_sku].iloc[0]; img = render_image_url(t_int['Image_URL'])
                    st.markdown(f"""<div style="border:1px solid #ddd; border-radius:8px; padding:10px; display:flex; align-items:center; background:#fff;"><img src="{img}" style="width:60px; height:60px; object-fit:cover; border-radius:4px; margin-right:10px;"><div><div style="font-weight:bold;">{t_int['Name']}</div><div style="font-family:monospace; color:#555;">{t_int['SKU']}</div><div style="color:#d32f2f; font-weight:bold;">現貨: {t_int['Qty']}</div></div></div>""", unsafe_allow_html=True)
            with c_i2:
                if t_int is not None:
                    with st.form("int_form_v55"):
                        iq = st.number_input("數量", 1, max_value=int(t_int['Qty']) if int(t_int['Qty']) > 0 else 1)
                        who = st.selectbox("領用人", staff_list if staff_list else ["Boss"])
                        rsn = st.selectbox("原因", ["公務制服", "福利", "樣品", "報廢", "其他"])
                        int_note = st.text_input("備註 (選填)")
                        if st.form_submit_button("確認領用 (扣除庫存)", type="primary"):
                            if int(t_int['Qty']) >= iq:
                                r = ws_items.find(t_int['SKU']).row; ws_items.update_cell(r, 5, int(t_int['Qty']) - iq)
                                log_detail = f"{t_int['SKU']} -{iq} | {who} | {rsn} | {int_note}"
                                log_event(ws_logs, st.session_state['user_name'], "Internal_Use", log_detail)
                                st.success(f"✅ 成功！"); time.sleep(1); st.rerun()
                            else: st.error("庫存不足！")

        st.divider(); st.markdown("#### 👁️ 全域領用/報廢總覽")
        if not display_df.empty:
            st.dataframe(display_df[['日期時間', '貨號', '品名', '數量(顯示)', '經手人', '用途', '備註']], use_container_width=True)
            st.markdown("##### 🛠️ 強制回溯操作")
            rev_options = display_df.apply(lambda x: f"{x['日期時間']} | {x['貨號']} ({x['品名']}) | {x['數量(顯示)']}", axis=1).tolist()
            sel_rev_target = st.selectbox("選擇要處理的紀錄", ["..."] + rev_options)
            if sel_rev_target != "...":
                target_ts = sel_rev_target.split(" | ")[0]; target_sku = sel_rev_target.split(" | ")[1].split(" (")[0]
                auto_restore_qty = 1
                try: q_str = sel_rev_target.split(" | ")[-1]; auto_restore_qty = abs(int(q_str))
                except: pass
                c_rev1, c_rev2, c_rev3 = st.columns([1,1,1])
                with c_rev1: manual_qty = st.number_input("🔢 校正歸還數量", min_value=0, value=auto_restore_qty)
                with c_rev2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🚫 歸還庫存並刪除日誌", type="primary"):
                        all_logs = ws_logs.get_all_values(); log_row = -1
                        for idx, row in enumerate(all_logs):
                            if row[0] == target_ts and target_sku in row[3]: log_row = idx + 1; break
                        if log_row != -1:
                            item_cell = ws_items.find(target_sku)
                            if item_cell:
                                curr_q = int(ws_items.cell(item_cell.row, 5).value); ws_items.update_cell(item_cell.row, 5, curr_q + manual_qty); ws_logs.delete_rows(log_row)
                                st.success(f"✅ 已歸還 {target_sku} +{manual_qty}，並移除紀錄。"); time.sleep(2); st.rerun()
                            else: st.error("❌ 商品不存在，請用右側刪除日誌。")
                        else: st.error("❌ 找不到日誌。")
                with c_rev3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ 僅刪除日誌"):
                        all_logs = ws_logs.get_all_values(); log_row = -1
                        for idx, row in enumerate(all_logs):
                            if row[0] == target_ts and target_sku in row[3]: log_row = idx + 1; break
                        if log_row != -1: ws_logs.delete_rows(log_row); st.warning("✅ 已強制移除日誌。"); time.sleep(2); st.rerun()
                        else: st.error("找不到日誌。")
        else: st.info("無紀錄。")

    # Tab 4: Mgmt (V49+V48)
    with tabs[3]:
        mt2, mt3, mt4 = st.tabs(["➕ 單品/全系列新增", "🛠️ 貨號重鑄", "🗑️ 刪除中心"])
        with mt2:
            st.markdown("<div class='sku-wizard'><div class='wizard-header'>🧠 智能矩陣生成</div>", unsafe_allow_html=True)
            gen_mode = st.radio("選擇模式", ["✨ 開闢新系列", "🧬 衍生/新色", "🔗 追加/補貨", "✍️ 手動輸入"], horizontal=True)
            auto_sku = ""; auto_name = ""; auto_img = ""; inherit_price = 0; inherit_cost = 0; inherit_curr = "TWD"; inherit_cat = "上衣(Top)"
            c_gen1, c_gen2 = st.columns([1, 1])
            if "開闢新系列" in gen_mode:
                with c_gen1: g_cat = st.selectbox("1. 選擇分類", CAT_LIST, key="v48_cat")
                with c_gen2:
                    if st.button("🎲 生成建議貨號", use_container_width=True):
                        base_code = generate_smart_style_code(g_cat, df['SKU'].tolist()); st.session_state['temp_base_sku'] = base_code; st.toast(f"Base SKU: {base_code}")
                if 'temp_base_sku' in st.session_state: auto_sku = st.session_state['temp_base_sku']
            elif "衍生/新色" in gen_mode:
                if not df.empty: style_opts = df[['Style_Code', 'Name']].drop_duplicates(subset=['Style_Code', 'Name']).apply(lambda x: f"{x['Style_Code']} | {x['Name']}", axis=1).tolist()
                else: style_opts = []
                with c_gen1: sel_parent = st.selectbox("1. 選擇母系列", ["..."] + style_opts, key="v48_parent")
                with c_gen2: suffix_code = st.text_input("2. 衍生代碼", key="v48_suffix")
                if sel_parent != "..." and suffix_code:
                    p_code = sel_parent.split(" | ")[0]; p_name = sel_parent.split(" | ")[1]; auto_sku = f"{p_code}-{suffix_code}"; auto_name = p_name
                    try: p_row = df[(df['Style_Code'] == p_code) & (df['Name'] == p_name)].iloc[0]; auto_img = p_row['Image_URL']; inherit_price = int(p_row['Price']); inherit_cost = int(p_row['Orig_Cost']) if p_row['Orig_Currency'] == 'CNY' else int(p_row['Cost']); inherit_curr = p_row['Orig_Currency']; inherit_cat = p_row['Category']; st.info(f"🧬 已繼承 [{p_code}]。")
                    except: pass
            elif "追加/補貨" in gen_mode:
                 if not df.empty: style_opts = df[['Style_Code', 'Name']].drop_duplicates(subset=['Style_Code', 'Name']).apply(lambda x: f"{x['Style_Code']} | {x['Name']}", axis=1).tolist()
                 else: style_opts = []
                 with c_gen1: sel_p = st.selectbox("1. 選擇款式", ["..."] + style_opts, key="v48_append")
                 if sel_p != "...":
                     p_c = sel_p.split(" | ")[0]; p_n = sel_p.split(" | ")[1]; auto_sku = p_c; auto_name = p_n
                     try: p_row = df[(df['Style_Code'] == p_c) & (df['Name'] == p_n)].iloc[0]; auto_img = p_row['Image_URL']; inherit_price = int(p_row['Price']); inherit_cost = int(p_row['Orig_Cost']) if p_row['Orig_Currency'] == 'CNY' else int(p_row['Cost']); inherit_curr = p_row['Orig_Currency']; inherit_cat = p_row['Category']
                     except: pass
            st.markdown("</div>", unsafe_allow_html=True)
            with st.form("matrix_add_v48"):
                c_sa, c_sb = st.columns([1, 1]); sku_val = auto_sku if auto_sku else ""; name_val = auto_name if auto_name else ""
                base_sku_input = c_sa.text_input("基礎貨號 (Base SKU)", value=sku_val); name_input = c_sb.text_input("商品名稱", value=name_val)
                c_info1, c_info2, c_info3, c_info4 = st.columns(4)
                cat_input = c_info1.selectbox("分類", CAT_LIST, index=CAT_LIST.index(inherit_cat) if inherit_cat in CAT_LIST else 0)
                price_input = c_info2.number_input("售價", value=inherit_price)
                curr_input = c_info3.selectbox("成本幣別", ["TWD", "CNY"], index=["TWD", "CNY"].index(inherit_curr) if inherit_curr in ["TWD", "CNY"] else 0)
                cost_input = c_info4.number_input("成本金額", value=inherit_cost)
                st.markdown("---"); st.markdown("<div class='batch-title'>🎹 尺寸庫存網格</div>", unsafe_allow_html=True)
                size_inputs = {}
                grid_cols = st.columns(5)
                for i, size in enumerate(SIZE_LIST):
                    with grid_cols[i % 5]:
                        hint_qty = 0
                        if "追加" in gen_mode and base_sku_input:
                            try: check_sku = f"{base_sku_input}-{size}"; row = df[df['SKU'] == check_sku]; hint_qty = int(row.iloc[0]['Qty']) if not row.empty else 0
                            except: pass
                        size_inputs[size] = st.number_input(f"{size}" + (f" (現:{hint_qty})" if hint_qty > 0 else ""), min_value=0, step=1, key=f"v48_qty_{size}")
                st.markdown("---"); final_img_payload = ""
                if auto_img: st.image(auto_img, width=100, caption="繼承圖片"); final_img_payload = auto_img
                img_file = st.file_uploader("上傳圖片", type=['jpg','png'])
                if st.form_submit_button("🚀 批量建立/更新庫存", use_container_width=True, type="primary"):
                    if base_sku_input and name_input:
                        if img_file: new_u = upload_image_to_imgbb(img_file); final_img_payload = new_u if new_u else final_img_payload
                        final_cost_val = int(cost_input * st.session_state['exchange_rate']) if curr_input == "CNY" else int(cost_input)
                        updates = 0; creates = 0; sku_log = []
                        for size, qty in size_inputs.items():
                            if qty > 0:
                                full_sku = f"{base_sku_input}-{size}"
                                if full_sku in df['SKU'].tolist():
                                    r = ws_items.find(full_sku).row
                                    current_q_val = int(df[df['SKU'] == full_sku].iloc[0]['Qty'])
                                    ws_items.update_cell(r, 5, current_q_val + qty); ws_items.update_cell(r, 8, get_taiwan_time_str())
                                    ws_items.update_cell(r, 2, name_input); ws_items.update_cell(r, 6, price_input)
                                    if final_img_payload: ws_items.update_cell(r, 9, final_img_payload)
                                    updates += 1; sku_log.append(f"{size}(+{qty})")
                                else:
                                    ws_items.append_row([full_sku, name_input, cat_input, size, qty, price_input, final_cost_val, get_taiwan_time_str(), final_img_payload, 5, curr_input, cost_input])
                                    creates += 1; sku_log.append(f"{size}:{qty}")
                        if updates + creates > 0: log_event(ws_logs, st.session_state['user_name'], "Matrix_Batch", f"{base_sku_input} | {', '.join(sku_log)}"); st.success("✅ 成功！"); time.sleep(1); st.rerun()
                        else: st.warning("⚠️ 未輸入任何尺寸數量。")
                    else: st.error("❌ 請填寫完整貨號與名稱。")
        with mt3:
            st.markdown("<div class='refactor-zone'><div class='refactor-header'>🛠️ 貨號重鑄與遷移</div>", unsafe_allow_html=True)
            if not df.empty: style_opts = df[['Style_Code', 'Name']].drop_duplicates(subset=['Style_Code', 'Name']).apply(lambda x: f"{x['Style_Code']} | {x['Name']}", axis=1).tolist()
            else: style_opts = []
            target_sel = st.selectbox("1. 選擇要修正的款式", ["..."] + style_opts, key="refactor_sel")
            if target_sel != "...":
                old_code = target_sel.split(" | ")[0]; old_name = target_sel.split(" | ")[1]
                affected_rows = df[(df['Style_Code'] == old_code) & (df['Name'] == old_name)]
                st.write(f"即將影響 {len(affected_rows)} 筆資料："); st.dataframe(affected_rows[['SKU', 'Name', 'Size']])
                c_new1, c_new2 = st.columns(2); new_base_code = c_new1.text_input("2. 輸入新貨號基底"); new_name_input = c_new2.text_input("3. 確認/修改名稱", value=old_name)
                if st.button("☣️ 執行重鑄遷移", type="primary", disabled=not new_base_code):
                    try:
                        count = 0; total = len(affected_rows); my_bar = st.progress(0, text="Migrating...")
                        for idx, row in affected_rows.iterrows():
                            new_full_sku = f"{new_base_code}-{row['Size']}"; cell = ws_items.find(row['SKU']); r = cell.row
                            ws_items.update_cell(r, 1, new_full_sku); ws_items.update_cell(r, 2, new_name_input)
                            count += 1; my_bar.progress(int(count/total * 100)); time.sleep(0.5)
                        st.success("✅ 遷移完成！"); log_event(ws_logs, st.session_state['user_name'], "Refactor_SKU", f"{old_code} -> {new_base_code}"); time.sleep(2); st.rerun()
                    except Exception as e: st.error(f"遷移失敗: {e}")
            st.markdown("</div>", unsafe_allow_html=True)
        with mt4:
            st.markdown("<div class='delete-zone'><div class='delete-header'>🗑️ 刪除中心</div>", unsafe_allow_html=True)
            del_mode = st.radio("選擇刪除模式", ["單品刪除", "全款刪除"], horizontal=True)
            if del_mode == "單品刪除":
                d_sku_sel = st.selectbox("選擇單品", ["..."] + (df['SKU'].tolist() if not df.empty else []), key="del_sku_sel")
                if d_sku_sel != "...":
                    if st.button("🚫 執行刪除", type="primary"):
                        try: cell = ws_items.find(d_sku_sel); ws_items.delete_rows(cell.row); st.success("已刪除"); time.sleep(1); st.rerun()
                        except: st.error("刪除失敗")
            elif del_mode == "全款刪除":
                d_style_sel = st.selectbox("選擇款式", ["..."] + style_opts, key="del_style_sel")
                if d_style_sel != "...":
                    target_code = d_style_sel.split(" | ")[0]; target_name = d_style_sel.split(" | ")[1]
                    to_delete_df = df[(df['Style_Code'] == target_code) & (df['Name'] == target_name)]
                    st.dataframe(to_delete_df[['SKU', 'Name', 'Size', 'Qty']])
                    if st.button("☢️ 執行全款刪除", type="primary"):
                        try:
                            rows_to_del = []; 
                            for idx, row in to_delete_df.iterrows(): cell = ws_items.find(row['SKU']); rows_to_del.append(cell.row)
                            rows_to_del.sort(reverse=True)
                            for r_idx in rows_to_del: ws_items.delete_rows(r_idx)
                            st.success("刪除完成！"); time.sleep(1); st.rerun()
                        except: st.error("刪除失敗")
            st.markdown("</div>", unsafe_allow_html=True)

    with tabs[4]:
        st.subheader("🕵️ 稽核日誌")
        logs_df = get_data_safe(ws_logs)
        if not logs_df.empty: st.dataframe(logs_df.sort_index(ascending=False), use_container_width=True)
    with tabs[5]:
        if st.session_state['user_role'] == 'Admin':
            st.subheader("👥 人員管理")
            users_df = get_data_safe(ws_users)
            st.dataframe(users_df, use_container_width=True)
            if st.button("☢️ 清空日誌"): ws_logs.clear(); ws_logs.append_row(["Timestamp", "User", "Action", "Details"]); st.rerun()

if __name__ == "__main__":
    main()
