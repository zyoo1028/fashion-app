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

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK ERP V109.1 ROSTER PRO", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【CSS 視覺核心：手機優先 & 資訊透視】
# ==========================================
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF !important; }
        
        /* POS 卡片 */
        .pos-card {
            border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;
            background: #fff; display: flex; flex-direction: column; 
            height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 10px;
        }
        .pos-img { width: 100%; height: 160px; object-fit: cover; background: #f9fafb; border-bottom: 1px solid #f3f4f6; }
        .pos-content { padding: 10px; flex-grow: 1; display: flex; flex-direction: column; }
        .pos-title { font-weight: bold; font-size: 1rem; margin-bottom: 4px; color: #111; line-height: 1.3; }
        .pos-meta { font-size: 0.8rem; color: #666; margin-bottom: 5px; }
        
        /* 庫存透視標籤 */
        .stock-tag-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; margin-bottom: 5px; }
        .stock-tag { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; border: 1px solid transparent; }
        .stock-tag.has-stock { background-color: #dcfce7; color: #166534; border-color: #bbf7d0; }
        .stock-tag.no-stock { background-color: #f3f4f6; color: #9ca3af; border-color: #e5e7eb; }
        
        /* 庫存列表 */
        .inv-row { border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; margin-bottom: 12px; background: #fff; display: flex; align-items: start; gap: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
        .inv-img { width: 90px; height: 90px; object-fit: cover; border-radius: 8px; flex-shrink: 0; background: #f1f5f9; }
        .inv-info { flex-grow: 1; }
        .inv-title { font-size: 1.1rem; font-weight: bold; color: #0f172a; margin-bottom: 4px; }
        
        /* 財務看板 */
        .finance-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
        .finance-val { font-size: 1.4rem; font-weight: 900; color: #0f172a; }
        .finance-lbl { font-size: 0.8rem; color: #64748b; font-weight: bold; }

        /* V109 排班表 PRO CSS */
        .roster-header { background: #f8fafc; padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e2e8f0; text-align: center; }
        .day-cell { border: 1px solid #f1f5f9; border-radius: 8px; padding: 2px; min-height: 90px; position: relative; margin-bottom: 5px; background: #fff; }
        .day-num { font-size: 0.8rem; font-weight: bold; color: #64748b; margin-bottom: 2px; padding-left: 4px; }
        
        /* 班別膠囊樣式 */
        .shift-pill { 
            font-size: 0.7rem; padding: 3px 4px; border-radius: 6px; 
            margin-bottom: 3px; color: white; display: block; 
            text-align: center; font-weight: bold; 
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }

        /* 全店公休樣式 */
        .store-closed {
            background-color: #EF4444; color: white;
            font-weight: 900; font-size: 0.9rem;
            display: flex; align-items: center; justify-content: center;
            height: 100%; border-radius: 6px; min-height: 80px;
        }
        
        .note-dot { position: absolute; top: 4px; right: 4px; width: 6px; height: 6px; background: #ef4444; border-radius: 50%; }

        /* 通用 */
        .metric-card { background: linear-gradient(145deg, #ffffff, #f8fafc); border-radius: 16px; padding: 15px; border: 1px solid #e2e8f0; text-align: center; margin-bottom: 10px; }
        .metric-value { font-size: 1.6rem; font-weight: 800; margin: 5px 0; color:#0f172a !important; }
        
        .cart-box { background: #f8fafc; border: 1px solid #cbd5e1; padding: 15px; border-radius: 12px; margin-bottom: 15px; }
        .cart-item { display: flex; justify-content: space-between; border-bottom: 1px dashed #cbd5e1; padding: 8px 0; font-size: 0.95rem; }
        .final-price-display { font-size: 2rem; font-weight: 900; color: #15803d; text-align: center; background: #dcfce7; padding: 10px; border-radius: 12px; margin-top: 15px; border: 1px solid #86efac; }
        
        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 700; border:none; box-shadow: 0 1px 2px rgba(0,0,0,0.1); background-color: #FFFFFF; color: #0f172a; border: 1px solid #cbd5e1; width: 100%; }
        input, .stTextInput>div>div, div[data-baseweb="select"]>div { border-radius: 8px !important; min-height: 42px; }
        
        .mgmt-box { border: 1px solid #e2e8f0; padding: 20px; border-radius: 16px; background: #fff; margin-bottom: 20px; }
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
# 🗓️ 排班系統 PRO (Module Rewrite V109.1)
# ==========================================
# 1. 班別顏色定義 (Hotfix: 公休=紅)
SHIFT_COLORS = {
    "早班": "#3B82F6", # 藍色
    "晚班": "#8B5CF6", # 紫色
    "全班": "#10B981", # 綠色
    "代班": "#F59E0B", # 橘色
    "公休": "#EF4444", # 紅色 (全店公休/個人公休)
    "特休": "#DB2777", # 粉紅 (個人假)
    "空班": "#6B7280", # 深灰
    "事假": "#EC4899", # 粉紫
    "病假": "#14B8A6"  # 青色
}

def get_shift_color(shift_type):
    return SHIFT_COLORS.get(shift_type, "#374151")

# 2. 班表圖片生成 (Matplotlib)
def generate_roster_image_buffer(year, month, shifts_df, days_in_month):
    try:
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.axis('off')
        
        ax.text(0.5, 0.95, f"IFUKUK Roster - {year}/{month}", ha='center', va='center', fontsize=20, weight='bold')
        
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
                    
                    # 邏輯判斷：是否全店公休
                    is_store_closed = False
                    if not day_shifts.empty:
                        for _, r in day_shifts.iterrows():
                            if r['Staff'] == "全店" and r['Type'] == "公休": is_store_closed = True; break
                    
                    if is_store_closed:
                        cell_text = f"{day}\n[全店公休]"
                    else:
                        cell_text = f"{day}\n"
                        if not day_shifts.empty:
                            for _, r in day_shifts.iterrows():
                                s_code = r['Type'][0] if r['Type'] else "?"
                                cell_text += f"{r['Staff']}({s_code})\n"
                    row_data.append(cell_text)
            table_data.append(row_data)

        table = ax.table(cellText=table_data, loc='center', cellLoc='left', bbox=[0, 0, 1, 0.9])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2) 

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf
    except Exception as e:
        return None

def render_roster_system(sh, users_list, user_name):
    # 讀取資料
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    shifts_df = get_data_safe(ws_shifts, ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    
    if not shifts_df.empty:
        if 'Shift_Type' in shifts_df.columns and 'Type' not in shifts_df.columns: shifts_df['Type'] = shifts_df['Shift_Type']
        if 'Type' not in shifts_df.columns: shifts_df['Type'] = '上班'
    else:
        shifts_df = pd.DataFrame(columns=["Date", "Staff", "Type", "Note", "Notify", "Updated_By"])

    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班中心 PRO</h3></div>", unsafe_allow_html=True)

    # --- 時間控制區 ---
    now = datetime.utcnow() + timedelta(hours=8)
    c_ctrl1, c_ctrl2, c_ctrl3 = st.columns([2, 1, 1])
    with c_ctrl1:
        c_y, c_m = st.columns(2)
        sel_year = c_y.number_input("年份", 2024, 2030, now.year, label_visibility="collapsed")
        sel_month = c_m.selectbox("月份", range(1, 13), now.month, label_visibility="collapsed")
    
    with c_ctrl2:
        if st.button("📤 生成 LINE 通告", use_container_width=True):
            line_txt = f"【IFUKUK {sel_month}月班表通知】\n"
            m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
            m_data = shifts_df[shifts_df['Date'].str.startswith(m_prefix)].sort_values(['Date', 'Staff'])
            if not m_data.empty:
                last_date = ""
                for _, r in m_data.iterrows():
                    d_short = r['Date'][5:]
                    if d_short != last_date: line_txt += f"\n📅 {d_short}:\n"; last_date = d_short
                    if r['Staff'] == "全店" and r['Type'] == "公休":
                        line_txt += f" - 🔴 全店公休\n"
                    else:
                        line_txt += f" - {r['Staff']}: {r['Type']} {f'({r['Note']})' if r['Note'] else ''}\n"
                st.code(line_txt, language="text")
                st.caption("👆 點擊右上角複製按鈕，貼上 LINE 群組")
            else:
                st.warning("本月尚無排班")

    with c_ctrl3:
        if st.button("📸 班表存圖", use_container_width=True):
            with st.spinner("繪製中..."):
                img_buf = generate_roster_image_buffer(sel_year, sel_month, shifts_df, calendar.monthrange(sel_year, sel_month)[1])
                if img_buf:
                    st.image(img_buf, caption=f"{sel_year}/{sel_month} 班表預覽")
                    st.download_button("💾 下載圖片", data=img_buf, file_name=f"roster_{sel_year}_{sel_month}.png", mime="image/png", use_container_width=True)
                else:
                    st.error("繪圖失敗")

    st.markdown("---")

    # --- 核心日曆區 (V109.1 Update) ---
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
                    
                    if st.button(f"📅 {day}", key=f"d_{date_str}", use_container_width=True):
                        st.session_state['roster_date'] = date_str
                        st.rerun()

                    # 邏輯判斷：優先檢查 "全店公休"
                    is_store_closed = False
                    if not day_shifts.empty:
                        for _, r in day_shifts.iterrows():
                            if r['Staff'] == "全店" and r['Type'] == "公休": is_store_closed = True; break

                    html_content = ""
                    if is_store_closed:
                        # 強制顯示全店公休 (紅色)
                        html_content = "<div class='store-closed'>🔴 全店公休</div>"
                    else:
                        if not day_shifts.empty:
                            for _, r in day_shifts.iterrows():
                                bg_color = get_shift_color(r['Type'])
                                html_content += f"""
                                    <span class='shift-pill' style='background-color:{bg_color};'>
                                        {r['Staff']} - {r['Type']}
                                    </span>
                                """
                    
                    st.markdown(f"<div class='day-cell'>{html_content}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='min-height:90px;'></div>", unsafe_allow_html=True)

    # --- 編輯與數據區 ---
    st.markdown("---")
    
    with st.expander("📊 人員出勤戰情室 (Month Statistics)", expanded=True):
        if not shifts_df.empty:
            m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
            m_data = shifts_df[shifts_df['Date'].str.startswith(m_prefix)]
            
            if not m_data.empty:
                stats = []
                for user in users_list:
                    u_data = m_data[m_data['Staff'] == user]
                    total_shifts = len(u_data[~u_data['Type'].isin(['公休', '特休', '事假', '病假'])])
                    off_days = len(u_data[u_data['Type'] == '公休'])
                    leave_days = len(u_data[u_data['Type'] == '特休'])
                    other_days = len(u_data[u_data['Type'].isin(['事假', '病假'])])
                    stats.append({
                        "人員": user,
                        "上班天數": total_shifts,
                        "公休": off_days,
                        "特休 (累計)": leave_days,
                        "其他假": other_days
                    })
                st.dataframe(pd.DataFrame(stats), use_container_width=True, hide_index=True)
            else:
                st.info("本月尚無數據")
        else:
            st.info("尚無數據")

    c_edit, c_smart = st.columns([1, 1])
    
    with c_edit:
        if 'roster_date' in st.session_state:
            t_date = st.session_state['roster_date']
            st.markdown(f"#### ✏️ 編輯排班: {t_date}")
            
            current_day_shifts = shifts_df[shifts_df['Date'] == t_date] if not shifts_df.empty else pd.DataFrame()
            
            # 檢查是否已設定全店公休
            is_closed = False
            if not current_day_shifts.empty:
                 if ((current_day_shifts['Staff'] == "全店") & (current_day_shifts['Type'] == "公休")).any(): is_closed = True

            if is_closed:
                st.error("🔴 目前設定為：全店公休")
                if st.button("🔓 解除全店公休 (恢復排班)", use_container_width=True):
                     all_vals = ws_shifts.get_all_values()
                     for idx, row in enumerate(all_vals):
                         if len(row) > 1 and row[0] == t_date and row[1] == "全店":
                             retry_action(ws_shifts.delete_rows, idx + 1); break
                     st.success("已解除"); time.sleep(0.5); st.cache_data.clear(); st.rerun()
            else:
                if not current_day_shifts.empty:
                    st.caption("已安排:")
                    for _, r in current_day_shifts.iterrows():
                        if st.button(f"❌ 移除 {r['Staff']} ({r['Type']})", key=f"del_{r['Staff']}_{t_date}"):
                            all_vals = ws_shifts.get_all_values()
                            for idx, row in enumerate(all_vals):
                                if len(row) > 1 and row[0] == t_date and row[1] == r['Staff']:
                                    retry_action(ws_shifts.delete_rows, idx + 1); break
                            st.success("已移除"); time.sleep(0.5); st.cache_data.clear(); st.rerun()

                with st.form("add_shift_pro"):
                    s_staff = st.selectbox("人員", users_list)
                    s_type = st.selectbox("班別類型", list(SHIFT_COLORS.keys()))
                    s_note = st.text_input("備註 (可選)")
                    
                    if not current_day_shifts.empty and s_staff in current_day_shifts['Staff'].values:
                        st.warning(f"⚠️ {s_staff} 在這天已經有班了！送出將會覆蓋。")

                    if st.form_submit_button("➕ 加入/更新排班", use_container_width=True):
                        all_vals = ws_shifts.get_all_values()
                        rows_to_del = []
                        for idx, row in enumerate(all_vals):
                            if len(row) > 1 and row[0] == t_date and row[1] == s_staff: rows_to_del.append(idx + 1)
                        for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                        
                        retry_action(ws_shifts.append_row, [t_date, s_staff, s_type, s_note, "FALSE", user_name])
                        st.cache_data.clear(); st.success("已更新"); time.sleep(0.5); st.rerun()

                # V109.1 新增：全店公休按鈕
                st.markdown("---")
                if st.button("🔴 設定為全店公休 (Store Closed)", type="primary", use_container_width=True):
                    # 刪除當天所有排班
                    all_vals = ws_shifts.get_all_values()
                    rows_to_del = []
                    for idx, row in enumerate(all_vals):
                        if len(row) > 1 and row[0] == t_date: rows_to_del.append(idx + 1)
                    for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                    
                    # 寫入全店公休
                    retry_action(ws_shifts.append_row, [t_date, "全店", "公休", "Store Closed", "FALSE", user_name])
                    st.cache_data.clear(); st.success("已設定全店公休"); st.rerun()
        else:
            st.info("👈 請點選左側日曆日期進行編輯")

    with c_smart:
        st.markdown("#### 🧠 智能排班工具")
        with st.expander("⚡ 快速複製 (Smart Copy)"):
            st.caption("將上週同一天的班表複製到這一天")
            if 'roster_date' in st.session_state:
                target_date_obj = datetime.strptime(st.session_state['roster_date'], "%Y-%m-%d")
                source_date_obj = target_date_obj - timedelta(days=7)
                source_date_str = source_date_obj.strftime("%Y-%m-%d")
                
                if st.button(f"從 {source_date_str} 複製到 {st.session_state['roster_date']}"):
                    source_shifts = shifts_df[shifts_df['Date'] == source_date_str]
                    if not source_shifts.empty:
                        target_d = st.session_state['roster_date']
                        all_vals = ws_shifts.get_all_values()
                        rows_to_del = [i+1 for i, r in enumerate(all_vals) if len(r)>0 and r[0]==target_d]
                        for r_idx in reversed(rows_to_del): retry_action(ws_shifts.delete_rows, r_idx)
                        
                        new_rows = []
                        for _, r in source_shifts.iterrows():
                            new_rows.append([target_d, r['Staff'], r['Type'], r.get('Note',''), r.get('Notify','FALSE'), user_name])
                        
                        for nr in new_rows: retry_action(ws_shifts.append_row, nr)
                        st.cache_data.clear(); st.success(f"已從 {source_date_str} 複製 {len(new_rows)} 筆排班"); time.sleep(1); st.rerun()
                    else:
                        st.error("上週同一天沒有排班資料")
            else:
                st.caption("請先選擇日期")

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
            st.markdown("<div style='text-align:center; color:#666; font-size:0.9rem; margin-bottom:30px;'>OMEGA V109.1 ROSTER PRO</div>", unsafe_allow_html=True)
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
    
    # 建立 SKU 對照表
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

    st.markdown("---")
    tabs = st.tabs(["📊 視覺庫存", "🛒 POS", "📈 銷售戰情", "🎁 領用/稽核", "👔 矩陣管理", "📝 日誌", "👥 Admin", "🗓️ 排班"])

    with tabs[0]:
        if not df.empty:
            c1, c2 = st.columns([1, 1])
            with c1:
                fig_pie = px.pie(df, names='Category', values='Qty', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            with c2:
                top = df.groupby(['Style_Code', 'Name']).agg({'Qty':'sum'}).reset_index().sort_values(by='Qty', ascending=False).head(10)
                fig_bar = px.bar(top, x='Qty', y='Name', orientation='h', text='Qty', color='Qty', color_continuous_scale=px.colors.qualitative.Pastel)
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
        
        st.markdown("##### 📅 結算週期與財務總覽 (自動統計)")
        c_date1, c_date2 = st.columns(2)
        start_d = c_date1.date_input("起始日期", value=date.today().replace(day=1))
        end_d = c_date2.date_input("結束日期", value=date.today())
        
        sales_data = []
        if not logs_df.empty:
            s_logs = logs_df[logs_df['Action'] == 'Sale']
            for _, row in s_logs.iterrows():
                try:
                    ts_str = row['Timestamp'].split(' ')[0]
                    log_date = datetime.strptime(ts_str, "%Y-%m-%d").date()
                    
                    if start_d <= log_date <= end_d:
                        d = row['Details']
                        total_m = re.search(r'Total:\$(\d+)', d); total_v = int(total_m.group(1)) if total_m else 0
                        
                        ch_v = "未分類"
                        if "Channel:" in d: ch_m = re.search(r'Channel:(.*?) \|', d + " |"); ch_v = ch_m.group(1).strip() if ch_m else "未分類"
                        elif " | " in d: ch_m = re.search(r' \| (門市|官網|直播|網路|其他)', d); ch_v = ch_m.group(1) if ch_m else "未分類"

                        pay_v = "未分類"
                        if "Pay:" in d: pay_m = re.search(r'Pay:(.*?) \|', d + " |"); pay_v = pay_m.group(1).strip() if pay_m else "未分類"

                        by_v = row['User']
                        if "By:" in d: by_m = re.search(r'By:(\w+)', d); by_v = by_m.group(1) if by_m else row['User']
                        
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
                except: pass
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
                st.plotly_chart(fig, use_container_width=True)
            with c2: 
                fig2 = px.bar(sdf.groupby('銷售員')['金額'].sum().reset_index(), x='銷售員', y='金額', title="人員業績排行", color='金額', color_continuous_scale=px.colors.sequential.Teal)
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

                st.info("⚠️ 注意：修改內容或商品後，系統將自動『歸還舊庫存』並『扣除新庫存』，確保數據絕對準確。")
                
                with st.form("edit_sale_form"):
                    e_items = st.text_area("商品內容 (格式: SKU x數量, SKU x數量)", value=curr_items_str)
                    c_e1, c_e2, c_e3 = st.columns(3)
                    e_total = c_e1.number_input("總金額", value=target_row['金額'])
                    e_ch = c_e2.selectbox("通路", ["門市","官網","直播","網路","其他"], index=["門市","官網","直播","網路","其他"].index(curr_ch) if curr_ch in ["門市","官網","直播","網路","其他"] else 0)
                    e_pay = c_e3.selectbox("付款", ["現金","刷卡","轉帳","禮券","其他"], index=["現金","刷卡","轉帳","禮券","其他"].index(curr_pay) if curr_pay in ["現金","刷卡","轉帳","禮券","其他"] else 0)
                    e_note = st.text_input("備註", value=curr_note)
                    
                    if st.form_submit_button("✅ 確認修改並同步庫存", type="primary"):
                        try:
                            all_logs = ws_logs.get_all_values()
                            log_idx = -1
                            for idx, row in enumerate(all_logs):
                                if row[0] == target_ts and "Sale" in row[2]: log_idx = idx + 1; break
                            
                            if log_idx == -1: st.error("找不到原始訂單"); st.stop()

                            for part in curr_items_str.split(','):
                                clean_part = re.sub(r'\s*\(\$.*?\)', '', part).strip()
                                if ' x' in clean_part:
                                    p_sku = clean_part.split(' x')[0].strip()
                                    p_qty = int(clean_part.split(' x')[1].strip())
                                    cell = ws_items.find(p_sku)
                                    if cell:
                                        curr_q = int(ws_items.cell(cell.row, 5).value)
                                        retry_action(ws_items.update_cell, cell.row, 5, curr_q + p_qty)
                            
                            new_items_list = []
                            for part in e_items.split(','):
                                clean_part = re.sub(r'\s*\(\$.*?\)', '', part).strip()
                                if ' x' in clean_part:
                                    p_sku = clean_part.split(' x')[0].strip()
                                    p_qty = int(clean_part.split(' x')[1].strip())
                                    cell = ws_items.find(p_sku)
                                    if cell:
                                        curr_q = int(ws_items.cell(cell.row, 5).value)
                                        if curr_q >= p_qty:
                                            retry_action(ws_items.update_cell, cell.row, 5, curr_q - p_qty)
                                            new_items_list.append(f"{p_sku} x{p_qty}")
                                        else:
                                            st.error(f"❌ 商品 {p_sku} 庫存不足"); st.stop()
                                    else: st.error(f"❌ 商品 {p_sku} 不存在"); st.stop()

                            retry_action(ws_logs.delete_rows, log_idx)
                            new_content = f"Sale | Total:${e_total} | Items:{','.join(new_items_list)} | Note:{e_note} | Pay:{e_pay} | Channel:{e_ch} | By:{st.session_state['user_name']} (Edited)"
                            log_event(ws_logs, st.session_state['user_name'], "Sale", new_content)
                            
                            st.success("✅ 訂單已修正！"); time.sleep(2); st.rerun()
                            
                        except Exception as e:
                            st.error(f"系統錯誤: {e}")

                if st.button("🗑️ 直接作廢此單 (歸還庫存)"):
                    try:
                        for part in curr_items_str.split(','):
                            clean_part = re.sub(r'\s*\(\$.*?\)', '', part).strip()
                            if ' x' in clean_part:
                                p_sku = clean_part.split(' x')[0].strip()
                                p_qty = int(clean_part.split(' x')[1].strip())
                                cell = ws_items.find(p_sku)
                                if cell:
                                    curr_q = int(ws_items.cell(cell.row, 5).value)
                                    retry_action(ws_items.update_cell, cell.row, 5, curr_q + p_qty)
                        
                        all_logs = ws_logs.get_all_values()
                        for idx, row in enumerate(all_logs):
                            if row[0] == target_ts and "Sale" in row[2]:
                                retry_action(ws_logs.delete_rows, idx + 1); break
                        st.success("已作廢"); time.sleep(1); st.rerun()
                    except: st.error("作廢失敗")

        else: st.info("無資料")

    with tabs[3]:
        st.subheader("🎁 內部領用/稽核 (統計修正)")
        if not logs_df.empty:
            int_df = logs_df[logs_df['Action'] == "Internal_Use"].copy()
            if not int_df.empty:
                def parse_int_who(d):
                    try: return d.split(' | ')[1].strip()
                    except: return "未分類"
                def parse_int_qty(d):
                    try: return int(d.split(' | ')[0].split(' -')[1])
                    except: return 0
                def parse_int_reason(d):
                    try: return d.split(' | ')[2].strip()
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
                    q = st.number_input("數量", 1); who = st.selectbox("領用人 (實際拿貨者)", staff_list); rsn = st.selectbox("原因", ["公務", "公關", "福利", "報廢", "樣品", "其他"]); n = st.text_input("備註")
                    if st.form_submit_button("執行"):
                        r = ws_items.find(tsku).row; retry_action(ws_items.update_cell, r, 5, int(tr['Qty'])-q)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{tsku} -{q} | {who} | {rsn} | {n}")
                        st.cache_data.clear(); st.success("已記錄"); st.rerun()
        
        st.divider()
        st.markdown("#### 🕵️ 紀錄管理")
        if not logs_df.empty and not int_df.empty:
            view_int_df = int_df.copy()
            view_int_df['商品'] = view_int_df['Details'].apply(lambda x: x.split(' | ')[0].split(' -')[0])
            view_int_df['商品'] = view_int_df['商品'].map(product_map).fillna(view_int_df['商品'])
            st.dataframe(view_int_df[['Timestamp', 'User', '實際領用人', '商品', '數量', '原因']], use_container_width=True)
            
            st.markdown("##### ✏️ 修正紀錄 (刪除或修改)")
            rev_opts = int_df.apply(lambda x: f"{x['Timestamp']} | {product_map.get(x['Details'].split(' -')[0], x['Details'])}", axis=1).tolist()
            sel_rev = st.selectbox("選擇要修正的紀錄", ["..."] + rev_opts)
            
            if sel_rev != "...":
                target_ts = sel_rev.split(" | ")[0]
                orig_row = logs_df[logs_df['Timestamp'] == target_ts].iloc[0]
                orig_detail = orig_row['Details']
                orig_sku = orig_detail.split(' -')[0]
                orig_qty = int(orig_detail.split(' -')[1].split(' | ')[0])
                
                c_mod1, c_mod2 = st.columns(2)
                if c_mod1.button("🚫 僅撤銷 (歸還庫存並刪除)"):
                    all_logs = ws_logs.get_all_values()
                    for idx, row in enumerate(all_logs):
                        if row[0] == target_ts: retry_action(ws_logs.delete_rows, idx + 1); break
                    
                    cell = ws_items.find(orig_sku)
                    if cell:
                        curr_q = int(ws_items.cell(cell.row, 5).value)
                        retry_action(ws_items.update_cell, cell.row, 5, curr_q + orig_qty)
                        st.success(f"已歸還 {orig_sku} +{orig_qty}"); time.sleep(1); st.rerun()

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
                for sku, info in product_map.items():
                    if sku in txt: txt = txt.replace(sku, info)
                return txt
            
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
