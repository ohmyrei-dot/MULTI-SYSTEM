import streamlit as st
import pandas as pd
import os

# -----------------------------------------------------------------------------
# 1. 페이지 공통 설정 (전역 설정)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="스마트 견적서 및 단가 관리",
    page_icon="📊",
    layout="wide"
)

st.title("🏠 스마트 견적서 및 단가 관리 시스템")
st.markdown("데이터를 초기화하고 불러오는 메인 화면입니다. 좌측 사이드바에서 원하는 기능을 선택해주세요.")

# -----------------------------------------------------------------------------
# 2. 데이터 로딩 및 세션 관리 (강제 로드)
# -----------------------------------------------------------------------------
file_path = 'price_list.xlsx'

if os.path.exists(file_path):
    try:
        # 데이터가 세션에 없으면 로드하여 저장
        if 'df_sales' not in st.session_state or 'df_purch' not in st.session_state:
            with st.spinner('데이터를 불러오는 중입니다...'):
                st.session_state['df_sales'] = pd.read_excel(file_path, sheet_name='Sales_매출단가')
                st.session_state['df_purch'] = pd.read_excel(file_path, sheet_name='Purchase_매입단가')
            
        st.success("✅ 데이터 로드 완료! 왼쪽 메뉴를 선택하세요.")
        
        # -----------------------------------------------------------------------------
        # 3. 메인 화면 데이터 샘플 표시
        # -----------------------------------------------------------------------------
        st.divider()
        st.subheader("📋 데이터 미리보기 (샘플)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**[매출단가 조회] 데이터 (상위 5개)**")
            st.dataframe(st.session_state['df_sales'].head(), use_container_width=True)
            
        with col2:
            st.markdown("**[매입견적 및 업체별 단가] 데이터 (상위 5개)**")
            st.dataframe(st.session_state['df_purch'].head(), use_container_width=True)
            
    except Exception as e:
        st.error(f"🚨 엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")
else:
    st.error(f"🚨 '{file_path}' 파일이 존재하지 않습니다. 파일을 동일한 폴더에 업로드해주세요.")
