import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- OMEGA 診斷模式 ---
st.set_page_config(page_title="OMEGA 結構診斷", layout="wide")

# 1. 連線設定
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ 找不到 Secrets 金鑰，無法診斷。")
        st.stop()
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    st.title("🛡️ OMEGA V103.0 雲端結構診斷")
    st.info("此程式正在讀取您的 Google Sheet 欄位順序...")

    try:
        client = get_connection()
        # V103.0 原始指定的 URL
        url = "https://docs.google.com/spreadsheets/d/1oCdUsYy8AGp8slJyrlYw2Qy2POgL2eaIp7_8aTVcX3w/edit?gid=1626161493#gid=1626161493"
        sh = client.open_by_url(url)
        
        # V103.0 預期的標準結構 (絕對鐵律)
        v103_expectations = {
            "Items": ["SKU", "Name", "Category", "Size", "Qty", "Price", "Cost", "Last_Updated", "Image_URL", "Safety_Stock", "Orig_Currency", "Orig_Cost", "Qty_CN"],
            "Logs": ["Timestamp", "User", "Action", "Details"],
            "Users": ["Name", "Password", "Role", "Status", "Created_At"]
        }

        # 檢查每一個工作表
        all_sheets = sh.worksheets()
        
        for ws in all_sheets:
            title = ws.title
            headers = ws.row_values(1) # 讀取第一列
            
            st.divider()
            st.subheader(f"📂 工作表: {title}")
            st.write(f"📊 目前您的 Sheet 實際欄位 ({len(headers)}欄):")
            st.code(str(headers), language="json")
                
            if title in v103_expectations:
                expected = v103_expectations[title]
                st.write(f"🎯 V103.0 要求的正確欄位 ({len(expected)}欄):")
                st.code(str(expected), language="json")
                
                # 比對邏輯
                if headers == expected:
                    st.success(f"✅ {title} 結構完美！無需調整。")
                else:
                    st.error(f"❌ {title} 結構不符！(這是問題所在)")
                    
                    # 幫 Boss 找出具體是第幾欄錯了
                    for i, (real, exp) in enumerate(zip(headers, expected)):
                        if real != exp:
                            st.markdown(f"🔴 **第 {i+1} 欄錯誤**：您的是 `{real}`，但 V103 需要 `{exp}`")
                            
                    # 檢查長度
                    if len(headers) < len(expected):
                        st.warning(f"⚠️ 警告：您的欄位太少，缺了 {len(expected)-len(headers)} 欄")
                    elif len(headers) > len(expected):
                        st.warning(f"⚠️ 警告：您的欄位太多，多了 {len(headers)-len(expected)} 欄")

    except Exception as e:
        st.error(f"連線失敗: {e}")

if __name__ == "__main__":
    main()
