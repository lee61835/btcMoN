import streamlit as st
import pandas as pd
import ccxt
import time
from datetime import datetime

# --- 1. 初始化交易所 (使用 Bybit 绕过 IP 限制) ---
def init_exchanges():
    # Bybit 节点对云服务器最友好，数据与币安同步率 99%
    bybit = ccxt.bybit({'options': {'defaultType': 'linear'}}) 
    # Coinbase 依然可用
    cb = ccxt.coinbase()
    return bybit, cb

# --- 2. 抓取数据逻辑 ---
def fetch_data(bybit_ex, cb_ex):
    try:
        # 1. 获取 Bybit 合约数据 (包含价格、24h成交量)
        f_ticker = bybit_ex.fetch_ticker('BTC/USDT:USDT')
        
        # 2. 获取 Bybit 实时持仓量 (OI)
        oi_resp = bybit_ex.publicLinearGetPublicOpenInterestValue({'symbol': 'BTCUSDT', 'period': '5min'})
        oi_value = float(oi_resp['result'][0]['open_interest'])
        
        # 3. 获取 Coinbase 现货价格 (作为机构锚点)
        cb_ticker = cb_ex.fetch_ticker('BTC/USD')
        
        # Bybit 现货价格 (用于计算基差)
        # 注意：Bybit 的合约价格与现货价格在 ticker 里都有
        s_price = float(f_ticker['last']) * 0.9998 # 模拟细微现货价差，或直接取其 index_price
        index_price = float(f_ticker['info']['index_price']) # 这是最硬的现货参考价
        
        return {
            "s_price": index_price,
            "f_price": float(f_ticker['last']),
            "cb_price": float(cb_ticker['last']),
            "oi": oi_value,
            "f_vol": float(f_ticker['quoteVolume']),
            "time": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        st.error(f"📡 正在重新连接全网节点... (错误提示: {e})")
        return None

# --- 3. UI 布局 ---
st.set_page_config(page_title="BTC 全网硬核指标", layout="wide")
st.title("🛡️ BTC 全网资金压力仪表盘 (Bybit 强力驱动)")
st.caption("基于 Bybit & Coinbase 实时数据 | 绕过地域限制方案")

s_ex, c_ex = init_exchanges()
data = fetch_data(s_ex, c_ex)

if data:
    # 核心指标计算
    basis = (data['f_price'] - data['s_price']) / data['s_price'] * 100
    cb_prem = (data['cb_price'] - data['s_price']) / data['s_price'] * 100
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("合约价格", f"${data['f_price']:,}")
        st.metric("基差率 (Basis%)", f"{basis:.4f}%")
    with col2:
        st.metric("全网持仓 (OI)", f"{data['oi']/1000000:.2f}M USDT")
        st.metric("美资溢价 (CB)", f"{cb_prem:.4f}%")
    with col3:
        st.metric("当前成交额", f"${data['f_vol']/1000000:.1f}M")
        status = "多头拥挤" if basis > 0.08 else "空头洗盘" if basis < -0.02 else "震荡中"
        st.metric("市场状态", status)

    # 风险诊断
    st.divider()
    if basis > 0.12:
        st.error("🚨 警告：基差过高，清算风险正在积聚！")
    elif basis < -0.05:
        st.success("✅ 信号：基差转负，多头已清洗干净。")

    st.info(f"最后刷新: {data['time']} (由于 Bybit API 限制，建议刷新频率设为 10s 以上)")
    
    time.sleep(10)
    st.rerun()
