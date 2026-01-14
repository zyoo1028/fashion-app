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
    page_title="IFUKUK ERP V110.1 VISUAL MASTER", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【CSS 視覺核心：強制白底 & 手機 Grid 優化】
# ==========================================
st.markdown("""
    <style>
        /* 1. 強制全域白底黑字 */
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; }
        [data-testid="stHeader"] { background-color: #FFFFFF !important; }
        
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {
            color: #000000 !important; background-color: #FFFFFF !important;
            -webkit-text-fill-color: #000000 !important; caret-color: #000000 !important;
            border-color: #E5E7EB !important;
        }
        div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #000000 !important; }
        label, .stMarkdown, h1, h2, h3, h4, h5, h6, p, span { color: #0f172a !important; }

        /* 卡片樣式 */
        .pos-card, .inv-row, .finance-card, .metric-card, .cart-box, .mgmt-box {
            background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important; color: #000000 !important;
        }
        
        .pos-img { width: 100%; height: 160px; object-fit: cover; background: #f9fafb; border-bottom: 1px solid #f3f4f6; }
        .pos-content { padding: 10px; flex-grow: 1; display: flex; flex-direction: column; }
        .pos-title { font-weight: bold; font-size: 1rem; margin-bottom: 4px; color: #111 !important; line-height: 1.3; }
        .pos-meta { font-size: 0.8rem; color: #666 !important; margin-bottom: 5px; }
        
        /* 庫存標籤 */
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

        /* V110.1 排班表 CSS (Mobile Grid Optimized) */
        .roster-header { background: #f1f5f9 !important; padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e2e8f0; text-align: center; }
        
        /* 響應式 Grid 格子: 手機上縮小字體與內距 */
        .day-cell { 
            border: 1px solid #e2e8f0; border-radius: 6px; 
            padding: 2px; min-height: 80px; /* 手機高度減少 */
            position: relative; margin-bottom: 4px; 
            background: #fff !important; 
            overflow: hidden;
        }
        
        /* 日期數字 */
        .day-num { 
            font-size: 0.8rem; font-weight: bold; color: #64748b; 
            margin-bottom: 2px; padding-left: 2px; 
        }
        
        /* 班別膠囊: 手機優化 */
        .shift-pill { 
            font-size: 0.65rem; /* 字體縮小 */
            padding: 2px 4px; border-radius: 4px; 
            margin-bottom: 2px; color: white !important; 
            display: block; /* 確保換行 */
            text-align: center; font-weight: bold; 
            box-shadow: 0 1px 1px rgba(0,0,0,0.1);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }

        /* 全店公休 */
        .store-closed {
            background-color: #EF4444 !important; color: white !important;
            font-weight: 900; font-size: 0.7rem;
            display: flex; align-items: center; justify-content: center;
            height: 100%; border-radius: 4px; min-height: 70px;
            text-align: center; line-height: 1.2;
        }
        
        /* 隱形按鈕覆蓋 */
        div.stButton > button:first-child {
            border-radius: 8px; height: 3.2em; font-weight: 700; 
            border: 1px solid #cbd5e1; background-color: #FFFFFF !important; 
            color: #0f172a !important; width: 100%;
        }
        
        /* 星期標頭 (手機縮小) */
        .week-header { font-size: 0.75rem; color: #94a3b8; font-weight: bold; text-align: center; }

    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- OMEGA 核心防護層 ---
def retry_action(func, *args, **kwargs):
    max_retries = 15
    for i in range(max_retries):
        try: return func(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Quota exceeded" in str(e) or "1006" in str(e) or "500" in str(e) or "503" in str(e):
                wait_time = (1.5 ** i) + random.uniform(0.5, 1.5)
                if i > 2: st.toast(f"⏳ 雲端同步中... ({i+1}/{max_retries})")
                time.sleep(wait_time); continue
            else: raise e
    st.error("❌ 同步失敗"); return None

@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets: st.error("❌ 找不到 Secrets"); st.stop()
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=10, show_spinner=False)
def get_data_safe(_ws, expected_headers=None):
    if _ws is None: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
    for attempt in range(5):
        try:
            raw = _ws.get_all_values()
            if not raw or len(raw) < 2: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            headers = raw[0]; rows = raw[1:]
            seen = {}; new_h = []
            for h in headers:
                if h in seen: seen[h]+=1; new_h.append(f"{h}_{seen[h]}")
                else: seen[h]=0; new_h.append(h)
            
            if expected_headers and "Qty_CN" in expected_headers and "Qty_CN" not in new_h:
                try: retry_action(_ws.update_cell, 1, len(new_h)+1, "Qty_CN"); new_h.append("Qty_CN"); raw = _ws.get_all_values(); rows = raw[1:]
                except: pass

            df = pd.DataFrame(rows)
            if not df.empty:
                if len(df.columns) < len(new_h):
                    for _ in range(len(new_h)-len(df.columns)): df[len(df.columns)]=""
                df.columns = new_h[:len(df.columns)]
            return df
        except: time.sleep(1.5**(attempt+1)); continue
    return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()

@st.cache_resource(ttl=600)
def init_db():
    try: return get_connection().open_by_url(GOOGLE_SHEET_URL)
    except: return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        try: ws = sh.add_worksheet(title, rows=100, cols=20); ws.append_row(headers); return ws
        except: return None
    except:
        try: time.sleep(2); return init_db().worksheet(title)
        except: return None

# --- 工具模組 ---
def get_taiwan_time_str(): return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
@st.cache_data(ttl=3600)
def get_live_rate():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/CNY", timeout=5)
        if r.status_code==200: return r.json()['rates']['TWD'], True
    except: pass
    return 4.50, False
def make_hash(p): return hashlib.sha256(str(p).encode()).hexdigest()
def check_hash(p, h): return make_hash(p) == h
def render_image_url(u):
    if not u or (isinstance(u, float) and math.isnan(u)): return "https://i.ibb.co/W31w56W/placeholder.png"
    s = str(u).strip(); return s if len(s)>10 and s.startswith("http") else "https://i.ibb.co/W31w56W/placeholder.png"
def upload_image_to_imgbb(img):
    if not IMGBB_API_KEY: return None
    try:
        res = requests.post("https://api.imgbb.com/1/upload", data={"key":IMGBB_API_KEY, "image":base64.b64encode(img.getvalue()).decode('utf-8')})
        if res.status_code==200: return res.json()["data"]["url"]
    except: pass; return None
def log_event(ws, u, a, d): retry_action(ws.append_row, [get_taiwan_time_str(), u, a, d])
def get_style_code(s): return str(s).strip().rsplit('-', 1)[0] if '-' in str(s) else str(s).strip()
SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
def get_size_sort_key(s): return SIZE_ORDER.index(s) if s in SIZE_ORDER else 99 
def generate_smart_style_code(cat, skus):
    pmap = {"上衣(Top)":"TOP", "褲子(Btm)":"BTM", "外套(Out)":"OUT", "套裝(Suit)":"SET", "鞋類(Shoe)":"SHOE", "包款(Bag)":"BAG", "帽子(Hat)":"HAT", "飾品(Acc)":"ACC", "其他(Misc)":"MSC"}
    p = f"{pmap.get(cat,'GEN')}-{(datetime.utcnow()+timedelta(hours=8)).strftime('%y%m')}"
    m = 0
    for s in skus:
        if str(s).startswith(p+"-"):
            try: m = max(m, int(s.replace(p+"-","").split("-")[0]))
            except: pass
    return f"{p}-{str(m+1).zfill(3)}"
def calculate_realized_revenue(df):
    t = 0
    if df.empty or 'Action' not in df.columns: return 0
    for _, r in df[df['Action']=='Sale'].iterrows():
        try: 
            m = re.search(r'Total:\$(\d+)', r['Details'])
            if m: t += int(m.group(1))
        except: pass
    return t

def render_navbar(ui):
    d = (datetime.utcnow()+timedelta(hours=8)).strftime("%Y/%m/%d")
    r = st.session_state.get('exchange_rate', 4.5)
    st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; background:#fff; padding:15px; border-bottom:1px solid #eee; margin-bottom:15px;">
            <div><span style="font-size:18px; font-weight:900; color:#111;">IFUKUK GLOBAL</span><br><span style="font-size:11px; color:#666; font-family:monospace;">{d} • Rate: {r}</span></div>
            <div style="width:36px; height:36px; background:#111; color:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold;">{ui}</div>
        </div>
    """, unsafe_allow_html=True)

CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]

# ==========================================
# 🗓️ 排班系統 ELITE (Module Rewrite V110.1)
# ==========================================

SHIFT_COLORS = {
    "早班": "#3B82F6", "晚班": "#8B5CF6", "全班": "#10B981", 
    "代班": "#F59E0B", "公休": "#EF4444", "特休": "#DB2777", 
    "空班": "#6B7280", "事假": "#EC4899", "病假": "#14B8A6"
}

def get_staff_color_map(users):
    VP = ["#2563EB", "#059669", "#7C3AED", "#DB2777", "#D97706", "#DC2626", "#0891B2", "#4F46E5", "#BE123C", "#B45309", "#1D4ED8", "#047857", "#6D28D9", "#BE185D", "#B45309", "#B91C1C", "#0E7490", "#4338CA", "#9F1239", "#92400E"]
    cm = {}; su = sorted([u for u in users if u != "全店"])
    for i, u in enumerate(su): cm[u] = VP[i % len(VP)]
    return cm

# V110.1: 字型修復 (自動下載)
def get_chinese_font_path():
    f_name = "NotoSansTC-Regular.otf"
    if not os.path.exists(f_name):
        try:
            r = requests.get("https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf")
            with open(f_name, 'wb') as f: f.write(r.content)
        except: return None
    return f_name

def generate_roster_image_buffer(year, month, shifts_df, days_in_month, color_map):
    try:
        fp = get_chinese_font_path()
        prop = fm.FontProperties(fname=fp) if fp else fm.FontProperties()
        
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
                    d_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                    ds = shifts_df[shifts_df['Date'] == d_str]
                    is_closed = False
                    if not ds.empty:
                        for _, r in ds.iterrows():
                            if r['Staff']=="全店" and r['Type']=="公休": is_closed=True; break
                    
                    txt = f"{day}\n"
                    if is_closed: txt += "\n[全店公休]"
                    else:
                        if not ds.empty:
                            for _, r in ds.iterrows():
                                stype = r['Type'].replace("早班","早").replace("晚班","晚").replace("全班","全")
                                txt += f"{r['Staff']} ({stype})\n"
                    row_data.append(txt)
            table_data.append(row_data)

        table = ax.table(cellText=table_data, loc='center', cellLoc='left', bbox=[0, 0, 1, 0.9])
        table.auto_set_font_size(False); table.set_fontsize(11)
        
        for (i, j), cell in table.get_celld().items():
            if i == 0: cell.set_text_props(weight='bold', fontproperties=prop); cell.set_facecolor('#f3f4f6'); cell.set_height(0.05)
            else:
                cell.set_height(0.15); cell.set_valign('top'); cell.set_text_props(fontproperties=prop)
                if "全店公休" in cell.get_text().get_text(): cell.set_facecolor('#FECACA'); cell.get_text().set_color('#991B1B')

        buf = io.BytesIO(); plt.savefig(buf, format='png', dpi=150, bbox_inches='tight'); buf.seek(0); plt.close(fig)
        return buf
    except: return None

def render_roster_system(sh, users_list, user_name):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    if ws_shifts is None: st.warning("⚠️ 系統連線忙碌中..."); return

    shifts_df = get_data_safe(ws_shifts, ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    if not shifts_df.empty:
        if 'Shift_Type' in shifts_df.columns and 'Type' not in shifts_df.columns: shifts_df['Type'] = shifts_df['Shift_Type']
        if 'Type' not in shifts_df.columns: shifts_df['Type'] = '上班'
    else: shifts_df = pd.DataFrame(columns=["Date", "Staff", "Type", "Note", "Notify", "Updated_By"])

    staff_color_map = get_staff_color_map(users_list)
    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班中心 (手機版)</h3></div>", unsafe_allow_html=True)

    now = datetime.utcnow() + timedelta(hours=8)
    with st.container():
        c1, c2 = st.columns([1.5, 1])
        with c1:
            cy, cm = st.columns(2)
            sel_year = cy.number_input("年份", 2024, 2030, now.year, label_visibility="collapsed")
            m_map = {1:"1月", 2:"2月", 3:"3月", 4:"4月", 5:"5月", 6:"6月", 7:"7月", 8:"8月", 9:"9月", 10:"10月", 11:"11月", 12:"12月"}
            rev_m = {v:k for k,v in m_map.items()}
            sel_m_str = cm.selectbox("月份", list(m_map.values()), index=list(m_map.values()).index(m_map[now.month]), label_visibility="collapsed")
            sel_month = rev_m[sel_m_str]
    
    st.markdown("---")

    # V110.1: 強制使用 Grid Layout (手機適配)
    cal = calendar.monthcalendar(sel_year, sel_month)
    cols = st.columns(7)
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    for i, d in enumerate(days): cols[i].markdown(f"<div class='week-header'>{d}</div>", unsafe_allow_html=True)
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day != 0:
                    d_str = f"{sel_year}-{str
