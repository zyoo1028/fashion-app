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

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK 核心戰情", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# --- ⚠️⚠️⚠️ 設定區 (請填入您的 4 把鑰匙) ⚠️⚠️⚠️ ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
LINE_CHANNEL_ACCESS_TOKEN = "IaGvcTOmbMFW8wKEJ5MamxfRx7QVo0kX1IyCqwKZw0WX2nxAVYY7SsSh5vAJ0r+WBNvyjjiU8G3eYkL1nozqIOjjWMOKr/4ZtzUMRRf7JNJkk5V6jLpWc/EOkzvNGVPMh0zwH+wQD51tR3XWipUULwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U55199b00fb78da85bb285db6d00b6ff5"
# ---------------------------------------------------

# --- 自定義 CSS (美學維持) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .brand-title { font-weight: 900; font-size: 3rem; color: #1a1a1a; text-align: center; letter-spacing: 3px; margin-bottom: 5px; text-transform: uppercase; }
    .metric-card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-left: 5px solid #1a1a1a; text-align: center; margin-bottom: 15px; }
    .metric-value { font-size: 1.8rem; color: #1a1a1a; font-weight: 700; margin: 10px 0; }
    .metric-label { font-size: 0.9rem; color: #888; font-weight: 600; text-transform: uppercase; }
    .stButton>button { border-radius: 50px; font-weight: 600; height: 3.2em; border: none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: all 0.2s; }
    .stButton>button:hover { transform: scale(1.02); }
    .product-card { background: white; border-radius: 15px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #eee; }
    .product-card img { border-radius: 10px; width: 100%; height: 150px; object-fit: cover; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線邏輯 (V15.0 重寫：防崩潰機制) ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=3600)
def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 系統錯誤：找不到 Secrets 金鑰。")
        st.stop()
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource(ttl=3600)
def init_db():
    client = get_connection()
    try:
        sh = client.open_by_url(GOOGLE_SHEET_URL)
        return sh
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return None

# --- V15.0 新增：安全獲取 Worksheet (防止 Duplicate Name 錯誤) ---
def get_or_create_worksheet(sh, title, rows, cols, header=None):
    try:
        # 先檢查是否存在
        existing_titles = [s.title for s in sh.worksheets()]
        if title in existing_titles:
            return sh.worksheet(title)
        else:
            ws = sh.add_worksheet(title, rows, cols)
            if header: ws.append_row(header)
            return ws
    except Exception as e:
        st.error(f"資料表初始化錯誤 ({title}): {e}")
        return None

# --- V15.0 新增：快取加速讀取 (大幅降低 API 呼叫次數) ---
@st.cache_data(ttl=5)  # 設定 5 秒快取，兼顧效能與即時性
def fetch_data_cached(_ws):
    try:
        data = _ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- 3. 工具模組 ---
def upload_image_to_imgbb(image_file):
    if not IMGBB_API_KEY or "請將您的" in IMGBB_API_KEY: return None
    try:
        img_bytes = image_file.getvalue()
        b64_string = base64.b64encode(img_bytes).decode('utf-8')
        payload = {"key": IMGBB_API_KEY, "image": b64_string}
        res = requests.post("https://api.imgbb.com/1/upload", data=payload)
        return res.json()["data"]["url"] if res.status_code == 200 else None
    except: return None

def send_line_push(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or len(LINE_CHANNEL_ACCESS_TOKEN) < 50: return "TOKEN_ERR"
    if not LINE_USER_ID or not LINE_USER_ID.startswith("U"): return "ID_ERR"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    data = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    try:
        requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)
        return "SUCCESS"
    except Exception as e: return str(e)

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue()

def log_event(ws_logs, user, action, detail):
    # 寫入操作不使用快取，確保即時性
    try:
        ws_logs.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, detail])
    except: pass # 紀錄失敗不阻斷流程

# --- 5. 主程式 ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = ""
        st.session_state['user_role'] = ""

    sh = init_db()
    if not sh: st.stop()

    # V15.0 穩定初始化
    ws_items = get_or_create_worksheet(sh, "Items", 100, 20, ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"])
    ws_logs = get_or_create_worksheet(sh, "Logs", 1000, 5, ["Timestamp", "User", "Action", "Details"])
    ws_users = get_or_create_worksheet(sh, "Users", 50, 5, ["Name", "Password", "Role", "Status", "Created_At"])

    # 初始化 Boss 帳號 (如果 Users 空的)
    if ws_users and len(ws_users.get_all_values()) <= 1:
        ws_users.append_row(["Boss", "1234", "Admin", "Active", str(datetime.now())])

    # --- A. 品牌登入 ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<div class='brand-title'>IFUKUK</div>", unsafe_allow_html=True)
            with st.form("login"):
                user_input = st.text_input("帳號")
                pass_input = st.text_input("密碼", type="password")
                if st.form_submit_button("登入 / LOGIN", type="primary"):
                    users_df = fetch_data_cached(ws_users)
                    if not users_df.empty:
                        users_df['Name'] = users_df['Name'].astype(str)
                        users_df['Password'] = users_df['Password'].astype(str)
                        valid = users_df[(users_df['Name'] == user_input) & (users_df['Password'] == pass_input)]
                        if not valid.empty:
                            st.session_state['logged_in'] = True
                            st.session_state['user_name'] = user_input
                            st.session_state['user_role'] = valid.iloc[0]['Role']
                            log_event(ws_logs, user_input, "Login", "Success")
                            st.rerun()
                        else: st.error("帳號或密碼錯誤")
                    else: st.error("系統初始化中，請稍後再試")
        return

    # --- B. 數據讀取 (使用 V15 快取引擎) ---
    df = fetch_data_cached(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    # --- C. 側邊欄 ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        st.caption(f"Role: {st.session_state['user_role']}")
        if st.button("🔄 重新整理系統"): # V15 新增：手動清快取
            st.cache_data.clear()
            st.rerun()
        if st.button("🚪 登出"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- D. 戰情儀表板 ---
    st.markdown("<div class='brand-title' style='font-size:2rem;text-align:left;'>DASHBOARD</div>", unsafe_allow_html=True)
    
    total_qty = df['Qty'].sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    total_rev = (df['Qty'] * df['Price']).sum()
    total_profit = total_rev - total_cost

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-card'><div class='metric-label'>📦 總庫存</div><div class='metric-value'>{total_qty:,}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card' style='border-left-color:#d32f2f;'><div class='metric-label'>💰 總成本</div><div class='metric-value'>${total_cost:,}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card' style='border-left-color:#f1c40f;'><div class='metric-label'>💎 預估營收</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card' style='border-left-color:#28a745;'><div class='metric-label'>📈 潛在毛利</div><div class='metric-value'>${total_profit:,}</div></div>", unsafe_allow_html=True)

    if not df.empty:
        cc1, cc2 = st.columns([2, 1])
        with cc1:
            # 手動色票 (Armani Grey)
            colors = ['#1a1a1a', '#4d4d4d', '#808080', '#b3b3b3', '#e6e6e6']
            fig = px.pie(df, names='Category', values='Qty', hole=0.4, color_discrete_sequence=colors)
            fig.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        with cc2:
            st.caption("🚨 缺貨清單")
            low = df[df['Qty'] < 5][['SKU', 'Name', 'Qty']]
            st.dataframe(low, hide_index=True, use_container_width=True)

    st.markdown("---")

    # --- E. 功能分頁 ---
    tabs = st.tabs(["🧥 樣品", "⚡ POS", "➕ 管理", "📝 紀錄"])

    # Tab 1: 樣品
    with tabs[0]:
        q = st.text_input("🔍 搜尋", placeholder="SKU / Name...")
        v_df = df.copy()
        if q: v_df = v_df[v_df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)]
        
        if not v_df.empty:
            rows = [v_df.iloc[i:i+4] for i in range(0, len(v_df), 4)]
            for row in rows:
                cols = st.columns(4)
                for idx, (col, item) in enumerate(zip(cols, row.iterrows())):
                    val = item[1]
                    with col:
                        url = str(val['Image_URL']).strip()
                        img = url if url.startswith('http') else "https://via.placeholder.com/150"
                        st.markdown(f"""
                        <div class='product-card'>
                            <img src='{img}'>
                            <div style='font-weight:bold;margin-top:5px;'>{val['Name']}</div>
                            <small>{val['SKU']}</small>
                            <div style='display:flex;justify-content:space-between;margin-top:5px;'>
                                <b>${val['Price']}</b> <span>Q:{val['Qty']}</span>
                            </div>
                        </div>""", unsafe_allow_html=True)

    # Tab 2: POS
    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            opts = df.apply(lambda x: f"{x['SKU']} | {x['Name']}", axis=1).tolist()
            sel = st.selectbox("選擇商品 (支援掃碼)", ["..."] + opts)
            target = None
            if sel != "...":
                target = df[df['SKU'] == sel.split(" | ")[0]].iloc[0]
                url = str(target['Image_URL']).strip()
                st.image(url if url.startswith('http') else "https://via.placeholder.com/150", width=150)
                st.markdown(f"**{target['Name']}** (庫存: {target['Qty']})")
        
        with c2:
            if target is not None:
                qty = st.number_input("數量", 1)
                if st.button("📤 銷售 (Sale)", type="primary"):
                    if int(target['Qty']) < qty: st.error("庫存不足")
                    else:
                        try:
                            r = ws_items.find(target['SKU']).row
                            current = int(target['Qty'])
                            new_val = current - qty
                            ws_items.update_cell(r, 5, new_val) # 更新庫存
                            log_event(ws_logs, st.session_state['user_name'], "Sale", f"{target['SKU']} -{qty}")
                            
                            if new_val < 5:
                                send_line_push(f"⚠️ 缺貨警報: {target['Name']} 剩 {new_val} 件")
                            
                            st.success("銷售成功")
                            st.cache_data.clear() # V15 關鍵：交易後清除快取，確保數據即時更新
                            time.sleep(1)
                            st.rerun()
                        except Exception as e: st.error(f"錯誤: {e}")

                if st.button("📥 進貨 (Stock In)", type="secondary"):
                    try:
                        r = ws_items.find(target['SKU']).row
                        new_val = int(target['Qty']) + qty
                        ws_items.update_cell(r, 5, new_val)
                        log_event(ws_logs, st.session_state['user_name'], "Restock", f"{target['SKU']} +{qty}")
                        st.success("進貨成功")
                        st.cache_data.clear() # 清除快取
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"錯誤: {e}")

    # Tab 3: 管理
    with tabs[2]:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("new"):
                st.subheader("新增商品")
                sku = st.text_input("SKU")
                name = st.text_input("名稱")
                cat = st.text_input("分類")
                size = st.selectbox("尺寸", ["F","S","M","L"])
                q = st.number_input("數量", 0)
                cost = st.number_input("成本", 0)
                price = st.number_input("售價", 0)
                img = st.file_uploader("圖片", type=['jpg','png'])
                if st.form_submit_button("建立"):
                    if sku and name:
                        if sku in df['SKU'].tolist(): st.error("SKU 已存在")
                        else:
                            u = upload_image_to_imgbb(img) if img else ""
                            ws_items.append_row([sku, name, cat, size, q, price, cost, str(datetime.now()), u])
                            st.success("成功")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
        with c2:
            st.subheader("工具箱")
            with st.expander("批量匯入"):
                up = st.file_uploader("CSV/Excel", type=['csv','xlsx'])
                if up and st.button("匯入"):
                    try:
                        d = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
                        cnt = 0
                        for _, r in d.iterrows():
                            s = str(r['SKU']).strip()
                            if s not in df['SKU'].tolist():
                                ws_items.append_row([s, r['Name'], r['Category'], r['Size'], r['Qty'], r['Price'], r['Cost'], str(datetime.now()), ""])
                                cnt+=1
                        st.success(f"匯入 {cnt} 筆")
                        st.cache_data.clear()
                        time.sleep(2)
                        st.rerun()
                    except: st.error("格式錯")
            
            with st.expander("QR Code"):
                t = st.selectbox("商品", df['SKU'].tolist())
                if t: st.image(generate_qr(t), width=100)

            d_s = st.selectbox("刪除", ["..."]+df['SKU'].tolist())
            if d_s != "..." and st.button("刪除"):
                ws_items.delete_rows(ws_items.find(d_s).row)
                st.success("已刪除")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

    # Tab 4: 紀錄
    with tabs[3]:
        logs = fetch_data_cached(ws_logs)
        st.dataframe(logs.sort_index(ascending=False).head(50), use_container_width=True)
        if st.session_state['user_role'] == 'Admin':
            if st.button("LINE 測試"):
                res = send_line_push("✅ V15.0 連線測試")
                if res=="SUCCESS": st.success("成功")
                else: st.error(res)

if __name__ == "__main__":
    main()
