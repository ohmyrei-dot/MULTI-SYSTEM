import streamlit as st
import pandas as pd

st.set_page_config(page_title="원가분석", page_icon="📊", layout="wide")

st.title("📊 로프가공 원가분석 (안전망 2cm)")
st.markdown("매입업체의 해배(m²)당 산출 방식에 맞춰 숨은 **인건비**를 자동으로 역산합니다.")

# 누적 기록을 저장할 세션 상태 초기화
if 'cost_history' not in st.session_state:
    st.session_state['cost_history'] = []

# 분석 모드 선택
mode = st.radio("📌 분석 모드 선택", ["규격품 (길이 50m 고정)", "제작망 (길이 가변, 다면/달기로프 가공)"], horizontal=True)
st.divider()

# -----------------------------------------------------------------------------
# 1. 입력 섹션
# -----------------------------------------------------------------------------
st.subheader("1. 단가 및 규격 입력")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    width = st.number_input("안전망 폭 (m)", min_value=0.5, max_value=20.0, value=None, step=0.1, help="망의 폭을 입력하세요.")
with col2:
    net_price_m2 = st.number_input("망 단가 (원/m²)", value=None, step=10, help="안전망 2cm 미가공 해배당 가격")
with col3:
    rope_price_200m = st.number_input("로프 200m 단가 (원/롤)", value=None, step=500, help="PP로프 1롤(200m) 구매 가격")
with col4:
    final_price_m2 = st.number_input("가공제품 매입단가 (원/m²)", value=None, step=10, help="최종적으로 매입업체에 지불하는 해배당 가격")
with col5:
    sales_price_m2 = st.number_input("최종 판매단가 (원/m²)", value=None, step=10, help="선택사항: 입력 시 이익금 계산")

# 제작망일 경우 추가 옵션
if "제작망" in mode:
    st.markdown("<br><b>🛠️ 제작망 상세 옵션</b>", unsafe_allow_html=True)
    c_len, c_edge, c_hang = st.columns([1, 1, 3])
    with c_len:
        length = st.number_input("안전망 길이 (m)", min_value=1.0, value=20.0, step=1.0)
    with c_edge:
        edge_type = st.selectbox("테두리 로프", ["2면 (길이방향 양쪽)", "4면 (전체 테두리)"])
    with c_hang:
        hang_qty = st.number_input("달기로프 갯수 (개)", min_value=0, value=0, step=1, help="폭 방향으로 들어가는 보강용 달기로프 수량")
        
    st.markdown("<br><b>🚚 부수적 비용 (선택)</b>", unsafe_allow_html=True)
    c_qty, c_extra, _ = st.columns([1, 1, 3])
    with c_qty:
        prod_qty = st.number_input("제작 갯수 (개)", min_value=1, value=1, step=1, help="운송비 등을 N빵하기 위한 총 수량")
    with c_extra:
        extra_cost_total = st.number_input("기타비용 총액 (원)", min_value=0, value=0, step=10000, help="운송비 등 전체 부수적 비용")
else:
    length = 50.0
    prod_qty = 1
    extra_cost_total = 0

st.divider()

# -----------------------------------------------------------------------------
# 2. 계산 로직 및 결과 표시
# -----------------------------------------------------------------------------
if net_price_m2 is not None and rope_price_200m is not None and final_price_m2 is not None and width is not None:
    # 면적 (폭 * 길이)
    area_total = width * length

    # 로프 1m당 단가
    rope_price_m = rope_price_200m / 200

    # 로프 소요량 계산
    if "규격품" in mode:
        rope_len_total = 124.0
        calc_desc = f"1롤(50m) 양끝면 가공 (로프 총 {rope_len_total}m 소요)"
        extra_cost_m2 = 0
    else:
        # 길이방향 로프 (신축성 20% 반영 + 여장 2m)
        len_rope_1line = (length * 1.2) + 2
        # 폭방향 로프 & 달기로프 (여장 2m)
        wid_rope_1line = width + 2
        
        edge_len = (len_rope_1line * 2) if "2면" in edge_type else (len_rope_1line * 2 + wid_rope_1line * 2)
        hang_len = wid_rope_1line * hang_qty
        rope_len_total = edge_len + hang_len
        calc_desc = f"테두리 {edge_type} + 달기로프 {hang_qty}개 (로프 총 {rope_len_total:.1f}m 소요)"
        extra_cost_m2 = extra_cost_total / (area_total * prod_qty) if (area_total * prod_qty) > 0 else 0

    # 로프 총 가격 및 해배(m²)당 환산
    rope_cost_total = rope_price_m * rope_len_total
    rope_price_m2 = rope_cost_total / area_total

    # 해배(m²)당 인건비 (역산) = 최종 매입단가 - 망 단가 - 로프 단가 - 기타비용 환산액
    labor_cost_m2 = final_price_m2 - net_price_m2 - rope_price_m2 - extra_cost_m2
    
    # 1롤(망 1개) 총 인건비
    labor_cost_total = labor_cost_m2 * area_total

    # 비율 계산 (ZeroDivisionError 방지)
    if final_price_m2 > 0:
        net_ratio = round((net_price_m2 / final_price_m2) * 100, 1)
        rope_ratio = round((rope_price_m2 / final_price_m2) * 100, 1)
        labor_ratio = round((labor_cost_m2 / final_price_m2) * 100, 1)
        extra_ratio = round((extra_cost_m2 / final_price_m2) * 100, 1)
    else:
        net_ratio = rope_ratio = labor_ratio = extra_ratio = 0

    st.subheader("2. 현재 계산 결과")

    # 결과 지표 1줄 표시
    if extra_cost_m2 > 0:
        c1, c2, c3, c_ex, c4, c5 = st.columns(6)
        c_ex.metric("기타비용 (m²)", f"{int(extra_cost_m2):,}원 ({extra_ratio}%)")
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        
    c1.metric("📌 규격 (폭x길이)", f"{width}m x {length}m")
    c2.metric("안전망 원가 (m²)", f"{int(net_price_m2):,}원 ({net_ratio}%)")
    c3.metric("로프 원가 (m²)", f"{int(rope_price_m2):,}원 ({rope_ratio}%)")
    c4.metric("추정 인건비 (m²)", f"{int(labor_cost_m2):,}원 ({labor_ratio}%)")
    c5.metric("매입단가 (m²)", f"{int(final_price_m2):,}원 (100%)")

    st.info(f"💡 **망 1개({area_total:.1f}m²) 작업 인건비 (총액) : {int(labor_cost_total):,}원** — {calc_desc}")
    
    if "제작망" in mode and extra_cost_total > 0:
        st.warning(f"🚚 기타비용 총액({extra_cost_total:,}원)을 전체 제작 면적({area_total * prod_qty:,.1f}m²)으로 나눈 **해배당 {int(extra_cost_m2):,}원**이 매입단가에서 추가로 제외되어 순수 인건비가 산출되었습니다.")

    # 이익금 및 이익률 계산 (판매단가가 있을 때만)
    if sales_price_m2 is not None:
        profit_m2 = sales_price_m2 - final_price_m2
        profit_ratio = round((profit_m2 / sales_price_m2) * 100, 1) if sales_price_m2 > 0 else 0
        
        # 간격 축소를 위해 컬럼 비율 조정 ([1.5, 3.5, 5])
        c6, c7, c8 = st.columns([1.5, 3.5, 5])
        c6.metric("최종 판매단가 (m²)", f"{int(sales_price_m2):,}원")
        c7.metric("💰 예상 이익금 (m²)", f"{int(profit_m2):,}원 (이익률: {profit_ratio}%)")
    else:
        st.caption("💡 상단의 '최종 판매단가'를 입력하시면 예상 이익금이 함께 계산됩니다.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 누적 기록 추가 버튼
    if st.button("➕ 현재 계산 결과를 아래 누적표에 저장하기", type="primary", use_container_width=True):
        hist_data = {
            "구분": "규격품" if "규격품" in mode else "제작망",
            "규격": f"{width}x{length}m",
            "안전망 (원)": f"{int(net_price_m2):,} ({net_ratio}%)",
            "로프 (원)": f"{int(rope_price_m2):,} ({rope_ratio}%)",
            "기타비용 (원)": f"{int(extra_cost_m2):,} ({extra_ratio}%)" if extra_cost_m2 > 0 else "-",
            "인건비 (원)": f"{int(labor_cost_m2):,} ({labor_ratio}%) / 총액: {int(labor_cost_total):,}",
            "매입단가 (원)": f"{int(final_price_m2):,}"
        }
        
        if sales_price_m2 is not None:
            hist_data["판매단가 (원)"] = f"{int(sales_price_m2):,}"
            hist_data["이익금 (원)"] = f"{int(profit_m2):,} ({profit_ratio}%)"
        else:
            hist_data["판매단가 (원)"] = "-"
            hist_data["이익금 (원)"] = "-"
            
        # 비고란 추가
        if "제작망" in mode and extra_cost_total > 0:
            hist_data["비고"] = f"제작 {prod_qty}개 / 기타총액 {int(extra_cost_total):,}원"
        else:
            hist_data["비고"] = "-"

        st.session_state['cost_history'].append(hist_data)
        st.rerun()

else:
    st.info("👆 위 입력칸에 기본 단가와 폭을 모두 입력하시면 결과와 [저장] 버튼이 나타납니다.")

st.divider()

# -----------------------------------------------------------------------------
# 3. 누적 결과 표 (계속 추가되는 곳)
# -----------------------------------------------------------------------------
st.subheader("📋 원가 비교 누적표")
if st.session_state['cost_history']:
    df_history = pd.DataFrame(st.session_state['cost_history'])
    
    if '삭제' not in df_history.columns:
        df_history.insert(0, '삭제', False)
    
    cols_config = {"삭제": st.column_config.CheckboxColumn("삭제", width="small")}
    disabled_cols = [c for c in df_history.columns if c != '삭제']
    
    edited_df = st.data_editor(
        df_history,
        hide_index=True,
        use_container_width=True,
        column_config=cols_config,
        disabled=disabled_cols
    )
    
    if edited_df['삭제'].any():
        keep_indices = edited_df[~edited_df['삭제']].index.tolist()
        st.session_state['cost_history'] = [st.session_state['cost_history'][i] for i in keep_indices]
        st.rerun()
    
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

if "규격품" in mode:
    st.markdown("""
    <div style='background-color: #f1f8ff; padding: 20px; border-radius: 10px; line-height: 1.8; font-size: 15px;'>
        <b>1. 1롤 기준 면적 산출</b><br>
        - 입력된 폭(m) × 기본 길이(50m) = <b>1롤당 총 해배(m²) 면적</b><br>
        <br>
        <b>2. 로프 원가 및 해배(m²)당 환산</b><br>
        - 로프 1m당 단가 = 200m 1롤 단가 ÷ 200<br>
        - 1롤당 로프 원가 = (로프 1m당 단가) × 124m (가공 시 양끝에 들어가는 평균 로프 소요량)<br>
        - <b>해배당 로프 원가</b> = 1롤당 로프 원가 ÷ 1롤 면적(m²)<br>
        <br>
        <b>3. 인건비(m²) 역산 및 1롤 총 인건비</b><br>
        - <b>해배당 인건비</b> = 매입업체 최종단가(m²) - 안전망 원가(m²) - 해배당 로프 원가(m²)<br>
        - <b>1롤 작업 총 인건비</b> = 해배당 인건비 × 1롤 면적(m²)
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style='background-color: #fff4f4; padding: 20px; border-radius: 10px; line-height: 1.8; font-size: 15px;'>
        <b>1. 면적 산출</b><br>
        - 폭(m) × 길이(m) = <b>총 해배(m²) 면적</b><br>
        <br>
        <b>2. 로프 소요량 및 해배(m²)당 환산</b><br>
        - 길이방향 로프 (1줄) = <b>(길이 × 1.2) + 2m</b> (신축성 20% 반영 및 양끝 여장 포함)<br>
        - 폭방향 및 달기로프 (1줄) = <b>폭 + 2m</b> (양끝 여장 포함, <span style='color:#d32f2f; font-weight:bold;'>※ 폭/달기로프는 신축성 20% 미적용</span>)<br>
        - 총 소요량 = 테두리 선택 면적 + (달기로프 1줄 길이 × 달기로프 갯수)<br>
        - <b>해배당 로프 원가</b> = (총 소요량 × 로프 1m당 단가) ÷ 총 해배(m²) 면적<br>
        <br>
        <b>3. 인건비(m²) 역산 및 총 인건비</b><br>
        - <b>해배당 인건비</b> = 매입업체 최종단가(m²) - 안전망 원가(m²) - 해배당 로프 원가(m²) <span style='color:#d32f2f; font-weight:bold;'>- (기타비용 해배당 환산액)</span><br>
        - <b>망 1개 작업 총 인건비</b> = 해배당 인건비 × 면적(m²)
    </div>
    """, unsafe_allow_html=True)
