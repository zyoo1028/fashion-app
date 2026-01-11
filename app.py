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
    page_title="IFUKUK V106.0 SAFE", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🛑 【視覺層 (V104 Skin)】
# ==========================================
st.markdown("""
    <style>
        .stApp { background-color: #F8F9FA !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
        
        /* 導航列優化 */
        div[data-testid="stRadio"] > label { display:none; }
        div[data-testid="stRadio"] > div { flex-direction: row; gap: 20px; justify-content: center; background: #fff; padding: 10px; border-radius: 12px; border: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        
        /* 卡片與容器 */
        .product-card { border: 1px solid #eee; border-radius: 12px; overflow: hidden; background: #fff; display: flex; flex-direction: column; height: 100%; transition: transform 0.1s; }
        .product-card:active { transform: scale(0.98); }
        .prod-img-box { width: 100%; height: 120px; object-fit: cover; background: #f0f0f0; }
        .prod-info { padding: 8px; flex-grow: 1; }
        .prod-title { font-weight: bold; font-size: 0.9rem; line-height: 1.2; margin-bottom: 4px; color: #111; }
        .prod-price { font-weight: 900; color: #059669; font-size: 1rem; margin-top: auto; }
        
        /* 購物車區塊 (V103 邏輯 + V104 樣式) */
        .cart-container { background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .cart-item { display: flex; justify-content: space-between; border-bottom: 1px dashed #eee; padding: 8px 0; font-size: 0.9rem; }
        .final-price-box { font-size: 1.8rem; font-weight: 900; color: #16a34a; text-align: center; background: #dcfce7; padding: 15px; border-radius: 8px; margin-top: 15px; border: 2px solid #86efac; }
        
        /* 戰情看板 (V103 復刻) */
        .metric-card { background: #fff; border-radius: 12px; padding: 15px; border: 1px solid #eee; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 100%; }
        .metric-val { font-size: 1.5rem; font-weight: 800; color:#111; margin: 5px 0; }
        .metric-lbl { font-size: 0.8rem; color:#666; font-weight: 600; text-transform: uppercase;}
        
        /* 按鈕與輸入 */
        .stButton>button { border-radius: 12px; height: 3rem; font-weight: 700; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 100%; }
        .shift-badge { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; color: white; font-weight: bold; }
        
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- 核心連線模組 (V104.3 穩定版) ---
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
        seen = {}; new_headers = []
        for h in headers:
            if h in seen: seen[h] += 1; new_headers.append(f"{h}_{seen[h]}")
            else: seen[h] = 0; new_headers.append(h)
        rows = raw_data[1:]
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

# --- V103 邏輯工具 ---
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
def calculate_realized_revenue(logs_df):
    total = 0
    if logs_df.empty: return 0
    sales = logs_df[logs_df['Action'] == 'Sale']
    for _, row in sales.iterrows():
        try: total += int(re.search(r'Total:\$(\d+)', row['Details']).group(1))
        except: pass
    return total

# --- 班表渲染 (V104 Module) ---
def get_staff_color(name):
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6366F1"]
    return colors[sum(ord(c) for c in str(name)) % len(colors)]

def render_shift_calendar(sh, users_list):
    ws_shifts = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Shift_Type", "Note", "Updated_By"])
    shifts_df = get_data_safe(ws_shifts, False)
    st.subheader("🗓️ 排班戰情室")
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
                    note_dot = "🔴" if any(len(str(r['Note'])) > 0 for _, r in day_shifts.iterrows()) else ""
                    if st.button(f"{day} {note_dot}", key=f"d_{date_str}", use_container_width=True): st.session_state['selected_date'] = date_str; st.rerun()
                    st.markdown(f"<div style='margin-top:-30px;pointer-events:none;padding:2px;'>{badges}</div>", unsafe_allow_html=True)
                else: st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True)
    if 'selected_date' in st.session_state:
        target_date = st.session_state['selected_date']
        with st.expander(f"📝 編輯：{target_date}", expanded=True):
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
    
    sh = init_db()
    if not sh: return
    
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])
    
    # 登入介面 (V104 Style, V103 Logic)
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><h1 style='text-align:center'>IFUKUK</h1><p style='text-align:center'>OMEGA V106.0 SAFE</p>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("ID"); p = st.text_input("PASSWORD", type="password")
                if st.form_submit_button("ENTER SYSTEM", type="primary"):
                    with st.spinner("Verifying..."):
                        udf = get_data_safe(ws_users, False)
                        if udf.empty and u=="Boss" and p=="1234": ws_users.append_row(["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()]); st.rerun()
                        tgt = udf[(udf['Name']==u) & (udf['Status']=='Active')]
                        if not tgt.empty:
                            stored = tgt.iloc[0]['Password']
                            if (len(stored)==64 and check_hash(p, stored)) or (p==stored):
                                st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=tgt.iloc[0]['Role']; st.rerun()
                        st.error("❌ 登入失敗")
        return

    # 登入後讀取資料
    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    
    # 頂部資訊
    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:15px;background:#fff;border-bottom:1px solid #eee;align-items:center;'><div><b>IFUKUK</b> | {st.session_state['user_name']}</div><div style='color:#666;font-size:0.8rem;'>V106.0</div></div>", unsafe_allow_html=True)
    
    df = get_data_safe(ws_items, True)
    for c in ["Qty","Price","Qty_CN","Cost","Orig_Cost","Safety_Stock"]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    
    # 導航 (Radio Button Navigation)
    nav_container = st.container()
    with nav_container:
        nav = st.radio("", ["🛒 POS", "📊 庫存", "🗓️ 班表", "📈 戰情", "🎁 領用", "👔 管理", "🚪 登出"], horizontal=True)

    # --- 1. POS (V104 圖庫 + V103 運算) ---
    if nav == "🛒 POS":
        c_l, c_r = st.columns([3, 2])
        
        # 左側：圖庫選擇 (V104 Style)
        with c_l:
            st.markdown("##### 🛍️ 商品畫廊")
            cats = ["全部"] + list(df['Category'].unique()) if not df.empty else []
            col_search, col_cat = st.columns([2, 1])
            q = col_search.text_input("🔍", placeholder="搜尋...", label_visibility="collapsed")
            cat = col_cat.selectbox("分類", cats, label_visibility="collapsed")
            
            vdf = df.copy()
            if cat != "全部": vdf = vdf[vdf['Category'] == cat]
            if q: vdf = vdf[vdf.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
            
            if not vdf.empty:
                rows = [vdf.iloc[i:i+3] for i in range(0, len(vdf), 3)]
                for r in rows:
                    cols = st.columns(3)
                    for i, (_, item) in enumerate(r.iterrows()):
                        with cols[i]:
                            # 卡片點擊加入 (使用 V103 的資料邏輯)
                            st.markdown(f"<div class='product-card'><div class='prod-img-box'><img src='{render_image_url(item['Image_URL'])}' style='width:100%;height:100%;object-fit:cover;'></div><div class='prod-info'><div class='prod-title'>{item['Name']}</div><div style='font-size:0.75rem;color:#666;'>{item['SKU']} | {item['Size']}</div><div class='prod-price'>${item['Price']}</div><div style='font-size:0.7rem;color:#1d4ed8;'>TW:{item['Qty']}</div></div></div>", unsafe_allow_html=True)
                            if st.button("➕", key=f"add_{item['SKU']}", use_container_width=True):
                                st.session_state['pos_cart'].append({"sku":item['SKU'],"name":item['Name'],"size":item['Size'],"price":item['Price'],"qty":1,"subtotal":item['Price']})
                                st.toast(f"已加入 {item['Name']}")
        
        # 右側：購物車 (V103 Logic Fix - 移除 form 讓更新即時生效)
        with c_r:
            st.markdown("##### 🧾 購物車")
            with st.container():
                st.markdown("<div class='cart-container'>", unsafe_allow_html=True)
                if st.session_state['pos_cart']:
                    # 1. 顯示商品與清空
                    base_total = sum(i['subtotal'] for i in st.session_state['pos_cart'])
                    for i in st.session_state['pos_cart']: 
                        st.markdown(f"<div class='cart-item'><span>{i['name']} ({i['size']})</span><b>${i['subtotal']}</b></div>", unsafe_allow_html=True)
                    
                    if st.button("🗑️ 清空", use_container_width=True): st.session_state['pos_cart']=[]; st.rerun()
                    
                    st.markdown("---")
                    
                    # 2. 即時計算區 (OUTSIDE FORM to fix bug)
                    col_d1, col_d2 = st.columns(2)
                    disc_mode = col_d1.radio("折扣", ["無", "員工7折", "員工8折", "自訂"], horizontal=True, key="disc_radio")
                    cust_off = col_d2.number_input("折數%", 1, 100, 95) if disc_mode=="自訂" else 0
                    
                    use_bundle = st.checkbox("啟用組合價 (Bundle)")
                    bundle_price = 0
                    if use_bundle:
                        bundle_price = st.number_input("組合總價", value=base_total)
                    
                    # 核心價格計算
                    final_price = base_total
                    note_str = ""
                    
                    if use_bundle:
                        final_price = bundle_price
                        note_str = "(組合價)"
                    else:
                        if disc_mode == "員工7折": final_price = int(round(base_total * 0.7)); note_str="(7折)"
                        elif disc_mode == "員工8折": final_price = int(round(base_total * 0.8)); note_str="(8折)"
                        elif disc_mode == "自訂": final_price = int(round(base_total * (cust_off/100))); note_str=f"({cust_off}折)"
                    
                    st.markdown(f"<div class='final-price-box'>${final_price}</div>", unsafe_allow_html=True)
                    
                    # 3. 結帳送出 (Inside Form is OK for submit only)
                    st.markdown("<br>", unsafe_allow_html=True)
                    sale_who = st.selectbox("經手人", [st.session_state['user_name']] + list(ws_users.col_values(1)[1:]))
                    sale_ch = st.selectbox("通路", ["門市", "官網", "直播", "其他"])
                    pay_method = st.selectbox("付款", ["現金", "刷卡", "轉帳"])
                    checkout_note = st.text_input("結帳備註")
                    
                    if st.button("✅ 確認結帳 (Checkout)", type="primary", use_container_width=True):
                        # 執行扣庫存
                        sales_log_items = []
                        valid = True
                        for i in st.session_state['pos_cart']:
                            cell = ws_items.find(i['sku'])
                            if not cell: st.error(f"找不到 {i['sku']}"); valid=False; break
                            curr_q = int(ws_items.cell(cell.row, 5).value)
                            if curr_q < i['qty']: st.error(f"{i['name']} 庫存不足 (剩 {curr_q})"); valid=False; break
                            # 更新
                            ws_items.update_cell(cell.row, 5, curr_q - i['qty'])
                            sales_log_items.append(f"{i['sku']} x1")
                        
                        if valid:
                            full_log = f"Sale | Total:${final_price} | Items:{','.join(sales_log_items)} | {checkout_note} {note_str} | {pay_method} | Ch:{sale_ch} | By:{sale_who}"
                            log_event(ws_logs, st.session_state['user_name'], "Sale", full_log)
                            st.session_state['pos_cart'] = []
                            st.balloons()
                            st.success(f"結帳成功！實收 ${final_price}")
                            time.sleep(2); st.rerun()
                else:
                    st.info("購物車是空的")
                st.markdown("</div>", unsafe_allow_html=True)

    # --- 2. 庫存 (V103 獨立分頁 - 表格模式) ---
    elif nav == "📊 庫存":
        st.subheader("📦 庫存總覽 (Inventory)")
        # 恢復 V103 的表格顯示，乾淨清楚
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("台灣總庫存", df['Qty'].sum())
        col_m2.metric("中國總庫存", df['Qty_CN'].sum())
        col_m3.metric("總品項數", len(df))
        
        st.dataframe(df, use_container_width=True)

    # --- 3. 班表 (V104 新功能 - 獨立分頁) ---
    elif nav == "🗓️ 班表":
        render_shift_calendar(sh, ws_users.col_values(1)[1:])

    # --- 4. 戰情 (V103 邏輯復刻) ---
    elif nav == "📈 戰情":
        st.subheader("📈 營運戰情室")
        # V103 的計算邏輯：包含原幣成本
        total_rev = (df['Qty'] * df['Price']).sum()
        total_cost_twd = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum()
        
        # RMB 原幣計算 (V103 Logic)
        rmb_cost = 0
        if 'Orig_Currency' in df.columns:
            rmb_df = df[df['Orig_Currency'] == 'CNY']
            if not rmb_df.empty:
                rmb_cost = ((rmb_df['Qty'] + rmb_df['Qty_CN']) * rmb_df['Orig_Cost']).sum()
        
        profit = total_rev - (df['Qty'] * df['Cost']).sum()
        realized = calculate_realized_revenue(get_data_safe(ws_logs, False))

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='metric-card'><div class='metric-lbl'>預估營收</div><div class='metric-val'>${total_rev:,}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-lbl'>總資產成本 (TWD)</div><div class='metric-val'>${total_cost_twd:,}</div><div style='font-size:0.8rem;color:#666;'>RMB原幣: ¥{rmb_cost:,}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><div class='metric-lbl'>潛在毛利</div><div class='metric-val' style='color:#f59e0b'>${profit:,}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card'><div class='metric-lbl'>實際營收</div><div class='metric-val' style='color:#10b981'>${realized:,}</div></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.caption("庫存分佈")
            fig = px.pie(df, names='Category', values='Qty', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.caption("Top 10")
            top = df.groupby('Name')['Qty'].sum().sort_values(ascending=False).head(10).reset_index()
            fig2 = px.bar(top, x='Qty', y='Name', orientation='h')
            st.plotly_chart(fig2, use_container_width=True)

    # --- 5. 領用 (V103 回歸) ---
    elif nav == "🎁 領用":
        st.subheader("🎁 內部領用")
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

    # --- 6. 管理 (V103 回歸) ---
    elif nav == "👔 管理":
        st.subheader("👔 後台管理")
        t1, t2 = st.tabs(["雙向調撥 (TW/CN)", "刪除商品"])
        with t1:
            s_t = st.selectbox("調撥商品", ["..."]+df['SKU'].tolist())
            if s_t != "...":
                row = df[df['SKU']==s_t].iloc[0]
                st.write(f"TW: {row['Qty']} | CN: {row['Qty_CN']}")
                q = st.number_input("數量", 1)
                c1, c2 = st.columns(2)
                if c1.button("TW -> CN"):
                    r = ws_items.find(s_t).row
                    ws_items.update_cell(r, 5, int(row['Qty'])-q); ws_items.update_cell(r, 13, int(row['Qty_CN'])+q)
                    st.success("OK"); st.rerun()
                if c2.button("CN -> TW"):
                    r = ws_items.find(s_t).row
                    ws_items.update_cell(r, 5, int(row['Qty'])+q); ws_items.update_cell(r, 13, int(row['Qty_CN'])-q)
                    st.success("OK"); st.rerun()
        with t2:
             d = st.selectbox("刪除", ["..."]+df['SKU'].tolist())
             if d != "..." and st.button("確認刪除"):
                 ws_items.delete_rows(ws_items.find(d).row); st.success("已刪除"); st.rerun()

    elif nav == "🚪 登出":
        st.session_state['logged_in'] = False; st.rerun()

if __name__ == "__main__":
    main()
