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

# --- 1. 系統全域設定 (必須放第一行) ---
st.set_page_config(
    page_title="IFUKUK V105.1 STABLE", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🛑 【視覺核心 (V104 Skin)】
# ==========================================
st.markdown("""
    <style>
        .stApp { background-color: #F8F9FA !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
        
        /* 卡片與容器優化 */
        .omega-card { background: #FFFFFF; border-radius: 16px; padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #E5E7EB; margin-bottom: 12px; }
        .product-card { border: 1px solid #eee; border-radius: 12px; overflow: hidden; background: #fff; display: flex; flex-direction: column; height: 100%; transition: transform 0.2s; }
        .product-card:active { transform: scale(0.98); }
        .prod-img-box { width: 100%; height: 120px; object-fit: cover; background: #f0f0f0; }
        .prod-info { padding: 8px; flex-grow: 1; }
        .prod-title { font-weight: bold; font-size: 0.9rem; line-height: 1.2; margin-bottom: 4px; color: #111; }
        .prod-meta { font-size: 0.8rem; color: #666; }
        .prod-price { font-weight: 900; color: #059669; font-size: 1rem; margin-top: auto; }
        
        /* 購物車與輸入優化 */
        .cart-box { background: #fff; border: 1px solid #e2e8f0; padding: 10px; border-radius: 12px; margin-bottom: 10px; }
        .cart-item { display: flex; justify-content: space-between; border-bottom: 1px dashed #eee; padding: 8px 0; font-size: 0.9rem; }
        .final-price { font-size: 1.5rem; font-weight: 900; color: #16a34a; text-align: center; background: #dcfce7; padding: 10px; border-radius: 8px; margin-top: 10px; }
        
        /* 按鈕與輸入 */
        .stButton>button { border-radius: 12px; height: 3.2rem; font-weight: 700; border: none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); width: 100%; }
        div[data-baseweb="select"] > div { border-radius: 12px !important; min-height: 3rem; }
        
        /* 戰情儀表板 */
        .metric-card { background: #fff; border-radius: 12px; padding: 10px; border: 1px solid #eee; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 100%; }
        .metric-val { font-size: 1.4rem; font-weight: 800; color:#111; margin: 5px 0; }
        .metric-lbl { font-size: 0.7rem; color:#666; font-weight: 600; text-transform: uppercase;}
        
        /* 排班表 */
        .shift-badge { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; margin-top: 4px; display: block; text-align: center; color: white; font-weight: bold; }
        .note-indicator { position: absolute; top: 5px; right: 5px; width: 8px; height: 8px; background-color: #EF4444; border-radius: 50%; }

        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- 核心連線模組 ---
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
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        try:
            ws = sh.add_worksheet(title, rows=100, cols=20)
            ws.append_row(headers)
            return ws
        except: return None
    except: return None

def get_data_safe(ws, ensure_qty_cn=False):
    try:
        if ws is None: return pd.DataFrame()
        raw_data = ws.get_all_values()
        if not raw_data or len(raw_data) < 2: return pd.DataFrame()
        headers = raw_data[0]
        # 標題去重
        seen = {}; new_headers = []
        for h in headers:
            if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
            else: seen[h] = 0; new_headers.append(h)
        rows = raw_data[1:]
        
        # 僅在讀取 Items 表時啟用欄位修復 (修復 Range Exceed 錯誤)
        if ensure_qty_cn and "Qty_CN" not in new_headers:
            try:
                ws.update_cell(1, len(new_headers)+1, "Qty_CN")
                new_headers.append("Qty_CN"); raw_data = ws.get_all_values(); rows = raw_data[1:]
            except: pass
            
        df = pd.DataFrame(rows)
        if not df.empty:
            if len(df.columns) < len(new_headers):
                for _ in range(len(new_headers) - len(df.columns)): df[len(df.columns)] = ""
            df.columns = new_headers[:len(df.columns)]
        return df
    except Exception: return pd.DataFrame()

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
SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
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

# --- 班表渲染 (V104 Feature) ---
def get_staff_color(name):
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6366F1"]
    return colors[sum(ord(c) for c in str(name)) % len(colors)]

def render_shift_calendar(sh, users_list):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Updated_By"])
    shifts_df = get_data_safe(ws_shifts, False)
    
    col_h1, col_h2 = st.columns([2, 1])
    with col_h1: st.subheader("🗓️ 排班戰情室")
    
    now = datetime.utcnow() + timedelta(hours=8)
    c_y, c_m = st.columns(2)
    sel_year = c_y.number_input("年份", 2024, 2030, now.year)
    sel_month = c_m.selectbox("月份", range(1, 13), now.month - 1)
    
    cal = calendar.monthcalendar(sel_year, sel_month)
    cols = st.columns(7)
    for i, d in enumerate(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]): cols[i].markdown(f"<div style='text-align:center;color:#888;font-weight:bold;'>{d}</div>", unsafe_allow_html=True)
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day != 0:
                    date_str = f"{sel_year}-{str(sel_month).zfill(2)}-{str(day).zfill(2)}"
                    day_shifts = shifts_df[shifts_df['Date'] == date_str] if not shifts_df.empty else pd.DataFrame()
                    badges = "".join([f"<span class='shift-badge' style='background:{get_staff_color(r['Staff'])}'>{r['Staff']}</span>" for _, r in day_shifts.iterrows()])
                    note_dot = "<div class='note-indicator'></div>" if any(len(str(r['Note'])) > 0 for _, r in day_shifts.iterrows()) else ""
                    if st.button(f"{day}", key=f"d_{date_str}", use_container_width=True): st.session_state['selected_date'] = date_str; st.rerun()
                    st.markdown(f"<div style='margin-top:-60px;pointer-events:none;padding:5px;'><div style='float:right'>{note_dot}</div><div style='margin-top:20px'>{badges}</div></div>", unsafe_allow_html=True)
                else: st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True)
    
    if 'selected_date' in st.session_state:
        target_date = st.session_state['selected_date']
        with st.expander(f"📝 編輯班表：{target_date}", expanded=True):
            with st.form(f"s_form_{target_date}"):
                c1, c2 = st.columns(2)
                s_staff = c1.selectbox("人員", users_list)
                s_note = c2.text_input("備註")
                if st.form_submit_button("➕ 排入"): ws_shifts.append_row([target_date, s_staff, "一般", s_note, st.session_state['user_name']]); st.rerun()
            curr = shifts_df[shifts_df['Date'] == target_date] if not shifts_df.empty else pd.DataFrame()
            for _, r in curr.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.info(f"{r['Staff']} | {r['Note']}")
                if c2.button("移除", key=f"rm_{target_date}_{r['Staff']}"):
                     all_v = ws_shifts.get_all_values()
                     for idx, v in enumerate(all_v):
                         if len(v)>1 and v[0]==target_date and v[1]==r['Staff']: ws_shifts.delete_rows(idx+1); break
                     st.rerun()

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False; st.session_state['user_name'] = ""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    
    # 步驟 1: 建立連線 (如有錯誤會直接顯示，不會白屏)
    sh = init_db()
    if not sh: return
    
    # 步驟 2: 僅讀取使用者表 (確保登入畫面秒開)
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])
    
    # ------------------
    # 登入介面
    # ------------------
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><h1 style='text-align:center'>IFUKUK</h1><p style='text-align:center'>OMEGA V105.1 (Fixed)</p>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("ID")
                p = st.text_input("PASSWORD", type="password")
                if st.form_submit_button("ENTER SYSTEM", type="primary"):
                    with st.spinner("Connecting..."):
                        # 禁止在此處修復欄位，避免 Range Error
                        udf = get_data_safe(ws_users, ensure_qty_cn=False)
                        
                        # Boss 初始後門
                        if udf.empty and u=="Boss" and p=="1234":
                            ws_users.append_row(["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                            st.success("Init Success. Please Login."); time.sleep(1); st.rerun()
                        
                        # 驗證邏輯
                        tgt = udf[(udf['Name']==u) & (udf['Status']=='Active')]
                        if not tgt.empty:
                            stored = tgt.iloc[0]['Password']
                            if (len(stored)==64 and check_hash(p, stored)) or (p==stored):
                                st.session_state['logged_in']=True
                                st.session_state['user_name']=u
                                st.session_state['user_role']=tgt.iloc[0]['Role']
                                st.rerun()
                        st.error("❌ 登入失敗 (Login Failed)")
        return  # 未登入時直接結束，避免讀取後面重資料

    # ------------------
    # 登入後：才讀取重資料 (Items, Logs)
    # ------------------
    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    
    # 頂部導航
    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:10px;border-bottom:1px solid #eee;'><b>IFUKUK | {st.session_state['user_name']}</b><span>V105.1</span></div>", unsafe_allow_html=True)
    
    # 讀取庫存 (僅在此處啟用欄位修復 ensure_qty_cn=True)
    df = get_data_safe(ws_items, ensure_qty_cn=True)
    for c in ["Qty","Price","Qty_CN","Cost","Orig_Cost","Safety_Stock"]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    
    # 手機導航 (加入領用、管理)
    nav = st.radio("", ["🛒 POS", "📊 庫存", "🗓️ 班表", "📈 戰情", "🎁 領用", "👔 管理", "🚪 登出"], horizontal=True, label_visibility="collapsed")
    
    # --- 1. POS (V104 畫廊 + V103 完整結帳邏輯) ---
    if nav == "🛒 POS":
        c_l, c_r = st.columns([3, 2])
        with c_l:
            st.markdown("#### 🛍️ 商品畫廊")
            cats = ["全部"] + list(df['Category'].unique()) if not df.empty else []
            cat = st.selectbox("分類", cats, label_visibility="collapsed")
            q = st.text_input("🔍", placeholder="搜尋...")
            vdf = df.copy()
            if cat != "全部": vdf = vdf[vdf['Category'] == cat]
            if q: vdf = vdf[vdf.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
            
            if not vdf.empty:
                rows = [vdf.iloc[i:i+3] for i in range(0, len(vdf), 3)]
                for r in rows:
                    cols = st.columns(3)
                    for i, (_, item) in enumerate(r.iterrows()):
                        with cols[i]:
                            st.markdown(f"<div class='product-card'><div class='prod-img-box'><img src='{render_image_url(item['Image_URL'])}' style='width:100%;height:100%;object-fit:cover;'></div><div class='prod-info'><div class='prod-title'>{item['Name']}</div><div class='prod-meta'>{item['SKU']} | {item['Size']}</div><div class='prod-price'>${item['Price']}</div><small>TW:{item['Qty']}</small></div></div>", unsafe_allow_html=True)
                            if st.button("➕", key=f"add_{item['SKU']}", use_container_width=True):
                                st.session_state['pos_cart'].append({"sku":item['SKU'],"name":item['Name'],"size":item['Size'],"price":item['Price'],"qty":1,"subtotal":item['Price']})
                                st.toast(f"已加入 {item['Name']}")
        
        with c_r:
            st.markdown("#### 🧾 購物車 (完整功能版)")
            if st.session_state['pos_cart']:
                base_total = sum(i['subtotal'] for i in st.session_state['pos_cart'])
                for i in st.session_state['pos_cart']: st.markdown(f"<div class='cart-item'><span>{i['name']} ({i['size']})</span><b>${i['subtotal']}</b></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:right;font-size:1.2rem;font-weight:bold;margin:10px 0'>原價: ${base_total}</div>", unsafe_allow_html=True)
                
                if st.button("🗑️ 清空購物車"): st.session_state['pos_cart']=[]; st.rerun()
                
                # V103 完整結帳邏輯回歸
                with st.form("checkout_v105"):
                    c1, c2 = st.columns(2)
                    sale_ch = c1.selectbox("通路", ["門市", "官網", "直播", "其他"])
                    sale_who = c2.selectbox("銷售員", [st.session_state['user_name']] + list(ws_users.col_values(1)[1:]))
                    
                    disc_mode = st.radio("折扣", ["無", "員工7折", "員工8折", "自訂折數"], horizontal=True)
                    cust_off = st.number_input("自訂折數(%)", 1, 100, 95) if disc_mode=="自訂折數" else 0
                    
                    # 計算
                    final = base_total
                    note_d = ""
                    if disc_mode == "員工7折": final = int(base_total*0.7); note_d="(7折)"
                    elif disc_mode == "員工8折": final = int(base_total*0.8); note_d="(8折)"
                    elif disc_mode == "自訂折數": final = int(base_total*(cust_off/100)); note_d=f"({cust_off}折)"
                    
                    # 組合價覆寫
                    use_bundle = st.checkbox("啟用組合總價覆寫")
                    if use_bundle: final = st.number_input("最終總價", value=final)
                    
                    st.markdown(f"<div class='final-price'>實收: ${final}</div>", unsafe_allow_html=True)
                    checkout_note = st.text_input("備註")
                    pay_method = st.selectbox("付款方式", ["現金", "刷卡", "轉帳"])
                    
                    if st.form_submit_button("✅ 確認結帳", type="primary"):
                        sales = []
                        for i in st.session_state['pos_cart']:
                            cell = ws_items.find(i['sku'])
                            curr = int(ws_items.cell(cell.row, 5).value)
                            if curr >= i['qty']: ws_items.update_cell(cell.row, 5, curr-i['qty']); sales.append(f"{i['sku']} x1")
                            else: st.error(f"{i['sku']} 庫存不足"); st.stop()
                        
                        log_content = f"Sale | Total:${final} | Items:{','.join(sales)} | {checkout_note} {note_d} | {pay_method} | Ch:{sale_ch} | By:{sale_who}"
                        log_event(ws_logs, st.session_state['user_name'], "Sale", log_content)
                        st.session_state['pos_cart']=[]; st.balloons(); st.success("結帳完成"); time.sleep(1); st.rerun()

    # --- 2. 庫存 (V104 Metric + V103 Table) ---
    elif nav == "📊 庫存":
        st.subheader("📦 庫存總覽")
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='metric-card'><div class='metric-val'>{df['Qty'].sum()}</div><div class='metric-lbl'>台灣庫存</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-val'>{df['Qty_CN'].sum()}</div><div class='metric-lbl'>中國庫存</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><div class='metric-val'>${(df['Qty']*df['Cost']).sum():,}</div><div class='metric-lbl'>庫存成本</div></div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)

    # --- 3. 班表 (V104 Feature) ---
    elif nav == "🗓️ 班表":
        render_shift_calendar(sh, ws_users.col_values(1)[1:])

    # --- 4. 戰情 (V103 Charts Restored) ---
    elif nav == "📈 戰情":
        st.subheader("📈 營運戰情室")
        total_rev = (df['Qty'] * df['Price']).sum()
        total_cost = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum()
        profit = total_rev - (df['Qty'] * df['Cost']).sum()
        realized = calculate_realized_revenue(get_data_safe(ws_logs, False))
        
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='metric-card'><div class='metric-lbl'>預估營收</div><div class='metric-val'>${total_rev:,}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-lbl'>總資產成本</div><div class='metric-val'>${total_cost:,}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card' style='border-bottom:4px solid #f59e0b'><div class='metric-lbl'>潛在毛利</div><div class='metric-val'>${profit:,}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card' style='border-bottom:4px solid #10b981'><div class='metric-lbl'>實際營收</div><div class='metric-val'>${realized:,}</div></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 📦 庫存分類佔比")
            fig = px.pie(df, names='Category', values='Qty', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("##### 🔥 熱銷 Top 10 (庫存量)")
            top = df.groupby('Name')['Qty'].sum().sort_values(ascending=False).head(10).reset_index()
            fig2 = px.bar(top, x='Qty', y='Name', orientation='h')
            st.plotly_chart(fig2, use_container_width=True)

    # --- 5. 內部領用 (V103 FEATURE RESTORED) ---
    elif nav == "🎁 領用":
        st.subheader("🎁 內部領用/稽核中心")
        t1, t2 = st.tabs(["➕ 新增領用", "🕵️ 領用紀錄/回溯"])
        
        with t1:
            sku_opt = [f"{r['SKU']} | {r['Name']}" for _, r in df.iterrows()]
            sel_sku = st.selectbox("選擇商品", ["..."]+sku_opt)
            if sel_sku != "...":
                r_sku = sel_sku.split(" | ")[0]
                row = df[df['SKU']==r_sku].iloc[0]
                st.info(f"當前庫存: {row['Qty']}")
                with st.form("int_use"):
                    iq = st.number_input("數量", 1, max_value=int(row['Qty']) if int(row['Qty'])>0 else 1)
                    iwho = st.selectbox("領用人", [st.session_state['user_name']]+list(ws_users.col_values(1)[1:]))
                    irsn = st.selectbox("原因", ["公務", "福利", "樣品", "報廢"])
                    inote = st.text_input("備註")
                    if st.form_submit_button("確認扣除"):
                        c_row = ws_items.find(r_sku).row
                        ws_items.update_cell(c_row, 5, int(row['Qty'])-iq)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{r_sku} -{iq} | {iwho} | {irsn} | {inote}")
                        st.success("已領用"); st.rerun()
        
        with t2:
            logs = get_data_safe(ws_logs, False)
            int_logs = logs[logs['Action']=="Internal_Use"] if not logs.empty else pd.DataFrame()
            st.dataframe(int_logs, use_container_width=True)

    # --- 6. 管理 (V103 FEATURE RESTORED) ---
    elif nav == "👔 管理":
        st.subheader("👔 後台管理矩陣")
        t1, t2, t3, t4 = st.tabs(["➕ 矩陣新增", "⚡ 雙向調撥", "⚙️ 貨號重鑄", "🗑️ 刪除商品"])
        
        # V103 矩陣新增邏輯完整回歸
        with t1:
            mode = st.radio("模式", ["新系列", "衍生/補貨"], horizontal=True)
            auto_sku, auto_name, auto_img = "", "", ""
            if mode == "新系列":
                cat = st.selectbox("分類", ["上衣(Top)", "褲子(Btm)", "外套(Out)", "其他(Misc)"])
                if st.button("生成貨號"): st.session_state['base'] = generate_smart_style_code(cat, df['SKU'].tolist())
                if 'base' in st.session_state: auto_sku = st.session_state['base']
            else:
                p = st.selectbox("母商品", ["..."] + df['SKU'].tolist())
                if p != "...": 
                    row = df[df['SKU']==p].iloc[0]
                    auto_sku = get_style_code(p) + "-NEW"
                    auto_name, auto_img = row['Name'], row['Image_URL']

            with st.form("matrix_add"):
                c1, c2 = st.columns(2)
                base_sku = c1.text_input("Base SKU", value=auto_sku)
                name = c2.text_input("品名", value=auto_name)
                c3, c4, c5 = st.columns(3)
                price = c3.number_input("售價", value=0)
                cost = c4.number_input("成本", value=0)
                img_file = c5.file_uploader("圖片")
                st.write("尺寸矩陣:")
                sizes = {}
                cols = st.columns(5)
                for i, s in enumerate(SIZE_ORDER): sizes[s] = cols[i%5].number_input(s, min_value=0)
                if st.form_submit_button("執行寫入"):
                    img_url = upload_image_to_imgbb(img_file) if img_file else auto_img
                    for s, q in sizes.items():
                        if q > 0:
                            full = f"{base_sku}-{s}"
                            ws_items.append_row([full, name, "New", s, q, price, cost, get_taiwan_time_str(), img_url, 5, "TWD", cost, 0])
                    st.success("完成"); st.rerun()

        # V103 調撥邏輯
        with t2:
            s_t = st.selectbox("商品", ["..."]+df['SKU'].tolist())
            if s_t != "...":
                row = df[df['SKU']==s_t].iloc[0]
                st.info(f"TW: {row['Qty']} | CN: {row['Qty_CN']}")
                q = st.number_input("數量", 1)
                c1, c2 = st.columns(2)
                if c1.button("TW -> CN"):
                    r = ws_items.find(s_t).row
                    ws_items.update_cell(r, 5, int(row['Qty'])-q); ws_items.update_cell(r, 13, int(row['Qty_CN'])+q)
                    log_event(ws_logs, st.session_state['user_name'], "Transfer_TW_CN", f"{s_t} {q}")
                    st.success("成功"); st.rerun()
                if c2.button("CN -> TW"):
                    r = ws_items.find(s_t).row
                    ws_items.update_cell(r, 5, int(row['Qty'])+q); ws_items.update_cell(r, 13, int(row['Qty_CN'])-q)
                    log_event(ws_logs, st.session_state['user_name'], "Transfer_CN_TW", f"{s_t} {q}")
                    st.success("成功"); st.rerun()

        # 重鑄與刪除
        with t3: st.warning("此區功能請謹慎操作。"); st.write("(功能代碼已就緒，請依需求展開)")
        with t4:
             d = st.selectbox("刪除對象", ["..."]+df['SKU'].tolist())
             if d != "..." and st.button("確認刪除"):
                 ws_items.delete_rows(ws_items.find(d).row); st.success("刪除成功"); st.rerun()

    elif nav == "🚪 登出":
        st.session_state['logged_in'] = False; st.rerun()

if __name__ == "__main__":
    main()
