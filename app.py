import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import requests
import plotly.express as px
import base64
import qrcode
from io import BytesIO
from PIL import Image

# --- 1. 系統全域設定 (美學版) ---
st.set_page_config(
    page_title="IFUKUK 核心戰情", 
    layout="wide", 
    page_icon="👑",
    initial_sidebar_state="expanded"
)

# --- ⚠️⚠️⚠️ 設定區 (請填入您的 4 把鑰匙) ⚠️⚠️⚠️ ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
LINE_CHANNEL_ACCESS_TOKEN = "IaGvcTOmbMFW8wKEJ5MamxfRx7QVo0kX1IyCqwKZw0WX2nxAVYY7SsSh5vAJ0r+WBNvyjjiU8G3eYkL1nozqIOjjWMOKr/4ZtzUMRRf7JNJkk5V6jLpWc/EOkzvNGVPMh0zwH+wQD51tR3XWipUULwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U55199b00fb78da85bb285db6d00b6ff5"
# ---------------------------------------------------

# --- 自定義 CSS (V14.0 時尚美學升級) ---
st.markdown("""
    <style>
    /* 全站字體與背景 */
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .brand-title {
        font-weight: 900;
        font-size: 3rem;
        color: #1a1a1a;
        text-align: center;
        letter-spacing: 3px;
        margin-bottom: 5px;
        text-transform: uppercase;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .brand-subtitle {
        text-align: center;
        color: #666;
        font-size: 1rem;
        letter-spacing: 1px;
        margin-bottom: 30px;
    }
    
    /* 數據卡片 */
    .metric-card {
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border-left: 5px solid #1a1a1a;
        transition: transform 0.2s;
        text-align: center;
        margin-bottom: 15px;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
    .metric-label {
        font-size: 0.9rem;
        color: #888;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        font-size: 1.8rem;
        color: #1a1a1a;
        font-weight: 700;
        margin: 10px 0;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #28a745;
        font-weight: 500;
    }
    
    /* 按鈕美化 */
    .stButton>button {
        width: 100%;
        border-radius: 50px;
        font-weight: 600;
        height: 3.2em;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 5px 15px rgba(0,0,0,0.15);
    }
    
    /* 商品卡片優化 */
    .product-card {
        background: white;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #eee;
        transition: all 0.2s;
    }
    .product-card img {
        border-radius: 10px;
        width: 100%;
        height: 150px;
        object-fit: cover;
    }
    
    /* Tabs 美化 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #fff;
        border-radius: 10px 10px 0 0;
        box-shadow: 0 -2px 5px rgba(0,0,0,0.02);
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1a1a1a;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線邏輯 ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=3600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def safe_api_call(func, *args, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            time.sleep(1)
    return None

@st.cache_resource(ttl=3600)
def init_db():
    client = get_connection()
    try:
        sh = client.open_by_url(GOOGLE_SHEET_URL)
        return sh
    except Exception as e:
        st.error(f"無法連結資料庫: {e}")
        return None

# --- 3. 工具模組 ---
def upload_image_to_imgbb(image_file):
    if not IMGBB_API_KEY or "請將您的" in IMGBB_API_KEY: return None
    try:
        img_bytes = image_file.getvalue()
        b64_string = base64.b64encode(img_bytes).decode('utf-8')
        payload = {"key": IMGBB_API_KEY, "image": b64_string}
        response = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if response.status_code == 200: return response.json()["data"]["url"]
        return None
    except: return None

def send_line_push(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or len(LINE_CHANNEL_ACCESS_TOKEN) < 50: return "ERROR_TOKEN"
    if not LINE_USER_ID or not LINE_USER_ID.startswith("U"): return "ERROR_ID"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    data = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    try:
        res = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)
        return "SUCCESS" if res.status_code == 200 else f"FAIL: {res.text}"
    except Exception as e: return str(e)

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue()

def get_data_safe(ws):
    data = safe_api_call(ws.get_all_records)
    if data is None: return pd.DataFrame()
    return pd.DataFrame(data)

def log_event(ws_logs, user, action, detail):
    safe_api_call(ws_logs.append_row, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, detail])

# --- 5. 主程式 ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = ""
        st.session_state['user_role'] = ""

    sh = init_db()
    if not sh: st.stop()

    try:
        ws_items = sh.worksheet("Items")
        headers = ws_items.row_values(1)
        required = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
        if len(headers) < len(required): 
            for i, h in enumerate(required): ws_items.update_cell(1, i+1, h)
    except:
        ws_items = sh.add_worksheet("Items", 100, 20)
        ws_items.append_row(["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"])

    try: ws_logs = sh.worksheet("Logs")
    except: 
        ws_logs = sh.add_worksheet("Logs", 1000, 5)
        ws_logs.append_row(["Timestamp", "User", "Action", "Details"])
        
    try: ws_users = sh.worksheet("Users")
    except:
        ws_users = sh.add_worksheet("Users", 50, 5)
        ws_users.append_row(["Name", "Password", "Role", "Status", "Created_At"])
        ws_users.append_row(["Boss", "1234", "Admin", "Active", str(datetime.now())])

    # --- A. 品牌登入 ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<div class='brand-title'>IFUKUK</div>", unsafe_allow_html=True)
            st.markdown("<div class='brand-subtitle'>INTELLIGENT INVENTORY SYSTEM</div>", unsafe_allow_html=True)
            
            with st.form("login"):
                user_input = st.text_input("帳號 / Username")
                pass_input = st.text_input("密碼 / Password", type="password")
                if st.form_submit_button("登入 / LOGIN", type="primary"):
                    users_df = get_data_safe(ws_users)
                    users_df['Name'] = users_df['Name'].astype(str)
                    users_df['Password'] = users_df['Password'].astype(str)
                    valid = users_df[(users_df['Name'] == user_input) & (users_df['Password'] == pass_input) & (users_df['Status'] == 'Active')]
                    if not valid.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = user_input
                        st.session_state['user_role'] = valid.iloc[0]['Role']
                        log_event(ws_logs, user_input, "Login", "Session Started")
                        st.rerun()
                    else:
                        st.error("登入失敗 / Login Failed")
        return

    # --- B. 數據處理 ---
    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    # --- C. 側邊欄 ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_label = "🔴 Admin" if st.session_state['user_role'] == 'Admin' else "🟢 Staff"
        st.caption(f"Role: {role_label}")
        
        with st.expander("⚙️ 帳號設定"):
            with st.form("pwd"):
                old = st.text_input("舊密碼", type="password")
                new = st.text_input("新密碼", type="password")
                if st.form_submit_button("更新密碼"):
                    try:
                        cell = ws_users.find(st.session_state['user_name'])
                        if str(old) == str(ws_users.cell(cell.row, 2).value) and new:
                            ws_users.update_cell(cell.row, 2, new)
                            st.success("更新成功")
                        else: st.error("失敗")
                    except: pass
        
        st.markdown("---")
        if st.button("🚪 安全登出"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- D. 戰情儀表板 ---
    st.markdown("<div class='brand-title' style='font-size:2rem;text-align:left;'>DASHBOARD</div>", unsafe_allow_html=True)
    
    total_qty = df['Qty'].sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    total_revenue_potential = (df['Qty'] * df['Price']).sum()
    potential_profit = total_revenue_potential - total_cost
    active_sku = len(df)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📦 總庫存件數</div>
            <div class="metric-value">{total_qty:,}</div>
            <div class="metric-sub">{active_sku} 款熱銷中</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid #d32f2f;">
            <div class="metric-label">💰 庫存總成本</div>
            <div class="metric-value">${total_cost:,}</div>
            <div class="metric-sub">資金積壓</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid #f1c40f;">
            <div class="metric-label">💎 預估總銷售額</div>
            <div class="metric-value">${total_revenue_potential:,}</div>
            <div class="metric-sub">全數售出價值</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid #28a745;">
            <div class="metric-label">📈 預估總毛利</div>
            <div class="metric-value">${potential_profit:,}</div>
            <div class="metric-sub">淨值成長潛力</div>
        </div>
        """, unsafe_allow_html=True)

    # 視覺化圖表 (V14.1 修正色票錯誤)
    if not df.empty:
        chart_col1, chart_col2 = st.columns([2, 1])
        with chart_col1:
            st.caption("📊 庫存分類占比 (Inventory Distribution)")
            
            # ⚠️ 修正點：使用手動定義的黑白灰色系，不依賴 px.colors.sequential
            fashion_greys = ['#1a1a1a', '#4d4d4d', '#808080', '#b3b3b3', '#e6e6e6', '#000000']
            
            fig = px.pie(df, names='Category', values='Qty', hole=0.4, color_discrete_sequence=fashion_greys)
            fig.update_layout(showlegend=True, margin=dict(l=0, r=0, t=0, b=0), height=250)
            st.plotly_chart(fig, use_container_width=True)
            
        with chart_col2:
            st.caption("🚨 低庫存警報 (<5件)")
            low_stock = df[df['Qty'] < 5][['SKU', 'Name', 'Qty']]
            if not low_stock.empty:
                st.dataframe(low_stock, hide_index=True, use_container_width=True)
            else:
                st.success("庫存水位健康")

    st.markdown("---")

    # --- E. 功能分頁 ---
    tabs = st.tabs(["🧥 樣品展示", "⚡ 快速 POS", "➕ 商品管理", "📝 系統後台"])

    # Tab 1
    with tabs[0]:
        search_txt = st.text_input("🔍 搜尋商品", placeholder="輸入名稱或 SKU...")
        show_df = df.copy()
        if search_txt: show_df = show_df[show_df.apply(lambda x: search_txt.lower() in str(x.values).lower(), axis=1)]
        
        if show_df.empty: st.info("無符合商品")
        else:
            rows = [show_df.iloc[i:i+4] for i in range(0, len(show_df), 4)]
            for row in rows:
                cols = st.columns(4)
                for idx, (col, item) in enumerate(zip(cols, row.iterrows())):
                    val = item[1]
                    with col:
                        raw_url = str(val['Image_URL']).strip()
                        img = raw_url if raw_url.startswith('http') else "https://via.placeholder.com/150"
                        st.markdown(f"""
                        <div class='product-card'>
                            <div style='height:150px;overflow:hidden;border-radius:5px;margin-bottom:10px;'>
                                <img src='{img}'>
                            </div>
                            <div style='font-weight:bold; color:#333; height:2.4em; overflow:hidden;'>{val['Name']}</div>
                            <div style='font-size:0.8em;color:#888;'>{val['SKU']}</div>
                            <div style='display:flex;justify-content:space-between;margin-top:8px;'>
                                <b style='color:#000;'>${val['Price']}</b>
                                <span style='background:#f1f1f1;padding:2px 8px;border-radius:10px;font-size:0.8em;color:#555;'>Q:{val['Qty']}</span>
                            </div>
                        </div>""", unsafe_allow_html=True)

    # Tab 2
    with tabs[1]:
        st.info("💡 提示：支援 Barcode / QR Code 掃描槍輸入")
        c_pos1, c_pos2 = st.columns([1, 1])
        with c_pos1:
            sku_opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist()
            sel_sku = st.selectbox("鎖定商品", ["請選擇..."] + sku_opts)
            target = None
            if sel_sku != "請選擇...":
                target = df[df['SKU'] == sel_sku.split(" | ")[0]].iloc[0]
                raw_url = str(target['Image_URL']).strip()
                img = raw_url if raw_url.startswith('http') else "https://via.placeholder.com/150"
                st.image(img, width=200)
                st.markdown(f"**{target['Name']}**")
                st.markdown(f"目前庫存: `{target['Qty']}` | 售價: `${target['Price']}`")

        with c_pos2:
            if target is not None:
                op_qty = st.number_input("操作數量", 1)
                note = st.text_input("備註 (選填)")
                b1, b2 = st.columns(2)
                if b1.button("📥 進貨入庫", type="secondary"):
                    r = ws_items.find(target['SKU']).row
                    new_q = int(target['Qty']) + op_qty
                    ws_items.update_cell(r, 5, new_q)
                    ws_items.update_cell(r, 8, str(datetime.now()))
                    log_event(ws_logs, st.session_state['user_name'], "進貨", f"{target['SKU']} +{op_qty}")
                    st.success("入庫完成")
                    time.sleep(1)
                    st.rerun()
                if b2.button("📤 確認銷售", type="primary"):
                    if int(target['Qty']) < op_qty: st.error("庫存不足！")
                    else:
                        r = ws_items.find(target['SKU']).row
                        new_q = int(target['Qty']) - op_qty
                        ws_items.update_cell(r, 5, new_q)
                        ws_items.update_cell(r, 8, str(datetime.now()))
                        log_event(ws_logs, st.session_state['user_name'], "銷售", f"{target['SKU']} -{op_qty}")
                        if new_q < 5:
                            msg = f"⚠️ [缺貨警報] {target['Name']} 剩餘 {new_q} 件！"
                            send_line_push(msg)
                        st.success("銷售成功")
                        time.sleep(1)
                        st.rerun()

    # Tab 3
    with tabs[2]:
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            st.subheader("➕ 新增商品")
            with st.form("add_item"):
                n_sku = st.text_input("SKU")
                n_name = st.text_input("名稱")
                n_cat = st.selectbox("分類", ["上衣", "褲子", "外套", "配件", "其他"])
                n_size = st.selectbox("尺寸", ["F", "S", "M", "L", "XL"])
                col_n1, col_n2 = st.columns(2)
                n_qty = col_n1.number_input("數量", 0)
                n_cost = col_n2.number_input("成本", 0)
                n_price = st.number_input("售價", 0)
                up_file = st.file_uploader("圖片", type=['jpg','png'])
                if st.form_submit_button("建立商品"):
                    if n_sku and n_name:
                        if n_sku in df['SKU'].tolist(): st.error("SKU 已存在")
                        else:
                            url = upload_image_to_imgbb(up_file) if up_file else ""
                            ws_items.append_row([n_sku, n_name, n_cat, n_size, n_qty, n_price, n_cost, str(datetime.now()), url])
                            st.success("已新增")
                            time.sleep(1)
                            st.rerun()

        with c_m2:
            st.subheader("📂 批量 / 標籤")
            with st.expander("Excel 批量匯入"):
                uploaded = st.file_uploader("上傳 CSV/Excel", type=['csv','xlsx'])
                if uploaded and st.button("開始匯入"):
                    try:
                        imp = pd.read_csv(uploaded) if uploaded.name.endswith('.csv') else pd.read_excel(uploaded)
                        cnt = 0
                        for _, row in imp.iterrows():
                            sku = str(row['SKU']).strip()
                            if sku not in df['SKU'].tolist():
                                ws_items.append_row([sku, row['Name'], row['Category'], row['Size'], row['Qty'], row['Price'], row['Cost'], str(datetime.now()), ""])
                                cnt += 1
                        st.success(f"匯入 {cnt} 筆")
                        time.sleep(2)
                        st.rerun()
                    except: st.error("格式錯誤")
            
            with st.expander("🖨️ QR Code"):
                tag = st.selectbox("選擇商品", df['SKU'].tolist())
                if tag: st.image(generate_qr(tag), width=150)

            st.markdown("---")
            d_sku = st.selectbox("刪除商品", ["請選擇..."]+df['SKU'].tolist())
            if d_sku != "請選擇..." and st.button("確認刪除"):
                ws_items.delete_rows(ws_items.find(d_sku).row)
                st.success("已刪除")
                time.sleep(1)
                st.rerun()

    # Tab 4
    with tabs[3]:
        st.subheader("📝 操作紀錄")
        st.dataframe(get_data_safe(ws_logs).sort_index(ascending=False).head(50), use_container_width=True)
        
        if st.session_state['user_role'] == 'Admin':
            st.markdown("---")
            st.subheader("⚙️ 管理員專區")
            if st.button("📡 LINE 連線測試"):
                res = send_line_push("✅ 系統測試連線正常")
                if res == "SUCCESS": st.success("發送成功")
                else: st.error(res)
            
            with st.expander("人員管理"):
                st.dataframe(get_data_safe(ws_users))
                
if __name__ == "__main__":
    main()
