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

# --- 1. 系統全域設定 (App-Like Config) ---
st.set_page_config(
    page_title="IFUKUK V104.1", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🛑 【OMEGA V104.1 視覺核心 (CSS Injection)】
# ==========================================
st.markdown("""
    <style>
        /* --- 0. 全局重置與 App 質感 --- */
        .stApp { background-color: #F8F9FA !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
        
        /* --- 1. 卡片式設計 (Card UI) --- */
        .omega-card {
            background: #FFFFFF;
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border: 1px solid #E5E7EB;
            margin-bottom: 12px;
            transition: transform 0.2s;
        }
        .omega-card:active { transform: scale(0.98); } 

        /* --- 2. 排班日曆樣式 (Roster Matrix) --- */
        .day-card {
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 8px;
            min-height: 80px;
            position: relative;
            cursor: pointer;
        }
        .day-card:hover { border-color: #000; }
        .day-num { font-weight: 900; font-size: 1.2rem; color: #333; }
        .shift-badge {
            font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; 
            margin-top: 4px; display: block; text-align: center; color: white; font-weight: bold;
        }
        .note-indicator {
            position: absolute; top: 5px; right: 5px; 
            width: 8px; height: 8px; background-color: #EF4444; border-radius: 50%;
        }
        
        /* --- 3. POS 畫廊模式 (Gallery Grid) --- */
        .product-card {
            border: 1px solid #eee; border-radius: 12px; overflow: hidden; background: #fff;
            display: flex; flex-direction: column; height: 100%;
        }
        .prod-img-box { width: 100%; height: 120px; object-fit: cover; background: #f0f0f0; }
        .prod-info { padding: 8px; flex-grow: 1; }
        .prod-title { font-weight: bold; font-size: 0.9rem; line-height: 1.2; margin-bottom: 4px; color: #111; }
        .prod-meta { font-size: 0.8rem; color: #666; }
        .prod-price { font-weight: 900; color: #059669; font-size: 1rem; margin-top: auto; }
        
        /* --- 4. 優化按鈕與輸入 (Thumb Zone) --- */
        .stButton>button {
            border-radius: 12px; height: 3.5rem; font-weight: 700; border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%;
        }
        div[data-baseweb="select"] > div { border-radius: 12px !important; min-height: 3rem; }
        
        /* --- 5. 戰情儀表板優化 --- */
        .metric-box {
            background: linear-gradient(135deg, #ffffff, #f3f4f6);
            border-radius: 12px; padding: 12px; text-align: center; border: 1px solid #e5e7eb;
        }
        .metric-val { font-size: 1.5rem; font-weight: 800; color: #111; }
        .metric-lbl { font-size: 0.75rem; color: #666; text-transform: uppercase; letter-spacing: 1px; }

        /* 隱藏預設元件噪音 */
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_data_safe(ws):
    max_retries = 3
    for i in range(max_retries):
        try:
            if ws is None: return pd.DataFrame()
            raw_data = ws.get_all_values()
            if not raw_data or len(raw_data) < 2: return pd.DataFrame()
            headers = raw_data[0]
            # Headers Deduplication
            seen = {}; new_headers = []
            for h in headers:
                if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
                else: seen[h] = 0; new_headers.append(h)
            rows = raw_data[1:]
            # Auto-Fix Qty_CN
            if "Qty_CN" not in new_headers:
                ws.update_cell(1, len(new_headers)+1, "Qty_CN")
                new_headers.append("Qty_CN"); raw_data = ws.get_all_values(); rows = raw_data[1:]
            df = pd.DataFrame(rows)
            if not df.empty:
                if len(df.columns) < len(new_headers):
                    for _ in range(len(new_headers) - len(df.columns)): df[len(df.columns)] = ""
                df.columns = new_headers[:len(df.columns)]
            return df
        except Exception: time.sleep(1); continue
    return pd.DataFrame()

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
def get_taiwan_time_str():
    return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

def render_image_url(url_input):
    if not url_input or (isinstance(url_input, float) and math.isnan(url_input)): return "https://i.ibb.co/W31w56W/placeholder.png"
    s = str(url_input).strip()
    return s if len(s) > 10 and s.startswith("http") else "https://i.ibb.co/W31w56W/placeholder.png"

def make_hash(password): return hashlib.sha256(str(password).encode()).hexdigest()
def check_hash(password, hashed_text): return make_hash(password) == hashed_text

def log_event(ws_logs, user, action, detail):
    try: ws_logs.append_row([get_taiwan_time_str(), user, action, detail])
    except: pass

# --- V104 智能排班邏輯 ---
def get_staff_color(name):
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6366F1"]
    hash_val = sum(ord(c) for c in str(name))
    return colors[hash_val % len(colors)]

def render_shift_calendar(sh, users_list):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Updated_By"])
    shifts_df = get_data_safe(ws_shifts)
    
    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        st.subheader("🗓️ 排班戰情室 (Roster Matrix)")
    
    now = datetime.utcnow() + timedelta(hours=8)
    c_y, c_m = st.columns(2)
    sel_year = c_y.number_input("年份", min_value=2024, max_value=2030, value=now.year)
    sel_month = c_m.selectbox("月份", range(1, 13), index=now.month - 1)
    
    cal = calendar.monthcalendar(sel_year, sel_month)
    month_name = calendar.month_name[sel_month]
    
    st.markdown(f"<h3 style='text-align:center; color:#444;'>{month_name} {sel_year}</h3>", unsafe_allow_html=True)
    
    cols = st.columns(7)
    days_header = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    for i, d in enumerate(days_header):
        cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#888;'>{d}</div>", unsafe_allow_html=True)
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True)
                else:
                    date_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == date_str] if not shifts_df.empty else pd.DataFrame()
                    has_note = False
                    badges_html = ""
                    if not day_shifts.empty:
                        for _, row in day_shifts.iterrows():
                            s_name = row['Staff']
                            s_note = row['Note']
                            bg_color = get_staff_color(s_name)
                            badges_html += f"<span class='shift-badge' style='background-color:{bg_color}'>{s_name}</span>"
                            if s_note and len(s_note) > 0: has_note = True
                    note_html = "<div class='note-indicator'></div>" if has_note else ""
                    if st.button(f"{day}", key=f"btn_day_{date_str}", use_container_width=True):
                        st.session_state['selected_date'] = date_str
                        st.rerun()
                    st.markdown(f"""
                        <div style='position:relative; margin-top:-60px; pointer-events:none; z-index:1; padding:5px;'>
                            <div style='float:right;'>{note_html}</div>
                            <div style='margin-top:20px;'>{badges_html}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

    if 'selected_date' in st.session_state:
        target_date = st.session_state['selected_date']
        with st.expander(f"📝 編輯班表：{target_date}", expanded=True):
            current_shifts = shifts_df[shifts_df['Date'] == target_date] if not shifts_df.empty else pd.DataFrame()
            c_edit1, c_edit2 = st.columns(2)
            with c_edit1:
                st.markdown("##### ➕ 新增排班")
                with st.form(f"add_shift_{target_date}"):
                    s_staff = st.selectbox("選擇人員", users_list)
                    s_note = st.text_input("備註/特別指令 (選填)")
                    if st.form_submit_button("排入班表"):
                        ws_shifts.append_row([target_date, s_staff, "一般", s_note, st.session_state['user_name']])
                        st.success("已排入"); time.sleep(0.5); st.rerun()
            with c_edit2:
                st.markdown("##### 🗑️ 當日已排人員")
                if not current_shifts.empty:
                    for _, row in current_shifts.iterrows():
                        col_info, col_del = st.columns([3, 1])
                        with col_info: st.info(f"👤 {row['Staff']} | 📝 {row['Note']}")
                        with col_del:
                            if st.button("移除", key=f"del_{target_date}_{row['Staff']}"):
                                all_vals = ws_shifts.get_all_values()
                                for idx, val in enumerate(all_vals):
                                    if len(val) > 1 and val[0] == target_date and val[1] == row['Staff']:
                                        ws_shifts.delete_rows(idx + 1); st.rerun()
                else: st.caption("尚無排班")

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = ""
        st.session_state['user_role'] = ""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    
    sh = init_db()
    if not sh: st.error("Database Connection Failed"); st.stop()

    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    # --- 登入頁面 (V104.1 FIX: 強韌登入邏輯) ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-weight:900; font-size:3rem; color:#111;'>IFUKUK</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; color:#666; font-size:1rem; letter-spacing:2px; margin-bottom:40px;'>OMEGA V104.1 (Stable)</div>", unsafe_allow_html=True)
            with st.form("login"):
                user_input = st.text_input("ID")
                pass_input = st.text_input("PASSWORD", type="password")
                
                if st.form_submit_button("ENTER SYSTEM", type="primary"):
                    # V104.1 Fix: 加入讀取回饋與嚴格錯誤捕捉
                    with st.spinner("Checking Credentials..."):
                        users_df = get_data_safe(ws_users)
                        input_u = str(user_input).strip()
                        input_p = str(pass_input).strip()
                        
                        if not input_u:
                            st.error("❌ 請輸入 ID")
                            st.stop()

                        # 1. 優先處理 Boss 初始化 (當資料庫真的為空時)
                        if users_df.empty and input_u == "Boss" and input_p == "1234":
                            ws_users.append_row(["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                            st.success("Admin Initialized. Please Login.")
                            time.sleep(1)
                            st.rerun()
                        
                        # 2. 正常登入檢查
                        if not users_df.empty:
                            target = users_df[(users_df['Name'] == input_u) & (users_df['Status'] == 'Active')]
                            if not target.empty:
                                stored = target.iloc[0]['Password']
                                if (len(stored)==64 and check_hash(input_p, stored)) or (input_p == stored):
                                    st.session_state['logged_in'] = True
                                    st.session_state['user_name'] = input_u
                                    st.session_state['user_role'] = target.iloc[0]['Role']
                                    log_event(ws_logs, input_u, "Login", "V104 Login")
                                    st.rerun()
                                else:
                                    st.error("❌ 密碼錯誤 (Invalid Password)")
                            else:
                                st.error(f"❌ 找不到使用者: {input_u}")
                        else:
                            # 3. 捕捉「資料庫讀取失敗」或「非 Boss 的空資料庫登入」
                            st.error("⚠️ 資料庫連線異常或為空，且非 Admin 初始帳號。")
        return

    # --- 主導航 ---
    user = st.session_state['user_name']
    st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #eee;">
            <div style="font-weight:900; font-size:1.2rem;">IFUKUK <span style="font-weight:400; font-size:0.8rem; color:#888;">| {user}</span></div>
            <div style="font-size:0.8rem; background:#eee; padding:4px 8px; border-radius:8px;">V104.1</div>
        </div>
    """, unsafe_allow_html=True)

    df = get_data_safe(ws_items)
    for c in ["Qty","Price","Qty_CN"]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    
    nav_options = ["🛒 POS", "📊 庫存", "🗓️ 班表", "📈 戰情", "🛠️ 管理", "🚪 登出"]
    nav_sel = st.radio("", nav_options, horizontal=True, label_visibility="collapsed")

    # --- 🛒 POS ---
    if nav_sel == "🛒 POS":
        c_pos_left, c_pos_right = st.columns([3, 2])
        with c_pos_left:
            st.markdown("#### 🛍️ 商品畫廊")
            cats = ["全部"] + list(df['Category'].unique()) if not df.empty else []
            sel_cat = st.selectbox("分類篩選", cats, label_visibility="collapsed")
            search_txt = st.text_input("🔍 快速搜尋...", placeholder="輸入關鍵字...")
            view_df = df.copy()
            if sel_cat != "全部": view_df = view_df[view_df['Category'] == sel_cat]
            if search_txt: view_df = view_df[view_df.apply(lambda x: search_txt.lower() in str(x.values).lower(), axis=1)]
            
            if not view_df.empty:
                cols_per_row = 3
                rows = [view_df.iloc[i:i+cols_per_row] for i in range(0, len(view_df), cols_per_row)]
                for row_data in rows:
                    cols = st.columns(cols_per_row)
                    for idx, (_, item) in enumerate(row_data.iterrows()):
                        with cols[idx]:
                            img_url = render_image_url(item['Image_URL'])
                            st.markdown(f"""
                                <div class="product-card">
                                    <div class="prod-img-box"><img src="{img_url}" style="width:100%; height:100%; object-fit:cover;"></div>
                                    <div class="prod-info">
                                        <div class="prod-title">{item['Name']}</div>
                                        <div class="prod-meta">{item['SKU']} | {item['Size']}</div>
                                        <div class="prod-price">${item['Price']}</div>
                                        <div style="font-size:0.7rem; color:#666;">TW:{item['Qty']}</div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            if st.button("➕", key=f"add_{item['SKU']}", use_container_width=True):
                                st.session_state['pos_cart'].append({
                                    "sku": item['SKU'], "name": item['Name'], "size": item['Size'],
                                    "price": int(item['Price']), "qty": 1, "subtotal": int(item['Price'])
                                })
                                st.toast(f"已加入: {item['Name']}")
            else: st.info("無符合商品")

        with c_pos_right:
            st.markdown("#### 🧾 購物車")
            if st.session_state['pos_cart']:
                cart_total = 0
                for i, c_item in enumerate(st.session_state['pos_cart']):
                    cart_total += c_item['subtotal']
                    st.markdown(f"""
                        <div style="background:#fff; padding:10px; border-radius:8px; border-bottom:1px dashed #ddd; display:flex; justify-content:space-between;">
                            <span>{c_item['name']} <small>({c_item['size']})</small> x1</span>
                            <b>${c_item['subtotal']}</b>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:right; font-size:1.5rem; font-weight:900; margin:10px 0;'>Total: ${cart_total}</div>", unsafe_allow_html=True)
                if st.button("🗑️ 清空", use_container_width=True): st.session_state['pos_cart'] = []; st.rerun()
                st.markdown("---")
                with st.form("checkout_v104"):
                    c_pay1, c_pay2 = st.columns(2)
                    pay_method = c_pay1.selectbox("付款", ["現金", "刷卡", "轉帳"])
                    sale_person = c_pay2.selectbox("經手", [user] + list(ws_users.col_values(1)[1:]))
                    note = st.text_input("備註")
                    if st.form_submit_button("✅ 確認結帳", type="primary"):
                        sale_details = []
                        for c_item in st.session_state['pos_cart']:
                            cell = ws_items.find(c_item['sku'])
                            if cell:
                                curr = int(ws_items.cell(cell.row, 5).value)
                                if curr >= c_item['qty']:
                                    ws_items.update_cell(cell.row, 5, curr - c_item['qty'])
                                    sale_details.append(f"{c_item['sku']} x1")
                                else: st.error(f"{c_item['sku']} 庫存不足"); st.stop()
                        full_log = f"Sale | Total:${cart_total} | {', '.join(sale_details)} | {note} | {pay_method} | By:{sale_person}"
                        log_event(ws_logs, user, "Sale", full_log)
                        st.session_state['pos_cart'] = []
                        st.balloons(); st.success(f"結帳完成 ${cart_total}"); time.sleep(1); st.rerun()
            else: st.info("購物車是空的")

    # --- 📊 庫存 ---
    elif nav_sel == "📊 庫存":
        st.subheader("📦 庫存總覽")
        m1, m2 = st.columns(2)
        m1.markdown(f"<div class='metric-box'><div class='metric-val'>{df['Qty'].sum()}</div><div class='metric-lbl'>台灣總庫存</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-box'><div class='metric-val'>{len(df)}</div><div class='metric-lbl'>總品項數</div></div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📄 詳細庫存表 (點擊展開)", expanded=True):
            st.dataframe(df[["SKU", "Name", "Category", "Size", "Qty", "Qty_CN", "Price"]], use_container_width=True)

    # --- 🗓️ 班表 ---
    elif nav_sel == "🗓️ 班表":
        users_list = ws_users.col_values(1)[1:] if ws_users else []
        render_shift_calendar(sh, users_list)

    # --- 📈 戰情 ---
    elif nav_sel == "📈 戰情":
        logs_df = get_data_safe(ws_logs)
        st.subheader("📈 銷售數據")
        if not logs_df.empty:
            sales = logs_df[logs_df['Action'] == 'Sale']
            st.write(f"總交易筆數: {len(sales)}")
            st.dataframe(sales, use_container_width=True)
        else: st.info("無數據")

    # --- 🛠️ 管理 ---
    elif nav_sel == "🛠️ 管理":
        st.warning("⚠️ 進階管理功能請使用桌面版 V103 介面操作。")
        with st.expander("🛠️ 快速調撥 (TW <-> CN)"): st.write("此處功能即將在 V104.1 開放")

    # --- 🚪 登出 ---
    elif nav_sel == "🚪 登出":
        st.session_state['logged_in'] = False; st.rerun()

if __name__ == "__main__":
    main()
