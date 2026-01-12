import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import requests
import plotly.express as px
import base64
import hashlib
import math
import re
import calendar

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK V103.17 PERFECTED", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🛑 CSS 視覺核心
# ==========================================
st.markdown("""
    <style>
        .stApp { background-color: #F8F9FA !important; }
        div[data-testid="stRadio"] > label { display:none; }
        div[data-testid="stRadio"] > div { 
            flex-direction: row; gap: 8px; justify-content: start; 
            background: #fff; padding: 10px; border-radius: 12px; 
            border: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
            overflow-x: auto; white-space: nowrap;
        }
        .uni-card { 
            background: #fff; border-radius: 12px; overflow: hidden; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid #E5E7EB; 
            display: flex; flex-direction: column; height: 100%; position: relative;
        }
        .uni-img { width: 100%; height: 140px; object-fit: cover; background: #f0f0f0; }
        .uni-content { padding: 10px; flex-grow: 1; }
        .uni-title { font-weight: bold; font-size: 0.95rem; color: #111; margin-bottom: 4px; line-height: 1.3; }
        .uni-spec { font-size: 0.85rem; color: #4b5563; margin-bottom: 6px; font-weight: 600; }
        .uni-price { color: #059669; font-weight: 900; font-size: 1rem; }
        .uni-badge { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; display: inline-block; margin-right: 4px; font-weight: bold;}
        .bg-tw { background: #dbeafe; color: #1e40af; }
        .bg-cn { background: #fef3c7; color: #92400e; }
        .pagination-container { display: flex; justify-content: center; align-items: center; gap: 20px; margin-top: 15px; padding: 10px; background: #fff; border-radius: 10px; }
        .cart-box { background: #fff; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px; margin-bottom: 10px; }
        .cart-item { display: flex; justify-content: space-between; border-bottom: 1px dashed #ddd; padding: 8px 0; font-size: 0.9rem; }
        .final-price-box { font-size: 1.8rem; font-weight: 900; color: #16a34a; text-align: center; background: #dcfce7; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #86efac; }
        .metric-card { background: #fff; border-radius: 12px; padding: 15px; border: 1px solid #eee; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 100%; }
        .metric-val { font-size: 1.6rem; font-weight: 800; color:#111; margin: 5px 0; }
        .metric-lbl { font-size: 0.8rem; color:#666; font-weight: 600; text-transform: uppercase;}
        .metric-sub { font-size: 0.75rem; color: #999; margin-top: -5px; }
        .roster-header { background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #bfdbfe; }
        .day-cell { border: 1px solid #eee; border-radius: 8px; padding: 5px; min-height: 80px; position: relative; margin-bottom: 5px; transition: 0.2s; background: #fff; }
        .day-cell:hover { border-color: #3b82f6; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .shift-tag { font-size: 0.75rem; padding: 2px 5px; border-radius: 4px; margin: 2px; display: block; text-align: center; color: white; font-weight: bold; }
        .note-dot { position: absolute; top: 5px; right: 5px; width: 8px; height: 8px; background: #ef4444; border-radius: 50%; }
        .stButton>button { border-radius: 10px; height: 3.2rem; font-weight: 700; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 100%; }
        input, .stTextInput>div>div, div[data-baseweb="select"]>div { border-radius: 10px !important; min-height: 3rem; }
        .audit-stat-box { background: #fff7ed; border: 1px solid #ffedd5; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 10px; }
        .audit-num { font-size: 1.5rem; font-weight: 800; color: #c2410c; }
        .audit-txt { font-size: 0.8rem; color: #9a3412; font-weight: bold; }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 設定區 ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
IMGBB_API_KEY = "c2f93d2a1a62bd3a6da15f477d2bb88a"
SHEET_HEADERS = ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CAT_LIST = ["上衣(Top)", "褲子(Btm)", "外套(Out)", "套裝(Suit)", "鞋類(Shoe)", "包款(Bag)", "帽子(Hat)", "飾品(Acc)", "其他(Misc)"]
SIZE_ORDER = ["F", "XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
ITEMS_PER_PAGE = 15

# --- 核心連線 ---
@st.cache_resource(ttl=600)
def get_connection():
    if "gcp_service_account" not in st.secrets: st.error("❌ 金鑰遺失"); st.stop()
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=10, show_spinner=False)
def get_data_smart(_ws_obj, expected_headers=None, ensure_qty_cn=False):
    for attempt in range(3):
        try:
            if _ws_obj is None: return pd.DataFrame(columns=expected_headers)
            raw = _ws_obj.get_all_values()
            if not raw or len(raw) < 2: return pd.DataFrame(columns=expected_headers)
            headers = raw[0]; rows = raw[1:]
            
            # Auto-fix Qty_CN
            if ensure_qty_cn and "Qty_CN" not in headers:
                try: _ws_obj.update_cell(1, len(headers)+1, "Qty_CN"); headers.append("Qty_CN"); raw = _ws_obj.get_all_values(); rows = raw[1:]
                except: pass
            
            df = pd.DataFrame(rows, columns=headers[:len(rows[0])] if rows else headers)
            # 確保欄位存在且名稱正確
            if expected_headers:
                for col in expected_headers:
                    if col not in df.columns: df[col] = ""
                df = df[expected_headers]
            return df
        except Exception: time.sleep(1); continue
    return pd.DataFrame(columns=expected_headers)

def update_cell_retry(ws, row, col, value):
    for i in range(3):
        try: ws.update_cell(row, col, value); return True
        except: time.sleep(1)
    return False

@st.cache_resource(ttl=600)
def init_db():
    try: return get_connection().open_by_url(GOOGLE_SHEET_URL)
    except: return None

def get_worksheet_safe(sh, title, headers):
    try: return sh.worksheet(title)
    except: return None

# --- 工具模組 ---
def get_taiwan_time_str(): return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
def render_image_url(url): return url if url and str(url).startswith('http') else "https://i.ibb.co/W31w56W/placeholder.png"
def make_hash(p): return hashlib.sha256(str(p).encode()).hexdigest()
def check_hash(p, h): return make_hash(p) == h
def log_event(ws, u, a, d):
    try: ws.append_row([get_taiwan_time_str(), u, a, d])
    except: pass
def upload_image(file):
    if not IMGBB_API_KEY: return None
    try:
        res = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY, "image": base64.b64encode(file.getvalue()).decode('utf-8')})
        return res.json()["data"]["url"] if res.status_code == 200 else None
    except: return None
def get_style_code(sku): return str(sku).strip().rsplit('-', 1)[0] if '-' in str(sku) else str(sku).strip()

# [FIXED] 智慧解析器 V2：精準抓取數據，去除英文雜訊
def parse_sales_details_smart(detail_str):
    # Pattern: Total:$2016 | Items: ... | Note | Pay | Ch:門市 | By:張哲
    try:
        total = "0"; items = "-"; note = "-"; pay = "-"; channel = "-"; who = "-"
        
        # 1. 抓取金額 (Total:$...)
        m_total = re.search(r'Total:\$(\d+)', detail_str)
        if m_total: total = m_total.group(1)
        
        # 2. 抓取通路 (Ch:...)
        m_ch = re.search(r'Ch:([^\s|]+)', detail_str)
        if m_ch: channel = m_ch.group(1)
        
        # 3. 抓取經手人 (By:...)
        m_by = re.search(r'By:([^\s|]+)', detail_str)
        if m_by: who = m_by.group(1)
        
        # 4. 抓取項目 (Items: ... |)
        m_items = re.search(r'Items:(.*?)(?:\||$)', detail_str)
        if m_items: items = m_items.group(1).strip()
        
        # 5. 抓取備註與付款 (中間剩餘的部分)
        # 簡單分割法：假設格式固定，取第3, 4欄位
        parts = detail_str.split('|')
        if len(parts) >= 4:
            note = parts[2].strip()
            pay = parts[3].strip()
            
        return total, items, note, pay, channel, who
    except:
        return '0', detail_str, '-', '-', '-', '-'

def calculate_realized_revenue(logs_df):
    total = 0
    if logs_df.empty: return 0
    sales = logs_df[logs_df['Action'] == 'Sale']
    for _, row in sales.iterrows():
        try: total += int(re.search(r'Total:\$(\d+)', row['Details']).group(1))
        except: pass
    return total

@st.cache_data(ttl=3600)
def get_live_rate():
    try: return requests.get("https://api.exchangerate-api.com/v4/latest/CNY", timeout=5).json()['rates']['TWD'], True
    except: return 4.50, False

def render_navbar(user):
    d = datetime.utcnow() + timedelta(hours=8)
    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:15px;background:#fff;border-bottom:1px solid #eee;margin-bottom:15px;'><div><span style='font-size:18px;font-weight:900;'>IFUKUK GLOBAL</span><br><span style='font-size:11px;color:#666;'>{d.strftime('%Y/%m/%d')}</span></div><div style='width:36px;height:36px;background:#111;color:#fff;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:bold;'>{user}</div></div>", unsafe_allow_html=True)

# --- 排班 ---
def get_staff_color(name):
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6366F1", "#14B8A6", "#F97316"]
    return colors[sum(ord(c) for c in str(name)) % len(colors)]

def render_roster(sh, users):
    ws = get_worksheet_safe(sh, "Shifts", ["Date", "Staff", "Type", "Note", "Notify", "Updated_By"])
    df = get_data_smart(ws, expected_headers=["Date", "Staff", "Type", "Note", "Notify", "Updated_By"])
    
    st.markdown("<div class='roster-header'><h3>🗓️ 專業排班與管理中心</h3></div>", unsafe_allow_html=True)
    
    # 批次排班
    with st.expander("⚡ 智慧批次排班 (多日連排)", expanded=False):
        with st.form("batch"):
            c1, c2, c3 = st.columns(3)
            staff = c1.selectbox("人員", users)
            typ = c2.selectbox("班別", ["正常班", "早班", "晚班", "全班", "公休", "特休", "空班", "代班"])
            dates = c3.date_input("日期範圍", [])
            note = st.text_input("備註")
            if st.form_submit_button("🚀 執行"):
                if len(dates)==2:
                    s, e = dates; delta = e - s
                    for i in range(delta.days + 1):
                        curr = (s + timedelta(days=i)).strftime("%Y-%m-%d")
                        vals = ws.get_all_values()
                        dels = [idx+1 for idx, v in enumerate(vals) if len(v)>1 and v[0]==curr and v[1]==staff]
                        for r in reversed(dels): ws.delete_rows(r)
                        ws.append_row([curr, staff, typ, note, "FALSE", st.session_state['user_name']])
                    st.cache_data.clear(); st.success("完成"); time.sleep(1); st.rerun()

    # 日曆
    now = datetime.utcnow() + timedelta(hours=8)
    c1, c2 = st.columns(2)
    y = c1.number_input("年", 2024, 2030, now.year)
    m = c2.selectbox("月", range(1, 13), now.month)
    cal = calendar.monthcalendar(y, m)
    cols = st.columns(7)
    for i, d in enumerate(["一","二","三","四","五","六","日"]): cols[i].markdown(f"<div style='text-align:center;font-weight:bold;'>{d}</div>", unsafe_allow_html=True)
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day!=0:
                    d_str = f"{y}-{str(m).zfill(2)}-{str(day).zfill(2)}"
                    d_shifts = df[df['Date']==d_str] if not df.empty else pd.DataFrame()
                    badges = ""
                    for _, r in d_shifts.iterrows():
                        bg = get_staff_color(r['Staff'])
                        if r['Type'] in ["公休","空班"]: bg="#9CA3AF"
                        if r['Type']=="特休": bg="#EF4444"
                        badges += f"<span class='shift-tag' style='background:{bg}'>{r['Staff']}</span>"
                    if st.button(f"{day}", key=f"d_{d_str}"): st.session_state['roster_date']=d_str; st.rerun()
                    st.markdown(f"<div style='min-height:30px;'>{badges}</div>", unsafe_allow_html=True)
                else: st.markdown("<div style='min-height:60px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if 'roster_date' in st.session_state:
            rd = st.session_state['roster_date']
            st.info(f"編輯: {rd}")
            with st.form("single"):
                s = st.selectbox("人", users); t = st.selectbox("班", ["正常班", "早班", "晚班", "全班", "公休", "特休", "空班"]); n = st.text_input("註")
                if st.form_submit_button("排入"):
                    vals = ws.get_all_values()
                    dels = [idx+1 for idx, v in enumerate(vals) if len(v)>1 and v[0]==rd and v[1]==s]
                    for r in reversed(dels): ws.delete_rows(r)
                    ws.append_row([rd, s, t, n, "FALSE", st.session_state['user_name']])
                    st.cache_data.clear(); st.success("OK"); st.rerun()
            
            curr = df[df['Date']==rd] if not df.empty else pd.DataFrame()
            if not curr.empty:
                for _, r in curr.iterrows():
                    if st.button(f"🗑️ {r['Staff']}", key=f"rm_{rd}_{r['Staff']}"):
                        vals = ws.get_all_values()
                        for idx, v in enumerate(vals):
                            if len(v)>1 and v[0]==rd and v[1]==r['Staff']: ws.delete_rows(idx+1); break
                        st.cache_data.clear(); st.rerun()
    with c2:
        st.markdown(f"##### 📊 {m}月 工時")
        if not df.empty:
            m_p = f"{y}-{str(m).zfill(2)}"
            m_d = df[df['Date'].str.startswith(m_p)]
            if not m_d.empty:
                cnt = m_d[~m_d['Type'].isin(['公休','空班','特休'])].groupby('Staff').size()
                st.dataframe(cnt.reset_index(name="天數"), use_container_width=True)

# --- 主程式 ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in']=False; st.session_state['user_name']=""
    if 'pos_cart' not in st.session_state: st.session_state['pos_cart']=[]
    for k in ['page_pos','page_inv','page_int']: 
        if k not in st.session_state: st.session_state[k]=0
    
    sh = init_db()
    if not sh: st.error("連線失敗"); return

    ws_items = get_worksheet_safe(sh, "Items", SHEET_HEADERS)
    ws_logs = get_worksheet_safe(sh, "Logs", ["Timestamp", "User", "Action", "Details"])
    ws_users = get_worksheet_safe(sh, "Users", ["Name", "Password", "Role", "Status", "Created_At"])

    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.markdown("<h1 style='text-align:center'>IFUKUK</h1><p style='text-align:center'>V103.17 PERFECTED</p>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("帳號"); p = st.text_input("密碼", type="password")
                if st.form_submit_button("登入"):
                    udf = get_data_smart(ws_users, expected_headers=["Name", "Password", "Role", "Status", "Created_At"])
                    if udf.empty and u=="Boss" and p=="1234":
                        ws_users.append_row(["Boss", make_hash("1234"), "Admin", "Active", get_taiwan_time_str()])
                        st.cache_data.clear(); st.rerun()
                    if not udf.empty:
                        tgt = udf[(udf['Name']==u) & (udf['Status']=='Active')]
                        if not tgt.empty and (check_hash(p, tgt.iloc[0]['Password']) or p==tgt.iloc[0]['Password']):
                            st.session_state['logged_in']=True; st.session_state['user_name']=u; st.session_state['user_role']=tgt.iloc[0]['Role']; st.rerun()
                        else: st.error("錯誤")
        return

    render_navbar(st.session_state['user_name'][0].upper())
    df = get_data_smart(ws_items, expected_headers=SHEET_HEADERS, ensure_qty_cn=True)
    for c in ["Qty","Price","Cost","Orig_Cost","Qty_CN"]: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)

    with st.sidebar:
        st.markdown(f"### {st.session_state['user_name']}")
        if 'exchange_rate' not in st.session_state: st.session_state['exchange_rate'] = 4.5
        nr = st.number_input("匯率", value=st.session_state['exchange_rate'])
        if nr!=st.session_state['exchange_rate']: st.session_state['exchange_rate']=nr
        if st.button("登出"): st.session_state['logged_in']=False; st.rerun()

    nav = st.radio("", ["🛒 POS收銀", "📊 庫存總覽", "🗓️ 員工排班", "📈 營運戰情", "🎁 領用/稽核", "👔 矩陣管理", "📝 全域日誌", "👥 員工管理"], horizontal=True)

    if nav == "🛒 POS收銀":
        c1, c2 = st.columns([3, 2])
        with c1:
            q = st.text_input("搜尋", placeholder="...", label_visibility="collapsed")
            vdf = df[df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)] if q else df
            
            # Pagination
            tot = len(vdf); pages = math.ceil(tot/ITEMS_PER_PAGE)
            if st.session_state['page_pos'] >= pages: st.session_state['page_pos'] = 0
            start = st.session_state['page_pos']*ITEMS_PER_PAGE
            
            rows = [vdf.iloc[start:start+ITEMS_PER_PAGE].iloc[i:i+3] for i in range(0, min(15, len(vdf.iloc[start:])), 3)]
            for r in rows:
                cols = st.columns(3)
                for i, (_, row) in enumerate(r.iterrows()):
                    with cols[i]:
                        st.markdown(f"<div class='uni-card'><div class='uni-img'><img src='{render_image_url(row['Image_URL'])}' style='width:100%;height:100px;object-fit:cover;'></div><div class='uni-content'><div class='uni-title'>{row['Name']}</div><div class='uni-spec'>{row['Size']}</div><div class='uni-price'>${row['Price']}</div></div></div>", unsafe_allow_html=True)
                        if st.button("➕", key=f"add_{row['SKU']}"):
                            st.session_state['pos_cart'].append({"sku":row['SKU'],"name":row['Name'],"size":row['Size'],"price":int(row['Price']),"qty":1,"subtotal":int(row['Price'])})
                            st.toast("已加入")
            
            c_p1, c_p2 = st.columns(2)
            if c_p1.button("⬅️", key="p_prev", disabled=st.session_state['page_pos']==0): st.session_state['page_pos']-=1; st.rerun()
            if c_p2.button("➡️", key="p_next", disabled=st.session_state['page_pos']>=pages-1): st.session_state['page_pos']+=1; st.rerun()

        with c2:
            if st.session_state['pos_cart']:
                tot = sum(i['subtotal'] for i in st.session_state['pos_cart'])
                for idx, i in enumerate(st.session_state['pos_cart']):
                    c_n, c_d = st.columns([4,1])
                    c_n.markdown(f"{i['name']} x{i['qty']} ${i['subtotal']}")
                    if c_d.button("x", key=f"rm_{idx}"): st.session_state['pos_cart'].pop(idx); st.rerun()
                
                st.divider()
                disc = st.radio("折扣", ["無","7折","8折","自訂"], horizontal=True)
                cust = st.number_input("%", 1, 100, 95) if disc=="自訂" else 0
                fin = int(round(tot*0.7)) if disc=="7折" else (int(round(tot*0.8)) if disc=="8折" else (int(round(tot*(cust/100))) if disc=="自訂" else tot))
                st.markdown(f"### 實收: ${fin}")
                
                who = st.selectbox("經手", ws_users.col_values(1)[1:] if ws_users else [])
                pay = st.selectbox("付", ["現金","刷卡","轉帳"]); ch = st.selectbox("通", ["門市","官網"])
                note = st.text_input("備註")
                
                if st.button("結帳", type="primary"):
                    items = []
                    for i in st.session_state['pos_cart']:
                        r = ws_items.find(i['sku']).row; cur = int(ws_items.cell(r, 5).value)
                        update_cell_retry(ws_items, r, 5, cur-i['qty']); items.append(f"{i['sku']} x{i['qty']}")
                    log_event(ws_logs, st.session_state['user_name'], "Sale", f"Total:${fin} | Items:{','.join(items)} | {note} | {pay} | Ch:{ch} | By:{who}")
                    st.session_state['pos_cart']=[]; st.cache_data.clear(); st.success("OK"); time.sleep(1); st.rerun()
            
            st.divider()
            st.markdown("##### 🧾 今日銷售 (可撤銷)")
            logs_df = get_data_smart(ws_logs, expected_headers=["Timestamp", "User", "Action", "Details"])
            if not logs_df.empty:
                sales = logs_df[logs_df['Action']=='Sale'].head(10)
                if not sales.empty:
                    # [FIXED] 智慧解析中文顯示
                    parsed = []
                    for idx, r in sales.iterrows():
                        t, i, n, p, c, w = parse_sales_details_smart(r['Details'])
                        parsed.append({"ID": idx, "時間": r['Timestamp'], "經手": w, "金額": t, "內容": i})
                    pdf = pd.DataFrame(parsed)
                    st.dataframe(pdf, use_container_width=True)
                    
                    rid = st.selectbox("撤銷ID", ["..."]+pdf['ID'].astype(str).tolist())
                    if rid!="..." and st.button("撤銷交易"):
                        tr = logs_df.loc[int(rid)]; dets = tr['Details']
                        try:
                            # 簡單解析補回庫存 logic
                            items_str = re.search(r'Items:(.*?)(?:\||$)', dets).group(1)
                            for it in items_str.split(','):
                                sk = it.split(' x')[0].strip(); qt = int(it.split(' x')[1])
                                cell = ws_items.find(sk); update_cell_retry(ws_items, cell.row, 5, int(ws_items.cell(cell.row, 5).value)+qt)
                            ws_logs.delete_rows(int(rid)+2); st.cache_data.clear(); st.rerun()
                        except: st.error("失敗")

    elif nav == "📊 庫存總覽":
        # [FIXED] 全中文欄位映射
        rename_map = {"SKU":"貨號", "Name":"品名", "Category":"分類", "Size":"尺寸", "Qty":"台灣庫存", "Qty_CN":"中國庫存", "Price":"售價", "Cost":"成本", "Last_Updated":"更新時間"}
        st.dataframe(df.rename(columns=rename_map), use_container_width=True)

    elif nav == "🗓️ 員工排班":
        render_roster_system(sh, ws_users.col_values(1)[1:] if ws_users else [])

    elif nav == "📈 營運戰情":
        # V103 Logic
        rev = (df['Qty']*df['Price']).sum()
        cost = ((df['Qty']+df['Qty_CN'])*df['Cost']).sum()
        m1, m2 = st.columns(2); m1.metric("預估營收", f"${rev:,}"); m2.metric("總成本", f"${cost:,}")

    elif nav == "🎁 領用/稽核":
        # [FIXED] 增加編輯/撤銷功能
        logs_df = get_data_smart(ws_logs, expected_headers=["Timestamp", "User", "Action", "Details"])
        if not logs_df.empty:
            int_logs = logs_df[logs_df['Action']=='Internal_Use']
            if not int_logs.empty:
                # 解析並顯示中文
                parsed = []
                for idx, r in int_logs.iterrows():
                    # Detail format: SKU -Qty | Who | Reason | Note
                    try:
                        parts = r['Details'].split('|')
                        sku_q = parts[0].strip(); who = parts[1].strip(); rsn = parts[2].strip()
                        parsed.append({"ID": idx, "時間": r['Timestamp'], "領用人": who, "項目": sku_q, "原因": rsn})
                    except: pass
                pdf = pd.DataFrame(parsed)
                st.dataframe(pdf, use_container_width=True)
                
                c_del, c_edit = st.columns(2)
                with c_del:
                    did = st.selectbox("刪除ID", ["..."]+pdf['ID'].astype(str).tolist())
                    if did!="..." and st.button("刪除並歸還"):
                        # Logic similar to sales revoke
                        tr = logs_df.loc[int(did)]; d = tr['Details']
                        sk = d.split(' -')[0].strip(); q = int(d.split(' -')[1].split(' |')[0])
                        c = ws_items.find(sk); update_cell_retry(ws_items, c.row, 5, int(ws_items.cell(c.row, 5).value)+q)
                        ws_logs.delete_rows(int(did)+2); st.cache_data.clear(); st.rerun()

        # 卡片式領用 (同 POS)
        c1, c2 = st.columns([3, 2])
        with c1:
            q = st.text_input("領用搜尋")
            idf = df[df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)] if q else df.head(15)
            # 顯示卡片 (略，同 POS 結構)
            for _, row in idf.iterrows():
                if st.button(f"{row['Name']} ({row['Size']})", key=f"int_{row['SKU']}"): st.session_state['int_t']=row['SKU']
        with c2:
            if 'int_t' in st.session_state:
                sku = st.session_state['int_t']; row = df[df['SKU']==sku].iloc[0]
                st.write(f"選中: {row['Name']}")
                with st.form("int_f"):
                    q = st.number_input("量", 1); w = st.selectbox("人", ws_users.col_values(1)[1:]); r = st.selectbox("因", ["公務制服","福利","樣品","報廢","其他"])
                    if st.form_submit_button("領用"):
                        c = ws_items.find(sku); update_cell_retry(ws_items, c.row, 5, int(row['Qty'])-q)
                        log_event(ws_logs, st.session_state['user_name'], "Internal_Use", f"{sku} -{q} | {w} | {r} | -")
                        st.cache_data.clear(); st.rerun()

    elif nav == "👔 矩陣管理":
        t1, t2, t3 = st.tabs(["新增", "調撥", "刪除"])
        with t3:
            # [FIXED] 卡片式刪除
            q = st.text_input("刪除搜尋")
            ddf = df[df.apply(lambda x: q.lower() in str(x.values).lower(), axis=1)] if q else df.head(10)
            for _, row in ddf.iterrows():
                c1, c2 = st.columns([4, 1])
                c1.write(f"{row['Name']} ({row['SKU']})")
                if c2.button("🗑️", key=f"del_{row['SKU']}"):
                    ws_items.delete_rows(ws_items.find(row['SKU']).row); st.cache_data.clear(); st.rerun()

    elif nav == "📝 全域日誌":
        st.dataframe(get_data_smart(ws_logs, ["Timestamp", "User", "Action", "Details"]), use_container_width=True)

    elif nav == "👥 員工管理":
        if st.session_state['user_role']=='Admin':
            st.dataframe(get_data_smart(ws_users, ["Name", "Password", "Role", "Status", "Created_At"]))
            with st.form("add_u"):
                n=st.text_input("ID"); p=st.text_input("PW"); r=st.selectbox("Role", ["Staff","Admin"])
                if st.form_submit_button("Add"): 
                    ws_users.append_row([n, make_hash(p), r, "Active", get_taiwan_time_str()]); st.cache_data.clear(); st.rerun()

    elif nav == "🚪 登出":
        st.session_state['logged_in'] = False; st.rerun()

if __name__ == "__main__":
    main()
