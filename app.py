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
# 2. 데이터 로딩 및 세션 관리
# -----------------------------------------------------------------------------
file_path = 'price_list.xlsx'

if os.path.exists(file_path):
    try:
        # 데이터가 세션에 없을 때만 최초 1회 로드
        if 'df_sales' not in st.session_state:
            st.session_state['df_sales'] = pd.read_excel(file_path, sheet_name='Sales_매출단가')
        
        if 'df_purch' not in st.session_state:
            st.session_state['df_purch'] = pd.read_excel(file_path, sheet_name='Purchase_매입단가')
            
        st.success(f"✅ '{file_path}' 데이터를 성공적으로 불러왔습니다.")
        
    except Exception as e:
        st.error(f"🚨 엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")
else:
    st.error(f"🚨 '{file_path}' 파일이 존재하지 않습니다. 파일을 동일한 폴더에 업로드해주세요.")
