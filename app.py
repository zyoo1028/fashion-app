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

# --- 1. 系統全域設定 (恢復美學版配置) ---
st.set_page_config(
    page_title="IFUKUK 核心戰情", 
    layout="wide", 
    page_icon="👑",
    initial_sidebar_state="expanded"
)

# --- ⚠️⚠️⚠️ 設定區 (請填入您的 4 把鑰匙) ⚠️⚠️⚠️ ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493    "
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
LINE_CHANNEL_ACCESS_TOKEN = "IaGvcTOmbMFW8wKEJ5MamxfRx7QVo0kX1IyCqwKZw0WX2nxAVYY7SsSh5vAJ0r+WBNvyjjiU8G3eYkL1nozqIOjjWMOKr/4ZtzUMRRf7JNJkk5V6jLpWc/EOkzvNGVPMh0zwH+wQD51tR3XWipUULwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U55199b00fb78da85bb285db6d00b6ff5"
# ---------------------------------------------------

# --- 自定義 CSS (V16.0: 完美復刻 V14 時尚美學) ---
st.markdown("""
    <style>
    /* 全站字體與背景 */
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .brand-title {
        font-weight: 900;
        font-size: 2.5rem;
        color: #1a1a1a;
        text-align: center;
        letter-spacing: 2px;
        margin-bottom: 20px;
        text-transform: uppercase;
    }
    
    /* 數據卡片 */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 6px solid #1a1a1a;
        text-align: center;
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-3px);
    }
    .metric-value {
        font-size: 2rem;
        color: #1a1a1a;
        font-weight: 700;
        margin: 5px 0;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #666;
        font-weight: 600;
        letter-spacing: 1px;
    }
    
    /* 按鈕美化 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        height: 3em;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 5px 10px rgba(0,0,0,0.1);
    }
    
    /* 商品卡片優化 */
    .product-card {
        background: white;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0 3px 8px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border: 1px solid #eee;
    }
    .product-card img {
        border-radius: 8px;
        width: 100%;
        height: 140px;
        object-fit: cover;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線邏輯 (V16.0: 智慧防崩潰版) ---
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
    try:
        return func(*args, **kwargs)
    except Exception as e:
        time.sleep(1)
        try:
            return func(*args, **kwargs)
        except:
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

# V16.0 核心修復：絕對安全的表單獲取邏輯
def get_worksheet_safe(sh, title, headers):
    try:
        # 嘗試直接獲取
        return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        # 如果找不到，才建立
        ws = sh.add_worksheet(title, rows=100, cols=20)
        ws.append_row(headers)
        return ws
    except Exception as e:
        st.error(f"資料表讀取錯誤 ({title}): {e}")
        return None

# --- 3. 工具模組 ---
def upload_image_to_imgbb(image_file):
    if not IMGBB_API_KEY or "請將您的" in IMGBB_API_KEY: return None
    try:
        img_bytes = image_file.getvalue()
        b64_string = base64.b64encode(img_bytes).decode('utf-8')
        payload = {"key": IMGBB_API_KEY, "image": b64_string}
        response = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if response.status_code == 200: return response.json()["data"]["url"]
        return None
    except: return None

def send_line_push(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or len(LINE_CHANNEL_ACCESS_TOKEN) < 50: return "ERROR_TOKEN"
    if not LINE_USER_ID or not LINE_USER_ID.startswith("U"): return "ERROR_ID"
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

def get_data_safe(ws):
    data = safe_api_call(ws.get_all_records)
    if data is None: return pd.DataFrame()
    return pd.DataFrame(data)

def log_event(ws_logs, user, action, detail):
    safe_api_call(ws_logs.append_row, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, detail])

# --- 5. 主程式 ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = ""
        st.session_state['user_role'] = ""

    sh = init_db()
    if not sh: st.stop()

    # V16.0 修正：使用安全函式獲取 Worksheet，防止重複建立崩潰
    ws_items = get_worksheet_safe(sh, "Items", ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"])
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    # --- A. 品牌登入 ---
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<div class='brand-title'>IFUKUK</div>", unsafe_allow_html=True)
            with st.form("login"):
                user_input = st.text_input("帳號")
                pass_input = st.text_input("密碼", type="password")
                if st.form_submit_button("登入系統", type="primary"):
                    users_df = get_data_safe(ws_users)
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
                    else:
                        # 緊急後門：如果資料庫是空的，允許 Boss 登入並初始化
                        if user_input == "Boss" and pass_input == "1234":
                            ws_users.append_row(["Boss", "1234", "Admin", "Active", str(datetime.now())])
                            st.success("系統初始化完成，請重新登入")
                        else:
                            st.error("系統初始化中或帳密錯誤")
        return

    # --- B. 數據讀取 ---
    df = get_data_safe(ws_items)
    cols = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL"]
    for c in cols: 
        if c not in df.columns: df[c] = ""
    for num in ['Qty', 'Price', 'Cost']:
        df[num] = pd.to_numeric(df[num], errors='coerce').fillna(0).astype(int)
    df['SKU'] = df['SKU'].astype(str)

    # --- C. 側邊欄 ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['user_name']}")
        role_label = "🔴 Admin" if st.session_state['user_role'] == 'Admin' else "🟢 Staff"
        st.caption(f"Role: {role_label}")
        
        with st.expander("⚙️ 帳號設定"):
            with st.form("pwd"):
                old = st.text_input("舊密碼", type="password")
                new = st.text_input("新密碼", type="password")
                if st.form_submit_button("更新"):
                    try:
                        cell = ws_users.find(st.session_state['user_name'])
                        if str(old) == str(ws_users.cell(cell.row, 2).value) and new:
                            ws_users.update_cell(cell.row, 2, new)
                            st.success("成功")
                        else: st.error("失敗")
                    except: pass
        
        st.markdown("---")
        if st.button("🚪 登出"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- D. 戰情儀表板 (V16 復刻美學版) ---
    st.markdown("<div class='brand-title' style='font-size:1.8rem;text-align:left;margin-bottom:10px;'>DASHBOARD</div>", unsafe_allow_html=True)
    
    total_qty = df['Qty'].sum()
    total_cost = (df['Qty'] * df['Cost']).sum()
    total_rev = (df['Qty'] * df['Price']).sum()
    total_profit = total_rev - total_cost

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>📦 總庫存</div><div class='metric-value'>{total_qty:,}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card' style='border-left-color:#d32f2f;'><div class='metric-label'>💰 總成本</div><div class='metric-value'>${total_cost:,}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card' style='border-left-color:#f1c40f;'><div class='metric-label'>💎 預估營收</div><div class='metric-value'>${total_rev:,}</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card' style='border-left-color:#28a745;'><div class='metric-label'>📈 潛在毛利</div><div class='metric-value'>${total_profit:,}</div></div>", unsafe_allow_html=True)

    if not df.empty:
        cc1, cc2 = st.columns([2, 1])
        with cc1:
            # V16 修復：手動指定顏色，不使用 plotly.express.colors (避免報錯)
            fashion_greys = ['#1a1a1a', '#4d4d4d', '#808080', '#b3b3b3', '#e6e6e6', '#000000']
            fig = px.pie(df, names='Category', values='Qty', hole=0.4, color_discrete_sequence=fashion_greys)
            fig.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        with cc2:
            st.caption("🚨 缺貨清單")
            low = df[df['Qty'] < 5][['SKU', 'Name', 'Qty']]
            st.dataframe(low, hide_index=True, use_container_width=True)

    st.markdown("---")

    # --- E. 功能分頁 ---
    tabs = st.tabs(["🧥 樣品展示", "⚡ POS", "➕ 商品管理", "📝 系統後台"])

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
                            <div style='font-weight:bold;margin-top:5px;height:2.4em;overflow:hidden;'>{val['Name']}</div>
                            <small style='color:#888'>{val['SKU']}</small>
                            <div style='display:flex;justify-content:space-between;margin-top:5px;'>
                                <b>${val['Price']}</b> <span style='background:#f0f0f0;padding:2px 6px;border-radius:4px;'>Q:{val['Qty']}</span>
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
                st.markdown(f"**{target['Name']}**")
                st.markdown(f"庫存: `{target['Qty']}` | 售價: `${target['Price']}`")
        
        with c2:
            if target is not None:
                qty = st.number_input("數量", 1)
                note = st.text_input("備註")
                b1, b2 = st.columns(2)
                if b1.button("📥 進貨", type="secondary"):
                    r = ws_items.find(target['SKU']).row
                    new_val = int(target['Qty']) + qty
                    ws_items.update_cell(r, 5, new_val)
                    ws_items.update_cell(r, 8, str(datetime.now()))
                    log_event(ws_logs, st.session_state['user_name'], "Restock", f"{target['SKU']} +{qty} | {note}")
                    st.success("成功")
                    time.sleep(1)
                    st.rerun()
                    
                if b2.button("📤 銷售", type="primary"):
                    if int(target['Qty']) < qty: st.error("庫存不足")
                    else:
                        r = ws_items.find(target['SKU']).row
                        new_val = int(target['Qty']) - qty
                        ws_items.update_cell(r, 5, new_val)
                        ws_items.update_cell(r, 8, str(datetime.now()))
                        log_event(ws_logs, st.session_state['user_name'], "Sale", f"{target['SKU']} -{qty} | {note}")
                        
                        if new_val < 5:
                            send_line_push(f"⚠️ 缺貨警報: {target['Name']} 剩 {new_val} 件")
                        st.success("成功")
                        time.sleep(1)
                        st.rerun()

    # Tab 3: 管理
    with tabs[2]:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("新增商品")
            with st.form("new"):
                sku = st.text_input("SKU")
                name = st.text_input("名稱")
                cat = st.selectbox("分類", ["上衣", "褲子", "外套", "配件", "其他"])
                size = st.selectbox("尺寸", ["F","S","M","L","XL"])
                col_sub1, col_sub2 = st.columns(2)
                q = col_sub1.number_input("數量", 0)
                cost = col_sub2.number_input("成本", 0)
                price = st.number_input("售價", 0)
                img = st.file_uploader("圖片", type=['jpg','png'])
                if st.form_submit_button("建立"):
                    if sku and name:
                        if sku in df['SKU'].tolist(): st.error("SKU 已存在")
                        else:
                            u = upload_image_to_imgbb(img) if img else ""
                            ws_items.append_row([sku, name, cat, size, q, price, cost, str(datetime.now()), u])
                            st.success("成功")
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
                        time.sleep(2)
                        st.rerun()
                    except: st.error("格式錯誤")
            
            with st.expander("QR Code"):
                t = st.selectbox("商品", df['SKU'].tolist())
                if t: st.image(generate_qr(t), width=100)

            st.markdown("---")
            d_s = st.selectbox("刪除商品", ["..."]+df['SKU'].tolist())
            if d_s != "..." and st.button("確認刪除"):
                ws_items.delete_rows(ws_items.find(d_s).row)
                st.success("已刪除")
                time.sleep(1)
                st.rerun()

    # Tab 4: 後台
    with tabs[3]:
        st.subheader("操作紀錄")
        st.dataframe(get_data_safe(ws_logs).sort_index(ascending=False).head(50), use_container_width=True)
        
        if st.session_state['user_role'] == 'Admin':
            st.markdown("---")
            st.subheader("管理員專區")
            if st.button("LINE 測試"):
                res = send_line_push("✅ V16.0 連線測試正常")
                if res=="SUCCESS": st.success("成功")
                else: st.error(res)
            
            with st.expander("人員管理"):
                st.dataframe(get_data_safe(ws_users))
                # (簡易版人員管理介面)
                action = st.radio("動作", ["新增/修改", "刪除"], horizontal=True)
                if action == "新增/修改":
                     n = st.text_input("帳號", key="u_n")
                     p = st.text_input("密碼", key="u_p")
                     r = st.selectbox("權限", ["Staff", "Admin"], key="u_r")
                     if st.button("儲存人員"):
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
                     if st.button("刪除人員"):
                         ws_users.delete_rows(ws_users.find(del_n).row)
                         st.success("已刪除")
                         time.sleep(1)
                         st.rerun()

if __name__ == "__main__":
    main()
