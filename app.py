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
    page_title="IFUKUK ERP V110.0 QUANTUM HARDENED", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【CSS 視覺核心：強制白底黑字 & 手機優化】
# ==========================================
st.markdown("""
    <style>
        /* 1. 強制全域白底黑字 (無視手機深色模式) */
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; }
        [data-testid="stHeader"] { background-color: #FFFFFF !important; }
        
        /* 2. 強制輸入框、選單文字顏色 */
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {
            color: #000000 !important; background-color: #FFFFFF !important;
            -webkit-text-fill-color: #000000 !important; caret-color: #000000 !important;
            border-color: #E5E7EB !important;
        }
        div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #000000 !important; }
        label, .stMarkdown, h1, h2, h3, h4, h5, h6, p, span { color: #0f172a !important; }

        /* 3. 優化卡片視覺 */
        .pos-card, .inv-row, .finance-card, .metric-card, .cart-box, .mgmt-box {
            background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important; color: #000000 !important;
        }
        
        .pos-img { width: 100%; height: 160px; object-fit: cover; background: #f9fafb; border-bottom: 1px solid #f3f4f6; }
        .pos-content { padding: 10px; flex-grow: 1; display: flex; flex-direction: column; }
        .pos-title { font-weight: bold; font-size: 1rem; margin-bottom: 4px; color: #111 !important; line-height: 1.3; }
        .pos-meta { font-size: 0.8rem; color: #666 !important; margin-bottom: 5px; }
        
        .stock-tag-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; margin-bottom: 5px; }
        .stock-tag { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; border: 1px solid transparent; }
        .stock-tag.has-stock { background-color: #dcfce7 !important; color: #166534 !important; border-color: #bbf7d0; }
        .stock-tag.no-stock { background-color: #f3f4f6 !important; color: #9ca3af !important; border-color: #e5e7eb; }
        
        .inv-row { display: flex; align-items: start; gap: 12px; padding: 12px; border-radius: 12px; margin-bottom: 10px; }
        .inv-img { width: 90px; height: 90px; object-fit: cover; border-radius: 8px; flex-shrink: 0; background: #f1f5f9; }
        .inv-info { flex-grow: 1; }
        .inv-title { font-size: 1.1rem; font-weight: bold; color: #0f172a !important; margin-bottom: 4px; }
        
        .finance-card { padding: 15px; text-align: center; border-radius: 10px; }
        .finance-val { font-size: 1.4rem; font-weight: 900; color: #0f172a !important; }
        .finance-lbl { font-size: 0.8rem; color: #64748b !important; font-weight: bold; }

        .roster-header { background: #f1f5f9 !important; padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e2e8f0; text-align: center; }
        .day-cell { border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; min-height: 100px; position: relative; margin-bottom: 5px; background: #fff !important; }
        .day-num { font-size: 0.8rem; font-weight: bold; color: #64748b; margin-bottom: 2px; padding-left: 4px; }
        
        .mobile-day-row { background: #FFFFFF !important; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }
        .mobile-day-date { font-size: 1.1rem; font-weight: 900; color: #334155 !important; width: 50px; text-align: center; border-right: 2px solid #f1f5f9; margin-right: 10px; }
        .mobile-day-content { flex-grow: 1; }
        
        .shift-pill { font-size: 0.75rem; padding: 4px 8px; border-radius: 6px; margin-bottom: 4px; color: white !important; display: inline-block; text-align: center; font-weight: bold; margin-right: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .store-closed { background-color: #EF4444 !important; color: white !important; font-weight: 900; font-size: 0.9rem; display: flex; align-items: center; justify-content: center; height: 100%; border-radius: 6px; min-height: 90px; }
        .store-closed-mobile { background-color: #FEF2F2 !important; color: #EF4444 !important; border: 1px solid #FCA5A5; padding: 5px 10px; border-radius: 6px; font-weight: bold; display: inline-block; }
        
        .metric-card { background: linear-gradient(145deg, #ffffff, #f8fafc) !important; color: black !important; }
        .metric-value { color: #0f172a !important; }
        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border: 1px solid #cbd5e1; background-color: #FFFFFF !important; color: #0f172a !important; width: 100%; }
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
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if any(err in str(e) for err in ["429", "Quota exceeded", "1006", "500", "503", "502"]):
                wait_time = (1.5 ** i) + random.uniform(0.5, 1.5)
                if i > 2: st.toast(f"⏳ 雲端連線忙碌中... 自動重試 ({i+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                raise e
    st.error("❌ 雲端同步失敗，請檢查網路。")
    return None

@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=10, show_spinner=False)
def get_data_safe(_ws, expected_headers=None):
    if _ws is None: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
    for attempt in range(5):
        try:
            raw_data = _ws.get_all_values()
            if not raw_data or len(raw_data) < 2: 
                return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            
            headers = raw_data[0]
            seen = {}; new_headers = []
            for h in headers:
                if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
                else: seen[h] = 0; new_headers.append(h)
            
            rows = raw_data[1:]
            df = pd.DataFrame(rows)
            
            # QUANTUM FIX: 補齊可能缺失的欄位
            if expected_headers:
                for col in expected_headers:
                    if col not in new_headers:
                        df[col] = ""
                        new_headers.append(col)
                        
            df.columns = new_headers[:len(df.columns)]
            
            # QUANTUM FIX: 核心數據清洗 (殺死所有空行幽靈數據)
            if 'SKU' in df.columns:
                df['SKU'] = df['SKU'].astype(str).str.strip()
                df = df[df['SKU'] != '']
                
            return df
        except Exception as e:
            time.sleep(1.5 ** (attempt + 1))
            continue
    return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()

@st.cache_resource(ttl=600)
def init_db():
    try: return get_connection().open_by_url(GOOGLE_SHEET_URL)
    except: return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        try:
            ws = sh.add_worksheet(title, rows=100, cols=20)
            ws.append_row(headers)
            return ws
        except: return None
    except Exception:
        try:
            time.sleep(2)
            return init_db().worksheet(title)
        except: return None

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
    if not url_input or pd.isna(url_input): return "https://i.ibb.co/W31w56W/placeholder.png"
    s = str(url_input).strip()
    return s if len(s) > 10 and s.startswith("http") else "https://i.ibb.co/W31w56W/placeholder.png"

def upload_image_to_imgbb(image_file):
    if not IMGBB_API_KEY: return None
    try:
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(image_file.getvalue()).decode('utf-8')}
        r = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if r.status_code == 200: return r.json()["data"]["url"]
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
            # QUANTUM FIX: 寬容的正則表達式，防止手動修改導致計算崩潰
            match = re.search(r'Total:\s*\$?\s*(\d+)', str(row['Details']))
            if match: total += int(match.group(1))
        except: pass
    return total

def render_navbar(user_initial):
    d_str = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y/%m/%d")
    rate = st.session_state.get('exchange_rate', 4.5)
    st.markdown(f"""
        <div class="navbar-container">
            <div style="display:flex; justify-content:space-between; align-items:center; background:#fff; padding:15px; border-bottom:1px solid #eee; margin-bottom:15px;">
                <div>
                    <span style="font-size:18px; font-weight:900; color:#111;">IFUKUK GLOBAL</span><br>
                    <span style="font-size:11px; color:#666; font-family:monospace;">{d_str} • Rate: {rate}</span>
                </div>
                <div style="width:36px; height:36px; background:#111; color:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold;">
                    {user_initial}
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]

# ==========================================
# 🗓️ 排班系統 ELITE (Module Rewrite V110.0)
# ==========================================
SHIFT_COLORS = { "早班": "#3B82F6", "晚班": "#8B5CF6", "全班": "#10B981", "代班": "#F59E0B", "公休": "#EF4444", "特休": "#DB2777", "空班": "#6B7280", "事假": "#EC4899", "病假": "#14B8A6" }

def get_staff_color_map(users_list):
    PALETTE = ["#2563EB", "#059669", "#7C3AED", "#DB2777", "#D97706", "#DC2626", "#0891B2", "#4F46E5", "#BE123C", "#B45309"]
    return {u: PALETTE[i % len(PALETTE)] for i, u in enumerate(sorted([x for x in users_list if x != "全店"]))}

def get_chinese_font_path():
    # QUANTUM FIX: 絕對掛載在 /tmp/ 防止 Streamlit 唯讀崩潰
    font_filename = "/tmp/NotoSansTC-Regular.otf"
    if not os.path.exists(font_filename):
        url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
        try:
            r = requests.get(url, timeout=10)
            with open(font_filename, 'wb') as f: f.write(r.content)
        except: return None
    return font_filename

def generate_roster_image_buffer(year, month, shifts_df, days_in_month, color_map):
    try:
        font_path = get_chinese_font_path()
        prop = fm.FontProperties(fname=font_path) if font_path else fm.FontProperties()
        
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.axis('off')
        
        ax.text(0.5, 0.96, f"IFUKUK Roster - {year}/{month}", ha='center', va='center', fontsize=22, weight='bold', fontproperties=prop)
        
        cols = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cal = calendar.monthcalendar(year, month)
        table_data = [cols]
        
        for week in cal:
            row_data = []
            for day in week:
                if day == 0: row_data.append("")
                else:
                    date_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == date_str]
                    
                    is_closed = any((r['Staff'] == "全店" and r['Type'] == "公休") for _, r in day_shifts.iterrows())
                    
                    cell_text = f"{day}\n"
                    if is_closed: cell_text += "\n[全店公休]\nStore Closed"
                    else:
                        for _, r in day_shifts.iterrows():
                            s_short = r['Type'].replace("早班","早").replace("晚班","晚").replace("全班","全").replace("公休","休")
                            cell_text += f"{r['Staff']} ({s_short})\n"
                    row_data.append(cell_text)
            table_data.append(row_data)

        table = ax.table(cellText=table_data, loc='center', cellLoc='left', bbox=[0, 0, 1, 0.9])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        
        for (i, j), cell in table.get_celld().items():
            if i == 0:
                cell.set_text_props(weight='bold', fontproperties=prop)
                cell.set_facecolor('#f3f4f6')
                cell.set_height(0.05)
            else:
                cell.set_height(0.15)
                cell.set_valign('top')
                cell.set_text_props(fontproperties=prop)
                if "全店公休" in cell.get_text().get_text():
                    cell.set_facecolor('#FECACA')
                    cell.get_text().set_color('#991B1B')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0); plt.close(fig)
        return buf
    except Exception as e: return None

def render_roster_system(sh, users_list, user_name):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    if ws_shifts is None:
        st.warning("⚠️ 系統連線中，請稍候重新整理...")
        return

    shifts_df = get_data_safe(ws_shifts, ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    if not shifts_df.empty:
        if 'Shift_Type' in shifts_df.columns and 'Type' not in shifts_df.columns: shifts_df['Type'] = shifts_df['Shift_Type']
        if 'Type' not in shifts_df.columns: shifts_df['Type'] = '上班'
    else:
        shifts_df = pd.DataFrame(columns=["Date", "Staff", "Type", "Note", "Notify", "Updated_By"])

    staff_color_map = get_staff_color_map(users_list)
    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班中心 MOBILE SUPREMACY</h3></div>", unsafe_allow_html=True)
    now = datetime.utcnow() + timedelta(hours=8)
    
    with st.container():
        c_ctrl1, c_ctrl2 = st.columns([1.5, 1])
        with c_ctrl1:
            c_y, c_m = st.columns(2)
            sel_year = c_y.number_input("年份", 2024, 2030, now.year, label_visibility="collapsed")
            month_map = {1:"1月 (Jan)", 2:"2月 (Feb)", 3:"3月 (Mar)", 4:"4月 (Apr)", 5:"5月 (May)", 6:"6月 (Jun)", 7:"7月 (Jul)", 8:"8月 (Aug)", 9:"9月 (Sep)", 10:"10月 (Oct)", 11:"11月 (Nov)", 12:"12月 (Dec)"}
            rev_month_map = {v:k for k,v in month_map.items()}
            curr_m_str = month_map.get(now.month, "1月 (Jan)")
            sel_month_str = c_m.selectbox("月份", list(month_map.values()), index=list(month_map.values()).index(curr_m_str), label_visibility="collapsed")
            sel_month = rev_month_map[sel_month_str]
        with c_ctrl2:
            view_mode = st.radio("👁️ 檢視模式", ["📅 電腦月曆", "📝 手機列表"], horizontal=True, label_visibility="collapsed")

    st.markdown("---")

    if view_mode == "📅 電腦月曆":
        cal = calendar.monthcalendar(sel_year, sel_month)
        cols = st.columns(7)
        days_map = ["MON 一", "TUE 二", "WED 三", "THU 四", "FRI 五", "SAT 六", "SUN 日"]
        for i, d in enumerate(days_map): cols[i].markdown(f"<div style='text-align:center;font-size:0.8rem;color:#94a3b8;font-weight:bold;'>{d}</div>", unsafe_allow_html=True)
        
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day != 0:
                        date_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                        day_shifts = shifts_df[shifts_df['Date'] == date_str] if not shifts_df.empty else pd.DataFrame()
                        
                        if st.button(f"📅 {day}", key=f"d_grid_{date_str}", use_container_width=True):
                            st.session_state['roster_date'] = date_str
                            st.rerun()

                        is_store_closed = any((r['Staff'] == "全店" and r['Type'] == "公休") for _, r in day_shifts.iterrows())

                        html_content = ""
                        if is_store_closed: html_content = "<div class='store-closed'>🔴 全店公休</div>"
                        else:
                            for _, r in day_shifts.iterrows():
                                bg_color = "#EF4444" if r['Type'] == "公休" else staff_color_map.get(r['Staff'], "#6B7280")
                                html_content += f"<span class='shift-pill' style='background-color:{bg_color};'>{r['Staff']} - {r['Type']}</span>"
                        st.markdown(f"<div class='day-cell'>{html_content}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='min-height:90px;'></div>", unsafe_allow_html=True)
    else:
        cal = calendar.monthcalendar(sel_year, sel_month)
        for week in cal:
            for day in week:
                if day != 0:
                    date_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == date_str] if not shifts_df.empty else pd.DataFrame()
                    weekday_str = ["週一","週二","週三","週四","週五","週六","週日"][datetime(sel_year, sel_month, day).weekday()]
                    
                    is_store_closed = any((r['Staff'] == "全店" and r['Type'] == "公休") for _, r in day_shifts.iterrows())
                    content_html = ""
                    if is_store_closed: content_html = "<span class='store-closed-mobile'>🔴 全店公休 (Store Closed)</span>"
                    elif not day_shifts.empty:
                        for _, r in day_shifts.iterrows():
                            bg_color = "#EF4444" if r['Type'] == "公休" else staff_color_map.get(r['Staff'], "#6B7280")
                            content_html += f"<span class='shift-pill' style='background-color:{bg_color};'>{r['Staff']} {r['Type']}</span>"
                    else: content_html = "<span style='color:#cbd5e1;font-size:0.8rem;'>尚無排班</span>"

                    st.markdown(f"""
                    <div class='mobile-day-row'>
                        <div class='mobile-day-date'>{day}<br><span style='font-size:0.7rem;color:#94a3b8;'>{weekday_str}</span></div>
                        <div class='mobile-day-content'>{content_html}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"編輯 {date_str}", key=f"btn_list_{date_str}", use_container_width=True):
                        st.session_state['roster_date'] = date_str; st.rerun()

    st.markdown("---")
    c_edit, c_smart = st.columns([1, 1])
    
    with c_edit:
        if 'roster_date' in st.session_state:
            t_date = st.session_state['roster_date']
            st.markdown(f"#### ✏️ 編輯排班: {t_date}")
            
            current_day_shifts = shifts_df[shifts_df['Date'] == t_date] if not shifts_df.empty else pd.DataFrame()
            is_closed = any((r['Staff'] == "全店" and r['Type'] == "公休") for _, r in current_day_shifts.iterrows())

            if is_closed:
                st.error("🔴 目前設定為：全店公休")
                if st.button("🔓 解除全店公休", use_container_width=True):
                      for idx, row in enumerate(ws_shifts.get_all_values()):
                          if len(row) > 1 and row[0] == t_date and row[1] == "全店":
                              retry_action(ws_shifts.delete_rows, idx + 1); break
                      st.success("已解除"); time.sleep(0.5); st.cache_data.clear(); st.rerun()
            else:
                if not current_day_shifts.empty:
                    st.caption("已安排 (點擊❌移除):")
                    for _, r in current_day_shifts.iterrows():
                        if st.button(f"❌ {r['Staff']} ({r['Type']})", key=f"del_{r['Staff']}_{t_date}"):
                            for idx, row in enumerate(ws_shifts.get_all_values()):
                                if len(row) > 1 and row[0] == t_date and row[1] == r['Staff']:
                                    retry_action(ws_shifts.delete_rows, idx + 1); break
                            st.success("已移除"); time.sleep(0.5); st.cache_data.clear(); st.rerun()

                with st.form("add_shift_pro"):
                    s_staff = st.selectbox("人員", users_list)
                    s_type = st.selectbox("班別類型", list(SHIFT_COLORS.keys()))
                    s_note = st.text_input("備註 (可選)")
                    
                    if st.form_submit_button("➕ 新增/更新排班", use_container_width=True):
                        try:
                            rows_to_del = [idx + 1 for idx, row in enumerate(ws_shifts.get_all_values()) if len(row) > 1 and row[0] == t_date and row[1] == s_staff]
                            for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                            retry_action(ws_shifts.append_row, [t_date, s_staff, s_type, s_note, "FALSE", user_name])
                            st.cache_data.clear(); st.success(f"已更新"); time.sleep(0.5); st.rerun()
                        except Exception as e: st.error(f"寫入失敗: {e}")

                st.markdown("---")
                if st.button("🔴 設定為全店公休 (Store Closed)", type="primary", use_container_width=True):
                    try:
                        rows_to_del = [idx + 1 for idx, row in enumerate(ws_shifts.get_all_values()) if len(row) > 1 and row[0] == t_date]
                        for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                        retry_action(ws_shifts.append_row, [t_date, "全店", "公休", "Store Closed", "FALSE", user_name])
                        st.cache_data.clear(); st.success("已設定全店公休"); st.rerun()
                    except Exception as e: st.error(f"設定失敗: {e}")
        else:
            st.info("👈 請點選上方列表日期進行編輯")

    with c_smart:
        st.markdown("#### 🧠 智能工具 & 輸出")
        with st.expander("📤 生成 LINE 通告 & 存圖", expanded=True):
            if st.button("📤 生成 LINE 通告文字", use_container_width=True):
                line_txt = f"📅 【IFUKUK {sel_month}月班表公告】\n------------------------\n"
                m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
                m_data = shifts_df[shifts_df['Date'].str.startswith(m_prefix)].sort_values(['Date', 'Staff'])
                if not m_data.empty:
                    last_date = ""
                    for _, r in m_data.iterrows():
                        d_short = r['Date'][5:]
                        if d_short != last_date: 
                            line_txt += f"\n🗓️ {d_short} ({calendar.day_name[datetime.strptime(r['Date'], '%Y-%m-%d').weekday()][:3]})\n"
                            last_date = d_short
                        if r['Staff'] == "全店" and r['Type'] == "公休": line_txt += f"   ⛔ 全店公休 (Store Closed)\n"
                        else: line_txt += f"   👤 {r['Staff']}：{r['Type']} {f'({r['Note']})' if r['Note'] else ''}\n"
                    st.text_area("內容", value=line_txt, height=150)
                else: st.warning("無資料")

            if st.button("📸 班表存圖 (Image)", use_container_width=True):
                with st.spinner("下載字型與繪圖中..."):
                    img_buf = generate_roster_image_buffer(sel_year, sel_month, shifts_df, calendar.monthrange(sel_year, sel_month)[1], staff_color_map)
                    if img_buf:
                        st.image(img_buf, caption=f"{sel_year}/{sel_month}")
                        st.download_button("💾 下載", data=img_buf, file_name=f"roster_{sel_year}_{sel_month}.png", mime="image/png", use_container_width=True)
                    else: st.error("繪圖失敗 (請檢查伺服器權限或網路)")

        with st.expander("🔄 循環排班 & 複製", expanded=False):
            wc_tab1, wc_tab2 = st.tabs(["👤 人員", "🔴 公休"])
            week_map = {"週一":0, "週二":1, "週三":2, "週四":3, "週五":4, "週六":5, "週日":6}
            with wc_tab1:
                p_staff = st.selectbox("對象", users_list, key="p_st")
                p_day_cn = st.selectbox("每週幾?", list(week_map.keys()), key="p_wd")
                p_type = st.selectbox("班別", list(SHIFT_COLORS.keys()), key="p_ty")
                if st.button("🚀 執行"):
                    target_weekday = week_map[p_day_cn]
                    all_vals = ws_shifts.get_all_values() 
                    added = 0
                    for week in calendar.monthcalendar(sel_year, sel_month):
                        day = week[target_weekday]
                        if day != 0:
                            d_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                            rows_to_del = [idx+1 for idx, row in enumerate(all_vals) if len(row)>1 and row[0]==d_str and row[1]==p_staff]
                            for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                            retry_action(ws_shifts.append_row, [d_str, p_staff, p_type, "Auto", "FALSE", user_name])
                            added += 1
                    st.cache_data.clear(); st.success(f"完成 {added} 筆"); st.rerun()

            with wc_tab2:
                sc_day_cn = st.selectbox("每週幾?", list(week_map.keys()), key="sc_wd")
                if st.button("🔴 執行"):
                    target_weekday = week_map[sc_day_cn]
                    target_dates = [f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}" for week in calendar.monthcalendar(sel_year, sel_month) for day in week if day!=0 and week.index(day) == target_weekday]
                    if target_dates:
                        all_vals = ws_shifts.get_all_values()
                        rows_to_del = [idx+1 for idx, row in enumerate(all_vals) if len(row)>0 and row[0] in target_dates]
                        for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                        for d in target_dates: retry_action(ws_shifts.append_row, [d, "全店", "公休", "Store Closed", "FALSE", user_name])
                        st.cache_data.clear(); st.success("完成"); st.rerun()

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False; st.session_state['user_name'] = ""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    if 'exchange_rate' not in st.session_state:
        l_rate, succ = get_live_rate()
        st.session_state['exchange_rate'] = l_rate
        st.session_state['rate_source'] = "Live API" if succ else "Manual"
    if 'inv_page' not in st.session_state: st.session_state['inv_page'] = 1

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
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>OMEGA V110.0 QUANTUM HARDENED</div>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("帳號 (ID)"); p = st.text_input("密碼 (Password)", type="password")
                if st.form_submit_button("登入 (LOGIN)", type="primary"):
                    with st.spinner("Secure Login..."):
                        users_df = get_data_safe(ws_users, ["Name", "Password", "Role", "Status", "Created_At"])
                        u = u.strip(); p = p.strip()
                        if users_df.empty and u == "Boss" and p == "1234":
                            retry_action(ws_users.append_row, ["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                            st.cache_data.clear(); st.success("Boss Created"); time.sleep(1); st.rerun()
                        
                        if not users_df.empty and 'Name' in users_df.columns:
                            tgt = users_df[(users_df['Name'] == u) & (users_df['Status'] == 'Active')]
                            if not tgt.empty:
                                stored = str(tgt.iloc[0]['Password'])
                                if (len(stored)==64 and check_hash(p, stored)) or (p == stored):
                                    st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=tgt.iloc[0]['Role']; log_event(ws_logs, u, "Login", "Success"); st.rerun()
                                else: st.error("密碼錯誤")
                            else: st.error("帳號不存在")
                        else: st.warning("⚠️ 連線忙碌，請重試")
        return

    # --- 主畫面 ---
    user_initial = st.session_state['user_name'][0].upper()
    render_navbar(user_initial)

    # QUANTUM DATA FETCH (已包含自動過濾空白行)
    df = get_data_safe(ws_items, SHEET_HEADERS)
    logs_df = get_data_safe(ws_logs, ["Timestamp", "User", "Action", "Details"]) 
    users_df = get_data_safe(ws_users, ["Name", "Password", "Role", "Status", "Created_At"])
    staff_list = users_df['Name'].tolist() if not users_df.empty and 'Name' in users_df.columns else []

    # QUANTUM TYPE CASTING (強制保護數字運算不崩潰)
    for c in ["SKU", "Name", "Category", "Size", "Last_Updated", "Image_URL", "Orig_Currency"]: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost', 'Safety_Stock', 'Orig_Cost', 'Qty_CN']:
        if num not in df.columns: df[num] = 0
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    
    df['Safe_Level'] = df['Safety_Stock'].apply(lambda x: 5 if x == 0 else x)
    df['SKU'] = df['SKU'].astype(str)
    df['Style_Code'] = df['SKU'].apply(get_style_code)
    
    product_map = {r['SKU']: f"{r['Name']} ({r['Size']})" for _, r in df.iterrows()} if not df.empty else {}

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        st.caption(f"職位: {st.session_state['user_role']}")
        st.markdown("---")
        with st.expander("💱 匯率監控", expanded=True):
            curr_rate = st.session_state['exchange_rate']
            new_r = st.number_input("人民幣(RMB) -> 台幣(TWD)", value=curr_rate, step=0.01)
            if new_r != curr_rate: st.session_state['exchange_rate'] = new_r
            if st.button("🔄 更新即時匯率"): 
                l_rate, succ = get_live_rate()
                st.session_state['exchange_rate'] = l_rate; st.rerun()
        st.markdown("---")
        if st.button("🚪 登出系統"): st.session_state['logged_in'] = False; st.rerun()

    # Dashboard
    total_qty_tw = df['Qty'].sum() if not df.empty else 0
    total_qty_cn = df['Qty_CN'].sum() if not df.empty else 0
    total_qty = total_qty_tw + total_qty_cn
    total_cost = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum() if not df.empty else 0
    total_rev = (df['Qty'] * df['Price']).sum() if not df.empty else 0
    profit = total_rev - (df['Qty'] * df['Cost']).sum() if not df.empty else 0
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
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='black')
                st.plotly_chart(fig_pie, use_container_width=True)
            with c2:
                top = df.groupby(['Style_Code', 'Name']).agg({'Qty':'sum'}).reset_index().sort_values(by='Qty', ascending=False).head(10)
                fig_bar = px.bar(top, x='Qty', y='Name', orientation='h', text='Qty', color='Qty', color_continuous_scale=px.colors.qualitative.Pastel)
                fig_bar.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='black')
                st.plotly_chart(fig_bar, use_container_width=True)
                
        st.divider(); st.subheader("📦 庫存區 (手機優化版)")
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1: search_q = st.text_input("🔍 搜尋商品", placeholder="輸入貨號或品名...")
        with col_s2: filter_cat = st.selectbox("📂 分類篩選", ["全部"] + CAT_LIST)
        gallery_df = df.copy()
        if search_q: gallery_df = gallery_df[gallery_df.apply(lambda x: search_q.lower() in str(x.values).lower(), axis=1)]
        if filter_cat != "全部": gallery_df = gallery_df[gallery_df['Category'] == filter_cat]
        
        if not gallery_df.empty:
            items_per_page = 10
            total_pages = math.ceil(len(gallery_df) / items_per_page)
            curr_page = st.session_state['inv_page']
            if curr_page > total_pages: curr_page = total_pages
            if curr_page < 1: curr_page = 1
            st.session_state['inv_page'] = curr_page
            
            c_p1, c_p2, c_p3 = st.columns([1, 2, 1])
            with c_p1: 
                if st.button("◀", key="p_up_prev", use_container_width=True, disabled=(curr_page==1)): st.session_state['inv_page'] -= 1; st.rerun()
            with c_p2: st.markdown(f"<div style='text-align:center;font-weight:bold;padding-top:10px;'>第 {curr_page} / {total_pages} 頁</div>", unsafe_allow_html=True)
            with c_p3:
                if st.button("▶", key="p_up_next", use_container_width=True, disabled=(curr_page==total_pages)): st.session_state['inv_page'] += 1; st.rerun()

            start_idx = (curr_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            view_df = gallery_df.iloc[start_idx:end_idx]

            grouped = view_df.groupby(['Style_Code', 'Name'])
            for (style_code, name), group in grouped:
                first_row = group.iloc[0]; img = render_image_url(first_row['Image_URL']); price = int(first_row['Price'])
                total_qty_tw = group['Qty'].sum(); total_qty_cn = group['Qty_CN'].sum()
                
                # QUANTUM FIX: 避免 SettingWithCopyWarning
                group_safe = group.copy()
                group_safe['size_sort'] = group_safe['Size'].apply(get_size_sort_key)
                sorted_group = group_safe.sort_values('size_sort')
                
                stock_badges = ""
                for _, r in sorted_group.iterrows():
                    cls = "has-stock" if r['Qty'] > 0 else "no-stock"
                    stock_badges += f"<span class='stock-tag {cls}'>{r['Size']}:{r['Qty']}</span>"

                with st.container(border=True):
                    st.markdown(f"""
                    <div class='inv-row'>
                        <img src='{img}' class='inv-img'>
                        <div class='inv-info'>
                            <div class='inv-title'>{name}</div>
                            <div class='inv-meta'>{style_code} | ${price}</div>
                            <div class='stock-tag-row'>{stock_badges}</div>
                            <div style='font-size:0.8rem; color:#64748b; margin-top:4px;'>
                                🇹🇼 總庫存: <b>{total_qty_tw}</b> | 🇨🇳 中國倉: <b>{total_qty_cn}</b>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    with st.expander("📝 庫存調整"):
                        with st.form(f"form_{style_code}_{name}"):
                            i_tw = {}; i_cn = {}; g_cols = st.columns(4)
                            for idx, r_data in enumerate(sorted_group.iterrows()):
                                _, row = r_data
                                with g_cols[idx%4]: 
                                    lbl = row['Size']; i_tw[row['SKU']] = st.number_input(f"TW {lbl}", value=int(row['Qty']), key=f"t_{row['SKU']}"); i_cn[row['SKU']] = st.number_input(f"CN {lbl}", value=int(row['Qty_CN']), key=f"c_{row['SKU']}")
                            if st.form_submit_button("💾 儲存變更", use_container_width=True):
                                for tsku, n_tw in i_tw.items():
                                    if tsku in df['SKU'].tolist():
                                        n_cn = i_cn[tsku]; r = ws_items.find(tsku).row
                                        retry_action(ws_items.update_cell, r, 5, n_tw)
                                        retry_action(ws_items.update_cell, r, 13, n_cn)
                                        retry_action(ws_items.update_cell, r, 8, get_taiwan_time_str())
                                st.cache_data.clear(); st.success("已更新"); time.sleep(0.5); st.rerun()
            
            c_p4, c_p5, c_p6 = st.columns([1, 2, 1])
            with c_p4: 
                if st.button("◀", key="p_dn_prev", use_container_width=True, disabled=(curr_page==1)): st.session_state['inv_page'] -= 1; st.rerun()
            with c_p5: st.markdown(f"<div style='text-align:center;font-weight:bold;padding-top:10px;'>{curr_page} / {total_pages}</div>", unsafe_allow_html=True)
            with c_p6:
                if st.button("▶", key="p_dn_next", use_container_width=True, disabled=(curr_page==total_pages)): st.session_state['inv_page'] += 1; st.rerun()

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
                vdf = vdf.sort_values(['Name', 'Size'])
                vdf = vdf.head(40)
                rows = [vdf.iloc[i:i+3] for i in range(0, len(vdf), 3)]
                for r in rows:
                    cols = st.columns(3)
                    for i, (_, item) in enumerate(r.iterrows()):
                        with cols[i]:
                            st.markdown(f"""
                            <div class='pos-card'>
                                <div class='pos-img'><img src='{render_image_url(item['Image_URL'])}' style='width:100%;height:100%;object-fit:cover;'></div>
                                <div class='pos-content'>
                                    <div class='pos-title'>{item['Name']}</div>
                                    <div class='pos-meta'>{item['Size']} | {item['Category']}</div>
                                    <div class='pos-price-row'>
                                        <div class='pos-price'>${item['Price']}</div>
                                        <div class='pos-stock'>現貨:{item['Qty']}</div>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button("➕ 加入", key=f"add_{item['SKU']}", use_container_width=True):
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
                        st.markdown(f"<div class='cart-item'><span>{i['name']} ({i['size']}) x{i['qty']}</span><b>${i['subtotal']}</b></div>", unsafe_allow_html=True)
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
                    sale_ch = st.selectbox("通路", ["門市","官網","直播","網路","其他"]) 
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
                            content = f"Sale | Total:${final_total} | Items:{','.join(logs)} | Note:{note} {note_str} | Pay:{pay} | Channel:{sale_ch} | By:{sale_who}"
                            log_event(ws_logs, st.session_state['user_name'], "Sale", content)
                            st.session_state['pos_cart'] = []
                            st.cache_data.clear(); st.balloons(); st.success("完成"); time.sleep(1); st.rerun()
                else: st.info("購物車是空的")
                st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        st.subheader("📈 營運戰情室")
        rev = (df['Qty'] * df['Price']).sum() if not df.empty else 0
        cost = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum() if not df.empty else 0
        profit = rev - (df['Qty'] * df['Cost']).sum() if not df.empty else 0
        real = calculate_realized_revenue(logs_df)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='metric-card'><div class='metric-label'>預估營收</div><div class='metric-value'>${rev:,}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-label'>總成本 (TWD)</div><div class='metric-value'>${cost:,}</div><div style='font-size:10px;'>含 RMB 原幣: ¥{rmb_stock_value:,}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><div class='metric-label'>潛在毛利</div><div class='metric-value' style='color:#f59e0b'>${profit:,}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card'><div class='metric-label'>實際營收</div><div class='metric-value' style='color:#10b981'>${real:,}</div></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown("##### 📅 結算週期與財務總覽 (自動統計)")
        c_date1, c_date2 = st.columns(2)
        start_d = c_date1.date_input("起始日期", value=date.today().replace(day=1))
        end_d = c_date2.date_input("結束日期", value=date.today())
        
        sales_data = []
        if not logs_df.empty:
            s_logs = logs_df[logs_df['Action'] == 'Sale']
            for _, row in s_logs.iterrows():
                try:
                    ts_str = str(row['Timestamp']).split(' ')[0]
                    # QUANTUM FIX: 如果日期格式有誤，直接跳過不崩潰
                    try:
                        log_date = datetime.strptime(ts_str, "%Y-%m-%d").date()
                    except ValueError:
                        continue
                    
                    if start_d <= log_date <= end_d:
                        d = str(row['Details'])
                        total_m = re.search(r'Total:\s*\$?\s*(\d+)', d)
                        total_v = int(total_m.group(1)) if total_m else 0
                        
                        ch_v = "未分類"
                        if "Channel:" in d: ch_m = re.search(r'Channel:(.*?) \|', d + " |"); ch_v = ch_m.group(1).strip() if ch_m else "未分類"
                        elif " | " in d: ch_m = re.search(r' \| (門市|官網|直播|網路|其他)', d); ch_v = ch_m.group(1) if ch_m else "未分類"

                        pay_v = "未分類"
                        if "Pay:" in d: pay_m = re.search(r'Pay:(.*?) \|', d + " |"); pay_v = pay_m.group(1).strip() if pay_m else "未分類"

                        by_v = str(row['User'])
                        if "By:" in d: by_m = re.search(r'By:(\w+)', d); by_v = by_m.group(1) if by_m else str(row['User'])
                        
                        items_v = "-"
                        if "Items:" in d: 
                            items_str = re.search(r'Items:(.*?) \|', d).group(1)
                            parsed_items = []
                            for part in items_str.split(','):
                                p_sku = part.split(' x')[0].strip()
                                p_qty = part.split(' x')[1].strip() if ' x' in part else "?"
                                p_name = product_map.get(p_sku, p_sku)
                                parsed_items.append(f"{p_name} x{p_qty}")
                            items_v = ", ".join(parsed_items)

                        if total_v > 0: sales_data.append({"日期":row['Timestamp'],"金額":total_v,"通路":ch_v,"付款":pay_v,"銷售員":by_v,"明細":items_v, "原始Log": d})
                except Exception as ex: 
                    pass
        sdf = pd.DataFrame(sales_data)
        
        if not sdf.empty:
            pay_stats = sdf.groupby('付款')['金額'].sum().to_dict()
            fc1, fc2, fc3, fc4 = st.columns(4)
            fc1.markdown(f"<div class='finance-card'><div class='finance-lbl'>現金總額</div><div class='finance-val'>${pay_stats.get('現金', 0):,}</div></div>", unsafe_allow_html=True)
            fc2.markdown(f"<div class='finance-card'><div class='finance-lbl'>轉帳總額</div><div class='finance-val'>${pay_stats.get('轉帳', 0):,}</div></div>", unsafe_allow_html=True)
            fc3.markdown(f"<div class='finance-card'><div class='finance-lbl'>刷卡總額</div><div class='finance-val'>${pay_stats.get('刷卡', 0):,}</div></div>", unsafe_allow_html=True)
            fc4.markdown(f"<div class='finance-card'><div class='finance-lbl'>禮券/其他</div><div class='finance-val'>${pay_stats.get('禮券', 0) + pay_stats.get('其他', 0):,}</div></div>", unsafe_allow_html=True)
            st.markdown("---")

            c1, c2 = st.columns(2)
            with c1: 
                fig = px.pie(sdf, names='通路', values='金額', hole=0.4, title="通路營收佔比", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='black')
                st.plotly_chart(fig, use_container_width=True)
            with c2: 
                fig2 = px.bar(sdf.groupby('銷售員')['金額'].sum().reset_index(), x='銷售員', y='金額', title="人員業績排行", color='金額', color_continuous_scale=px.colors.sequential.Teal)
                fig2.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='black')
                st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("##### 📝 銷售明細表 (含管理)")
            st.dataframe(sdf.drop(columns=['原始Log']), use_container_width=True)

            st.markdown("##### 📝 編輯/修正訂單 (自動回補庫存)")
            sale_opts = sdf.apply(lambda x: f"{x['日期']} | ${x['金額']} | {x['明細'][:20]}...", axis=1).tolist()
            sel_sale = st.selectbox("選擇要處理的訂單", ["..."] + sale_opts)
            
            if sel_sale != "...":
                target_ts = sel_sale.split(" | ")[0]
                target_row = sdf[sdf['日期'] == target_ts].iloc[0]
                raw_log = target_row['原始Log']
                
                curr_note = ""; curr_ch = ""; curr_pay = ""; curr_items_str = ""
                try:
                    curr_items_str = re.search(r'Items:(.*?) \|', raw_log).group(1)
                    if "Note:" in raw_log: curr_note = re.search(r'Note:(.*?) \|', raw_log + " |").group(1).strip()
                    if "Channel:" in raw_log: curr_ch = re.search(r'Channel:(.*?) \|', raw_log + " |").group(1).strip()
                    if "Pay:" in raw_log: curr_pay = re.search(r'Pay:(.*?) \|', raw_log + " |").group(1).strip()
                except: pass

                with st.form("edit_sale_form"):
                    e_items = st.text_area("商品內容", value=curr_items_str)
                    c_e1, c_e2, c_e3 = st.columns(3)
                    e_total = c_e1.number_input("總金額", value=int(target_row['金額']))
                    e_ch = c_e2.selectbox("通路", ["門市","官網","直播","網路","其他"], index=["門市","官網","直播","網路","其他"].index(curr_ch) if curr_ch in ["門市","官網","直播","網路","其他"] else 0)
                    e_pay = c_e3.selectbox("付款", ["現金","刷卡","轉帳","禮券","其他"], index=["現金","刷卡","轉帳","禮券","其他"].index(curr_pay) if curr_pay in ["現金","刷卡","轉帳","禮券","其他"] else 0)
                    e_note = st.text_input("備註", value=curr_note)
                    
                    if st.form_submit_button("✅ 確認修改"):
                        try:
                            all_logs = ws_logs.get_all_values()
                            log_idx = -1
                            for idx, row in enumerate(all_logs):
                                if row[0] == target_ts and "Sale" in row[2]: log_idx = idx + 1; break
                            if log_idx != -1:
                                for part in curr_items_str.split(','):
                                    clean_part = re.sub(r'\s*\(\$.*?\)', '', part).strip()
                                    if ' x' in clean_part:
                                        p_sku = clean_part.split(' x')[0].strip(); p_qty = int(clean_part.split(' x')[1].strip())
                                        cell = ws_items.find(p_sku)
                                        if cell: retry_action(ws_items.update_cell, cell.row, 5, int(ws_items.cell(cell.row, 5).value) + p_qty)
                                
                                new_items_list = []
                                for part in e_items.split(','):
                                    clean_part = re.sub(r'\s*\(\$.*?\)', '', part).strip()
                                    if ' x' in clean_part:
                                        p_sku = clean_part.split(' x')[0].strip(); p_qty = int(clean_part.split(' x')[1].strip())
                                        cell = ws_items.find(p_sku)
                                        if cell:
                                            retry_action(ws_items.update_cell, cell.row, 5, int(ws_items.cell(cell.row, 5).value) - p_qty)
                                            new_items_list.append(f"{p_sku} x{p_qty}")
                                
                                retry_action(ws_logs.delete_rows, log_idx)
                                new_content = f"Sale | Total:${int(e_total)} | Items:{','.join(new_items_list)} | Note:{e_note} | Pay:{e_pay} | Channel:{e_ch} | By:{st.session_state['user_name']} (Edited)"
                                log_event(ws_logs, st.session_state['user_name'], "Sale", new_content)
                                st.success("✅ 訂單已修正！"); time.sleep(2); st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

                if st.button("🗑️ 作廢"):
                    try:
                        for part in curr_items_str.split(','):
                            clean_part = re.sub(r'\s*\(\$.*?\)', '', part).strip()
                            if ' x' in clean_part:
                                p_sku = clean_part.split(' x')[0].strip(); p_qty = int(clean_part.split(' x')[1].strip())
                                cell = ws_items.find(p_sku)
                                if cell: retry_action(ws_items.update_cell, cell.row, 5, int(ws_items.cell(cell.row, 5).value) + p_qty)
                        all_logs = ws_logs.get_all_values()
                        for idx, row in enumerate(all_logs):
                            if row[0] == target_ts and "Sale" in row[2]: retry_action(ws_logs.delete_rows, idx + 1); break
                        st.success("已作廢"); time.sleep(1); st.rerun()
                    except: st.error("失敗")

        else: st.info("尚無日誌數據")

    with tabs[3]:
        st.subheader("🎁 內部領用/稽核 (統計修正)")
        if not logs_df.empty:
            int_df = logs_df[logs_df['Action'] == "Internal_Use"].copy()
            if not int_df.empty:
                def parse_int_who(d):
                    try: return str(d).split(' | ')[1].strip()
                    except: return "未分類"
                def parse_int_qty(d):
                    try: return int(str(d).split(' | ')[0].split(' -')[1])
                    except: return 0
                def parse_int_reason(d):
                    try: return str(d).split(' | ')[2].strip()
                    except: return "未分類"
                
                int_df['實際領用人'] = int_df['Details'].apply(parse_int_who)
                int_df['數量'] = int_df['Details'].apply(parse_int_qty)
                int_df['原因'] = int_df['Details'].apply(parse_int_reason)
                
                st.markdown("##### 📊 領用統計 (依實際領用人)")
                stats = int_df.groupby(['實際領用人', '原因'])['數量'].sum().unstack(fill_value=0)
                st.dataframe(stats, use_container_width=True)

        with st.expander("➕ 新增領用單", expanded=True):
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} {x['Size']}", axis=1).tolist() if not df.empty else []
            sel = st.selectbox("商品", ["..."] + opts)
            if sel != "...":
                tsku = sel.split(" | ")[0]; tr = df[df['SKU'] == tsku].iloc[0]; st.info(f"目前庫存: {tr['Qty']}")
                with st.form("internal"):
                    q = st.number_input("數量", 1); who = st.selectbox("領用人", staff_list); rsn = st.selectbox("原因", ["公務", "公關", "福利", "報廢", "樣品", "其他"]); n = st.text_input("備註")
                    if st.form_submit_button("執行"):
                        r = ws_items.find(tsku).row; retry_action(ws_items.update_cell, r, 5, int(tr['Qty'])-q)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{tsku} -{q} | {who} | {rsn} | {n}")
                        st.cache_data.clear(); st.success("已記錄"); st.rerun()
        
        st.divider()
        st.markdown("#### 🕵️ 紀錄管理")
        if not logs_df.empty and 'int_df' in locals() and not int_df.empty:
            rev_opts = int_df.apply(lambda x: f"{x['Timestamp']} | {x['Details']}", axis=1).tolist()
            sel_rev = st.selectbox("選擇要修正/編輯的領用紀錄", ["..."] + rev_opts)
            
            if sel_rev != "...":
                target_ts = sel_rev.split(" | ")[0]
                orig_row = logs_df[logs_df['Timestamp'] == target_ts].iloc[0]
                orig_detail = str(orig_row['Details'])
                try:
                    parts = orig_detail.split(' | ')
                    orig_sku_part = parts[0]
                    orig_sku = orig_sku_part.split(' -')[0]
                    orig_qty = int(orig_sku_part.split(' -')[1])
                    orig_who = parts[1]
                    orig_reason = parts[2]
                    orig_note = parts[3] if len(parts) > 3 else ""
                except:
                    st.error("資料格式無法解析，無法編輯"); st.stop()

                with st.form("edit_internal_log"):
                    st.info(f"正在編輯: {orig_sku} (原數量: {orig_qty})")
                    new_q = st.number_input("修正數量", value=orig_qty, min_value=1)
                    new_who = st.selectbox("修正領用人", staff_list, index=staff_list.index(orig_who) if orig_who in staff_list else 0)
                    new_rsn = st.selectbox("修正原因", ["公務", "公關", "福利", "報廢", "樣品", "其他"], index=["公務", "公關", "福利", "報廢", "樣品", "其他"].index(orig_reason) if orig_reason in ["公務", "公關", "福利", "報廢", "樣品", "其他"] else 0)
                    new_note = st.text_input("修正備註", value=orig_note)
                    
                    c_edit_1, c_edit_2 = st.columns(2)
                    
                    if c_edit_1.form_submit_button("✅ 確認更新"):
                        cell = ws_items.find(orig_sku)
                        if cell:
                            curr_stock = int(ws_items.cell(cell.row, 5).value)
                            temp_stock = curr_stock + orig_qty
                            final_stock = temp_stock - new_q
                            retry_action(ws_items.update_cell, cell.row, 5, final_stock)
                            all_logs = ws_logs.get_all_values()
                            for idx, row in enumerate(all_logs):
                                if row[0] == target_ts: retry_action(ws_logs.delete_rows, idx + 1); break
                            log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{orig_sku} -{new_q} | {new_who} | {new_rsn} | {new_note} (Edited)")
                            st.success("紀錄已更新"); time.sleep(1); st.rerun()
                        else: st.error("找不到該商品SKU，無法更新庫存")

                    if c_edit_2.form_submit_button("🗑️ 刪除此紀錄"):
                        cell = ws_items.find(orig_sku)
                        if cell:
                            curr_stock = int(ws_items.cell(cell.row, 5).value)
                            retry_action(ws_items.update_cell, cell.row, 5, curr_stock + orig_qty)
                            all_logs = ws_logs.get_all_values()
                            for idx, row in enumerate(all_logs):
                                if row[0] == target_ts: retry_action(ws_logs.delete_rows, idx + 1); break
                            st.success("紀錄已刪除，庫存已歸還"); time.sleep(1); st.rerun()

    with tabs[4]:
        st.markdown("<div class='mgmt-box'>", unsafe_allow_html=True)
        st.markdown("<div class='mgmt-title'>矩陣管理中心</div>", unsafe_allow_html=True)
        mt1, mt2, mt3 = st.tabs(["✨ 商品新增", "⚡ 雙向調撥", "🗑️ 商品刪除"])
        
        with mt1:
            mode = st.radio("模式", ["新系列", "衍生"], horizontal=True)
            a_sku, a_name = "", ""
            if mode == "新系列":
                c = st.selectbox("分類", CAT_LIST)
                if st.button("生成"): st.session_state['base'] = generate_smart_style_code(c, df['SKU'].tolist())
                if 'base' in st.session_state: a_sku = st.session_state['base']
            else:
                p_opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist()
                p = st.selectbox("母商品", ["..."] + p_opts)
                if p != "...": 
                    p_sku = p.split(" | ")[0]
                    pr = df[df['SKU']==p_sku].iloc[0]; a_sku = get_style_code(p_sku)+"-NEW"; a_name = pr['Name']
            
            with st.form("add_m"):
                c1, c2 = st.columns(2); bs = c1.text_input("Base SKU", value=a_sku); nm = c2.text_input("品名", value=a_name)
                c3, c4 = st.columns(2); pr = c3.number_input("售價", 0); co = c4.number_input("原幣成本", 0)
                cur = st.selectbox("幣別", ["TWD", "CNY"]); img = st.file_uploader("圖")
                sz = {}; cols = st.columns(5)
                for i, s in enumerate(SIZE_ORDER): sz[s] = cols[i%5].number_input(s, min_value=0)
                if st.form_submit_button("寫入資料庫"):
                    url = upload_image_to_imgbb(img) if img else ""
                    fc = int(co * st.session_state['exchange_rate']) if cur == "CNY" else co
                    for s, q in sz.items():
                        if q > 0: retry_action(ws_items.append_row, [f"{bs}-{s}", nm, "New", s, q, pr, fc, get_taiwan_time_str(), url, 5, cur, co, 0])
                    st.cache_data.clear(); st.success("完成"); st.rerun()
        
        with mt2:
            st.info("💡 請選擇要調撥的商品，系統將自動增減兩地庫存。")
            t_opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} {x['Size']} (TW:{x['Qty']} / CN:{x['Qty_CN']})", axis=1).tolist()
            sel = st.selectbox("選擇調撥商品", ["..."] + t_opts)
            if sel != "...":
                sel_sku = sel.split(" | ")[0]
                r = df[df['SKU']==sel_sku].iloc[0]
                c1, c2 = st.columns(2)
                q = c1.number_input("調撥數量", 1)
                c_act1, c_act2 = st.columns(2)
                if c_act1.button("TW ➡️ CN (台灣轉中國)"): 
                    row_idx = ws_items.find(sel_sku).row
                    retry_action(ws_items.update_cell, row_idx, 5, int(r['Qty'])-q)
                    retry_action(ws_items.update_cell, row_idx, 13, int(r['Qty_CN'])+q)
                    st.cache_data.clear(); st.success("調撥完成"); st.rerun()
                if c_act2.button("CN ➡️ TW (中國轉台灣)"):
                    row_idx = ws_items.find(sel_sku).row
                    retry_action(ws_items.update_cell, row_idx, 5, int(r['Qty'])+q)
                    retry_action(ws_items.update_cell, row_idx, 13, int(r['Qty_CN'])-q)
                    st.cache_data.clear(); st.success("調撥完成"); st.rerun()

        with mt3:
            st.warning("⚠️ 刪除後無法復原，請謹慎操作。")
            d_opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} {x['Size']}", axis=1).tolist()
            d = st.selectbox("選擇刪除商品", ["..."] + d_opts)
            if d != "..." and st.button("確認永久刪除"): 
                d_sku = d.split(" | ")[0]
                retry_action(ws_items.delete_rows, ws_items.find(d_sku).row)
                st.cache_data.clear(); st.success("已刪除"); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[5]: 
        st.subheader("📝 日誌搜尋")
        l_q = st.text_input("搜尋關鍵字 (人員/動作/品名)")
        if not logs_df.empty:
            view_df = logs_df.sort_index(ascending=False).copy()
            view_df.columns = ['時間', '人員', '動作', '內容詳情']
            action_map = {"Sale": "銷售", "Internal_Use": "內部領用", "Login": "登入", "Transfer": "調撥", "Batch": "批量"}
            view_df['動作'] = view_df['動作'].map(action_map).fillna(view_df['動作'])
            def translate_details(txt):
                txt_str = str(txt)
                for sku, info in product_map.items():
                    if sku in txt_str: txt_str = txt_str.replace(sku, info)
                return txt_str
            view_df['內容詳情'] = view_df['內容詳情'].apply(translate_details)
            if l_q: view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(l_q, case=False)).any(axis=1)]
            st.dataframe(view_df, use_container_width=True)

    with tabs[6]: 
        st.subheader("👥 人員管理 (Admin)")
        if st.session_state['user_role'] == 'Admin':
            admin_view = users_df.copy()
            admin_view.columns = ['姓名', '密碼(Hash)', '權限', '狀態', '建立時間']
            st.dataframe(admin_view, use_container_width=True)
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
