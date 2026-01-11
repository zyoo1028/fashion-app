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
    page_title="IFUKUK V104.4 Fusion", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🛑 【OMEGA V104.4 視覺核心】
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
        
        /* 按鈕與輸入優化 */
        .stButton>button { border-radius: 12px; height: 3.5rem; font-weight: 700; border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; }
        div[data-baseweb="select"] > div { border-radius: 12px !important; min-height: 3rem; }
        
        /* 戰情儀表板 (V103 復刻樣式) */
        .metric-card { background: linear-gradient(145deg, #ffffff, #f5f7fa); border-radius: 16px; padding: 15px; border: 1px solid #e1e4e8; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.02); margin-bottom: 10px; height: 100%; }
        .metric-value { font-size: 1.5rem; font-weight: 800; margin: 5px 0; color:#111 !important; }
        .metric-label { font-size: 0.8rem; letter-spacing: 1px; color:#666 !important; font-weight: 600; text-transform: uppercase;}
        .profit-card { border-bottom: 4px solid #f59e0b; }
        .realized-card { border-bottom: 4px solid #10b981; }

        /* 排班表樣式 */
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

# --- 核心邏輯 (V103 + V104.3 Fix) ---
@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

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
    except: return pd.DataFrame()

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
    except: return None

# --- 工具模組 (V103 + V104) ---
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

# --- 班表渲染 (V104) ---
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
                     # 簡易刪除
                     all_v = ws_shifts.get_all_values()
                     for idx, v in enumerate(all_v):
                         if len(v)>1 and v[0]==target_date and v[1]==r['Staff']: ws_shifts.delete_rows(idx+1); break
                     st.rerun()

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False; st.session_state['user_name'] = ""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []
    if 'exchange_rate' not in st.session_state: st.session_state['exchange_rate'] = 4.5
    
    sh = init_db()
    if not sh: st.error("❌ 連線失敗"); st.stop()
    
    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    # 登入頁面
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><h1 style='text-align:center'>IFUKUK</h1><p style='text-align:center'>OMEGA V104.4 (Grand Fusion)</p>", unsafe_allow_html=True)
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

    # 導航
    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:10px;border-bottom:1px solid #eee;'><b>IFUKUK | {st.session_state['user_name']}</b><span>V104.4</span></div>", unsafe_allow_html=True)
    
    df = get_data_safe(ws_items, True)
    for c in ["Qty","Price","Qty_CN","Cost","Orig_Cost","Safety_Stock"]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    
    # 導航列 (V104 樣式)
    nav = st.radio("", ["🛒 POS", "📊 庫存", "🗓️ 班表", "📈 戰情", "🛠️ 管理", "🚪 登出"], horizontal=True, label_visibility="collapsed")
    
    # --- 1. POS (V104 畫廊) ---
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
            st.markdown("#### 🧾 購物車")
            if st.session_state['pos_cart']:
                total = sum(i['subtotal'] for i in st.session_state['pos_cart'])
                for i in st.session_state['pos_cart']: st.markdown(f"<div style='border-bottom:1px dashed #ddd;padding:5px;display:flex;justify-content:space-between'><span>{i['name']} ({i['size']})</span><b>${i['subtotal']}</b></div>", unsafe_allow_html=True)
                st.markdown(f"<h2 style='text-align:right'>${total}</h2>", unsafe_allow_html=True)
                if st.button("🗑️ 清空"): st.session_state['pos_cart']=[]; st.rerun()
                if st.button("✅ 結帳", type="primary"):
                    sales = []
                    for i in st.session_state['pos_cart']:
                        cell = ws_items.find(i['sku'])
                        curr = int(ws_items.cell(cell.row, 5).value)
                        if curr >= i['qty']: ws_items.update_cell(cell.row, 5, curr-i['qty']); sales.append(f"{i['sku']} x1")
                    log_event(ws_logs, st.session_state['user_name'], "Sale", f"Total:${total} | {','.join(sales)}")
                    st.session_state['pos_cart']=[]; st.balloons(); st.success("完成"); time.sleep(1); st.rerun()

    # --- 2. 庫存 (V104 卡片 + V103 表格) ---
    elif nav == "📊 庫存":
        st.subheader("📦 庫存總覽")
        m1, m2, m3 = st.columns(3)
        m1.metric("台灣總庫存", df['Qty'].sum())
        m2.metric("中國總庫存", df['Qty_CN'].sum())
        m3.metric("庫存總成本", f"${(df['Qty']*df['Cost']).sum()+(df['Qty_CN']*df['Cost']).sum():,}")
        
        with st.expander("📄 詳細庫存表 (V103 經典模式)", expanded=True):
            st.dataframe(df, use_container_width=True)

    # --- 3. 班表 (V104) ---
    elif nav == "🗓️ 班表":
        render_shift_calendar(sh, ws_users.col_values(1)[1:])

    # --- 4. 戰情 (V103 完整復刻) ---
    elif nav == "📈 戰情":
        st.subheader("📈 營運戰情室 (V103 Full Dashboard)")
        # 數據計算
        total_rev = (df['Qty'] * df['Price']).sum()
        total_cost = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum()
        profit = total_rev - (df['Qty'] * df['Cost']).sum()
        realized = calculate_realized_revenue(get_data_safe(ws_logs, False))
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.markdown(f"<div class='metric-card'><div class='metric-label'>預估營收</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-label'>總資產成本</div><div class='metric-value'>${total_cost:,}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card profit-card'><div class='metric-label'>潛在毛利</div><div class='metric-value'>${profit:,}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card realized-card'><div class='metric-label'>實際營收 (已售)</div><div class='metric-value'>${realized:,}</div></div>", unsafe_allow_html=True)
        m5.markdown(f"<div class='metric-card'><div class='metric-label'>庫存總量</div><div class='metric-value'>{df['Qty'].sum()+df['Qty_CN'].sum():,}</div></div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption("庫存分類佔比")
            fig = px.pie(df, names='Category', values='Qty', hole=0.5)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.caption("Top 10 重點商品")
            top = df.groupby('Name')['Qty'].sum().sort_values(ascending=False).head(10).reset_index()
            fig2 = px.bar(top, x='Qty', y='Name', orientation='h')
            st.plotly_chart(fig2, use_container_width=True)
            
    # --- 5. 管理 (V103 矩陣管理 + 匯率設定) ---
    elif nav == "🛠️ 管理":
        st.subheader("🛠️ 後台管理中心")
        t1, t2, t3, t4 = st.tabs(["➕ 矩陣新增 (Matrix)", "⚡ 雙向調撥", "⚙️ 匯率/重鑄", "🗑️ 刪除"])
        
        # Tab 1: 矩陣新增 (V103 Logic)
        with t1:
            st.info("💡 這裡是 V103 的矩陣新增功能，已完整恢復。")
            mode = st.radio("模式", ["新系列", "衍生/補貨"], horizontal=True)
            auto_sku, auto_name, auto_img = "", "", ""
            
            if mode == "新系列":
                cat = st.selectbox("分類", ["上衣(Top)", "褲子(Btm)", "外套(Out)", "其他(Misc)"])
                if st.button("生成貨號"): st.session_state['base'] = generate_smart_style_code(cat, df['SKU'].tolist())
                if 'base' in st.session_state: auto_sku = st.session_state['base']
            else:
                p = st.selectbox("選擇母商品", ["..."] + df['SKU'].tolist())
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
                
                st.write("尺寸數量矩陣:")
                sizes = {}
                cols = st.columns(5)
                for i, s in enumerate(SIZE_ORDER): sizes[s] = cols[i%5].number_input(s, min_value=0)
                
                if st.form_submit_button("🚀 執行寫入"):
                    img_url = upload_image_to_imgbb(img_file) if img_file else auto_img
                    for s, q in sizes.items():
                        if q > 0:
                            full_sku = f"{base_sku}-{s}"
                            ws_items.append_row([full_sku, name, "New", s, q, price, cost, get_taiwan_time_str(), img_url, 5, "TWD", cost, 0])
                    st.success("新增完成"); st.rerun()

        # Tab 2: 調撥
        with t2:
            st.write("雙向調撥樞紐")
            sku = st.selectbox("選擇商品", ["..."] + df['SKU'].tolist())
            if sku != "...":
                row = df[df['SKU']==sku].iloc[0]
                st.write(f"TW: {row['Qty']} | CN: {row['Qty_CN']}")
                c1, c2 = st.columns(2)
                q = c1.number_input("數量", 1)
                if c2.button("TW -> CN"):
                    r = ws_items.find(sku).row
                    ws_items.update_cell(r, 5, int(row['Qty'])-q); ws_items.update_cell(r, 13, int(row['Qty_CN'])+q)
                    st.success("調撥完成"); st.rerun()

        # Tab 3: 匯率與重鑄
        with t3:
            st.write("匯率設定")
            st.session_state['exchange_rate'] = st.number_input("RMB 匯率", value=st.session_state['exchange_rate'])
            st.write("---")
            st.write("貨號重鑄 (Refactor) - 此功能風險較高，請謹慎使用")

        # Tab 4: 刪除
        with t4:
            d_sku = st.selectbox("刪除商品", ["..."] + df['SKU'].tolist())
            if d_sku != "..." and st.button("確認刪除"):
                cell = ws_items.find(d_sku)
                ws_items.delete_rows(cell.row)
                st.success("已刪除"); st.rerun()

    elif nav == "🚪 登出":
        st.session_state['logged_in'] = False; st.rerun()

if __name__ == "__main__":
    main()
