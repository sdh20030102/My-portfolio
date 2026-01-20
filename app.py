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
st.title("🚀 내 포트폴리오 (최종 디버깅 모드)")

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
        '0154F0', # 🚨 여기가 문제! (아래 팁 참고)
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

# 🇰🇷 한국 주식 크롤링 (네이버)
def get_naver_price(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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

# 🇺🇸 미국 주식 크롤링 (야후)
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
    errors = []

    progress_bar = st.progress(0)
    total = len(df)

    for i, raw_code in enumerate(df['종목코드']):
        # 대문자 강제 변환
        code = str(raw_code).upper().strip()
        price = 0
        
        # 1. 한국 주식 (숫자로 시작하면 무조건 시도)
        if code[0].isdigit():
            # [시도 1] 네이버 금융 크롤링
            price = get_naver_price(code)
            
            # [시도 2] 실패 시 FDR (KRX 데이터) 사용
            if price == 0:
                try:
                    stock_data = fdr.DataReader(code)
                    if not stock_data.empty:
                        price = stock_data['Close'].iloc[-1]
                except:
                    pass
            
            # [시도 3] 그래도 0원이면 에러 목록에 추가
            if price == 0:
                errors.append(f"{df['종목명'][i]}({code})")

        # 2. 미국 주식
        else:
            price = get_yahoo_price(code, exchange_rate)
            if price == 0:
                errors.append(f"{df['종목명'][i]}({code})")

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
    
    return df, errors

if st.button('⚡ 강제 새로고침 (실시간)'):
    st.cache_data.clear()
    st.rerun()

try:
    df_result, error_stocks = load_data()

    total_asset = df_result['평가금액'].sum()
    total_asset_eok = total_asset // 100000000
    total_asset_man = (total_asset % 100000000) // 10000
    st.metric(label="💰 총 자산 (추정)", value=f"{total_asset_eok:.0f}억 {total_asset_man:.0f}만 원 (₩{total_asset:,.0f})")

    # 🚨 에러 발생 시 힌트 제공
    if error_stocks:
        st.error(f"⚠️ 다음 종목의 가격을 못 가져왔어요: {', '.join(error_stocks)}")
        st.info("💡 팁: 'WON 초대형IB'는 오늘(1/20) 상장해서 네이버에 아직 없을 수 있습니다. 네이버 금융에서 종목명으로 검색해서 나오는 '숫자 6자리 코드(예: 4xxxxx)'를 넣어보세요!")

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
