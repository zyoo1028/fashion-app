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
import calendar

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK V103.9 FINAL", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 V103.0 原始視覺 (您最習慣的樣子)
# ==========================================
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF !important; }
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; border-right: 1px solid #E5E7EB; }
        h1, h2, h3, h4, h5, h6, p, span, div, label, li, .stMarkdown { color: #000000 !important; }
        
        input, textarea, .stTextInput > div > div, .stNumberInput > div > div {
            color: #000000 !important; background-color: #F3F4F6 !important; border-color: #D1D5DB !important;
            border-radius: 8px !important;
        }
        div[data-baseweb="select"] > div { background-color: #F3F4F6 !important; color: #000000 !important; border-color: #D1D5DB !important; border-radius: 8px !important; }
        
        .metric-card { 
            background: linear-gradient(145deg, #ffffff, #f5f7fa); 
            border-radius: 16px; padding: 15px; border: 1px solid #e1e4e8; 
            text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.02); 
            margin-bottom: 10px; height: 100%;
        }
        .metric-value { font-size: 1.8rem; font-weight: 800; margin: 5px 0; color:#111 !important; }
        .metric-label { font-size: 0.8rem; letter-spacing: 1px; color:#666 !important; font-weight: 600; text-transform: uppercase;}
        .realized-card { border-bottom: 4px solid #10b981; }
        .profit-card { border-bottom: 4px solid #f59e0b; }

        .inv-card-container {
            border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; margin-bottom: 12px;
            background-color: #ffffff; transition: all 0.2s;
        }
        .inv-card-container:hover { border-color: #94a3b8; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .stock-pill-tw { background-color: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; margin-right: 5px; }
        .stock-pill-cn { background-color: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }

        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border:none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); background-color: #FFFFFF; color: #000000; border: 1px solid #E5E7EB; }
        [data-testid="stDataFrame"] { border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden; }
        
        .cart-box { background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px; margin-bottom: 15px; }
        .cart-item { display: flex; justify-content: space-between; border-bottom: 1px dashed #cbd5e1; padding: 8px 0; font-size: 0.9rem; }
        .cart-total { font-size: 1.2rem; font-weight: 800; color: #0f172a; text-align: right; margin-top: 10px; }
        .final-price-display { font-size: 1.8rem; font-weight: 900; color: #16a34a; text-align: center; background: #dcfce7; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #86efac; }
        
        /* 排班表樣式 */
        .roster-header { background: #f0f9ff; padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #bae6fd; }
        .day-cell { border: 1px solid #eee; border-radius: 8px; padding: 5px; min-height: 80px; position: relative; margin-bottom: 5px; transition: 0.2s; }
        .day-cell:hover { border-color: #3b82f6; cursor: pointer; }
        .shift-tag { font-size: 0.7rem; padding: 2px 4px; border-radius: 4px; margin-bottom: 2px; color: white; display: block; text-align: center; }
        .note-dot { position: absolute; top: 5px; right: 5px; width: 6px; height: 6px; background: red; border-radius: 50%; }
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- 核心連線 (Cache + Retry) ---
@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=15, show_spinner=False)
def get_data_safe(_ws, expected_headers=None):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if _ws is None: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            raw_data = _ws.get_all_values()
            
            if not raw_data or len(raw_data) < 2: 
                return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            
            headers = raw_data[0]
            # 去重
            seen = {}
            new_headers = []
            for h in headers:
                if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
                else: seen[h] = 0; new_headers.append(h)
            
            rows = raw_data[1:]
            
            # 自動修復 Qty_CN
            if expected_headers and "Qty_CN" in expected_headers and "Qty_CN" not in new_headers:
                try: _ws.update_cell(1, len(new_headers)+1, "Qty_CN"); new_headers.append("Qty_CN"); raw_data = _ws.get_all_values(); rows = raw_data[1:]
                except: pass

            df = pd.DataFrame(rows)
            if not df.empty:
                if len(df.columns) < len(new_headers):
                    for _ in range(len(new_headers) - len(df.columns)): df[len(df.columns)] = ""
                df.columns = new_headers[:len(df.columns)]
                
            return df
        except Exception:
            time.sleep(1)
            continue
    return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()

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

# --- 工具模組 ---
def get_taiwan_time_str(): return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
@st.cache_data(ttl=3600)
def get_live_rate():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/CNY"
        response = requests.get(url, timeout=5)
        if response.status_code == 200: return response.json()['rates']['TWD'], True
    except: pass
    return 4.50, False
def make_hash(password): return hashlib.sha256(str(password).encode()).hexdigest()
def check_hash(password, hashed_text): return make_hash(password) == hashed_text
def render_image_url(url_input):
    if not url_input or (isinstance(url_input, float) and math.isnan(url_input)): return "https://i.ibb.co/W31w56W/placeholder.png"
    s = str(url_input).strip()
    return s if len(s) > 10 and s.startswith("http") else "https://i.ibb.co/W31w56W/placeholder.png"
def upload_image_to_imgbb(image_file):
    if not IMGBB_API_KEY: return None
    try:
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(image_file.getvalue()).decode('utf-8')}
        response = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if response.status_code == 200: return response.json()["data"]["url"]
    except: pass; return None
def log_event(ws_logs, user, action, detail):
    try: ws_logs.append_row([get_taiwan_time_str(), user, action, detail])
    except: pass
def get_style_code(sku): return str(sku).strip().rsplit('-', 1)[0] if '-' in str(sku) else str(sku).strip()
SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
def get_size_sort_key(size_str): return SIZE_ORDER.index(size_str) if size_str in SIZE_ORDER else 99
def generate_smart_style_code(category, existing_skus):
    prefix_map = {"上衣(Top)": "TOP", "褲子(Btm)": "BTM", "外套(Out)": "OUT", "套裝(Suit)": "SET", "鞋類(Shoe)": "SHOE", "包款(Bag)": "BAG", "帽子(Hat)": "HAT", "飾品(Acc)": "ACC", "其他(Misc)": "MSC"}
    prefix = f"{prefix_map.get(category, 'GEN')}-{(datetime.utcnow() + timedelta(hours=8)).strftime('%y%m')}"
    max_seq = 0
    for sku in existing_skus:
        if str(sku).startswith(prefix + "-"):
            try: max_seq = max(max_seq, int(sku.replace(prefix + "-", "").split("-")[0]))
            except: pass
    return f"{prefix}-{str(max_seq + 1).zfill(3)}"
def calculate_realized_revenue(logs_df):
    total = 0
    if logs_df.empty or 'Action' not in logs_df.columns: return 0
    sales_logs = logs_df[logs_df['Action'] == 'Sale']
    for _, row in sales_logs.iterrows():
        try: total += int(re.search(r'Total:\$(\d+)', row['Details']).group(1))
        except: pass
    return total

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

# 全域變數
CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]

# ==========================================
# 🗓️ 專業排班系統 (V103.9 Fix: KeyError Solved)
# ==========================================
def get_staff_color(name):
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6366F1", "#14B8A6", "#F97316"]
    return colors[sum(ord(c) for c in str(name)) % len(colors)]

def render_roster_system(sh, users_list):
    # 讀取 Sheet，允許欄位不一致
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    shifts_df = get_data_safe(ws_shifts)
    
    # 🛑 關鍵修復：自動修正欄位名稱，防止 KeyError
    if not shifts_df.empty:
        if 'Shift_Type' in shifts_df.columns and 'Type' not in shifts_df.columns:
            shifts_df = shifts_df.rename(columns={'Shift_Type': 'Type'})
        if 'Type' not in shifts_df.columns:
            shifts_df['Type'] = '上班' # 防呆預設值
    
    st.markdown("<div class='roster-header'><h3>🗓️ 員工排班中心</h3></div>", unsafe_allow_html=True)
    
    now = datetime.utcnow() + timedelta(hours=8)
    c1, c2 = st.columns([1, 1])
    sel_year = c1.number_input("年份", 2024, 2030, now.year)
    sel_month = c2.selectbox("月份", range(1, 13), now.month)
    
    cal = calendar.monthcalendar(sel_year, sel_month)
    cols = st.columns(7)
    for i, d in enumerate(["一", "二", "三", "四", "五", "六", "日"]): 
        cols[i].markdown(f"<div style='text-align:center;font-weight:bold;'>{d}</div>", unsafe_allow_html=True)
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day != 0:
                    date_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = pd.DataFrame()
                    has_note = False
                    
                    if not shifts_df.empty:
                        day_shifts = shifts_df[shifts_df['Date'] == date_str]
                        if 'Note' in day_shifts.columns and not day_shifts[day_shifts['Note'] != ""].empty: has_note = True
                    
                    if st.button(f"{day}", key=f"cal_{date_str}", use_container_width=True):
                        st.session_state['roster_date'] = date_str
                        st.rerun()
                    
                    badges_html = ""
                    if not day_shifts.empty and 'Type' in day_shifts.columns:
                        for _, r in day_shifts.iterrows():
                            s_type = r['Type']
                            color = get_staff_color(r['Staff'])
                            if s_type == "公休": color = "#9CA3AF"
                            elif s_type == "特休": color = "#EF4444"
                            elif s_type == "空班": color = "#F59E0B"
                            badges_html += f"<span class='shift-tag' style='background-color:{color}'>{r['Staff']}</span>"
                    
                    note_html = "<div class='note-dot'></div>" if has_note else ""
                    st.markdown(f"""<div class='day-cell' style='margin-top:-10px; border:none; background:transparent;'>{note_html}{badges_html}</div>""", unsafe_allow_html=True)
                else: st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    c_edit, c_view = st.columns([1, 1.5])
    
    with c_edit:
        if 'roster_date' in st.session_state:
            t_date = st.session_state['roster_date']
            st.markdown(f"#### ✏️ 編輯: {t_date}")
            with st.form("add_shift"):
                s_staff = st.selectbox("人員", users_list)
                s_type = st.selectbox("狀態", ["早班", "晚班", "全班", "公休", "特休", "空班", "代班"])
                s_note = st.text_input("備註")
                s_notify = st.checkbox("🔔 需要通知")
                if st.form_submit_button("➕ 加入"):
                    all_vals = ws_shifts.get_all_values()
                    rows_to_del = []
                    for idx, row in enumerate(all_vals):
                        if len(row) > 1 and row[0] == t_date and row[1] == s_staff: rows_to_del.append(idx + 1)
                    for r_idx in reversed(rows_to_del): ws_shifts.delete_rows(r_idx)
                    ws_shifts.append_row([t_date, s_staff, s_type, s_note, "TRUE" if s_notify else "FALSE", st.session_state['user_name']])
                    st.cache_data.clear(); st.success("已更新"); time.sleep(0.5); st.rerun()
            
            # 刪除區
            if not shifts_df.empty:
                curr_day = shifts_df[shifts_df['Date'] == t_date]
                if not curr_day.empty:
                    st.caption("移除:")
                    for _, r in curr_day.iterrows():
                        if st.button(f"🗑️ {r['Staff']} ({r.get('Type','?')})", key=f"del_{t_date}_{r['Staff']}"):
                            all_vals = ws_shifts.get_all_values()
                            for idx, row in enumerate(all_vals):
                                if len(row) > 1 and row[0] == t_date and row[1] == r['Staff']: ws_shifts.delete_rows(idx + 1); break
                            st.cache_data.clear(); st.rerun()
        else: st.info("👈 請點選上方日期")

    with c_view:
        st.markdown(f"#### 📅 {sel_month}月 總覽")
        if not shifts_df.empty:
            m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
            m_data = shifts_df[shifts_df['Date'].str.startswith(m_prefix)].copy()
            if not m_data.empty:
                m_data = m_data.sort_values(['Date', 'Staff'])
                # 再次確保欄位顯示正確
                if 'Type' in m_data.columns:
                    m_data = m_data.rename(columns={'Type': '班別'})
                
                # 安全顯示，只選存在的欄位
                cols_to_show = [c for c in ['Date', 'Staff', '班別', 'Note', 'Notify'] if c in m_data.columns]
                st.dataframe(m_data[cols_to_show], use_container_width=True, hide_index=True, height=300)
                
                st.markdown("---")
                st.markdown("#### 📢 複製通知")
                tmr = (datetime.utcnow() + timedelta(hours=8) + timedelta(days=1)).strftime("%Y-%m-%d")
                if 'Notify' in shifts_df.columns:
                    tmr_shifts = shifts_df[(shifts_df['Date'] == tmr) & (shifts_df['Notify'] == "TRUE")]
                    if not tmr_shifts.empty:
                        msg = f"【明日上班提醒 {tmr}】\n"
                        for _, r in tmr_shifts.iterrows():
                            s_type = r.get('Type', '上班')
                            msg += f"- {r['Staff']} ({s_type}) {r.get('Note','')}\n"
                        msg += "請準時打卡！"
                        st.text_area("內容:", value=msg, height=100)
                    else: st.info("明日無需提醒")
            else: st.info("本月無資料")
        else: st.info("尚無資料")

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False; st.session_state['user_name'] = ""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    if 'exchange_rate' not in st.session_state:
        l_rate, succ = get_live_rate()
        st.session_state['exchange_rate'] = l_rate
        st.session_state['rate_source'] = "Live API" if succ else "Manual"

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
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>OMEGA V103.9 FINAL</div>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("ID"); p = st.text_input("Password", type="password")
                if st.form_submit_button("LOGIN", type="primary"):
                    with st.spinner("Logging in..."):
                        users_df = get_data_safe(ws_users, ["Name", "Password", "Role", "Status", "Created_At"])
                        u = u.strip(); p = p.strip()
                        if users_df.empty and u == "Boss" and p == "1234":
                            ws_users.append_row(["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                            st.cache_data.clear(); st.success("Boss Created"); time.sleep(1); st.rerun()
                        
                        if not users_df.empty and 'Name' in users_df.columns:
                            tgt = users_df[(users_df['Name'] == u) & (users_df['Status'] == 'Active')]
                            if not tgt.empty:
                                stored = tgt.iloc[0]['Password']
                                if (len(stored)==64 and check_hash(p, stored)) or (p == stored):
                                    st.session_state['logged_in'] = True; st.session_state['user_name'] = u; st.session_state['user_role'] = tgt.iloc[0]['Role']; log_event(ws_logs, u, "Login", "Success"); st.rerun()
                                else: st.error("Wrong Password")
                            else: st.error("User Not Found")
                        else: st.error("System Busy (Try again in 30s)")
        return

    # --- 主畫面 ---
    user_initial = st.session_state['user_name'][0].upper()
    render_navbar(user_initial)

    # 讀取資料
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
    
    # 側邊欄
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_label = "🔴 Admin" if st.session_state['user_role'] == 'Admin' else "🟢 Staff"
        st.caption(f"Role: {role_label}")
        st.markdown("---")
        with st.expander("💱 匯率監控", expanded=True):
            curr_rate = st.session_state['exchange_rate']
            new_r = st.number_input("RMB to TWD", value=curr_rate, step=0.01)
            if new_r != curr_rate: st.session_state['exchange_rate'] = new_r
            if st.button("🔄 更新匯率"): 
                l_rate, succ = get_live_rate()
                st.session_state['exchange_rate'] = l_rate; st.rerun()
        st.markdown("---")
        if st.button("🚪 登出"): st.session_state['logged_in'] = False; st.rerun()

    # Dashboard
    total_qty_tw = df['Qty'].sum(); total_qty_cn = df['Qty_CN'].sum(); total_qty = total_qty_tw + total_qty_cn
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
    tabs = st.tabs(["📊 視覺庫存", "🛒 POS", "📈 銷售戰情", "🎁 領用/稽核", "👔 矩陣管理", "📝 日誌", "👥 Admin", "🗓️ 排班"])

    with tabs[0]:
        if not df.empty:
            c1, c2 = st.columns([1, 1])
            with c1:
                fig_pie = px.pie(df, names='Category', values='Qty', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
            with c2:
                top = df.groupby(['Style_Code', 'Name']).agg({'Qty':'sum'}).reset_index().sort_values(by='Qty', ascending=False).head(10)
                fig_bar = px.bar(top, x='Qty', y='Name', orientation='h', text='Qty', color='Qty', color_continuous_scale='Bluered')
                st.plotly_chart(fig_bar, use_container_width=True)
        
        st.divider()
        st.subheader("📦 庫存區")
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1: search_q = st.text_input("🔍 搜尋商品", placeholder="輸入貨號...")
        with col_s2: filter_cat = st.selectbox("📂 分類篩選", ["全部"] + CAT_LIST)
        gallery_df = df.copy()
        if search_q: gallery_df = gallery_df[gallery_df.apply(lambda x: search_q.lower() in str(x.values).lower(), axis=1)]
        if filter_cat != "全部": gallery_df = gallery_df[gallery_df['Category'] == filter_cat]
        
        if not gallery_df.empty:
            grouped = gallery_df.groupby(['Style_Code', 'Name'])
            for (style_code, name), group in grouped:
                first_row = group.iloc[0]; img = render_image_url(first_row['Image_URL']); price = int(first_row['Price'])
                total_qty_tw = group['Qty'].sum(); total_qty_cn = group['Qty_CN'].sum()
                group['size_sort'] = group['Size'].apply(get_size_sort_key); sorted_group = group.sort_values('size_sort')
                with st.container(border=True):
                    c_img, c_info = st.columns([1, 4])
                    with c_img: st.image(img, use_column_width=True)
                    with c_info:
                        st.markdown(f"#### {name}"); st.caption(f"貨號: {style_code}"); st.markdown(f"🇹🇼 TW: **{total_qty_tw}** | 🇨🇳 CN: **{total_qty_cn}** | ${price}")
                        tags = ""
                        for _, r in sorted_group.iterrows():
                            if r['Qty']>0: tags += f"<span class='stock-pill-tw'>{r['Size']}:{r['Qty']}</span> "
                            if r['Qty_CN']>0: tags += f"<span class='stock-pill-cn'>{r['Size']}(CN):{r['Qty_CN']}</span> "
                        if tags: st.markdown(tags, unsafe_allow_html=True)
                    with st.expander("📝 管理庫存"):
                        with st.form(f"form_{style_code}_{name}"):
                            i_tw = {}; i_cn = {}; g_cols = st.columns(4)
                            for idx, r_data in enumerate(sorted_group.iterrows()):
                                _, row = r_data
                                with g_cols[idx%4]: 
                                    lbl = row['Size']; i_tw[row['SKU']] = st.number_input(f"TW {lbl}", value=int(row['Qty']), key=f"t_{row['SKU']}"); i_cn[row['SKU']] = st.number_input(f"CN {lbl}", value=int(row['Qty_CN']), key=f"c_{row['SKU']}")
                            if st.form_submit_button("💾 更新"):
                                for tsku, n_tw in i_tw.items():
                                    if tsku in df['SKU'].tolist():
                                        n_cn = i_cn[tsku]; r = ws_items.find(tsku).row
                                        update_cell_retry(ws_items, r, 5, n_tw); update_cell_retry(ws_items, r, 13, n_cn); update_cell_retry(ws_items, r, 8, get_taiwan_time_str())
                                st.cache_data.clear(); st.success("Updated"); time.sleep(1); st.rerun()
        else: st.info("無資料")

    with tabs[1]:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("1. 商品選擇")
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} ({x['Size']}) | T:{x['Qty']}", axis=1).tolist() if not df.empty else []
            sel = st.selectbox("搜尋", ["..."] + opts)
            if sel != "...":
                tsku = sel.split(" | ")[0]; tgt = df[df['SKU'] == tsku].iloc[0]; st.image(render_image_url(tgt['Image_URL']), width=150)
                st.markdown(f"**{tgt['Name']}** | ${tgt['Price']}"); aq = st.number_input("數量", 1, value=1)
                if st.button("➕ 加入", type="primary"):
                    st.session_state['pos_cart'].append({"sku": tsku, "name": tgt['Name'], "size": tgt['Size'], "price": int(tgt['Price']), "qty": aq, "subtotal": int(tgt['Price'])*aq})
                    st.success("Added"); time.sleep(0.5); st.rerun()
        with c2:
            st.subheader("2. 結帳")
            if st.session_state['pos_cart']:
                tot = sum(i['subtotal'] for i in st.session_state['pos_cart'])
                st.markdown("<div class='cart-box'>", unsafe_allow_html=True)
                for i in st.session_state['pos_cart']: st.markdown(f"<div class='cart-item'><span>{i['name']} ({i['size']}) x{i['qty']}</span><span>${i['subtotal']}</span></div>", unsafe_allow_html=True)
                if st.button("🗑️ 清空"): st.session_state['pos_cart']=[]; st.rerun()
                st.markdown(f"<div class='cart-total'>${tot}</div></div>", unsafe_allow_html=True)
                
                c_d1, c_d2 = st.columns(2); disc = c_d1.radio("折扣", ["無", "7折", "8折", "自訂"], horizontal=True); cust = c_d2.number_input("折數", 1, 100, 95)
                bun = st.checkbox("組合價"); b_val = st.number_input("組合總額", value=tot) if bun else tot
                
                fin = b_val
                if disc=="7折": fin=int(round(b_val*0.7))
                elif disc=="8折": fin=int(round(b_val*0.8))
                elif disc=="自訂": fin=int(round(b_val*(cust/100)))
                
                st.markdown(f"<div class='final-price-display'>實收: ${fin}</div>", unsafe_allow_html=True)
                who = st.selectbox("人員", staff_list); pay = st.selectbox("付款", ["現金", "刷卡"]); note = st.text_input("備註")
                if st.button("✅ 結帳", type="primary"):
                    items = []; valid = True
                    for i in st.session_state['pos_cart']:
                        r = ws_items.find(i['sku']).row; cur = int(ws_items.cell(r, 5).value)
                        if cur >= i['qty']: update_cell_retry(ws_items, r, 5, cur-i['qty']); items.append(f"{i['sku']} x{i['qty']}")
                        else: valid = False; st.error("庫存不足"); break
                    if valid:
                        log_event(ws_logs, st.session_state['user_name'], "Sale", f"Total:${fin} | {','.join(items)} | {note} | {pay} | {who}")
                        st.session_state['pos_cart']=[]; st.cache_data.clear(); st.success("OK"); time.sleep(1); st.rerun()
            else: st.info("空")

    with tabs[2]:
        sales_data = []
        if not logs_df.empty and 'Action' in logs_df.columns:
            s_logs = logs_df[logs_df['Action'] == 'Sale']
            for _, row in s_logs.iterrows():
                try:
                    val = int(re.search(r'Total:\$(\d+)', row['Details']).group(1))
                    sales_data.append({"日期": row['Timestamp'], "金額": val, "經手": row['User']})
                except: pass
        if sales_data: st.dataframe(pd.DataFrame(sales_data), use_container_width=True)
        else: st.info("無數據")

    with tabs[3]:
        st.subheader("內部領用")
        with st.expander("新增", expanded=True):
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist() if not df.empty else []
            sel = st.selectbox("商品", ["..."] + opts)
            if sel != "...":
                tsku = sel.split(" | ")[0]; tr = df[df['SKU'] == tsku].iloc[0]; st.info(f"庫存: {tr['Qty']}")
                with st.form("internal"):
                    q = st.number_input("數量", 1); who = st.selectbox("人", staff_list); rsn = st.selectbox("因", ["公務", "報廢"]); n = st.text_input("備註")
                    if st.form_submit_button("執行"):
                        r = ws_items.find(tsku).row; update_cell_retry(ws_items, r, 5, int(tr['Qty'])-q)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{tsku} -{q} | {who} | {rsn} | {n}")
                        st.cache_data.clear(); st.success("OK"); st.rerun()
        if not logs_df.empty and 'Action' in logs_df.columns:
            st.dataframe(logs_df[logs_df['Action']=="Internal_Use"], use_container_width=True)

    with tabs[4]:
        st.subheader("矩陣管理")
        mt1, mt2, mt3 = st.tabs(["新增", "調撥", "刪除"])
        with mt1:
            mode = st.radio("模式", ["新系列", "衍生"], horizontal=True)
            auto_sku, auto_name = "", ""
            if mode == "新系列":
                c = st.selectbox("分類", CAT_LIST)
                if st.button("生成"): st.session_state['base'] = generate_smart_style_code(c, df['SKU'].tolist())
                if 'base' in st.session_state: auto_sku = st.session_state['base']
            else:
                p = st.selectbox("母商品", ["..."] + df['SKU'].tolist())
                if p != "...": pr = df[df['SKU']==p].iloc[0]; auto_sku = get_style_code(p)+"-NEW"; auto_name = pr['Name']
            with st.form("add_m"):
                c1, c2 = st.columns(2); bs = c1.text_input("Base SKU", value=auto_sku); nm = c2.text_input("品名", value=auto_name)
                c3, c4 = st.columns(2); pr = c3.number_input("售價", 0); co = c4.number_input("原幣成本", 0)
                cur = st.selectbox("幣別", ["TWD", "CNY"]); img = st.file_uploader("圖")
                sz = {}; cols = st.columns(5)
                for i, s in enumerate(SIZE_ORDER): sz[s] = cols[i%5].number_input(s, min_value=0)
                if st.form_submit_button("寫入"):
                    url = upload_image_to_imgbb(img) if img else ""
                    fc = int(co * st.session_state['exchange_rate']) if cur == "CNY" else co
                    for s, q in sz.items():
                        if q > 0: ws_items.append_row([f"{bs}-{s}", nm, "New", s, q, pr, fc, get_taiwan_time_str(), url, 5, cur, co, 0])
                    st.cache_data.clear(); st.success("完成"); st.rerun()
        with mt2:
            sel = st.selectbox("調撥", ["..."] + df['SKU'].tolist())
            if sel != "...":
                r = df[df['SKU']==sel].iloc[0]; st.write(f"TW: {r['Qty']} | CN: {r['Qty_CN']}"); q = st.number_input("量", 1)
                c1, c2 = st.columns(2)
                if c1.button("TW->CN"): 
                    rw = ws_items.find(sel).row; update_cell_retry(ws_items, rw, 5, int(r['Qty'])-q); update_cell_retry(ws_items, rw, 13, int(r['Qty_CN'])+q); st.cache_data.clear(); st.success("OK"); st.rerun()
                if c2.button("CN->TW"):
                    rw = ws_items.find(sel).row; update_cell_retry(ws_items, rw, 5, int(r['Qty'])+q); update_cell_retry(ws_items, rw, 13, int(r['Qty_CN'])-q); st.cache_data.clear(); st.success("OK"); st.rerun()
        with mt3:
            d = st.selectbox("刪除", ["..."] + df['SKU'].tolist())
            if d != "..." and st.button("確認刪除"): ws_items.delete_rows(ws_items.find(d).row); st.cache_data.clear(); st.success("OK"); st.rerun()

    with tabs[5]: st.dataframe(logs_df, use_container_width=True)
    with tabs[6]: st.dataframe(users_df, use_container_width=True)
    
    # --- Tab 8: 專業排班 (修復版) ---
    with tabs[7]:
        render_roster_system(sh, staff_list)

if __name__ == "__main__":
    main()
