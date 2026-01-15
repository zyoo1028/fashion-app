import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, date
import time
import requests
import plotly.express as px
import base64
import hashlib
import math
import re
import random
import calendar
import matplotlib.pyplot as plt
import io
import matplotlib.font_manager as fm
import os

# --- 1. 系統全域設定 ---
st.set_page_config(
    page_title="IFUKUK ERP V110.0 MOBILE SUPREMACY", 
    layout="wide", 
    page_icon="🌏",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 【CSS 視覺核心：強制白底黑字 & 手機優化】
# ==========================================
st.markdown("""
    <style>
        /* 1. 強制全域白底黑字 (無視手機深色模式) */
        [data-testid="stAppViewContainer"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #F8F9FA !important;
        }
        [data-testid="stHeader"] {
            background-color: #FFFFFF !important;
        }
        
        /* 2. 強制輸入框、選單文字顏色 */
        .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {
            color: #000000 !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: #000000 !important;
            caret-color: #000000 !important;
            border-color: #E5E7EB !important;
        }
        /* 下拉選單選項顏色 */
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        /* 文字標籤 */
        label, .stMarkdown, h1, h2, h3, h4, h5, h6, p, span {
            color: #0f172a !important;
        }

        /* 3. 優化卡片視覺 (加強陰影與邊框，確保白底) */
        .pos-card, .inv-row, .finance-card, .metric-card, .cart-box, .mgmt-box {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
            color: #000000 !important;
        }
        
        .pos-img { width: 100%; height: 160px; object-fit: cover; background: #f9fafb; border-bottom: 1px solid #f3f4f6; }
        .pos-content { padding: 10px; flex-grow: 1; display: flex; flex-direction: column; }
        .pos-title { font-weight: bold; font-size: 1rem; margin-bottom: 4px; color: #111 !important; line-height: 1.3; }
        .pos-meta { font-size: 0.8rem; color: #666 !important; margin-bottom: 5px; }
        
        /* 庫存透視標籤 */
        .stock-tag-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; margin-bottom: 5px; }
        .stock-tag { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; border: 1px solid transparent; }
        .stock-tag.has-stock { background-color: #dcfce7 !important; color: #166534 !important; border-color: #bbf7d0; }
        .stock-tag.no-stock { background-color: #f3f4f6 !important; color: #9ca3af !important; border-color: #e5e7eb; }
        
        /* 庫存列表 */
        .inv-row { display: flex; align-items: start; gap: 12px; padding: 12px; border-radius: 12px; margin-bottom: 10px; }
        .inv-img { width: 90px; height: 90px; object-fit: cover; border-radius: 8px; flex-shrink: 0; background: #f1f5f9; }
        .inv-info { flex-grow: 1; }
        .inv-title { font-size: 1.1rem; font-weight: bold; color: #0f172a !important; margin-bottom: 4px; }
        
        /* 財務看板 */
        .finance-card { padding: 15px; text-align: center; border-radius: 10px; }
        .finance-val { font-size: 1.4rem; font-weight: 900; color: #0f172a !important; }
        .finance-lbl { font-size: 0.8rem; color: #64748b !important; font-weight: bold; }

        /* V110 排班表 CSS (Desktop & Mobile) */
        .roster-header { background: #f1f5f9 !important; padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e2e8f0; text-align: center; }
        
        /* Desktop View */
        .day-cell { border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; min-height: 100px; position: relative; margin-bottom: 5px; background: #fff !important; }
        .day-num { font-size: 0.8rem; font-weight: bold; color: #64748b; margin-bottom: 2px; padding-left: 4px; }
        
        /* Mobile List View */
        .mobile-day-row {
            background: #FFFFFF !important;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }
        .mobile-day-date {
            font-size: 1.1rem; font-weight: 900; color: #334155 !important;
            width: 50px; text-align: center; border-right: 2px solid #f1f5f9; margin-right: 10px;
        }
        .mobile-day-content { flex-grow: 1; }
        
        /* 班別膠囊 */
        .shift-pill { 
            font-size: 0.75rem; padding: 4px 8px; border-radius: 6px; 
            margin-bottom: 4px; color: white !important; display: inline-block; 
            text-align: center; font-weight: bold; margin-right: 4px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }

        /* 全店公休樣式 */
        .store-closed {
            background-color: #EF4444 !important; color: white !important;
            font-weight: 900; font-size: 0.9rem;
            display: flex; align-items: center; justify-content: center;
            height: 100%; border-radius: 6px; min-height: 90px;
        }
        .store-closed-mobile {
            background-color: #FEF2F2 !important; color: #EF4444 !important;
            border: 1px solid #FCA5A5; padding: 5px 10px; border-radius: 6px;
            font-weight: bold; display: inline-block;
        }
        
        /* 數據卡片強制白底 */
        .metric-card { background: linear-gradient(145deg, #ffffff, #f8fafc) !important; color: black !important; }
        .metric-value { color: #0f172a !important; }
        
        /* 按鈕樣式 */
        .stButton>button { border-radius: 8px; height: 3.
