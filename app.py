import streamlit as st
import pandas as pd

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 스타일링
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="스마트 견적 비교 시스템",
    page_icon="⚖️",
    layout="wide"
)

# CSS를 통해 버튼 스타일 및 레이아웃 미세 조정
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        border-radius: 5px;
    }
    .mobile-card {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #ddd;
    }
    .price-tag {
        font-weight: bold;
        color: #2c3e50;
    }
    .total-highlight {
        font-size: 1.1em;
        color: #e74c3c;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 세션 상태 초기화
# -----------------------------------------------------------------------------
# 한글 파일명("단가표.xlsx")으로 인한 오류 방지를 위해 인코딩된 URL 사용
# "단가표" -> "%EB%8B%A8%EA%B0%80%ED%91%9C"
DATA_URL = "https://raw.githubusercontent.com/ohmyrei-dot/MULTI-SYSTEM/main/%EB%8B%A8%EA%B0%80%ED%91%9C.xlsx"

@st.cache_data
def load_excel_data(url):
    try:
        df = pd.read_excel(url)
        # 필수 컬럼이 없는 경우 예외 처리 또는 기본값 설정
        if '수량' not in df.columns:
            df['수량'] = 1  # 수량이 없으면 기본 1로 설정
        
        # 데이터 정제 (NaN 값을 0으로 채움)
        df = df.fillna(0)
        return df
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# 세션 상태에 데이터 저장 (삭제 기능을 위해 필요)
if 'df' not in st.session_state:
    st.session_state.df = load_excel_data(DATA_URL)

# 행 삭제 함수
def delete_row(index):
    st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)
    st.rerun()

# -----------------------------------------------------------------------------
# 3. 사이드바 및 설정
# -----------------------------------------------------------------------------
st.title("⚖️ 스마트 견적 비교 시스템")

with st.sidebar:
    st.header("⚙️ 설정")
    
    # 데이터가 로드되었는지 확인
    if not st.session_state.df.empty:
        # 숫자형 컬럼만 추출하여 업체 선택 옵션으로 제공
        numeric_cols = st.session_state.df.select_dtypes(include=['number']).columns.tolist()
        # '수량'이나 불필요한 컬럼 제외 (단가 컬럼 추론)
        price_cols = [c for c in numeric_cols if c != '수량']
        
        st.subheader("업체 선택")
        vendor_a = st.selectbox("업체 A (기준)", price_cols, index=0 if len(price_cols) > 0 else 0)
        vendor_b = st.selectbox("업체 B (비교)", price_cols, index=1 if len(price_cols) > 1 else 0)
    else:
        st.warning("데이터를 불러올 수 없습니다.")
        st.stop()

# -----------------------------------------------------------------------------
# 4. 화면 모드 선택
# -----------------------------------------------------------------------------
# st.radio 대신 pills나 버튼 그룹처럼 보이게 설정할 수도 있으나, 요구사항에 따라 버튼형식 UI 제공
mode = st.radio(
    "화면 모드",
    ["📱 모바일(카드)", "💻 PC(표)"],
    index=0,
    horizontal=True
)

st.divider()

# 데이터프레임 복사본 생성 (계산용)
display_df = st.session_state.df.copy()

# 합계 계산
if vendor_a and vendor_b:
    display_df[f'{vendor_a}_합계'] = display_df[vendor_a] * display_df['수량']
    display_df[f'{vendor_b}_합계'] = display_df[vendor_b] * display_df['수량']

# -----------------------------------------------------------------------------
# 5. UI 렌더링 (모바일 vs PC)
# -----------------------------------------------------------------------------

# --- A. 모바일 버전 (카드 뷰) ---
if "모바일" in mode:
    st.caption("💡 각 항목의 휴지통 아이콘을 누르면 목록에서 삭제됩니다.")
    
    for idx, row in display_df.iterrows():
        # 카드 컨테이너 스타일링
        with st.container(border=True):
            # 1. 상단: 품목명 + 삭제 버튼
            col_top_1, col_top_2 = st.columns([8, 1])
            with col_top_1:
                st.markdown(f"#### {row.get('품목', '품목명 없음')}")
            with col_top_2:
                if st.button("🗑️", key=f"del_m_{idx}", help="삭제"):
                    delete_row(idx)
            
            # 2. 중간: 규격 | 수량
            spec = row.get('규격', '-')
            qty = row.get('수량', 0)
            st.markdown(f"📏 **규격**: {spec}  |  📦 **수량**: {qty}개")
            
            st.markdown("---")
            
            # 3. 하단: 업체별 단가 및 합계
            # 업체 A
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**{vendor_a}**")
                st.text(f"단가: {int(row[vendor_a]):,}원")
                st.markdown(f"<span style='color:blue'>합계: {int(row[f'{vendor_a}_합계']):,}원</span>", unsafe_allow_html=True)
            
            # 업체 B
            with c2:
                st.markdown(f"**{vendor_b}**")
                st.text(f"단가: {int(row[vendor_b]):,}원")
                st.markdown(f"<span style='color:red'>합계: {int(row[f'{vendor_b}_합계']):,}원</span>", unsafe_allow_html=True)

# --- B. PC 버전 (표 뷰) ---
else:
    st.caption("💡 왼쪽의 삭제 버튼을 눌러 항목을 제거할 수 있습니다.")
    
    # 헤더 출력
    cols = st.columns([1, 4, 3, 2, 3, 3])
    fields = ["삭제", "품목", "규격", "수량", f"{vendor_a} (합계)", f"{vendor_b} (합계)"]
    for col, field in zip(cols, fields):
        col.markdown(f"**{field}**")
    
    st.markdown("---")
    
    # 데이터 행 출력
    for idx, row in display_df.iterrows():
        cols = st.columns([1, 4, 3, 2, 3, 3])
        
        # 1. 삭제 버튼
        if cols[0].button("🗑️", key=f"del_pc_{idx}"):
            delete_row(idx)
            
        # 2. 데이터 표시
        cols[1].write(row.get('품목', ''))
        cols[2].write(str(row.get('규격', '')))
        cols[3].write(f"{int(row.get('수량', 0))}")
        
        # 업체 A 정보
        price_a = int(row[vendor_a])
        total_a = int(row[f'{vendor_a}_합계'])
        cols[4].write(f"{total_a:,}원 ({price_a:,})")
        
        # 업체 B 정보
        price_b = int(row[vendor_b])
        total_b = int(row[f'{vendor_b}_합계'])
        cols[5].write(f"{total_b:,}원 ({price_b:,})")
        
        st.markdown("<hr style='margin: 5px 0; border-top: 1px dashed #ddd;'>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. 결론 (최종 비교)
# -----------------------------------------------------------------------------
st.markdown("### 📊 최종 결론")

total_sum_a = display_df[f'{vendor_a}_합계'].sum()
total_sum_b = display_df[f'{vendor_b}_합계'].sum()

# 결과 카드
result_container = st.container(border=True)

with result_container:
    col_res_1, col_res_2, col_res_3 = st.columns(3)
    
    col_res_1.metric(label=f"{vendor_a} 총 견적", value=f"{int(total_sum_a):,}원")
    col_res_2.metric(label=f"{vendor_b} 총 견적", value=f"{int(total_sum_b):,}원")
    
    diff = abs(total_sum_a - total_sum_b)
    
    with col_res_3:
        if total_sum_a < total_sum_b:
            winner = vendor_a
            loser = vendor_b
            saved = total_sum_b - total_sum_a
            st.success(f"{winner} 승리!")
        elif total_sum_b < total_sum_a:
            winner = vendor_b
            loser = vendor_a
            saved = total_sum_a - total_sum_b
            st.success(f"{winner} 승리!")
        else:
            winner = "무승부"
            saved = 0
            st.info("견적 금액이 동일합니다.")

if winner != "무승부":
    st.markdown(f"""
    ### 🚨 분석 결과: **{winner}**가 더 저렴합니다!
    
    **{winner}**를 선택하면 **{loser}**보다 
    <span style='color:green; font-size:1.5em; font-weight:bold;'>{int(saved):,}원</span> 절약할 수 있습니다.
    """, unsafe_allow_html=True)
else:
    st.markdown("### ⚖️ 두 업체의 견적 총액이 정확히 일치합니다.")
