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

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK V103.6 ANCHOR", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🛑 全域變數定義 (防止 NameError 的關鍵)
# ==========================================
# 這些變數現在放在最外層，保證任何功能區都能讀取到，不會再報錯
CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]
SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]

SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"

# ==========================================
# 🛑 視覺樣式 (V104 Fluid Skin)
# ==========================================
st.markdown("""
    <style>
        .stApp { background-color: #F8F9FA !important; }
        
        /* 導航列優化 */
        div[data-testid="stRadio"] > label { display:none; }
        div[data-testid="stRadio"] > div { 
            flex-direction: row; gap: 10px; justify-content: center; 
            background: #fff; padding: 10px; border-radius: 12px; 
            border: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
            overflow-x: auto;
        }
        
        /* POS 卡片 */
        .pos-card { 
            background: #fff; border-radius: 12px; overflow: hidden; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid #E5E7EB; 
            display: flex; flex-direction: column; height: 100%; 
        }
        .pos-img { width: 100%; height: 120px; object-fit: cover; background: #f0f0f0; }
        .pos-content { padding: 8px; flex-grow: 1; }
        .pos-title { font-weight: bold; font-size: 0.9rem; color: #111; margin-bottom: 4px; line-height: 1.2; }
        .pos-price { color: #059669; font-weight: 900; font-size: 1rem; }
        .pos-stock { font-size: 0.75rem; color: #666; background: #f3f4f6; padding: 2px 6px; border-radius: 4px; display: inline-block; margin-top: 4px; }

        /* 購物車與價格 */
        .cart-box { background: #fff; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px; }
        .cart-item { display: flex; justify-content: space-between; border-bottom: 1px dashed #ddd; padding: 8px 0; font-size: 0.9rem; }
        .final-price-box { font-size: 1.8rem; font-weight: 900; color: #16a34a; text-align: center; background: #dcfce7; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #86efac; }
        
        /* 戰情看板 */
        .metric-card { background: #fff; border-radius: 12px; padding: 15px; border: 1px solid #eee; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 100%; }
        .metric-val { font-size: 1.5rem; font-weight: 800; color:#111; margin: 5px 0; }
        .metric-lbl { font-size: 0.8rem; color:#666; font-weight: 600; text-transform: uppercase;}
        .metric-sub { font-size: 0.75rem; color: #999; margin-top: -5px; }

        /* 按鈕與輸入 */
        .stButton>button { border-radius: 10px; height: 3.2rem; font-weight: 700; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 100%; }
        input, .stTextInput>div>div, div[data-baseweb="select"]>div { border-radius: 10px !important; min-height: 3rem; }
        .shift-badge { font-size: 0.7rem; padding: 2px 5px; border-radius: 4px; margin: 2px; display: inline-block; color: white; font-weight: bold; }
        
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 核心連線 (Anti-Crash Logic) ---
@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def init_db():
    try:
        client = get_connection()
        return client.open_by_url(GOOGLE_SHEET_URL)
    except Exception: return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        try:
            ws = sh.add_worksheet(title, rows=100, cols=20)
            ws.append_row(headers)
            return ws
        except: return None
    except: return None

# [快取讀取] 防止 Quota Exceeded
@st.cache_data(ttl=15, show_spinner=False) 
def get_data_cached(_ws_obj, ensure_qty_cn=False):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if _ws_obj is None: return pd.DataFrame()
            raw_data = _ws_obj.get_all_values()
            if not raw_data or len(raw_data) < 2: return pd.DataFrame()
            headers = raw_data[0]
            seen = {}; new_headers = []
            for h in headers:
                if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
                else: seen[h] = 0; new_headers.append(h)
            rows = raw_data[1:]
            if ensure_qty_cn and "Qty_CN" not in new_headers:
                try:
                    _ws_obj.update_cell(1, len(new_headers)+1, "Qty_CN")
                    new_headers.append("Qty_CN"); raw_data = _ws_obj.get_all_values(); rows = raw_data[1:]
                except: pass
            df = pd.DataFrame(rows)
            if not df.empty:
                if len(df.columns) < len(new_headers):
                    for _ in range(len(new_headers) - len(df.columns)): df[len(df.columns)] = ""
                df.columns = new_headers[:len(df.columns)]
            return df
        except Exception as e:
            if "429" in str(e): time.sleep(2 ** (attempt + 1)); continue
            return pd.DataFrame()
    return pd.DataFrame()

# [重試寫入]
def update_cell_retry(ws, row, col, value, retries=3):
    for i in range(retries):
        try: ws.update_cell(row, col, value); return True
        except Exception as e:
            if "429" in str(e): time.sleep(2 ** (i + 1)); continue
    return False

# --- 工具模組 ---
def get_taiwan_time_str(): return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
def render_image_url(url_input):
    if not url_input or (isinstance(url_input, float) and math.isnan(url_input)): return "https://i.ibb.co/W31w56W/placeholder.png"
    s = str(url_input).strip()
    return s if len(s) > 10 and s.startswith("http") else "https://i.ibb.co/W31w56W/placeholder.png"
def make_hash(password): return hashlib.sha256(str(password).encode()).hexdigest()
def check_hash(password, hashed_text): return make_hash(password) == hashed_text
def log_event(ws_logs, user, action, detail):
    try: ws_logs.append_row([get_taiwan_time_str(), user, action, detail])
    except: pass
def upload_image_to_imgbb(image_file):
    if not IMGBB_API_KEY: return None
    try:
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(image_file.getvalue()).decode('utf-8')}
        response = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if response.status_code == 200: return response.json()["data"]["url"]
    except: pass; return None
def get_style_code(sku): return str(sku).strip().rsplit('-', 1)[0] if '-' in str(sku) else str(sku).strip()
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
    if logs_df.empty: return 0
    sales = logs_df[logs_df['Action'] == 'Sale']
    for _, row in sales.iterrows():
        try: total += int(re.search(r'Total:\$(\d+)', row['Details']).group(1))
        except: pass
    return total

# --- 班表模組 ---
def get_status_color(status):
    if status == "上班": return "#10B981"
    if status == "公休": return "#6B7280"
    if status == "特休": return "#EF4444"
    if status == "空班": return "#F59E0B"
    return "#3B82F6"

def render_roster_system(sh, users_list):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Updated_By"])
    shifts_df = get_data_cached(ws_shifts)
    
    st.subheader("🗓️ 專業排班系統")
    now = datetime.utcnow() + timedelta(hours=8)
    c1, c2 = st.columns([1, 1])
    sel_year = c1.number_input("年份", 2024, 2030, now.year)
    sel_month = c2.selectbox("月份", range(1, 13), now.month - 1)
    
    cal = calendar.monthcalendar(sel_year, sel_month)
    cols = st.columns(7)
    for i, d in enumerate(["一", "二", "三", "四", "五", "六", "日"]): 
        cols[i].markdown(f"<div style='text-align:center;font-weight:bold;'>{d}</div>", unsafe_allow_html=True)
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day != 0:
                    date_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == date_str] if not shifts_df.empty else pd.DataFrame()
                    badges = "".join([f"<span class='shift-badge' style='background:{get_status_color(r['Shift_Type'])}'>{r['Staff']}</span>" for _, r in day_shifts.iterrows()])
                    if st.button(f"{day}", key=f"cal_{date_str}", use_container_width=True):
                        st.session_state['roster_date'] = date_str
                        st.rerun()
                    st.markdown(f"<div style='min-height:30px;text-align:center;line-height:1.2;'>{badges}</div>", unsafe_allow_html=True)
                else: st.markdown("<div style='min-height:60px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    ce, cl = st.columns([1, 2])
    with ce:
        if 'roster_date' in st.session_state:
            t_date = st.session_state['roster_date']
            st.info(f"編輯: {t_date}")
            with st.form("roster_add"):
                staff = st.selectbox("人員", users_list)
                status = st.selectbox("狀態", ["上班", "公休", "特休", "空班"])
                note = st.text_input("備註")
                if st.form_submit_button("💾 儲存"):
                    all_v = ws_shifts.get_all_values()
                    rows_to_del = [idx+1 for idx, v in enumerate(all_v) if len(v)>1 and v[0]==t_date and v[1]==staff]
                    for r_idx in reversed(rows_to_del): ws_shifts.delete_rows(r_idx)
                    ws_shifts.append_row([t_date, staff, status, note, st.session_state['user_name']])
                    st.cache_data.clear(); st.success("已更新"); time.sleep(0.5); st.rerun()
            
            curr = shifts_df[shifts_df['Date'] == t_date] if not shifts_df.empty else pd.DataFrame()
            if not curr.empty:
                st.caption("點擊移除:")
                for _, r in curr.iterrows():
                    if st.button(f"❌ {r['Staff']} ({r['Shift_Type']})", key=f"del_{t_date}_{r['Staff']}"):
                        all_v = ws_shifts.get_all_values()
                        for idx, v in enumerate(all_v):
                            if len(v)>1 and v[0]==t_date and v[1]==r['Staff']: ws_shifts.delete_rows(idx+1); break
                        st.cache_data.clear(); st.rerun()
        else: st.info("👈 請選擇日期")

    with cl:
        st.markdown(f"##### 📅 {sel_month}月 總表")
        if not shifts_df.empty:
            m_prefix = f"{sel_year}-{str(sel_month).zfill(2)}"
            m_df = shifts_df[shifts_df['Date'].str.startswith(m_prefix)].copy()
            if not m_df.empty:
                m_df = m_df.sort_values(['Date', 'Staff'])
                st.dataframe(m_df[['Date', 'Staff', 'Shift_Type', 'Note']], use_container_width=True, hide_index=True)
            else: st.caption("無資料")

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False; st.session_state['user_name'] = ""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    
    sh = init_db()
    if not sh: st.warning("連線建立中..."); return
    
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])
    
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><h1 style='text-align:center'>IFUKUK</h1><p style='text-align:center'>OMEGA V103.6 ANCHOR</p>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("ID"); p = st.text_input("PASSWORD", type="password")
                if st.form_submit_button("ENTER SYSTEM", type="primary"):
                    with st.spinner("Secure Login..."):
                        udf = get_data_cached(ws_users, False)
                        if udf.empty and u=="Boss" and p=="1234":
                            ws_users.append_row(["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                            st.cache_data.clear(); st.success("Init OK"); time.sleep(1); st.rerun()
                        # 安全讀取，避免 KeyError
                        if not udf.empty and 'Name' in udf.columns:
                            tgt = udf[(udf['Name']==u) & (udf['Status']=='Active')]
                            if not tgt.empty:
                                stored = tgt.iloc[0]['Password']
                                if (len(stored)==64 and check_hash(p, stored)) or (p==stored):
                                    st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=tgt.iloc[0]['Role']; st.rerun()
                            st.error("❌ 登入失敗")
                        else: st.warning("⚠️ 連線忙碌，請重試")
        return

    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    
    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:10px;border-bottom:1px solid #eee;'><b>IFUKUK | {st.session_state['user_name']}</b><span>V103.6</span></div>", unsafe_allow_html=True)
    
    df = get_data_cached(ws_items, True)
    for c in ["Qty","Price","Qty_CN","Cost","Orig_Cost","Safety_Stock"]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    
    nav = st.radio("", ["🛒 POS", "📊 庫存", "🗓️ 班表", "📈 戰情", "🎁 領用", "👔 管理", "🚪 登出"], horizontal=True, label_visibility="collapsed")
    
    # --- 1. POS ---
    if nav == "🛒 POS":
        c_l, c_r = st.columns([3, 2])
        with c_l:
            st.markdown("##### 🛍️ 商品畫廊")
            # 修正圖二問題：確保下拉選單包含所有分類
            cats_available = list(df['Category'].unique()) if not df.empty else []
            # 結合 預設分類表(CAT_LIST) 與 實際有貨分類(cats_available) 並去重
            all_cats = sorted(list(set(CAT_LIST + cats_available)))
            
            col_s1, col_s2 = st.columns([2,1])
            q = col_s1.text_input("🔍", placeholder="搜尋...", label_visibility="collapsed")
            cat = col_s2.selectbox("分類", ["全部"] + all_cats, label_visibility="collapsed")
            
            vdf = df.copy()
            if cat != "全部": vdf = vdf[vdf['Category'] == cat]
            if q: vdf = vdf[vdf.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
            
            if not vdf.empty:
                vdf = vdf.head(40)
                rows = [vdf.iloc[i:i+3] for i in range(0, len(vdf), 3)]
                for r in rows:
                    cols = st.columns(3)
                    for i, (_, item) in enumerate(r.iterrows()):
                        with cols[i]:
                            st.markdown(f"<div class='pos-card'><div class='pos-img'><img src='{render_image_url(item['Image_URL'])}' style='width:100%;height:100%;object-fit:cover;'></div><div class='pos-content'><div class='pos-title'>{item['Name']}</div><div class='pos-price'>${item['Price']}</div><div class='pos-stock'>TW:{item['Qty']}</div></div></div>", unsafe_allow_html=True)
                            if st.button("➕", key=f"add_{item['SKU']}", use_container_width=True):
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
                        st.markdown(f"<div class='cart-item'><span>{i['name']} ({i['size']})</span><b>${i['subtotal']}</b></div>", unsafe_allow_html=True)
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
                    st.markdown(f"<div class='final-price-box'>${final_total}</div>", unsafe_allow_html=True)
                    
                    sale_who = st.selectbox("經手", [st.session_state['user_name']] + list(ws_users.col_values(1)[1:]))
                    sale_ch = st.selectbox("通路", ["門市","官網","直播"])
                    pay = st.selectbox("付款", ["現金","刷卡","轉帳"])
                    note = st.text_input("備註")
                    
                    if st.button("✅ 結帳", type="primary", use_container_width=True):
                        logs = []
                        valid = True
                        for item in st.session_state['pos_cart']:
                            cell = ws_items.find(item['sku'])
                            if cell:
                                curr = int(ws_items.cell(cell.row, 5).value)
                                if curr >= item['qty']:
                                    update_cell_retry(ws_items, cell.row, 5, curr - item['qty'])
                                    logs.append(f"{item['sku']} x{item['qty']}")
                                else: st.error(f"{item['name']} 庫存不足"); valid=False; break
                        
                        if valid:
                            content = f"Sale | Total:${final_total} | Items:{','.join(logs)} | {note} {note_str} | {pay} | {sale_ch} | By:{sale_who}"
                            log_event(ws_logs, st.session_state['user_name'], "Sale", content)
                            st.session_state['pos_cart'] = []
                            st.cache_data.clear(); st.balloons(); st.success("完成"); time.sleep(1); st.rerun()
                else: st.info("購物車是空的")
                st.markdown("</div>", unsafe_allow_html=True)

    # --- 2. 庫存 ---
    elif nav == "📊 庫存":
        st.subheader("📦 庫存總覽")
        m1, m2, m3 = st.columns(3)
        m1.metric("台灣總庫存", df['Qty'].sum())
        m2.metric("中國總庫存", df['Qty_CN'].sum())
        m3.metric("總品項數", len(df))
        st.dataframe(df, use_container_width=True)

    # --- 3. 班表 ---
    elif nav == "🗓️ 班表":
        render_roster_system(sh, ws_users.col_values(1)[1:])

    # --- 4. 戰情 ---
    elif nav == "📈 戰情":
        st.subheader("📈 營運戰情室")
        rev = (df['Qty'] * df['Price']).sum()
        cost = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum()
        rmb_total = 0
        if 'Orig_Currency' in df.columns:
            rmb_df = df[df['Orig_Currency'] == 'CNY']
            if not rmb_df.empty: rmb_total = ((rmb_df['Qty'] + rmb_df['Qty_CN']) * rmb_df['Orig_Cost']).sum()
        profit = rev - (df['Qty'] * df['Cost']).sum()
        real = calculate_realized_revenue(get_data_cached(ws_logs))
        
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='metric-card'><div class='metric-lbl'>預估營收</div><div class='metric-val'>${rev:,}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-lbl'>總成本 (TWD)</div><div class='metric-val'>${cost:,}</div><div class='metric-sub'>含 RMB 原幣: ¥{rmb_total:,}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><div class='metric-lbl'>潛在毛利</div><div class='metric-val' style='color:#f59e0b'>${profit:,}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card'><div class='metric-lbl'>實際營收</div><div class='metric-val' style='color:#10b981'>${real:,}</div></div>", unsafe_allow_html=True)
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(df, names='Category', values='Qty', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            top = df.groupby('Name')['Qty'].sum().sort_values(ascending=False).head(10).reset_index()
            fig2 = px.bar(top, x='Qty', y='Name', orientation='h')
            st.plotly_chart(fig2, use_container_width=True)

    # --- 5. 領用 ---
    elif nav == "🎁 領用":
        st.subheader("🎁 內部領用")
        t1, t2 = st.tabs(["新增領用", "紀錄"])
        with t1:
            opts = [f"{r['SKU']} | {r['Name']}" for _, r in df.iterrows()]
            sel = st.selectbox("商品", ["..."]+opts)
            if sel != "...":
                sku = sel.split(" | ")[0]
                row = df[df['SKU']==sku].iloc[0]
                st.info(f"庫存: {row['Qty']}")
                with st.form("int_use"):
                    q = st.number_input("數量", 1, max_value=int(row['Qty']) if int(row['Qty'])>0 else 1)
                    who = st.selectbox("人", [st.session_state['user_name']]+list(ws_users.col_values(1)[1:]))
                    rsn = st.selectbox("原因", ["公務","福利","樣品","報廢"])
                    note = st.text_input("備註")
                    if st.form_submit_button("扣除"):
                        r = ws_items.find(sku).row
                        update_cell_retry(ws_items, r, 5, int(row['Qty'])-q)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{sku} -{q} | {who} | {rsn} | {note}")
                        st.cache_data.clear(); st.success("OK"); st.rerun()
        with t2:
            logs = get_data_cached(ws_logs)
            if not logs.empty: st.dataframe(logs[logs['Action']=="Internal_Use"], use_container_width=True)

    # --- 6. 管理 ---
    elif nav == "👔 管理":
        st.subheader("👔 管理矩陣")
        t1, t2, t3, t4 = st.tabs(["矩陣新增", "調撥", "重鑄", "刪除"])
        
        with t1:
            mode = st.radio("模式", ["新系列", "衍生"], horizontal=True)
            a_sku, a_name = "", ""
            if mode=="新系列":
                # 修正圖一問題：這裡的 CAT_LIST 現在是讀取全域變數，絕對安全
                c = st.selectbox("分類", CAT_LIST)
                if st.button("生成貨號"): st.session_state['base'] = generate_smart_style_code(c, df['SKU'].tolist())
                if 'base' in st.session_state: a_sku = st.session_state['base']
            else:
                p = st.selectbox("母商品", ["..."]+df['SKU'].tolist())
                if p!="...": 
                    r = df[df['SKU']==p].iloc[0]
                    a_sku = get_style_code(p)+"-NEW"; a_name = r['Name']
            
            with st.form("add_m"):
                c1, c2 = st.columns(2)
                b_sku = c1.text_input("Base SKU", value=a_sku)
                name = c2.text_input("品名", value=a_name)
                c3, c4 = st.columns(2)
                pr = c3.number_input("售價", 0)
                co = c4.number_input("成本", 0)
                img = st.file_uploader("圖片")
                st.caption("尺寸:")
                sizes = {}
                cols = st.columns(5)
                # 修正圖一問題：SIZE_ORDER 也是全域變數，安全
                for i, s in enumerate(SIZE_ORDER): sizes[s] = cols[i%5].number_input(s, min_value=0)
                if st.form_submit_button("寫入"):
                    url = upload_image_to_imgbb(img) if img else ""
                    for s, q in sizes.items():
                        if q>0: ws_items.append_row([f"{b_sku}-{s}", name, "New", s, q, pr, co, get_taiwan_time_str(), url, 5, "TWD", co, 0])
                    st.cache_data.clear(); st.success("OK"); st.rerun()

        with t2:
            s = st.selectbox("調撥商品", ["..."]+df['SKU'].tolist())
            if s!="...":
                r = df[df['SKU']==s].iloc[0]
                st.write(f"TW: {r['Qty']} | CN: {r['Qty_CN']}")
                q = st.number_input("數量", 1)
                c1, c2 = st.columns(2)
                if c1.button("TW->CN"):
                    rw = ws_items.find(s).row
                    update_cell_retry(ws_items, rw, 5, int(r['Qty'])-q)
                    update_cell_retry(ws_items, rw, 13, int(r['Qty_CN'])+q)
                    st.cache_data.clear(); st.success("OK"); st.rerun()
                if c2.button("CN->TW"):
                    rw = ws_items.find(s).row
                    update_cell_retry(ws_items, rw, 5, int(r['Qty'])+q)
                    update_cell_retry(ws_items, rw, 13, int(r['Qty_CN'])-q)
                    st.cache_data.clear(); st.success("OK"); st.rerun()
        
        with t4:
            d = st.selectbox("刪除", ["..."]+df['SKU'].tolist())
            if d!="..." and st.button("確認"):
                ws_items.delete_rows(ws_items.find(d).row)
                st.cache_data.clear(); st.success("OK"); st.rerun()

    elif nav == "🚪 登出":
        st.session_state['logged_in'] = False; st.rerun()

if __name__ == "__main__":
    main()
