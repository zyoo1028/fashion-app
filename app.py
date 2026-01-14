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
    page_title="IFUKUK ERP V110.4 FINAL FUSION", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【CSS 視覺核心：還原 V110.1 強制白底 & 手機 7 格並排】
# ==========================================
st.markdown("""
    <style>
        /* 1. 強制全域白底黑字 (V110.1 核心) */
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

        /* 卡片樣式 (V110.1 核心) */
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

        /* V110.1 Mobile Grid Force (黑科技：強制手機 7 欄並排) */
        [data-testid="column"] {
            min-width: 0px !important; /* 允許無限縮小 */
            flex: 1 1 0px !important;  /* 強制均分寬度 */
            padding: 0px 2px !important; /* 減少間距 */
        }
        
        /* 日曆表頭縮小 */
        .roster-header { background: #f1f5f9 !important; padding: 10px; border-radius: 12px; margin-bottom: 10px; border: 1px solid #e2e8f0; text-align: center; }
        .week-header { font-size: 0.6rem !important; color: #64748b; font-weight: bold; text-align: center; }

        /* 日期格子極限壓縮 */
        .day-cell { 
            border: 1px solid #e2e8f0; border-radius: 4px; 
            padding: 2px; min-height: 60px; /* 手機高度減少 */
            position: relative; margin-bottom: 2px; 
            background: #fff !important; 
            overflow: hidden;
        }
        
        .day-num { 
            font-size: 0.7rem !important; font-weight: bold; color: #64748b; 
            margin-bottom: 1px; text-align: center;
        }
        
        /* 班別膠囊極限縮小 */
        .shift-pill { 
            font-size: 0.55rem !important; /* 極小字體 */
            padding: 1px 2px; border-radius: 3px; 
            margin-bottom: 1px; color: white !important; 
            display: block; 
            text-align: center; font-weight: bold; 
            line-height: 1.1;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }

        .store-closed {
            background-color: #EF4444 !important; color: white !important;
            font-weight: 900; font-size: 0.6rem !important;
            display: flex; align-items: center; justify-content: center;
            height: 100%; border-radius: 4px; min-height: 50px;
            writing-mode: vertical-rl; /* 直式排列節省空間 */
        }
        
        /* 隱形按鈕覆蓋優化 */
        div.stButton > button:first-child {
            border-radius: 6px; height: 2.5em; font-weight: 700; 
            border: 1px solid #cbd5e1; background-color: #FFFFFF !important; 
            color: #0f172a !important; width: 100%; padding: 0px;
        }
        
        /* 數據卡片強制白底 */
        .metric-card { background: linear-gradient(145deg, #ffffff, #f8fafc) !important; color: black !important; }
        .metric-value { color: #0f172a !important; }

        /* 編輯模式提示框 */
        .edit-mode-box {
            border: 2px solid #3B82F6 !important;
            background-color: #EFF6FF !important;
            padding: 10px; border-radius: 8px; margin-bottom: 10px;
            text-align: center; font-weight: bold; color: #1E3A8A !important;
        }

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
# 🗓️ 排班系統 ELITE (V110.4 Final Fusion)
# ==========================================

SHIFT_COLORS = {
    "早班": "#3B82F6", "晚班": "#8B5CF6", "全班": "#10B981", 
    "代班": "#F59E0B", "公休": "#EF4444", "特休": "#DB2777", 
    "空班": "#6B7280", "事假": "#EC4899", "病假": "#14B8A6"
}

def get_staff_color_map(users):
    # 20色高對比色票 (固定分配)
    VP = ["#2563EB", "#059669", "#7C3AED", "#DB2777", "#D97706", "#DC2626", "#0891B2", "#4F46E5", "#BE123C", "#B45309", "#1D4ED8", "#047857", "#6D28D9", "#BE185D", "#B45309", "#B91C1C", "#0E7490", "#4338CA", "#9F1239", "#92400E"]
    cm = {}; su = sorted([u for u in users if u != "全店"])
    for i, u in enumerate(su): cm[u] = VP[i % len(VP)]
    return cm

# V110.4: 字型下載修復 (存到 /tmp) - 徹底解決繪圖失敗
def get_chinese_font_path():
    font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
    font_path = "/tmp/NotoSansCJKtc-Regular.otf"
    if not os.path.exists(font_path):
        try:
            r = requests.get(font_url, timeout=10)
            if r.status_code == 200:
                with open(font_path, 'wb') as f: f.write(r.content)
            else: return None
        except: return None
    return font_path

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
    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班中心 (手機最適化)</h3></div>", unsafe_allow_html=True)

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

    # V110.4: 強制使用 Grid Layout (手機適配)
    cal = calendar.monthcalendar(sel_year, sel_month)
    cols = st.columns(7)
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    for i, d in enumerate(days): cols[i].markdown(f"<div class='week-header'>{d}</div>", unsafe_allow_html=True)
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day != 0:
                    d_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    ds = shifts_df[shifts_df['Date'] == d_str] if not shifts_df.empty else pd.DataFrame()
                    
                    # 隱形按鈕覆蓋 -> 點擊進入編輯
                    if st.button(f"{day}", key=f"d_{d_str}", use_container_width=True):
                        st.session_state['roster_date'] = d_str
                        st.session_state['edit_target_staff'] = None # 重置編輯狀態
                        st.rerun()

                    is_closed = False
                    html = ""
                    if not ds.empty:
                        for _, r in ds.iterrows():
                            if r['Staff']=="全店" and r['Type']=="公休": is_closed=True; break
                    
                    if is_closed: html = "<div class='store-closed'>店休</div>"
                    elif not ds.empty:
                        for _, r in ds.iterrows():
                            bg = staff_color_map.get(r['Staff'], "#666") if r['Type']!="公休" else "#EF4444"
                            stype = r['Type'].replace("早班","早").replace("晚班","晚").replace("全班","全")
                            html += f"<span class='shift-pill' style='background:{bg}'>{r['Staff']}{stype}</span>"
                    
                    st.markdown(f"<div class='day-cell'><div class='day-num'>{day}</div>{html}</div>", unsafe_allow_html=True)
                else: st.markdown("<div style='min-height:50px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # 編輯區 (V110.4: 智慧編輯邏輯)
    c_edit, c_smart = st.columns([1, 1])
    with c_edit:
        if 'roster_date' in st.session_state:
            t_date = st.session_state['roster_date']
            st.markdown(f"#### ✏️ 編輯: {t_date}")
            ds = shifts_df[shifts_df['Date'] == t_date] if not shifts_df.empty else pd.DataFrame()
            
            # 狀態初始化
            if 'edit_target_staff' not in st.session_state: st.session_state['edit_target_staff'] = None

            is_closed = False
            if not ds.empty and ((ds['Staff']=="全店")&(ds['Type']=="公休")).any(): is_closed=True
            
            if is_closed:
                st.error("🔴 全店公休")
                if st.button("🔓 解除公休"):
                    all_v = ws_shifts.get_all_values()
                    for i, r in enumerate(all_v):
                        if len(r)>1 and r[0]==t_date and r[1]=="全店": retry_action(ws_shifts.delete_rows, i+1); break
                    st.success("已解除"); st.rerun()
            else:
                if not ds.empty:
                    st.caption("排班列表 (點擊✏️修改):")
                    for _, r in ds.iterrows():
                        c1, c2, c3 = st.columns([3, 1, 1])
                        with c1: st.write(f"{r['Staff']} ({r['Type']})")
                        with c2: 
                            if st.button("✏️", key=f"ed_{r['Staff']}_{t_date}"):
                                st.session_state['edit_target_staff'] = r['Staff']
                                st.session_state['edit_target_type'] = r['Type']
                                st.session_state['edit_target_note'] = r.get('Note','')
                                st.rerun()
                        with c3:
                            if st.button("🗑️", key=f"del_{r['Staff']}_{t_date}"):
                                all_v = ws_shifts.get_all_values()
                                for i, row in enumerate(all_v):
                                    if len(row)>1 and row[0]==t_date and row[1]==r['Staff']: retry_action(ws_shifts.delete_rows, i+1); break
                                st.success("已移除"); st.rerun()
                
                # 編輯表單
                target = st.session_state.get('edit_target_staff')
                if target:
                    st.markdown(f"<div class='edit-mode-box'>正在修改: {target}</div>", unsafe_allow_html=True)
                    s_idx = users_list.index(target) if target in users_list else 0
                    t_idx = list(SHIFT_COLORS.keys()).index(st.session_state['edit_target_type'])
                    n_val = st.session_state['edit_target_note']
                    btn_txt = "✅ 確認修改"
                else:
                    st.caption("新增排班:")
                    s_idx=0; t_idx=0; n_val=""; btn_txt = "➕ 新增排班"

                with st.form("shift_op"):
                    s = st.selectbox("人員", users_list, index=s_idx)
                    t = st.selectbox("班別", list(SHIFT_COLORS.keys()), index=t_idx)
                    n = st.text_input("備註", value=n_val)
                    c_sub1, c_sub2 = st.columns(2)
                    if c_sub1.form_submit_button(btn_txt):
                        all_v = ws_shifts.get_all_values()
                        # 若是編輯，刪除舊的 target; 若是新增，刪除該員當天舊的 (Upsert)
                        del_target = target if target else s
                        to_del = [i+1 for i, r in enumerate(all_v) if len(r)>1 and r[0]==t_date and r[1]==del_target]
                        for i in reversed(to_del): retry_action(ws_shifts.delete_rows, i)
                        
                        retry_action(ws_shifts.append_row, [t_date, s, t, n, "FALSE", user_name])
                        st.session_state['edit_target_staff'] = None
                        st.success("已更新"); time.sleep(0.5); st.rerun()
                    
                    if target and c_sub2.form_submit_button("❌ 取消"):
                        st.session_state['edit_target_staff'] = None; st.rerun()
                
                if not target and st.button("🔴 設定全店公休"):
                    all_v = ws_shifts.get_all_values() # Clean day
                    to_del = [i+1 for i, r in enumerate(all_v) if len(r)>0 and r[0]==t_date]
                    for i in reversed(to_del): retry_action(ws_shifts.delete_rows, i)
                    retry_action(ws_shifts.append_row, [t_date, "全店", "公休", "Store Closed", "FALSE", user_name])
                    st.success("已設定"); st.rerun()
        else: st.info("👈 點擊日期編輯")

    with c_smart:
        st.markdown("#### 🧠 智能工具")
        with st.expander("📤 LINE / 存圖 / 循環", expanded=True):
            if st.button("生成 LINE 通告 (精美版)"):
                txt = f"📅 【IFUKUK {sel_month}月班表公告】\n━━━━━━━━━━━━━━\n"
                mp = f"{sel_year}-{str(sel_month).zfill(2)}"
                md = shifts_df[shifts_df['Date'].str.startswith(mp)].sort_values(['Date','Staff'])
                if not md.empty:
                    last_d = ""
                    for _, r in md.iterrows():
                        if r['Date'] != last_d:
                            wd = ["週一","週二","週三","週四","週五","週六","週日"][datetime.strptime(r['Date'],"%Y-%m-%d").weekday()]
                            txt += f"\n【 {r['Date'][5:]} ({wd}) 】\n━━━━━━━━━━━━━━\n"; last_d = r['Date']
                        if r['Staff']=="全店" and r['Type']=="公休": txt += "🔴 全店公休 (Store Closed)\n"
                        else: txt += f"● {r['Staff']} : {r['Type']} {f'({r['Note']})' if r['Note'] else ''}\n"
                    st.text_area("內容", txt, height=200)
                else: st.warning("無資料")
            
            if st.button("班表存圖 (修復版)"):
                with st.spinner("下載字型與繪圖中..."):
                    ib = generate_roster_image_buffer(sel_year, sel_month, shifts_df, 30, staff_color_map)
                    if ib: st.image(ib); st.download_button("下載圖片", ib, f"roster_{sel_year}_{sel_month}.png", "image/png")
                    else: st.error("繪圖失敗")

            st.markdown("---")
            st.caption("循環排班:")
            wc_t1, wc_t2 = st.tabs(["人員", "公休"])
            week_map = {"週一":0, "週二":1, "週三":2, "週四":3, "週五":4, "週六":5, "週日":6}
            with wc_t1:
                p_s = st.selectbox("誰", users_list, key="wc_s")
                p_d = st.selectbox("週幾", list(week_map.keys()), key="wc_d")
                p_t = st.selectbox("班別", list(SHIFT_COLORS.keys()), key="wc_t")
                if st.button("執行人員"):
                    cal = calendar.monthcalendar(sel_year, sel_month); av = ws_shifts.get_all_values()
                    cnt=0
                    for w in cal:
                        d = w[week_map[p_d]]
                        if d!=0:
                            ds = f"{sel_year}-{str(sel_month).zfill(2)}-{str(d).zfill(2)}"
                            td = [i+1 for i,r in enumerate(av) if len(r)>1 and r[0]==ds and r[1]==p_s]
                            for i in reversed(td): retry_action(ws_shifts.delete_rows, i)
                            retry_action(ws_shifts.append_row, [ds, p_s, p_t, "Auto", "FALSE", user_name]); cnt+=1
                    st.success(f"完成 {cnt} 筆"); st.rerun()
            with wc_t2:
                sc_d = st.selectbox("週幾", list(week_map.keys()), key="sc_d")
                if st.button("執行公休"):
                    cal = calendar.monthcalendar(sel_year, sel_month); av = ws_shifts.get_all_values()
                    cnt=0
                    for w in cal:
                        d = w[week_map[sc_d]]
                        if d!=0:
                            ds = f"{sel_year}-{str(sel_month).zfill(2)}-{str(d).zfill(2)}"
                            td = [i+1 for i,r in enumerate(av) if len(r)>0 and r[0]==ds]
                            for i in reversed(td): retry_action(ws_shifts.delete_rows, i)
                            retry_action(ws_shifts.append_row, [ds, "全店", "公休", "Store Closed", "FALSE", user_name]); cnt+=1
                    st.success(f"完成 {cnt} 筆"); st.rerun()

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in']=False
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart']=[]
    if 'exchange_rate' not in st.session_state: st.session_state['exchange_rate'],_ = get_live_rate()

    sh = init_db()
    if not sh: st.error("Database Connection Error"); return

    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status"])

    if not st.session_state['logged_in']:
        c1,c2,c3=st.columns([1,2,1])
        with c2:
            st.markdown("<br><h1 style='text-align:center'>IFUKUK</h1>", unsafe_allow_html=True)
            with st.form("login"):
                u=st.text_input("ID"); p=st.text_input("PWD", type="password")
                if st.form_submit_button("LOGIN"):
                    udf = get_data_safe(ws_users, ["Name","Password","Role","Status"])
                    if udf.empty and u=="Boss" and p=="1234": retry_action(ws_users.append_row, ["Boss", make_hash("1234"), "Admin", "Active"]); st.rerun()
                    tgt = udf[(udf['Name']==u)&(udf['Status']=='Active')]
                    if not tgt.empty and (check_hash(p, tgt.iloc[0]['Password']) or p==tgt.iloc[0]['Password']):
                        st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=tgt.iloc[0]['Role']; log_event(ws_logs, u, "Login", "Success"); st.rerun()
                    else: st.error("Error")
        return

    render_navbar(st.session_state['user_name'][0])
    
    df = get_data_safe(ws_items, SHEET_HEADERS)
    logs_df = get_data_safe(ws_logs, ["Timestamp", "User", "Action", "Details"])
    udf = get_data_safe(ws_users, ["Name", "Role"])
    staff_list = udf['Name'].tolist() if not udf.empty else []

    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Image_URL", "Qty_CN"]
    for c in cols: 
        if c not in df.columns: df[c]=""
    for n in ['Qty','Price','Cost','Qty_CN']: df[n] = pd.to_numeric(df[n], errors='coerce').fillna(0).astype(int)
    
    df['SKU']=df['SKU'].astype(str); df['Style_Code']=df['SKU'].apply(get_style_code)
    pmap = {r['SKU']:f"{r['Name']} ({r['Size']})" for _,r in df.iterrows()}

    with st.sidebar:
        st.write(f"User: {st.session_state['user_name']}")
        if st.button("Logout"): st.session_state['logged_in']=False; st.rerun()

    tabs = st.tabs(["📊 庫存", "🛒 POS", "📈 戰情", "🎁 領用", "👔 管理", "📝 日誌", "👥 Admin", "🗓️ 排班"])

    with tabs[0]: # 庫存
        st.subheader("📦 庫存總覽")
        q = st.text_input("搜尋商品")
        vdf = df[df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)] if q else df
        if not vdf.empty:
            for i, r in vdf.head(20).iterrows():
                with st.expander(f"{r['Name']} ({r['Size']})"):
                    st.image(render_image_url(r['Image_URL']), width=100)
                    with st.form(f"upd_{r['SKU']}"):
                        n_tw = st.number_input("TW", value=int(r['Qty']))
                        n_cn = st.number_input("CN", value=int(r['Qty_CN']))
                        if st.form_submit_button("更新"):
                            ridx = ws_items.find(r['SKU']).row
                            retry_action(ws_items.update_cell, ridx, 5, n_tw)
                            retry_action(ws_items.update_cell, ridx, 13, n_cn)
                            st.success("已更新"); st.rerun()

    with tabs[1]: # POS
        c1, c2 = st.columns([2,1])
        with c1:
            q = st.text_input("POS 搜尋")
            pdf = df[df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)] if q else df.head(20)
            for _, r in pdf.iterrows():
                if st.button(f"➕ {r['Name']} ({r['Size']}) ${r['Price']}", key=f"pos_{r['SKU']}"):
                    st.session_state['pos_cart'].append(r.to_dict())
        with c2:
            st.write("🛒 購物車")
            total = sum(int(i['Price']) for i in st.session_state['pos_cart'])
            for i in st.session_state['pos_cart']: st.write(f"{i['Name']} ${i['Price']}")
            st.write(f"**Total: ${total}**")
            if st.button("結帳"):
                items_str = ",".join([f"{i['SKU']} x1" for i in st.session_state['pos_cart']])
                log_event(ws_logs, st.session_state['user_name'], "Sale", f"Total:${total} | Items:{items_str}")
                for i in st.session_state['pos_cart']:
                    cell = ws_items.find(i['SKU'])
                    if cell: retry_action(ws_items.update_cell, cell.row, 5, int(ws_items.cell(cell.row, 5).value)-1)
                st.session_state['pos_cart']=[]; st.success("完成"); st.rerun()
            if st.button("清空"): st.session_state['pos_cart']=[]; st.rerun()

    with tabs[3]: # 領用 (V110.4: 數據透視 & 備註統計)
        st.subheader("🎁 領用/稽核 (Pivot Analytics)")
        if not logs_df.empty:
            int_df = logs_df[logs_df['Action']=="Internal_Use"].copy()
            if not int_df.empty:
                # 解析資料
                parsed = []
                for _, r in int_df.iterrows():
                    d = r['Details']; note = "-"
                    # 格式: SKU -Qty | Who | Reason | Note
                    try:
                        pts = d.split(' | ')
                        sku_pt = pts[0].split(' -')
                        parsed.append({
                            "日期": r['Timestamp'][:10], "SKU": sku_pt[0], "數量": int(sku_pt[1]),
                            "人員": pts[1], "原因": pts[2], "備註": pts[3] if len(pts)>3 else "-"
                        })
                    except: pass
                
                pdf = pd.DataFrame(parsed)
                if not pdf.empty:
                    # 儀表板
                    m1, m2, m3 = st.columns(3)
                    m1.metric("本月領用總數", f"{pdf['數量'].sum()} 件")
                    top_user = pdf.groupby('人員')['數量'].sum().idxmax()
                    m2.metric("領用王", top_user)
                    top_reason = pdf.groupby('原因')['數量'].sum().idxmax()
                    m3.metric("最常原因", top_reason)
                    
                    st.markdown("---")
                    # 透視表
                    t1, t2 = st.tabs(["依人員", "依備註"])
                    with t1:
                        st.dataframe(pdf.groupby(['人員','原因'])['數量'].sum().unstack(fill_value=0), use_container_width=True)
                    with t2:
                        st.caption("依據備註 (Note) 統計，方便查看特定活動/場次的領用")
                        st.dataframe(pdf.groupby(['備註','SKU'])['數量'].sum().unstack(fill_value=0), use_container_width=True)

        with st.expander("新增領用"):
            sel = st.selectbox("商品", df['SKU'].tolist())
            q = st.number_input("數量", 1)
            who = st.selectbox("人", staff_list)
            rsn = st.selectbox("原因", ["公務","樣品","其他"])
            note = st.text_input("備註")
            if st.button("送出"):
                r = ws_items.find(sel).row
                retry_action(ws_items.update_cell, r, 5, int(ws_items.cell(r,5).value)-q)
                log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{sel} -{q} | {who} | {rsn} | {note}")
                st.success("OK"); st.rerun()

    with tabs[7]: # 排班
        render_roster_system(sh, staff_list, st.session_state['user_name'])

if __name__ == "__main__":
    main()
