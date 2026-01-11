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

# --- 1. 系統全域設定 (回到 V103 側邊欄佈局) ---
st.set_page_config(
    page_title="IFUKUK V103.1 RESTORED", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 V103.1 原始樣式 (無花俏 CSS)
# ==========================================
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF !important; }
        .metric-card { 
            background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 10px; 
            padding: 15px; text-align: center; margin-bottom: 10px;
        }
        .metric-value { font-size: 1.8rem; font-weight: bold; color: #333; }
        .metric-label { font-size: 0.9rem; color: #666; }
        
        .stock-pill-tw { background-color: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 4px; font-weight: bold; margin-right: 5px; font-size: 0.8rem; }
        .stock-pill-cn { background-color: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
        
        .cart-box { background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px; margin-bottom: 15px; }
        .cart-item { display: flex; justify-content: space-between; border-bottom: 1px dashed #cbd5e1; padding: 8px 0; }
        .final-price-display { font-size: 1.8rem; font-weight: 900; color: #16a34a; text-align: center; background: #dcfce7; padding: 10px; border-radius: 8px; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# 全域常數
CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]
SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]

# --- 核心連線 (保留 V104 的強力防斷線，但用於 V103 架構) ---
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

# [強力讀取] 解決 "系統無資料"
def get_data_safe(ws):
    max_retries = 3
    for i in range(max_retries):
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
            
            # V103 自動修復欄位
            if "Qty_CN" not in new_headers:
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
        except Exception: time.sleep(1); continue
    return pd.DataFrame()

# [強力寫入] 解決 Quota Exceeded
def update_cell_retry(ws, row, col, value, retries=3):
    for i in range(retries):
        try: ws.update_cell(row, col, value); return True
        except: time.sleep(1 + i); continue
    return False

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
    try: ws_logs.append_row([get_taiwan_time_str(), user, action, detail])
    except: pass
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

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False; st.session_state['user_name'] = ""
    if 'exchange_rate' not in st.session_state:
        live_rate, is_success = get_live_rate()
        st.session_state['exchange_rate'] = live_rate
        st.session_state['rate_source'] = "Live API" if is_success else "Manual/Default"
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart'] = []

    sh = init_db()
    if not sh: st.error("Database Connection Failed"); st.stop()

    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    # 登入頁面
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><h1 style='text-align:center'>IFUKUK</h1><p style='text-align:center'>MATRIX ERP V103.1 (RESTORED)</p>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("帳號 (ID)")
                p = st.text_input("密碼 (Password)", type="password")
                if st.form_submit_button("登入 (LOGIN)", type="primary"):
                    users_df = get_data_safe(ws_users)
                    if users_df.empty and u == "Boss" and p == "1234":
                        ws_users.append_row(["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                        st.success("Boss Created"); time.sleep(1); st.rerun()
                    if not users_df.empty:
                        target = users_df[(users_df['Name'] == u) & (users_df['Status'] == 'Active')]
                        if not target.empty:
                            stored = target.iloc[0]['Password']
                            if (len(stored)==64 and check_hash(p, stored)) or (p == stored):
                                st.session_state['logged_in'] = True; st.session_state['user_name'] = u; st.session_state['user_role'] = target.iloc[0]['Role']; st.rerun()
                            else: st.error("密碼錯誤")
                        else: st.error("帳號無效")
                    else: st.error("系統讀取失敗，請重試 (System No Data)")
        return

    # 主畫面
    df = get_data_safe(ws_items)
    for c in ["Qty","Price","Cost","Safety_Stock","Orig_Cost","Qty_CN"]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    
    # 側邊欄 (V103 Original)
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        st.caption(f"Role: {st.session_state['user_role']}")
        st.markdown("---")
        with st.expander("💱 匯率設定", expanded=True):
            st.caption(f"Source: {st.session_state.get('rate_source', 'Manual')}")
            curr_rate = st.session_state['exchange_rate']
            new_r = st.number_input("RMB -> TWD", value=curr_rate, step=0.01)
            if new_r != curr_rate: st.session_state['exchange_rate'] = new_r
            if st.button("🔄 更新匯率"): 
                l_rate, succ = get_live_rate()
                st.session_state['exchange_rate'] = l_rate; st.rerun()
        st.markdown("---")
        if st.button("🚪 登出"): st.session_state['logged_in'] = False; st.rerun()

    tabs = st.tabs(["📊 視覺庫存", "🛒 POS", "📈 戰情", "🎁 領用", "👔 矩陣管理", "📝 日誌", "👥 Admin"])

    # Tab 1: 視覺庫存 (V103 Logic)
    with tabs[0]:
        c1, c2 = st.columns([2, 1])
        q = c1.text_input("搜尋商品", placeholder="輸入貨號...")
        cat = c2.selectbox("分類篩選", ["全部"] + CAT_LIST)
        
        vdf = df.copy()
        if q: vdf = vdf[vdf.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
        if cat != "全部": vdf = vdf[vdf['Category'] == cat]
        
        if not vdf.empty:
            grp = vdf.groupby(['SKU', 'Name']).first().reset_index() # 簡單顯示
            st.dataframe(vdf, use_container_width=True)
        else: st.info("無資料")

    # Tab 2: POS (V103 Dropdown Style)
    with tabs[1]:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("1. 選擇商品")
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']} ({x['Size']}) | T:{x['Qty']}", axis=1).tolist() if not df.empty else []
            sel = st.selectbox("搜尋 (下拉選單)", ["..."] + opts)
            
            if sel != "...":
                sku = sel.split(" | ")[0]
                row = df[df['SKU'] == sku].iloc[0]
                st.image(render_image_url(row['Image_URL']), width=150)
                st.markdown(f"**{row['Name']}** | ${row['Price']}")
                qty = st.number_input("數量", 1, value=1)
                if st.button("➕ 加入購物車", type="primary"):
                    st.session_state['pos_cart'].append({
                        "sku": sku, "name": row['Name'], "size": row['Size'], 
                        "price": int(row['Price']), "qty": qty, "subtotal": int(row['Price'])*qty
                    })
                    st.success("已加入")

        with c2:
            st.subheader("2. 結帳")
            if st.session_state['pos_cart']:
                total = sum(i['subtotal'] for i in st.session_state['pos_cart'])
                for i in st.session_state['pos_cart']:
                    st.markdown(f"{i['name']} ({i['size']}) x{i['qty']} = ${i['subtotal']}")
                st.markdown("---")
                if st.button("清空"): st.session_state['pos_cart'] = []; st.rerun()
                
                # 結帳表單
                with st.form("checkout"):
                    disc = st.radio("折扣", ["無", "7折", "8折", "自訂"], horizontal=True)
                    cust = st.number_input("折數", 1, 100, 95)
                    bundle = st.checkbox("組合價")
                    b_val = st.number_input("組合金額", value=total)
                    
                    final = total
                    if bundle: final = b_val
                    elif disc == "7折": final = int(round(total*0.7))
                    elif disc == "8折": final = int(round(total*0.8))
                    elif disc == "自訂": final = int(round(total*(cust/100)))
                    
                    st.markdown(f"### 實收: ${final}")
                    who = st.selectbox("經手", [st.session_state['user_name']])
                    pay = st.selectbox("付款", ["現金", "刷卡"])
                    note = st.text_input("備註")
                    
                    if st.form_submit_button("確認結帳"):
                        logs = []
                        valid = True
                        for i in st.session_state['pos_cart']:
                            r = ws_items.find(i['sku']).row
                            curr = int(ws_items.cell(r, 5).value)
                            if curr >= i['qty']:
                                update_cell_retry(ws_items, r, 5, curr-i['qty'])
                                logs.append(f"{i['sku']} x{i['qty']}")
                            else: valid = False; st.error("庫存不足"); break
                        
                        if valid:
                            log_event(ws_logs, st.session_state['user_name'], "Sale", f"Total:${final} | {','.join(logs)} | {note}")
                            st.session_state['pos_cart'] = []
                            st.success("完成"); time.sleep(1); st.rerun()

    # Tab 3: 戰情 (V103 Logic - 包含雙幣顯示)
    with tabs[2]:
        rev = (df['Qty'] * df['Price']).sum()
        cost = ((df['Qty'] + df['Qty_CN']) * df['Cost']).sum()
        
        # RMB 計算 (Restored)
        rmb = 0
        if 'Orig_Currency' in df.columns:
            rmb_df = df[df['Orig_Currency'] == 'CNY']
            if not rmb_df.empty:
                rmb = ((rmb_df['Qty'] + rmb_df['Qty_CN']) * rmb_df['Orig_Cost']).sum()
        
        profit = rev - (df['Qty'] * df['Cost']).sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("預估營收", f"${rev:,}")
        m2.metric("總成本 (TWD)", f"${cost:,}", f"RMB: ¥{rmb:,}")
        m3.metric("潛在毛利", f"${profit:,}")
        m4.metric("總庫存", df['Qty'].sum() + df['Qty_CN'].sum())

    # Tab 4: 領用
    with tabs[3]:
        st.subheader("內部領用")
        with st.form("internal"):
            sel = st.selectbox("商品", ["..."] + (df['SKU'] + " | " + df['Name']).tolist())
            q = st.number_input("數量", 1)
            rsn = st.selectbox("原因", ["公務", "報廢", "其他"])
            if st.form_submit_button("執行"):
                if sel != "...":
                    sku = sel.split(" | ")[0]
                    r = ws_items.find(sku).row
                    curr = int(ws_items.cell(r, 5).value)
                    update_cell_retry(ws_items, r, 5, curr-q)
                    log_event(ws_logs, st.session_state['user_name'], "Internal", f"{sku} -{q} ({rsn})")
                    st.success("OK"); st.rerun()

    # Tab 5: 矩陣管理 (V103 完整版 - 包含原幣設定)
    with tabs[4]:
        st.subheader("矩陣新增 (Matrix)")
        mode = st.radio("模式", ["新系列", "衍生"], horizontal=True)
        a_sku, a_name = "", ""
        
        if mode == "新系列":
            c = st.selectbox("分類", CAT_LIST)
            if st.button("生成貨號"): st.session_state['base'] = generate_smart_style_code(c, df['SKU'].tolist())
            if 'base' in st.session_state: a_sku = st.session_state['base']
        else:
            p = st.selectbox("母商品", ["..."] + df['SKU'].tolist())
            if p != "...": 
                r = df[df['SKU']==p].iloc[0]
                a_sku = get_style_code(p) + "-NEW"; a_name = r['Name']

        with st.form("matrix_add"):
            c1, c2 = st.columns(2)
            bsku = c1.text_input("Base SKU", value=a_sku)
            name = c2.text_input("品名", value=a_name)
            
            # [RESTORED] V103 關鍵功能：原幣成本輸入
            c3, c4, c5 = st.columns(3)
            pr = c3.number_input("售價 (TWD)", 0)
            curr = c4.selectbox("成本幣別", ["TWD", "CNY"])
            cost_org = c5.number_input("原幣成本", 0)
            
            img = st.file_uploader("圖片")
            st.write("尺寸數量 (預設寫入台灣庫存):")
            sizes = {}
            cols = st.columns(5)
            for i, s in enumerate(SIZE_ORDER): sizes[s] = cols[i%5].number_input(s, min_value=0)
            
            if st.form_submit_button("寫入資料庫"):
                # 計算台幣成本
                final_cost = int(cost_org * st.session_state['exchange_rate']) if curr == "CNY" else cost_org
                url = upload_image_to_imgbb(img) if img else ""
                
                for s, q in sizes.items():
                    if q > 0:
                        full = f"{bsku}-{s}"
                        # 寫入完整欄位 (包含 Orig_Currency, Orig_Cost)
                        ws_items.append_row([
                            full, name, "New", s, q, pr, final_cost, get_taiwan_time_str(), 
                            url, 5, curr, cost_org, 0
                        ])
                st.success("新增完成"); st.rerun()

    # Tab 6 & 7
    with tabs[5]: 
        logs = get_data_safe(ws_logs)
        st.dataframe(logs, use_container_width=True)
    with tabs[6]:
        users = get_data_safe(ws_users)
        st.dataframe(users, use_container_width=True)

if __name__ == "__main__":
    main()
