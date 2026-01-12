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
    page_title="IFUKUK V103.16 SALES-FORCE", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🛑 CSS 視覺核心 (V103.15 完整保留)
# ==========================================
st.markdown("""
    <style>
        .stApp { background-color: #F8F9FA !important; }
        div[data-testid="stRadio"] > label { display:none; }
        div[data-testid="stRadio"] > div { 
            flex-direction: row; gap: 8px; justify-content: start; 
            background: #fff; padding: 10px; border-radius: 12px; 
            border: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
            overflow-x: auto; white-space: nowrap;
        }
        .uni-card { 
            background: #fff; border-radius: 12px; overflow: hidden; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid #E5E7EB; 
            display: flex; flex-direction: column; height: 100%; position: relative;
        }
        .uni-img { width: 100%; height: 140px; object-fit: cover; background: #f0f0f0; }
        .uni-content { padding: 10px; flex-grow: 1; }
        .uni-title { font-weight: bold; font-size: 0.95rem; color: #111; margin-bottom: 4px; line-height: 1.3; }
        .uni-spec { font-size: 0.85rem; color: #4b5563; margin-bottom: 6px; font-weight: 600; }
        .uni-price { color: #059669; font-weight: 900; font-size: 1rem; }
        .uni-badge { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; display: inline-block; margin-right: 4px; font-weight: bold;}
        .bg-tw { background: #dbeafe; color: #1e40af; }
        .bg-cn { background: #fef3c7; color: #92400e; }
        .pagination-container { display: flex; justify-content: center; align-items: center; gap: 20px; margin-top: 15px; padding: 10px; background: #fff; border-radius: 10px; }
        .cart-box { background: #fff; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px; margin-bottom: 10px; }
        .cart-item { display: flex; justify-content: space-between; border-bottom: 1px dashed #ddd; padding: 8px 0; font-size: 0.9rem; }
        .final-price-box { font-size: 1.8rem; font-weight: 900; color: #16a34a; text-align: center; background: #dcfce7; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #86efac; }
        .metric-card { background: #fff; border-radius: 12px; padding: 15px; border: 1px solid #eee; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 100%; }
        .metric-val { font-size: 1.6rem; font-weight: 800; color:#111; margin: 5px 0; }
        .metric-lbl { font-size: 0.8rem; color:#666; font-weight: 600; text-transform: uppercase;}
        .metric-sub { font-size: 0.75rem; color: #999; margin-top: -5px; }
        .roster-header { background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #bfdbfe; }
        .day-cell { border: 1px solid #eee; border-radius: 8px; padding: 5px; min-height: 80px; position: relative; margin-bottom: 5px; transition: 0.2s; background: #fff; }
        .day-cell:hover { border-color: #3b82f6; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .shift-tag { font-size: 0.75rem; padding: 2px 5px; border-radius: 4px; margin: 2px; display: block; text-align: center; color: white; font-weight: bold; }
        .note-dot { position: absolute; top: 5px; right: 5px; width: 8px; height: 8px; background: #ef4444; border-radius: 50%; }
        .stButton>button { border-radius: 10px; height: 3.2rem; font-weight: 700; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 100%; }
        input, .stTextInput>div>div, div[data-baseweb="select"]>div { border-radius: 10px !important; min-height: 3rem; }
        .audit-stat-box { background: #fff7ed; border: 1px solid #ffedd5; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 10px; }
        .audit-num { font-size: 1.5rem; font-weight: 800; color: #c2410c; }
        .audit-txt { font-size: 0.8rem; color: #9a3412; font-weight: bold; }
        
        /* V103.16 新增：激勵看板樣式 */
        .sales-leader-box { background: linear-gradient(to right, #ecfdf5, #fff); border: 1px solid #a7f3d0; padding: 15px; border-radius: 12px; margin-top: 15px; }
        .crown-icon { font-size: 1.2rem; margin-right: 5px; }
        
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]
SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
ITEMS_PER_PAGE = 15

# --- 核心連線 (V103.15 Zero Conflict) ---
@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=15, show_spinner=False)
def get_data_pure(_ws_obj, expected_headers=None):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if _ws_obj is None: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            raw_data = _ws_obj.get_all_values()
            if not raw_data or len(raw_data) < 2: 
                if expected_headers:
                    try:
                        _ws_obj.clear(); _ws_obj.append_row(expected_headers)
                        return pd.DataFrame(columns=expected_headers)
                    except: pass
                return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            
            headers = raw_data[0]
            seen = {}; new_headers = []
            for h in headers:
                if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
                else: seen[h] = 0; new_headers.append(h)
            rows = raw_data[1:]
            
            if expected_headers and "Qty_CN" in expected_headers and "Qty_CN" not in new_headers:
                try: _ws_obj.update_cell(1, len(new_headers)+1, "Qty_CN"); new_headers.append("Qty_CN"); raw_data = _ws_obj.get_all_values(); rows = raw_data[1:]
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

def update_cell_retry(ws, row, col, value, retries=3):
    for i in range(retries):
        try: ws.update_cell(row, col, value); return True
        except Exception as e:
            if "429" in str(e): time.sleep(2 ** (i + 1)); continue
    return False

@st.cache_resource(ttl=600)
def init_db():
    try:
        client = get_connection()
        return client.open_by_url(GOOGLE_SHEET_URL)
    except Exception: return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        try:
            ws = sh.add_worksheet(title, rows=100, cols=20)
            ws.append_row(headers)
            return ws
        except: return None
    except: return None

# --- 工具模組 ---
def get_taiwan_time_str(): return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
def render_image_url(url_input):
    if not url_input or (isinstance(url_input, float) and math.isnan(url_input)): return "https://i.ibb.co/W31w56W/placeholder.png"
    s = str(url_input).strip()
    return s if len(s) > 10 and s.startswith("http") else "https://i.ibb.co/W31w56W/placeholder.png"
def make_hash(password): return hashlib.sha256(str(password).encode()).hexdigest()
def check_hash(password, hashed_text): return make_hash(password) == hashed_text
def log_event(ws_logs, user, action, detail):
    try: ws_logs.append_row([get_taiwan_time_str(), user, action, detail])
    except: pass
def upload_image_to_imgbb(image_file):
    if not IMGBB_API_KEY: return None
    try:
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(image_file.getvalue()).decode('utf-8')}
        response = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if response.status_code == 200: return response.json()["data"]["url"]
    except: pass; return None
def get_style_code(sku): return str(sku).strip().rsplit('-', 1)[0] if '-' in str(sku) else str(sku).strip()
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
@st.cache_data(ttl=3600)
def get_live_rate():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/CNY"
        response = requests.get(url, timeout=5)
        if response.status_code == 200: return response.json()['rates']['TWD'], True
    except: pass
    return 4.50, False

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

# ==========================================
# 🗓️ 排班模組 (V103.15 Perfect)
# ==========================================
def get_staff_color(name):
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6366F1", "#14B8A6", "#F97316"]
    return colors[sum(ord(c) for c in str(name)) % len(colors)]

def render_roster_system(sh, users_list):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Type", "Note", "Notify", "Updated_By"])
    shifts_df = get_data_pure(ws_shifts, expected_headers=["Date", "Staff", "Type", "Note", "Notify", "Updated_By"])
    
    if not shifts_df.empty:
        if 'Shift_Type' in shifts_df.columns: shifts_df = shifts_df.rename(columns={'Shift_Type': 'Type'})
        if 'Type' not in shifts_df.columns: shifts_df['Type'] = '正常班'

    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班與管理中心</h3></div>", unsafe_allow_html=True)
    
    with st.expander("⚡ 智慧批次排班 (Date Range)", expanded=False):
        with st.form("batch_roster"):
            c1, c2, c3 = st.columns(3)
            b_staff = c1.selectbox("人員", users_list)
            b_type = c2.selectbox("班別", ["正常班", "早班", "晚班", "全班", "公休", "特休", "空班", "代班"])
            b_dates = c3.date_input("日期範圍 (起~迄)", [])
            b_note = st.text_input("備註 (選填)")
            if st.form_submit_button("🚀 執行批次排班", type="primary"):
                if len(b_dates) == 2:
                    start_d, end_d = b_dates
                    delta = end_d - start_d
                    for i in range(delta.days + 1):
                        curr_d = (start_d + timedelta(days=i)).strftime("%Y-%m-%d")
                        all_vals = ws_shifts.get_all_values()
                        rows_to_del = [idx+1 for idx, v in enumerate(all_vals) if len(v)>1 and v[0]==curr_d and v[1]==b_staff]
                        for r_idx in reversed(rows_to_del): ws_shifts.delete_rows(r_idx)
                        ws_shifts.append_row([curr_d, b_staff, b_type, b_note, "FALSE", st.session_state['user_name']])
                    st.cache_data.clear(); st.success(f"已排入 {delta.days+1} 天"); time.sleep(1); st.rerun()
                else: st.error("請選擇完整日期")

    now = datetime.utcnow() + timedelta(hours=8)
    col1, col2 = st.columns([1, 1])
    sel_year = col1.number_input("年份", 2024, 2030, now.year)
    sel_month = col2.selectbox("月份", range(1, 13), now.month)
    
    cal = calendar.monthcalendar(sel_year, sel_month)
    cols = st.columns(7)
    for i, d in enumerate(["一", "二", "三", "四", "五", "六", "日"]): cols[i].markdown(f"<div style='text-align:center;font-weight:bold;color:#666;'>{d}</div>", unsafe_allow_html=True)
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day != 0:
                    date_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == date_str] if not shifts_df.empty else pd.DataFrame()
                    badges = ""
                    for _, r in day_shifts.iterrows():
                        bg = get_staff_color(r['Staff'])
                        s_type = r.get('Type', '正常班')
                        if s_type in ["公休", "空班"]: bg = "#9CA3AF"
                        if s_type == "特休": bg = "#EF4444"
                        badges += f"<span class='shift-tag' style='background:{bg}'>{r['Staff']}</span>"
                    if st.button(f"{day}", key=f"c_{date_str}", use_container_width=True):
                        st.session_state['roster_date'] = date_str; st.rerun()
                    st.markdown(f"<div style='min-height:30px;text-align:center;line-height:1.2;'>{badges}</div>", unsafe_allow_html=True)
                else: st.markdown("<div style='min-height:60px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    c_edit, c_stat = st.columns([1, 1])
    with c_edit:
        if 'roster_date' in st.session_state:
            t_date = st.session_state['roster_date']
            st.info(f"編輯: {t_date}")
            with st.form("single_roster"):
                s_staff = st.selectbox("人員", users_list, key="s_st")
                s_type = st.selectbox("狀態", ["正常班", "早班", "晚班", "全班", "公休", "特休", "空班", "代班"], key="s_tp")
                s_note = st.text_input("備註", key="s_nt")
                if st.form_submit_button("➕ 排入單日"):
                    all_vals = ws_shifts.get_all_values()
                    rows_to_del = [idx+1 for idx, v in enumerate(all_vals) if len(v)>1 and v[0]==t_date and v[1]==s_staff]
                    for r_idx in reversed(rows_to_del): ws_shifts.delete_rows(r_idx)
                    ws_shifts.append_row([t_date, s_staff, s_type, s_note, "FALSE", st.session_state['user_name']])
                    st.cache_data.clear(); st.success("OK"); st.rerun()
            
            curr = shifts_df[shifts_df['Date'] == t_date] if not shifts_df.empty else pd.DataFrame()
            if not curr.empty:
                st.caption("當日已排 (點擊刪除):")
                for _, r in curr.iterrows():
                    if st.button(f"🗑️ {r['Staff']} ({r.get('Type','?')})", key=f"del_{t_date}_{r['Staff']}"):
                        all_v = ws_shifts.get_all_values()
                        for idx, v in enumerate(all_v):
                            if len(v)>1 and v[0]==t_date and v[1]==r['Staff']: ws_shifts.delete_rows(idx+1); break
                        st.cache_data.clear(); st.rerun()
        else: st.info("👈 點擊日期進行編輯")

    with c_stat:
        st.markdown(f"##### 📊 {sel_month}月 工時統計")
        if not shifts_df.empty:
            m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
            m_data = shifts_df[shifts_df['Date'].str.startswith(m_prefix)]
            if not m_data.empty:
                work_data = m_data[~m_data['Type'].isin(['公休','空班','特休'])]
                counts = work_data.groupby('Staff').size()
                st.dataframe(counts.reset_index(name="上班天數"), use_container_width=True, hide_index=True)
            else: st.caption("本月無上班資料")

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False; st.session_state['user_name'] = ""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    
    # 狀態初始化
    for k in ['page_num_pos', 'page_num_inv', 'page_num_int']:
        if k not in st.session_state: st.session_state[k] = 0
    
    if 'exchange_rate' not in st.session_state:
        l_rate, succ = get_live_rate()
        st.session_state['exchange_rate'] = l_rate
        st.session_state['rate_source'] = "Live API" if succ else "Manual"

    sh = init_db()
    if not sh: st.error("資料庫連線失敗 (Connection Error)"); return

    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><br><h1 style='text-align:center'>IFUKUK</h1><p style='text-align:center'>OMEGA V103.16 SALES-FORCE</p>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("帳號 (ID)"); p = st.text_input("密碼 (Password)", type="password")
                if st.form_submit_button("登入 (LOGIN)", type="primary"):
                    with st.spinner("安全登入中..."):
                        udf = get_data_pure(ws_users, expected_headers=["Name", "Password", "Role", "Status", "Created_At"])
                        if udf.empty and u=="Boss" and p=="1234":
                            ws_users.append_row(["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                            st.cache_data.clear(); st.success("Boss 初始化成功"); time.sleep(1); st.rerun()
                        if not udf.empty and 'Name' in udf.columns:
                            tgt = udf[(udf['Name']==u) & (udf['Status']=='Active')]
                            if not tgt.empty:
                                stored = tgt.iloc[0]['Password']
                                if (len(stored)==64 and check_hash(p, stored)) or (p==stored):
                                    st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=tgt.iloc[0]['Role']; log_event(ws_logs, u, "Login", "Success"); st.rerun()
                                else: st.error("密碼錯誤")
                            else: st.error("找不到帳號")
                        else: st.warning("系統連線忙碌，請稍後再試")
        return

    render_navbar(st.session_state['user_name'][0].upper())
    df = get_data_pure(ws_items, expected_headers=SHEET_HEADERS)
    for c in ["Qty","Price","Cost","Orig_Cost","Qty_CN"]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        st.caption(f"權限: {st.session_state['user_role']}")
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

    nav = st.radio("", ["🛒 POS收銀", "📊 庫存總覽", "🗓️ 員工排班", "📈 營運戰情", "🎁 領用/稽核", "👔 矩陣管理", "📝 全域日誌", "👥 員工管理"], horizontal=True)

    # --- 1. POS ---
    if nav == "🛒 POS收銀":
        c_l, c_r = st.columns([3, 2])
        with c_l:
            st.markdown("##### 🛍️ 商品畫廊 (點擊加入)")
            cats_avail = sorted(list(set(CAT_LIST + (df['Category'].unique().tolist() if not df.empty else []))))
            c_s1, c_s2 = st.columns([2, 1])
            q = c_s1.text_input("搜尋商品", placeholder="輸入款號或名稱...", label_visibility="collapsed")
            cat = c_s2.selectbox("分類", ["全部"] + cats_avail, label_visibility="collapsed")
            vdf = df.copy()
            if cat != "全部": vdf = vdf[vdf['Category'] == cat]
            if q: vdf = vdf[vdf.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
            
            total_items = len(vdf)
            total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
            if st.session_state['page_num_pos'] >= total_pages: st.session_state['page_num_pos'] = 0
            start_idx = st.session_state['page_num_pos'] * ITEMS_PER_PAGE
            page_df = vdf.iloc[start_idx : start_idx + ITEMS_PER_PAGE]
            
            if not page_df.empty:
                rows = [page_df.iloc[i:i+3] for i in range(0, len(page_df), 3)]
                for row_items in rows:
                    cols = st.columns(3)
                    for i, (_, item) in enumerate(row_items.iterrows()):
                        with cols[i]:
                            st.markdown(f"<div class='uni-card'><div class='uni-img'><img src='{render_image_url(item['Image_URL'])}' style='width:100%;height:100%;object-fit:cover;'></div><div class='uni-content'><div class='uni-title'>{item['Name']}</div><div class='uni-spec'>{item['Size']} | {item['SKU']}</div><div class='uni-price'>${item['Price']}</div><span class='uni-badge bg-tw'>TW:{item['Qty']}</span></div></div>", unsafe_allow_html=True)
                            if st.button("➕ 加入", key=f"pos_add_{item['SKU']}", use_container_width=True):
                                st.session_state['pos_cart'].append({"sku":item['SKU'],"name":item['Name'],"size":item['Size'],"price":item['Price'],"qty":1,"subtotal":item['Price']})
                                st.toast(f"已加入 {item['Name']} ({item['Size']})")
                st.markdown("<div class='pagination-container'>", unsafe_allow_html=True)
                cp1, cp2, cp3 = st.columns([1, 2, 1])
                if cp1.button("⬅️ 上頁", key="pos_prev", disabled=st.session_state['page_num_pos']==0): st.session_state['page_num_pos'] -= 1; st.rerun()
                cp2.markdown(f"<div style='text-align:center'>第 {st.session_state['page_num_pos']+1} / {total_pages} 頁</div>", unsafe_allow_html=True)
                if cp3.button("下頁 ➡️", key="pos_next", disabled=st.session_state['page_num_pos']>=total_pages-1): st.session_state['page_num_pos'] += 1; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else: st.info("無符合商品")

        with c_r:
            st.markdown("##### 🧾 購物車")
            with st.container():
                st.markdown("<div class='cart-box'>", unsafe_allow_html=True)
                if st.session_state['pos_cart']:
                    base = sum(i['subtotal'] for i in st.session_state['pos_cart'])
                    for idx, i in enumerate(st.session_state['pos_cart']): 
                        c_n, c_d = st.columns([4, 1])
                        c_n.markdown(f"**{i['name']}** ({i['size']}) x{i['qty']} = ${i['subtotal']}")
                        if c_d.button("🗑️", key=f"rm_cart_{idx}"): st.session_state['pos_cart'].pop(idx); st.rerun()
                    st.markdown("---")
                    if st.button("🗑️ 清空購物車", use_container_width=True): st.session_state['pos_cart']=[]; st.rerun()
                    st.markdown("###### 💰 結帳設定")
                    c_d1, c_d2 = st.columns(2)
                    disc = c_d1.radio("折扣", ["無", "7折", "8折", "自訂"], horizontal=True)
                    cust = c_d2.number_input("折數 %", 1, 100, 95) if disc=="自訂" else 0
                    bundle = st.checkbox("啟用組合價")
                    b_val = st.number_input("組合總額", value=base) if bundle else base
                    final = int(round(b_val * 0.7)) if disc=="7折" else (int(round(b_val * 0.8)) if disc=="8折" else (int(round(b_val * (cust/100))) if disc=="自訂" else b_val))
                    st.markdown(f"<div class='final-price-box'>實收: ${final}</div>", unsafe_allow_html=True)
                    c_ch, c_who = st.columns(2)
                    sale_ch = c_ch.selectbox("銷售通路", ["門市", "官網", "直播", "其他"])
                    who = c_who.selectbox("經手人", [st.session_state['user_name']]+(list(ws_users.col_values(1)[1:]) if ws_users else []))
                    pay = st.selectbox("付款方式", ["現金","刷卡","轉帳"]); note = st.text_input("備註")
                    if st.button("✅ 確認結帳", type="primary", use_container_width=True):
                        items = []; valid = True
                        for i in st.session_state['pos_cart']:
                            cell = ws_items.find(i['sku'])
                            if cell:
                                curr = int(ws_items.cell(cell.row, 5).value)
                                if curr >= i['qty']:
                                    update_cell_retry(ws_items, cell.row, 5, curr-i['qty'])
                                    items.append(f"{i['sku']} x{i['qty']}")
                                else: st.error("庫存不足"); valid=False; break
                        if valid:
                            log_event(ws_logs, st.session_state['user_name'], "Sale", f"Total:${final} | {','.join(items)} | {note} | {pay} | {sale_ch} | {who}")
                            st.session_state['pos_cart']=[]; st.cache_data.clear(); st.success("結帳完成"); time.sleep(1); st.rerun()
                else: st.info("購物車是空的")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # --- V103.16 NEW: 銷售激勵與統計 ---
            with st.expander("🏆 今日/本月 銷售戰績與明細", expanded=False):
                logs_df = get_data_pure(ws_logs, expected_headers=["Timestamp", "User", "Action", "Details"])
                if not logs_df.empty:
                    # 篩選銷售
                    sales_logs = logs_df[logs_df['Action'] == 'Sale'].copy()
                    sales_logs['Amount'] = sales_logs['Details'].apply(lambda x: int(re.search(r'Total:\$(\d+)', x).group(1)) if re.search(r'Total:\$(\d+)', x) else 0)
                    
                    if not sales_logs.empty:
                        # 1. 業績統計 (本月)
                        st.markdown("##### 🥇 本月銷售排行榜")
                        sales_by_user = sales_logs.groupby('User')['Amount'].sum().sort_values(ascending=False).reset_index()
                        
                        # 視覺化長條圖
                        fig_bar = px.bar(sales_by_user, x='User', y='Amount', text='Amount', color='Amount', color_continuous_scale='Bluered')
                        fig_bar.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0))
                        st.plotly_chart(fig_bar, use_container_width=True)
                        
                        # Top 1 顯示
                        top_sales = sales_by_user.iloc[0]
                        st.markdown(f"<div class='sales-leader-box'><span class='crown-icon'>👑</span> <b>本月銷售冠軍: {top_sales['User']}</b> (業績: ${top_sales['Amount']:,})</div>", unsafe_allow_html=True)
                        
                        st.divider()
                        
                        # 2. 今日明細
                        st.markdown("##### 📅 今日成交明細")
                        today = datetime.utcnow() + timedelta(hours=8)
                        today_str = today.strftime("%Y-%m-%d")
                        today_recs = sales_logs[sales_logs['Timestamp'].str.contains(today_str)]
                        if not today_recs.empty:
                            st.dataframe(today_recs[['Timestamp', 'User', 'Details', 'Amount']], use_container_width=True)
                        else: st.caption("今日尚無成交紀錄")
                    else: st.info("尚無銷售數據")
                else: st.info("尚無日誌資料")

    # --- 2. 庫存 ---
    elif nav == "📊 庫存總覽":
        st.subheader("📦 庫存清單")
        m1, m2 = st.columns(2)
        m1.metric("TW 總庫存", df['Qty'].sum())
        m2.metric("CN 總庫存", df['Qty_CN'].sum())
        
        df_display = df.rename(columns={"SKU": "貨號", "Name": "品名", "Category": "分類", "Size": "尺寸", "Qty": "台灣庫存", "Qty_CN": "中國庫存", "Price": "售價", "Cost": "成本"})
        tot = len(df)
        tot_p = math.ceil(tot/20)
        col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
        if col_p1.button("⬅️", key="inv_prev", disabled=st.session_state['page_num_inv']==0): st.session_state['page_num_inv'] -= 1; st.rerun()
        col_p2.markdown(f"<div style='text-align:center'>第 {st.session_state['page_num_inv']+1} / {tot_p} 頁</div>", unsafe_allow_html=True)
        if col_p3.button("➡️", key="inv_next", disabled=st.session_state['page_num_inv']>=tot_p-1): st.session_state['page_num_inv'] += 1; st.rerun()
        p_start = st.session_state['page_num_inv'] * 20
        cols_show = ["貨號", "品名", "分類", "尺寸", "台灣庫存", "中國庫存", "售價"]
        st.dataframe(df_display.iloc[p_start : p_start+20][cols_show], use_container_width=True)

    # --- 3. 排班 ---
    elif nav == "🗓️ 員工排班":
        render_roster_system(sh, ws_users.col_values(1)[1:] if ws_users else [])

    # --- 4. 戰情 ---
    elif nav == "📈 營運戰情":
        st.subheader("📈 營運戰情室")
        rev = (df['Qty']*df['Price']).sum()
        cost = ((df['Qty']+df['Qty_CN'])*df['Cost']).sum()
        rmb = 0
        if 'Orig_Currency' in df.columns:
            rmb_df = df[df['Orig_Currency']=='CNY']
            if not rmb_df.empty: rmb = ((rmb_df['Qty']+rmb_df['Qty_CN'])*rmb_df['Orig_Cost']).sum()
        profit = rev - (df['Qty'] * df['Cost']).sum()
        logs_df = get_data_pure(ws_logs, expected_headers=["Timestamp", "User", "Action", "Details"])
        real = calculate_realized_revenue(logs_df)
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='metric-card'><div class='metric-lbl'>預估營收</div><div class='metric-val'>${rev:,}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-lbl'>總成本 (含原幣)</div><div class='metric-val'>${cost:,}</div><div class='metric-sub'>¥{rmb:,}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><div class='metric-lbl'>潛在毛利</div><div class='metric-val' style='color:#f59e0b'>${profit:,}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card'><div class='metric-lbl'>實際營收</div><div class='metric-val' style='color:#10b981'>${real:,}</div></div>", unsafe_allow_html=True)
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 📦 庫存分類佔比")
            fig = px.pie(df, names='Category', values='Qty', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("##### 🔥 熱銷 Top 10 (庫存量)")
            top = df.groupby('Name')['Qty'].sum().sort_values(ascending=False).head(10).reset_index()
            fig2 = px.bar(top, x='Qty', y='Name', orientation='h', text='Qty')
            st.plotly_chart(fig2, use_container_width=True)

    # --- 5. 領用 ---
    elif nav == "🎁 領用/稽核":
        st.subheader("🎁 領用管理中心")
        logs_df = get_data_pure(ws_logs, expected_headers=["Timestamp", "User", "Action", "Details"])
        int_logs = pd.DataFrame()
        if not logs_df.empty and 'Action' in logs_df.columns:
            int_logs = logs_df[logs_df['Action'] == 'Internal_Use']
        if not int_logs.empty:
            total_int = len(int_logs)
            st.markdown(f"""<div style='display:flex; gap:10px; margin-bottom:10px;'><div class='audit-stat-box' style='flex:1;'><div class='audit-num'>{total_int}</div><div class='audit-txt'>總領用筆數</div></div></div>""", unsafe_allow_html=True)
            with st.expander("🏆 各人員領用統計 (點擊展開)", expanded=False):
                rank = int_logs['User'].value_counts().reset_index()
                rank.columns = ['人員', '筆數']
                st.dataframe(rank, use_container_width=True)

        st.markdown("##### ➕ 新增領用")
        c_l, c_r = st.columns([3, 2])
        with c_l:
            q = st.text_input("搜尋領用品", placeholder="...", label_visibility="collapsed")
            idf = df.copy()
            if q: idf = idf[idf.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
            tot_i = len(idf)
            tot_pi = math.ceil(tot_i / 9)
            if st.session_state['page_num_int'] >= tot_pi: st.session_state['page_num_int'] = 0
            start = st.session_state['page_num_int'] * 9
            page_idf = idf.iloc[start : start+9]
            if not page_idf.empty:
                rows = [page_idf.iloc[i:i+3] for i in range(0, len(page_idf), 3)]
                for r in rows:
                    cols = st.columns(3)
                    for i, (_, item) in enumerate(r.iterrows()):
                        with cols[i]:
                            st.markdown(f"<div class='uni-card'><div class='uni-img'><img src='{render_image_url(item['Image_URL'])}' style='width:100%;height:100%;object-fit:cover;'></div><div class='uni-content'><div class='uni-title'>{item['Name']}</div><div class='uni-spec'>{item['Size']}</div><span class='uni-badge bg-tw'>現貨:{item['Qty']}</span></div></div>", unsafe_allow_html=True)
                            if st.button("選取", key=f"int_{item['SKU']}", use_container_width=True):
                                st.session_state['int_target'] = item['SKU']
                st.markdown("<div class='pagination-container'>", unsafe_allow_html=True)
                cp1, cp2, cp3 = st.columns([1, 2, 1])
                if cp1.button("⬅️", key="int_prev", disabled=st.session_state['page_num_int']==0): st.session_state['page_num_int'] -= 1; st.rerun()
                cp2.markdown(f"<div style='text-align:center'>Page {st.session_state['page_num_int']+1}</div>", unsafe_allow_html=True)
                if cp3.button("➡️", key="int_next", disabled=st.session_state['page_num_int']>=tot_pi-1): st.session_state['page_num_int'] += 1; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        with c_r:
            if 'int_target' in st.session_state:
                tsku = st.session_state['int_target']
                trow = df[df['SKU']==tsku].iloc[0]
                st.info(f"已選: {trow['Name']} ({trow['Size']})")
                st.write(f"當前庫存: {trow['Qty']}")
                with st.form("int_do"):
                    q = st.number_input("數量", 1)
                    who = st.selectbox("領用人", ws_users.col_values(1)[1:] if ws_users else [])
                    rsn = st.selectbox("原因", ["公務制服", "福利", "樣品", "報廢", "其他"])
                    n = st.text_input("備註")
                    if st.form_submit_button("執行扣除"):
                        r = ws_items.find(tsku).row
                        update_cell_retry(ws_items, r, 5, int(trow['Qty'])-q)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{tsku} -{q} | {who} | {rsn} | {n}")
                        st.cache_data.clear(); st.success("OK"); time.sleep(1); st.rerun()
            else: st.info("👈 請選擇商品")
        st.divider()
        st.markdown("#### 📋 領用紀錄明細")
        if not int_logs.empty:
            int_display = int_logs[['Timestamp', 'User', 'Details']].copy()
            int_display.columns = ['時間', '經手人', '詳情 (含備註)']
            st.dataframe(int_display.sort_values('時間', ascending=False), use_container_width=True)
        else: st.caption("尚無領用紀錄")

    # --- 6. 管理 ---
    elif nav == "👔 矩陣管理":
        st.subheader("👔 管理中樞")
        t1, t2, t3 = st.tabs(["矩陣新增", "視覺調撥", "刪除庫存"])
        with t1:
            st.markdown("#### 新增商品")
            mode = st.radio("模式", ["新系列", "衍生"], horizontal=True)
            a_sku, a_name = "", ""
            if mode=="新系列":
                c = st.selectbox("分類", CAT_LIST)
                if st.button("生成"): st.session_state['base'] = generate_smart_style_code(c, df['SKU'].tolist())
                if 'base' in st.session_state: a_sku = st.session_state['base']
            else:
                p = st.selectbox("母商品", ["..."]+df['SKU'].tolist())
                if p!="...": pr=df[df['SKU']==p].iloc[0]; a_sku=get_style_code(p)+"-NEW"; a_name=pr['Name']
            with st.form("add_m"):
                c1, c2 = st.columns(2); bs = c1.text_input("Base SKU", value=a_sku); nm = c2.text_input("品名", value=a_name)
                c3, c4 = st.columns(2); pr = c3.number_input("售價 (TWD)", 0); co = c4.number_input("原幣成本", 0)
                cur = st.selectbox("成本幣別", ["TWD", "CNY"]); img = st.file_uploader("圖")
                sz = {}; cols = st.columns(5)
                for i, s in enumerate(SIZE_ORDER): sz[s] = cols[i%5].number_input(s, min_value=0)
                if st.form_submit_button("寫入資料庫"):
                    url = upload_image_to_imgbb(img) if img else ""
                    fc = int(co * st.session_state['exchange_rate']) if cur == "CNY" else co
                    for s, q in sz.items():
                        if q>0: ws_items.append_row([f"{bs}-{s}", nm, "New", s, q, pr, fc, get_taiwan_time_str(), url, 5, cur, co, 0])
                    st.cache_data.clear(); st.success("OK"); st.rerun()
        with t2:
            st.markdown("#### 📦 視覺化調撥")
            c_l, c_r = st.columns([3, 2])
            with c_l:
                q = st.text_input("搜尋調撥品", placeholder="...")
                tdf = df[df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)] if q else df.head(10)
                if not tdf.empty:
                    rows = [tdf.iloc[i:i+3] for i in range(0, len(tdf), 3)]
                    for r in rows:
                        cols = st.columns(3)
                        for i, (_, item) in enumerate(r.iterrows()):
                            with cols[i]:
                                st.markdown(f"<div class='uni-card'><div class='uni-img'><img src='{render_image_url(item['Image_URL'])}' style='width:100%;height:100%;object-fit:cover;'></div><div class='uni-content'><div class='uni-title'>{item['Name']}</div><div class='uni-spec'>{item['Size']}</div><span class='uni-badge bg-tw'>TW:{item['Qty']}</span> <span class='uni-badge bg-cn'>CN:{item['Qty_CN']}</span></div></div>", unsafe_allow_html=True)
                                if st.button("調撥", key=f"tr_{item['SKU']}", use_container_width=True):
                                    st.session_state['trans_target'] = item['SKU']
            with c_r:
                if 'trans_target' in st.session_state:
                    tsku = st.session_state['trans_target']; tr = df[df['SKU']==tsku].iloc[0]
                    st.info(f"調撥: {tr['Name']} ({tr['Size']})")
                    st.write(f"TW: {tr['Qty']} | CN: {tr['Qty_CN']}")
                    tq = st.number_input("數量", 1)
                    if st.button("TW -> CN"):
                        r = ws_items.find(tsku).row
                        update_cell_retry(ws_items, r, 5, int(tr['Qty'])-tq); update_cell_retry(ws_items, r, 13, int(tr['Qty_CN'])+tq)
                        st.cache_data.clear(); st.success("OK"); time.sleep(1); st.rerun()
                    if st.button("CN -> TW"):
                        r = ws_items.find(tsku).row
                        update_cell_retry(ws_items, r, 5, int(tr['Qty'])+tq); update_cell_retry(ws_items, r, 13, int(tr['Qty_CN'])-tq)
                        st.cache_data.clear(); st.success("OK"); time.sleep(1); st.rerun()
                else: st.info("👈 請選擇商品")
        with t3:
            st.markdown("#### 🗑️ 刪除商品")
            d_sku = st.selectbox("選擇刪除對象", ["..."] + df['SKU'].tolist())
            if d_sku != "...":
                st.warning(f"確定要刪除 {d_sku} 嗎？此操作不可逆。")
                if st.button("🔴 確認刪除"):
                    ws_items.delete_rows(ws_items.find(d_sku).row)
                    st.cache_data.clear(); st.success("已刪除"); st.rerun()

    # --- 7. 全域日誌 ---
    elif nav == "📝 全域日誌":
        st.subheader("📝 系統全域日誌與查詢")
        col_search, col_act = st.columns([3, 1])
        q = col_search.text_input("🔍 超級搜尋 (輸入日期/人名/商品/單號)", placeholder="例如: 2024-01-13 或 Admin 或 銷售")
        logs = get_data_pure(ws_logs, expected_headers=["Timestamp", "User", "Action", "Details"])
        if not logs.empty:
            filtered_logs = logs.copy()
            if q: filtered_logs = filtered_logs[filtered_logs.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
            filtered_logs.columns = ['時間', '操作人', '動作類型', '詳細內容']
            st.dataframe(filtered_logs.sort_values('時間', ascending=False), use_container_width=True)
        else: st.info("尚無日誌資料")

    # --- 8. 員工管理 ---
    elif nav == "👥 員工管理":
        if st.session_state['user_role'] == 'Admin':
            st.subheader("👥 員工帳號管理")
            users_df = get_data_cached(ws_users)
            st.dataframe(users_df, use_container_width=True)
            with st.expander("➕ 新增員工"):
                with st.form("add_user"):
                    n = st.text_input("帳號 (ID)"); p = st.text_input("密碼 (PWD)"); r = st.selectbox("權限", ["Staff", "Admin"])
                    if st.form_submit_button("新增"):
                        ws_users.append_row([n, make_hash(p), r, "Active", get_taiwan_time_str()])
                        st.cache_data.clear(); st.success("OK"); st.rerun()
            with st.expander("🗑️ 刪除員工"):
                d_u = st.selectbox("選擇帳號", users_df['Name'].tolist() if not users_df.empty else [])
                if st.button("確認刪除"):
                    cell = ws_users.find(d_u)
                    ws_users.delete_rows(cell.row); st.cache_data.clear(); st.success("Deleted"); st.rerun()
        else:
            st.error("權限不足 (Access Denied)")

    elif nav == "🚪 登出":
        st.session_state['logged_in'] = False; st.rerun()

if __name__ == "__main__":
    main()
