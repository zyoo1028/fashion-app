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
    page_title="IFUKUK ERP V110.10 TIME-SYNC FIXED", 
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
        [data-testid="stAppViewContainer"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #F8F9FA !important;
        }
        [data-testid="stHeader"] {
            background-color: #FFFFFF !important;
        }
        
        /* 2. 強制輸入框、選單文字顏色 */
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {
            color: #000000 !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: #000000 !important;
            caret-color: #000000 !important;
            border-color: #E5E7EB !important;
        }
        /* 下拉選單選項顏色 */
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        /* 文字標籤 */
        label, .stMarkdown, h1, h2, h3, h4, h5, h6, p, span {
            color: #0f172a !important;
        }

        /* 3. 優化卡片視覺 (加強陰影與邊框，確保白底) */
        .pos-card, .inv-row, .finance-card, .metric-card, .cart-box, .mgmt-box {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
            color: #000000 !important;
        }
        
        .pos-img { width: 100%; height: 160px; object-fit: cover; background: #f9fafb; border-bottom: 1px solid #f3f4f6; }
        .pos-content { padding: 10px; flex-grow: 1; display: flex; flex-direction: column; }
        .pos-title { font-weight: bold; font-size: 1rem; margin-bottom: 4px; color: #111 !important; line-height: 1.3; }
        .pos-meta { font-size: 0.8rem; color: #666 !important; margin-bottom: 5px; }
        
        /* 庫存透視標籤 */
        .stock-tag-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; margin-bottom: 5px; }
        .stock-tag { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; border: 1px solid transparent; }
        .stock-tag.has-stock { background-color: #dcfce7 !important; color: #166534 !important; border-color: #bbf7d0; }
        .stock-tag.no-stock { background-color: #f3f4f6 !important; color: #9ca3af !important; border-color: #e5e7eb; }
        
        /* 庫存列表 */
        .inv-row { display: flex; align-items: start; gap: 12px; padding: 12px; border-radius: 12px; margin-bottom: 10px; }
        .inv-img { width: 90px; height: 90px; object-fit: cover; border-radius: 8px; flex-shrink: 0; background: #f1f5f9; }
        .inv-info { flex-grow: 1; }
        .inv-title { font-size: 1.1rem; font-weight: bold; color: #0f172a !important; margin-bottom: 4px; }
        
        /* 財務看板 */
        .finance-card { padding: 15px; text-align: center; border-radius: 10px; }
        .finance-val { font-size: 1.4rem; font-weight: 900; color: #0f172a !important; }
        .finance-lbl { font-size: 0.8rem; color: #64748b !important; font-weight: bold; }

        /* V110 排班表 CSS (Desktop & Mobile) */
        .roster-header { background: #f1f5f9 !important; padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e2e8f0; text-align: center; }
        
        /* Desktop View */
        .day-cell { border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; min-height: 100px; position: relative; margin-bottom: 5px; background: #fff !important; }
        .day-num { font-size: 0.8rem; font-weight: bold; color: #64748b; margin-bottom: 2px; padding-left: 4px; }
        
        /* Mobile List View */
        .mobile-day-row {
            background: #FFFFFF !important;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }
        .mobile-day-date {
            font-size: 1.1rem; font-weight: 900; color: #334155 !important;
            width: 50px; text-align: center; border-right: 2px solid #f1f5f9; margin-right: 10px;
        }
        .mobile-day-content { flex-grow: 1; }
        
        /* 班別膠囊 */
        .shift-pill { 
            font-size: 0.75rem; padding: 4px 8px; border-radius: 6px; 
            margin-bottom: 4px; color: white !important; display: inline-block; 
            text-align: center; font-weight: bold; margin-right: 4px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }

        /* 全店公休樣式 */
        .store-closed {
            background-color: #EF4444 !important; color: white !important;
            font-weight: 900; font-size: 0.9rem;
            display: flex; align-items: center; justify-content: center;
            height: 100%; border-radius: 6px; min-height: 90px;
        }
        .store-closed-mobile {
            background-color: #FEF2F2 !important; color: #EF4444 !important;
            border: 1px solid #FCA5A5; padding: 5px 10px; border-radius: 6px;
            font-weight: bold; display: inline-block;
        }
        
        /* 數據卡片強制白底 */
        .metric-card { background: linear-gradient(145deg, #ffffff, #f8fafc) !important; color: black !important; }
        .metric-value { color: #0f172a !important; }
        
        /* 按鈕樣式 */
        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border: 1px solid #cbd5e1; background-color: #FFFFFF !important; color: #0f172a !important; width: 100%; }
        
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- OMEGA 核心防護層 V110.0 (Anti-Crash Logic) ---
def retry_action(func, *args, **kwargs):
    max_retries = 15
    for i in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Quota exceeded" in str(e) or "1006" in str(e) or "500" in str(e) or "503" in str(e):
                wait_time = (1.5 ** i) + random.uniform(0.5, 1.5)
                if i > 2:
                    st.toast(f"⏳ 雲端連線忙碌中... 自動重試 ({i+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                raise e
    st.error("❌ 雲端同步失敗，請檢查網路或稍後再試。")
    return None

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
    if _ws is None:
        return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()

    max_retries = 5
    for attempt in range(max_retries):
        try:
            raw_data = _ws.get_all_values()
            if not raw_data or len(raw_data) < 2: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
            
            headers = raw_data[0]
            seen = {}
            new_headers = []
            for h in headers:
                if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
                else: seen[h] = 0; new_headers.append(h)
            
            rows = raw_data[1:]
            
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
            time.sleep(1.5 ** (attempt + 1))
            continue
            
    return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()

@st.cache_resource(ttl=600)
def init_db():
    client = get_connection()
    try: return client.open_by_url(GOOGLE_SHEET_URL)
    except: return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        try:
            ws = sh.add_worksheet(title, rows=100, cols=20)
            ws.append_row(headers)
            return ws
        except: return None
    except Exception as e:
        try:
            time.sleep(2)
            sh_retry = init_db()
            return sh_retry.worksheet(title)
        except:
            return None

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
# 🗓️ 排班系統 ELITE (Module Rewrite V110.0)
# ==========================================

SHIFT_COLORS = {
    "早班": "#3B82F6", "晚班": "#8B5CF6", "全班": "#10B981", 
    "代班": "#F59E0B", "公休": "#EF4444", "特休": "#DB2777", 
    "空班": "#6B7280", "事假": "#EC4899", "病假": "#14B8A6"
}

def get_staff_color_map(users_list):
    VIBRANT_PALETTE = [
        "#2563EB", "#059669", "#7C3AED", "#DB2777", "#D97706", 
        "#DC2626", "#0891B2", "#4F46E5", "#BE123C", "#B45309",
        "#1D4ED8", "#047857", "#6D28D9", "#BE185D", "#B45309",
        "#B91C1C", "#0E7490", "#4338CA", "#9F1239", "#92400E"
    ]
    color_map = {}
    sorted_users = sorted([u for u in users_list if u != "全店"])
    for i, user in enumerate(sorted_users):
        color_map[user] = VIBRANT_PALETTE[i % len(VIBRANT_PALETTE)]
    return color_map

# V110.0: 強制下載中文字型，解決繪圖失敗問題
def get_chinese_font_path():
    font_filename = "NotoSansTC-Regular.otf"
    if not os.path.exists(font_filename):
        # 從 Google Fonts 鏡像或 GitHub 下載
        url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
        try:
            r = requests.get(url)
            with open(font_filename, 'wb') as f:
                f.write(r.content)
        except:
            return None
    return font_filename

def generate_roster_image_buffer(year, month, shifts_df, days_in_month, color_map):
    try:
        # V110.0: 使用下載的字型
        font_path = get_chinese_font_path()
        prop = fm.FontProperties(fname=font_path) if font_path else fm.FontProperties()
        
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.axis('off')
        
        title = f"IFUKUK Roster - {year}/{month}"
        ax.text(0.5, 0.96, title, ha='center', va='center', fontsize=22, weight='bold', fontproperties=prop)
        
        cols = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cal = calendar.monthcalendar(year, month)
        
        table_data = []
        table_data.append(cols)
        
        for week in cal:
            row_data = []
            for day in week:
                if day == 0:
                    row_data.append("")
                else:
                    date_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == date_str]
                    
                    is_store_closed = False
                    if not day_shifts.empty:
                        for _, r in day_shifts.iterrows():
                            if r['Staff'] == "全店" and r['Type'] == "公休": is_store_closed = True; break
                    
                    cell_text = f"{day}\n"
                    if is_store_closed:
                        cell_text += "\n[全店公休]\nStore Closed"
                    else:
                        if not day_shifts.empty:
                            for _, r in day_shifts.iterrows():
                                s_type = r['Type']
                                s_short = s_type.replace("早班","早").replace("晚班","晚").replace("全班","全").replace("公休","休")
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
                cell.set_text_props(fontproperties=prop) # 套用中文字型
                txt = cell.get_text().get_text()
                if "全店公休" in txt:
                    cell.set_facecolor('#FECACA')
                    cell.get_text().set_color('#991B1B')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf
    except Exception as e:
        return None

def render_roster_system(sh, users_list, user_name):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    if ws_shifts is None:
        st.warning("⚠️ 系統正在全力與 Google 連線，請稍候 3 秒後重新整理頁面...")
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
    
    # V110.0: 排班控制區塊優化 (Mobile Friendly)
    with st.container():
        c_ctrl1, c_ctrl2 = st.columns([1.5, 1])
        with c_ctrl1:
            c_y, c_m = st.columns(2)
            sel_year = c_y.number_input("年份", 2024, 2030, now.year, label_visibility="collapsed")
            month_map = {1:"1月 (Jan)", 2:"2月 (Feb)", 3:"3月 (Mar)", 4:"4月 (Apr)", 5:"5月 (May)", 6:"6月 (Jun)", 
                         7:"7月 (Jul)", 8:"8月 (Aug)", 9:"9月 (Sep)", 10:"10月 (Oct)", 11:"11月 (Nov)", 12:"12月 (Dec)"}
            rev_month_map = {v:k for k,v in month_map.items()}
            curr_m_str = month_map[now.month]
            sel_month_str = c_m.selectbox("月份", list(month_map.values()), index=list(month_map.values()).index(curr_m_str), label_visibility="collapsed")
            sel_month = rev_month_map[sel_month_str]
        
        with c_ctrl2:
            # V110.0: 檢視模式切換 (解決手機排版反人類問題)
            view_mode = st.radio("👁️ 檢視模式", ["📅 電腦月曆", "📝 手機列表"], horizontal=True, label_visibility="collapsed")

    st.markdown("---")

    # V110.0: 根據模式渲染不同介面
    if view_mode == "📅 電腦月曆":
        # --- 原有 Desktop Grid View ---
        cal = calendar.monthcalendar(sel_year, sel_month)
        cols = st.columns(7)
        days_map = ["MON 一", "TUE 二", "WED 三", "THU 四", "FRI 五", "SAT 六", "SUN 日"]
        for i, d in enumerate(days_map): 
            cols[i].markdown(f"<div style='text-align:center;font-size:0.8rem;color:#94a3b8;font-weight:bold;'>{d}</div>", unsafe_allow_html=True)
        
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

                        is_store_closed = False
                        if not day_shifts.empty:
                            for _, r in day_shifts.iterrows():
                                if r['Staff'] == "全店" and r['Type'] == "公休": is_store_closed = True; break

                        html_content = ""
                        if is_store_closed:
                            html_content = "<div class='store-closed'>🔴 全店公休</div>"
                        else:
                            if not day_shifts.empty:
                                for _, r in day_shifts.iterrows():
                                    if r['Type'] == "公休": bg_color = "#EF4444"
                                    else: bg_color = staff_color_map.get(r['Staff'], "#6B7280")
                                    
                                    html_content += f"<span class='shift-pill' style='background-color:{bg_color};'>{r['Staff']} - {r['Type']}</span>"
                            
                        st.markdown(f"<div class='day-cell'>{html_content}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='min-height:90px;'></div>", unsafe_allow_html=True)
    
    else:
        # --- V110.0: 全新 Mobile List View (手機優化) ---
        cal = calendar.monthcalendar(sel_year, sel_month)
        for week in cal:
            for day in week:
                if day != 0:
                    date_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == date_str] if not shifts_df.empty else pd.DataFrame()
                    weekday_str = ["週一","週二","週三","週四","週五","週六","週日"][datetime(sel_year, sel_month, day).weekday()]
                    
                    # 內容生成
                    content_html = ""
                    is_store_closed = False
                    if not day_shifts.empty:
                        for _, r in day_shifts.iterrows():
                            if r['Staff'] == "全店" and r['Type'] == "公休": is_store_closed = True; break
                    
                    if is_store_closed:
                        content_html = "<span class='store-closed-mobile'>🔴 全店公休 (Store Closed)</span>"
                    elif not day_shifts.empty:
                        for _, r in day_shifts.iterrows():
                            if r['Type'] == "公休": bg_color = "#EF4444"
                            else: bg_color = staff_color_map.get(r['Staff'], "#6B7280")
                            content_html += f"<span class='shift-pill' style='background-color:{bg_color};'>{r['Staff']} {r['Type']}</span>"
                    else:
                        content_html = "<span style='color:#cbd5e1;font-size:0.8rem;'>尚無排班</span>"

                    # 渲染卡片
                    st.markdown(f"""
                    <div class='mobile-day-row'>
                        <div class='mobile-day-date'>{day}<br><span style='font-size:0.7rem;color:#94a3b8;'>{weekday_str}</span></div>
                        <div class='mobile-day-content'>{content_html}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 隱藏按鈕覆蓋 (Trick)
                    if st.button(f"編輯 {date_str}", key=f"btn_list_{date_str}", use_container_width=True):
                        st.session_state['roster_date'] = date_str
                        st.rerun()

    st.markdown("---")
    
    # 編輯與功能區 (維持不變)
    c_edit, c_smart = st.columns([1, 1])
    
    with c_edit:
        if 'roster_date' in st.session_state:
            t_date = st.session_state['roster_date']
            st.markdown(f"#### ✏️ 編輯排班: {t_date}")
            
            current_day_shifts = shifts_df[shifts_df['Date'] == t_date] if not shifts_df.empty else pd.DataFrame()
            is_closed = False
            if not current_day_shifts.empty:
                 if ((current_day_shifts['Staff'] == "全店") & (current_day_shifts['Type'] == "公休")).any(): is_closed = True

            if is_closed:
                st.error("🔴 目前設定為：全店公休")
                if st.button("🔓 解除全店公休", use_container_width=True):
                      all_vals = ws_shifts.get_all_values()
                      for idx, row in enumerate(all_vals):
                          if len(row) > 1 and row[0] == t_date and row[1] == "全店":
                              retry_action(ws_shifts.delete_rows, idx + 1); break
                      st.success("已解除"); time.sleep(0.5); st.cache_data.clear(); st.rerun()
            else:
                if not current_day_shifts.empty:
                    st.caption("已安排 (點擊❌移除):")
                    for _, r in current_day_shifts.iterrows():
                        if st.button(f"❌ {r['Staff']} ({r['Type']})", key=f"del_{r['Staff']}_{t_date}"):
                            all_vals = ws_shifts.get_all_values()
                            for idx, row in enumerate(all_vals):
                                if len(row) > 1 and row[0] == t_date and row[1] == r['Staff']:
                                    retry_action(ws_shifts.delete_rows, idx + 1); break
                            st.success("已移除"); time.sleep(0.5); st.cache_data.clear(); st.rerun()

                with st.form("add_shift_pro"):
                    s_staff = st.selectbox("人員", users_list)
                    s_type = st.selectbox("班別類型", list(SHIFT_COLORS.keys()))
                    s_note = st.text_input("備註 (可選)")
                    
                    if st.form_submit_button("➕ 新增/更新排班", use_container_width=True):
                        try:
                            all_vals = ws_shifts.get_all_values()
                            rows_to_del = []
                            for idx, row in enumerate(all_vals):
                                if len(row) > 1 and row[0] == t_date and row[1] == s_staff: rows_to_del.append(idx + 1)
                            for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                            
                            retry_action(ws_shifts.append_row, [t_date, s_staff, s_type, s_note, "FALSE", user_name])
                            st.cache_data.clear(); st.success(f"已更新 {s_staff} 的班表"); time.sleep(0.5); st.rerun()
                        except Exception as e:
                            st.error(f"寫入失敗，請重試: {e}")

                st.markdown("---")
                if st.button("🔴 設定為全店公休 (Store Closed)", type="primary", use_container_width=True):
                    try:
                        all_vals = ws_shifts.get_all_values()
                        rows_to_del = []
                        for idx, row in enumerate(all_vals):
                            if len(row) > 1 and row[0] == t_date: rows_to_del.append(idx + 1)
                        for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                        retry_action(ws_shifts.append_row, [t_date, "全店", "公休", "Store Closed", "FALSE", user_name])
                        st.cache_data.clear(); st.success("已設定全店公休"); st.rerun()
                    except Exception as e:
                        st.error(f"設定失敗: {e}")
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

            # V110.0: 存圖功能 (字型已修復)
            if st.button("📸 班表存圖 (Image)", use_container_width=True):
                with st.spinner("下載字型與繪圖中..."):
                    img_buf = generate_roster_image_buffer(sel_year, sel_month, shifts_df, calendar.monthrange(sel_year, sel_month)[1], staff_color_map)
                    if img_buf:
                        st.image(img_buf, caption=f"{sel_year}/{sel_month}")
                        st.download_button("💾 下載", data=img_buf, file_name=f"roster_{sel_year}_{sel_month}.png", mime="image/png", use_container_width=True)
                    else: st.error("繪圖失敗")

        with st.expander("🔄 循環排班 & 複製", expanded=False):
            wc_tab1, wc_tab2 = st.tabs(["👤 人員", "🔴 公休"])
            week_map = {"週一":0, "週二":1, "週三":2, "週四":3, "週五":4, "週六":5, "週日":6}
            with wc_tab1:
                p_staff = st.selectbox("對象", users_list, key="p_st")
                p_day_cn = st.selectbox("每週幾?", list(week_map.keys()), key="p_wd")
                p_type = st.selectbox("班別", list(SHIFT_COLORS.keys()), key="p_ty")
                if st.button("🚀 執行"):
                    # (省略重複邏輯以節省篇幅，邏輯同 V109.7)
                    target_weekday = week_map[p_day_cn]
                    cal = calendar.monthcalendar(sel_year, sel_month)
                    all_vals = ws_shifts.get_all_values() 
                    added=0
                    for week in cal:
                        day = week[target_weekday]
                        if day != 0:
                            d_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                            rows_to_del = [idx+1 for idx, row in enumerate(all_vals) if len(row)>1 and row[0]==d_str and row[1]==p_staff]
                            for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                            retry_action(ws_shifts.append_row, [d_str, p_staff, p_type, "Auto", "FALSE", user_name])
                            added+=1
                    st.cache_data.clear(); st.success(f"完成 {added} 筆"); st.rerun()

            with wc_tab2:
                sc_day_cn = st.selectbox("每週幾?", list(week_map.keys()), key="sc_wd")
                if st.button("🔴 執行"):
                    target_weekday = week_map[sc_day_cn]
                    cal = calendar.monthcalendar(sel_year, sel_month)
                    target_dates = []
                    for week in cal:
                        day = week[target_weekday]
                        if day!=0: target_dates.append(f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}")
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
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>OMEGA V110.0 MOBILE SUPREMACY</div>", unsafe_allow_html=True)
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
                                stored = tgt.iloc[0]['Password']
                                if (len(stored)==64 and check_hash(p, stored)) or (p == stored):
                                    st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=tgt.iloc[0]['Role']; log_event(ws_logs, u, "Login", "Success"); st.rerun()
                                else: st.error("密碼錯誤")
                            else: st.error("帳號不存在")
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
    
    product_map = {}
    if not df.empty:
        for _, r in df.iterrows(): product_map[r['SKU']] = f"{r['Name']} ({r['Size']})"

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

    # Plotly Charts Color Update (Force Light)
    st.markdown("---")
    tabs = st.tabs(["📊 視覺庫存", "🛒 POS", "📈 銷售戰情", "🎁 領用/稽核", "👔 矩陣管理", "📝 日誌", "👥 Admin", "🗓️ 排班"])

    with tabs[0]:
        if not df.empty:
            c1, c2 = st.columns([1, 1])
            with c1:
                fig_pie = px.pie(df, names='Category', values='Qty', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='black') # Force Light
                st.plotly_chart(fig_pie, use_container_width=True)
            with c2:
                top = df.groupby(['Style_Code', 'Name']).agg({'Qty':'sum'}).reset_index().sort_values(by='Qty', ascending=False).head(10)
                fig_bar = px.bar(top, x='Qty', y='Name', orientation='h', text='Qty', color='Qty', color_continuous_scale=px.colors.qualitative.Pastel)
                fig_bar.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='black') # Force Light
                st.plotly_chart(fig_bar, use_container_width=True)
        # ... (Inventory Logic Same) ...
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
                group['size_sort'] = group['Size'].apply(get_size_sort_key); sorted_group = group.sort_values('size_sort')
                
                stock_badges = ""
                for _, r in sorted_group.iterrows():
                    cls = "has-stock" if r['Qty'] > 0 else "no-stock"
                    stock_badges += f"<span class='stock-tag {cls}'>{r['Size']}:{r['Qty']}</span>"

                with st.container(border=True):
                    st.markdown(f"""
                    <div class='inv-row'>
                        <img src='{img}' class='inv-img'>
                        <div class='inv-info'>
                            <div class='
