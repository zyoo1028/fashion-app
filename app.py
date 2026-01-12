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
    page_title="IFUKUK V103.22 TITANIUM", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🛑 CSS 視覺核心
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
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
LOG_HEADERS = ["Timestamp", "User", "Action", "Details"]
USER_HEADERS = ["Name", "Password", "Role", "Status", "Created_At"]
SHIFT_HEADERS = ["Date", "Staff", "Type", "Note", "Notify", "Updated_By"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]
SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
ITEMS_PER_PAGE = 15

# --- 核心連線 ---
@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets: st.error("❌ 金鑰遺失"); st.stop()
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=10, show_spinner=False)
def get_data_robust(_ws_obj, expected_headers):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if _ws_obj is None: return pd.DataFrame(columns=expected_headers)
            raw_data = _ws_obj.get_all_values()
            
            if not raw_data or len(raw_data) < 2:
                try: 
                    if not raw_data: _ws_obj.append_row(expected_headers)
                except: pass
                return pd.DataFrame(columns=expected_headers)
            
            headers = raw_data[0]
            seen = {}; new_headers = []
            for h in headers:
                if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
                else: seen[h] = 0; new_headers.append(h)
            
            rows = raw_data[1:]
            df = pd.DataFrame(rows)
            
            if not df.empty:
                if len(df.columns) > len(new_headers): df = df.iloc[:, :len(new_headers)]
                elif len(df.columns) < len(new_headers):
                    for _ in range(len(new_headers) - len(df.columns)): df[len(df.columns)] = ""
                df.columns = new_headers
                
                # Auto-fix Qty_CN
                if "Qty_CN" in expected_headers and "Qty_CN" not in df.columns:
                    df["Qty_CN"] = "0"
                
                for col in expected_headers:
                    if col not in df.columns: df[col] = ""
                
                df = df[expected_headers]
            return df
        except Exception as e:
            if "429" in str(e): time.sleep(2 ** (attempt + 1)); continue
            return pd.DataFrame(columns=expected_headers)
    return pd.DataFrame(columns=expected_headers)

def update_cell_retry(ws, row, col, value, retries=3):
    for i in range(retries):
        try: ws.update_cell(row, col, value); return True
        except: time.sleep(1 + i); continue
    return False

@st.cache_resource(ttl=600)
def init_db():
    try: return get_connection().open_by_url(GOOGLE_SHEET_URL)
    except: return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        try: ws = sh.add_worksheet(title, rows=100, cols=20); ws.append_row(headers); return ws
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

def parse_sales_details_smart(detail_str, sku_map=None):
    try:
        total = "0"; items_str = "-"; note = "-"; pay = "-"; channel = "門市 (舊紀錄)"; who = "-"
        m_total = re.search(r'Total:\$(\d+)', detail_str); 
        if m_total: total = m_total.group(1)
        m_ch = re.search(r'Ch:([^\s|]+)', detail_str); 
        if m_ch: channel = m_ch.group(1)
        m_by = re.search(r'By:([^\s|]+)', detail_str); 
        if m_by: who = m_by.group(1)
        m_items = re.search(r'Items:(.*?)(?:\||$)', detail_str); 
        if m_items: 
            raw_items = m_items.group(1).strip()
            if sku_map:
                translated = []
                for it in raw_items.split(','):
                    it = it.strip()
                    if ' x' in it:
                        sk = it.split(' x')[0]; qt = it.split(' x')[1]
                        nm = sku_map.get(sk, sk); translated.append(f"{nm} x{qt}")
                items_str = "、".join(translated)
            else: items_str = raw_items
        parts = detail_str.split('|')
        if len(parts) >= 4: note = parts[2].strip(); pay = parts[3].strip()
        return total, items_str, note, pay, channel, who
    except: return '0', detail_str, '-', '-', '-', '-'

def calculate_realized_revenue(logs_df):
    total = 0
    if logs_df.empty: return 0
    sales = logs_df[logs_df['Action'] == 'Sale']
    for _, row in sales.iterrows():
        try: total += int(re.search(r'Total:\$(\d+)', row['Details']).group(1))
        except: pass
    return total

@st.cache_data(ttl=3600)
def get_live_rate():
    try:
        return requests.get("https://api.exchangerate-api.com/v4/latest/CNY", timeout=5).json()['rates']['TWD'], True
    except: return 4.50, False

def render_navbar(user_initial):
    d = datetime.utcnow() + timedelta(hours=8)
    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:15px;background:#fff;border-bottom:1px solid #eee;margin-bottom:15px;'><div><span style='font-size:18px;font-weight:900;'>IFUKUK GLOBAL</span><br><span style='font-size:11px;color:#666;'>{d.strftime('%Y/%m/%d')}</span></div><div style='width:36px;height:36px;background:#111;color:#fff;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:bold;'>{user_initial}</div></div>", unsafe_allow_html=True)

# ==========================================
# 🗓️ 排班模組 (V103.22: 完整功能回歸)
# ==========================================
def get_staff_color(name):
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6366F1", "#14B8A6", "#F97316"]
    return colors[sum(ord(c) for c in str(name)) % len(colors)]

def render_roster_system(sh, users_list):
    ws_shifts = get_worksheet_safe(sh, "Shifts", SHIFT_HEADERS)
    shifts_df = get_data_robust(ws_shifts, SHIFT_HEADERS)
    
    if not shifts_df.empty:
        if 'Shift_Type' in shifts_df.columns: shifts_df = shifts_df.rename(columns={'Shift_Type': 'Type'})
        if 'Type' not in shifts_df.columns: shifts_df['Type'] = '正常班'

    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班與管理中心</h3></div>", unsafe_allow_html=True)
    
    # 批次排班
    with st.expander("⚡ 智慧批次排班 (Date Range)", expanded=True):
        with st.form("batch_roster"):
            c1, c2, c3 = st.columns(3)
            b_type = c1.selectbox("班別/狀態", ["正常班", "早班", "晚班", "全班", "公休", "特休", "空班", "代班"])
            b_staff = c2.selectbox("人員", users_list, disabled=(b_type=="公休"))
            b_dates = c3.date_input("日期範圍", [])
            b_note = st.text_input("備註 (選填)")
            
            if st.form_submit_button("🚀 執行批次排班", type="primary"):
                if len(b_dates) == 2:
                    start_d, end_d = b_dates
                    delta = end_d - start_d
                    final_staff = "店休" if b_type == "公休" else b_staff
                    
                    for i in range(delta.days + 1):
                        curr_d = (start_d + timedelta(days=i)).strftime("%Y-%m-%d")
                        all_vals = ws_shifts.get_all_values()
                        rows_to_del = [idx+1 for idx, v in enumerate(all_vals) if len(v)>1 and v[0]==curr_d and (v[1]==final_staff or b_type=="公休")]
                        for r_idx in reversed(rows_to_del): ws_shifts.delete_rows(r_idx)
                        ws_shifts.append_row([curr_d, final_staff, b_type, b_note, "FALSE", st.session_state['user_name']])
                    
                    st.cache_data.clear(); st.success(f"已排入 {delta.days+1} 天"); time.sleep(1); st.rerun()
                else: st.error("請選擇完整日期")

    # 日曆
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
                        nm = r['Staff']; tp = r['Type']
                        if tp == "公休" or nm == "店休":
                            bg = "#EF4444"; text = "⛔ 店休"
                        elif tp == "特休":
                            bg = "#F59E0B"; text = f"{nm} (特)"
                        elif tp == "空班":
                            bg = "#9CA3AF"; text = f"{nm} (空)"
                        else:
                            bg = get_staff_color(nm); text = f"{nm} ({tp})"
                        
                        badges += f"<span class='shift-tag' style='background:{bg}'>{text}</span>"
                    
                    if st.button(f"{day}", key=f"c_{date_str}", use_container_width=True):
                        st.session_state['roster_date'] = date_str; st.rerun()
                    st.markdown(f"<div style='min-height:40px;text-align:center;line-height:1.2;'>{badges}</div>", unsafe_allow_html=True)
                else: st.markdown("<div style='min-height:60px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # 編輯與統計
    c_edit, c_stat = st.columns([1, 1])
    
    with c_edit:
        if 'roster_date' in st.session_state:
            t_date = st.session_state['roster_date']
            st.info(f"編輯: {t_date}")
            with st.form("single_roster"):
                c1, c2, c3 = st.columns(3)
                s_type = c1.selectbox("狀態", ["正常班", "早班", "晚班", "全班", "公休", "特休", "空班", "代班"], key="s_tp")
                s_staff = c2.selectbox("人員", users_list, key="s_st", disabled=(s_type=="公休"))
                s_note = c3.text_input("備註", key="s_nt")
                
                if st.form_submit_button("➕ 排入單日"):
                    final_s = "店休" if s_type == "公休" else s_staff
                    all_vals = ws_shifts.get_all_values()
                    rows_to_del = [idx+1 for idx, v in enumerate(all_vals) if len(v)>1 and v[0]==t_date and (v[1]==final_s or s_type=="公休")]
                    for r_idx in reversed(rows_to_del): ws_shifts.delete_rows(r_idx)
                    
                    ws_shifts.append_row([t_date, final_s, s_type, s_note, "FALSE", st.session_state['user_name']])
                    st.cache_data.clear(); st.success("OK"); st.rerun()
            
            curr = shifts_df[shifts_df['Date'] == t_date] if not shifts_df.empty else pd.DataFrame()
            if not curr.empty:
                for _, r in curr.iterrows():
                    col1, col2 = st.columns([4,1])
                    col1.write(f"**{r['Staff']}** - {r['Type']}")
                    if col2.button("🗑️", key=f"del_{t_date}_{r['Staff']}"):
                        all_v = ws_shifts.get_all_values()
                        for idx, v in enumerate(all_v):
                            if len(v)>1 and v[0]==t_date and v[1]==r['Staff']: ws_shifts.delete_rows(idx+1); break
                        st.cache_data.clear(); st.rerun()
    
    with c_stat:
        st.markdown(f"##### 📊 {sel_month}月 班表統計與複製")
        if not shifts_df.empty:
            m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
            m_data = shifts_df[shifts_df['Date'].str.startswith(m_prefix)].sort_values('Date')
            
            if not m_data.empty:
                # 統計
                counts = m_data[~m_data['Type'].isin(['公休','空班','特休'])].groupby('Staff').size()
                st.dataframe(counts.reset_index(name="上班天數"), use_container_width=True, hide_index=True)
                
                # 複製文字生成
                copy_text = f"【{sel_month}月班表】\n"
                for _, r in m_data.iterrows():
                    copy_text += f"{r['Date'][5:]} {r['Staff']} ({r['Type']})\n"
                
                st.text_area("📋 班表文字版 (可複製)", value=copy_text, height=150)
            else: st.caption("本月無資料")

# --- 主程式 ---
def main():
    # 1. 狀態初始化 (修復圖1錯誤)
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False; st.session_state['user_name'] = ""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    # [FIXED] 確保分頁變數已定義
    for k in ['page_num_pos', 'page_num_inv', 'page_num_int', 'page_num_trans']:
        if k not in st.session_state: st.session_state[k] = 0
    
    if 'exchange_rate' not in st.session_state:
        l_rate, succ = get_live_rate()
        st.session_state['exchange_rate'] = l_rate
        st.session_state['rate_source'] = "Live API" if succ else "Manual"

    sh = init_db()
    if not sh: st.error("資料庫連線失敗 (Connection Error)"); return

    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", LOG_HEADERS)
    ws_users = get_worksheet_safe(sh, "Users", USER_HEADERS)

    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><br><h1 style='text-align:center'>IFUKUK</h1><p style='text-align:center'>OMEGA V103.22 TITANIUM</p>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("帳號 (ID)"); p = st.text_input("密碼 (Password)", type="password")
                if st.form_submit_button("登入 (LOGIN)", type="primary"):
                    with st.spinner("安全登入中..."):
                        udf = get_data_robust(ws_users, USER_HEADERS)
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
    df = get_data_robust(ws_items, SHEET_HEADERS)
    for c in ["Qty","Price","Cost","Orig_Cost","Qty_CN"]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    
    sku_translator = {}
    if not df.empty: sku_translator = dict(zip(df['SKU'], df['Name'] + " (" + df['Size'] + ")"))

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
            
            total_items = len(vdf); total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
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
                            if st.button("➕ 加入", key=f"pos_add_{item['SKU']}"):
                                st.session_state['pos_cart'].append({"sku":item['SKU'],"name":item['Name'],"size":item['Size'],"price":item['Price'],"qty":1,"subtotal":item['Price']})
                                st.toast(f"已加入")
                st.markdown("<div class='pagination-container'>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1, 2, 1])
                if c1.button("⬅️", key="pos_p", disabled=st.session_state['page_num_pos']==0): st.session_state['page_num_pos'] -= 1; st.rerun()
                c2.markdown(f"<div style='text-align:center'>P {st.session_state['page_num_pos']+1}/{total_pages}</div>", unsafe_allow_html=True)
                if c3.button("➡️", key="pos_n", disabled=st.session_state['page_num_pos']>=total_pages-1): st.session_state['page_num_pos'] += 1; st.rerun()
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
                        if c_d.button("x", key=f"rm_{idx}"): st.session_state['pos_cart'].pop(idx); st.rerun()
                    st.markdown("---")
                    if st.button("🗑️ 清空購物車", use_container_width=True): st.session_state['pos_cart']=[]; st.rerun()
                    
                    st.markdown("###### 💰 結帳設定")
                    c_d1, c_d2 = st.columns(2)
                    disc = c_d1.radio("折扣", ["無", "7折", "8折", "自訂"], horizontal=True)
                    cust = c_d2.number_input("折數 %", 1, 100, 95) if disc=="自訂" else 0
                    
                    # [Fix] 組合價回歸
                    use_bundle = st.checkbox("啟用組合價")
                    b_val = st.number_input("組合總額", value=base) if use_bundle else base
                    
                    final = int(round(b_val * 0.7)) if disc=="7折" else (int(round(b_val * 0.8)) if disc=="8折" else (int(round(b_val * (cust/100))) if disc=="自訂" else b_val))
                    st.markdown(f"<div class='final-price-box'>實收: ${final}</div>", unsafe_allow_html=True)
                    
                    c_ch, c_who = st.columns(2)
                    sale_ch = c_ch.selectbox("銷售通路", ["門市", "官網", "直播", "網路", "其他"])
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
                            log_event(ws_logs, who, "Sale", f"Total:${final} | Items: {','.join(items)} | {note} | {pay} | Ch:{sale_ch} | By:{who}")
                            st.session_state['pos_cart']=[]; st.cache_data.clear(); st.success("結帳完成"); time.sleep(1); st.rerun()
                else: st.info("購物車是空的")
                st.markdown("</div>", unsafe_allow_html=True)
            
            st.divider()
            st.markdown("##### 🧾 銷售紀錄 (可撤銷/編輯)")
            logs_df = get_data_robust(ws_logs, LOG_HEADERS)
            if not logs_df.empty:
                raw_sales = logs_df[logs_df['Action']=='Sale'].head(15).copy()
                if not raw_sales.empty:
                    parsed_data = []
                    for idx, row in raw_sales.iterrows():
                        t, i, n, p, c, w = parse_sales_details_smart(row['Details'], sku_translator)
                        parsed_data.append({"ID": idx, "時間": row['Timestamp'], "經手人": w, "通路": c, "付款": p, "內容": i, "金額": t, "備註": n})
                    
                    pdf = pd.DataFrame(parsed_data)
                    st.dataframe(pdf, use_container_width=True)
                    
                    c_rev, c_ed = st.columns(2)
                    with c_rev:
                        rev_idx = st.selectbox("撤銷ID", ["..."] + pdf['ID'].astype(str).tolist())
                        if rev_idx != "..." and st.button("❌ 撤銷"):
                            target_row = logs_df.loc[int(rev_idx)]
                            try:
                                items_part = re.search(r'Items:(.*?)(?:\||$)', target_row['Details']).group(1)
                                for it in items_part.split(','):
                                    sk = it.split(' x')[0].strip(); qt = int(it.split(' x')[1])
                                    c = ws_items.find(sk); update_cell_retry(ws_items, c.row, 5, int(ws_items.cell(c.row, 5).value)+qt)
                                ws_logs.delete_rows(int(rev_idx) + 2); st.cache_data.clear(); st.rerun()
                            except: st.error("失敗")
                    with c_ed:
                        ed_idx = st.selectbox("編輯ID", ["..."] + pdf['ID'].astype(str).tolist(), key="pos_ed")
                        if ed_idx != "...":
                            cur_r = pdf[pdf['ID']==int(ed_idx)].iloc[0]
                            n_ch = st.selectbox("新通路", ["門市", "官網", "直播", "網路", "其他"], index=["門市", "官網", "直播", "網路", "其他"].index(cur_r['通路']) if cur_r['通路'] in ["門市", "官網", "直播", "網路", "其他"] else 0)
                            n_note = st.text_input("新備註", cur_r['備註'])
                            n_pay = st.text_input("新付款", cur_r['付款'])
                            if st.button("💾 保存"):
                                raw_detail = logs_df.loc[int(ed_idx)]['Details']
                                items_part = re.search(r'Items:(.*?)(?:\||$)', raw_detail).group(1)
                                new_d = f"Total:${cur_r['金額']} | Items:{items_part} | {n_note} | {n_pay} | Ch:{n_ch} | By:{cur_r['經手']}"
                                ws_logs.update_cell(int(ed_idx) + 2, 4, new_d); st.cache_data.clear(); st.success("Saved"); st.rerun()

    # --- 2. 庫存 ---
    elif nav == "📊 庫存總覽":
        st.subheader("📦 庫存清單")
        m1, m2 = st.columns(2)
        m1.metric("TW 總庫存", df['Qty'].sum())
        m2.metric("CN 總庫存", df['Qty_CN'].sum())
        
        df_display = df.rename(columns={"SKU": "貨號", "Name": "品名", "Category": "分類", "Size": "尺寸", "Qty": "台灣庫存", "Qty_CN": "中國庫存", "Price": "售價", "Cost": "成本", "Orig_Cost": "原幣成本", "Last_Updated": "更新時間", "Safety_Stock": "安全水位", "Orig_Currency": "幣別"})
        
        tot = len(df); tot_p = math.ceil(tot/20)
        c1, c2, c3 = st.columns([1,2,1])
        if c1.button("⬅️", key="ip", disabled=st.session_state['page_num_inv']==0): st.session_state['page_num_inv']-=1; st.rerun()
        c2.markdown(f"<div style='text-align:center'>{st.session_state['page_num_inv']+1}/{tot_p}</div>", unsafe_allow_html=True)
        if c3.button("➡️", key="in", disabled=st.session_state['page_num_inv']>=tot_p-1): st.session_state['page_num_inv']+=1; st.rerun()
        
        start = st.session_state['page_num_inv']*20
        cols = [c for c in df_display.columns if c not in ["Image_URL", "Safety_Stock", "Orig_Currency"]]
        st.dataframe(df_display.iloc[start:start+20][cols], use_container_width=True)

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
        logs_df = get_data_robust(ws_logs, LOG_HEADERS)
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
            st.markdown("##### 🔥 熱銷 Top 10")
            top = df.groupby('Name')['Qty'].sum().sort_values(ascending=False).head(10).reset_index()
            fig2 = px.bar(top, x='Qty', y='Name', orientation='h', text='Qty')
            st.plotly_chart(fig2, use_container_width=True)

    # --- 5. 領用 ---
    elif nav == "🎁 領用/稽核":
        st.subheader("🎁 領用管理")
        logs_df = get_data_robust(ws_logs, LOG_HEADERS)
        int_logs = logs_df[logs_df['Action']=='Internal_Use'].copy() if not logs_df.empty else pd.DataFrame()
        
        if not int_logs.empty:
            def extract_beneficiary(detail):
                try: return detail.split('|')[1].strip()
                except: return "未知"
            int_logs['Real_User'] = int_logs['Details'].apply(extract_beneficiary)
            total_int = len(int_logs)
            st.markdown(f"""<div style='display:flex; gap:10px; margin-bottom:10px;'><div class='audit-stat-box' style='flex:1;'><div class='audit-num'>{total_int}</div><div class='audit-txt'>總領用筆數</div></div></div>""", unsafe_allow_html=True)
            with st.expander("🏆 領用統計", expanded=True):
                st.dataframe(int_logs['Real_User'].value_counts().reset_index(name='筆數'), use_container_width=True)

        st.markdown("##### ➕ 新增領用")
        c1, c2 = st.columns([3, 2])
        with c1:
            q = st.text_input("搜尋")
            idf = df[df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)] if q else df.head(10)
            
            for _, r in idf.iterrows():
                if st.button(f"{r['Name']} ({r['Size']})", key=f"int_{r['SKU']}"): st.session_state['int_t']=r['SKU']
            
            c_p1, c_p2, c_p3 = st.columns([1,2,1])
            if c_p1.button("⬅️", key="ip_p", disabled=st.session_state['page_num_int']==0): st.session_state['page_num_int']-=1; st.rerun()
            c_p2.markdown(f"<div style='text-align:center'>{st.session_state['page_num_int']+1}</div>", unsafe_allow_html=True)
            if c_p3.button("➡️", key="ip_n"): st.session_state['page_num_int']+=1; st.rerun()

        with c2:
            if 'int_t' in st.session_state:
                sku = st.session_state['int_t']; row = df[df['SKU']==sku].iloc[0]
                st.info(f"選中: {row['Name']} ({row['Size']})")
                with st.form("int"):
                    q = st.number_input("量", 1); w = st.selectbox("人", ws_users.col_values(1)[1:] if ws_users else [])
                    r = st.selectbox("因", ["公務制服","福利","樣品","報廢","其他"]); n = st.text_input("註")
                    if st.form_submit_button("執行"):
                        c = ws_items.find(sku); update_cell_retry(ws_items, c.row, 5, int(df[df['SKU']==sku].iloc[0]['Qty'])-q)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{sku} -{q} | {w} | {r} | {n}")
                        st.cache_data.clear(); st.rerun()
        
        st.divider()
        if not int_logs.empty:
            int_disp = int_logs.reset_index()[['index','Timestamp','Details','Real_User']]
            st.dataframe(int_disp, use_container_width=True)
            c_del, c_ed = st.columns(2)
            with c_del:
                did = st.selectbox("刪除ID", ["..."]+int_disp['index'].astype(str).tolist())
                if did!="..." and st.button("刪除"):
                    tr = logs_df.loc[int(did)]; d = tr['Details']
                    sk = d.split(' -')[0].strip(); q = int(d.split(' -')[1].split(' |')[0])
                    c = ws_items.find(sk); update_cell_retry(ws_items, c.row, 5, int(ws_items.cell(c.row, 5).value)+q)
                    ws_logs.delete_rows(int(did)+2); st.cache_data.clear(); st.rerun()
            with c_ed:
                eid = st.selectbox("編輯ID", ["..."]+int_disp['index'].astype(str).tolist(), key="ie")
                if eid!="...":
                    rw = logs_df.loc[int(eid)]; dt = rw['Details'].split('|')
                    nq = st.number_input("新數量", value=int(dt[0].split(' -')[1]))
                    nn = st.text_input("新備註", value=dt[3].strip())
                    if st.button("更新"):
                        sk = dt[0].split(' -')[0].strip(); oq = int(dt[0].split(' -')[1])
                        c = ws_items.find(sk); update_cell_retry(ws_items, c.row, 5, int(ws_items.cell(c.row, 5).value) - (nq-oq))
                        new_dt = f"{sk} -{nq} | {dt[1]} | {dt[2]} | {nn}"
                        ws_logs.update_cell(int(eid)+2, 4, new_dt); st.cache_data.clear(); st.rerun()

    # --- 6. 管理 ---
    elif nav == "👔 矩陣管理":
        t1, t2, t3 = st.tabs(["新增", "調撥", "刪除"])
        with t1:
            with st.form("add"):
                c1, c2 = st.columns(2); bs = c1.text_input("Base SKU"); nm = c2.text_input("品名")
                c3, c4 = st.columns(2); pr = c3.number_input("售價", 0); co = c4.number_input("成本", 0)
                cur = st.selectbox("幣別", ["TWD", "CNY"]); cat = st.selectbox("分類", CAT_LIST)
                sz = {}; cols = st.columns(5)
                for i, s in enumerate(SIZE_ORDER): sz[s] = cols[i%5].number_input(s, min_value=0)
                if st.form_submit_button("寫入"):
                    fc = int(co * st.session_state['exchange_rate']) if cur == "CNY" else co
                    for s, q in sz.items():
                        if q>0: ws_items.append_row([f"{bs}-{s}", nm, cat, s, q, pr, fc, get_taiwan_time_str(), "", 5, cur, co, 0])
                    st.cache_data.clear(); st.success("OK"); st.rerun()
        with t2:
            st.markdown("#### 視覺調撥")
            q = st.text_input("調撥搜尋")
            vdf = df.copy()
            if q: vdf = vdf[vdf.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
            
            tot = len(vdf); pages = math.ceil(tot/ITEMS_PER_PAGE)
            if st.session_state['page_num_trans'] >= pages: st.session_state['page_num_trans'] = 0
            start = st.session_state['page_num_trans'] * ITEMS_PER_PAGE
            page_df = vdf.iloc[start : start + ITEMS_PER_PAGE]
            
            for _, r in page_df.iterrows():
                with st.container():
                    st.markdown(f"**{r['Name']}** TW:{r['Qty']} CN:{r['Qty_CN']}")
                    if st.button("選取調撥", key=f"tr_{r['SKU']}"): st.session_state['tr_t']=r['SKU']
            
            c_p1, c_p2, c_p3 = st.columns([1,2,1])
            if c_p1.button("⬅️", key="tp_p", disabled=st.session_state['page_num_trans']==0): st.session_state['page_num_trans']-=1; st.rerun()
            c_p2.markdown(f"<div style='text-align:center'>P {st.session_state['page_num_trans']+1}/{pages}</div>", unsafe_allow_html=True)
            if c_p3.button("➡️", key="tp_n", disabled=st.session_state['page_num_trans']>=pages-1): st.session_state['page_num_trans']+=1; st.rerun()

            if 'tr_t' in st.session_state:
                tsku = st.session_state['tr_t']; tr = df[df['SKU']==tsku].iloc[0]
                st.info(f"調撥: {tr['Name']}")
                tq = st.number_input("數量", 1)
                c1, c2 = st.columns(2)
                if c1.button("TW -> CN"):
                    r = ws_items.find(tsku).row
                    update_cell_retry(ws_items, r, 5, int(tr['Qty'])-tq); update_cell_retry(ws_items, r, 13, int(tr['Qty_CN'])+tq)
                    st.cache_data.clear(); st.success("OK"); st.rerun()
                if c2.button("CN -> TW"):
                    r = ws_items.find(tsku).row
                    update_cell_retry(ws_items, r, 5, int(tr['Qty'])+tq); update_cell_retry(ws_items, r, 13, int(tr['Qty_CN'])-tq)
                    st.cache_data.clear(); st.success("OK"); st.rerun()
        with t3:
            st.markdown("#### 刪除")
            q = st.text_input("刪除搜尋")
            ddf = df[df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)] if q else df.head(5)
            for _, r in ddf.iterrows():
                c1, c2 = st.columns([4,1])
                c1.write(f"{r['Name']} ({r['SKU']})")
                if c2.button("🗑️", key=f"d_{r['SKU']}"):
                    ws_items.delete_rows(ws_items.find(r['SKU']).row); st.cache_data.clear(); st.rerun()

    elif nav == "📝 全域日誌":
        q = st.text_input("🔍 搜尋")
        logs = get_data_robust(ws_logs, LOG_HEADERS)
        if not logs.empty:
            if q: logs = logs[logs.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
            logs.columns = ['時間','操作人','動作','詳細']
            st.dataframe(logs.sort_values('時間', ascending=False), use_container_width=True)

    elif nav == "👥 員工管理":
        if st.session_state['user_role']=='Admin':
            st.dataframe(get_data_robust(ws_users, USER_HEADERS))
            with st.form("add"):
                n=st.text_input("ID"); p=st.text_input("PW"); r=st.selectbox("Role", ["Staff","Admin"])
                if st.form_submit_button("新增"): ws_users.append_row([n, make_hash(p), r, "Active", get_taiwan_time_str()]); st.cache_data.clear(); st.rerun()
            d = st.selectbox("刪除", ws_users.col_values(1)[1:] if ws_users else [])
            if st.button("確認刪除"): ws_users.delete_rows(ws_users.find(d).row); st.cache_data.clear(); st.rerun()

    elif nav == "🚪 登出":
        st.session_state['logged_in'] = False; st.rerun()

if __name__ == "__main__":
    main()
