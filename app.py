import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Apex V7.3 Config (專業版設定) ---
st.set_page_config(page_title="Apex 庫存戰情室", layout="wide", page_icon="🏢")

# --- 連線核心 ---
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
    st.title("🏢 Apex 庫存戰情室 - V7.3")

    # 1. 啟動連線
    client = get_connection()
    sh = init_db(client)
    if not sh: st.stop()

    ws_items = sh.worksheet("Items")
    ws_logs = sh.worksheet("Logs")

    # 2. 身份驗證 (門禁系統)
    with st.sidebar:
        st.header("🔐 團隊登入")
        user_name = st.text_input("輸入姓名 (例如: Boss)")
        if not user_name:
            st.warning("請先輸入姓名解鎖系統")
            st.stop()
        
        st.success(f"👤 {user_name} 在線中")
        st.divider()
        st.link_button("🔗 打開原始資料庫 (Google Sheet)", sh.url)

    # 3. 讀取與處理資料
    data = ws_items.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        sku_list = []
        df = pd.DataFrame(columns=["SKU", "Name", "Size", "Qty", "Last_Updated", "Image_URL"])
    else:
        df['SKU'] = df['SKU'].astype(str)
        # 確保有圖片欄位
        if "Image_URL" not in df.columns:
            df["Image_URL"] = "" 
        sku_list = df['SKU'].tolist()

    # --- 📊 戰情儀表板 (Dashboard) ---
    # 讓老闆一進來就看到重點
    total_items = len(df)
    total_stock = df['Qty'].sum() if not df.empty else 0
    low_stock_count = len(df[df['Qty'] < 5]) if not df.empty and 'Qty' in df.columns else 0

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("📦 總商品款數", f"{total_items} 款")
    col_m2.metric("👕 總庫存件數", f"{total_stock} 件")
    col_m3.metric("⚠️ 低庫存警示", f"{low_stock_count} 款", delta_color="inverse")
    
    st.divider()

    # --- 功能分頁 ---
    tab1, tab2, tab3 = st.tabs(["📋 庫存總覽", "⚙️ 進貨與管理 (新增/刪除)", "📝 操作日誌"])

    # === Tab 1: 庫存總覽 (像專業電商後台一樣顯示) ===
    with tab1:
        if df.empty:
            st.info("目前無資料")
        else:
            # 搜尋
            search = st.text_input("🔍 搜尋商品", placeholder="輸入 SKU 或 名稱...")
            if search:
                df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
            
            # 專業展示：把圖片連結變成真的圖片顯示
            st.dataframe(
                df, 
                column_config={
                    "Image_URL": st.column_config.ImageColumn("預覽圖"),
                    "Qty": st.column_config.ProgressColumn("庫存水位", format="%d", min_value=0, max_value=50),
                },
                use_container_width=True
            )

    # === Tab 2: 管理中心 (新增 + 刪除) ===
    with tab2:
        col_add, col_del = st.columns([1, 1])
        
        # 左邊：新增/進貨
        with col_add:
            st.subheader("➕ 新增商品")
            with st.form("add_form"):
                n_sku = st.text_input("SKU (編號)", placeholder="例如: T-001")
                n_name = st.text_input("商品名稱")
                n_size = st.selectbox("尺寸", ["S", "M", "L", "XL", "F"])
                n_qty = st.number_input("初始數量", min_value=1, value=10)
                n_img = st.text_input("圖片連結 (選填)", placeholder="貼上圖片網址...")
                
                if st.form_submit_button("確認新增"):
                    if n_sku in sku_list:
                        st.error("SKU 已存在！請使用下方刪除功能先移除舊的。")
                    elif n_sku and n_name:
                        ws_items.append_row([n_sku, n_name, n_size, n_qty, str(datetime.now()), n_img])
                        ws_logs.append_row([str(datetime.now()), user_name, "新增", f"{n_sku} {n_name}"])
                        st.success(f"已建立 {n_name}")
                        st.rerun()

        # 右邊：刪除 (這是您要的新功能)
        with col_del:
            st.subheader("🗑️ 刪除商品")
            st.warning("注意：刪除後無法復原！")
            
            del_sku = st.selectbox("選擇要刪除的 SKU", ["請選擇..."] + sku_list)
            
            if del_sku != "請選擇...":
                # 顯示該商品資訊確認
                item_info = df[df['SKU'] == del_sku].iloc[0]
                st.info(f"即將刪除：{item_info['Name']} (庫存: {item_info['Qty']})")
                
                if st.button("確認刪除 (Delete)", type="primary"):
                    try:
                        # 找到那一列在哪裡
                        cell = ws_items.find(del_sku)
                        ws_items.delete_rows(cell.row)
                        
                        ws_logs.append_row([str(datetime.now()), user_name, "刪除", f"移除 SKU: {del_sku}"])
                        st.success("刪除成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"刪除失敗: {e}")

    # === Tab 3: 日誌 ===
    with tab3:
        st.dataframe(pd.DataFrame(ws_logs.get_all_records()), use_container_width=True)

if __name__ == "__main__":
    main()
