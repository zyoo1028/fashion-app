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

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK 企業資源中樞", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【MATRIX-V46.0 全域聯動與介面重塑核心】
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

        .history-card { display: flex; align-items: center; background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 10px; margin-bottom: 8px; }
        .history-img { width: 50px; height: 50px; border-radius: 5px; object-fit: cover; margin-right: 10px; flex-shrink: 0; }
        .history-tag { background: #ffe0b2; color: #e65100 !important; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; margin-left: auto; white-space: nowrap; }

        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border:none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); background-color: #FFFFFF; color: #000000; border: 1px solid #E5E7EB; }
        [data-testid="stDataFrame"] { border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden; }
        
        /* --- 4. 生成區塊與網格樣式 (V45/V46) --- */
        .sku-wizard {
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
            border: 1px solid #e2e8f0;
            padding: 20px;
            border-radius: 16px;
            margin-bottom: 20px;
        }
        .wizard-header { color: #334155 !important; font-weight: 800; font-size: 1.1em; margin-bottom: 15px; display:flex; align-items:center; gap:8px;}
        
        /* 強制對齊的 Label 與 提示 */
        .stNumberInput label { font-size: 0.85rem; font-weight: 700; color: #444; }
        .sku-hint { font-size: 0.7rem; color: #94a3b8; margin-top: -15px; margin-bottom: 10px; display: block; font-family: monospace; }
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

# --- 工具模組 ---

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

# ----------------------------------------------------
# 🛑 V46.0 核心修正
# ----------------------------------------------------
def get_style_code(sku):
    sku_str = str(sku).strip()
    if '-' in sku_str:
        return sku_str.rsplit('-', 1)[0]
    return sku_str

# V46: 智能排序
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
    date_code = datetime.now().strftime("%y%m")
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
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>MATRIX ERP V46.0</div>", unsafe_allow_html=True)
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
    
    # V46: 簡單分割
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
    tabs = st.tabs(["📊 視覺庫存", "⚡ POS", "🎁 內部領用", "👔 矩陣管理", "📝 日誌", "👥 Admin"])

    # Tab 1: 視覺總覽 (Grid & Sort Fix)
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
                top_items = df.groupby(['Style_Code', 'Name']).agg({'Qty':'sum'}).reset_index().sort_values(by='Qty', ascending=False).head(10)
                fig_bar = px.bar(top_items, x='Qty', y='Name', orientation='h', text='Qty', color='Qty', color_continuous_scale='Bluered')
                fig_bar.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0), yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)
        
        st.divider()
        st.subheader("🖼️ 庫存畫廊 (Visual Inventory)")
        
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
                
                # 🛑 V46: 智能排序與顯示
                group['size_sort'] = group['Size'].apply(get_size_sort_key)
                sorted_group = group.sort_values('size_sort')

                with st.expander(f"📦 {name} ({style_code}) - 總庫存: {total_qty}", expanded=False):
                    c_card1, c_card2 = st.columns([1, 2])
                    with c_card1:
                        st.image(img, use_column_width=True)
                        st.markdown(f"**NT$ {price}**")
                    with c_card2:
                        st.markdown("#### 📝 管理庫存")
                        with st.form(f"dyn_form_{style_code}_{name}"):
                            # 🛑 V46: 強制 4 欄位網格 + 智能提示
                            inputs = {}
                            grid_cols = st.columns(4)
                            
                            for idx, row in enumerate(sorted_group.iterrows()):
                                _, r_data = row
                                with grid_cols[idx % 4]: 
                                    count_of_this_size = sorted_group[sorted_group['Size'] == r_data['Size']].shape[0]
                                    label = f"{r_data['Size']}"
                                    if count_of_this_size > 1:
                                        # 顯示完整 SKU 尾碼以供辨識
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
                                        ws_items.update_cell(r, 8, str(datetime.now()))
                                        changes.append(f"{t_sku.split('-')[-1]}:{new_q}")
                                log_event(ws_logs, st.session_state['user_name'], "Quick_Update", f"{style_code} | {', '.join(changes)}")
                                st.success("更新完成！"); time.sleep(1); st.rerun()

        else: st.info("無符合資料")

        st.markdown("##### 📦 庫存明細 (歸戶檢視)")
        if not gallery_df.empty:
            agg_df = gallery_df.groupby(['Style_Code', 'Name']).agg({
                'Category': 'first',
                'Qty': 'sum',
                'Price': 'max',
                'Cost': 'mean',
                'Orig_Cost': 'first',
                'Orig_Currency': 'first',
                'Last_Updated': 'max'
            }).reset_index()
            
            def get_stock_dist(row):
                grp = gallery_df[(gallery_df['Style_Code'] == row['Style_Code']) & (gallery_df['Name'] == row['Name'])]
                grp['s_sort'] = grp['Size'].apply(get_size_sort_key)
                grp = grp.sort_values('s_sort')
                dist = []
                for _, r in grp.iterrows():
                    dist.append(f"{r['Size']}:{r['Qty']}")
                return ", ".join(dist)
            
            agg_df['Size_Detail'] = agg_df.apply(get_stock_dist, axis=1)
            agg_df['Total_Qty'] = agg_df['Qty']
            agg_df['Avg_Cost'] = agg_df['Cost'].astype(int)
            agg_df['Ref_Orig_Cost'] = agg_df.apply(lambda x: f"¥{x['Orig_Cost']}" if x['Orig_Currency'] == 'CNY' else "-", axis=1)
            
            agg_df = agg_df.rename(columns=COLUMN_MAPPING)
            show_cols = ["款號(Style)", "商品名稱", "分類", "庫存分佈", "總庫存", "售價(NTD)", "平均成本(NTD)", "參考原幣(CNY)", "最後更新"]
            st.dataframe(agg_df[show_cols], use_container_width=True)

    # Tab 2: POS
    with tabs[1]:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("商品")
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist()
            sel = st.selectbox("選擇商品", ["..."] + opts)
            target = None
            if sel != "...":
                target = df[df['SKU'] == sel.split(" | ")[0]].iloc[0]
                img = render_image_url(target['Image_URL'])
                orig_show = f"<span class='cost-tag'>原幣: ¥{target['Orig_Cost']}</span>" if target['Orig_Currency'] == 'CNY' else ""
                card_html = f"""
                <div style="display:flex; align-items:center; background:#f9f9f9; padding:15px; border-radius:10px;">
                    <img src="{img}" style="width:80px; height:80px; border-radius:8px; object-fit:cover; margin-right:15px;">
                    <div>
                        <div style="font-weight:bold; font-size:18px;">{target['Name']}</div>
                        <div style="color:#666;">{target['SKU']}</div>
                        <div style="margin-top:5px;">成本: <b>NT${target['Cost']}</b> {orig_show}</div>
                        <div style="font-weight:bold; color:#d32f2f; font-size:20px; margin-top:5px;">現貨: {target['Qty']}</div>
                    </div>
                </div>
                """
                st.markdown(card_html.replace('\n', ''), unsafe_allow_html=True)
        with c2:
            st.subheader("操作")
            if target is not None:
                qty = st.number_input("數量", 1)
                t1, t2 = st.tabs(["📥 進貨", "📤 銷售"])
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
                    int_note = st.text_input("備註")
                    if st.form_submit_button("領用 (扣除庫存)"):
                        r = ws_items.find(t_int['SKU']).row
                        ws_items.update_cell(r, 5, int(t_int['Qty']) - iq)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{t_int['SKU']} -{iq} | {who}")
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
                        card_html = f"""
                        <div class="history-card">
                            <img src="{img_url}" class="history-img">
                            <div style="flex:1">
                                <div style="font-weight:bold; font-size:14px;">{log['User']}</div>
                                <div style="font-size:12px; color:#666;">{log['Details']}</div>
                                <div style="font-size:10px; color:#999;">{log['Timestamp']}</div>
                            </div>
                            <div class="history-tag">Internal</div>
                        </div>
                        """
                        st.markdown(card_html.replace('\n', ''), unsafe_allow_html=True)
                    except: pass

    # Tab 4: Mgmt
    with tabs[3]:
        mt1, mt2, mt3 = st.tabs(["🚀 矩陣批量 (新款/追加)", "➕ 單品新增 (智能版)", "✏️ 數據修改"])
        
        # SubTab 1: 矩陣批量
        with mt1:
            st.markdown("##### 👔 款式矩陣中樞")
            st.caption("輸入款號，自動判斷新增或追加。")
            all_skus = df['SKU'].tolist()
            existing_styles = sorted(list(set([get_style_code(s) for s in all_skus])))
            
            c_style1, c_style2 = st.columns([1, 2])
            with c_style1:
                cat_batch = st.selectbox("分類", CAT_LIST, key="batch_cat")
                if st.button("🎲 生成新款號"):
                    new_style = generate_smart_style_code(cat_batch, all_skus)
                    st.session_state['matrix_style_code'] = new_style.rsplit('-', 1)[0] if '-' in new_style else new_style
                    st.toast(f"已生成: {st.session_state['matrix_style_code']}")

            with c_style2:
                input_style = st.text_input("輸入款號 (Ex: TOP-2601)", value=st.session_state.get('matrix_style_code', ""), key="matrix_input")
                sel_exist = st.selectbox("或選擇現有款式:", ["..."] + existing_styles)
                if sel_exist != "...": input_style = sel_exist

            if input_style:
                related_skus = df[df['SKU'].str.startswith(input_style + "-")]
                is_edit_mode = not related_skus.empty
                
                if is_edit_mode:
                    st.success(f"🟢 [{input_style}] 已存在。已自動繼承成本與圖片。")
                    first_row = related_skus.iloc[0]
                    default_name = first_row['Name']; default_price = int(first_row['Price']); default_cost_twd = int(first_row['Cost'])
                    default_currency = first_row['Orig_Currency']; default_orig_cost = int(first_row['Orig_Cost'])
                    default_img = first_row['Image_URL']
                else:
                    st.info(f"🔵 [{input_style}] 為新商品。")
                    default_name = ""; default_price = 0; default_cost_twd = 0; default_currency = "TWD"; default_orig_cost = 0; default_img = ""

                with st.form("matrix_form"):
                    st.markdown("#### 1. 款式參數")
                    name_b = st.text_input("商品名稱", value=default_name)
                    c_p1, c_p2 = st.columns(2)
                    price_b = c_p1.number_input("售價 (NTD)", value=default_price)
                    c_curr_b, c_cost_b = c_p2.columns([1, 1])
                    curr_sel_b = c_curr_b.selectbox("成本幣別", ["TWD", "CNY"], index=["TWD", "CNY"].index(default_currency) if default_currency in ["TWD", "CNY"] else 0)
                    cost_in_b = c_cost_b.number_input("成本金額", value=default_orig_cost if curr_sel_b=="CNY" else default_cost_twd)
                    final_cost_b = int(cost_in_b * st.session_state['exchange_rate']) if curr_sel_b == "CNY" else int(cost_in_b)
                    
                    img_b = st.file_uploader("圖片 (若不修改請留空)", type=['jpg','png'])
                    
                    st.markdown("#### 2. 尺寸矩陣")
                    # 🛑 V45/V46: 矩陣輸入網格化
                    size_cols1 = st.columns(5)
                    size_inputs = {}
                    for idx, size in enumerate(SIZE_LIST[:5]):
                        current_q = 0
                        if is_edit_mode:
                            target_sku = f"{input_style}-{size}"
                            match = related_skus[related_skus['SKU'] == target_sku]
                            if not match.empty: current_q = int(match.iloc[0]['Qty'])
                        with size_cols1[idx]:
                            size_inputs[size] = st.number_input(f"{size}", min_value=0, value=current_q, key=f"mx_{size}")

                    size_cols2 = st.columns(5)
                    for idx, size in enumerate(SIZE_LIST[5:]):
                        if idx < 5:
                            current_q = 0
                            if is_edit_mode:
                                target_sku = f"{input_style}-{size}"
                                match = related_skus[related_skus['SKU'] == target_sku]
                                if not match.empty: current_q = int(match.iloc[0]['Qty'])
                            with size_cols2[idx]:
                                size_inputs[size] = st.number_input(f"{size}", min_value=0, value=current_q, key=f"mx_{size}")

                    if st.form_submit_button("🚀 執行同步"):
                        if name_b and input_style:
                            final_u = default_img
                            if img_b:
                                new_u = upload_image_to_imgbb(img_b)
                                if new_u: final_u = new_u
                            ocode = "CNY" if curr_sel_b == "CNY" else "TWD"
                            updated_count = 0; created_count = 0
                            for size, new_q in size_inputs.items():
                                target_sku = f"{input_style}-{size}"
                                if target_sku in df['SKU'].tolist():
                                    r = ws_items.find(target_sku).row
                                    ws_items.update_cell(r, 2, name_b); ws_items.update_cell(r, 3, cat_batch)
                                    ws_items.update_cell(r, 5, new_q); ws_items.update_cell(r, 6, price_b)
                                    ws_items.update_cell(r, 7, final_cost_b); ws_items.update_cell(r, 8, str(datetime.now()))
                                    if img_b: ws_items.update_cell(r, 9, final_u)
                                    ws_items.update_cell(r, 11, ocode); ws_items.update_cell(r, 12, cost_in_b)
                                    updated_count += 1
                                elif new_q > 0:
                                    ws_items.append_row([target_sku, name_b, cat_batch, size, new_q, price_b, final_cost_b, str(datetime.now()), final_u, 5, ocode, cost_in_b])
                                    created_count += 1
                            log_event(ws_logs, st.session_state['user_name'], "Matrix_Sync", f"{input_style} | U:{updated_count} C:{created_count}")
                            st.success(f"完成！更新 {updated_count} 筆，新增 {created_count} 筆。"); time.sleep(2); st.rerun()
                        else: st.error("請填寫完整")

        # SubTab 2: 單品新增
        with mt2:
            st.markdown("<div class='sku-wizard'><div class='wizard-header'>🧠 智能單品生成 (Smart Single Add)</div>", unsafe_allow_html=True)
            
            gen_mode = st.radio("選擇模式", ["✨ 開闢新系列 (New Series)", "🎨 同款新色 (Color Variant)", "🔗 追加尺寸 (Append Size)", "✍️ 手動輸入"], horizontal=True)
            
            auto_sku = ""
            auto_name = ""
            auto_img = ""
            parent_style_info = None

            c_gen1, c_gen2 = st.columns([1, 1])

            if "開闢新系列" in gen_mode:
                with c_gen1: g_cat = st.selectbox("1. 選擇分類", CAT_LIST, key="v46_cat")
                with c_gen2: g_size = st.selectbox("2. 選擇尺寸", SIZE_LIST, key="v46_size")
                if st.button("🎲 生成建議貨號", use_container_width=True):
                    style_base = generate_smart_style_code(g_cat, df['SKU'].tolist())
                    auto_sku = f"{style_base}-{g_size}"
                    st.session_state['temp_sku'] = auto_sku
                    st.toast(f"Generated: {auto_sku}")
                if 'temp_sku' in st.session_state: auto_sku = st.session_state['temp_sku']

            elif "同款新色" in gen_mode:
                # 🛑 V46 關鍵修正：同時使用 Style_Code 和 Name 進行去重，防止同代碼不同款被過濾
                if not df.empty:
                    style_opts = df[['Style_Code', 'Name']].drop_duplicates(subset=['Style_Code', 'Name']).apply(lambda x: f"{x['Style_Code']} | {x['Name']}", axis=1).tolist()
                else: style_opts = []
                
                with c_gen1: 
                    sel_parent = st.selectbox("1. 選擇母系列 (繼承圖片/成本)", ["..."] + style_opts, key="v46_parent")
                with c_gen2:
                    c_col1, c_col2 = st.columns(2)
                    color_code = c_col1.text_input("2a. 新色代碼 (Ex: BK)", key="v46_color")
                    g_size_col = c_col2.selectbox("2b. 尺寸", SIZE_LIST, key="v46_size_col")
                
                if sel_parent != "..." and color_code:
                    p_code = sel_parent.split(" | ")[0]
                    p_name = sel_parent.split(" | ")[1]
                    auto_sku = f"{p_code}-{color_code}-{g_size_col}"
                    auto_name = p_name
                    try:
                        p_row = df[(df['Style_Code'] == p_code) & (df['Name'] == p_name)].iloc[0]
                        auto_img = p_row['Image_URL']
                        st.info(f"🎨 已繼承 [{p_code} {p_name}] 資料。")
                    except: pass
            
            elif "追加尺寸" in gen_mode:
                 if not df.empty:
                    style_opts = df[['Style_Code', 'Name']].drop_duplicates(subset=['Style_Code', 'Name']).apply(lambda x: f"{x['Style_Code']} | {x['Name']}", axis=1).tolist()
                 else: style_opts = []
                 with c_gen1: sel_p = st.selectbox("1. 選擇款式", ["..."] + style_opts, key="v46_append")
                 with c_gen2: g_sz = st.selectbox("2. 追加尺寸", SIZE_LIST, key="v46_sz_app")
                 if sel_p != "...":
                     p_c = sel_p.split(" | ")[0]
                     p_n = sel_p.split(" | ")[1]
                     auto_sku = f"{p_c}-{g_sz}"
                     auto_name = p_n
                     try: 
                         auto_img = df[(df['Style_Code'] == p_c) & (df['Name'] == p_n)].iloc[0]['Image_URL']
                     except: pass
            
            st.markdown("</div>", unsafe_allow_html=True)

            with st.form("single_add_v46"):
                c_sa, c_sb = st.columns([1, 1])
                sku_val = auto_sku if auto_sku else ""
                name_val = auto_name if auto_name else ""
                
                sku_s = c_sa.text_input("貨號 (SKU)", value=sku_val)
                name_s = c_sb.text_input("商品名稱", value=name_val)
                
                c_s1, c_s2, c_s3, c_s4 = st.columns(4)
                cat_s = c_s1.selectbox("分類", CAT_LIST)
                
                def_size_idx = 0
                if sku_val:
                    last_part = sku_val.split('-')[-1]
                    if last_part in SIZE_LIST: def_size_idx = SIZE_LIST.index(last_part)
                size_s = c_s2.selectbox("尺寸", SIZE_LIST, index=def_size_idx)
                
                price_s = c_s3.number_input("售價", 0)
                qty_s = c_s4.number_input("數量", 0)
                
                c_sc1, c_sc2 = st.columns([1, 1])
                curr_s = c_sc1.selectbox("成本幣別", ["TWD", "CNY"])
                cost_s = c_sc2.number_input("成本金額", 0)
                
                st.markdown("---")
                final_img_payload = ""
                if auto_img:
                    st.image(auto_img, width=100, caption="已繼承圖片")
                    final_img_payload = auto_img
                
                img_s = st.file_uploader("上傳圖片 (若已繼承則選填)", type=['jpg','png'])
                
                if st.form_submit_button("新增單品"):
                    if sku_s and name_s:
                        if sku_s in df['SKU'].tolist():
                            st.error("❌ 貨號已存在！請使用數據修改。")
                        else:
                            if img_s:
                                new_u = upload_image_to_imgbb(img_s)
                                if new_u: final_img_payload = new_u
                            
                            final_c_s = int(cost_s * st.session_state['exchange_rate']) if curr_s == "CNY" else int(cost_s)
                            ocode_s = "CNY" if curr_s == "CNY" else "TWD"
                            
                            ws_items.append_row([sku_s, name_s, cat_s, size_s, qty_s, price_s, final_c_s, str(datetime.now()), final_img_payload, 5, ocode_s, cost_s])
                            log_event(ws_logs, st.session_state['user_name'], "New_Item", f"單品: {sku_s}")
                            st.success("成功"); time.sleep(1); st.rerun()

        # SubTab 3: 修改
        with mt3:
            st.markdown("##### ✏️ 數據修改")
            edit_target_sku = st.selectbox("選擇對象", ["..."] + opts)
            if edit_target_sku != "...":
                t_sku = edit_target_sku.split(" | ")[0]
                t_row = df[df['SKU'] == t_sku].iloc[0]
                with st.form("edit_form_single"):
                    e_name = st.text_input("名稱", value=t_row['Name'])
                    c_e1, c_e2, c_e3 = st.columns(3)
                    e_price = c_e1.number_input("售價", value=int(t_row['Price']))
                    e_safe = c_e2.number_input("安全庫存", value=int(t_row['Safe_Level']))
                    curr_cat_idx = CAT_LIST.index(t_row['Category']) if t_row['Category'] in CAT_LIST else 0
                    e_cat = c_e3.selectbox("分類", CAT_LIST, index=curr_cat_idx)
                    e_img = st.file_uploader("更新圖片", type=['jpg','png'])
                    if st.form_submit_button("💾 儲存修改"):
                        r_idx = ws_items.find(t_sku).row
                        ws_items.update_cell(r_idx, 2, e_name); ws_items.update_cell(r_idx, 3, e_cat)
                        ws_items.update_cell(r_idx, 6, e_price); ws_items.update_cell(r_idx, 10, e_safe)
                        ws_items.update_cell(r_idx, 8, str(datetime.now()))
                        if e_img:
                            new_u = upload_image_to_imgbb(e_img)
                            if new_u: ws_items.update_cell(r_idx, 9, new_u)
                        log_event(ws_logs, st.session_state['user_name'], "Edit_Item", f"修改: {t_sku}")
                        st.success("修改完成！"); time.sleep(1); st.rerun()

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
