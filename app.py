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

# --- 1. 系統全域設定 ---
st.set_page_config(page_title="IFUKUK 智慧中樞", layout="wide", page_icon="🧠")

# --- ⚠️⚠️⚠️ 設定區 (請填入資料) ⚠️⚠️⚠️ ---

# 1. Google Sheet 網址
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"

# 2. ImgBB API Key
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"

# 3. LINE Channel Access Token (長的那串)
LINE_CHANNEL_ACCESS_TOKEN = "6e6b206277d145fc0e6c24ec3ed94064"

# 4. LINE User ID (U開頭的那串)
LINE_USER_ID = "U55199b00fb78da85bb285db6d00b6ff5"

# ---------------------------------------------------

# --- 自定義 CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .brand-title {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-weight: 800;
        font-size: 2.2rem;
        color: #1E1E1E;
        text-align: center;
        letter-spacing: 1px;
        margin-bottom: 15px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        height: 3.5em;
        transition: all 0.2s;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] label { color: #333333 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #000000 !important; }
    .product-card {
        background: white;
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border: 1px solid #f0f0f0;
    }
    .product-card div, .product-card b, .product-card span {
        color: #333333 !important;
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
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                st.error(f"連線異常: {e}")
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
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": IMGBB_API_KEY, "image": b64_string}
        response = requests.post(url, data=payload)
        if response.status_code == 200: return response.json()["data"]["url"]
        return None
    except: return None

# V13.1: LINE Messaging API (含錯誤回報)
def send_line_push(message):
    # 1. 檢查是否填寫資料
    if not LINE_CHANNEL_ACCESS_TOKEN or "請將您的" in LINE_CHANNEL_ACCESS_TOKEN:
        return "ERROR_TOKEN_EMPTY"
    if not LINE_USER_ID or "請將您的" in LINE_USER_ID:
        return "ERROR_ID_EMPTY"
    
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return "SUCCESS"
        else:
            # 回傳錯誤代碼與訊息以便除錯
            return f"FAILED: {response.status_code} - {response.text}"
    except Exception as e:
        return f"EXCEPTION: {str(e)}"

# QR Code
def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue()

# --- 4. 數據與日誌模組 ---
def get_data_safe(ws):
    data = safe_api_call(ws.get_all_records)
    if data is None: return pd.DataFrame()
    return pd.DataFrame(data)

def log_event(ws_logs, user, action, detail):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_api_call(ws_logs.append_row, [timestamp, user, action, detail])

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
        required_headers = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
        if len(headers) < len(required_headers):
            for i, h in enumerate(required_headers):
                if i >= len(headers) or headers[i] != h: ws_items.update_cell(1, i+1, h)
    except:
        ws_items = sh.add_worksheet(title="Items", rows="100", cols="20")
        ws_items.append_row(["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"])

    try: ws_logs = sh.worksheet("Logs")
    except:
        ws_logs = sh.add_worksheet(title="Logs", rows="1000", cols="5")
        ws_logs.append_row(["Timestamp", "User", "Action", "Details"])

    try: ws_users = sh.worksheet("Users")
    except:
        ws_users = sh.add_worksheet(title="Users", rows="50", cols="5")
        ws_users.append_row(["Name", "Password", "Role", "Status", "Created_At"])
        ws_users.append_row(["Boss", "1234", "Admin", "Active", str(datetime.now())])

    # --- A. 品牌登入 ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 class='brand-title'>IFUKUK</h1>", unsafe_allow_html=True)
            with st.form("login"):
                user_input = st.text_input("帳號")
                pass_input = st.text_input("密碼", type="password")
                if st.form_submit_button("登入系統", type="primary"):
                    users_df = get_data_safe(ws_users)
                    users_df['Name'] = users_df['Name'].astype(str)
                    users_df['Password'] = users_df['Password'].astype(str)
                    valid_user = users_df[(users_df['Name'] == user_input) & (users_df['Password'] == pass_input) & (users_df['Status'] == 'Active')]
                    if not valid_user.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = user_input
                        st.session_state['user_role'] = valid_user.iloc[0]['Role']
                        log_event(ws_logs, user_input, "系統登入", "Session Started")
                        st.rerun()
                    else:
                        st.error("登入失敗")
        return

    # --- B. 系統主畫面 ---
    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols:
        if c not in df.columns: df[c] = ""
    for num_col in ['Qty', 'Price', 'Cost']:
        df[num_col] = pd.to_numeric(df[num_col], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_badge = "🔴 管理員" if st.session_state['user_role'] == 'Admin' else "🟢 員工"
        st.markdown(f"**權限:** {role_badge}")
        with st.expander("🔑 修改密碼"):
            with st.form("pwd"):
                old = st.text_input("舊密碼", type="password")
                new = st.text_input("新密碼", type="password")
                if st.form_submit_button("修改"):
                    try:
                        cell = ws_users.find(st.session_state['user_name'])
                        real = ws_users.cell(cell.row, 2).value
                        if str(old) == str(real) and new:
                            ws_users.update_cell(cell.row, 2, new)
                            st.success("成功")
                        else: st.error("失敗")
                    except: pass
        st.divider()
        if st.button("🔒 登出"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- 儀表板 ---
    st.markdown("### 🚀 營運戰情")
    total_rev = (df['Qty'] * df['Price']).sum()
    profit = total_rev - (df['Qty'] * df['Cost']).sum()
    kpi1, kpi2 = st.columns(2)
    kpi3, kpi4 = st.columns(2)
    kpi1.metric("📦 款式", f"{len(df)}")
    kpi2.metric("👕 庫存", f"{df['Qty'].sum()}")
    kpi3.metric("💰 市值", f"${total_rev:,.0f}")
    kpi4.metric("📈 淨利", f"${profit:,.0f}")
    st.divider()

    tabs = st.tabs(["🧥 樣品", "⚡ POS", "➕ 商品與匯入", "📝 紀錄/後台"])

    # Tab 1: 樣品
    with tabs[0]:
        search_txt = st.text_input("🔍 搜尋商品", placeholder="輸入名稱或SKU...")
        show_df = df.copy()
        if search_txt: show_df = show_df[show_df.apply(lambda x: search_txt.lower() in str(x.values).lower(), axis=1)]
        if show_df.empty: st.info("無商品")
        else:
            rows = [show_df.iloc[i:i+2] for i in range(0, len(show_df), 2)]
            for row in rows:
                cols = st.columns(2)
                for idx, (col, item) in enumerate(zip(cols, row.iterrows())):
                    val = item[1]
                    with col:
                        img = val['Image_URL'] if str(val['Image_URL']).startswith('http') else "https://via.placeholder.com/150"
                        st.markdown(f"""
                        <div class='product-card'>
                            <div style='height:120px;overflow:hidden;border-radius:5px;margin-bottom:5px;'>
                                <img src='{img}' style='width:100%;height:100%;object-fit:cover;'>
                            </div>
                            <div style='font-weight:bold;font-size:1em;height:2.4em;overflow:hidden;'>{val['Name']}</div>
                            <div style='font-size:0.8em;color:#666;'>{val['SKU']}</div>
                            <div style='display:flex;justify-content:space-between;margin-top:5px;'>
                                <b style='color:#d32f2f;'>${val['Price']}</b>
                                <span style='background:#eee;padding:1px 5px;border-radius:3px;font-size:0.9em;'>Q:{val['Qty']}</span>
                            </div>
                        </div>""", unsafe_allow_html=True)

    # Tab 2: POS
    with tabs[1]:
        st.caption("🔍 支援 QR Code 掃描槍")
        sku_opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist()
        sel_sku = st.selectbox("鎖定商品", ["請選擇..."] + sku_opts)
        
        target = None
        if sel_sku != "請選擇...":
            target = df[df['SKU'] == sel_sku.split(" | ")[0]].iloc[0]
            st.info(f"庫存: {target['Qty']} | 售價: ${target['Price']}")
            op_qty = st.number_input("數量", 1)
            note = st.text_input("備註")
            c_in, c_out = st.columns(2)
            
            if c_in.button("📥 進貨", type="secondary"):
                r = ws_items.find(target['SKU']).row
                new_q = int(target['Qty']) + op_qty
                ws_items.update_cell(r, 5, new_q)
                ws_items.update_cell(r, 8, str(datetime.now()))
                log_event(ws_logs, st.session_state['user_name'], "進貨", f"{target['SKU']} +{op_qty} | {note}")
                st.success("成功")
                time.sleep(1)
                st.rerun()
                
            if c_out.button("📤 銷售", type="primary"):
                if int(target['Qty']) < op_qty:
                    st.error("庫存不足")
                else:
                    r = ws_items.find(target['SKU']).row
                    new_q = int(target['Qty']) - op_qty
                    ws_items.update_cell(r, 5, new_q)
                    ws_items.update_cell(r, 8, str(datetime.now()))
                    log_event(ws_logs, st.session_state['user_name'], "銷售", f"{target['SKU']} -{op_qty} | {note}")
                    
                    # 警報觸發
                    if new_q < 5:
                        msg = f"⚠️ [缺貨警報] \n商品: {target['Name']} \n剩餘: {new_q} 件 \n請盡速補貨！"
                        result = send_line_push(msg)
                        if result == "SUCCESS":
                            st.toast("✅ LINE 通知已發送", icon="📢")
                        else:
                            st.error(f"❌ LINE 發送失敗: {result}")
                        
                    st.success("成功")
                    time.sleep(2)
                    st.rerun()

    # Tab 3: 商品與匯入
    with tabs[2]:
        st.subheader("🛠️ 商品資料庫管理")
        with st.expander("➕ 單筆新增 / 圖片上傳"):
            with st.form("new_item"):
                c1, c2 = st.columns(2)
                n_sku = c1.text_input("SKU 編號")
                n_name = c2.text_input("商品名稱")
                c3, c4, c5 = st.columns(3)
                n_cat = c3.text_input("分類")
                n_size = c4.selectbox("尺寸", ["F", "S", "M", "L", "XL"])
                n_qty = c5.number_input("數量", 0)
                c6, c7 = st.columns(2)
                n_cost = c6.number_input("成本", 0)
                n_price = c7.number_input("售價", 0)
                up_file = st.file_uploader("圖片", type=['png', 'jpg'])
                if st.form_submit_button("建立"):
                    if n_sku and n_name:
                        if n_sku in df['SKU'].tolist(): st.error("SKU重複")
                        else:
                            url = upload_image_to_imgbb(up_file) if up_file else ""
                            ws_items.append_row([n_sku, n_name, n_cat, n_size, n_qty, n_price, n_cost, str(datetime.now()), url])
                            st.success("成功")
                            time.sleep(1)
                            st.rerun()
                            
        with st.expander("📂 Excel 批量匯入 (進階)"):
            st.info("請先下載範本，填寫後上傳。")
            sample_data = pd.DataFrame(columns=["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost"])
            csv = sample_data.to_csv(index=False).encode('utf-8')
            st.download_button("📥 下載範本 (CSV)", data=csv, file_name="import_template.csv", mime="text/csv")
            uploaded_excel = st.file_uploader("上傳檔案", type=['csv', 'xlsx'])
            if uploaded_excel:
                if st.button("確認匯入"):
                    try:
                        if uploaded_excel.name.endswith('.csv'): imp_df = pd.read_csv(uploaded_excel)
                        else: imp_df = pd.read_excel(uploaded_excel)
                        success_count = 0
                        existing_skus = df['SKU'].tolist()
                        progress_bar = st.progress(0)
                        for idx, row in imp_df.iterrows():
                            sku = str(row['SKU']).strip()
                            if sku in existing_skus:
                                cell = ws_items.find(sku)
                                current_q = int(ws_items.cell(cell.row, 5).value)
                                ws_items.update_cell(cell.row, 5, current_q + int(row['Qty']))
                            else: ws_items.append_row([sku, row['Name'], row['Category'], row['Size'], row['Qty'], row['Price'], row['Cost'], str(datetime.now()), ""])
                            success_count += 1
                            progress_bar.progress((idx + 1) / len(imp_df))
                        st.success(f"匯入 {success_count} 筆成功")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e: st.error(f"錯誤: {e}")

        with st.expander("🖨️ QR Code 標籤"):
            tag_sku = st.selectbox("選擇商品", df['SKU'].tolist())
            if tag_sku:
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    qr_bytes = generate_qr(tag_sku)
                    st.image(qr_bytes, width=150)
                with col_info: st.info("可右鍵下載列印")

        st.divider()
        st.caption("🗑️ 刪除商品")
        del_sku = st.selectbox("選擇刪除", ["請選擇..."] + df['SKU'].tolist())
        if del_sku != "請選擇...":
            if st.button("永久刪除", type="secondary"):
                r = ws_items.find(del_sku).row
                safe_api_call(ws_items.delete_rows, r)
                st.success("已刪除")
                time.sleep(1)
                st.rerun()

    # Tab 4: 紀錄/後台
    with tabs[3]:
        st.subheader("🔍 紀錄")
        col_date, col_key = st.columns(2)
        search_date = col_date.date_input("📅 日期", value=None)
        search_key = col_key.text_input("關鍵字")
        logs_df = get_data_safe(ws_logs)
        if not logs_df.empty:
            logs_df['DateObj'] = pd.to_datetime(logs_df['Timestamp'], errors='coerce').dt.date
            display_logs = logs_df.copy()
            if search_date: display_logs = display_logs[display_logs['DateObj'] == search_date]
            if search_key: display_logs = display_logs[display_logs.apply(lambda x: search_key.lower() in str(x.values).lower(), axis=1)]
            st.dataframe(display_logs.drop(columns=['DateObj']).sort_index(ascending=False).tail(500), use_container_width=True)
        
        if st.session_state['user_role'] == 'Admin':
            st.divider()
            st.subheader("⚙️ 管理員後台")
            
            # === V13.1 新增：LINE 連線測試 ===
            st.info("📡 LINE 系統診斷中心")
            if st.button("發送測試訊息 (Test Connection)"):
                test_msg = "✅ IFUKUK 系統連線成功！這是一條測試訊息。"
                result = send_line_push(test_msg)
                if result == "SUCCESS":
                    st.success("測試成功！您的手機應該會收到訊息。")
                elif "ERROR_TOKEN_EMPTY" in result:
                    st.error("❌ 失敗：請檢查代碼第 26 行，Channel Access Token 尚未填入。")
                elif "ERROR_ID_EMPTY" in result:
                    st.error("❌ 失敗：請檢查代碼第 29 行，User ID 尚未填入。")
                else:
                    st.error(f"❌ 傳送失敗，錯誤詳情：\n{result}")
            # ==================================

            with st.expander("👥 員工管理 / 🔴 清空"):
                st.dataframe(get_data_safe(ws_users), use_container_width=True)
                action = st.radio("動作", ["新增/修改", "刪除"], horizontal=True)
                if action == "新增/修改":
                     n = st.text_input("帳號", key="u_n")
                     p = st.text_input("密碼", key="u_p")
                     r = st.selectbox("權限", ["Staff", "Admin"], key="u_r")
                     if st.button("儲存"):
                         try:
                             cell = ws_users.find(n)
                             ws_users.update_cell(cell.row, 2, p)
                             ws_users.update_cell(cell.row, 3, r)
                         except: ws_users.append_row([n, p, r, "Active", str(datetime.now())])
                         st.success("完成")
                         time.sleep(1)
                         st.rerun()
                else:
                     del_n = st.selectbox("刪除誰", ws_users.col_values(1)[1:])
                     if st.button("刪除"):
                         ws_users.delete_rows(ws_users.find(del_n).row)
                         st.success("已刪除")
                         time.sleep(1)
                         st.rerun()
                if st.button("🔴 清空紀錄"):
                    ws_logs.clear()
                    ws_logs.append_row(["Timestamp", "User", "Action", "Details"])
                    st.success("已清空")
                    time.sleep(1)
                    st.rerun()

if __name__ == "__main__":
    main()
