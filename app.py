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

# --- 1. 系統全域設定 (V103.0 Base) ---
st.set_page_config(
    page_title="IFUKUK V103.7 CHRONOS", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【V103.0 原始視覺 + V103.7 排班擴充】
# ==========================================
st.markdown("""
    <style>
        /* --- V103.0 原版樣式保留 --- */
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
        
        /* --- V103.7 新增：專業排班樣式 --- */
        .roster-header {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: white; padding: 15px; border-radius: 12px; margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .day-cell {
            border: 1px solid #e5e7eb; border-radius: 8px; padding: 5px; min-height: 80px;
            background: #fff; position: relative; margin-bottom: 10px; transition: all 0.2s;
        }
        .day-cell:hover { border-color: #3b82f6; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
        .day-num { font-weight: 900; color: #333; font-size: 1.1rem; margin-bottom: 5px; }
        .shift-tag {
            font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; margin-bottom: 2px;
            color: white; font-weight: bold; display: block; text-align: center;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .note-dot {
            position: absolute; top: 5px; right: 5px; width: 8px; height: 8px;
            background-color: #ef4444; border-radius: 50%;
        }
        .notify-bell { font-size: 0.8rem; color: #f59e0b; margin-left: 2px; }
        
        .overview-row {
            padding: 8px; border-bottom: 1px dashed #eee; display: flex; align-items: center; justify-content: space-between;
        }
        .overview-row:hover { background-color: #f8fafc; }
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- 核心連線 (V103.0 Gold) ---
@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=10, show_spinner=False)
def get_data_safe(_ws, expected_headers=None):
    max_retries = 3
    for i in range(max_retries):
        try:
            if _ws is None: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            raw_data = _ws.get_all_values()
            if not raw_data or len(raw_data) < 2: 
                return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            headers = raw_data[0]
            seen = {}; new_headers = []
            for h in headers:
                if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
                else: seen[h] = 0; new_headers.append(h)
            rows = raw_data[1:]
            if "Qty_CN" not in new_headers and expected_headers and "Qty_CN" in expected_headers:
                try: _ws.update_cell(1, len(new_headers)+1, "Qty_CN"); new_headers.append("Qty_CN"); raw_data = _ws.get_all_values(); rows = raw_data[1:]
                except: pass
            df = pd.DataFrame(rows)
            if not df.empty:
                if len(df.columns) < len(new_headers):
                    for _ in range(len(new_headers) - len(df.columns)): df[len(df.columns)] = ""
                df.columns = new_headers[:len(df.columns)]
            return df
        except Exception as e:
            if "429" in str(e): time.sleep(2 ** (i + 1)); continue
            return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
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
        <div style="display:flex; justify-content:space-between; align-items:center; background:#fff; padding:15px; border-bottom:1px solid #eee; margin-bottom:15px;">
            <div>
                <span style="font-size:18px; font-weight:900; color:#111;">IFUKUK GLOBAL</span><br>
                <span style="font-size:11px; color:#666; font-family:monospace;">{date_str} • Rate: {rate}</span>
            </div>
            <div style="width:36px; height:36px; background:#111; color:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold;">
                {user_initial}
            </div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 🗓️ V103.7 專業排班系統 (CHRONOS ROSTER)
# ==========================================
def get_staff_color(name):
    # 為每個人產生固定顏色
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6366F1", "#14B8A6", "#F97316"]
    return colors[sum(ord(c) for c in str(name)) % len(colors)]

def render_roster_system(sh, users_list):
    # 1. 確保 Shifts 表存在 (Date, Staff, Type, Note, Notify, By)
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Type", "Note", "Notify", "Updated_By"])
    shifts_df = get_data_safe(ws_shifts, ["Date", "Staff", "Type", "Note", "Notify", "Updated_By"])
    
    st.markdown("<div class='roster-header'><h3>🗓️ 員工排班與提醒中心</h3></div>", unsafe_allow_html=True)
    
    # 2. 控制台 (年月選擇)
    now = datetime.utcnow() + timedelta(hours=8)
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 2])
    sel_year = col_ctrl1.number_input("年份", 2024, 2030, now.year)
    sel_month = col_ctrl2.selectbox("月份", range(1, 13), now.month)
    
    # 3. 月曆視圖 (The Grid)
    cal = calendar.monthcalendar(sel_year, sel_month)
    month_name = calendar.month_name[sel_month]
    
    # 星期標頭
    cols = st.columns(7)
    days_name = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    for i, d in enumerate(days_name): cols[i].markdown(f"<div style='text-align:center;font-weight:bold;color:#666;'>{d}</div>", unsafe_allow_html=True)
    
    # 日曆內容
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day != 0:
                    date_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    
                    # 篩選當日班表
                    day_shifts = pd.DataFrame()
                    has_note = False
                    if not shifts_df.empty:
                        day_shifts = shifts_df[shifts_df['Date'] == date_str]
                        # 檢查是否有備註
                        if not day_shifts[day_shifts['Note'] != ""].empty: has_note = True
                    
                    # 點擊按鈕 (更新 session state)
                    if st.button(f"{day}", key=f"cal_{date_str}", use_container_width=True):
                        st.session_state['roster_date'] = date_str
                        st.rerun()
                    
                    # 視覺化 Badge (用 HTML 渲染在按鈕下方)
                    badges_html = ""
                    if not day_shifts.empty:
                        for _, r in day_shifts.iterrows():
                            color = get_staff_color(r['Staff'])
                            # 狀態顏色覆蓋
                            if r['Type'] == "公休": color = "#9CA3AF" # Gray
                            elif r['Type'] == "特休": color = "#EF4444" # Red
                            elif r['Type'] == "空班": color = "#F59E0B" # Orange
                            
                            notify_icon = "🔔" if r['Notify'] == "TRUE" else ""
                            badges_html += f"<span class='shift-tag' style='background-color:{color}'>{r['Staff']} {notify_icon}</span>"
                    
                    note_html = "<div class='note-dot'></div>" if has_note else ""
                    st.markdown(f"""
                        <div class='day-cell' style='margin-top:-10px; border:none; background:transparent;'>
                            {note_html}
                            {badges_html}
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # 4. 編輯與檢視區 (Split View)
    c_edit, c_view = st.columns([1, 1.5])
    
    # [左側] 編輯區
    with c_edit:
        if 'roster_date' in st.session_state:
            target_date = st.session_state['roster_date']
            st.markdown(f"#### ✏️ 編輯: {target_date}")
            
            with st.form("add_shift"):
                c1, c2 = st.columns(2)
                s_staff = c1.selectbox("人員", users_list)
                s_type = c2.selectbox("班別/狀態", ["早班", "晚班", "全班", "公休", "特休", "空班", "代班"])
                s_note = st.text_input("備註 (選填)")
                s_notify = st.checkbox("🔔 需要通知 (明天上班提醒)")
                
                if st.form_submit_button("➕ 加入/更新排班", type="primary"):
                    # 刪除舊紀錄 (避免同一人同一天重複)
                    all_vals = ws_shifts.get_all_values()
                    rows_to_del = []
                    for idx, row in enumerate(all_vals):
                        if len(row) > 1 and row[0] == target_date and row[1] == s_staff:
                            rows_to_del.append(idx + 1)
                    for r_idx in reversed(rows_to_del): ws_shifts.delete_rows(r_idx)
                    
                    # 新增
                    ws_shifts.append_row([target_date, s_staff, s_type, s_note, "TRUE" if s_notify else "FALSE", st.session_state['user_name']])
                    st.cache_data.clear() # 強制刷新
                    st.success(f"已排入: {s_staff}")
                    time.sleep(0.5); st.rerun()
            
            # 顯示當日名單 (可刪除)
            curr_day = shifts_df[shifts_df['Date'] == target_date] if not shifts_df.empty else pd.DataFrame()
            if not curr_day.empty:
                st.caption("點擊按鈕移除:")
                for _, r in curr_day.iterrows():
                    col_info, col_btn = st.columns([4, 1])
                    notify_mk = "🔔" if r['Notify'] == "TRUE" else ""
                    col_info.info(f"{r['Staff']} ({r['Type']}) {r['Note']} {notify_mk}")
                    if col_btn.button("🗑️", key=f"del_{target_date}_{r['Staff']}"):
                        all_vals = ws_shifts.get_all_values()
                        for idx, row in enumerate(all_vals):
                            if len(row) > 1 and row[0] == target_date and row[1] == r['Staff']:
                                ws_shifts.delete_rows(idx + 1)
                                break
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.info("👈 請點擊上方日曆日期開始排班")

    # [右側] 總覽與通知生成
    with c_view:
        st.markdown(f"#### 📅 {sel_month}月 排班總覽")
        
        # 篩選本月資料
        if not shifts_df.empty:
            m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
            m_data = shifts_df[shifts_df['Date'].str.startswith(m_prefix)].copy()
            
            if not m_data.empty:
                m_data = m_data.sort_values(['Date', 'Staff'])
                
                # 顯示表格
                st.dataframe(
                    m_data[['Date', 'Staff', 'Type', 'Note', 'Notify']],
                    column_config={
                        "Date": "日期", "Staff": "人員", "Type": "班別", 
                        "Note": "備註", "Notify": "提醒"
                    },
                    use_container_width=True,
                    hide_index=True,
                    height=300
                )
                
                st.markdown("---")
                st.markdown("#### 📢 通知文案生成器")
                st.caption("由於系統無法直接發送 Line，請點擊下方按鈕複製文案，發送至群組。")
                
                # 生成明日通知
                tmr = (datetime.utcnow() + timedelta(hours=8) + timedelta(days=1)).strftime("%Y-%m-%d")
                tmr_shifts = shifts_df[(shifts_df['Date'] == tmr) & (shifts_df['Notify'] == "TRUE")]
                
                if not tmr_shifts.empty:
                    msg = f"【明日上班提醒 {tmr}】\n"
                    for _, r in tmr_shifts.iterrows():
                        msg += f"- {r['Staff']} ({r['Type']}) {r['Note']}\n"
                    msg += "請準時打卡！"
                    st.text_area("複製內容:", value=msg, height=100)
                else:
                    st.info(f"明日 ({tmr}) 無設定需提醒的班表。")
            else:
                st.info("本月尚無排班資料。")
        else:
            st.info("尚無資料。")

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

    # --- 登入頁面 (V103.0 Original) ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-weight:900; font-size:2.5rem; margin-bottom:10px;'>IFUKUK</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>OMEGA V103.7 CHRONOS</div>", unsafe_allow_html=True)
            with st.form("login"):
                user_input = st.text_input("帳號 (ID)")
                pass_input = st.text_input("密碼 (Password)", type="password")
                if st.form_submit_button("登入 (LOGIN)", type="primary"):
                    with st.spinner("Verifying..."):
                        users_df = get_data_safe(ws_users, ["Name", "Password", "Role", "Status", "Created_At"])
                        input_u = str(user_input).strip()
                        input_p = str(pass_input).strip()
                        
                        if users_df.empty and input_u == "Boss" and input_p == "1234":
                            hashed_pw = make_hash("1234")
                            ws_users.append_row(["Boss", hashed_pw, "Admin", "Active", get_taiwan_time_str()])
                            st.cache_data.clear()
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
                        else: st.error("系統連線忙碌 (Protected Mode)")
        return

    # --- 主畫面 ---
    user_initial = st.session_state['user_name'][0].upper()
    render_navbar(user_initial)

    # 讀取數據 (Cache Enabled)
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
            current_rate = st.session_state['exchange_rate']
            new_rate = st.number_input("RMB to TWD", value=current_rate, step=0.01, format="%.2f")
            if new_rate != current_rate:
                st.session_state['exchange_rate'] = new_rate
                st.session_state['rate_source'] = "Manual Override"
            if st.button("🔄 重抓 Live 匯率"):
                live_r, success = get_live_rate()
                st.session_state['exchange_rate'] = live_r; st.rerun()

        st.markdown("---")
        if st.button("🚪 安全登出"):
            log_event(ws_logs, st.session_state['user_name'], "Logout", "登出")
            st.session_state['logged_in'] = False; st.rerun()

    # --- Dashboard ---
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

    # --- Tabs ---
    tabs = st.tabs(["📊 視覺庫存", "🛒 POS", "📈 銷售戰情", "🎁 領用/稽核", "👔 矩陣管理", "📝 日誌", "👥 Admin", "🗓️ 排班"])

    # Tab 1-7: V103.0 Original Logic
    with tabs[0]:
        if not df.empty:
            c_chart1, c_chart2 = st.columns([1, 1])
            with c_chart1:
                fig_pie = px.pie(df, names='Category', values='Qty', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
            with c_chart2:
                top_items = df.groupby(['Style_Code', 'Name']).agg({'Qty':'sum'}).reset_index().sort_values(by='Qty', ascending=False).head(10)
                fig_bar = px.bar(top_items, x='Qty', y='Name', orientation='h', text='Qty', color='Qty', color_continuous_scale='Bluered')
                st.plotly_chart(fig_bar, use_container_width=True)
        
        st.divider()
        st.subheader("📦 庫存區")
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1: search_q = st.text_input("🔍 搜尋商品", placeholder="輸入貨號或品名...")
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
                    c_card_img, c_card_info = st.columns([1, 4])
                    with c_card_img: st.image(img, use_column_width=True)
                    with c_card_info:
                        st.markdown(f"#### {name}"); st.caption(f"貨號: {style_code}"); st.markdown(f"🇹🇼 台灣: **{total_qty_tw}** | 🇨🇳 中國: **{total_qty_cn}** | 售價: ${price}")
                        preview_tags = ""
                        for _, row in sorted_group.iterrows():
                            if row['Qty'] > 0: preview_tags += f"<span class='stock-pill-tw'>{row['Size']}:{row['Qty']}</span> "
                            if row['Qty_CN'] > 0: preview_tags += f"<span class='stock-pill-cn'>{row['Size']}(CN):{row['Qty_CN']}</span> "
                        if preview_tags: st.markdown(preview_tags, unsafe_allow_html=True)
                    with st.expander("📝 管理庫存"):
                        with st.form(f"dyn_form_{style_code}_{name}"):
                            inputs_tw = {}; inputs_cn = {}; grid_cols = st.columns(4)
                            for idx, row in enumerate(sorted_group.iterrows()):
                                _, r_data = row
                                with grid_cols[idx % 4]: 
                                    label = f"{r_data['Size']}"; inputs_tw[r_data['SKU']] = st.number_input(f"🇹🇼 {label}", value=int(r_data['Qty']), key=f"dtw_{r_data['SKU']}")
                                    inputs_cn[r_data['SKU']] = st.number_input(f"🇨🇳 {label}", value=int(r_data['Qty_CN']), key=f"dcn_{r_data['SKU']}")
                            if st.form_submit_button("💾 更新"):
                                for t_sku, new_q_tw in inputs_tw.items():
                                    if t_sku in df['SKU'].tolist():
                                        new_q_cn = inputs_cn[t_sku]; r = ws_items.find(t_sku).row
                                        update_cell_retry(ws_items, r, 5, new_q_tw); update_cell_retry(ws_items, r, 13, new_q_cn); update_cell_retry(ws_items, r, 8, get_taiwan_time_str())
                                st.cache_data.clear(); st.success("Updated"); time.sleep(1); st.rerun()
        else: st.info("無資料")

    with tabs[1]:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("1. 商品選擇")
            sku_opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} ({x['Size']}) | 🇹🇼:{x['Qty']}", axis=1).tolist() if not df.empty else []
            sel_sku = st.selectbox("搜尋商品", ["..."] + sku_opts, key="pos_sel")
            if sel_sku != "...":
                target_sku = sel_sku.split(" | ")[0]; target = df[df['SKU'] == target_sku].iloc[0]; img = render_image_url(target['Image_URL'])
                st.markdown(f"""<div style="border:1px solid #e5e7eb; border-radius:12px; padding:15px; display:flex; align-items:center; background:#f9fafb;"><img src="{img}" style="width:80px; height:80px; object-fit:cover; border-radius:8px; margin-right:15px;"><div><div style="font-weight:bold; font-size:16px;">{target['Name']}</div><div style="color:#666; font-size:12px;">{target['SKU']} ({target['Size']})</div><div style="margin-top:5px; font-weight:bold; color:#059669;">${target['Price']}</div><div style="color:#1e40af; font-weight:bold;">🇹🇼 現貨: {target['Qty']}</div></div></div>""", unsafe_allow_html=True)
                c_add1, c_add2 = st.columns([1, 2]); add_qty = c_add1.number_input("數量", min_value=1, value=1, key="pos_qty")
                if c_add2.button("➕ 加入", type="primary"):
                    st.session_state['pos_cart'].append({"sku": target['SKU'], "name": target['Name'], "size": target['Size'], "price": int(target['Price']), "qty": add_qty, "subtotal": int(target['Price']) * add_qty})
                    st.success("Added"); time.sleep(0.5); st.rerun()
        with c2:
            st.subheader("2. 結帳")
            if len(st.session_state['pos_cart']) > 0:
                total = sum(i['subtotal'] for i in st.session_state['pos_cart'])
                st.markdown("<div class='cart-box'>", unsafe_allow_html=True)
                for i in st.session_state['pos_cart']: st.markdown(f"""<div class="cart-item"><span>{i['name']} ({i['size']}) x{i['qty']}</span><span>${i['subtotal']}</span></div>""", unsafe_allow_html=True)
                if st.button("🗑️ 清空"): st.session_state['pos_cart'] = []; st.rerun()
                st.markdown(f"<div class='cart-total'>${total}</div></div>", unsafe_allow_html=True)
                
                c_d1, c_d2 = st.columns(2); disc = c_d1.radio("折扣", ["無", "7折", "8折", "自訂"], horizontal=True); cust = c_d2.number_input("折數", 1, 100, 95)
                bundle = st.checkbox("組合價"); b_val = st.number_input("組合總價", value=total) if bundle else total
                
                final = b_val
                if disc == "7折": final = int(round(b_val * 0.7))
                elif disc == "8折": final = int(round(b_val * 0.8))
                elif disc == "自訂": final = int(round(b_val * (cust/100)))
                
                st.markdown(f"<div class='final-price-display'>實收: ${final}</div>", unsafe_allow_html=True)
                who = st.selectbox("人員", staff_list); ch = st.selectbox("通路", ["門市", "官網"]); pay = st.selectbox("付款", ["現金", "刷卡"]); note = st.text_input("備註")
                if st.button("✅ 結帳", type="primary", use_container_width=True):
                    items = []
                    for i in st.session_state['pos_cart']:
                        r = ws_items.find(i['sku']).row; curr = int(ws_items.cell(r, 5).value)
                        if curr >= i['qty']: update_cell_retry(ws_items, r, 5, curr - i['qty']); items.append(f"{i['sku']} x{i['qty']}")
                    log_event(ws_logs, st.session_state['user_name'], "Sale", f"Total:${final} | {','.join(items)} | {note} | {pay} | {ch} | {who}")
                    st.session_state['pos_cart'] = []; st.cache_data.clear(); st.success("結帳完成"); time.sleep(2); st.rerun()
            else: st.info("空")

    with tabs[2]:
        sales_data = []
        if not logs_df.empty and 'Action' in logs_df.columns:
            s_logs = logs_df[logs_df['Action'] == 'Sale']
            for _, row in s_logs.iterrows():
                try:
                    total_val = int(re.search(r'Total:\$(\d+)', row['Details']).group(1))
                    sales_data.append({"日期": row['Timestamp'], "金額": total_val, "經手": row['User']})
                except: pass
        sdf = pd.DataFrame(sales_data)
        if not sdf.empty:
            st.markdown(f"#### 總銷售: ${sdf['金額'].sum():,}")
            st.dataframe(sdf, use_container_width=True)
        else: st.info("無數據")

    with tabs[3]:
        st.subheader("內部領用")
        with st.expander("新增領用", expanded=True):
            sel = st.selectbox("商品", ["..."] + (df['SKU'] + " | " + df['Name']).tolist(), key="int_sel")
            if sel != "...":
                tsku = sel.split(" | ")[0]; trow = df[df['SKU'] == tsku].iloc[0]; st.info(f"庫存: {trow['Qty']}")
                with st.form("int"):
                    q = st.number_input("數量", 1); who = st.selectbox("人", staff_list); rsn = st.selectbox("因", ["公務", "報廢"]); n = st.text_input("備註")
                    if st.form_submit_button("執行"):
                        r = ws_items.find(tsku).row; update_cell_retry(ws_items, r, 5, int(trow['Qty']) - q)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{tsku} -{q} | {who} | {rsn} | {n}")
                        st.cache_data.clear(); st.success("OK"); st.rerun()
        logs = get_data_safe(ws_logs); 
        if not logs.empty and 'Action' in logs.columns: st.dataframe(logs[logs['Action']=="Internal_Use"], use_container_width=True)

    with tabs[4]:
        st.subheader("矩陣管理")
        mt1, mt2 = st.tabs(["新增", "調撥"])
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
                        if q > 0: ws_items.append_row([f"{bs}-{s}", nm, "New", s, q, pr, fc, get_taiwan_time_str(), url, 5, cur, co, 0])
                    st.cache_data.clear(); st.success("完成"); st.rerun()
        with mt2:
            sel = st.selectbox("調撥", ["..."] + df['SKU'].tolist())
            if sel != "...":
                row = df[df['SKU']==sel].iloc[0]; st.write(f"TW: {row['Qty']} | CN: {row['Qty_CN']}"); q = st.number_input("量", 1)
                c1, c2 = st.columns(2)
                if c1.button("TW->CN"): 
                    r = ws_items.find(sel).row; update_cell_retry(ws_items, r, 5, int(row['Qty'])-q); update_cell_retry(ws_items, r, 13, int(row['Qty_CN'])+q); st.cache_data.clear(); st.success("OK"); st.rerun()
                if c2.button("CN->TW"):
                    r = ws_items.find(sel).row; update_cell_retry(ws_items, r, 5, int(row['Qty'])+q); update_cell_retry(ws_items, r, 13, int(row['Qty_CN'])-q); st.cache_data.clear(); st.success("OK"); st.rerun()

    with tabs[5]:
        st.dataframe(logs_df, use_container_width=True)
    with tabs[6]:
        st.dataframe(users_df, use_container_width=True)

    # --- Tab 8: 新增的排班系統 (CHRONOS) ---
    with tabs[7]:
        render_roster_system(sh, staff_list)

if __name__ == "__main__":
    main()
