import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import plotly.express as px
import datetime

# 페이지 설정
st.set_page_config(page_title="내 자산 현황", layout="wide")
st.title("🚀 Market Map & My Portfolio (FDR Ver.)")

# ---------------------------------------------------------
# ▼▼ 1. 내 원금 설정 (고정) ▼▼
# ---------------------------------------------------------
FIXED_PRINCIPAL = 163798147 

# ---------------------------------------------------------
# ▼▼ 2. 포트폴리오 설정 ▼▼
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
        '0154F0', # WON 초대형IB
        '033780', '105560', '066570', '298040',
        '329180', '0153K0', # KODEX 주주환원
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

# 🇰🇷 한국 주식 (FinanceDataReader 사용 - 0% 오류 해결)
def get_korea_data(code):
    try:
        # 최근 7일치 데이터를 가져옵니다 (주말/휴장일 고려 넉넉하게)
        # FDR은 네이버/KRX 데이터를 표 형태로 가져오므로 HTML 구조 변경 영향 안 받음
        start_date = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        df = fdr.DataReader(code, start=start_date)
        
        if len(df) >= 1:
            current_price = int(df['Close'].iloc[-1]) # 오늘 종가(현재가)
            
            # 전일 종가 구하기 (데이터가 2개 이상일 때만)
            if len(df) >= 2:
                prev_price = int(df['Close'].iloc[-2])
                change_rate = ((current_price - prev_price) / prev_price) * 100
            else:
                change_rate = 0 # 신규상장 등 데이터 부족시
                
            return current_price, change_rate
            
        return 0, 0
    except:
        return 0, 0

# 🇺🇸 미국 주식 (야후 파이낸스)
def get_yahoo_data(code, exchange_rate):
    try:
        ticker = yf.Ticker(code)
        # fast_info가 가장 빠르고 정확함
        current_price = ticker.fast_info.last_price
        prev_close = ticker.fast_info.previous_close
        
        if current_price is None: # 데이터 없으면 히스토리 조회
            hist = ticker.history(period="5d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            else:
                return 0, 0

        current_price *= exchange_rate
        prev_close *= exchange_rate

        if prev_close > 0:
            change_rate = ((current_price - prev_close) / prev_close) * 100
        else:
            change_rate = 0

        return current_price, change_rate
    except:
        return 0, 0

def load_data():
    df = pd.DataFrame(my_portfolio)
    current_prices = []
    daily_rates = []
    exchange_rate = 1460 # 환율

    progress_bar = st.progress(0)
    total = len(df)

    for i, raw_code in enumerate(df['종목코드']):
        code = str(raw_code).upper().strip()
        
        # 한국 주식 (숫자로 시작) -> FDR 사용
        if code[0].isdigit():
            curr, rate = get_korea_data(code)
        # 미국 주식 -> 야후 사용
        else:
            curr, rate = get_yahoo_data(code, exchange_rate)

        current_prices.append(curr)
        daily_rates.append(rate)
        progress_bar.progress((i + 1) / total)

    progress_bar.empty()

    df['현재가'] = current_prices
    df['오늘등락률(%)'] = daily_rates
    
    # 평가금액 및 등락폭
    df['평가금액'] = df['현재가'] * df['수량']
    df['오늘등락폭'] = df['평가금액'] - (df['평가금액'] / (1 + df['오늘등락률(%)']/100))
    
    # 누적 수익률 계산
    df['매수단가_계산용'] = df.apply(
        lambda x: x['매수단가'] * exchange_rate if not str(x['종목코드'])[0].isdigit() else x['매수단가'], 
        axis=1
    )
    df['투자원금'] = df['매수단가_계산용'] * df['수량']
    df['누적수익률(%)'] = ((df['평가금액'] - df['투자원금']) / df['투자원금']) * 100

    return df

if st.button('⚡ 새로고침'):
    st.cache_data.clear()
    st.rerun()

try:
    df_result = load_data()

    # ▼▼▼ [색상 강제 통일] 무조건 하얀색(white) 함수 ▼▼▼
    def format_white_text(val, type='percent'):
        if type == 'percent':
            return f"<span style='color:white; font-weight:bold'>{val:+.2f}%</span>"
        else:
            return f"<span style='color:white'>({val:+,.0f})</span>"

    # 모든 등락률과 등락폭을 하얀색으로 변환
    df_result['HTML_등락률'] = df_result['오늘등락률(%)'].apply(lambda x: format_white_text(x, 'percent'))
    
    # 1주당 등락폭 계산
    df_result['1주당등락폭'] = df_result.apply(
        lambda x: x['오늘등락폭'] / x['수량'] if x['수량'] > 0 else 0, axis=1
    )
    df_result['HTML_등락폭'] = df_result['1주당등락폭'].apply(lambda x: format_white_text(x, 'value'))

    # 트리맵 (오늘 시장 현황)
    fig = px.treemap(
        df_result,
        path=['섹터', '종목명'],
        values='평가금액', 
        color='오늘등락률(%)', 
        # 색상: 하락(빨강) -> 보합(검정) -> 상승(초록)
        color_continuous_scale=['#FF3333', '#262626', '#00CC00'], 
        color_continuous_midpoint=0,
        range_color=[-3, 3],
        height=900
    )
    
    # 지도 위 텍스트 설정 (전부 하얀색!)
    fig.data[0].customdata = df_result[['HTML_등락률', '현재가', 'HTML_등락폭']]
    fig.data[0].texttemplate = (
        "<b><span style='font-size:24px; color:white'>%{label}</span></b><br><br>" +
        "<span style='font-size:18px'>%{customdata[0]}</span><br>" + # 하얀색 등락률
        "<span style='font-size:16px; color:white'>₩%{customdata[1]:,.0f}</span><br>" + 
        "<span style='font-size:14px'>%{customdata[2]}</span>" # 하얀색 등락폭
    )
    fig.update_layout(font=dict(family="Arial", size=14), margin=dict(t=20, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # 하단 박스 (고정 원금 대비 수익률)
    st.markdown("---")
    
    current_total_asset = df_result['평가금액'].sum()
    total_profit = current_total_asset - FIXED_PRINCIPAL
    total_return_rate = (total_profit / FIXED_PRINCIPAL) * 100
    
    total_color = "#00CC00" if total_profit >= 0 else "#FF3333"
    sign = "+" if total_profit >= 0 else ""

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("설정된 원금", f"{FIXED_PRINCIPAL:,.0f} 원")
    with c2:
        st.metric("현재 총 자산", f"{current_total_asset:,.0f} 원")
    with c3:
        st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 2px solid {total_color}; text-align:center;">
                <p style="margin:0; font-size:16px; color:#AAAAAA;">총 수익률 (원금 대비)</p>
                <p style="margin:5px 0 0 0; font-size:32px; font-weight:bold; color:{total_color};">
                    {sign}{total_return_rate:.2f}%
                </p>
                <p style="margin:0; font-size:14px; color:{total_color};">
                    ({sign}{total_profit:,.0f}원)
                </p>
            </div>
        """, unsafe_allow_html=True)

    # ▼▼▼ 3. 상세 데이터 표 (요청하신 3개 항목만!) ▼▼▼
    with st.expander("📊 상세 데이터 보기 (클릭)"):
        # 요청: 현재가, 평가금액, 누적상승률
        display_df = df_result[['종목명', '현재가', '평가금액', '누적수익률(%)']].copy()
        
        st.dataframe(display_df.style.format({
            '현재가': '₩{:,.0f}',
            '평가금액': '₩{:,.0f}',
            '누적수익률(%)': '{:+.2f}%'
        }))

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
