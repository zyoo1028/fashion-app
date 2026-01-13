import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import base64
import calendar

# --- 1. 系統全域設定 & CSS ---
st.set_page_config(
    page_title="OMEGA STOCK V102",
    layout="wide",
    page_icon="🧊",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    /* 全域字體與背景優化 */
    .stApp { background-color: #F8F9FA !important; }
    
    /* 卡片式設計優化 */
    .css-1r6slb0 { border: 1px solid #ddd; padding: 10px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    
    /* 排班表優化 */
    .shift-tag {
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: bold;
        color: white;
        margin-left: 5px;
    }
    .shift-早 { background-color: #10b981; }
    .shift-晚 { background-color: #8b5cf6; }
    .shift-全 { background-color: #f59e0b; }
    .shift-休 { background-color: #ef4444; }
    
    /* 隱藏預設選單 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 連線設定 (請確認你的 Secrets 或憑證設定) ---
# 這裡假設你已經有 secrets.toml 設定，或者直接把憑證 dict 放這裡
# 若你的連線方式不同，請保留你原本的前 15 行連線設定
# ==========================================
try:
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    # 嘗試從 Streamlit Secrets 讀取 (推薦)
    if 'gcp_service_account' in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets['gcp_service_account'], scopes=scope)
    else:
        # 本地測試 fallback (若無 secret)
        st.error("找不到憑證設定，請確認 .streamlit/secrets.toml")
        st.stop()
        
    client = gspread.authorize(creds)
    # 請將這裡換成你的 Google Sheet 名稱或網址
    SHEET_URL = st.secrets["private_gsheets_url"] if "private_gsheets_url" in st.secrets else "你的試算表網址" 
    
    # 嘗試開啟試算表
    if "http" in SHEET_URL:
        sh = client.open_by_url(SHEET_URL)
    else:
        sh = client.open(SHEET_URL)
        
except Exception as e:
    st.error(f"連線失敗，請檢查憑證或網址: {str(e)}")
    st.stop()

# --- 3. 輔助函式 ---

def get_data(worksheet_name):
    try:
        ws = sh.worksheet(worksheet_name)
        return pd.DataFrame(ws.get_all_records())
    except:
        return pd.DataFrame() # 若無該表則回傳空

def save_image_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            bytes_data = uploaded_file.getvalue()
            base64_str = base64.b64encode(bytes_data).decode()
            # 判斷副檔名
            mime = "image/png" if uploaded_file.type == "image/png" else "image/jpeg"
            return f"data:{mime};base64,{base64_str}"
        except:
            return ""
    return ""

# --- 4. 主程式邏輯 ---

# 頂部導航
menu = ["📦 新增商品", "🔄 視覺調撥", "🗑️ 商品刪除", "📅 排班管理"]
choice = st.selectbox("功能選單", menu, label_visibility="collapsed")

st.divider()

# ==================== 1. 新增商品區 (修復：成本 + 圖片上傳) ====================
if choice == "📦 新增商品":
    st.header("📦 新增商品數據 (完整版)")
    
    with st.form("add_product_form", clear_on_submit=False):
        c1, c2 = st.columns([1, 1])
        
        with c1:
            base_sku = st.text_input("Base SKU (款號)", placeholder="例如: TOP-2601")
            p_name = st.text_input("商品名稱", placeholder="例如: 米色低胸長袖")
            category = st.selectbox("分類", ["上衣 (Top)", "下身 (Bottom)", "配件 (Accessory)"])
            
            # 【修復】加入成本欄位
            col_p, col_c = st.columns(2)
            with col_p:
                price = st.number_input("售價 (Price)", min_value=0)
            with col_c:
                cost = st.number_input("成本 (Cost)", min_value=0, help="輸入進貨成本")
                
            currency = st.selectbox("幣別", ["TWD", "CNY"])

        with c2:
            # 【修復】使用 file_uploader 支援手機/電腦選圖
            uploaded_file = st.file_uploader("上傳商品圖片 (支援手機拍照)", type=['png', 'jpg', 'jpeg'])
            
            st.write("各尺寸庫存數量:")
            sizes_cols = st.columns(5)
            qty_map = {}
            size_labels = ["F", "S", "M", "L", "XL"]
            for i, s_label in enumerate(size_labels):
                with sizes_cols[i]:
                    qty_map[s_label] = st.number_input(f"{s_label}", min_value=0, value=0, key=f"qty_{s_label}")

        submitted = st.form_submit_button("💾 寫入資料庫")
        
        if submitted:
            if not base_sku or not p_name:
                st.error("請填寫 SKU 與 商品名稱！")
            else:
                try:
                    ws = sh.worksheet("Products")
                except:
                    ws = sh.add_worksheet("Products", 1000, 20)
                    ws.append_row(["Timestamp", "BaseSKU", "FullSKU", "Name", "Category", "Size", "Price", "Cost", "Currency", "Stock", "Image"])

                # 處理圖片
                img_str = save_image_base64(uploaded_file)
                
                # 批次寫入
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rows_to_add = []
                
                for size, qty in qty_map.items():
                    # 即使庫存為0也建立資料，方便後續管理，或可依需求改為 if qty > 0
                    full_sku = f"{base_sku}-{size}"
                    rows_to_add.append([
                        timestamp, base_sku, full_sku, p_name, category, 
                        size, price, cost, currency, qty, img_str
                    ])
                
                if rows_to_add:
                    ws.append_rows(rows_to_add)
                    st.success(f"✅ 商品 {p_name} (共 {len(rows_to_add)} 個尺寸) 已新增成功！")
                    time.sleep(1)
                    st.rerun()

# ==================== 2. 調撥區 (修復：顯示完整資訊) ====================
elif choice == "🔄 視覺調撥":
    st.header("🔄 視覺調撥系統")
    
    if st.button("🔄 重新整理庫存"):
        st.cache_data.clear()
        st.rerun()

    df = get_data("Products")
    
    if df.empty:
        st.warning("目前無商品資料")
    else:
        # 搜尋功能
        search_term = st.text_input("🔍 搜尋商品 (名稱/SKU)", "")
        if search_term:
            df = df[df['Name'].astype(str).str.contains(search_term, case=False) | 
                    df['FullSKU'].astype(str).str.contains(search_term, case=False)]

        # 版面配置：左邊商品牆，右邊操作籃
        col_main, col_cart = st.columns([3, 1])
        
        # 初始化 Session State
        if 'selected_item' not in st.session_state:
            st.session_state.selected_item = None

        with col_main:
            st.caption("點擊商品圖片進行選取")
            # 製作 Grid Layout
            cols = st.columns(4) # 4欄位
            for idx, row in df.iterrows():
                c = cols[idx % 4]
                with c:
                    # 【修復】卡片顯示邏輯：圖片 -> 名稱 -> 尺寸 -> SKU
                    with st.container():
                        # 顯示圖片 (若無圖片顯示 placeholder)
                        if str(row['Image']).startswith('data:image'):
                            st.image(row['Image'], use_column_width=True)
                        else:
                            st.markdown("📷 *No Image*")
                        
                        # 按鈕作為卡片點擊區
                        # label 顯示 名稱 + 尺寸
                        btn_label = f"{row['Name']} ({row['Size']})\n{row['FullSKU']}"
                        if st.button(btn_label, key=f"btn_{idx}"):
                            st.session_state.selected_item = row

        with col_cart:
            st.info("🛒 操作面板")
            item = st.session_state.selected_item
            if item is not None:
                st.write(f"**{item['Name']}**")
                st.write(f"Size: {item['Size']}")
                st.write(f"SKU: {item['FullSKU']}")
                st.write(f"目前庫存: {item['Stock']}")
                
                qty = st.number_input("調撥數量", min_value=1, value=1)
                
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button("TW ➔ CN"):
                    st.toast(f"已從 TW 調撥 {qty} 件至 CN (模擬)")
                    # 這裡需補上實際扣減庫存邏輯
                if c_btn2.button("CN ➔ TW"):
                    st.toast(f"已從 CN 調撥 {qty} 件至 TW (模擬)")
            else:
                st.write("👈 請先從左側選取商品")

# ==================== 3. 刪除區 (修復：表格詳細模式) ====================
elif choice == "🗑️ 商品刪除":
    st.header("🗑️ 商品刪除管理 (表格檢視)")
    
    df = get_data("Products")
    if df.empty:
        st.write("無資料")
    else:
        # 搜尋
        filter_txt = st.text_input("搜尋欲刪除商品...", "")
        if filter_txt:
            df = df[df['Name'].str.contains(filter_txt, case=False) | df['FullSKU'].str.contains(filter_txt, case=False)]

        # 【修復】使用 dataframe 搭配勾選框或多選刪除，比純文字列表清楚
        # 為了達到「表格 + 圖片 + 刪除」的最佳體驗，我們使用 st.data_editor (如果 Streamlit 版本夠新)
        # 或者使用手刻表格
        
        st.write("請勾選要刪除的項目 (支援批次刪除):")
        
        # 增加一個 checkbox column
        if "Delete" not in df.columns:
            df.insert(0, "Delete", False)
            
        # 顯示可編輯表格 (除了 Delete 外其他唯讀)
        edited_df = st.data_editor(
            df[['Delete', 'FullSKU', 'Name', 'Size', 'Stock', 'Price']], 
            column_config={
                "Delete": st.column_config.CheckboxColumn("刪除?", help="勾選以刪除", default=False),
                "Image": st.column_config.ImageColumn("預覽圖") # 如果要顯示圖片需將 Image 欄位放入
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 執行刪除按鈕
        to_delete = edited_df[edited_df["Delete"] == True]
        
        if not to_delete.empty:
            st.error(f"⚠️ 即將刪除 {len(to_delete)} 筆資料！")
            if st.button("❌ 確認永久刪除"):
                ws = sh.worksheet("Products")
                all_values = ws.get_all_values()
                
                # 簡單邏輯：過濾掉要刪除的 FullSKU
                # 注意：這在大數據量時可能較慢，建議用 gspread 的 batch_clear 或 delete_row
                # 這裡使用重建法確保安全
                
                sku_to_remove = to_delete['FullSKU'].tolist()
                new_data = [all_values[0]] # header
                
                # 找出 FullSKU 在第幾欄 (假設是第3欄, index 2)
                header = all_values[0]
                sku_idx = header.index("FullSKU")
                
                for row in all_values[1:]:
                    if row[sku_idx] not in sku_to_remove:
                        new_data.append(row)
                
                ws.clear()
                ws.update(new_data)
                st.success("刪除成功！")
                time.sleep(1)
                st.rerun()

# ==================== 4. 排班區 (修復：括號與顯示邏輯) ====================
elif choice == "📅 排班管理":
    st.header("📅 人員排班表")
    
    # 讀取排班資料
    try:
        sch_df = get_data("Schedule")
    except:
        sch_df = pd.DataFrame(columns=["Date", "Name", "Shift"])

    # 選擇年/月
    c_y, c_m = st.columns(2)
    now = datetime.now()
    sel_year = c_y.number_input("年份", value=now.year)
    sel_month = c_m.number_input("月份", min_value=1, max_value=12, value=now.month)
    
    # 排班操作區
    st.write("---")
    c_act1, c_act2, c_act3, c_act4 = st.columns(4)
    target_date = c_act1.date_input("選擇日期", value=now)
    target_staff = c_act2.selectbox("人員", ["結瑋", "張哲", "叡", "店長"])
    target_shift = c_act3.selectbox("班別", ["早", "晚", "全", "休", "DELETE"])
    
    if c_act4.button("提交排班"):
        date_str = target_date.strftime("%Y-%m-%d")
        ws_sch = None
        try:
            ws_sch = sh.worksheet("Schedule")
        except:
            ws_sch = sh.add_worksheet("Schedule", 1000, 5)
            ws_sch.append_row(["Date", "Name", "Shift"])
            
        # 先刪除舊的 (簡單做法：讀取 -> 過濾 -> 寫回 -> 新增)
        # 為了效能，這裡直接 append，顯示時取最新的即可 (Append-only log)
        # 或是做正規的 update
        
        # 這裡採用 Append 模式，顯示時去重
        if target_shift == "DELETE":
             # 標記刪除 (可以在顯示邏輯過濾)
             ws_sch.append_row([date_str, target_staff, "DELETE"])
        else:
             ws_sch.append_row([date_str, target_staff, target_shift])
             
        st.success(f"已更新: {date_str} {target_staff} -> {target_shift}")
        time.sleep(0.5)
        st.rerun()

    # --- 日曆顯示邏輯 (修復括號問題) ---
    st.write("---")
    
    # 整理資料：將 DataFrame 轉為 Dict 方便查詢 {(Date, Name): Shift}
    # 取最後一筆 (覆蓋舊的)
    shift_map = {}
    if not sch_df.empty:
        for _, row in sch_df.iterrows():
            d = str(row['Date'])
            n = row['Name']
            s = row['Shift']
            key = (d, n)
            if s == "DELETE":
                if key in shift_map: del shift_map[key]
            else:
                shift_map[key] = s

    # 繪製月曆
    cal = calendar.monthcalendar(sel_year, sel_month)
    days = ["一", "二", "三", "四", "五", "六", "日"]
    
    # 表頭
    cols = st.columns(7)
    for i, d in enumerate(days):
        cols[i].markdown(f"**{d}**")
        
    # 表格內容
    staff_list = ["結瑋", "張哲", "叡", "店長"]
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.write("") # 空白日
                else:
                    # 日期格式化
                    current_date_str = f"{sel_year}-{sel_month:02d}-{day:02d}"
                    
                    # 顯示日期
                    st.markdown(f"##### {day}")
                    
                    # 顯示當天排班
                    for staff in staff_list:
                        shift = shift_map.get((current_date_str, staff), None)
                        
                        # 【修復】這裡解決括號空白問題
                        if shift:
                            # 有排班：顯示 名字 + (班別) + 顏色標籤
                            # 使用 HTML 渲染顏色
                            html_tag = f"""
                            <div style='margin-bottom:2px; font-size:12px;'>
                                {staff} <span class='shift-tag shift-{shift}'>({shift})</span>
                            </div>
                            """
                            st.markdown(html_tag, unsafe_allow_html=True)
                        else:
                            # 無排班：不顯示，或顯示淡淡的名字
                            # 依據你的需求，這裡選擇不顯示空白括號
                            pass
                            # 如果想顯示未排班狀態，可打開下面這行：
                            # st.markdown(f"<div style='color:#ddd; font-size:10px;'>{staff}</div>", unsafe_allow_html=True)

    st.caption("註：若剛排班未顯示，請點擊上方重新整理")
