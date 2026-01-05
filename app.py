import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Apex V7.2 Config ---
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
    try:
        # ⚠️⚠️⚠️ 主理人請注意：請將下方引號內的網址，換成您剛剛測試成功的那串 Google 試算表網址 ⚠️⚠️⚠️
        sh = client.open_by_url("https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493") 
        return sh
    except Exception as e:
        st.error(f"連線失敗，請檢查網址或權限: {e}")
        return None

def main():
    st.title("☁️ Apex 服飾庫存 - V7.2 團隊版")

    # 1. 啟動連線
    client = get_connection()
    sh = init_db(client)
    if not sh: st.stop()

    ws_items = sh.worksheet("Items")
    ws_logs = sh.worksheet("Logs") # 這裡我們把紀錄功能加回來

    # 2. 身份驗證 (把門鎖裝回來)
    st.sidebar.header("🔐 員工登入")
    user_name = st.sidebar.text_input("請輸入您的姓名")
    
    if not user_name:
        st.warning("⚠️ 請先在左側輸入姓名，以解鎖系統並開始作業。")
        st.stop() # 這裡會暫停，直到輸入名字
    
    st.sidebar.success(f"Hi, {user_name} (已連線)")
    st.sidebar.divider()
    st.sidebar.link_button("🔗 打開 Google 資料庫", sh.url)

    # 3. 讀取資料
    data = ws_items.get_all_records()
    df = pd.DataFrame(data)

    # 處理空資料
    if df.empty:
        sku_list = []
    else:
        df['SKU'] = df['SKU'].astype(str) # 強制轉文字
        sku_list = df['SKU'].tolist()

    # --- 分頁介面 ---
    tab1, tab2, tab3 = st.tabs(["📦 庫存清單", "➕ 新增商品", "📝 操作紀錄"])

    # === Tab 1: 清單 ===
    with tab1:
        if df.empty:
            st.info("目前資料庫是空的。請到隔壁分頁新增商品 👉")
        else:
            # 搜尋框
            search = st.text_input("🔍 搜尋商品 (SKU 或名稱)")
            if search:
                # 簡單搜尋邏輯
                df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
            
            st.dataframe(df, use_container_width=True)

    # === Tab 2: 新增 ===
    with tab2:
        with st.form("add_form"):
            n_name = st.text_input("商品名稱 (例如：修身牛仔褲)")
            n_sku = st.text_input("SKU (例如：JN-001)")
            n_size = st.selectbox("尺寸", ["S", "M", "L", "XL", "F"])
            n_qty = st.number_input("數量", value=10)
            
            if st.form_submit_button("確認新增"):
                if n_sku and n_name:
                    if n_sku in sku_list:
                        st.error(f"❌ SKU '{n_sku}' 已經存在了！")
                    else:
                        # 寫入商品表
                        ws_items.append_row([n_sku, n_name, n_size, n_qty, str(datetime.now())])
                        # 寫入紀錄表 (加上 user_name)
                        ws_logs.append_row([str(datetime.now()), user_name, "新增商品", f"{n_sku} {n_name}"])
                        
                        st.success(f"✅ 成功新增：{n_name}")
                        st.rerun()
                else:
                    st.warning("請填寫完整資訊")

    # === Tab 3: 紀錄 (看誰做了什麼) ===
    with tab3:
        logs_data = ws_logs.get_all_records()
        st.dataframe(pd.DataFrame(logs_data), use_container_width=True)

if __name__ == "__main__":
    main()
