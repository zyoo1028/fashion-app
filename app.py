import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, date
import time
import requests
import plotly.express as px
import base64
import hashlib
import math
import re
import random
import calendar
import matplotlib.pyplot as plt
import io
import matplotlib.font_manager as fm
import os

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK ERP V122.0 OMNI-PRECISION", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【CSS 視覺核心：完全保留 V120.0】
# ==========================================
st.markdown("""
    <style>
        html, body, [class*="css"], [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; color: #0f172a !important; }
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; }
        [data-testid="stHeader"] { background-color: #FFFFFF !important; }
        p, span, h1, h2, h3, h4, h5, h6, label, div, th, td, li, a { color: #0f172a !important; }
        .shift-pill, .shift-pill span, .store-closed, .store-closed span { color: #ffffff !important; }
        button[data-testid="baseButton-primary"] p, button[kind="primary"] p { color: #ffffff !important; }
        .st-emotion-cache-1n76uvr { color: #ffffff !important; }
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input, textarea {
            color: #0f172a !important; background-color: #FFFFFF !important;
            -webkit-text-fill-color: #0f172a !important; caret-color: #0f172a !important;
            border-color: #E5E7EB !important;
        }
        div[data-baseweb="select"] > div, div[data-baseweb="popover"] * { background-color: #FFFFFF !important; color: #0f172a !important; }
        button[data-baseweb="tab"] { background-color: #f8fafc !important; border-bottom: 2px solid #e2e8f0 !important; }
        button[data-baseweb="tab"][aria-selected="true"] { border-bottom: 2px solid #2563eb !important; background-color: #ffffff !important; }
        button[data-baseweb="tab"] p { font-weight: 800 !important; font-size: 1rem !important; }
        .pos-card, .inv-row, .finance-card, .metric-card, .cart-box, .mgmt-box {
            background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important; color: #0f172a !important;
        }
        .pos-img { width: 100%; height: 160px; object-fit: cover; background: #f9fafb; border-bottom: 1px solid #f3f4f6; }
        .pos-content { padding: 10px; flex-grow: 1; display: flex; flex-direction: column; }
        .pos-title { font-weight: bold; font-size: 1rem; margin-bottom: 4px; color: #111 !important; line-height: 1.3; }
        .stock-tag-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; margin-bottom: 5px; }
        .stock-tag { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; border: 1px solid transparent; }
        .stock-tag.has-stock { background-color: #dcfce7 !important; color: #166534 !important; border-color: #bbf7d0; }
        .stock-tag.no-stock { background-color: #fee2e2 !important; color: #991b1b !important; border-color: #fecaca; }
        .inv-row { display: flex; align-items: start; gap: 12px; padding: 12px; border-radius: 12px; margin-bottom: 10px; }
        .inv-img { width: 90px; height: 90px; object-fit: cover; border-radius: 8px; flex-shrink: 0; background: #f1f5f9; }
        .inv-info { flex-grow: 1; }
        .inv-title { font-size: 1.1rem; font-weight: bold; color: #0f172a !important; margin-bottom: 4px; }
        .roster-header { background: #f1f5f9 !important; padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e2e8f0; text-align: center; }
        .day-cell { border: 1px solid #e2e8f0; border-radius: 8px; padding: 5px; min-height: 110px; position: relative; margin-bottom: 5px; background: #fff !important; display: flex; flex-direction: column; gap: 4px; }
        .desktop-shift-pill { flex: 1; display: flex; align-items: center; justify-content: center; width: 100%; font-size: 1.05rem; font-weight: 900; border-radius: 6px; color: white !important; box-shadow: 0 1px 3px rgba(0,0,0,0.15); min-height: 35px; letter-spacing: 1px;}
        .mobile-day-row { background: #FFFFFF !important; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }
        .mobile-day-date { font-size: 1.1rem; font-weight: 900; color: #334155 !important; width: 50px; text-align: center; border-right: 2px solid #f1f5f9; margin-right: 10px; }
        .mobile-day-content { flex-grow: 1; }
        .shift-pill { font-size: 0.8rem; padding: 4px 8px; border-radius: 6px; margin-bottom: 4px; display: inline-block; text-align: center; font-weight: bold; margin-right: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .store-closed { flex: 1; width: 100%; background-color: #EF4444 !important; font-weight: 900; font-size: 1.1rem; display: flex; align-items: center; justify-content: center; border-radius: 6px; min-height: 40px; color: white !important;}
        .metric-card { background: linear-gradient(145deg, #ffffff, #f8fafc) !important; border: 1px solid #e2e8f0 !important; padding: 10px !important;}
        .metric-value { color: #0f172a !important; font-size: 1.2rem !important; font-weight: 900 !important;}
        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border: 1px solid #cbd5e1; background-color: #FFFFFF !important; width: 100%; transition: all 0.2s; }
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- OMEGA 防禦層 ---
def retry_action(func, *args, **kwargs):
    max_retries = 15
    for i in range(max_retries):
        try: return func(*args, **kwargs)
        except Exception as e:
            if any(err in str(e) for err in ["429", "Quota exceeded", "1006", "500", "503", "502"]):
                wait_time = (1.5 ** i) + random.uniform(0.5, 1.5)
                time.sleep(wait_time); continue
            else: raise e
    return None

@st.cache_resource(ttl=600)
def get_connection():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=10, show_spinner=False)
def get_data_safe(_ws, expected_headers=None):
    try:
        raw_data = _ws.get_all_values()
        if not raw_data or len(raw_data) < 2: return pd.DataFrame(columns=expected_headers)
        df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
        if 'SKU' in df.columns: df['SKU'] = df['SKU'].astype(str).str.strip(); df = df[df['SKU'] != '']
        return df
    except: return pd.DataFrame(columns=expected_headers)

@st.cache_resource(ttl=600)
def init_db():
    try: return get_connection().open_by_url(GOOGLE_SHEET_URL)
    except: return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except:
        ws = sh.add_worksheet(title, rows=100, cols=20)
        ws.append_row(headers); return ws

# --- 工具模組 ---
def get_taiwan_time_str(): return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
@st.cache_data(ttl=3600)
def get_live_rate():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/CNY", timeout=5)
        if r.status_code == 200: return r.json()['rates']['TWD'], True
    except: pass
    return 4.50, False

def make_hash(password): return hashlib.sha256(str(password).encode()).hexdigest()
def check_hash(password, hashed_text): return make_hash(password) == hashed_text
def render_image_url(url_input):
    s = str(url_input).strip()
    return s if len(s) > 10 and s.startswith("http") else "https://i.ibb.co/W31w56W/placeholder.png"

def upload_image_to_imgbb(image_file):
    try:
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(image_file.getvalue()).decode('utf-8')}
        r = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if r.status_code == 200: return r.json()["data"]["url"]
    except: return None

def log_event(ws_logs, user, action, detail):
    try: retry_action(ws_logs.append_row, [get_taiwan_time_str(), user, action, detail])
    except: pass

def get_style_code(sku): return str(sku).strip().rsplit('-', 1)[0] if '-' in str(sku) else str(sku).strip()
SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
def get_size_sort_key(size_str): return SIZE_ORDER.index(size_str) if size_str in SIZE_ORDER else 99 

def calculate_realized_revenue(logs_df):
    total = 0
    if logs_df.empty or 'Action' not in logs_df.columns: return 0
    sales_logs = logs_df[logs_df['Action'] == 'Sale']
    for _, row in sales_logs.iterrows():
        match = re.search(r'Total:\s*\$?\s*(\d+)', str(row['Details']))
        if match: total += int(match.group(1))
    return total

def calculate_sunk_cost(logs_df, cost_map):
    sunk_total = 0
    if logs_df.empty or 'Action' not in logs_df.columns: return 0
    int_logs = logs_df[logs_df['Action'] == 'Internal_Use']
    for _, row in int_logs.iterrows():
        try:
            parts = str(row['Details']).split(' | ')
            sku = parts[0].split(' -')[0].strip(); qty = int(parts[0].split(' -')[1])
            unit_cost = int(parts[4].replace("Cost:", "").strip()) if len(parts) > 4 else cost_map.get(sku, 0)
            sunk_total += (unit_cost * qty)
        except: pass
    return sunk_total

def render_navbar(user_initial):
    d_str = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y/%m/%d")
    rate = st.session_state.get('exchange_rate', 4.5)
    st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; background:#fff; padding:15px; border-bottom:1px solid #e2e8f0; margin-bottom:15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div><span style="font-size:18px; font-weight:900; color:#0f172a;">IFUKUK GLOBAL</span><br><span style="font-size:11px; color:#64748b;">{d_str} • Rate: {rate}</span></div>
            <div style="width:36px; height:36px; background:#0f172a; color:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold;">{user_initial}</div>
        </div>
    """, unsafe_allow_html=True)

CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]

# ==========================================
# 🗓️ 排班系統 V120.0 完整保留
# ==========================================
SHIFT_COLORS = { "早班": "#3B82F6", "晚班": "#8B5CF6", "全班": "#10B981", "代班": "#F59E0B", "公休": "#EF4444", "特休": "#DB2777", "空班": "#6B7280", "事假": "#EC4899", "病假": "#14B8A6" }
def get_staff_color_map(users_list):
    PALETTE = ["#2563EB", "#059669", "#7C3AED", "#DB2777", "#D97706", "#DC2626", "#0891B2", "#4F46E5", "#BE123C", "#B45309"]
    return {u: PALETTE[i % len(PALETTE)] for i, u in enumerate(sorted([x for x in users_list if x != "全店"]))}

@st.cache_resource(show_spinner=False)
def get_chinese_font():
    font_path = "NotoSansTC.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/notosanstc/NotoSansTC-Regular.ttf"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                with open(font_path, 'wb') as f: f.write(r.content)
        except: pass
    return font_path if os.path.exists(font_path) else None

def generate_roster_image_buffer(year, month, shifts_df, days_in_month, color_map):
    try:
        font_path = get_chinese_font(); prop = fm.FontProperties(fname=font_path) if font_path else fm.FontProperties()
        fig, ax = plt.subplots(figsize=(14, 10), facecolor='#f8fafc'); ax.axis('off')
        ax.text(0.5, 0.95, f"IFUKUK 專業排班表 - {year}/{month}", ha='center', va='center', fontsize=26, fontproperties=prop, color='#0f172a')
        cols = ["週一 Mon", "週二 Tue", "週三 Wed", "週四 Thu", "週五 Fri", "週六 Sat", "週日 Sun"]
        cal = calendar.monthcalendar(year, month); table_data = [cols]
        for week in cal:
            row_data = []
            for day in week:
                if day == 0: row_data.append("")
                else:
                    date_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == date_str]
                    is_closed = any((r['Staff'] == "全店" and r['Type'] == "公休") for _, r in day_shifts.iterrows())
                    cell_text = f"{day}\n"
                    if is_closed: cell_text += "\n[全店公休]"
                    else:
                        for _, r in day_shifts.iterrows(): cell_text += f"{r['Staff']} ({r['Type'][0]})\n"
                    row_data.append(cell_text.strip())
            table_data.append(row_data)
        table = ax.table(cellText=table_data, loc='center', cellLoc='center', bbox=[0, 0, 1, 0.9])
        table.auto_set_font_size(False); table.set_fontsize(14)
        for (i, j), cell in table.get_celld().items():
            cell.set_edgecolor('#cbd5e1')
            if i == 0: cell.set_facecolor('#e2e8f0'); cell.set_text_props(fontproperties=prop, color='#0f172a')
            else: cell.set_height(0.16); cell.set_facecolor('#ffffff'); cell.set_text_props(fontproperties=prop, color='#334155')
        buf = io.BytesIO(); plt.savefig(buf, format='png', dpi=200, bbox_inches='tight'); buf.seek(0); plt.close(fig); return buf
    except Exception as e: return str(e)

def render_roster_system(sh, users_list, user_name):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    shifts_df = get_data_safe(ws_shifts)
    if not shifts_df.empty:
        if 'Shift_Type' in shifts_df.columns: shifts_df['Type'] = shifts_df['Shift_Type']
    else: shifts_df = pd.DataFrame(columns=["Date", "Staff", "Type", "Note"])
    
    staff_color_map = get_staff_color_map(users_list)
    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班中心</h3></div>", unsafe_allow_html=True)
    now = datetime.utcnow() + timedelta(hours=8)
    c_y, c_m, c_v = st.columns([1, 1, 1])
    sel_year = c_y.number_input("年份", 2024, 2030, now.year); sel_month = c_m.number_input("月份", 1, 12, now.month); view_mode = c_v.radio("檢視", ["月曆", "列表"], horizontal=True)

    if view_mode == "月曆":
        cal = calendar.monthcalendar(sel_year, sel_month)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    d_shifts = shifts_df[shifts_df['Date'] == d_str]
                    html = ""
                    for _, r in d_shifts.iterrows():
                        clr = "#EF4444" if r['Type'] == "公休" else staff_color_map.get(r['Staff'], "#6B7280")
                        html += f"<div class='desktop-shift-pill' style='background-color:{clr};'>{r['Staff']}-{r['Type'][0]}</div>"
                    with cols[i]:
                        if st.button(f"{day}", key=f"d_{d_str}"): st.session_state['roster_date'] = d_str; st.rerun()
                        st.markdown(f"<div class='day-cell'>{html}</div>", unsafe_allow_html=True)
    
    st.divider()
    if 'roster_date' in st.session_state:
        t_date = st.session_state['roster_date']
        with st.form("edit_roster"):
            st.write(f"編輯 {t_date}")
            s_staff = st.selectbox("人員", users_list); s_type = st.selectbox("班別", list(SHIFT_COLORS.keys()))
            if st.form_submit_button("儲存"):
                retry_action(ws_shifts.append_row, [t_date, s_staff, s_type, "", "FALSE", user_name])
                st.cache_data.clear(); st.success("OK"); st.rerun()

    if st.button("📸 生成班表截圖"):
        img = generate_roster_image_buffer(sel_year, sel_month, shifts_df, 31, staff_color_map)
        if isinstance(img, io.BytesIO): st.image(img); st.download_button("下載 PNG", img, file_name="Roster.png")

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    if 'exchange_rate' not in st.session_state:
        r, _ = get_live_rate(); st.session_state['exchange_rate'] = r
    
    sh = init_db(); ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    if not st.session_state['logged_in']:
        with st.form("login"):
            u = st.text_input("ID"); p = st.text_input("PW", type="password")
            if st.form_submit_button("LOGIN"):
                users = get_data_safe(ws_users)
                if users.empty and u == "Boss" and p == "1234":
                    ws_users.append_row(["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()]); st.rerun()
                tgt = users[users['Name'] == u]
                if not tgt.empty and check_hash(p, tgt.iloc[0]['Password']):
                    st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=tgt.iloc[0]['Role']; st.rerun()
        return

    render_navbar(st.session_state['user_name'][0].upper())
    df = get_data_safe(ws_items, SHEET_HEADERS)
    for num in ['Qty', 'Price', 'Cost', 'Safety_Stock', 'Orig_Cost', 'Qty_CN']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    
    logs_df = get_data_safe(ws_logs); cost_map = {r['SKU']: r['Cost'] for _, r in df.iterrows()}
    product_map = {r['SKU']: f"{r['Name']} ({r['Size']})" for _, r in df.iterrows()}

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("總庫存", f"{df['Qty'].sum() + df['Qty_CN'].sum():,}")
    m2.metric("預估營收", f"${(df['Qty'] * df['Price']).sum():,}")
    m3.metric("內部消耗", f"${calculate_sunk_cost(logs_df, cost_map):,}")
    m4.metric("實際入帳", f"${calculate_realized_revenue(logs_df):,}")

    tabs = st.tabs(["📊 視覺庫存", "🛒 POS", "📈 戰情室", "🎁 領用稽核", "👔 矩陣管理", "📝 日誌", "👥 Admin", "🗓️ 排班"])

    with tabs[0]:
        t1, t2 = st.tabs(["📦 庫存巡報區", "💰 成本與毛利總覽矩陣 (Precision Edit)"])
        with t1:
            q = st.text_input("🔍 搜尋商品"); gallery = df.copy()
            if q: gallery = gallery[gallery.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
            for _, r in gallery.head(20).iterrows():
                with st.container(border=True):
                    c_i, c_f = st.columns([1, 3])
                    c_i.image(render_image_url(r['Image_URL']), width=100)
                    c_f.markdown(f"**{r['Name']} ({r['Size']})** \nSKU: {r['SKU']} | 售價: ${r['Price']} | 庫存: {r['Qty']}")

        with t2:
            st.markdown("#### 🛠️ 財務數據精準修正區")
            st.info("此處為 V122.0 新增：直接選取特定貨號修正幣別與成本，系統將自動重算全域數據。")
            sku_list = df['SKU'].tolist()
            target_sku = st.selectbox("🎯 選擇要修正的貨號", ["請選擇..."] + sku_list)
            if target_sku != "請選擇...":
                row = df[df['SKU'] == target_sku].iloc[0]
                with st.form("precision_fix"):
                    c1, c2, c3 = st.columns(3)
                    new_curr = c1.selectbox("修正原幣別", ["TWD", "CNY"], index=0 if row['Orig_Currency'] == "TWD" else 1)
                    new_orig_cost = c2.number_input("修正原幣成本", value=int(row['Orig_Cost']))
                    new_price = c3.number_input("修正終端定價", value=int(row['Price']))
                    if st.form_submit_button("✅ 執行量子級聯動同步"):
                        new_cost = int(new_orig_cost * st.session_state['exchange_rate']) if new_curr == "CNY" else int(new_orig_cost)
                        cell = ws_items.find(target_sku)
                        if cell:
                            retry_action(ws_items.update_cell, cell.row, 6, new_price)
                            retry_action(ws_items.update_cell, cell.row, 7, new_cost)
                            retry_action(ws_items.update_cell, cell.row, 8, get_taiwan_time_str())
                            retry_action(ws_items.update_cell, cell.row, 11, new_curr)
                            retry_action(ws_items.update_cell, cell.row, 12, new_orig_cost)
                            st.cache_data.clear(); st.success("數據已精準同步！"); time.sleep(1); st.rerun()
            st.divider()
            st.dataframe(df[['SKU', 'Name', 'Orig_Currency', 'Orig_Cost', 'Cost', 'Price', 'Qty']], use_container_width=True, hide_index=True)

    with tabs[1]: # POS
        c_l, c_r = st.columns([3, 2])
        with c_l:
            bc = st.text_input("🎯 條碼掃描")
            if bc:
                match = df[df['SKU'] == bc.strip()]
                if not match.empty:
                    st.session_state['pos_cart'].append({"sku":bc,"name":match.iloc[0]['Name'],"price":match.iloc[0]['Price'],"qty":1})
                    st.success("已加入")
        with c_r:
            st.write("🛒 購物車")
            total = sum(i['price'] for i in st.session_state['pos_cart'])
            st.write(f"總計: ${total}")
            if st.button("結帳"):
                for i in st.session_state['pos_cart']:
                    cell = ws_items.find(i['sku'])
                    if cell: ws_items.update_cell(cell.row, 5, int(ws_items.cell(cell.row, 5).value)-1)
                log_event(ws_logs, st.session_state['user_name'], "Sale", f"Total:${total}")
                st.session_state['pos_cart'] = []; st.cache_data.clear(); st.success("完成"); st.rerun()

    with tabs[7]: render_roster_system(sh, ws_users.col_values(1)[1:], st.session_state['user_name'])

if __name__ == "__main__": main()
