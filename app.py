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
    page_title="IFUKUK ERP V110.0 MOBILE SUPREMACY", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【CSS 視覺核心：強制白底黑字 & 手機優化】
# ==========================================
st.markdown("""
    <style>
        /* 1. 強制全域白底黑字 */
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; }
        [data-testid="stHeader"] { background-color: #FFFFFF !important; }
        
        /* 2. 輸入框與文字優化 */
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {
            color: #000000 !important; background-color: #FFFFFF !important;
            -webkit-text-fill-color: #000000 !important; caret-color: #000000 !important;
            border-color: #E5E7EB !important;
        }
        div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #000000 !important; }
        label, .stMarkdown, h1, h2, h3, h4, h5, h6, p, span { color: #0f172a !important; }

        /* 3. 卡片視覺 */
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
        
        /* 庫存列表 */
        .inv-row { display: flex; align-items: start; gap: 12px; padding: 12px; border-radius: 12px; margin-bottom: 10px; }
        .inv-img { width: 90px; height: 90px; object-fit: cover; border-radius: 8px; flex-shrink: 0; background: #f1f5f9; }
        .inv-info { flex-grow: 1; }
        .inv-title { font-size: 1.1rem; font-weight: bold; color: #0f172a !important; margin-bottom: 4px; }
        
        /* V110 排班表 CSS (Desktop & Mobile) */
        .roster-header { background: #f1f5f9 !important; padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e2e8f0; text-align: center; }
        .day-cell { border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; min-height: 100px; position: relative; margin-bottom: 5px; background: #fff !important; }
        .day-num { font-size: 0.8rem; font-weight: bold; color: #64748b; margin-bottom: 2px; padding-left: 4px; }
        
        .mobile-day-row {
            background: #FFFFFF !important; border: 1px solid #e2e8f0; border-radius: 10px;
            padding: 12px; margin-bottom: 8px; display: flex; align-items: center;
            justify-content: space-between; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }
        .mobile-day-date {
            font-size: 1.1rem; font-weight: 900; color: #334155 !important;
            width: 50px; text-align: center; border-right: 2px solid #f1f5f9; margin-right: 10px;
        }
        .mobile-day-content { flex-grow: 1; }
        
        .shift-pill { 
            font-size: 0.75rem; padding: 4px 8px; border-radius: 6px; 
            margin-bottom: 4px; color: white !important; display: inline-block; 
            text-align: center; font-weight: bold; margin-right: 4px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }

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

# --- OMEGA 核心防護層 ---
def retry_action(func, *args, **kwargs):
    max_retries = 15
    for i in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Quota exceeded" in str(e) or "1006" in str(e) or "500" in str(e):
                time.sleep((1.5 ** i) + random.uniform(0.5, 1.5))
                continue
            else: raise e
    st.error("❌ 雲端同步失敗，請檢查網路。")
    return None

@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 找不到 Secrets 金鑰。"); st.stop()
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=10, show_spinner=False)
def get_data_safe(_ws, expected_headers=None):
    if _ws is None: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
    try:
        raw_data = _ws.get_all_values()
        if not raw_data or len(raw_data) < 2: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
        headers = raw_data[0]
        seen = {}; new_headers = []
        for h in headers:
            if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
            else: seen[h] = 0; new_headers.append(h)
        df = pd.DataFrame(raw_data[1:])
        if len(df.columns) < len(new_headers): 
            for _ in range(len(new_headers)-len(df.columns)): df[len(df.columns)] = ""
        df.columns = new_headers[:len(df.columns)]
        return df
    except: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()

@st.cache_resource(ttl=600)
def init_db():
    client = get_connection()
    try: return client.open_by_url(GOOGLE_SHEET_URL)
    except: return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except:
        try: ws = sh.add_worksheet(title, rows=100, cols=20); ws.append_row(headers); return ws
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
def render_image_url(u): return u if isinstance(u, str) and u.startswith("http") and len(u)>10 else "https://i.ibb.co/W31w56W/placeholder.png"
def upload_image_to_imgbb(img):
    try:
        if not IMGBB_API_KEY: return None
        pl = {"key":IMGBB_API_KEY, "image":base64.b64encode(img.getvalue()).decode('utf-8')}
        r = requests.post("https://api.imgbb.com/1/upload", data=pl)
        if r.status_code==200: return r.json()["data"]["url"]
    except: pass
    return None
def log_event(ws, u, a, d): retry_action(ws.append_row, [get_taiwan_time_str(), u, a, d])
def get_style_code(s): return str(s).strip().rsplit('-', 1)[0] if '-' in str(s) else str(s).strip()
SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
def get_size_sort_key(s): return SIZE_ORDER.index(s) if s in SIZE_ORDER else 99 
def generate_smart_style_code(cat, existing):
    p_map = {"上衣(Top)":"TOP", "褲子(Btm)":"BTM", "外套(Out)":"OUT", "套裝(Suit)":"SET", "鞋類(Shoe)":"SHOE", "包款(Bag)":"BAG", "帽子(Hat)":"HAT", "飾品(Acc)":"ACC", "其他(Misc)":"MSC"}
    p = f"{p_map.get(cat,'GEN')}-{(datetime.utcnow()+timedelta(hours=8)).strftime('%y%m')}"
    seq = 0
    for sk in existing:
        if str(sk).startswith(p+"-"):
            try: seq = max(seq, int(sk.split('-')[-1]))
            except: pass
    return f"{p}-{str(seq+1).zfill(3)}"
def calculate_realized_revenue(df):
    t = 0
    if not df.empty and 'Action' in df.columns:
        for _, r in df[df['Action']=='Sale'].iterrows():
            try: t += int(re.search(r'Total:\$(\d+)', r['Details']).group(1))
            except: pass
    return t

def render_navbar(u_init):
    d = (datetime.utcnow()+timedelta(hours=8)).strftime("%Y/%m/%d")
    st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; background:#fff; padding:15px; border-bottom:1px solid #eee; margin-bottom:15px;">
            <div><span style="font-size:18px; font-weight:900;">IFUKUK GLOBAL</span><br><span style="font-size:11px; color:#666;">{d}</span></div>
            <div style="width:36px; height:36px; background:#111; color:#fff; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold;">{u_init}</div>
        </div>
    """, unsafe_allow_html=True)

CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]

# ==========================================
# 🗓️ 排班系統 ELITE
# ==========================================
SHIFT_COLORS = {"早班":"#3B82F6", "晚班":"#8B5CF6", "全班":"#10B981", "代班":"#F59E0B", "公休":"#EF4444", "特休":"#DB2777", "空班":"#6B7280", "事假":"#EC4899", "病假":"#14B8A6"}
def get_staff_color_map(users):
    pal = ["#2563EB", "#059669", "#7C3AED", "#DB2777", "#D97706", "#DC2626", "#0891B2", "#4F46E5", "#BE123C", "#B45309"]
    return {u: pal[i%len(pal)] for i, u in enumerate(sorted([x for x in users if x!="全店"]))}

def get_chinese_font_path():
    fn = "NotoSansTC-Regular.otf"
    if not os.path.exists(fn):
        try:
            r = requests.get("https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf")
            with open(fn, 'wb') as f: f.write(r.content)
        except: return None
    return fn

def generate_roster_image_buffer(year, month, shifts_df, days_in_month, color_map):
    try:
        font_path = get_chinese_font_path()
        prop = fm.FontProperties(fname=font_path) if font_path else fm.FontProperties()
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.axis('off')
        ax.text(0.5, 0.96, f"IFUKUK Roster - {year}/{month}", ha='center', va='center', fontsize=22, weight='bold', fontproperties=prop)
        
        cal = calendar.monthcalendar(year, month)
        cols = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        table_data = [cols]
        for week in cal:
            row_data = []
            for day in week:
                if day == 0: row_data.append("")
                else:
                    d_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                    ds = shifts_df[shifts_df['Date'] == d_str]
                    is_cl = any((r['Staff']=="全店" and r['Type']=="公休") for _, r in ds.iterrows())
                    txt = f"{day}\n"
                    if is_cl: txt += "\n[全店公休]\nStore Closed"
                    else:
                        for _, r in ds.iterrows():
                            txt += f"{r['Staff']} ({r['Type'][0]})\n"
                    row_data.append(txt)
            table_data.append(row_data)

        table = ax.table(cellText=table_data, loc='center', cellLoc='left', bbox=[0, 0, 1, 0.9])
        table.auto_set_font_size(False); table.set_fontsize(11)
        
        for (i, j), cell in table.get_celld().items():
            if i == 0:
                cell.set_text_props(weight='bold', fontproperties=prop); cell.set_facecolor('#f3f4f6'); cell.set_height(0.05)
            else:
                cell.set_height(0.15); cell.set_valign('top'); cell.set_text_props(fontproperties=prop)
                if "全店公休" in cell.get_text().get_text(): cell.set_facecolor('#FECACA'); cell.get_text().set_color('#991B1B')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0); plt.close(fig)
        return buf
    except: return None

def render_roster_system(sh, users_list, user_name):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    if not ws_shifts: st.warning("Connecting..."); return
    shifts_df = get_data_safe(ws_shifts, ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    if not shifts_df.empty:
        if 'Shift_Type' in shifts_df.columns: shifts_df['Type'] = shifts_df['Shift_Type']
        if 'Type' not in shifts_df.columns: shifts_df['Type'] = '上班'
    else: shifts_df = pd.DataFrame(columns=["Date", "Staff", "Type", "Note", "Notify", "Updated_By"])

    staff_color_map = get_staff_color_map(users_list)
    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班中心</h3></div>", unsafe_allow_html=True)
    now = datetime.utcnow() + timedelta(hours=8)
    
    with st.container():
        c1, c2 = st.columns([1.5, 1])
        with c1:
            cy, cm = st.columns(2)
            sel_year = cy.number_input("年份", 2024, 2030, now.year, label_visibility="collapsed")
            month_map = {1:"1月", 2:"2月", 3:"3月", 4:"4月", 5:"5月", 6:"6月", 7:"7月", 8:"8月", 9:"9月", 10:"10月", 11:"11月", 12:"12月"}
            rev_m = {v:k for k,v in month_map.items()}
            sel_month_str = cm.selectbox("月份", list(month_map.values()), index=now.month-1, label_visibility="collapsed")
            sel_month = rev_m[sel_month_str]
        with c2:
            view_mode = st.radio("檢視", ["📅 月曆", "📝 列表"], horizontal=True, label_visibility="collapsed")

    st.markdown("---")
    if view_mode == "📅 月曆":
        cal = calendar.monthcalendar(sel_year, sel_month)
        cols = st.columns(7)
        for i, d in enumerate(["MON","TUE","WED","THU","FRI","SAT","SUN"]): cols[i].markdown(f"<div style='text-align:center;font-weight:bold;color:#888;'>{d}</div>", unsafe_allow_html=True)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day != 0:
                        d_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                        ds = shifts_df[shifts_df['Date'] == d_str]
                        if st.button(f"{day}", key=f"d_{d_str}", use_container_width=True):
                            st.session_state['roster_date'] = d_str; st.rerun()
                        
                        is_cl = any((r['Staff']=="全店" and r['Type']=="公休") for _,r in ds.iterrows())
                        c_html = ""
                        if is_cl: c_html = "<div class='store-closed'>休</div>"
                        else:
                            for _, r in ds.iterrows():
                                bg = staff_color_map.get(r['Staff'], "#666")
                                c_html += f"<span class='shift-pill' style='background:{bg};'>{r['Staff']}</span>"
                        st.markdown(f"<div class='day-cell'>{c_html}</div>", unsafe_allow_html=True)
                    else: st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True)
    else:
        cal = calendar.monthcalendar(sel_year, sel_month)
        for week in cal:
            for day in week:
                if day != 0:
                    d_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    ds = shifts_df[shifts_df['Date'] == d_str]
                    wk = ["一","二","三","四","五","六","日"][datetime(sel_year, sel_month, day).weekday()]
                    c_html = ""
                    is_cl = any((r['Staff']=="全店" and r['Type']=="公休") for _,r in ds.iterrows())
                    if is_cl: c_html = "<span class='store-closed-mobile'>全店公休</span>"
                    else:
                        for _, r in ds.iterrows():
                            bg = staff_color_map.get(r['Staff'], "#666")
                            c_html += f"<span class='shift-pill' style='background:{bg};'>{r['Staff']} {r['Type']}</span>"
                    
                    st.markdown(f"<div class='mobile-day-row'><div class='mobile-day-date'>{day}<br><span style='font-size:0.7rem;'>週{wk}</span></div><div class='mobile-day-content'>{c_html}</div></div>", unsafe_allow_html=True)
                    if st.button(f"編輯 {d_str}", key=f"l_{d_str}", use_container_width=True):
                        st.session_state['roster_date'] = d_str; st.rerun()

    st.markdown("---")
    ce, cs = st.columns(2)
    with ce:
        if 'roster_date' in st.session_state:
            td = st.session_state['roster_date']
            st.markdown(f"#### ✏️ {td}")
            ds = shifts_df[shifts_df['Date'] == td]
            if not ds.empty:
                for _, r in ds.iterrows():
                    if st.button(f"❌ {r['Staff']}", key=f"del_{r['Staff']}_{td}"):
                        av = ws_shifts.get_all_values()
                        for i, row in enumerate(av):
                            if len(row)>1 and row[0]==td and row[1]==r['Staff']: retry_action(ws_shifts.delete_rows, i+1); break
                        st.rerun()
            
            with st.form("add_s"):
                u = st.selectbox("人", users_list)
                t = st.selectbox("班", list(SHIFT_COLORS.keys()))
                n = st.text_input("註")
                if st.form_submit_button("➕"):
                    av = ws_shifts.get_all_values()
                    dl = [i+1 for i, row in enumerate(av) if len(row)>1 and row[0]==td and row[1]==u]
                    for i in reversed(dl): retry_action(ws_shifts.delete_rows, i)
                    retry_action(ws_shifts.append_row, [td, u, t, n, "FALSE", user_name])
                    st.rerun()
            
            if st.button("🔴 全店公休"):
                av = ws_shifts.get_all_values()
                dl = [i+1 for i, row in enumerate(av) if len(row)>0 and row[0]==td]
                for i in reversed(dl): retry_action(ws_shifts.delete_rows, i)
                retry_action(ws_shifts.append_row, [td, "全店", "公休", "Closed", "FALSE", user_name])
                st.rerun()
        else: st.info("👈 點擊日期編輯")

    with cs:
        with st.expander("📤 工具", expanded=True):
            if st.button("LINE 文字"):
                m_p = f"{sel_year}-{str(sel_month).zfill(2)}"
                md = shifts_df[shifts_df['Date'].str.startswith(m_p)].sort_values(['Date','Staff'])
                txt = f"【{sel_month}月班表】\n"
                ld = ""
                for _, r in md.iterrows():
                    dd = r['Date'][5:]
                    if dd != ld: txt += f"\n🗓️ {dd}\n"; ld = dd
                    txt += f" {r['Staff']} {r['Type']}\n"
                st.text_area("Copy", txt)
            
            if st.button("下載圖片"):
                b = generate_roster_image_buffer(sel_year, sel_month, shifts_df, 30, staff_color_map)
                if b: st.download_button("Download", b, f"roster.png", "image/png")

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False; st.session_state['user_name'] = ""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    if 'exchange_rate' not in st.session_state:
        r, s = get_live_rate()
        st.session_state['exchange_rate'] = r
    if 'inv_page' not in st.session_state: st.session_state['inv_page'] = 1

    sh = init_db()
    if not sh: st.error("DB Error"); st.stop()

    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    if not st.session_state['logged_in']:
        st.title("IFUKUK V110.0"); 
        with st.form("login"):
            u = st.text_input("ID"); p = st.text_input("PW", type="password")
            if st.form_submit_button("LOGIN"):
                udf = get_data_safe(ws_users, ["Name", "Password", "Role", "Status"])
                if udf.empty and u=="Boss" and p=="1234":
                    retry_action(ws_users.append_row, ["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                    st.success("Admin Created"); st.rerun()
                t = udf[(udf['Name']==u) & (udf['Status']=='Active')]
                if not t.empty and (check_hash(p, t.iloc[0]['Password']) or p==t.iloc[0]['Password']):
                    st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=t.iloc[0]['Role']; st.rerun()
                else: st.error("Error")
        return

    render_navbar(st.session_state['user_name'][0])
    df = get_data_safe(ws_items, SHEET_HEADERS)
    logs_df = get_data_safe(ws_logs, ["Timestamp", "User", "Action", "Details"]) 
    users_df = get_data_safe(ws_users, ["Name"])
    staff_list = users_df['Name'].tolist() if not users_df.empty else []

    for c in ["Qty", "Price", "Cost", "Qty_CN"]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str); df['Style_Code'] = df['SKU'].apply(get_style_code)
    
    with st.sidebar:
        st.write(f"User: {st.session_state['user_name']}")
        if st.button("Logout"): st.session_state['logged_in']=False; st.rerun()

    # Dashboard
    rev = calculate_realized_revenue(logs_df)
    st.metric("實際營收", f"${rev:,}")
    st.markdown("---")

    tabs = st.tabs(["📊 庫存", "🛒 POS", "📈 戰情", "🎁 領用", "👔 管理", "📝 日誌", "👥 Admin", "🗓️ 排班"])

    with tabs[0]: # Inventory
        q = st.text_input("Search SKU")
        vdf = df.copy()
        if q: vdf = vdf[vdf.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)]
        
        # Pagination
        items_per_page = 10
        total_pages = math.ceil(len(vdf) / items_per_page)
        curr_page = st.session_state['inv_page']
        if curr_page > total_pages: curr_page = total_pages
        if curr_page < 1: curr_page = 1
        st.session_state['inv_page'] = curr_page

        c_p1, c_p2, c_p3 = st.columns([1, 2, 1])
        with c_p1: 
            if st.button("◀", disabled=(curr_page==1)): st.session_state['inv_page'] -= 1; st.rerun()
        with c_p2: st.markdown(f"<div style='text-align:center;'>{curr_page} / {total_pages}</div>", unsafe_allow_html=True)
        with c_p3:
            if st.button("▶", disabled=(curr_page==total_pages)): st.session_state['inv_page'] += 1; st.rerun()
        
        start = (curr_page-1)*items_per_page
        show_df = vdf.iloc[start:start+items_per_page]
        
        for idx, row in show_df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1,3])
                c1.image(render_image_url(row['Image_URL']))
                c2.write(f"**{row['Name']}** ({row['SKU']})")
                c2.write(f"Size: {row['Size']} | Price: ${row['Price']}")
                c2.write(f"TW: {row['Qty']} | CN: {row['Qty_CN']}")
                with st.expander("Edit"):
                    with st.form(f"e_{row['SKU']}"):
                        nq = st.number_input("TW Qty", value=row['Qty'])
                        nc = st.number_input("CN Qty", value=row['Qty_CN'])
                        if st.form_submit_button("Save"):
                            r_idx = ws_items.find(row['SKU']).row
                            retry_action(ws_items.update_cell, r_idx, 5, nq)
                            retry_action(ws_items.update_cell, r_idx, 13, nc)
                            st.rerun()

    with tabs[1]: # POS
        c1, c2 = st.columns([3, 2])
        with c1:
            pq = st.text_input("Search POS")
            pdf = df.copy()
            if pq: pdf = pdf[pdf.astype(str).apply(lambda x: x.str.contains(pq, case=False)).any(axis=1)]
            for i, r in pdf.head(20).iterrows():
                if st.button(f"➕ {r['Name']} (${r['Price']})", key=f"p_{r['SKU']}"):
                    st.session_state['pos_cart'].append(r.to_dict())
        with c2:
            st.write("Cart")
            tot = 0
            for i in st.session_state['pos_cart']:
                st.write(f"{i['Name']} ${i['Price']}")
                tot += i['Price']
            st.write(f"Total: ${tot}")
            if st.button("Clear"): st.session_state['pos_cart']=[]; st.rerun()
            if st.button("Checkout"):
                items_log = []
                for i in st.session_state['pos_cart']:
                    cell = ws_items.find(i['SKU'])
                    curr = int(ws_items.cell(cell.row, 5).value)
                    retry_action(ws_items.update_cell, cell.row, 5, curr-1)
                    items_log.append(f"{i['SKU']} x1")
                log_event(ws_logs, st.session_state['user_name'], "Sale", f"Total:${tot} | Items:{','.join(items_log)}")
                st.session_state['pos_cart']=[]; st.success("Done"); st.rerun()

    with tabs[2]: # Dashboard
        st.write("Dashboard V110.0")
        st.dataframe(pd.DataFrame(logs_df).head(50))

    with tabs[3]: # Internal
        sku = st.selectbox("Item", df['SKU'].tolist())
        q = st.number_input("Qty", 1)
        if st.button("Submit Internal"):
            log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{sku} -{q}")
            st.success("Recorded")

    with tabs[4]: # Matrix
        st.write("Matrix Management")

    with tabs[5]: # Logs
        st.dataframe(logs_df)

    with tabs[6]: # Admin
        st.dataframe(users_df)

    with tabs[7]: # Roster
        render_roster_system(sh, staff_list, st.session_state['user_name'])

if __name__ == "__main__":
    main()
