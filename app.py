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
import random
import calendar

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK ERP V104.0 PLATINUM", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【CSS 視覺核心：V103.10 風格 + V104 優化】
# ==========================================
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF !important; }
        
        /* POS 卡片樣式 (V103.10) */
        .pos-card {
            border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;
            background: #fff; display: flex; flex-direction: column; 
            height: 100%; transition: transform 0.1s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .pos-card:active { transform: scale(0.98); border-color: #3b82f6; }
        .pos-img { width: 100%; height: 140px; object-fit: cover; background: #f9fafb; }
        .pos-content { padding: 10px; flex-grow: 1; }
        .pos-title { font-weight: bold; font-size: 0.95rem; margin-bottom: 4px; color: #1f2937; line-height: 1.3; }
        .pos-meta { font-size: 0.75rem; color: #6b7280; margin-bottom: 8px; }
        .pos-price { font-weight: 900; color: #059669; font-size: 1.1rem; }
        .pos-stock { font-size: 0.7rem; background: #eff6ff; color: #1d4ed8; padding: 2px 6px; border-radius: 4px; float: right; margin-top: 4px; }

        /* 排班表樣式 */
        .roster-header { background: #f0f9ff; padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #bae6fd; }
        .day-cell { border: 1px solid #eee; border-radius: 8px; padding: 5px; min-height: 80px; position: relative; margin-bottom: 5px; transition: 0.2s; background: #fff; }
        .day-cell:hover { border-color: #3b82f6; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .shift-tag { font-size: 0.7rem; padding: 2px 4px; border-radius: 4px; margin-bottom: 2px; color: white; display: block; text-align: center; font-weight: bold; }
        .note-dot { position: absolute; top: 5px; right: 5px; width: 8px; height: 8px; background: #ef4444; border-radius: 50%; }

        /* 通用樣式 */
        .metric-card { background: linear-gradient(145deg, #ffffff, #f5f7fa); border-radius: 16px; padding: 15px; border: 1px solid #e1e4e8; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.02); margin-bottom: 10px; height: 100%; }
        .metric-value { font-size: 1.8rem; font-weight: 800; margin: 5px 0; color:#111 !important; }
        .metric-label { font-size: 0.8rem; letter-spacing: 1px; color:#666 !important; font-weight: 600; text-transform: uppercase;}
        
        .cart-box { background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px; margin-bottom: 15px; }
        .cart-item { display: flex; justify-content: space-between; border-bottom: 1px dashed #cbd5e1; padding: 8px 0; font-size: 0.9rem; }
        .cart-total { font-size: 1.2rem; font-weight: 800; color: #0f172a; text-align: right; margin-top: 10px; }
        .final-price-display { font-size: 1.8rem; font-weight: 900; color: #16a34a; text-align: center; background: #dcfce7; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #86efac; }
        
        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border:none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); background-color: #FFFFFF; color: #000000; border: 1px solid #E5E7EB; width: 100%; }
        input, .stTextInput>div>div, div[data-baseweb="select"]>div { border-radius: 8px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- OMEGA 核心防護層 (Anti-Crash Logic) ---
def retry_action(func, *args, **kwargs):
    max_retries = 5
    for i in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Quota exceeded" in str(e):
                wait_time = (2 ** i) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue
            else:
                raise e
    return None

@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=5, show_spinner=False)
def get_data_safe(_ws, expected_headers=None):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if _ws is None: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            raw_data = _ws.get_all_values()
            if not raw_data or len(raw_data) < 2: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            
            headers = raw_data[0]
            seen = {}
            new_headers = []
            for h in headers:
                if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
                else: seen[h] = 0; new_headers.append(h)
            
            rows = raw_data[1:]
            
            # Auto-Fix Qty_CN
            if expected_headers and "Qty_CN" in expected_headers and "Qty_CN" not in new_headers:
                try: retry_action(_ws.update_cell, 1, len(new_headers)+1, "Qty_CN"); new_headers.append("Qty_CN"); raw_data = _ws.get_all_values(); rows = raw_data[1:]
                except: pass

            df = pd.DataFrame(rows)
            if not df.empty:
                if len(df.columns) < len(new_headers):
                    for _ in range(len(new_headers) - len(df.columns)): df[len(df.columns)] = ""
                df.columns = new_headers[:len(df.columns)]
            return df
        except Exception as e:
            if "429" in str(e): time.sleep(2 ** (attempt + 1)); continue
            return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
    return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()

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
    try: retry_action(ws_logs.append_row, [get_taiwan_time_str(), user, action, detail])
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
        try: 
            match = re.search(r'Total:\$(\d+)', row['Details'])
            if match: total += int(match.group(1))
        except: pass
    return total

def render_navbar(user_initial):
    current_date = datetime.utcnow() + timedelta(hours=8)
    date_str = current_date.strftime("%Y/%m/%d")
    rate = st.session_state.get('exchange_rate', 4.5)
    st.markdown(f"""
        <div class="navbar-container">
            <div style="display:flex; justify-content:space-between; align-items:center; background:#fff; padding:15px; border-bottom:1px solid #eee; margin-bottom:15px;">
                <div>
                    <span style="font-size:18px; font-weight:900; color:#111;">IFUKUK GLOBAL</span><br>
                    <span style="font-size:11px; color:#666; font-family:monospace;">{date_str} • Rate: {rate}</span>
                </div>
                <div style="width:36px; height:36px; background:#111; color:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold;">
                    {user_initial}
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]

# ==========================================
# 🗓️ 排班系統 (V103.10)
# ==========================================
def get_staff_color(name):
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6366F1", "#14B8A6", "#F97316"]
    return colors[sum(ord(c) for c in str(name)) % len(colors)]

def render_roster_system(sh, users_list, user_name):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    shifts_df = get_data_safe(ws_shifts, ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    
    if not shifts_df.empty:
        if 'Shift_Type' in shifts_df.columns and 'Type' not in shifts_df.columns: shifts_df['Type'] = shifts_df['Shift_Type']
        if 'Type' not in shifts_df.columns: shifts_df['Type'] = '上班'
    
    st.markdown("<div class='roster-header'><h3>🗓️ 員工排班中心</h3></div>", unsafe_allow_html=True)
    
    now = datetime.utcnow() + timedelta(hours=8)
    c1, c2 = st.columns([1, 1])
    sel_year = c1.number_input("年份", 2024, 2030, now.year)
    sel_month = c2.selectbox("月份", range(1, 13), now.month)
    
    cal = calendar.monthcalendar(sel_year, sel_month)
    cols = st.columns(7)
    for i, d in enumerate(["一", "二", "三", "四", "五", "六", "日"]): cols[i].markdown(f"<div style='text-align:center;font-weight:bold;'>{d}</div>", unsafe_allow_html=True)
    
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
                            s_type = r['Type']; color = get_staff_color(r['Staff'])
                            if s_type == "公休": color = "#9CA3AF"
                            elif s_type == "特休": color = "#EF4444"
                            elif s_type == "空班": color = "#F59E0B"
                            badges_html += f"<span class='shift-tag' style='background-color:{color}'>{r['Staff']}</span>"
                    
                    note_html = "<div class='note-dot'></div>" if has_note else ""
                    st.markdown(f"<div class='day-cell' style='margin-top:-10px; border:none; background:transparent;'>{note_html}{badges_html}</div>", unsafe_allow_html=True)
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
                s_notify = st.checkbox("🔔 通知")
                if st.form_submit_button("➕ 加入"):
                    all_vals = ws_shifts.get_all_values()
                    rows_to_del = []
                    for idx, row in enumerate(all_vals):
                        if len(row) > 1 and row[0] == t_date and row[1] == s_staff: rows_to_del.append(idx + 1)
                    for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                    retry_action(ws_shifts.append_row, [t_date, s_staff, s_type, s_note, "TRUE" if s_notify else "FALSE", user_name])
                    st.cache_data.clear(); st.success("已更新"); time.sleep(0.5); st.rerun()
            
            if not shifts_df.empty:
                curr_day = shifts_df[shifts_df['Date'] == t_date]
                if not curr_day.empty:
                    st.caption("移除:")
                    for _, r in curr_day.iterrows():
                        if st.button(f"🗑️ {r['Staff']} ({r.get('Type','?')})", key=f"del_{t_date}_{r['Staff']}"):
                            all_vals = ws_shifts.get_all_values()
                            for idx, row in enumerate(all_vals):
                                if len(row) > 1 and row[0] == t_date and row[1] == r['Staff']: retry_action(ws_shifts.delete_rows, idx + 1); break
                            st.cache_data.clear(); st.rerun()
        else: st.info("👈 請點選上方日期")

    with c_view:
        st.markdown(f"#### 📅 {sel_month}月 總覽")
        if not shifts_df.empty:
            m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
            m_data = shifts_df[shifts_df['Date'].str.startswith(m_prefix)].copy()
            if not m_data.empty:
                m_data = m_data.sort_values(['Date', 'Staff'])
                if 'Type' in m_data.columns: m_data = m_data.rename(columns={'Type': '班別'})
                cols_to_show = [c for c in ['Date', 'Staff', '班別', 'Note', 'Notify'] if c in m_data.columns]
                st.dataframe(m_data[cols_to_show], use_container_width=True, hide_index=True, height=300)
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

    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-weight:900; font-size:2.5rem; margin-bottom:10px;'>IFUKUK</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>OMEGA V104.0 PLATINUM</div>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("ID"); p = st.text_input("Password", type="password")
                if st.form_submit_button("LOGIN", type="primary"):
                    with st.spinner("Secure Login..."):
                        users_df = get_data_safe(ws_users, ["Name", "Password", "Role", "Status", "Created_At"])
                        u = u.strip(); p = p.strip()
                        if users_df.empty and u == "Boss" and p == "1234":
                            retry_action(ws_users.append_row, ["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                            st.cache_data.clear(); st.success("Boss Created"); time.sleep(1); st.rerun()
                        
                        if not users_df.empty and 'Name' in users_df.columns:
                            tgt = users_df[(users_df['Name'] == u) & (users_df['Status'] == 'Active')]
                            if not tgt.empty:
                                stored = tgt.iloc[0]['Password']
                                if (len(stored)==64 and check_hash(p, stored)) or (p == stored):
                                    st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=tgt.iloc[0]['Role']; log_event(ws_logs, u, "Login", "Success"); st.rerun()
                                else: st.error("Wrong Password")
                            else: st.error("User Not Found")
                        else: st.warning("⚠️ 連線忙碌，請重試")
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
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        st.caption(f"Role: {st.session_state['user_role']}")
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
    tabs = st.tabs(["📊 視覺庫存", "🛒 POS (V104)", "📈 銷售戰情", "🎁 領用/稽核", "👔 矩陣管理", "📝 日誌", "👥 Admin", "🗓️ 排班"])

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
        st.divider(); st.subheader("📦 庫存區")
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
                                        retry_action(ws_items.update_cell, r, 5, n_tw)
                                        retry_action(ws_items.update_cell, r, 13, n_cn)
                                        retry_action(ws_items.update_cell, r, 8, get_taiwan_time_str())
                                st.cache_data.clear(); st.success("Updated"); time.sleep(1); st.rerun()
        else: st.info("無資料")

    with tabs[1]:
        c_l, c_r = st.columns([3, 2])
        with c_l:
            st.markdown("##### 🛍️ 商品畫廊 (點擊加入)")
            cats_available = list(df['Category'].unique()) if not df.empty else []
            all_cats = sorted(list(set(CAT_LIST + cats_available)))
            col_s1, col_s2 = st.columns([2,1])
            q = col_s1.text_input("POS搜尋", placeholder="關鍵字...", label_visibility="collapsed")
            cat = col_s2.selectbox("POS分類", ["全部"] + all_cats, label_visibility="collapsed")
            
            vdf = df.copy()
            if cat != "全部": vdf = vdf[vdf['Category'] == cat]
            if q: vdf = vdf[vdf.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
            
            if not vdf.empty:
                vdf = vdf.head(40)
                rows = [vdf.iloc[i:i+3] for i in range(0, len(vdf), 3)]
                for r in rows:
                    cols = st.columns(3)
                    for i, (_, item) in enumerate(r.iterrows()):
                        with cols[i]:
                            st.markdown(f"<div class='pos-card'><div class='pos-img'><img src='{render_image_url(item['Image_URL'])}' style='width:100%;height:100%;object-fit:cover;'></div><div class='pos-content'><div class='pos-title'>{item['Name']}</div><div class='pos-price'>${item['Price']}</div><div class='pos-stock'>TW:{item['Qty']}</div></div></div>", unsafe_allow_html=True)
                            if st.button("➕", key=f"add_{item['SKU']}", use_container_width=True):
                                st.session_state['pos_cart'].append({"sku":item['SKU'],"name":item['Name'],"size":item['Size'],"price":item['Price'],"qty":1,"subtotal":item['Price']})
                                st.toast(f"已加入 {item['Name']}")
            else: st.info("無商品")
        
        with c_r:
            st.markdown("##### 🧾 購物車")
            with st.container():
                st.markdown("<div class='cart-box'>", unsafe_allow_html=True)
                if st.session_state['pos_cart']:
                    base_raw = sum(i['subtotal'] for i in st.session_state['pos_cart'])
                    for i in st.session_state['pos_cart']: 
                        st.markdown(f"<div class='cart-item'><span>{i['name']} ({i['size']})</span><b>${i['subtotal']}</b></div>", unsafe_allow_html=True)
                    if st.button("🗑️ 清空"): st.session_state['pos_cart']=[]; st.rerun()
                    st.markdown("---")
                    
                    col_d1, col_d2 = st.columns(2)
                    use_bundle = col_d1.checkbox("啟用組合價")
                    bundle_val = col_d2.number_input("組合總價", value=base_raw) if use_bundle else 0
                    calc_base = bundle_val if use_bundle else base_raw
                    
                    st.markdown("---")
                    col_disc1, col_disc2 = st.columns(2)
                    disc_mode = col_disc1.radio("再打折", ["無", "7折", "8折", "自訂"], horizontal=True)
                    cust_off = col_disc2.number_input("折數 %", 1, 100, 95) if disc_mode=="自訂" else 0
                    
                    final_total = calc_base
                    note_arr = []
                    if use_bundle: note_arr.append(f"(組合價${bundle_val})")
                    if disc_mode == "7折": final_total = int(round(calc_base * 0.7)); note_arr.append("(7折)")
                    elif disc_mode == "8折": final_total = int(round(calc_base * 0.8)); note_arr.append("(8折)")
                    elif disc_mode == "自訂": final_total = int(round(calc_base * (cust_off/100))); note_arr.append(f"({cust_off}折)")
                    
                    note_str = " ".join(note_arr)
                    st.markdown(f"<div class='final-price-display'>${final_total}</div>", unsafe_allow_html=True)
                    
                    sale_who = st.selectbox("經手", [st.session_state['user_name']] + [u for u in staff_list if u != st.session_state['user_name']])
                    sale_ch = st.selectbox("通路", ["門市","官網","直播","其他"])
                    pay = st.selectbox("付款", ["現金","刷卡","轉帳","禮券","其他"])
                    note = st.text_input("備註")
                    
                    if st.button("✅ 結帳", type="primary", use_container_width=True):
                        logs = []
                        valid = True
                        for item in st.session_state['pos_cart']:
                            cell = ws_items.find(item['sku'])
                            if cell:
                                curr = int(ws_items.cell(cell.row, 5).value)
                                if curr >= item['qty']:
                                    retry_action(ws_items.update_cell, cell.row, 5, curr - item['qty'])
                                    logs.append(f"{item['sku']} x{item['qty']}")
                                else: st.error(f"{item['name']} 庫存不足"); valid=False; break
                        
                        if valid:
                            content = f"Sale | Total:${final_total} | Items:{','.join(logs)} | {note} {note_str} | {pay} | {sale_ch} | By:{sale_who}"
                            log_event(ws_logs, st.session_state['user_name'], "Sale", content)
                            st.session_state['pos_cart'] = []
                            st.cache_data.clear(); st.balloons(); st.success("完成"); time.sleep(1); st.rerun()
                else: st.info("購物車是空的")
                st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        st.subheader("📈 營運戰情室")
        rev = (df['Qty'] * df['Price']).sum()
        cost = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum()
        rmb_total = 0
        if 'Orig_Currency' in df.columns:
            rmb_df = df[df['Orig_Currency'] == 'CNY']
            if not rmb_df.empty: rmb_total = ((rmb_df['Qty'] + rmb_df['Qty_CN']) * rmb_df['Orig_Cost']).sum()
        profit = rev - (df['Qty'] * df['Cost']).sum()
        real = calculate_realized_revenue(get_data_safe(ws_logs))
        
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='metric-card'><div class='metric-label'>預估營收</div><div class='metric-value'>${rev:,}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-label'>總成本 (TWD)</div><div class='metric-value'>${cost:,}</div><div style='font-size:10px;'>含 RMB 原幣: ¥{rmb_total:,}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><div class='metric-label'>潛在毛利</div><div class='metric-value' style='color:#f59e0b'>${profit:,}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card'><div class='metric-label'>實際營收</div><div class='metric-value' style='color:#10b981'>${real:,}</div></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        sales_data = []
        if not logs_df.empty:
            s_logs = logs_df[logs_df['Action'] == 'Sale']
            for _, row in s_logs.iterrows():
                try:
                    d = row['Details']
                    # 支援 V103.10 與 V104 新格式
                    total_m = re.search(r'Total:\$(\d+)', d); total_v = int(total_m.group(1)) if total_m else 0
                    ch_m = re.search(r' \| (門市|官網|直播|其他)', d); ch_v = ch_m.group(1) if ch_m else "未分類"
                    pay_m = re.search(r' \| (現金|刷卡|轉帳|禮券)', d); pay_v = pay_m.group(1) if pay_m else "-"
                    by_m = re.search(r'By:(\w+)', d); by_v = by_m.group(1) if by_m else row['User']
                    items_m = re.search(r'Items:(.*?) \|', d); items_v = items_m.group(1) if items_m else "-"
                    if total_v > 0: sales_data.append({"日期":row['Timestamp'],"金額":total_v,"通路":ch_v,"付款":pay_v,"銷售員":by_v,"明細":items_v})
                except: pass
        sdf = pd.DataFrame(sales_data)
        
        if not sdf.empty:
            c1, c2 = st.columns(2)
            with c1: 
                fig = px.pie(sdf, names='通路', values='金額', hole=0.4, title="通路營收佔比"); st.plotly_chart(fig, use_container_width=True)
            with c2: 
                fig2 = px.bar(sdf.groupby('銷售員')['金額'].sum().reset_index(), x='銷售員', y='金額', title="人員業績排行"); st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(sdf, use_container_width=True)
        else: st.info("尚無銷售數據")

    with tabs[3]:
        st.subheader("🎁 內部領用/稽核 (含回溯功能)")
        with st.expander("新增領用單", expanded=True):
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist() if not df.empty else []
            sel = st.selectbox("商品", ["..."] + opts)
            if sel != "...":
                tsku = sel.split(" | ")[0]; tr = df[df['SKU'] == tsku].iloc[0]; st.info(f"庫存: {tr['Qty']}")
                with st.form("internal"):
                    q = st.number_input("數量", 1); who = st.selectbox("人", staff_list); rsn = st.selectbox("因", ["公務", "報廢", "福利"]); n = st.text_input("備註")
                    if st.form_submit_button("執行"):
                        r = ws_items.find(tsku).row; retry_action(ws_items.update_cell, r, 5, int(tr['Qty'])-q)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{tsku} -{q} | {who} | {rsn} | {n}")
                        st.cache_data.clear(); st.success("OK"); st.rerun()
        
        st.divider()
        st.markdown("#### 🕵️ 紀錄與回溯")
        if not logs_df.empty:
            int_df = logs_df[logs_df['Action']=="Internal_Use"]
            st.dataframe(int_df, use_container_width=True)
            
            # V103.0 強制回溯功能 (Source 6)
            st.markdown("##### 🛠️ 強制回溯 (修正錯誤)")
            rev_opts = int_df.apply(lambda x: f"{x['Timestamp']} | {x['Details']}", axis=1).tolist()
            sel_rev = st.selectbox("選擇紀錄", ["..."] + rev_opts)
            if sel_rev != "...":
                if st.button("🚫 撤銷此紀錄並歸還庫存"):
                    # 解析 Log
                    try:
                        ts = sel_rev.split(" | ")[0]
                        detail_part = sel_rev.split(" | ", 1)[1]
                        sku_part = detail_part.split(" -")[0]
                        qty_part = int(detail_part.split(" -")[1].split(" | ")[0])
                        
                        # 找 Log 行並刪除
                        all_logs = ws_logs.get_all_values()
                        for idx, row in enumerate(all_logs):
                            if row[0] == ts and sku_part in row[3]: retry_action(ws_logs.delete_rows, idx + 1); break
                        
                        # 歸還庫存
                        cell = ws_items.find(sku_part)
                        if cell:
                            curr_q = int(ws_items.cell(cell.row, 5).value)
                            retry_action(ws_items.update_cell, cell.row, 5, curr_q + qty_part)
                            st.success(f"已歸還 {sku_part} +{qty_part}"); time.sleep(1); st.rerun()
                    except: st.error("解析失敗，請手動修正")

    with tabs[4]:
        st.subheader("矩陣管理")
        mt1, mt2, mt3 = st.tabs(["新增", "雙向調撥", "刪除"])
        with mt1:
            mode = st.radio("模式", ["新系列", "衍生"], horizontal=True)
            a_sku, a_name = "", ""
            if mode == "新系列":
                c = st.selectbox("分類", CAT_LIST)
                if st.button("生成"): st.session_state['base'] = generate_smart_style_code(c, df['SKU'].tolist())
                if 'base' in st.session_state: a_sku = st.session_state['base']
            else:
                p = st.selectbox("母商品", ["..."] + df['SKU'].tolist())
                if p != "...": 
                    pr = df[df['SKU']==p].iloc[0]; a_sku = get_style_code(p)+"-NEW"; a_name = pr['Name']
            with st.form("add_m"):
                c1, c2 = st.columns(2); bs = c1.text_input("Base SKU", value=a_sku); nm = c2.text_input("品名", value=a_name)
                c3, c4 = st.columns(2); pr = c3.number_input("售價", 0); co = c4.number_input("原幣成本", 0)
                cur = st.selectbox("幣別", ["TWD", "CNY"]); img = st.file_uploader("圖")
                sz = {}; cols = st.columns(5)
                for i, s in enumerate(SIZE_ORDER): sz[s] = cols[i%5].number_input(s, min_value=0)
                if st.form_submit_button("寫入"):
                    url = upload_image_to_imgbb(img) if img else ""
                    fc = int(co * st.session_state['exchange_rate']) if cur == "CNY" else co
                    for s, q in sz.items():
                        if q > 0: retry_action(ws_items.append_row, [f"{bs}-{s}", nm, "New", s, q, pr, fc, get_taiwan_time_str(), url, 5, cur, co, 0])
                    st.cache_data.clear(); st.success("完成"); st.rerun()
        with mt2:
            sel = st.selectbox("調撥", ["..."] + df['SKU'].tolist())
            if sel != "...":
                r = df[df['SKU']==sel].iloc[0]; st.write(f"TW: {r['Qty']} | CN: {r['Qty_CN']}"); q = st.number_input("量", 1)
                c1, c2 = st.columns(2)
                if c1.button("TW->CN"): 
                    r = ws_items.find(sel).row; retry_action(ws_items.update_cell, r, 5, int(r['Qty'])-q); retry_action(ws_items.update_cell, r, 13, int(r['Qty_CN'])+q); st.cache_data.clear(); st.success("OK"); st.rerun()
                if c2.button("CN->TW"):
                    r = ws_items.find(sel).row; retry_action(ws_items.update_cell, r, 5, int(r['Qty'])+q); retry_action(ws_items.update_cell, r, 13, int(r['Qty_CN'])-q); st.cache_data.clear(); st.success("OK"); st.rerun()
        with mt3:
            d = st.selectbox("刪除", ["..."] + df['SKU'].tolist())
            if d != "..." and st.button("確認刪除"): retry_action(ws_items.delete_rows, ws_items.find(d).row); st.cache_data.clear(); st.success("OK"); st.rerun()

    with tabs[5]: 
        st.subheader("📝 日誌搜尋")
        l_q = st.text_input("搜尋日誌 (人名/動作/內容)")
        if not logs_df.empty:
            view_df = logs_df.sort_index(ascending=False)
            if l_q: view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(l_q, case=False)).any(axis=1)]
            st.dataframe(view_df, use_container_width=True)

    with tabs[6]: 
        st.subheader("👥 人員管理 (Admin)")
        if st.session_state['user_role'] == 'Admin':
            st.dataframe(users_df, use_container_width=True)
            with st.expander("新增人員"):
                with st.form("new_user"):
                    nu = st.text_input("帳號"); np = st.text_input("密碼"); nr = st.selectbox("權限", ["Staff", "Admin"])
                    if st.form_submit_button("新增"):
                        retry_action(ws_users.append_row, [nu, make_hash(np), nr, "Active", get_taiwan_time_str()])
                        st.cache_data.clear(); st.success("已新增"); st.rerun()
            with st.expander("刪除人員"):
                du = st.selectbox("選擇刪除", users_df['Name'].tolist())
                if st.button("確認刪除"):
                    cell = ws_users.find(du)
                    retry_action(ws_users.delete_rows, cell.row)
                    st.cache_data.clear(); st.success("已刪除"); st.rerun()
        else:
            st.error("權限不足")
    
    with tabs[7]:
        render_roster_system(sh, staff_list, st.session_state['user_name'])

if __name__ == "__main__":
    main()
