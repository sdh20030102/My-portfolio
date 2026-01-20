import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup

# 페이지 설정
st.set_page_config(page_title="오늘의 시장 & 내 자산", layout="wide")
st.title("🚀 오늘 내 주식은 얼마나 올랐을까?")

# ---------------------------------------------------------
# ▼▼ 포트폴리오 설정 ▼▼
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
    # 등락률 계산에 집중하므로 매수단가는 0으로 두거나 생략해도 되지만 구조 유지
    '매수단가': [0] * 24
}

# 🇰🇷 한국 주식 (네이버: 현재가 & 전일종가)
def get_naver_data(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 현재가
        price_area = soup.select_one('.no_today .blind')
        if not price_area: return 0, 0
        current_price = int(price_area.text.replace(',', '').strip())
        
        # 전일 종가 (등락률 계산의 기준)
        prev_area = soup.select_one('.no_exday .blind')
        if not prev_area: return current_price, current_price
        prev_close = int(prev_area.text.replace(',', '').strip())
        
        return current_price, prev_close
    except:
        return 0, 0

# 🇺🇸 미국 주식 (야후: 현재가 & 전일종가)
def get_yahoo_data(code, exchange_rate):
    try:
        ticker = yf.Ticker(code)
        # 5일치 데이터를 가져와서 안정적으로 전일 종가 찾기
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
    exchange_rate = 1460 # 환율

    progress_bar = st.progress(0)
    total = len(df)

    for i, raw_code in enumerate(df['종목코드']):
        code = str(raw_code).upper().strip()
        
        # 한국 주식
        if code[0].isdigit():
            curr, prev = get_naver_data(code)
            # 네이버 실패시 FDR 백업
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
    df['전일종가'] = df['전일종가'].replace(0, 1) # 0원 방지

    # 1. 오늘 등락률 (Today %)
    df['오늘등락률(%)'] = ((df['현재가'] - df['전일종가']) / df['전일종가']) * 100
    
    # 2. 오늘 등락금액 (Today ₩)
    df['오늘등락폭'] = df['현재가'] - df['전일종가']
    
    # 3. 평가금액 (내 자산 비중용)
    df['평가금액'] = df['현재가'] * df['수량']
    
    # 4. 내 오늘 수익금 (오늘 하루 번 돈)
    df['오늘내수익금'] = df['오늘등락폭'] * df['수량']

    return df

if st.button('⚡ 새로고침 (실시간 변동 확인)'):
    st.cache_data.clear()
    st.rerun()

try:
    df_result = load_data()

    # 색상 함수 (초록=상승, 빨강=하락)
    def format_color(val, type='percent'):
        color = '#00CC00' if val > 0 else '#FF3333' if val < 0 else 'white'
        if type == 'percent':
            return f"<span style='color:{color}; font-weight:bold'>{val:+.2f}%</span>"
        else:
            return f"<span style='color:{color}'>({val:+,.0f})</span>"

    df_result['HTML_등락률'] = df_result['오늘등락률(%)'].apply(lambda x: format_color(x, 'percent'))
    df_result['HTML_등락폭'] = df_result['오늘등락폭'].apply(lambda x: format_color(x, 'value'))

    # 트리맵 (박스 크기: 내 돈 비중 / 색상: 오늘 등락률)
    fig = px.treemap(
        df_result,
        path=['섹터', '종목명'],
        values='평가금액', 
        color='오늘등락률(%)', 
        color_continuous_scale=['#FF3333', '#262626', '#00CC00'], # 빨강 -> 검정 -> 초록
        color_continuous_midpoint=0,
        range_color=[-3, 3], # 하루 변동폭 기준 (진하기 조절)
        height=900
    )

    fig.data[0].customdata = df_result[['HTML_등락률', '현재가', 'HTML_등락폭']]
    fig.data[0].texttemplate = (
        "<b><span style='font-size:24px'>%{label}</span></b><br><br>" +
        "<span style='font-size:18px'>%{customdata[0]}</span><br>" + # 오늘 몇% 올랐나
        "<span style='font-size:16px'>₩%{customdata[1]:,.0f}</span><br>" + 
        "<span style='font-size:14px'>%{customdata[2]}</span>" # 오늘 얼마 올랐나
    )
    
    fig.update_layout(font=dict(family="Arial", size=14), margin=dict(t=20, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # ▼▼ 하단: 오늘 내 계좌 변동 현황 (Today's Total) ▼▼
    # ---------------------------------------------------------
    st.markdown("---")
    
    total_asset = df_result['평가금액'].sum()
    today_profit = df_result['오늘내수익금'].sum() # 오늘 하루 번 돈
    
    # 어제 내 총 자산 (추정)
    yesterday_asset = total_asset - today_profit
    today_profit_rate = (today_profit / yesterday_asset) * 100 if yesterday_asset != 0 else 0
    
    # 색상 결정
    total_color = "#00CC00" if today_profit >= 0 else "#FF3333"
    sign = "+" if today_profit >= 0 else ""

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("현재 총 자산", f"{total_asset:,.0f} 원")
    with c2:
        st.metric("오늘 하루 변동금액", f"{sign}{today_profit:,.0f} 원", delta_color="off")
    with c3:
        # 여기가 핵심! 오늘 내 계좌가 몇 % 올랐는지 표시
        st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 2px solid {total_color}; text-align:center;">
                <p style="margin:0; font-size:16px; color:#AAAAAA;">오늘 내 자산 상승률</p>
                <p style="margin:5px 0 0 0; font-size:32px; font-weight:bold; color:{total_color};">
                    {sign}{today_profit_rate:.2f}%
                </p>
                <p style="margin:0; font-size:14px; color:{total_color};">
                    ({sign}{today_profit:,.0f}원)
                </p>
            </div>
        """, unsafe_allow_html=True)

    with st.expander("📊 상세 등락표 보기"):
        st.dataframe(
            df_result[['종목명', '현재가', '오늘등락률(%)', '오늘등락폭', '오늘내수익금']].style.format({
                '현재가': '₩{:,.0f}',
                '오늘등락률(%)': '{:+.2f}%',
                '오늘등락폭': '{:+,.0f}',
                '오늘내수익금': '{:+,.0f}'
            })
        )

except Exception as e:
    st.error(f"오류: {e}")
