import streamlit as st
import pandas as pd
import ccxt
import time
from datetime import datetime

def init_exchanges():
    # 使用 binance.vision 或 data-api 这种开发者专用且限制较少的节点
    binance_spot = ccxt.binance({
        'urls': {
            'api': {
                'public': 'https://data-api.binance.vision',
                'private': 'https://data-api.binance.vision',
            }
        },
        'options': {'defaultType': 'spot'}
    })
    
    binance_future = ccxt.binance({
        'urls': {
            'api': {
                'public': 'https://fapi.binance.com',
                'fapiPublic': 'https://fapi.binance.com',
            }
        },
        'options': {'defaultType': 'future'}
    })
    
    cb = ccxt.coinbase()
    return binance_spot, binance_future, cb

# --- 2. 数据抓取逻辑 (带容错) ---
def fetch_data(spot_ex, fut_ex, cb_ex):
    try:
        # 获取现货 (Binance)
        s_ticker = spot_ex.fetch_ticker('BTC/USDT')
        # 获取合约 (Binance)
        f_ticker = fut_ex.fetch_ticker('BTC/USDT')
        # 获取持仓量 (通过合约接口)
        oi_resp = fut_ex.fapiPublicGetOpenInterest({'symbol': 'BTCUSDT'})
        # 获取 Coinbase 现货
        cb_ticker = cb_ex.fetch_ticker('BTC/USD')
        
        return {
            "s_price": float(s_ticker['last']),
            "f_price": float(f_ticker['last']),
            "cb_price": float(cb_ticker['last']),
            "oi": float(oi_resp['openInterest']),
            "s_vol": float(s_ticker['quoteVolume']),
            "f_vol": float(f_ticker['quoteVolume']),
            "time": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        st.error(f"⚠️ 节点连接中... 请稍候 (错误详情: {e})")
        return None

# --- 3. UI 布局 ---
st.set_page_config(page_title="BTC 硬核监控", layout="wide")
st.title("🛡️ BTC 全网资金压力仪表盘")

# 初始化
s_ex, f_ex, c_ex = init_exchanges()
data = fetch_data(s_ex, f_ex, c_ex)

if data:
    # 计算硬指标
    basis = (data['f_price'] - data['s_price']) / data['s_price'] * 100
    casino = data['f_vol'] / data['s_vol']
    cb_prem = (data['cb_price'] - data['s_price']) / data['s_price'] * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("基差率 (Basis%)", f"{basis:.4f}%")
    col2.metric("赌场系数 (合约/现货)", f"{casino:.1f}x")
    col3.metric("CB 溢价 (美资)", f"{cb_prem:.4f}%")

    # 风险诊断
    if casino > 15:
        st.warning(f"检测到杠杆过热！当前倍数: {casino:.1f}")
    if cb_prem < -0.05:
        st.error("美资机构正在砸盘/离场！")

    st.write(f"最后更新时间: {data['time']}")
    
    # 自动刷新
    time.sleep(10)
    st.rerun()
