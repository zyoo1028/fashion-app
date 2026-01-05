import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. 系統全域設定 (System Config) ---
st.set_page_config(page_title="Apex Inventory OS", layout="wide", page_icon="💎")

# --- 自定義 CSS (時尚化介面) ---
st.markdown("""
    <style>
    /* 隱藏預設選單和Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 按鈕美化 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
    }
    
    /* 儀表板卡片風格 */
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
    }
    
    /* 登入框置中優化 */
    .login-box {
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線邏輯 (Brain) ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到金鑰 (Secrets)。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def init_db(client):
    try:
        # ⚠️⚠️⚠️ 主理人：請在此填入您的 Google 試算表網址 ⚠️⚠️⚠️
        sh = client.open_by_url("https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493")
        return sh
    except Exception as e:
        st.error(f"連線失敗: {e}")
        st.stop()

# --- 3. 稽核日誌系統 (Audit System) ---
def log_event(ws_logs, user, action, detail):
    """
    寫入日誌的核心功能
    包含：時間、操作者、動作類別、詳細內容
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws_logs.append_row([timestamp, user, action, detail])

# --- 4. 主程式邏輯 ---
def main():
    # 初始化 Session State (用於記住登入狀態)
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = ""

    # 啟動連線
    client = get_connection()
    sh = init_db(client)
    
    # 自動維護表格結構 (確保 Price 欄位存在)
    try:
        ws_items = sh.worksheet("Items")
        headers = ws_items.row_values(1)
        if "Price" not in headers:
            # 如果發現舊表格沒價格欄位，自動加上
            ws_items.update_cell(1, len(headers)+1, "Price")
            ws_items.update_cell(1, len(headers)+2, "Image_URL") # 確保也有圖
    except:
        # 如果連 Items 表都沒有，直接建立標準表
        ws_items = sh.add_worksheet(title="Items", rows="100", cols="20")
        ws_items.append_row(["SKU", "Name", "Size", "Qty", "Price", "Last_Updated", "Image_URL"])

    try:
        ws_logs = sh.worksheet("Logs")
    except:
        ws_logs = sh.add_worksheet(title="Logs", rows="1000", cols="5")
        ws_logs.append_row(["Timestamp", "User", "Action", "Details"])

    # --- 畫面 A: 登入門戶 (Login Portal) ---
    if not st.session_state['logged_in']:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br><br>", unsafe_allow_html=True) # 排版留白
            st.title("💎 Apex OS | Login")
            st.info("請輸入身分以存取企業資料庫")
            
            input_name = st.text_input("User Name", placeholder="輸入您的姓名...")
            
            if st.button("登入系統 (Access System)", type="primary"):
                if input_name.strip():
                    st.session_state['logged_in'] = True
                    st.session_state['user_name'] = input_name
                    # 🔥 關鍵功能：記錄登入時間
                    log_event(ws_logs, input_name, "系統登入", "使用者已登入 Session")
                    st.rerun()
                else:
                    st.error("請輸入姓名")
        return # 沒登入就停在這裡，不執行下面代碼

    # --- 畫面 B: 系統主介面 (Logged In) ---
    
    # 側邊導航
    with st.sidebar:
        st.title("🎛️ 控制中心")
        st.write(f"👤 **{st.session_state['user_name']}** 在線")
        
        if st.button("登出 (Logout)"):
            log_event(ws_logs, st.session_state['user_name'], "系統登出", "使用者結束作業")
            st.session_state['logged_in'] = False
            st.rerun()
        
        st.divider()
        st.link_button("📂 原始資料庫 (Google Sheet)", sh.url)

    # 讀取數據
    data = ws_items.get_all_records()
    df = pd.DataFrame(data)
    
    # 確保欄位齊全 (防呆)
    required_cols = ["SKU", "Name", "Size", "Qty", "Price", "Last_Updated", "Image_URL"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = "" # 補空值

    # 數據轉型
    df['SKU'] = df['SKU'].astype(str)
    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0).astype(int)
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0).astype(int)

    # --- 📊 戰情儀表板 (Dashboard) ---
    st.markdown("### 🚀 營運概況 (Dashboard)")
    total_val = (df['Qty'] * df['Price']).sum() # 計算總資產
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 商品總款數", f"{len(df)} 款")
    m2.metric("👕 總庫存件數", f"{df['Qty'].sum()} 件")
    m3.metric("💰 庫存總資產", f"${total_val:,.0f}")
    m4.metric("⚠️ 缺貨預警", f"{len(df[df['Qty']<5])} 款", delta_color="inverse")
    
    st.divider()

    # --- 功能分頁 ---
    tab_view, tab_op, tab_edit, tab_log = st.tabs([
        "👁️ 庫存總覽 (View)", 
        "⚡ 快速進出貨 (Ops)", 
        "🛠️ 商品管理 (Edit/Del)", 
        "📝 稽核日誌 (Logs)"
    ])

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

    # === 2. 快速進出貨 ===
    with tab_op:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("📦 選擇商品")
            sku_opt = st.selectbox("SKU", df['SKU'].tolist(), key="op_sku")
            # 顯示選中商品的當前資訊
            if sku_opt:
                curr_item = df[df['SKU'] == sku_opt].iloc[0]
                st.info(f"當前: {curr_item['Name']} | 庫存: {curr_item['Qty']} | 尺寸: {curr_item['Size']}")
                curr_qty = int(curr_item['Qty'])
                row_idx = ws_items.find(sku_opt).row # 找到行數
            
        with c2:
            st.subheader("⚡ 執行動作")
            op_qty = st.number_input("變動數量", min_value=1, value=1)
            
            col_in, col_out = st.columns(2)
            if col_in.button("📥 進貨 (Inbound)", type="secondary"):
                new_q = curr_qty + op_qty
                # 更新試算表 (欄位4是Qty, 欄位6是時間)
                ws_items.update_cell(row_idx, 4, new_q)
                ws_items.update_cell(row_idx, 6, str(datetime.now()))
                # 記錄
                log_event(ws_logs, st.session_state['user_name'], "進貨", f"{sku_opt} +{op_qty} (結餘:{new_q})")
                st.success("進貨完成")
                time.sleep(1)
                st.rerun()

            if col_out.button("📤 出貨 (Outbound)", type="primary"):
                if curr_qty < op_qty:
                    st.error("❌ 庫存不足！")
                else:
                    new_q = curr_qty - op_qty
                    ws_items.update_cell(row_idx, 4, new_q)
                    ws_items.update_cell(row_idx, 6, str(datetime.now()))
                    log_event(ws_logs, st.session_state['user_name'], "出貨", f"{sku_opt} -{op_qty} (結餘:{new_q})")
                    st.success("出貨完成")
                    time.sleep(1)
                    st.rerun()

    # === 3. 商品管理 (新增/修改/刪除) ===
    with tab_edit:
        mode = st.radio("模式選擇", ["➕ 新增新品", "✏️ 修改資訊", "🗑️ 刪除商品"], horizontal=True)
        
        if mode == "➕ 新增新品":
            with st.form("new_prod"):
                c_a, c_b = st.columns(2)
                n_sku = c_a.text_input("SKU (編號)")
                n_name = c_b.text_input("商品名稱")
                n_price = c_a.number_input("單價 ($)", min_value=0)
                n_qty = c_b.number_input("初始數量", min_value=0)
                n_size = c_a.selectbox("尺寸", ["F", "S", "M", "L", "XL"])
                n_img = c_b.text_input("圖片連結 (URL)")
                
                if st.form_submit_button("建立商品"):
                    if n_sku in df['SKU'].tolist():
                        st.error("SKU 已存在")
                    elif n_sku and n_name:
                        ws_items.append_row([n_sku, n_name, n_size, n_qty, n_price, str(datetime.now()), n_img])
                        log_event(ws_logs, st.session_state['user_name'], "新增資料", f"建立 {n_sku} {n_name}")
                        st.success("已建立")
                        st.rerun()

        elif mode == "✏️ 修改資訊":
            st.warning("⚠️ 此區修改將直接覆寫資料庫，請謹慎操作。")
            edit_sku = st.selectbox("選擇要修改的商品", df['SKU'].tolist())
            if edit_sku:
                # 抓出舊資料
                old_data = df[df['SKU'] == edit_sku].iloc[0]
                
                with st.form("edit_form"):
                    e_name = st.text_input("名稱", value=old_data['Name'])
                    e_price = st.number_input("單價", value=int(old_data['Price']))
                    e_img = st.text_input("圖片連結", value=old_data['Image_URL'])
                    
                    if st.form_submit_button("確認修改"):
                        # 找出列數
                        e_row = ws_items.find(edit_sku).row
                        # 檢查變更了什麼
                        changes = []
                        if e_name != old_data['Name']: changes.append(f"名稱: {old_data['Name']}->{e_name}")
                        if e_price != int(old_data['Price']): changes.append(f"價格: {old_data['Price']}->{e_price}")
                        if e_img != old_data['Image_URL']: changes.append("更新圖片")
                        
                        if changes:
                            # 執行更新 (欄位對應: 2=Name, 5=Price, 7=Image)
                            ws_items.update_cell(e_row, 2, e_name)
                            ws_items.update_cell(e_row, 5, e_price)
                            ws_items.update_cell(e_row, 7, e_img)
                            ws_items.update_cell(e_row, 6, str(datetime.now())) # 更新時間
                            
                            # 記錄修改內容
                            log_event(ws_logs, st.session_state['user_name'], "修改資料", f"{edit_sku}: {', '.join(changes)}")
                            st.success("修改完成")
                            st.rerun()
                        else:
                            st.info("未偵測到變更")

        elif mode == "🗑️ 刪除商品":
            del_sku = st.selectbox("選擇刪除對象", ["請選擇..."] + df['SKU'].tolist())
            if del_sku != "請選擇...":
                st.error(f"確定要刪除 {del_sku} 嗎？此操作不可逆！")
                if st.button("確認執行刪除"):
                    d_row = ws_items.find(del_sku).row
                    ws_items.delete_rows(d_row)
                    log_event(ws_logs, st.session_state['user_name'], "刪除資料", f"移除 SKU: {del_sku}")
                    st.success("已刪除")
                    st.rerun()

    # === 4. 稽核日誌 ===
    with tab_log:
        st.dataframe(pd.DataFrame(ws_logs.get_all_records()), use_container_width=True)

if __name__ == "__main__":
    main()
