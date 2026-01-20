import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="내 자산 현황", layout="wide")
st.title("🚀 Market Map & My Portfolio (Global ver.)")

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
    # 한국 주식은 숫자, 미국 주식은 티커
    '종목코드': [
        '005930', '000660', '079550', '086790', '064350',
        '005380', '271560', '000880', '003550', '0117V0',
        '0154F0', # WON 초대형IB
        '033780', '105560', '066570', '298040',
        '329180', '0153K0', 
        'GOOG',   # ✅ 알파벳 (구글) 확인!
        'QQQ', 'TQQQ', 'TSLA',
        'BRK-B', 'ZETA', 'QCOM'
    ],
    '수량': [
        151, 12, 39, 114, 20,
        27, 32, 24, 90, 500,
        1100, 80, 21, 25, 2,
        17, 800,
        17, 2, 3, 4,
        2, 58, 4
    ]
}

# 🌍 글로벌 통합 데이터 수집 함수 (야후 파이낸스 단일화)
def get_market_data(code, exchange_rate=1460):
    try:
        # 1. 티커 변환 (한국 주식은 뒤에 .KS 붙여야 야후가 인식함)
        ticker_symbol = code
        is_korea = False
        
        if code[0].isdigit(): # 숫자로 시작하면 한국 주식
            ticker_symbol = code + ".KS" 
            is_korea = True
        
        # 2. 데이터 가져오기 (fast_info 사용으로 속도 UP)
        ticker = yf.Ticker(ticker_symbol)
        
        # fast_info는 실시간 데이터를 더 잘 가져옵니다.
        current_price = ticker.fast_info.last_price
        prev_close = ticker.fast_info.previous_close
        
        # 데이터가 없을 경우 (가끔 신규 상장주 등)
        if current_price is None or prev_close is None:
             # 히스토리 방식으로 재시도
             hist = ticker.history(period="5d")
             if len(hist) >= 1:
                 current_price = hist['Close'].iloc[-1]
                 prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
             else:
                 return 0, 0

        # 3. 미국 주식 환율 적용
        if not is_korea:
            current_price *= exchange_rate
            prev_close *= exchange_rate

        # 4. 등락률 계산
        if prev_close > 0:
            change_rate = ((current_price - prev_close) / prev_close) * 100
        else:
            change_rate = 0

        return current_price, change_rate

    except Exception as e:
        # 에러 발생 시 0 반환 (화면 멈춤 방지)
        return 0, 0

def load_data():
    df = pd.DataFrame(my_portfolio)
    current_prices = []
    daily_rates = []
    
    # 진행률 표시 바
    progress_bar = st.progress(0)
    total = len(df)

    for i, code in enumerate(df['종목코드']):
        # 공백 제거 및 대문자 변환
        clean_code = str(code).upper().strip()
        
        # 통합 함수 호출
        curr, rate = get_market_data(clean_code)
        
        current_prices.append(curr)
        daily_rates.append(rate)
        
        # 진행률 업데이트
        progress_bar.progress((i + 1) / total)

    progress_bar.empty()

    df['현재가'] = current_prices
    df['오늘등락률(%)'] = daily_rates
    
    # 평가금액 계산
    df['평가금액'] = df['현재가'] * df['수량']
    
    # 오늘 등락폭(원) 역산
    df['오늘등락폭'] = df['평가금액'] - (df['평가금액'] / (1 + df['오늘등락률(%)']/100))

    return df

if st.button('⚡ 새로고침'):
    st.cache_data.clear()
    st.rerun()

try:
    df_result = load_data()

    # 색상 포맷팅 함수
    def format_color(val, type='percent'):
        color = '#00CC00' if val > 0 else '#FF3333' if val < 0 else 'white'
        if type == 'percent':
            return f"<span style='color:{color}; font-weight:bold'>{val:+.2f}%</span>"
        else:
            return f"<span style='color:{color}'>({val:+,.0f})</span>"

    df_result['HTML_등락률'] = df_result['오늘등락률(%)'].apply(lambda x: format_color(x, 'percent'))
    
    # 1주당 등락폭 계산 (보여주기용)
    df_result['1주당등락폭'] = df_result.apply(
        lambda x: x['오늘등락폭'] / x['수량'] if x['수량'] > 0 else 0, axis=1
    )
    df_result['HTML_등락폭'] = df_result['1주당등락폭'].apply(lambda x: format_color(x, 'value'))

    # ---------------------------------------------------------
    # ▼▼ 1. 트리맵 (오늘 시장 현황) ▼▼
    # ---------------------------------------------------------
    fig = px.treemap(
        df_result,
        path=['섹터', '종목명'],
        values='평가금액', 
        color='오늘등락률(%)', 
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
    # ▼▼ 2. 하단 박스 (고정 원금 대비 수익률) ▼▼
    # ---------------------------------------------------------
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

    with st.expander("📊 상세 데이터 보기"):
        st.dataframe(df_result[['종목명', '현재가', '오늘등락률(%)', '평가금액']].style.format({
            '현재가': '₩{:,.0f}',
            '오늘등락률(%)': '{:+.2f}%',
            '평가금액': '₩{:,.0f}'
        }))

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
