import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Apex V7.1 Config ---
st.set_page_config(page_title="服飾庫存 Apex", layout="wide", page_icon="☁️")

# --- 連線設定 ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("請設定 Secrets！")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def init_db(client):
    # 這裡請務必確認是您正確的網址 (若您之前已貼上正確的，請把下面這行換回您的網址)
    # 為了保險，我們這裡用 "open_by_url" 並請您再次確認填入
    # 如果您懶得改，可以先試著用回 open("Inventory_DB")，但我建議用網址最穩
    try:
        # ⚠️ 請注意：下面這一行請換成您真正的 Google 試算表網址 ⚠️
        sh = client.open_by_url("https://docs.google.com/spreadsheets/d/您的試算表ID_請替換這裡") 
        return sh
    except Exception as e:
        st.error(f"連線失敗，請檢查網址或權限: {e}")
        return None

def main():
    st.title("☁️ Apex 服飾庫存 - V7.1 最終版")

    client = get_connection()
    sh = init_db(client)
    if not sh: st.stop()

    ws_items = sh.worksheet("Items")
    ws_logs = sh.worksheet("Logs")

    # 🔗 絕對傳送門：讓 App 告訴你它連去哪了
    st.sidebar.success("系統連線正常")
    st.sidebar.link_button("🔗 點我打開目前連線的資料庫", sh.url)

    # 讀取資料
    data = ws_items.get_all_records()
    df = pd.DataFrame(data)

    # 處理空資料狀況
    if df.empty:
        sku_list = []
    else:
        # 強制轉字串避免數字/文字混淆
        df['SKU'] = df['SKU'].astype(str)
        sku_list = df['SKU'].tolist()

    # --- 介面 ---
    tab1, tab2 = st.tabs(["📦 庫存清單", "➕ 新增商品"])

    with tab1:
        if df.empty:
            st.info("目前資料庫是空的。請到隔壁分頁新增商品 👉")
        else:
            st.dataframe(df, use_container_width=True)

    with tab2:
        with st.form("add_form"):
            n_name = st.text_input("商品名稱 (例如：白T)")
            n_sku = st.text_input("SKU (例如：T-001)")
            n_qty = st.number_input("數量", value=10)
            
            if st.form_submit_button("確認新增"):
                if n_sku and n_name:
                    # ✨ V7.1 新邏輯：直接檢查我們剛剛讀到的清單 ✨
                    # 如果清單是空的，這裡絕對不會擋你
                    if n_sku in sku_list:
                        st.error(f"❌ SKU '{n_sku}' 已經存在了！不能重複。")
                    else:
                        ws_items.append_row([n_sku, n_name, "F", n_qty, str(datetime.now())])
                        st.success(f"✅ 成功新增：{n_name}")
                        st.rerun() # 立刻刷新
                else:
                    st.warning("請把名稱和 SKU 填好")

if __name__ == "__main__":
    main()
