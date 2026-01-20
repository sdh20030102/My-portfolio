import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
import time

# 페이지 설정
st.set_page_config(page_title="내 주식 현황판", layout="wide")
st.title("🚀 내 포트폴리오 (Real-time Hybrid)")

# ---------------------------------------------------------
# ▼▼ 내 포트폴리오 설정 ▼▼
# ---------------------------------------------------------
my_portfolio = {
    '섹터': [
        '반도체/IT', '반도체/IT', '방산/기계', '금융지주', '방산/기계',
        '자동차/소비재', '자동차/소비재', '방산/기계', '금융지주', '전력/인프라',
        '금융지주', '자동차/소비재', '금융지주', '가전/IT', '전력/인프라',
        '조선/중공업', '금융지주',
        '미국 빅테크', '미국 지수ETF', '미국 지수ETF', '미국 전기차',
        '미국 금융', '미국 빅테크', '미국 반도체'
    ],
    '종목명': [
        '삼성전자', 'SK하이닉스', 'LIG넥스원', '하나금융지주', '현대로템',
        '현대차', '오리온', '한화', 'LG', 'TIGER AI전력기기',
        'WON 초대형IB', 'KT&G', 'KB금융', 'LG전자', '효성중공업',
        'HD현대중공업', 'KODEX 주주환원',
        'Alphabet C', 'Invesco QQQ', 'TQQQ', 'Tesla',
        'Berkshire B', 'Zeta Global', 'Qualcomm'
    ],
    '종목코드': [
        '005930', '000660', '079550', '086790', '064350',
        '005380', '271560', '000880', '003550', '0117V0',
        '0154F0', # 대문자로 적었지만, 혹시 소문자여도 아래 코드에서 자동으로 고쳐줍니다!
        '033780', '105560', '066570', '298040',
        '329180', '0153K0', 
        'GOOG', 'QQQ', 'TQQQ', 'TSLA',
        'BRK-B', 'ZETA', 'QCOM'
    ],
    '수량': [
        151, 12, 39, 114, 20,
        27, 32, 24, 90, 500,
        1100, 80, 21, 25, 2,
        17, 800,
        17, 2, 3, 4,
        2, 58, 4
    ],
    '매수단가': [
        117639, 736000, 523833, 98789, 196918,
        388518, 115500, 125000, 88428, 14450,
        10350, 147500, 132605, 106700, 2208000,
        615235, 10430,
        287.55, 624.58, 54.50, 466.97,
        493.98, 23.52, 182.39
    ]
}

def get_naver_price(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        price_area = soup.select_one('.no_today .blind')
        if not price_area:
             price_area = soup.select_one('.no_today')
        if price_area:
            return int(price_area.text.replace(',', '').strip())
        return 0
    except:
        return 0

def get_yahoo_price(code, exchange_rate):
    try:
        ticker = yf.Ticker(code)
        data = ticker.history(period="1d", interval="1m", prepost=True)
        if not data.empty:
            return data['Close'].iloc[-1] * exchange_rate
        return 0
    except:
        return 0

def load_data():
    df = pd.DataFrame(my_portfolio)
    current_prices = []
    exchange_rate = 1450

    progress_bar = st.progress(0)
    total = len(df)

    for i, raw_code in enumerate(df['종목코드']):
        # ✅ [핵심 수정] 무조건 대문자로 변환해서 처리 (소문자 문제 해결)
        code = str(raw_code).upper().strip()
        
        # 한국 주식 (숫자로 시작)
        if code[0].isdigit():
            price = get_naver_price(code) 
            if price == 0:
                try:
                    stock_data = fdr.DataReader(code)
                    price = stock_data['Close'].iloc[-1]
                except:
                    price = 0
        # 미국 주식
        else:
            price = get_yahoo_price(code, exchange_rate)

        current_prices.append(price)
        progress_bar.progress((i + 1) / total)

    progress_bar.empty()

    df['현재가'] = current_prices
    df['계산용_현재가'] = df.apply(lambda x: x['매수단가'] if x['현재가'] == 0 else x['현재가'], axis=1)
    df['평가금액'] = df['계산용_현재가'] * df['수량']

    df['매수단가_원화'] = df.apply(
        lambda x: x['매수단가'] * exchange_rate if (not str(x['종목코드'])[0].isdigit()) else x['매수단가'],
        axis=1
    )

    df['수익률(%)'] = ((df['계산용_현재가'] - df['매수단가_원화']) / df['매수단가_원화']) * 100

    return df

if st.button('⚡ 강제 새로고침 (실시간)'):
    st.cache_data.clear()
    st.rerun()

try:
    df_result = load_data()

    total_asset = df_result['평가금액'].sum()
    total_asset_eok = total_asset // 100000000
    total_asset_man = (total_asset % 100000000) // 10000
    st.metric(label="💰 총 자산 (추정)", value=f"{total_asset_eok:.0f}억 {total_asset_man:.0f}만 원 (₩{total_asset:,.0f})")

    fig = px.treemap(
        df_result,
        path=['섹터', '종목명'],
        values='평가금액',
        color='수익률(%)',
        color_continuous_scale=['#FF0000', '#F0F2F6', '#00FF00'],
        color_continuous_midpoint=0,
        range_color=[-3, 3],
        height=900
    )

    fig.data[0].customdata = df_result[['수익률(%)', '현재가', '평가금액']]
    fig.data[0].texttemplate = (
        "<b><span style='font-size:20px'>%{label}</span></b><br>" +
        "<span style='font-size:16px'>%{customdata[0]:.2f}%</span><br>" +
        "<span style='font-size:14px'>₩%{customdata[1]:,.0f}</span>"
    )
    fig.update_layout(font=dict(family="Arial", size=14), margin=dict(t=30, l=10, r=10, b=10))

    st.plotly_chart(fig, use_container_width=True)

    if (df_result['현재가'] == 0).any():
        zeros = df_result[df_result['현재가'] == 0]['종목명'].tolist()
        st.warning(f"⚠️ 가격을 못 가져온 종목이 있어요: {zeros}")

    with st.expander("📊 상세 표 보기 (클릭)"):
        st.dataframe(
            df_result[['섹터', '종목명', '수량', '현재가', '수익률(%)', '평가금액']].style.format({
                '수량': '{:,.0f}주',
                '현재가': '₩{:,.0f}',
                '평가금액': '₩{:,.0f}',
                '수익률(%)': '{:+.2f}%'
            })
        )

except Exception as e:
    st.error(f"오류: {e}")

