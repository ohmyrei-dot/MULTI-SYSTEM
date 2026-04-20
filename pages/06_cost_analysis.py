import streamlit as st
import pandas as pd

st.set_page_config(page_title="원가분석", page_icon="📊", layout="wide")

st.title("📊 로프가공 원가분석 (안전망 2cm)")
st.markdown("매입업체의 해배(m²)당 산출 방식에 맞춰 숨은 **인건비**를 자동으로 역산합니다.")

# 누적 기록을 저장할 세션 상태 초기화
if 'cost_history' not in st.session_state:
    st.session_state['cost_history'] = []

# -----------------------------------------------------------------------------
# 1. 입력 섹션
# -----------------------------------------------------------------------------
st.subheader("1. 단가 및 규격 입력")
col1, col2, col3, col4 = st.columns(4)

with col1:
    net_price_m2 = st.number_input("망 단가 (원/m²)", value=None, step=10, help="안전망 2cm 미가공 해배당 가격")
with col2:
    rope_price_200m = st.number_input("로프 200m 단가 (원/롤)", value=None, step=500, help="PP로프 1롤(200m) 구매 가격")
with col3:
    final_price_m2 = st.number_input("가공제품 매입단가 (원/m²)", value=None, step=10, help="최종적으로 매입업체에 지불하는 해배당 가격")
with col4:
    width = st.number_input("안전망 폭 (m)", min_value=0.5, max_value=14.0, value=None, step=0.1, help="길이는 50m로 고정되어 있습니다.")

st.divider()

# -----------------------------------------------------------------------------
# 2. 계산 로직 및 결과 표시
# -----------------------------------------------------------------------------
if net_price_m2 is not None and rope_price_200m is not None and final_price_m2 is not None and width is not None:
    # 1롤 기준 면적 (폭 * 50m)
    area_per_roll = width * 50

    # 로프 1m당 단가
    rope_price_m = rope_price_200m / 200

    # 1롤당 들어가는 로프 총 가격 (양끝면 약 62m * 2 = 124m 소요)
    rope_cost_per_roll = rope_price_m * 124

    # 해배(m²)당 로프 가격 환산
    rope_price_m2 = rope_cost_per_roll / area_per_roll

    # 해배(m²)당 인건비 (역산) = 최종 매입단가 - 망 단가 - 로프 단가
    labor_cost_m2 = final_price_m2 - net_price_m2 - rope_price_m2
    
    # 1롤 총 인건비 = 해배당 인건비 * 1롤 면적
    labor_cost_total = labor_cost_m2 * area_per_roll

    # 비율 계산 (ZeroDivisionError 방지)
    if final_price_m2 > 0:
        net_ratio = round((net_price_m2 / final_price_m2) * 100, 1)
        rope_ratio = round((rope_price_m2 / final_price_m2) * 100, 1)
        labor_ratio = round((labor_cost_m2 / final_price_m2) * 100, 1)
    else:
        net_ratio = rope_ratio = labor_ratio = 0

    st.subheader("2. 현재 계산 결과")

    # 결과 지표 표시 (2줄로 나누어 가독성 확보)
    c1, c2, c3 = st.columns(3)
    c1.metric("📌 안전망 규격 (폭 x 길이)", f"{width}m x 50m ({area_per_roll}m²)")
    c2.metric("안전망 원가 (m²)", f"{int(net_price_m2):,}원 ({net_ratio}%)")
    c3.metric("로프 원가 (m²)", f"{int(rope_price_m2):,}원 ({rope_ratio}%)")

    st.markdown("<br>", unsafe_allow_html=True)
    
    c4, c5, c6 = st.columns(3)
    c4.metric("추정 인건비 (m²)", f"{int(labor_cost_m2):,}원 ({labor_ratio}%)")
    c5.metric("💡 1롤 작업 인건비 (총액)", f"{int(labor_cost_total):,}원 / 롤")
    c6.metric("최종 매입단가 (m²)", f"{int(final_price_m2):,}원 (100%)")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 누적 기록 추가 버튼
    if st.button("➕ 현재 계산 결과를 아래 누적표에 저장하기", type="primary", use_container_width=True):
        st.session_state['cost_history'].append({
            "폭 (m)": f"{width}",
            "안전망 (원)": f"{int(net_price_m2):,} ({net_ratio}%)",
            "로프 (원)": f"{int(rope_price_m2):,} ({rope_ratio}%)",
            "인건비 (원)": f"{int(labor_cost_m2):,} ({labor_ratio}%)",
            "1롤 인건비 (원)": f"{int(labor_cost_total):,}",
            "최종단가 (원)": f"{int(final_price_m2):,} (100%)"
        })
        st.rerun()

else:
    st.info("👆 위 입력칸 4곳에 단가와 폭을 모두 입력하시면 결과와 [저장] 버튼이 나타납니다.")

st.divider()

# -----------------------------------------------------------------------------
# 3. 누적 결과 표 (계속 추가되는 곳)
# -----------------------------------------------------------------------------
st.subheader("📋 폭(m)별 원가 비교 누적표")
if st.session_state['cost_history']:
    df_history = pd.DataFrame(st.session_state['cost_history'])
    
    html_table = df_history.to_html(index=False, classes="custom-table", border=0)
    
    css = '<style>.custom-table { width: 100%; border-collapse: collapse; font-size: 15px; margin-bottom: 20px; } .custom-table th { background-color: #f8f9fa; color: #31333F; font-weight: bold; text-align: center !important; padding: 12px; border-bottom: 2px solid #ddd; } .custom-table td { text-align: center !important; padding: 10px; border-bottom: 1px solid #eee; }</style>'
    
    st.markdown(css + html_table, unsafe_allow_html=True)
    
    if st.button("🗑️ 누적 기록 전체 삭제"):
        st.session_state['cost_history'] = []
        st.rerun()
else:
    st.info("아직 추가된 기록이 없습니다. 위에서 계산 후 파란색 [저장하기] 버튼을 누르세요.")

st.divider()

# -----------------------------------------------------------------------------
# 4. 하단 계산 로직 설명
# -----------------------------------------------------------------------------
st.subheader("📝 계산 로직 설명")
st.markdown("""
<div style='background-color: #f1f8ff; padding: 20px; border-radius: 10px; line-height: 1.8; font-size: 15px;'>
    <b>1. 1롤 기준 면적 산출</b><br>
    - 입력된 폭(m) × 기본 길이(50m) = <b>1롤당 총 해배(m²) 면적</b><br>
    <br>
    <b>2. 1롤당 로프 원가 산출</b><br>
    - 로프 1m당 단가 = 200m 1롤 단가 ÷ 200<br>
    - <b>1롤당 로프 원가</b> = (로프 1m당 단가) × 124m (가공 시 양끝에 들어가는 평균 로프 소요량)<br>
    <br>
    <b>3. 해배(m²)당 로프 원가 환산</b><br>
    - <b>해배당 로프 원가</b> = 1롤당 로프 원가 ÷ 1롤 면적(m²)<br>
    <br>
    <b>4. 인건비(m²) 역산 및 1롤 총 인건비</b><br>
    - <b>해배당 인건비</b> = 매입업체 최종단가(m²) - 안전망 원가(m²) - 해배당 로프 원가(m²)<br>
    - <b>1롤 작업 총 인건비</b> = 해배당 인건비 × 1롤 면적(m²)
</div>
""", unsafe_allow_html=True)
