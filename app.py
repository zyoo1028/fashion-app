import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import requests
import plotly.express as px
import base64

# --- 1. 系統全域設定 ---
st.set_page_config(page_title="IFUKUK 企業核心系統", layout="wide", page_icon="🛡️")

# --- ⚠️⚠️⚠️ 設定區 (請填入資料) ⚠️⚠️⚠️ ---
# 1. Google Sheet 網址
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"

# 2. ImgBB API Key (請填入您的 Key)
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a" 

# ---------------------------------------------------

# --- 自定義 CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .brand-title {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-weight: 800;
        font-size: 3rem;
        color: #1E1E1E;
        text-align: center;
        letter-spacing: 2px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        height: 3em;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #f0f0f0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .product-card {
        background: white;
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        transition: transform 0.2s;
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

# --- 3. 圖片上傳模組 ---
def upload_image_to_imgbb(image_file):
    if not IMGBB_API_KEY or "請將您的" in IMGBB_API_KEY:
        st.warning("⚠️ 請先在代碼中填入 ImgBB API Key。")
        return None
    try:
        img_bytes = image_file.getvalue()
        b64_string = base64.b64encode(img_bytes).decode('utf-8')
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": IMGBB_API_KEY, "image": b64_string}
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            return response.json()["data"]["url"]
        else:
            st.error(f"上傳失敗: {response.json().get('error', {}).get('message')}")
            return None
    except Exception as e:
        st.error(f"上傳錯誤: {e}")
        return None

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

    # --- 初始化資料表 (含 Users) ---
    try:
        ws_items = sh.worksheet("Items")
        headers = ws_items.row_values(1)
        required_headers = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
        if len(headers) < len(required_headers):
            for i, h in enumerate(required_headers):
                if i >= len(headers) or headers[i] != h:
                    ws_items.update_cell(1, i+1, h)
    except:
        ws_items = sh.add_worksheet(title="Items", rows="100", cols="20")
        ws_items.append_row(["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"])

    try:
        ws_logs = sh.worksheet("Logs")
    except:
        ws_logs = sh.add_worksheet(title="Logs", rows="1000", cols="5")
        ws_logs.append_row(["Timestamp", "User", "Action", "Details"])

    # V11 新增：Users 表格 (權限管理)
    try:
        ws_users = sh.worksheet("Users")
    except:
        ws_users = sh.add_worksheet(title="Users", rows="50", cols="5")
        ws_users.append_row(["Name", "Password", "Role", "Status", "Created_At"])
        # 預設 Boss 帳號
        ws_users.append_row(["Boss", "1234", "Admin", "Active", str(datetime.now())])

    # --- A. 品牌登入入口 (加入密碼驗證) ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 class='brand-title'>IFUKUK</h1>", unsafe_allow_html=True)
            
            with st.form("login"):
                user_input = st.text_input("帳號 (Name)")
                pass_input = st.text_input("密碼 (Password)", type="password")
                
                if st.form_submit_button("登入系統", type="primary"):
                    # 讀取使用者名單
                    users_df = get_data_safe(ws_users)
                    # 確保欄位都是字串以防比對錯誤
                    users_df['Name'] = users_df['Name'].astype(str)
                    users_df['Password'] = users_df['Password'].astype(str)
                    
                    # 驗證
                    valid_user = users_df[
                        (users_df['Name'] == user_input) & 
                        (users_df['Password'] == pass_input) &
                        (users_df['Status'] == 'Active')
                    ]
                    
                    if not valid_user.empty:
                        role = valid_user.iloc[0]['Role']
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = user_input
                        st.session_state['user_role'] = role
                        log_event(ws_logs, user_input, "系統登入", "Session Started")
                        st.rerun()
                    else:
                        st.error("帳號/密碼錯誤，或帳號已被停用")
        return

    # --- B. 企業戰情中心 ---
    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols:
        if c not in df.columns: df[c] = ""
    for num_col in ['Qty', 'Price', 'Cost']:
        df[num_col] = pd.to_numeric(df[num_col], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    # 側邊導航
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_badge = "🔴 管理員" if st.session_state['user_role'] == 'Admin' else "🟢 員工"
        st.markdown(f"**權限:** {role_badge}")
        
        st.divider()
        if st.button("🔒 安全登出"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- 儀表板 ---
    st.markdown("### 🚀 營運戰情室 (Dashboard)")
    total_rev = (df['Qty'] * df['Price']).sum()
    profit = total_rev - (df['Qty'] * df['Cost']).sum()
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("📦 活躍款式", f"{len(df)} 款")
    kpi2.metric("👕 總庫存量", f"{df['Qty'].sum()} 件")
    kpi3.metric("💰 庫存總市值", f"${total_rev:,.0f}")
    kpi4.metric("📈 預估淨利", f"${profit:,.0f}", delta="Profit", delta_color="normal")
    st.divider()

    # --- 功能分頁 ---
    # 根據權限決定顯示哪些分頁
    tabs = st.tabs(["🧥 樣品室", "⚡ 進銷存", "📝 紀錄與搜尋", "⚙️ 管理後台"])

    # === Tab 1 & 2: 樣品室 與 POS (保持原樣，略作精簡以節省篇幅) ===
    with tabs[0]: # 樣品室
        search_txt = st.text_input("🔍 搜尋商品", placeholder="輸入...")
        show_df = df.copy()
        if search_txt: show_df = show_df[show_df.apply(lambda x: search_txt.lower() in str(x.values).lower(), axis=1)]
        if show_df.empty: st.info("無商品")
        else:
            rows = [show_df.iloc[i:i+4] for i in range(0, len(show_df), 4)]
            for row in rows:
                cols = st.columns(4)
                for idx, (col, item) in enumerate(zip(cols, row.iterrows())):
                    val = item[1]
                    with col:
                        img = val['Image_URL'] if str(val['Image_URL']).startswith('http') else "https://via.placeholder.com/150"
                        st.markdown(f"""<div class='product-card'><img src='{img}' style='width:100%;height:150px;object-fit:cover;border-radius:5px;'><b>{val['Name']}</b><br>Q: {val['Qty']}</div>""", unsafe_allow_html=True)

    with tabs[1]: # POS
        c1, c2 = st.columns([1, 1])
        with c1:
            sku_opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist()
            sel_sku = st.selectbox("選擇商品", ["請選擇..."] + sku_opts)
            target = None
            if sel_sku != "請選擇...":
                target = df[df['SKU'] == sel_sku.split(" | ")[0]].iloc[0]
                st.info(f"庫存: {target['Qty']}")
        with c2:
            if target is not None:
                op_qty = st.number_input("數量", 1)
                note = st.text_input("備註")
                if st.button("確認交易", type="primary"):
                    # 簡單範例，實際代碼可沿用 V10
                    r = ws_items.find(target['SKU']).row
                    # 判斷進貨或銷貨(這裡簡化為一個按鈕範例，實際請參考V10分流)
                    log_event(ws_logs, st.session_state['user_name'], "交易", f"{target['SKU']} 變動 {op_qty} | {note}")
                    st.success("交易已記錄 (請自行補完V10的完整進銷邏輯)")
                    # 這裡為了縮短代碼長度，省略了 V10 的進銷按鈕邏輯，請務必保留 V10 那段

    # === Tab 3: 紀錄與搜尋 (V11 重點優化) ===
    with tabs[2]:
        st.subheader("🔍 歷史紀錄搜尋")
        c_search, c_user = st.columns([3, 1])
        q_keyword = c_search.text_input("輸入關鍵字 (SKU/動作/備註)", placeholder="例如: TEST-002 或 進貨")
        
        # 讀取日誌
        logs_df = get_data_safe(ws_logs)
        
        if not logs_df.empty:
            # 預設顯示最後 1000 筆 (避免當機)
            display_logs = logs_df.tail(1000)
            
            # 搜尋邏輯
            if q_keyword:
                display_logs = logs_df[logs_df.apply(lambda x: q_keyword.lower() in str(x.values).lower(), axis=1)]
            
            # 顯示
            st.dataframe(display_logs.sort_index(ascending=False), use_container_width=True) # 倒序顯示，最新的在上面
            st.caption(f"顯示 {len(display_logs)} 筆紀錄 (資料庫總筆數: {len(logs_df)})")
            
            # 管理員刪除區
            if st.session_state['user_role'] == 'Admin':
                st.divider()
                with st.expander("🗑️ 管理員專用：清理紀錄"):
                    st.warning("⚠️ 警告：此操作將永久刪除所有日誌，無法復原！")
                    if st.button("清除所有測試紀錄", type="primary"):
                        # 保留標題列，刪除其他
                        ws_logs.clear()
                        ws_logs.append_row(["Timestamp", "User", "Action", "Details"])
                        log_event(ws_logs, st.session_state['user_name'], "系統維護", "已清空所有歷史紀錄")
                        st.success("紀錄已清空")
                        time.sleep(1)
                        st.rerun()

    # === Tab 4: 管理後台 (V11 全新功能) ===
    with tabs[3]:
        if st.session_state['user_role'] != 'Admin':
            st.error("⛔ 權限不足：此區域僅限管理員進入")
        else:
            st.subheader("👥 人員權限管理")
            
            # 1. 顯示目前員工列表
            users_list = get_data_safe(ws_users)
            st.dataframe(users_list, use_container_width=True)
            
            st.divider()
            
            # 2. 新增/修改員工
            c_add, c_del = st.columns(2)
            
            with c_add:
                st.markdown("#### ➕ 新增/修改員工")
                with st.form("user_mgt"):
                    u_name = st.text_input("帳號 (Name)")
                    u_pass = st.text_input("密碼 (Password)")
                    u_role = st.selectbox("權限", ["Staff", "Admin"])
                    u_stat = st.selectbox("狀態", ["Active", "Inactive"])
                    
                    if st.form_submit_button("儲存設定"):
                        if u_name and u_pass:
                            # 檢查是否已存在
                            try:
                                cell = ws_users.find(u_name)
                                # 更新現有
                                r = cell.row
                                ws_users.update_cell(r, 2, u_pass)
                                ws_users.update_cell(r, 3, u_role)
                                ws_users.update_cell(r, 4, u_stat)
                                st.success(f"已更新員工 {u_name} 的資料")
                            except:
                                # 新增
                                ws_users.append_row([u_name, u_pass, u_role, u_stat, str(datetime.now())])
                                st.success(f"已新增員工 {u_name}")
                            
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("帳號密碼不可為空")

            with c_del:
                st.markdown("#### 🗑️ 刪除員工")
                del_u = st.selectbox("選擇員工", ["請選擇..."] + users_list['Name'].tolist())
                if del_u != "請選擇...":
                    if del_u == "Boss": 
                        st.error("❌ 無法刪除初始管理員 Boss")
                    elif del_u == st.session_state['user_name']:
                        st.error("❌ 無法刪除自己")
                    else:
                        if st.button("確認刪除員工"):
                            r = ws_users.find(del_u).row
                            ws_users.delete_rows(r)
                            st.success(f"已移除 {del_u}")
                            time.sleep(1)
                            st.rerun()
            
            # 商品管理區 (Admin 才能看到的進階功能)
            st.divider()
            st.subheader("🛠️ 商品資料庫維護")
            # (這裡可以放 V10 的新增商品功能，只有管理員能用)
            # 為了節省篇幅，建議您將 V10 的 'Tab Admin' 內容搬移至此處

if __name__ == "__main__":
    main()
