import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
import re

# 페이지 설정
st.set_page_config(page_title="내 자산 현황", layout="wide", page_icon="💰")
st.title("🚀 Market Map & My Portfolio (Real-Time)")

# ---------------------------------------------------------
# ▼▼ 1. 내 원금 설정 (ETF 3종 제외 후 수정됨) ▼▼
# ---------------------------------------------------------
FIXED_PRINCIPAL = 136844147 

# ---------------------------------------------------------
# ▼▼ 2. 포트폴리오 설정 (3종목 삭제 완료) ▼▼
# ---------------------------------------------------------
my_portfolio = {
    '섹터': [
        '반도체/IT', '반도체/IT', '방산/기계', '금융지주', '방산/기계',
        '자동차/소비재', '자동차/소비재', '방산/기계', '금융지주',
        '자동차/소비재', '금융지주', '가전/IT', '전력/인프라',
        '조선/중공업',
        '미국 빅테크', '미국 지수ETF', '미국 지수ETF', '미국 전기차',
        '미국 금융', '미국 빅테크', '미국 반도체'
    ],
    '종목명': [
        '삼성전자', 'SK하이닉스', 'LIG넥스원', '하나금융지주', '현대로템',
        '현대차', '오리온', '한화', 'LG',
        'KT&G', 'KB금융', 'LG전자', '효성중공업',
        'HD현대중공업',
        'Alphabet C', 'Invesco QQQ', 'TQQQ', 'Tesla',
        'Berkshire B', 'Zeta Global', 'Qualcomm'
    ],
    '종목코드': [
        '005930', '000660', '079550', '086790', '064350',
        '005380', '271560', '000880', '003550',
        '033780', '105560', '066570', '298040',
        '329180', 
        'GOOG', 'QQQ', 'TQQQ', 'TSLA',
        'BRK-B', 'ZETA', 'QCOM'
    ],
    '수량': [
        151, 12, 39, 114, 20,
        27, 32, 24, 90,
        80, 21, 25, 2,
        17,
        17, 2, 3, 4,
        2, 58, 4
    ],
    '매수단가': [
        117639, 736000, 523833, 98789, 196918,
        388518, 115500, 125000, 88428,
        147500, 132605, 106700, 2208000,
        615235,
        287.55, 624.58, 54.50, 466.97,
        493.98, 23.52, 182.39
    ]
}

# ---------------------------------------------------------
# ▼▼ 함수 정의 ▼▼
# ---------------------------------------------------------

def get_exchange_rate():
    """실시간 원/달러 환율 조회"""
    try:
        ticker = yf.Ticker("KRW=X")
        data = ticker.history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
        return 1460.0
    except:
        return 1460.0

def get_naver_realtime(code):
    """네이버 금융 크롤링"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=3)
        
        if response.status_code != 200:
            return 0, 0
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        meta_desc = soup.find("meta", property="og:description")
        if meta_desc:
            content = meta_desc["content"]
            price_match = re.search(r'([\d,]+)원', content)
            current_price = int(price_match.group(1).replace(',', '')) if price_match else 0
            
            rate_match = re.search(r'([+-]?[\d.]+)%', content)
            current_rate = float(rate_match.group(1)) if rate_match else 0.0
            
            return current_price, current_rate
            
        price_tag = soup.select_one('.no_today .blind')
        if price_tag:
            current_price = int(price_tag.text.replace(',', ''))
            prev_tag = soup.select_one('.no_exday .blind')
            if prev_tag:
                prev_price = int(prev_tag.text.replace(',', ''))
                current_rate = ((current_price - prev_price) / prev_price) * 100 if prev_price else 0
            else:
                current_rate = 0
            return current_price, current_rate
            
        return 0, 0
    except:
        return 0, 0

def get_yahoo_data(code, exchange_rate):
    """야후 파이낸스 데이터 조회"""
    try:
        ticker = yf.Ticker(code)
        hist = ticker.history(period="2d")
        
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            if len(hist) > 1:
                prev_close = hist['Close'].iloc[-2]
                change_rate = ((current_price - prev_close) / prev_close) * 100
            else:
                change_rate = 0 
            
            return current_price * exchange_rate, change_rate
        return 0, 0
    except:
        return 0, 0

# ---------------------------------------------------------
# ▼▼ 데이터 로드 (캐싱 적용) ▼▼
# ---------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def load_data():
    df = pd.DataFrame(my_portfolio)
    current_prices = []
    daily_rates = []
    
    exchange_rate = get_exchange_rate()
    
    for raw_code in df['종목코드']:
        code = str(raw_code).upper().strip()
        
        # 한국 주식 (숫자로 시작)
        if code[0].isdigit():
            curr, rate = get_naver_realtime(code)
            # 백업: FDR
            if curr == 0:
                try:
                    df_fdr = fdr.DataReader(code)
                    if not df_fdr.empty:
                        curr = df_fdr['Close'].iloc[-1]
                        rate = ((curr - df_fdr['Close'].iloc[-2]) / df_fdr['Close'].iloc[-2] * 100) if len(df_fdr) >= 2 else 0
                except:
                    pass
        # 미국 주식
        else:
            curr, rate = get_yahoo_data(code, exchange_rate)

        current_prices.append(curr)
        daily_rates.append(rate)

    df['현재가'] = current_prices
    df['오늘등락률(%)'] = daily_rates
    
    df['평가금액'] = df['현재가'] * df['수량']
    df['오늘등락폭'] = df['평가금액'] - (df['평가금액'] / (1 + df['오늘등락률(%)']/100))
    
    df['매수단가_계산용'] = df.apply(
        lambda x: x['매수단가'] * exchange_rate if not str(x['종목코드'])[0].isdigit() else x['매수단가'], axis=1
    )
    df['투자원금'] = df['매수단가_계산용'] * df['수량']
    df['누적수익률(%)'] = df.apply(
        lambda x: ((x['평가금액'] - x['투자원금']) / x['투자원금'] * 100) if x['투자원금'] > 0 else 0, axis=1
    )

    return df, exchange_rate

# ---------------------------------------------------------
# ▼▼ 메인 UI ▼▼
# ---------------------------------------------------------

if st.button('⚡ 데이터 새로고침'):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner("데이터를 불러오는 중입니다..."):
        df_result, applied_exchange_rate = load_data()

    st.caption(f"ℹ️ 적용 환율: 1 USD = {applied_exchange_rate:,.2f} KRW (실시간)")

    # 포맷팅 함수 (흰색 글씨)
    def format_white_text(val, type='percent'):
        color = 'white'
        if type == 'percent':
            return f"<span style='color:{color}; font-weight:bold'>{val:+.2f}%</span>"
        else:
            return f"<span style='color:{color}'>({val:+,.0f})</span>"

    df_result['HTML_등락률'] = df_result['오늘등락률(%)'].apply(lambda x: format_white_text(x, 'percent'))
    
    df_result['1주당등락폭'] = df_result.apply(
        lambda x: x['오늘등락폭'] / x['수량'] if x['수량'] > 0 else 0, axis=1
    )
    df_result['HTML_등락폭'] = df_result['1주당등락폭'].apply(lambda x: format_white_text(x, 'value'))

    # 트리맵
    fig = px.treemap(
        df_result,
        path=['섹터', '종목명'],
        values='평가금액', 
        color='오늘등락률(%)', 
        color_continuous_scale=['#FF3333', '#262626', '#00CC00'], 
        color_continuous_midpoint=0,
        range_color=[-3, 3],
        height=750
    )
    
    fig.data[0].customdata = df_result[['HTML_등락률', '현재가', 'HTML_등락폭']]
    fig.data[0].texttemplate = (
        "<b><span style='font-size:20px; color:white'>%{label}</span></b><br>" +
        "<span style='font-size:16px'>%{customdata[0]}</span><br>" +
        "<span style='font-size:14px; color:#DDDDDD'>₩%{customdata[1]:,.0f}</span>"
    )
    
    fig.update_layout(
        font=dict(family="Pretendard, Malgun Gothic, sans-serif"),
        margin=dict(t=20, l=10, r=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

    # 하단 정보창
    st.markdown("---")
    
    current_total_asset = df_result['평가금액'].sum()
    total_profit = current_total_asset - FIXED_PRINCIPAL
    total_return_rate = (total_profit / FIXED_PRINCIPAL) * 100
    
    total_color = "#00CC00" if total_profit >= 0 else "#FF3333"
    sign = "+" if total_profit >= 0 else ""

    c1, c2, c3 = st.columns([1, 1, 1.5])
    with c1:
        st.metric("💰 설정된 원금 (ETF 제외)", f"{FIXED_PRINCIPAL:,.0f} 원")
    with c2:
        st.metric("📊 현재 총 자산", f"{current_total_asset:,.0f} 원", delta=f"{sign}{total_profit:,.0f} 원")
    with c3:
        st.markdown(f"""
            <div style="background-color: #262626; padding: 15px; border-radius: 10px; border: 1px solid {total_color}; text-align:center;">
                <span style="font-size:14px; color:#CCCCCC;">총 수익률</span>
                <br>
                <span style="font-size:28px; font-weight:bold; color:{total_color};">
                    {sign}{total_return_rate:.2f}%
                </span>
            </div>
        """, unsafe_allow_html=True)

    with st.expander("📂 상세 포트폴리오 데이터 확인"):
        display_df = df_result[['섹터', '종목명', '수량', '현재가', '평가금액', '누적수익률(%)']].copy()
        st.dataframe(
            display_df.style.format({
                '현재가': '₩{:,.0f}',
                '평가금액': '₩{:,.0f}',
                '누적수익률(%)': '{:+.2f}%'
            }).background_gradient(subset=['누적수익률(%)'], cmap='RdYlGn', vmin=-20, vmax=20),
            use_container_width=True,
            height=400
        )

except Exception as e:
    st.error(f"⚠️ 오류가 발생했습니다: {e}")
