import streamlit as st
import pandas as pd

st.set_page_config(page_title="원가분석", page_icon="📊", layout="wide")

st.title("📊 로프가공 원가분석 (안전망 2cm)")
st.markdown("매입업체의 해배(m²)당 산출 방식에 맞춰 임가공비를 자동으로 역산합니다.")

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

    # 해배(m²)당 임가공비 (역산) = 최종 매입단가 - 망 단가 - 로프 단가
    labor_cost_m2 = final_price_m2 - net_price_m2 - rope_price_m2

    # 비율 계산 (ZeroDivisionError 방지)
    if final_price_m2 > 0:
        net_ratio = round((net_price_m2 / final_price_m2) * 100, 1)
        rope_ratio = round((rope_price_m2 / final_price_m2) * 100, 1)
        labor_ratio = round((labor_cost_m2 / final_price_m2) * 100, 1)
    else:
        net_ratio = rope_ratio = labor_ratio = 0

    st.subheader(f"2. 해배(m²)당 원가 분석 결과 (폭 {width}m 기준)")

    # 핵심 지표 표시 (가로 나열 및 괄호 안에 비율 추가)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("안전망 원가 (m²)", f"{int(net_price_m2):,}원 ({net_ratio}%)")
    c2.metric("로프 원가 (m²)", f"{int(rope_price_m2):,}원 ({rope_ratio}%)")
    c3.metric("추정 임가공비 (m²)", f"{int(labor_cost_m2):,}원 ({labor_ratio}%)")
    c4.metric("최종 매입단가 (m²)", f"{int(final_price_m2):,}원 (100%)")

    st.markdown("<br>", unsafe_allow_html=True)
    st.info(f"💡 **계산 근거:** 1롤 면적은 **{area_per_roll}m²** (폭 {width}m x 길이 50m)이며, 로프는 1롤에 **124m**가 소요되는 것을 기준으로 1m²당 가격을 환산했습니다.")
else:
    st.info("👆 위 입력칸 4곳에 단가와 폭을 모두 입력하시면 원가 분석 결과가 나타납니다.")
