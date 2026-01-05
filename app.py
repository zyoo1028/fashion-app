import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. 系統全域設定 ---
st.set_page_config(page_title="Apex Inventory OS", layout="wide", page_icon="💎")

# --- 自定義 CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
    }
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線邏輯 (加入 @st.cache_resource 防止頻繁連線) ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=3600) # 快取連線物件 1 小時，避免重複登入
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到金鑰 (Secrets)。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource(ttl=3600) # 快取試算表物件
def init_db():
    client = get_connection()
    try:
        # ⚠️⚠️⚠️ 主理人：請再次填入您的 Google 試算表網址 ⚠️⚠️⚠️
        sh = client.open_by_url("https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493")
        return sh
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return None

# 讀取資料專用的函數 (加入快取與自動重試)
def fetch_data(sheet_object):
    try:
        return sheet_object.get_all_records()
    except Exception as e:
        # 如果遇到 429 錯誤，等待後重試
        time.sleep(2)
        try:
            return sheet_object.get_all_records()
        except:
            st.warning("系統繁忙 (Google API 限流)，請稍後再試...")
            return []

# 清除快取的 helper
def clear_cache():
    st.cache_data.clear()

# --- 3. 稽核日誌系統 ---
def log_event(ws_logs, user, action, detail):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        ws_logs.append_row([timestamp, user, action, detail])
    except:
        pass # 日誌寫入失敗不應卡住主流程

# --- 4. 主程式邏輯 ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = ""

    sh = init_db()
    if not sh: st.stop()
    
    # 自動維護表格結構
    try:
        ws_items = sh.worksheet("Items")
        headers = ws_items.row_values(1)
        if "Price" not in headers:
            ws_items.update_cell(1, len(headers)+1, "Price")
            ws_items.update_cell(1, len(headers)+2, "Image_URL")
    except:
        ws_items = sh.add_worksheet(title="Items", rows="100", cols="20")
        ws_items.append_row(["SKU", "Name", "Size", "Qty", "Price", "Last_Updated", "Image_URL"])

    try:
        ws_logs = sh.worksheet("Logs")
    except:
        ws_logs = sh.add_worksheet(title="Logs", rows="1000", cols="5")
        ws_logs.append_row(["Timestamp", "User", "Action", "Details"])

    # --- 畫面 A: 登入門戶 ---
    if not st.session_state['logged_in']:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.title("💎 Apex OS | Login")
            st.info("請輸入身分以存取企業資料庫")
            input_name = st.text_input("User Name", placeholder="輸入您的姓名...")
            if st.button("登入系統 (Access System)", type="primary"):
                if input_name.strip():
                    st.session_state['logged_in'] = True
                    st.session_state['user_name'] = input_name
                    log_event(ws_logs, input_name, "系統登入", "使用者已登入 Session")
                    st.rerun()
                else:
                    st.error("請輸入姓名")
        return

    # --- 畫面 B: 系統主介面 ---
    with st.sidebar:
        st.title("🎛️ 控制中心")
        st.write(f"👤 **{st.session_state['user_name']}** 在線")
        if st.button("登出 (Logout)"):
            log_event(ws_logs, st.session_state['user_name'], "系統登出", "使用者結束作業")
            st.session_state['logged_in'] = False
            st.rerun()
        st.divider()
        st.link_button("📂 原始資料庫", sh.url)

    # 讀取資料 (使用優化過的 fetch_data)
    data = fetch_data(ws_items)
    df = pd.DataFrame(data)
    
    # 確保欄位齊全
    required_cols = ["SKU", "Name", "Size", "Qty", "Price", "Last_Updated", "Image_URL"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    # 格式轉換
    df['SKU'] = df['SKU'].astype(str)
    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0).astype(int)
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0).astype(int)

    # --- 儀表板 ---
    st.markdown("### 🚀 營運概況 (Dashboard)")
    total_val = (df['Qty'] * df['Price']).sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 商品總款數", f"{len(df)} 款")
    m2.metric("👕 總庫存件數", f"{df['Qty'].sum()} 件")
    m3.metric("💰 庫存總資產", f"${total_val:,.0f}")
    m4.metric("⚠️ 缺貨預警", f"{len(df[df['Qty']<5])} 款", delta_color="inverse")
    st.divider()

    # --- 功能分頁 ---
    tab_view, tab_op, tab_edit, tab_log = st.tabs(["👁️ 庫存總覽", "⚡ 快速進出貨", "🛠️ 商品管理", "📝 稽核日誌"])

    # === 1. 庫存總覽 ===
    with tab_view:
        search_q = st.text_input("🔍 全局搜尋 (SKU/名稱)", placeholder="Type to search...")
        view_df = df.copy()
        if search_q:
            view_df = view_df[view_df.apply(lambda row: row.astype(str).str.contains(search_q, case=False).any(), axis=1)]
        st.dataframe(
            view_df,
            column_config={
                "Image_URL": st.column_config.ImageColumn("預覽"),
                "Price": st.column_config.NumberColumn("單價", format="$%d"),
                "Qty": st.column_config.ProgressColumn("庫存", min_value=0, max_value=50, format="%d"),
            },
            use_container_width=True,
            hide_index=True
        )

    # === 2. 快速進出貨
