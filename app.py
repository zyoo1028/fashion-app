import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import requests
import plotly.express as px
import base64
import qrcode
import hashlib
from io import BytesIO

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK 企業資源中樞", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【MATRIX-V32.4 視覺與核心修復補丁】
# ==========================================
st.markdown("""
    <style>
        /* --- 1. 全局基礎鎖定 (白底黑字) --- */
        .stApp { background-color: #FFFFFF !important; }
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; border-right: 1px solid #E5E7EB; }
        h1, h2, h3, h4, h5, h6, p, span, div, label, li { color: #000000 !important; }
        
        /* --- 2. 輸入框與顯示框基礎樣式 --- */
        input, textarea, .stTextInput > div > div, .stNumberInput > div > div {
            color: #000000 !important;
            background-color: #F3F4F6 !important;
            border-color: #D1D5DB !important;
        }
        /* Selectbox 未展開時的顯示框 */
        div[data-baseweb="select"] > div {
            background-color: #F3F4F6 !important;
            color: #000000 !important;
            border-color: #D1D5DB !important;
        }

        /* ========================================================================
           3. [關鍵修復] 下拉選單 (Selectbox) 彈出視窗
           ======================================================================== */
        /* 強制所有彈出視窗容器為白底黑字 */
        div[data-baseweb="popover"], div[data-baseweb="menu"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #E5E7EB !important;
        }
        /* 選項列表容器 */
        ul[role="listbox"] {
            background-color: #FFFFFF !important;
        }
        /* 每一個選項 (Option) */
        li[role="option"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        /* 選項內的文字容器 */
        li[role="option"] div {
            color: #000000 !important;
        }
        /* 滑鼠滑過或選中時的狀態 (淺灰底黑字) */
        li[role="option"]:hover, li[role="option"][aria-selected="true"] {
            background-color: #F3F4F6 !important;
            color: #000000 !important;
        }

        /* ========================================================================
           4. [關鍵修復] 日期選擇器 (Date Picker) 彈出視窗
           ======================================================================== */
        /* 鎖定日期選擇器的彈出層容器 */
        div[data-testid="stDateInput"] > div:nth-of-type(2) > div {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #E5E7EB !important;
        }
        /* 日曆 Header */
        div[data-testid="stDateInput"] div[class*="CalendarHeader"] {
            color: #000000 !important;
        }
        div[data-testid="stDateInput"] button[aria-label="Previous month"],
        div[data-testid="stDateInput"] button[aria-label="Next month"] {
             color: #000000 !important;
        }
        /* 星期幾的標題 */
        div[data-testid="stDateInput"] div[class*="WeekDays"] {
            color: #666666 !important;
        }
        /* 日曆內的日期按鈕 */
        div[data-testid="stDateInput"] button[role="gridcell"] {
            color: #000000 !important;
            background-color: #FFFFFF !important;
        }
        /* 滑鼠滑過日期 */
        div[data-testid="stDateInput"] button[role="gridcell"]:hover {
             background-color: #F3F4F6 !important;
        }
        /* 被選中的日期 */
        div[data-testid="stDateInput"] button[role="gridcell"][aria-selected="true"] {
             background-color: #FF4B4B !important;
             color: #FFFFFF !important;
        }
        /* 今天日期 */
        div[data-testid="stDateInput"] button[role="gridcell"][tabindex="0"]:not([aria-selected="true"]) {
             color: #FF4B4B !important;
             font-weight: bold;
        }

        /* --- 5. 其他元件樣式 --- */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            display: block !important;
            z-index: 9999 !important;
        }
        .block-container {
            padding-top: 6rem !important; 
            padding-bottom: 5rem !important;
        }

        .navbar-container {
            position: fixed;
            top: 50px; left: 0; width: 100%; z-index: 99;
            background-color: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(12px);
            padding: 12px 24px;
            border-bottom: 1px solid #e0e0e0;
            display: flex; justify-content: space-between; align-items: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        }

        .metric-card {
            background: linear-gradient(145deg, #ffffff, #f5f7fa); 
            border-radius: 16px; padding: 20px;
            border: 1px solid #e1e4e8; text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 10px; transition: all 0.2s;
            position: relative; overflow: hidden;
        }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(0,0,0,0.06); }
        .metric-value { font-size: 2rem; font-weight: 800; margin: 8px 0; color:#111 !important; letter-spacing: -0.5px; }
        .
