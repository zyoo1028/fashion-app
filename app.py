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
    page_title="IFUKUK ERP V116.0 OMNI-ROSTER", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【CSS 視覺核心：絕對對比覆蓋防護】
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

        [data-testid="stDataFrame"] { background-color: #FFFFFF !important; }
        [data-testid="stDataFrame"] * { color: #0f172a !important; }

        .pos-card, .inv-row, .finance-card, .metric-card, .cart-box, .mgmt-box {
            background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important; color: #0f172a !important;
        }
        
        .pos-img { width: 100%; height: 160px; object-fit: cover; background: #f9fafb; border-bottom: 1px solid #f3f4f6; }
        .pos-content { padding: 10px; flex-grow: 1; display: flex; flex-direction: column; }
        .pos-title { font-weight: bold; font-size: 1rem; margin-bottom: 4px; color: #111 !important; line-height: 1.3; }
        .pos-meta { font-size: 0.8rem; color: #666 !important; margin-bottom: 5px; }
        
        .stock-tag-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; margin-bottom: 5px; }
        .stock-tag { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; border: 1px solid transparent; }
        .stock-tag.has-stock { background-color: #dcfce7 !important; color: #166534 !important; border-color: #bbf7d0; }
        .stock-tag.no-stock { background-color: #fee2e2 !important; color: #991b1b !important; border-color: #fecaca; }
        
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
        
        .shift-pill { font-size: 0.75rem; padding: 4px 8px; border-radius: 6px; margin-bottom: 4px; display: inline-block; text-align: center; font-weight: bold; margin-right: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .store-closed { background-color: #EF4444 !important; font-weight: 900; font-size: 0.9rem; display: flex; align-items: center; justify-content: center; height: 100%; border-radius: 6px; min-height: 90px; }
        .store-closed-mobile { background-color: #FEF2F2 !important; border: 1px solid #FCA5A5; padding: 5px 10px; border-radius: 6px; font-weight: bold; display: inline-block; }
        
        .metric-card { background: linear-gradient(145deg, #ffffff, #f8fafc) !important; border: 1px solid #e2e8f0 !important; padding: 10px !important;}
        .metric-label { font-size: 0.8rem !important; font-weight: bold !important; color: #64748b !important; }
        .metric-value { color: #0f172a !important; font-size: 1.2rem !important; font-weight: 900 !important;}
        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border: 1px solid #cbd5e1; background-color: #FFFFFF !important; width: 100%; transition: all 0.2s; }
        .stButton>button p { color: #0f172a !important; }
        .stButton>button:hover { border-color: #94a3b8; }
        .stButton>button[data-testid="baseButton-primary"] p { color: #ffffff !important; }
        
        .barcode-form { background: #f8fafc; border: 2px dashed #cbd5e1; padding: 10px; border-radius: 10px; margin-bottom: 15px;}
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
            
            if expected_headers:
                for col in expected_headers:
                    if col not in new_headers:
                        df[col] = ""; new_headers.append(col)
                        
            df.columns = new_headers[:len(df.columns)]
            
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
            match = re.search(r'Total:\s*\$?\s*(\d+)', str(row['Details']))
            if match: total += int(match.group(1))
        except: pass
    return total

def calculate_sunk_cost(logs_df, cost_map):
    sunk_total = 0
    if logs_df.empty or 'Action' not in logs_df.columns: return 0
    int_logs = logs_df[logs_df['Action'] == 'Internal_Use']
    for _, row in int_logs.iterrows():
        try:
            parts = str(row['Details']).split(' | ')
            sku = parts[0].split(' -')[0].strip()
            qty = int(parts[0].split(' -')[1])
            
            unit_cost = 0
            if len(parts) > 4 and "Cost:" in parts[4]:
                unit_cost = int(parts[4].replace("Cost:", "").strip())
            else:
                unit_cost = cost_map.get(sku, 0)
                
            sunk_total += (unit_cost * qty)
        except: pass
    return sunk_total

def render_navbar(user_initial):
    d_str = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y/%m/%d")
    rate = st.session_state.get('exchange_rate', 4.5)
    st.markdown(f"""
        <div class="navbar-container">
            <div style="display:flex; justify-content:space-between; align-items:center; background:#fff; padding:15px; border-bottom:1px solid #e2e8f0; margin-bottom:15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div>
                    <span style="font-size:18px; font-weight:900; color:#0f172a;">IFUKUK GLOBAL</span><br>
                    <span style="font-size:11px; color:#64748b; font-family:monospace;">{d_str} • Rate: {rate}</span>
                </div>
                <div style="width:36px; height:36px; background:#0f172a; color:#ffffff !important; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold;">
                    {user_initial}
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]

# ==========================================
# 🗓️ 排班系統 ELITE V116.0 (OMNI-ROSTER)
# ==========================================
SHIFT_COLORS = { "早班": "#3B82F6", "晚班": "#8B5CF6", "全班": "#10B981", "代班": "#F59E0B", "公休": "#EF4444", "特休": "#DB2777", "空班": "#6B7280", "事假": "#EC4899", "病假": "#14B8A6" }

def get_staff_color_map(users_list):
    PALETTE = ["#2563EB", "#059669", "#7C3AED", "#DB2777", "#D97706", "#DC2626", "#0891B2", "#4F46E5", "#BE123C", "#B45309"]
    return {u: PALETTE[i % len(PALETTE)] for i, u in enumerate(sorted([x for x in users_list if x != "全店"]))}

# V116.0: 伺服器繞過與快取掛載 (解決繪圖失敗)
@st.cache_resource(show_spinner=False)
def get_cached_font():
    # 改寫入當前目錄，避開 Streamlit Cloud 對 /tmp/ 的權限清洗
    font_name = "NotoSansTC-Regular.ttf" 
    if not os.path.exists(font_name):
        try:
            # 使用更穩定的 Google Fonts raw link
            url = "https://github.com/google/fonts/raw/main/ofl/notosanstc/NotoSansTC-Regular.ttf"
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                with open(font_name, 'wb') as f:
                    f.write(r.content)
            else: return None
        except Exception as e: 
            print(f"Font Error: {e}")
            return None
    return font_name

def generate_roster_image_buffer(year, month, shifts_df, days_in_month, color_map):
    try:
        font_path = get_cached_font()
        prop = fm.FontProperties(fname=font_path) if font_path else fm.FontProperties()
        
        # 優化畫布比例與背景色，逼近真實 UI 介面
        fig, ax = plt.subplots(figsize=(14, 10), facecolor='#f8fafc')
        ax.axis('off')
        
        ax.text(0.5, 0.95, f"IFUKUK 專業排班表 - {year}/{month}", ha='center', va='center', fontsize=26, weight='bold', fontproperties=prop, color='#0f172a')
        
        cols = ["週一 Mon", "週二 Tue", "週三 Wed", "週四 Thu", "週五 Fri", "週六 Sat", "週日 Sun"]
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
                    if is_closed: cell_text += "\n[全店公休]"
                    else:
                        for _, r in day_shifts.iterrows():
                            # 縮寫保持畫面整潔
                            s_short = r['Type'].replace("早班","早").replace("晚班","晚").replace("全班","全").replace("公休","休")
                            cell_text += f"● {r['Staff']} ({s_short})\n"
                    row_data.append(cell_text.strip())
            table_data.append(row_data)

        # 繪製高質感表格
        table = ax.table(cellText=table_data, loc='center', cellLoc='left', bbox=[0, 0, 1, 0.9])
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        
        for (i, j), cell in table.get_celld().items():
            cell.set_edgecolor('#cbd5e1')
            cell.set_text_props(fontproperties=prop, color='#334155')
            if i == 0:
                cell.set_text_props(weight='bold', fontproperties=prop, color='#475569')
                cell.set_facecolor('#e2e8f0')
                cell.set_height(0.06)
            else:
                cell.set_height(0.16)
                cell.set_valign('top')
                cell.set_facecolor('#ffffff')
                txt = cell.get_text().get_text()
                if "全店公休" in txt:
                    cell.set_facecolor('#fee2e2')
                    cell.get_text().set_color('#991b1b')
                    cell.get_text().set_weight('bold')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
        buf.seek(0); plt.close(fig)
        return buf
    except Exception as e: 
        return str(e) # 回傳精準錯誤碼給前端

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
    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班中心</h3></div>", unsafe_allow_html=True)
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
        for i, d in enumerate(days_map): cols[i].markdown(f"<div style='text-align:center;font-size:0.8rem;color:#64748b;font-weight:bold;'>{d}</div>", unsafe_allow_html=True)
        
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
                        if is_store_closed: html_content = "<div class='store-closed'><span style='color:white !important;'>🔴 全店公休</span></div>"
                        else:
                            for _, r in day_shifts.iterrows():
                                bg_color = "#EF4444" if r['Type'] == "公休" else staff_color_map.get(r['Staff'], "#6B7280")
                                html_content += f"<span class='shift-pill' style='background-color:{bg_color};'><span style='color:white !important;'>{r['Staff']} - {r['Type']}</span></span>"
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
                    if is_store_closed: content_html = "<span class='store-closed-mobile'><span style='color:#EF4444 !important;'>🔴 全店公休</span></span>"
                    elif not day_shifts.empty:
                        for _, r in day_shifts.iterrows():
                            bg_color = "#EF4444" if r['Type'] == "公休" else staff_color_map.get(r['Staff'], "#6B7280")
                            content_html += f"<span class='shift-pill' style='background-color:{bg_color};'><span style='color:white !important;'>{r['Staff']} {r['Type']}</span></span>"
                    else: content_html = "<span style='color:#94a3b8;font-size:0.8rem;'>尚無排班</span>"

                    st.markdown(f"""
                    <div class='mobile-day-row'>
                        <div class='mobile-day-date'>{day}<br><span style='font-size:0.7rem;color:#64748b !important;'>{weekday_str}</span></div>
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
            
            # V116.0 徹底解決手機排版雜亂的終極方案 (Emoji Block Formatting)
            if st.button("📤 生成 LINE 通告文字 (行動端優化版)", use_container_width=True):
                line_txt = f"📅 【IFUKUK {sel_month}月班表公告】\n"
                line_txt += "━━━━━━━━━━━━━━\n"
                
                m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
                m_data = shifts_df[shifts_df['Date'].str.startswith(m_prefix)].sort_values(['Date', 'Staff'])
                
                if not m_data.empty:
                    last_date = ""
                    for _, r in m_data.iterrows():
                        d_obj = datetime.strptime(r['Date'], "%Y-%m-%d")
                        weekday_str = ["一","二","三","四","五","六","日"][d_obj.weekday()]
                        d_short = f"{d_obj.month}/{d_obj.day} (週{weekday_str})"
                        
                        if d_short != last_date: 
                            line_txt += f"\n🔹 {d_short}\n"
                            last_date = d_short
                            
                        if r['Staff'] == "全店" and r['Type'] == "公休": 
                            line_txt += f"🔴 全店公休\n"
                        else: 
                            note_str = f" ({r['Note']})" if pd.notna(r['Note']) and r['Note'].strip() != "" else ""
                            line_txt += f"👤 {r['Staff']} ({r['Type']}){note_str}\n"
                    
                    st.text_area("請複製下方文字，貼上至 LINE 絕對整齊：", value=line_txt, height=250)
                else: st.warning("本月尚無任何排班資料")

            # V116.0 強固型伺服器繞過繪圖機制
            if st.button("📸 一鍵生成班表截圖 (Image)", use_container_width=True):
                with st.spinner("量子繪圖引擎啟動中 (首次需時3秒)..."):
                    img_buf = generate_roster_image_buffer(sel_year, sel_month, shifts_df, calendar.monthrange(sel_year, sel_month)[1], staff_color_map)
                    
                    if isinstance(img_buf, io.BytesIO):
                        st.image(img_buf, caption=f"IFUKUK_{sel_year}_{sel_month}_Roster", use_container_width=True)
                        st.download_button("💾 下載高清 PNG 圖片", data=img_buf, file_name=f"IFUKUK_{sel_year}_{sel_month}_Roster.png", mime="image/png", use_container_width=True)
                    else: 
                        st.error(f"❌ 伺服器繪圖引擎阻擋。偵錯碼：\n`{img_buf}`\n(請截圖此訊息給工程師，通常是雲端主機封鎖了外部字型連線)")

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
            st.markdown("<div style='text-align:center; font-weight:900; font-size:2.5rem; margin-bottom:10px; color:#0f172a;'>IFUKUK</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; color:#64748b; font-size:0.9rem; margin-bottom:30px;'>OMEGA V116.0 OMNI-ROSTER</div>", unsafe_allow_html=True)
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

    # QUANTUM DATA FETCH
    df = get_data_safe(ws_items, SHEET_HEADERS)
    logs_df = get_data_safe(ws_logs, ["Timestamp", "User", "Action", "Details"]) 
    users_df = get_data_safe(ws_users, ["Name", "Password", "Role", "Status", "Created_At"])
    staff_list = users_df['Name'].tolist() if not users_df.empty and 'Name' in users_df.columns else []

    # QUANTUM TYPE CASTING
    for c in ["SKU", "Name", "Category", "Size", "Last_Updated", "Image_URL", "Orig_Currency"]: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost', 'Safety_Stock', 'Orig_Cost', 'Qty_CN']:
        if num not in df.columns: df[num] = 0
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    
    df['Safe_Level'] = df['Safety_Stock'].apply(lambda x: 5 if x == 0 else x)
    df['SKU'] = df['SKU'].astype(str)
    df['Style_Code'] = df['SKU'].apply(get_style_code)
    
    product_map = {r['SKU']: f"{r['Name']} ({r['Size']})" for _, r in df.iterrows()} if not df.empty else {}
    cost_map = {r['SKU']: r['Cost'] for _, r in df.iterrows()} if not df.empty else {}

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

    # Dashboard Metrics
    total_qty_tw = df['Qty'].sum() if not df.empty else 0
    total_qty_cn = df['Qty_CN'].sum() if not df.empty else 0
    total_qty = total_qty_tw + total_qty_cn
    total_cost = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum() if not df.empty else 0
    total_rev = (df['Qty'] * df['Price']).sum() if not df.empty else 0
    profit = total_rev - (df['Qty'] * df['Cost']).sum() if not df.empty else 0
    realized_revenue = calculate_realized_revenue(logs_df)
    sunk_cost = calculate_sunk_cost(logs_df, cost_map)
    
    rmb_stock_value = 0
    if not df.empty and 'Orig_Currency' in df.columns:
        rmb_items = df[df['Orig_Currency'] == 'CNY']
        if not rmb_items.empty: rmb_stock_value = ((rmb_items['Qty'] + rmb_items['Qty_CN']) * rmb_items['Orig_Cost']).sum()

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1: st.markdown(f"<div class='metric-card'><div class='metric-label'>📦 總庫存 (TW+CN)</div><div class='metric-value'>{total_qty:,}</div><div style='font-size:10px; color:#64748b;'>🇹🇼:{total_qty_tw} | 🇨🇳:{total_qty_cn}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='metric-card'><div class='metric-label'>💎 預估營收 (TW)</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='metric-card'><div class='metric-label'>💰 總資產成本</div><div class='metric-value'>${total_cost:,}</div><div style='font-size:11px;color:#64748b;'>含RMB原幣: ¥{rmb_stock_value:,}</div></div>", unsafe_allow_html=True)
    with m4: st.markdown(f"<div class='metric-card' style='background:#fef2f2 !important; border-color:#fecaca !important;'><div class='metric-label' style='color:#991b1b !important;'>📉 內部消耗 (沉沒成本)</div><div class='metric-value' style='color:#b91c1c !important;'>${sunk_cost:,}</div></div>", unsafe_allow_html=True)
    with m5: st.markdown(f"<div class='metric-card profit-card'><div class='metric-label'>📈 潛在毛利</div><div class='metric-value' style='color:#d97706 !important'>${profit:,}</div></div>", unsafe_allow_html=True)
    with m6: st.markdown(f"<div class='metric-card realized-card'><div class='metric-label'>💵 實際營收 (已售)</div><div class='metric-value' style='color:#059669 !important'>${realized_revenue:,}</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    tabs = st.tabs(["📊 視覺庫存", "🛒 POS", "📈 銷售戰情", "🎁 領用/稽核看板", "👔 矩陣管理", "📝 日誌", "👥 Admin", "🗓️ 排班"])

    with tabs[0]:
        inv_t1, inv_t2 = st.tabs(["📦 庫存巡報區 (Smart Alert)", "💰 成本與毛利總覽矩陣 (Cost Matrix)"])
        
        with inv_t1:
            if not df.empty:
                c1, c2 = st.columns([1, 1])
                with c1:
                    fig_pie = px.pie(df, names='Category', values='Qty', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='#0f172a', margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
                with c2:
                    top = df.groupby(['Style_Code', 'Name']).agg({'Qty':'sum'}).reset_index().sort_values(by='Qty', ascending=False).head(10)
                    fig_bar = px.bar(top, x='Qty', y='Name', orientation='h', text='Qty', color='Qty', color_continuous_scale=px.colors.qualitative.Pastel)
                    fig_bar.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='#0f172a', margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
            st.divider()
            c_search1, c_search2, c_search3 = st.columns([2, 1, 1])
            with c_search1: search_q = st.text_input("🔍 搜尋商品", placeholder="輸入貨號或品名...")
            with c_search2: filter_cat = st.selectbox("📂 分類篩選", ["全部"] + CAT_LIST)
            with c_search3: 
                st.markdown("<br>", unsafe_allow_html=True) 
                show_low_stock = st.toggle("🚨 僅顯示低庫存警報", value=False)
                
            gallery_df = df.copy()
            if search_q: gallery_df = gallery_df[gallery_df.apply(lambda x: search_q.lower() in str(x.values).lower(), axis=1)]
            if filter_cat != "全部": gallery_df = gallery_df[gallery_df['Category'] == filter_cat]
            if show_low_stock: gallery_df = gallery_df[gallery_df['Qty'] < gallery_df['Safe_Level']]
            
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
                    
                    group_safe = group.copy()
                    group_safe['size_sort'] = group_safe['Size'].apply(get_size_sort_key)
                    sorted_group = group_safe.sort_values('size_sort')
                    
                    stock_badges = ""
                    has_warning = False
                    restock_advice = 0
                    
                    for _, r in sorted_group.iterrows():
                        cls = "has-stock" if r['Qty'] > 0 else "no-stock"
                        if r['Qty'] < r['Safe_Level']: 
                            cls = "no-stock"
                            has_warning = True
                            restock_advice += (r['Safe_Level'] - r['Qty'])
                        stock_badges += f"<span class='stock-tag {cls}'><span>{r['Size']}:{r['Qty']}</span></span>"

                    warning_html = f"<span style='color:#ef4444; font-weight:bold; font-size:0.8rem; margin-left:10px;'>⚠️ 需補貨 (建議補 {restock_advice} 件)</span>" if has_warning else ""

                    with st.container(border=True):
                        st.markdown(f"""
                        <div class='inv-row'>
                            <img src='{img}' class='inv-img'>
                            <div class='inv-info'>
                                <div class='inv-title'>{name} {warning_html}</div>
                                <div class='inv-meta'>{style_code} | ${price}</div>
                                <div class='stock-tag-row'>{stock_badges}</div>
                                <div style='font-size:0.8rem; color:#64748b; margin-top:4px;'>
                                    🇹🇼 總庫存: <b>{total_qty_tw}</b> | 🇨🇳 中國倉: <b>{total_qty_cn}</b>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        with st.expander("⚙️ 進階編輯與庫存管理"):
                            tab_qty, tab_info, tab_del = st.tabs(["📦 數量微調", "✏️ 基礎資訊修改 (全尺寸套用)", "🗑️ 徹底刪除此款"])
                            
                            with tab_qty:
                                with st.form(f"qty_{style_code}"):
                                    i_tw = {}; i_cn = {}; g_cols = st.columns(4)
                                    for idx, r_data in enumerate(sorted_group.iterrows()):
                                        _, row = r_data
                                        with g_cols[idx%4]: 
                                            lbl = row['Size']; i_tw[row['SKU']] = st.number_input(f"TW {lbl}", value=int(row['Qty']), key=f"t_{row['SKU']}"); i_cn[row['SKU']] = st.number_input(f"CN {lbl}", value=int(row['Qty_CN']), key=f"c_{row['SKU']}")
                                    if st.form_submit_button("💾 儲存庫存變更", use_container_width=True):
                                        for tsku, n_tw in i_tw.items():
                                            if tsku in df['SKU'].tolist():
                                                n_cn = i_cn[tsku]; r = ws_items.find(tsku).row
                                                retry_action(ws_items.update_cell, r, 5, n_tw)
                                                retry_action(ws_items.update_cell, r, 13, n_cn)
                                                retry_action(ws_items.update_cell, r, 8, get_taiwan_time_str())
                                        st.cache_data.clear(); st.success("數量已更新"); time.sleep(0.5); st.rerun()

                            with tab_info:
                                with st.form(f"info_{style_code}"):
                                    st.caption(f"修改此處資訊將同步套用於 {style_code} 的所有尺寸。")
                                    c_i1, c_i2 = st.columns(2)
                                    new_name = c_i1.text_input("品名", value=name)
                                    new_cat = c_i2.selectbox("分類", CAT_LIST, index=CAT_LIST.index(first_row['Category']) if first_row['Category'] in CAT_LIST else 0)
                                    
                                    c_i3, c_i4 = st.columns(2)
                                    new_price = c_i3.number_input("終端售價", value=int(first_row['Price']))
                                    new_orig_curr = c_i4.selectbox("原幣別", ["TWD", "CNY"], index=["TWD", "CNY"].index(first_row['Orig_Currency']) if first_row['Orig_Currency'] in ["TWD", "CNY"] else 0)
                                    
                                    c_i5, c_i6 = st.columns(2)
                                    new_orig_cost = c_i5.number_input("原幣成本", value=int(first_row['Orig_Cost']))
                                    new_safe = c_i6.number_input("安全庫存警告線", value=int(first_row['Safety_Stock']))
                                    
                                    new_img_url = st.text_input("直接輸入圖片網址 (若有)", value=first_row['Image_URL'])
                                    new_img_file = st.file_uploader("或上傳新圖片覆蓋", key=f"img_{style_code}")
                                    
                                    if st.form_submit_button("✅ 儲存商品資訊覆蓋", type="primary", use_container_width=True):
                                        final_img = upload_image_to_imgbb(new_img_file) if new_img_file else new_img_url
                                        final_cost = int(new_orig_cost * st.session_state['exchange_rate']) if new_orig_curr == "CNY" else new_orig_cost
                                        
                                        all_vals = ws_items.get_all_values()
                                        for idx, r_data in enumerate(all_vals):
                                            if idx == 0: continue
                                            if get_style_code(r_data[0]) == style_code:
                                                row_num = idx + 1
                                                retry_action(ws_items.update_cell, row_num, 2, new_name)
                                                retry_action(ws_items.update_cell, row_num, 3, new_cat)
                                                retry_action(ws_items.update_cell, row_num, 6, new_price)
                                                retry_action(ws_items.update_cell, row_num, 7, final_cost)
                                                retry_action(ws_items.update_cell, row_num, 8, get_taiwan_time_str())
                                                retry_action(ws_items.update_cell, row_num, 9, final_img)
                                                retry_action(ws_items.update_cell, row_num, 10, new_safe)
                                                retry_action(ws_items.update_cell, row_num, 11, new_orig_curr)
                                                retry_action(ws_items.update_cell, row_num, 12, new_orig_cost)
                                        st.cache_data.clear(); st.success("商品資訊已全數同步更新！"); time.sleep(1); st.rerun()

                            with tab_del:
                                st.warning("🔴 警告：按下此按鈕將永久刪除此款式的所有庫存資料。")
                                if st.button(f"🗑️ 確認刪除 {style_code}", key=f"del_{style_code}", use_container_width=True):
                                    all_vals = ws_items.get_all_values()
                                    rows_to_del = [idx + 1 for idx, r in enumerate(all_vals) if idx > 0 and get_style_code(r[0]) == style_code]
                                    for r_idx in reversed(rows_to_del): retry_action(ws_items.delete_rows, r_idx)
                                    st.cache_data.clear(); st.success(f"{style_code} 已徹底刪除"); time.sleep(1); st.rerun()

                c_p4, c_p5, c_p6 = st.columns([1, 2, 1])
                with c_p4: 
                    if st.button("◀", key="p_dn_prev", use_container_width=True, disabled=(curr_page==1)): st.session_state['inv_page'] -= 1; st.rerun()
                with c_p5: st.markdown(f"<div style='text-align:center;font-weight:bold;padding-top:10px;'>{curr_page} / {total_pages}</div>", unsafe_allow_html=True)
                with c_p6:
                    if st.button("▶", key="p_dn_next", use_container_width=True, disabled=(curr_page==total_pages)): st.session_state['inv_page'] += 1; st.rerun()

            else: st.info("查無符合條件的商品")

        with inv_t2:
            st.markdown("#### 💰 成本與定價總覽矩陣 (Cost & Margin Matrix)")
            st.markdown("此頁面統一匯總所有商品的 **人民幣成本 (RMB) / 台幣成本 (TWD) / 定價 / 單件毛利**，方便老闆隨時掌控利潤空間。")
            if not df.empty:
                cost_df = df[['SKU', 'Name', 'Category', 'Orig_Currency', 'Orig_Cost', 'Cost', 'Price', 'Qty', 'Qty_CN']].copy()
                cost_df['毛利 (TWD)'] = cost_df['Price'] - cost_df['Cost']
                cost_df['毛利率 (%)'] = (cost_df['毛利 (TWD)'] / cost_df['Price'] * 100).fillna(0).round(1).astype(str) + "%"
                cost_df.columns = ['貨號 (SKU)', '品名', '分類', '原幣別', '原幣成本(¥)', '台幣成本($)', '終端定價($)', 'TW現貨', 'CN現貨', '單件毛利($)', '毛利率(%)']
                st.dataframe(cost_df, use_container_width=True, hide_index=True)
            else:
                st.info("尚無商品數據。")

    with tabs[1]:
        c_l, c_r = st.columns([3, 2])
        with c_l:
            st.markdown("##### 🛍️ POS 快速結帳區")
            
            st.markdown("<div class='barcode-form'>", unsafe_allow_html=True)
            with st.form("barcode_scanner", clear_on_submit=True):
                bc_input = st.text_input("🎯 條碼/貨號快速掃描 (支援掃描槍，按 Enter 直接加入)")
                bc_submit = st.form_submit_button("掃描")
                if bc_submit and bc_input:
                    bc_match = df[df['SKU'] == bc_input.strip()]
                    if not bc_match.empty:
                        bc_item = bc_match.iloc[0]
                        if bc_item['Qty'] > 0:
                            st.session_state['pos_cart'].append({"sku":bc_item['SKU'],"name":bc_item['Name'],"size":bc_item['Size'],"price":bc_item['Price'],"qty":1,"subtotal":bc_item['Price']})
                            st.success(f"✅ 已掃描加入: {bc_item['Name']} ({bc_item['Size']})")
                        else:
                            st.error(f"❌ 庫存不足: {bc_item['Name']} 已售完")
                    else:
                        st.error(f"⚠️ 找不到條碼: {bc_input}")
            st.markdown("</div>", unsafe_allow_html=True)

            cats_available = list(df['Category'].unique()) if not df.empty else []
            all_cats = sorted(list(set(CAT_LIST + cats_available)))
            col_s1, col_s2 = st.columns([2,1])
            q = col_s1.text_input("手動搜尋 (品名/貨號)", placeholder="輸入關鍵字...", label_visibility="collapsed")
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
                            stock_clr = "#166534" if item['Qty'] > 0 else "#991b1b"
                            st.markdown(f"""
                            <div class='pos-card'>
                                <div class='pos-img'><img src='{render_image_url(item['Image_URL'])}' style='width:100%;height:100%;object-fit:cover;'></div>
                                <div class='pos-content'>
                                    <div class='pos-title'>{item['Name']}</div>
                                    <div class='pos-meta'>{item['Size']} | {item['Category']}</div>
                                    <div class='pos-price-row'>
                                        <div class='pos-price'>${item['Price']}</div>
                                        <div class='pos-stock' style='color:{stock_clr}; font-weight:bold;'>現貨:{item['Qty']}</div>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if item['Qty'] > 0:
                                if st.button("➕ 加入購物車", key=f"add_{item['SKU']}", use_container_width=True):
                                    st.session_state['pos_cart'].append({"sku":item['SKU'],"name":item['Name'],"size":item['Size'],"price":item['Price'],"qty":1,"subtotal":item['Price']})
                                    st.toast(f"已加入 {item['Name']}")
                            else:
                                st.button("❌ 已售完", key=f"out_{item['SKU']}", use_container_width=True, disabled=True)
            else: st.info("無商品")
        
        with c_r:
            st.markdown("##### 🧾 當前購物車 (實時毛利試算)")
            with st.container():
                st.markdown("<div class='cart-box'>", unsafe_allow_html=True)
                if st.session_state['pos_cart']:
                    base_raw = sum(i['subtotal'] for i in st.session_state['pos_cart'])
                    for i in st.session_state['pos_cart']: 
                        st.markdown(f"<div class='cart-item'><span>{i['name']} ({i['size']}) x{i['qty']}</span><b>${i['subtotal']}</b></div>", unsafe_allow_html=True)
                    if st.button("🗑️ 清空購物車"): st.session_state['pos_cart']=[]; st.rerun()
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
                    
                    total_cart_cost = 0
                    for cart_item in st.session_state['pos_cart']:
                        match_item = df[df['SKU'] == cart_item['sku']]
                        if not match_item.empty:
                            total_cart_cost += int(match_item['Cost'].values[0]) * cart_item['qty']
                    
                    est_profit = final_total - total_cart_cost
                    est_margin = round((est_profit / final_total * 100), 1) if final_total > 0 else 0
                    
                    note_str = " ".join(note_arr)
                    st.markdown(f"<div style='font-size:2rem; font-weight:900; color:#0f172a; text-align:right;'>應收: ${final_total}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:right; color:#059669; font-weight:bold; margin-bottom:15px;'>💡 本單預估毛利: ${est_profit} ({est_margin}%)</div>", unsafe_allow_html=True)
                    
                    sale_who = st.selectbox("經手人員", [st.session_state['user_name']] + [u for u in staff_list if u != st.session_state['user_name']])
                    sale_ch = st.selectbox("銷售通路", ["門市","官網","直播","網路","其他"]) 
                    pay = st.selectbox("付款方式", ["現金","刷卡","轉帳","禮券","其他"])
                    note = st.text_input("備註說明")
                    
                    if st.button("✅ 確認結帳 (防超賣雙重驗證)", type="primary", use_container_width=True):
                        logs = []
                        valid = True
                        for item in st.session_state['pos_cart']:
                            cell = ws_items.find(item['sku'])
                            if cell:
                                live_stock = int(ws_items.cell(cell.row, 5).value)
                                if live_stock >= item['qty']:
                                    retry_action(ws_items.update_cell, cell.row, 5, live_stock - item['qty'])
                                    logs.append(f"{item['sku']} x{item['qty']}")
                                else: 
                                    st.error(f"❌ 防禦攔截：{item['name']} 雲端庫存已被其他人買走，目前剩餘 {live_stock} 件。請重試。")
                                    valid = False; break
                        
                        if valid:
                            content = f"Sale | Total:${final_total} | Items:{','.join(logs)} | Note:{note} {note_str} | Pay:{pay} | Channel:{sale_ch} | By:{sale_who}"
                            log_event(ws_logs, st.session_state['user_name'], "Sale", content)
                            st.session_state['pos_cart'] = []
                            st.cache_data.clear(); st.balloons(); st.success("結帳成功！庫存已同步"); time.sleep(1.5); st.rerun()
                else: st.info("🛒 目前購物車是空的")
                st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        st.subheader("📈 營運戰情室 (Financial Hub)")
        rev = (df['Qty'] * df['Price']).sum() if not df.empty else 0
        cost = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum() if not df.empty else 0
        profit = rev - (df['Qty'] * df['Cost']).sum() if not df.empty else 0
        real = calculate_realized_revenue(logs_df)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='metric-card'><div class='metric-label'>總預估營收</div><div class='metric-value'>${rev:,}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-label'>庫存總成本 (TWD)</div><div class='metric-value'>${cost:,}</div><div style='font-size:10px;'>含 RMB 原幣: ¥{rmb_stock_value:,}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><div class='metric-label'>潛在最高毛利</div><div class='metric-value' style='color:#d97706'>${profit:,}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card'><div class='metric-label'>已入帳營收 (實際)</div><div class='metric-value' style='color:#059669'>${real:,}</div></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown("##### 📅 結算週期與財務篩選 (全自動透視)")
        c_date1, c_date2 = st.columns(2)
        start_d = c_date1.date_input("分析起始日期", value=date.today().replace(day=1))
        end_d = c_date2.date_input("分析結束日期", value=date.today())
        
        sales_data = []
        if not logs_df.empty:
            s_logs = logs_df[logs_df['Action'] == 'Sale']
            for _, row in s_logs.iterrows():
                try:
                    ts_str = str(row['Timestamp']).split(' ')[0]
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
            fc1.markdown(f"<div class='finance-card'><div class='finance-lbl'>💰 現金收入</div><div class='finance-val'>${pay_stats.get('現金', 0):,}</div></div>", unsafe_allow_html=True)
            fc2.markdown(f"<div class='finance-card'><div class='finance-lbl'>🏦 轉帳收入</div><div class='finance-val'>${pay_stats.get('轉帳', 0):,}</div></div>", unsafe_allow_html=True)
            fc3.markdown(f"<div class='finance-card'><div class='finance-lbl'>💳 刷卡收入</div><div class='finance-val'>${pay_stats.get('刷卡', 0):,}</div></div>", unsafe_allow_html=True)
            fc4.markdown(f"<div class='finance-card'><div class='finance-lbl'>🎫 禮券/其他</div><div class='finance-val'>${pay_stats.get('禮券', 0) + pay_stats.get('其他', 0):,}</div></div>", unsafe_allow_html=True)
            st.markdown("---")

            c1, c2 = st.columns(2)
            with c1: 
                fig = px.pie(sdf, names='通路', values='金額', hole=0.4, title="📊 通路營收佔比", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='#0f172a', margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            with c2: 
                fig2 = px.bar(sdf.groupby('銷售員')['金額'].sum().reset_index(), x='銷售員', y='金額', title="🏆 人員業績排行", color='金額', color_continuous_scale=px.colors.sequential.Teal)
                fig2.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='#0f172a', margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("##### 📝 銷售明細總表 (含售後管理)")
            st.dataframe(sdf.drop(columns=['原始Log']), use_container_width=True)

            with st.expander("🛠️ 編輯/作廢訂單 (自動回補庫存系統聯動)"):
                sale_opts = sdf.apply(lambda x: f"{x['日期']} | ${x['金額']} | {x['明細'][:20]}...", axis=1).tolist()
                sel_sale = st.selectbox("選擇要處理的歷史訂單", ["..."] + sale_opts)
                
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
                        e_items = st.text_area("商品內容 (修改需依照原本格式)", value=curr_items_str)
                        c_e1, c_e2, c_e3 = st.columns(3)
                        e_total = c_e1.number_input("總金額", value=int(target_row['金額']))
                        e_ch = c_e2.selectbox("通路", ["門市","官網","直播","網路","其他"], index=["門市","官網","直播","網路","其他"].index(curr_ch) if curr_ch in ["門市","官網","直播","網路","其他"] else 0)
                        e_pay = c_e3.selectbox("付款", ["現金","刷卡","轉帳","禮券","其他"], index=["現金","刷卡","轉帳","禮券","其他"].index(curr_pay) if curr_pay in ["現金","刷卡","轉帳","禮券","其他"] else 0)
                        e_note = st.text_input("備註", value=curr_note)
                        
                        c_act1, c_act2 = st.columns(2)
                        if c_act1.form_submit_button("✅ 儲存修改 (聯動庫存)"):
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
                                    st.success("✅ 訂單已修正且庫存聯動完畢！"); time.sleep(1.5); st.rerun()
                            except Exception as e: st.error(f"系統錯誤: {e}")

                        if c_act2.form_submit_button("🗑️ 整筆作廢 (全數退回庫存)"):
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
                                st.success("已作廢！商品已退回庫存"); time.sleep(1.5); st.rerun()
                            except: st.error("作廢失敗")

        else: st.info("📊 本區間尚無銷售數據")

    with tabs[3]:
        st.markdown("### 🎁 領用與稽核戰情中心 (Audit Command Center)")
        
        c_add, c_board = st.columns([1, 2.5])
        
        with c_add:
            st.markdown("#### ➕ 快速領用登記")
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} {x['Size']}", axis=1).tolist() if not df.empty else []
            sel = st.selectbox("選擇商品 (將自動扣除庫存)", ["..."] + opts)
            if sel != "...":
                tsku = sel.split(" | ")[0]; tr = df[df['SKU'] == tsku].iloc[0]; st.info(f"當前台灣現貨: {tr['Qty']}")
                with st.form("internal"):
                    q = st.number_input("申請數量", 1); who = st.selectbox("領用人員", staff_list); rsn = st.selectbox("事由", ["公務", "公關", "福利", "報廢", "樣品", "遺失", "其他"]); n = st.text_input("專案/詳細備註")
                    if st.form_submit_button("✅ 送出並扣庫存", use_container_width=True):
                        cell = ws_items.find(tsku)
                        live_stock = int(ws_items.cell(cell.row, 5).value)
                        if live_stock >= q:
                            retry_action(ws_items.update_cell, cell.row, 5, live_stock - q)
                            log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{tsku} -{q} | {who} | {rsn} | {n} | Cost:{tr['Cost']}")
                            st.cache_data.clear(); st.success("登記成功！庫存已同步減少。"); time.sleep(1); st.rerun()
                        else:
                            st.error(f"庫存不足，無法領用！(雲端即時庫存剩餘: {live_stock})")

        with c_board:
            if not logs_df.empty:
                int_df = logs_df[logs_df['Action'] == "Internal_Use"].copy()
                if not int_df.empty:
                    parsed_data = []
                    for _, r in int_df.iterrows():
                        d = str(r['Details'])
                        try:
                            parts = d.split(' | ')
                            sku = parts[0].split(' -')[0].strip()
                            qty = int(parts[0].split(' -')[1])
                            user = parts[1].strip()
                            reason = parts[2].strip()
                            note = parts[3].strip() if len(parts) > 3 else ""
                            
                            unit_cost = 0
                            if len(parts) > 4 and "Cost:" in parts[4]:
                                unit_cost = int(parts[4].replace("Cost:", "").strip())
                            else:
                                unit_cost = cost_map.get(sku, 0)
                                
                            total_cost = unit_cost * qty
                            item_name = product_map.get(sku, sku)
                            
                            parsed_data.append({
                                "時間": r['Timestamp'], "商品": item_name, "SKU": sku, 
                                "數量": qty, "領用人": user, "原因": reason, "備註": note, 
                                "單位成本": unit_cost, "總消耗成本": total_cost
                            })
                        except: pass
                    
                    if parsed_data:
                        audit_df = pd.DataFrame(parsed_data)
                        total_items_used = audit_df['數量'].sum()
                        total_cost_used = audit_df['總消耗成本'].sum()
                        
                        k1, k2 = st.columns(2)
                        k1.markdown(f"<div class='metric-card' style='background:#fef2f2 !important;'><div class='metric-label'>📦 歷史累計領用總件數</div><div class='metric-value' style='color:#b91c1c !important;'>{total_items_used} 件</div></div>", unsafe_allow_html=True)
                        k2.markdown(f"<div class='metric-card' style='background:#fffbeb !important;'><div class='metric-label'>💸 歷史累計消耗總成本</div><div class='metric-value' style='color:#b45309 !important;'>${total_cost_used:,}</div></div>", unsafe_allow_html=True)
                        st.markdown("---")
                        
                        c_chart1, c_chart2 = st.columns(2)
                        with c_chart1:
                            fig_r = px.pie(audit_df, names='原因', values='數量', title="📊 領用原因佔比 (數量)", hole=0.3, color_discrete_sequence=px.colors.qualitative.Set2)
                            fig_r.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='#0f172a', margin=dict(t=0, b=0, l=0, r=0))
                            st.plotly_chart(fig_r, use_container_width=True)
                        with c_chart2:
                            user_cost = audit_df.groupby('領用人')['總消耗成本'].sum().reset_index()
                            fig_u = px.bar(user_cost, x='領用人', y='總消耗成本', title="👤 人員消耗成本排行", color='總消耗成本', color_continuous_scale='Reds')
                            fig_u.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='#0f172a', margin=dict(t=0, b=0, l=0, r=0))
                            st.plotly_chart(fig_u, use_container_width=True)

                        st.markdown("#### 📜 領用流水帳與細節 (可點擊表頭排序)")
                        st.dataframe(audit_df[['時間', '商品', '數量', '領用人', '原因', '總消耗成本', '備註']], use_container_width=True)

                    else:
                        st.info("資料格式舊版，無法生成圖表。未來的領用將以新格式完美呈現。")
                else:
                    st.info("尚無任何領用紀錄。")
            else:
                st.info("尚無任何領用紀錄。")

        st.divider()
        with st.expander("🛠️ 修正或刪除錯誤的領用紀錄 (系統將自動歸還庫存)"):
            if not logs_df.empty and 'int_df' in locals() and not int_df.empty:
                rev_opts = int_df.apply(lambda x: f"{x['Timestamp']} | {x['Details']}", axis=1).tolist()
                sel_rev = st.selectbox("選擇要修正的紀錄", ["..."] + rev_opts)
                
                if sel_rev != "...":
                    target_ts = sel_rev.split(" | ")[0]
                    orig_row = logs_df[logs_df['Timestamp'] == target_ts].iloc[0]
                    orig_detail = str(orig_row['Details'])
                    try:
                        parts = orig_detail.split(' | ')
                        orig_sku = parts[0].split(' -')[0].strip()
                        orig_qty = int(parts[0].split(' -')[1])
                        orig_who = parts[1].strip()
                        orig_reason = parts[2].strip()
                        orig_note = parts[3].strip() if len(parts) > 3 else ""
                        orig_cost_str = parts[4] if len(parts) > 4 else f"Cost:{cost_map.get(orig_sku, 0)}"
                    except: st.error("資料無法解析"); st.stop()

                    with st.form("edit_internal_log"):
                        st.info(f"正在編輯: {product_map.get(orig_sku, orig_sku)} (原數量: {orig_qty})")
                        new_q = st.number_input("修正為正確數量", value=orig_qty, min_value=1)
                        new_who = st.selectbox("修正領用人", staff_list, index=staff_list.index(orig_who) if orig_who in staff_list else 0)
                        new_rsn = st.selectbox("修正原因", ["公務", "公關", "福利", "報廢", "樣品", "遺失", "其他"], index=["公務", "公關", "福利", "報廢", "樣品", "遺失", "其他"].index(orig_reason) if orig_reason in ["公務", "公關", "福利", "報廢", "樣品", "遺失", "其他"] else 0)
                        new_note = st.text_input("修正備註", value=orig_note)
                        
                        c_edit_1, c_edit_2 = st.columns(2)
                        if c_edit_1.form_submit_button("✅ 更新紀錄並同步庫存"):
                            cell = ws_items.find(orig_sku)
                            if cell:
                                curr_stock = int(ws_items.cell(cell.row, 5).value)
                                final_stock = curr_stock + orig_qty - new_q 
                                retry_action(ws_items.update_cell, cell.row, 5, final_stock)
                                
                                all_logs = ws_logs.get_all_values()
                                for idx, row in enumerate(all_logs):
                                    if row[0] == target_ts: retry_action(ws_logs.delete_rows, idx + 1); break
                                log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{orig_sku} -{new_q} | {new_who} | {new_rsn} | {new_note} | {orig_cost_str}")
                                st.success("紀錄已完美更新！"); time.sleep(1); st.rerun()
                            else: st.error("找不到該商品SKU")

                        if c_edit_2.form_submit_button("🗑️ 撤銷此單 (全數歸還庫存)"):
                            cell = ws_items.find(orig_sku)
                            if cell:
                                curr_stock = int(ws_items.cell(cell.row, 5).value)
                                retry_action(ws_items.update_cell, cell.row, 5, curr_stock + orig_qty) 
                                all_logs = ws_logs.get_all_values()
                                for idx, row in enumerate(all_logs):
                                    if row[0] == target_ts: retry_action(ws_logs.delete_rows, idx + 1); break
                                st.success("已撤銷，庫存已歸還！"); time.sleep(1); st.rerun()

    with tabs[4]:
        st.markdown("<div class='mgmt-box'>", unsafe_allow_html=True)
        st.markdown("<div class='mgmt-title'>矩陣管理中心</div>", unsafe_allow_html=True)
        st.info("💡 提醒：庫存區的卡片已支援【單一商品的修改與刪除】，此處用於大批量的全域操作。")
        mt1, mt2 = st.tabs(["✨ 批量衍生商品", "⚡ 雙向調撥"])
        
        with mt1:
            mode = st.radio("模式", ["新系列", "衍生"], horizontal=True)
            a_sku, a_name = "", ""
            if mode == "新系列":
                c = st.selectbox("分類", CAT_LIST)
                if st.button("生成智慧貨號"): st.session_state['base'] = generate_smart_style_code(c, df['SKU'].tolist())
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
                cur = st.selectbox("幣別 (若選 CNY 系統將依左側匯率自動換算台幣成本)", ["TWD", "CNY"]); img = st.file_uploader("上傳圖片 (選填)")
                sz = {}; cols = st.columns(5)
                for i, s in enumerate(SIZE_ORDER): sz[s] = cols[i%5].number_input(s, min_value=0)
                if st.form_submit_button("寫入資料庫"):
                    url = upload_image_to_imgbb(img) if img else ""
                    fc = int(co * st.session_state['exchange_rate']) if cur == "CNY" else co
                    for s, q in sz.items():
                        if q > 0: retry_action(ws_items.append_row, [f"{bs}-{s}", nm, "New", s, q, pr, fc, get_taiwan_time_str(), url, 5, cur, co, 0])
                    st.cache_data.clear(); st.success("商品新增完成！成本已同步記錄。"); st.rerun()
        
        with mt2:
            st.info("💡 兩地倉庫雙向調撥。系統將自動增減兩地庫存數字。")
            t_opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} {x['Size']} (TW:{x['Qty']} / CN:{x['Qty_CN']})", axis=1).tolist()
            sel = st.selectbox("選擇要調撥的商品", ["..."] + t_opts)
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
                    log_event(ws_logs, st.session_state['user_name'], "Transfer", f"{sel_sku} TW to CN qty:{q}")
                    st.cache_data.clear(); st.success("調撥完成"); st.rerun()
                if c_act2.button("CN ➡️ TW (中國轉台灣)"):
                    row_idx = ws_items.find(sel_sku).row
                    retry_action(ws_items.update_cell, row_idx, 5, int(r['Qty'])+q)
                    retry_action(ws_items.update_cell, row_idx, 13, int(r['Qty_CN'])-q)
                    log_event(ws_logs, st.session_state['user_name'], "Transfer", f"{sel_sku} CN to TW qty:{q}")
                    st.cache_data.clear(); st.success("調撥完成"); st.rerun()

    with tabs[5]: 
        st.subheader("📝 系統全域日誌 (Log System)")
        l_q = st.text_input("🔍 搜尋關鍵字 (人員/動作/品名/金額)")
        if not logs_df.empty:
            view_df = logs_df.sort_index(ascending=False).copy()
            view_df.columns = ['時間', '操作人員', '動作類型', '內容詳情']
            action_map = {"Sale": "💰 銷售結帳", "Internal_Use": "🎁 內部領用", "Login": "🔑 登入", "Transfer": "📦 調撥", "Batch": "⚡ 批量"}
            view_df['動作類型'] = view_df['動作類型'].map(action_map).fillna(view_df['動作類型'])
            
            def translate_details(txt):
                txt_str = str(txt)
                for sku, info in product_map.items():
                    if sku in txt_str: txt_str = txt_str.replace(sku, f"[{info}]")
                return txt_str
            view_df['內容詳情'] = view_df['內容詳情'].apply(translate_details)
            
            if l_q: view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(l_q, case=False)).any(axis=1)]
            st.dataframe(view_df, use_container_width=True)

    with tabs[6]: 
        st.subheader("👥 人員與權限管理 (Admin Matrix)")
        if st.session_state['user_role'] == 'Admin':
            admin_view = users_df.copy()
            admin_view.columns = ['員工帳號', '密碼(已加密Hash)', '權限等級', '狀態', '建立時間']
            st.dataframe(admin_view, use_container_width=True)
            
            c_u1, c_u2 = st.columns(2)
            with c_u1:
                with st.expander("➕ 新增員工"):
                    with st.form("new_user"):
                        nu = st.text_input("設定帳號"); np = st.text_input("設定密碼"); nr = st.selectbox("權限", ["Staff", "Admin"])
                        if st.form_submit_button("開通帳號"):
                            retry_action(ws_users.append_row, [nu, make_hash(np), nr, "Active", get_taiwan_time_str()])
                            st.cache_data.clear(); st.success("帳號已開通"); st.rerun()
            with c_u2:
                with st.expander("🗑️ 刪除員工"):
                    du = st.selectbox("選擇要註銷的帳號", users_df['Name'].tolist())
                    if st.button("確認註銷此員工"):
                        cell = ws_users.find(du)
                        retry_action(ws_users.delete_rows, cell.row)
                        st.cache_data.clear(); st.success("帳號已註銷"); st.rerun()
        else:
            st.error("🔒 權限不足。僅 Admin 可訪問此區域。")
    
    with tabs[7]:
        render_roster_system(sh, staff_list, st.session_state['user_name'])

if __name__ == "__main__":
    main()
