import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup

# 페이지 설정
st.set_page_config(page_title="시장 현황판", layout="wide")
st.title("🚀 오늘의 시장 지도 & 내 자산 현황")

# ---------------------------------------------------------
# ▼▼ 포트폴리오 설정 (매수단가 복구 완료!) ▼▼
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
        '0154F0', # ✅ WON 초대형IB
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
    # 내 수익률 계산을 위해 매수단가 복구!
    '매수단가': [
        117639, 736000, 523833, 98789, 196918,
        388518, 115500, 125000, 88428, 14450,
        10350, 147500, 132605, 106700, 2208000,
        615235, 10430,
        287.55, 624.58, 54.50, 466.97,
        493.98, 23.52, 182.39
    ]
}

# 🇰🇷 한국 주식 (네이버)
def get_naver_data(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        price_area = soup.select_one('.no_today .blind')
        if not price_area: return 0, 0
        current_price = int(price_area.text.replace(',', '').strip())
        
        prev_area = soup.select_one('.no_exday .blind')
        if not prev_area: return current_price, current_price
        prev_close = int(prev_area.text.replace(',', '').strip())
        
        return current_price, prev_close
    except:
        return 0, 0

# 🇺🇸 미국 주식 (야후)
def get_yahoo_data(code, exchange_rate):
    try:
        ticker = yf.Ticker(code)
        data = ticker.history(period="5d") 
        
        if len(data) >= 2:
            current_price = data['Close'].iloc[-1] * exchange_rate
            prev_close = data['Close'].iloc[-2] * exchange_rate
            return current_price, prev_close
        elif len(data) == 1:
             current_price = data['Close'].iloc[-1] * exchange_rate
             return current_price, current_price
        return 0, 0
    except:
        return 0, 0

def load_data():
    df = pd.DataFrame(my_portfolio)
    current_prices = []
    prev_closes = []
    exchange_rate = 1460 

    progress_bar = st.progress(0)
    total = len(df)

    for i, raw_code in enumerate(df['종목코드']):
        code = str(raw_code).upper().strip()
        
        # 한국 주식
        if code[0].isdigit():
            curr, prev = get_naver_data(code)
            if curr == 0:
                try:
                    data = fdr.DataReader(code)
                    curr = data['Close'].iloc[-1]
                    prev = data['Close'].iloc[-2] if len(data) > 1 else curr
                except:
                    curr, prev = 0, 0
        # 미국 주식
        else:
            curr, prev = get_yahoo_data(code, exchange_rate)

        current_prices.append(curr)
        prev_closes.append(prev)
        progress_bar.progress((i + 1) / total)

    progress_bar.empty()

    df['현재가'] = current_prices
    df['전일종가'] = prev_closes
    df['전일종가'] = df['전일종가'].replace(0, 1) 

    # 시장 등락률 (어제 대비 오늘)
    df['등락률(%)'] = ((df['현재가'] - df['전일종가']) / df['전일종가']) * 100
    df['등락폭'] = df['현재가'] - df['전일종가']
    df['평가금액'] = df['현재가'] * df['수량']

    # 내 수익률 계산 (매수단가 대비)
    # 한국 주식이면 그대로, 미국 주식이면 환율 곱해서 매수단가 계산
    df['매수단가_원화'] = df.apply(
        lambda x: x['매수단가'] * exchange_rate if (not str(x['종목코드'])[0].isdigit()) else x['매수단가'], 
        axis=1
    )
    df['투자원금'] = df['매수단가_원화'] * df['수량']
    df['내수익금'] = df['평가금액'] - df['투자원금']
    df['내수익률(%)'] = (df['내수익금'] / df['투자원금']) * 100

    return df

if st.button('⚡ 새로고침'):
    st.cache_data.clear()
    st.rerun()

try:
    df_result = load_data()

    # 1. 메인 지도 (오늘 시장 상황)
    st.subheader("📊 오늘의 시장 지도 (Market Map)")
    
    # 색상 함수 (상승=초록, 하락=빨강)
    def format_color(val, type='percent'):
        color = '#00CC00' if val > 0 else '#FF3333' if val < 0 else 'white'
        if type == 'percent':
            return f"<span style='color:{color}; font-weight:bold'>{val:+.2f}%</span>"
        else:
            return f"<span style='color:{color}'>({val:+,.0f})</span>"

    df_result['HTML_등락률'] = df_result['등락률(%)'].apply(lambda x: format_color(x, 'percent'))
    df_result['HTML_등락폭'] = df_result['등락폭'].apply(lambda x: format_color(x, 'value'))

    fig = px.treemap(
        df_result,
        path=['섹터', '종목명'],
        values='평가금액', 
        color='등락률(%)', 
        color_continuous_scale=['#FF3333', '#262626', '#00CC00'], 
        color_continuous_midpoint=0,
        range_color=[-3, 3],
        height=900
    )

    fig.data[0].customdata = df_result[['HTML_등락률', '현재가', 'HTML_등락폭']]
    fig.data[0].texttemplate = (
        "<b><span style='font-size:24px'>%{label}</span></b><br><br>" +
        "<span style='font-size:18px'>%{customdata[0]}</span><br>" + 
        "<span style='font-size:16px'>₩%{customdata[1]:,.0f}</span><br>" + 
        "<span style='font-size:14px'>%{customdata[2]}</span>"
    )
    fig.update_layout(font=dict(family="Arial", size=14), margin=dict(t=20, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # ▼▼ 2. 내 자산 변동률 (요청하신 부분) ▼▼
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("💰 내 자산 성적표")

    total_invest = df_result['투자원금'].sum()
    total_eval = df_result['평가금액'].sum()
    total_profit = total_eval - total_invest
    total_rate = (total_profit / total_invest) * 100
    
    # 수익 여부에 따른 색상 (초록/빨강)
    color_code = "green" if total_profit >= 0 else "red"
    profit_sign = "+" if total_profit >= 0 else ""

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("총 투자 원금", f"{total_invest:,.0f} 원")
    with col2:
        st.metric("현재 평가 금액", f"{total_eval:,.0f} 원")
    with col3:
        # 여기가 핵심입니다! 색상을 입혀서 크게 보여줍니다.
        st.markdown(f"""
        <div style="text-align: left;">
            <p style="font-size: 1rem; margin-bottom: 0;">총 수익금 (수익률)</p>
            <p style="font-size: 2rem; color: {color_code}; font-weight: bold; margin-top: 0;">
                {profit_sign}{total_profit:,.0f}원 ({profit_sign}{total_rate:.2f}%)
            </p>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("📊 상세 포트폴리오 보기"):
        st.dataframe(
            df_result[['종목명', '수량', '매수단가', '현재가', '내수익률(%)', '평가금액']].style.format({
                '수량': '{:,.0f}',
                '매수단가': '{:,.0f}', # 원화 환산 기준 표시일 수 있음
                '현재가': '₩{:,.0f}',
                '평가금액': '₩{:,.0f}',
                '내수익률(%)': '{:+.2f}%'
            })
        )

except Exception as e:
    st.error(f"오류: {e}")
