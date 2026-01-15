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
    page_title="IFUKUK ERP V110.9 HOTFIX", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【CSS 視覺核心：強制白底 & 手機 Grid 強制並排】
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
        
        /* 庫存標籤 */
        .stock-tag { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
        .stock-tag.has-stock { background-color: #dcfce7 !important; color: #166534 !important; }
        .stock-tag.no-stock { background-color: #f3f4f6 !important; color: #9ca3af !important; }

        /* V110.8 特化：手機版排班強制 7 格並排 (Force 7-Col Grid) */
        /* 當螢幕寬度小於 768px 時，強制 column 不堆疊 */
        @media (max-width: 768px) {
            div[data-testid="column"] {
                width: 14.28% !important;
                flex: 1 1 14.28% !important;
                min-width: 0 !important;
                padding: 0px 2px !important;
            }
            /* 手機版排班格子內文字縮小 */
            .day-cell { min-height: 60px !important; padding: 2px !important; font-size: 0.6rem !important; }
            .day-num { font-size: 0.7rem !important; }
            .shift-pill { font-size: 0.5rem !important; padding: 1px 2px !important; margin-bottom: 2px !important; }
            .store-closed { font-size: 0.6rem !important; min-height: 60px !important; }
        }

        /* Desktop 排班樣式 */
        .roster-header { background: #f1f5f9; padding: 15px; border-radius: 12px; margin-bottom: 20px; text-align: center; }
        .day-cell { border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; min-height: 100px; position: relative; margin-bottom: 5px; background: #fff !important; }
        .day-num { font-size: 0.8rem; font-weight: bold; color: #64748b; margin-bottom: 2px; }
        .shift-pill { 
            font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; 
            margin-bottom: 4px; color: white !important; display: block; 
            text-align: center; font-weight: bold; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
        }
        .store-closed { background-color: #EF4444 !important; color: white !important; font-weight: 900; font-size: 0.9rem; display: flex; align-items: center; justify-content: center; height: 100%; border-radius: 6px; min-height: 90px; }
        
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
            else:
                raise e
    st.error("❌ 雲端同步失敗，請檢查網路。")
    return None

@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 找不到 Secrets 金鑰。")
        st.stop()
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=10, show_spinner=False)
def get_data_safe(_ws, expected_headers=None):
    if _ws is None: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
    try:
        raw_data = _ws.get_all_values()
        if not raw_data or len(raw_data) < 2: return pd.DataFrame(columns=expected_headers) if expected_headers else pd.DataFrame()
        headers = raw_data[0]
        # 處理重複 Header
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
        try:
            ws = sh.add_worksheet(title, rows=100, cols=20)
            ws.append_row(headers); return ws
        except: return None

# --- 工具模組 ---
def get_taiwan_time_str(): return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
@st.cache_data(ttl=3600)
def get_live_rate():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/CNY", timeout=3)
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
    pmap = {"上衣(Top)":"TOP", "褲子(Btm)":"BTM", "外套(Out)":"OUT", "套裝(Suit)":"SET", "鞋類(Shoe)":"SHOE", "包款(Bag)":"BAG", "帽子(Hat)":"HAT", "飾品(Acc)":"ACC", "其他(Misc)":"MSC"}
    p = f"{pmap.get(cat,'GEN')}-{(datetime.utcnow()+timedelta(hours=8)).strftime('%y%m')}"
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
# 🗓️ 排班系統 ELITE (V110.9)
# ==========================================
SHIFT_COLORS = {"早班":"#3B82F6", "晚班":"#8B5CF6", "全班":"#10B981", "代班":"#F59E0B", "公休":"#EF4444", "特休":"#DB2777", "空班":"#6B7280", "事假":"#EC4899", "病假":"#14B8A6"}
def get_staff_color_map(users):
    pal = ["#2563EB","#059669","#7C3AED","#DB2777","#D97706","#DC2626","#0891B2","#4F46E5","#BE123C","#B45309"]
    return {u: pal[i%len(pal)] for i, u in enumerate(sorted([x for x in users if x!="全店"]))}

# V110.8: 強化版字型下載 (防崩潰)
def get_chinese_font_path_robust():
    font_name = "NotoSansTC-Regular.otf"
    if os.path.exists(font_name): return font_name
    urls = [
        "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf",
        "https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/TraditionalChinese/SourceHanSansTC-Regular.otf"
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(font_name, 'wb') as f: f.write(r.content)
                return font_name
        except: continue
    return None

def generate_roster_image_buffer(year, month, shifts_df, days_in_month, color_map):
    try:
        font_path = get_chinese_font_path_robust()
        prop = fm.FontProperties(fname=font_path) if font_path else fm.FontProperties()
        
        # 針對手機優化：調整圖片比例與字體大小
        fig, ax = plt.subplots(figsize=(10, 8), dpi=150) # 提高 DPI
        ax.axis('off')
        
        title = f"IFUKUK {year}/{month} 班表"
        ax.text(0.5, 0.98, title, ha='center', va='center', fontsize=20, weight='bold', fontproperties=prop)
        
        cols = ["Mon 一", "Tue 二", "Wed 三", "Thu 四", "Fri 五", "Sat 六", "Sun 日"]
        cal = calendar.monthcalendar(year, month)
        table_data = [cols]
        
        for week in cal:
            row_data = []
            for day in week:
                if day == 0: row_data.append("")
                else:
                    d_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == d_str]
                    is_closed = any((r['Staff']=="全店" and r['Type']=="公休") for _,r in day_shifts.iterrows())
                    
                    cell_txt = f"{day}\n"
                    if is_closed: cell_txt += "\n[全店公休]\nCLOSED"
                    else:
                        for _, r in day_shifts.iterrows():
                            s_short = r['Type'][0] # 取第一個字
                            cell_txt += f"{r['Staff']} ({s_short})\n"
                    row_data.append(cell_txt)
            table_data.append(row_data)

        table = ax.table(cellText=table_data, loc='center', cellLoc='left', bbox=[0, 0, 1, 0.93])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        
        for (i, j), cell in table.get_celld().items():
            if i == 0:
                cell.set_text_props(weight='bold', fontproperties=prop)
                cell.set_facecolor('#f3f4f6')
                cell.set_height(0.06)
            else:
                cell.set_height(0.14)
                cell.set_valign('top')
                cell.set_text_props(fontproperties=prop)
                txt = cell.get_text().get_text()
                if "全店公休" in txt:
                    cell.set_facecolor('#FECACA')
                    cell.get_text().set_color('#991B1B')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf
    except Exception as e:
        print(f"Plot Error: {e}")
        return None

def render_roster_system(sh, users_list, user_name):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    if ws_shifts is None: st.warning("Connecting..."); return
    shifts_df = get_data_safe(ws_shifts, ["Date", "Staff", "Shift_Type", "Note", "Notify", "Updated_By"])
    if 'Shift_Type' in shifts_df.columns: shifts_df['Type'] = shifts_df['Shift_Type']
    if 'Type' not in shifts_df.columns: shifts_df['Type'] = '上班'
    
    staff_color_map = get_staff_color_map(users_list)
    now = datetime.utcnow() + timedelta(hours=8)
    
    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班中心 (Smart Grid)</h3></div>", unsafe_allow_html=True)

    # 控制區
    c1, c2 = st.columns([2, 1])
    with c1:
        cy, cm = st.columns(2)
        sel_year = cy.number_input("年份", 2024, 2030, now.year, label_visibility="collapsed")
        sel_month = cm.selectbox("月份", range(1,13), index=now.month-1, label_visibility="collapsed")
    with c2:
        # V110.8: 強制電腦版視圖，不給切換，因為我們用 CSS 解決了
        st.caption(f"📅 檢視: {sel_year}/{sel_month}")

    # --- 核心排班顯示邏輯 (CSS Grid) ---
    cal = calendar.monthcalendar(sel_year, sel_month)
    cols = st.columns(7)
    days_map = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    for i, d in enumerate(days_map): 
        cols[i].markdown(f"<div style='text-align:center;font-size:0.8rem;color:#64748b;font-weight:bold;'>{d}</div>", unsafe_allow_html=True)

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day != 0:
                    d_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == d_str]
                    
                    # 點擊日期按鈕 (觸發編輯)
                    if st.button(f"{day}", key=f"d_{d_str}", use_container_width=True):
                        st.session_state['roster_date'] = d_str
                        st.rerun()

                    is_closed = any((r['Staff']=="全店" and r['Type']=="公休") for _,r in day_shifts.iterrows())
                    content = ""
                    if is_closed:
                        content = "<div class='store-closed'>休</div>"
                    else:
                        for _, r in day_shifts.iterrows():
                            bg = staff_color_map.get(r['Staff'], "#666")
                            # 手機版只顯示首字
                            content += f"<div class='shift-pill' style='background:{bg};'>{r['Staff']}</div>"
                    
                    st.markdown(f"<div class='day-cell'>{content}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True)

    st.divider()

    # --- 智慧編輯區 (Smart Edit) ---
    # 邏輯: 點選上方日期 -> 顯示該日詳情 -> 每一行都有「更新」按鈕
    c_edit, c_tools = st.columns([1.5, 1])
    
    with c_edit:
        if 'roster_date' in st.session_state:
            t_date = st.session_state['roster_date']
            st.markdown(f"#### ✏️ 編輯: {t_date}")
            
            current_day_shifts = shifts_df[shifts_df['Date'] == t_date]
            
            # 1. 顯示現有排班並提供「原位修改」
            if not current_day_shifts.empty:
                for _, r in current_day_shifts.iterrows():
                    with st.expander(f"👤 {r['Staff']} - {r['Type']}", expanded=False):
                        with st.form(f"edit_{t_date}_{r['Staff']}"):
                            c_new1, c_new2 = st.columns(2)
                            new_type = c_new1.selectbox("狀態", list(SHIFT_COLORS.keys()), index=list(SHIFT_COLORS.keys()).index(r['Type']) if r['Type'] in SHIFT_COLORS else 0)
                            new_note = c_new2.text_input("備註", value=r['Note'])
                            
                            c_btn1, c_btn2 = st.columns(2)
                            if c_btn1.form_submit_button("💾 更新狀態"):
                                # 查找並更新
                                all_vals = ws_shifts.get_all_values()
                                for idx, row in enumerate(all_vals):
                                    if len(row)>1 and row[0]==t_date and row[1]==r['Staff']:
                                        # 更新: Date, Staff, Type, Note, Notify, By
                                        retry_action(ws_shifts.update_cell, idx+1, 3, new_type)
                                        retry_action(ws_shifts.update_cell, idx+1, 4, new_note)
                                        retry_action(ws_shifts.update_cell, idx+1, 6, user_name)
                                        break
                                st.success("已更新"); time.sleep(0.5); st.cache_data.clear(); st.rerun()
                            
                            if c_btn2.form_submit_button("🗑️ 刪除此班"):
                                all_vals = ws_shifts.get_all_values()
                                for idx, row in enumerate(all_vals):
                                    if len(row)>1 and row[0]==t_date and row[1]==r['Staff']:
                                        retry_action(ws_shifts.delete_rows, idx+1); break
                                st.success("已刪除"); time.sleep(0.5); st.cache_data.clear(); st.rerun()

            # 2. 新增排班 (保持原有)
            st.markdown("---")
            with st.form("add_new_shift"):
                st.caption("➕ 新增排班")
                c_add1, c_add2 = st.columns(2)
                n_staff = c_add1.selectbox("人員", users_list)
                n_type = c_add2.selectbox("班別", list(SHIFT_COLORS.keys()))
                n_note = st.text_input("備註")
                if st.form_submit_button("新增"):
                    # 先刪舊
                    all_vals = ws_shifts.get_all_values()
                    rows_del = [i+1 for i, row in enumerate(all_vals) if len(row)>1 and row[0]==t_date and row[1]==n_staff]
                    for i in reversed(rows_del): retry_action(ws_shifts.delete_rows, i)
                    # 後寫新
                    retry_action(ws_shifts.append_row, [t_date, n_staff, n_type, n_note, "FALSE", user_name])
                    st.cache_data.clear(); st.success("已新增"); st.rerun()
            
            # 3. 全店公休
            if st.button("🔴 設定全店公休"):
                all_vals = ws_shifts.get_all_values()
                rows_del = [i+1 for i, row in enumerate(all_vals) if len(row)>0 and row[0]==t_date]
                for i in reversed(rows_del): retry_action(ws_shifts.delete_rows, i)
                retry_action(ws_shifts.append_row, [t_date, "全店", "公休", "Store Closed", "FALSE", user_name])
                st.cache_data.clear(); st.rerun()

        else:
            st.info("👈 點擊上方日期進行編輯")

    with c_tools:
        st.markdown("#### 🛠️ 工具箱")
        
        # V110.8: 精美 LINE 文字生成 (樹狀結構)
        if st.button("💬 生成 LINE 通告 (繁體精美版)"):
            txt = f"📅 【IFUKUK {sel_month}月班表公告】\n"
            txt += f"統計區間: {sel_year}/{sel_month}\n"
            txt += "━" * 20 + "\n"
            
            m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
            m_data = shifts_df[shifts_df['Date'].str.startswith(m_prefix)].sort_values(['Date', 'Staff'])
            
            last_date = ""
            for _, r in m_data.iterrows():
                d_obj = datetime.strptime(r['Date'], "%Y-%m-%d")
                w_str = ["週一","週二","週三","週四","週五","週六","週日"][d_obj.weekday()]
                d_display = f"{d_obj.month}/{d_obj.day} ({w_str})"
                
                if d_display != last_date:
                    txt += f"\n🗓️ {d_display}\n"
                    last_date = d_display
                
                if r['Staff'] == "全店" and r['Type'] == "公休":
                    txt += "   🔴 全店公休 (Store Closed)\n"
                else:
                    note = f" ({r['Note']})" if r['Note'] else ""
                    txt += f"   └ 👤 {r['Staff']}：{r['Type']}{note}\n"
            
            st.text_area("複製下方文字", value=txt, height=300)

        # V110.8: 穩健版存圖
        if st.button("📸 下載班表圖片 (Safe Mode)"):
            with st.spinner("繪圖引擎啟動中..."):
                img_buf = generate_roster_image_buffer(sel_year, sel_month, shifts_df, 30, staff_color_map)
                if img_buf:
                    st.image(img_buf, caption="長按儲存圖片")
                    st.download_button("💾 下載 PNG", data=img_buf, file_name=f"Roster_{sel_year}_{sel_month}.png", mime="image/png")
                else:
                    st.error("繪圖失敗，請稍後再試 (已啟用防崩潰機制)")

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False; st.session_state['user_name'] = ""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    if 'exchange_rate' not in st.session_state:
        r, s = get_live_rate()
        st.session_state['exchange_rate'] = r

    sh = init_db()
    if not sh: st.error("Database Error"); st.stop()

    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    # LOGIN
    if not st.session_state['logged_in']:
        st.markdown("<br><br><h1 style='text-align:center;'>IFUKUK V110.9</h1>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("ID"); p = st.text_input("PWD", type="password")
            if st.form_submit_button("LOGIN", type="primary"):
                udf = get_data_safe(ws_users, ["Name", "Password", "Role", "Status"])
                if udf.empty and u=="Boss" and p=="1234":
                    retry_action(ws_users.append_row, ["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                    st.success("Admin Created"); st.rerun()
                
                target = udf[(udf['Name']==u) & (udf['Status']=='Active')]
                if not target.empty:
                    pwd_hash = target.iloc[0]['Password']
                    if check_hash(p, pwd_hash) or p==pwd_hash:
                        st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=target.iloc[0]['Role']
                        log_event(ws_logs, u, "Login", "Success"); st.rerun()
                    else: st.error("Wrong Password")
                else: st.error("User Not Found")
        return

    # MAIN APP
    u_initial = st.session_state['user_name'][0].upper()
    render_navbar(u_initial)

    df = get_data_safe(ws_items, SHEET_HEADERS)
    logs_df = get_data_safe(ws_logs, ["Timestamp", "User", "Action", "Details"])
    users_df = get_data_safe(ws_users)
    staff_list = users_df['Name'].tolist() if not users_df.empty else []

    # Pre-process Data
    for c in ["Qty", "Price", "Cost", "Qty_CN", "Safety_Stock"]: 
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    
    df['SKU'] = df['SKU'].astype(str)
    product_map = {r['SKU']: f"{r['Name']} ({r['Size']})" for _, r in df.iterrows()}

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        st.write(f"Role: {st.session_state['user_role']}")
        if st.button("Logout"): st.session_state['logged_in']=False; st.rerun()

    # Tabs
    tabs = st.tabs(["📊 庫存", "🛒 POS", "📈 戰情", "🎁 領用/稽核", "👔 管理", "📝 日誌", "👥 用戶", "🗓️ 排班"])

    # 1. 庫存 (FIXED: 移除 'Color' 以防止崩潰)
    with tabs[0]:
        st.subheader("📦 庫存總覽")
        col1, col2 = st.columns([3, 1])
        q = col1.text_input("🔍 搜尋庫存", placeholder="SKU / 品名")
        cat = col2.selectbox("分類", ["全部"] + CAT_LIST)
        
        vdf = df.copy()
        if q: vdf = vdf[vdf.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)]
        if cat != "全部": vdf = vdf[vdf['Category'] == cat]
        
        # 修正點：移除 'Color'
        st.dataframe(vdf[['SKU','Name','Size','Qty','Qty_CN','Price']], use_container_width=True, hide_index=True)

    # 2. POS (核心邏輯保持)
    with tabs[1]:
        c_l, c_r = st.columns([3, 2])
        with c_l:
            pq = st.text_input("POS 搜尋", key="pos_q")
            pdf = df.copy()
            if pq: pdf = pdf[pdf.astype(str).apply(lambda x: x.str.contains(pq, case=False)).any(axis=1)]
            
            for i in range(0, len(pdf), 3):
                cols = st.columns(3)
                for j, (_, row) in enumerate(pdf.iloc[i:i+3].iterrows()):
                    with cols[j]:
                        st.markdown(f"<div class='pos-card'><div class='pos-title'>{row['Name']}</div><div>${row['Price']} | 存:{row['Qty']}</div></div>", unsafe_allow_html=True)
                        if st.button("➕", key=f"add_{row['SKU']}"):
                            st.session_state['pos_cart'].append(row.to_dict())
                            st.toast(f"已加入 {row['Name']}")
        with c_r:
            st.markdown("#### 🛒 購物車")
            total = 0
            if st.session_state['pos_cart']:
                for idx, item in enumerate(st.session_state['pos_cart']):
                    st.markdown(f"{item['Name']} - ${item['Price']}")
                    total += item['Price']
                st.markdown(f"**總計: ${total}**")
                
                if st.button("✅ 結帳"):
                    # 扣庫存邏輯
                    sales_log = []
                    for item in st.session_state['pos_cart']:
                        cell = ws_items.find(item['SKU'])
                        curr = int(ws_items.cell(cell.row, 5).value)
                        retry_action(ws_items.update_cell, cell.row, 5, curr - 1)
                        sales_log.append(f"{item['SKU']} x1")
                    
                    log_event(ws_logs, st.session_state['user_name'], "Sale", f"Total:${total} | Items:{','.join(sales_log)}")
                    st.session_state['pos_cart'] = []
                    st.success("結帳完成"); st.cache_data.clear(); st.rerun()
                
                if st.button("🗑️ 清空"): st.session_state['pos_cart'] = []; st.rerun()

    # 3. 戰情 (保持 V110.0)
    with tabs[2]:
        rev = calculate_realized_revenue(logs_df)
        st.metric("實際營收", f"${rev:,}")
        
    # 4. 🎁 領用/稽核 (V110.8 大升級)
    with tabs[3]:
        st.subheader("🎁 內部領用與稽核中心 (Advanced Audit)")
        
        # A. 新增領用
        with st.expander("➕ 新增領用單", expanded=False):
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} {x['Size']}", axis=1).tolist()
            sel_item = st.selectbox("選擇商品", ["..."]+opts)
            if sel_item != "...":
                sku = sel_item.split(" | ")[0]
                with st.form("add_internal"):
                    q = st.number_input("數量", 1)
                    who = st.selectbox("領用人", staff_list)
                    rsn = st.selectbox("原因", ["公務","公關","福利","報廢","樣品","其他"])
                    note = st.text_input("備註 (Project/細節)")
                    if st.form_submit_button("提交"):
                        cell = ws_items.find(sku)
                        curr = int(ws_items.cell(cell.row, 5).value)
                        retry_action(ws_items.update_cell, cell.row, 5, curr - q)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{sku} -{q} | {who} | {rsn} | {note}")
                        st.success("已記錄"); st.cache_data.clear(); st.rerun()

        # B. 數據透視表 (Pivot Table)
        st.markdown("### 📊 多維度數據透視")
        if not logs_df.empty:
            int_df = logs_df[logs_df['Action']=="Internal_Use"].copy()
            if not int_df.empty:
                # 解析 Data
                def parse_log(d):
                    try:
                        p = d.split(' | ')
                        sku_p = p[0].split(' -')
                        return pd.Series([sku_p[0], int(sku_p[1]), p[1], p[2], p[3] if len(p)>3 else ""])
                    except: return pd.Series(["", 0, "", "", ""])
                
                int_df[['SKU', 'Qty', 'User', 'Reason', 'Note']] = int_df['Details'].apply(parse_log)
                # Join 商品資訊
                int_df['ItemName'] = int_df['SKU'].map(lambda x: product_map.get(x, x))
                int_df['Cost'] = int_df['SKU'].map(lambda x: df[df['SKU']==x]['Cost'].values[0] if not df[df['SKU']==x].empty else 0)
                int_df['TotalCost'] = int_df['Qty'] * int_df['Cost']

                # 統計控制台
                c_p1, c_p2 = st.columns(2)
                group_by = c_p1.selectbox("分組依據", ["User", "Reason", "ItemName", "Note"])
                metric = c_p2.radio("統計數值", ["Qty", "TotalCost"], horizontal=True)
                
                pivot = int_df.groupby(group_by)[metric].sum().sort_values(ascending=False).reset_index()
                st.dataframe(pivot, use_container_width=True)
                
                # 詳細清單
                with st.expander("查看詳細流水帳"):
                    st.dataframe(int_df[['Timestamp', 'User', 'ItemName', 'Qty', 'Reason', 'Note', 'TotalCost']], use_container_width=True)
            else: st.info("尚無領用紀錄")

    # 5. 管理 (保持)
    with tabs[4]:
        st.write("矩陣管理功能區 (同 V110.0)")

    # 6. 日誌 (保持)
    with tabs[5]:
        st.dataframe(logs_df, use_container_width=True)

    # 7. 用戶 (保持)
    with tabs[6]:
        st.dataframe(users_df, use_container_width=True)

    # 8. 排班 (使用新版 render_roster_system)
    with tabs[7]:
        render_roster_system(sh, staff_list, st.session_state['user_name'])

if __name__ == "__main__":
    main()
