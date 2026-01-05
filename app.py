import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Apex V7.0 Cloud Config ---
st.set_page_config(page_title="服飾庫存雲端版", layout="wide", page_icon="☁️")

# --- 連接 Google Sheets ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_connection():
    """連接到 Google Sheets 資料庫"""
    # 從 Streamlit Secrets 讀取金鑰
    if "gcp_service_account" not in st.secrets:
        st.error("未設定金鑰！請檢查 Streamlit Secrets 設定。")
        st.stop()
    
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

def init_db(client):
    """初始化試算表"""
    try:
        sh = client.open_by_url("https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493")
        
        # 檢查或建立 'Items' 工作表
        try:
            ws = sh.worksheet("Items")
        except:
            ws = sh.add_worksheet(title="Items", rows="100", cols="20")
            ws.append_row(["SKU", "Name", "Size", "Qty", "Last_Updated"])

        # 檢查或建立 'Logs' 工作表
        try:
            log_ws = sh.worksheet("Logs")
        except:
            log_ws = sh.add_worksheet(title="Logs", rows="100", cols="20")
            log_ws.append_row(["Timestamp", "User", "Action", "Details"])
            
        return sh
    except Exception as e:
        st.error(f"無法連接資料庫，請確認 Google Sheet 名稱是否為 'Inventory_DB' 且已共用給機器人 Email。錯誤訊息: {e}")
        return None

# --- 核心邏輯 ---
def main():
    st.title("☁️ Apex 服飾庫存 - 全球連線版")

    # 1. 建立連線
    try:
        client = get_connection()
        sh = init_db(client)
        if not sh: st.stop()
        ws_items = sh.worksheet("Items")
        ws_logs = sh.worksheet("Logs")
    except Exception as e:
        st.error(f"連線失敗: {e}")
        st.stop()

    # 2. 側邊欄登入
    st.sidebar.header("🔐 員工登入")
    user_name = st.sidebar.text_input("輸入您的姓名")
    if not user_name:
        st.warning("請先輸入姓名以解鎖系統")
        st.stop()
    st.sidebar.success(f"Hi, {user_name}")

    # 3. 讀取資料
    data = ws_items.get_all_records()
    df = pd.DataFrame(data)

    # 分頁介面
    tab1, tab2, tab3 = st.tabs(["📦 庫存管理", "➕ 新增商品", "📝 操作紀錄"])

    # === Tab 1: 庫存管理 ===
    with tab1:
        if not df.empty:
            # 確保 Qty 是數字
            if 'Qty' in df.columns:
                df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0).astype(int)
            
            # 警示
            low_stock = df[df['Qty'] < 5] if 'Qty' in df.columns else pd.DataFrame()
            if not low_stock.empty:
                st.error(f"⚠️ 缺貨警報：{len(low_stock)} 款商品低於 5 件！")
                st.dataframe(low_stock)

            st.dataframe(df, use_container_width=True)

            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            
            sku_list = df['SKU'].tolist() if 'SKU' in df.columns else []
            selected_sku = col1.selectbox("選擇商品 SKU", sku_list) if sku_list else None
            qty_change = col2.number_input("數量", min_value=1, value=1)

            # 尋找該 SKU 在第幾列
            if selected_sku:
                try:
                    cell = ws_items.find(selected_sku)
                    current_qty = int(ws_items.cell(cell.row, 4).value)
                    col1.info(f"目前庫存: {current_qty}")

                    if col3.button("📥 進貨"):
                        new_qty = current_qty + qty_change
                        ws_items.update_cell(cell.row, 4, new_qty)
                        ws_items.update_cell(cell.row, 5, str(datetime.now()))
                        ws_logs.append_row([str(datetime.now()), user_name, "進貨", f"{selected_sku} +{qty_change}"])
                        st.success("進貨完成！")
                        st.rerun()

                    if col4.button("📤 出貨"):
                        if current_qty < qty_change:
                            st.error("庫存不足！")
                        else:
                            new_qty = current_qty - qty_change
                            ws_items.update_cell(cell.row, 4, new_qty)
                            ws_items.update_cell(cell.row, 5, str(datetime.now()))
                            ws_logs.append_row([str(datetime.now()), user_name, "出貨", f"{selected_sku} -{qty_change}"])
                            st.success("出貨完成！")
                            st.rerun()
                except Exception as e:
                    st.error("讀取數據錯誤，請重試")
        else:
            st.info("目前無資料，請去新增商品。")

    # === Tab 2: 新增商品 ===
    with tab2:
        with st.form("new_item"):
            n_name = st.text_input("商品名稱")
            n_sku = st.text_input("SKU (唯一編號)")
            n_size = st.selectbox("尺寸", ["S", "M", "L", "XL", "F"])
            n_qty = st.number_input("初始數量", 0)
            if st.form_submit_button("新增"):
                if n_sku and n_name:
                    try:
                        ws_items.find(n_sku)
                        st.error("SKU 已存在！")
                    except:
                        ws_items.append_row([n_sku, n_name, n_size, n_qty, str(datetime.now())])
                        ws_logs.append_row([str(datetime.now()), user_name, "新增商品", f"{n_sku} {n_name}"])
                        st.success("已新增！")
                        st.rerun()

    # === Tab 3: 紀錄 ===
    with tab3:
        logs_data = ws_logs.get_all_records()
        st.dataframe(pd.DataFrame(logs_data), use_container_width=True)

if __name__ == "__main__":
    main()
