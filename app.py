import streamlit as st
import pandas as pd

# 페이지 기본 설정
st.set_page_config(
    page_title="스마트 견적 비교 시스템",
    page_icon="⚡",
    layout="wide"
)

def main():
    st.title("⚡ 스마트 견적 비교 시스템")
    st.markdown("필요한 **품목을 선택**하고 **수량**을 입력하면, 실시간으로 최저가와 총 차액을 분석합니다.")

    # 1. 파일 업로드 섹션
    with st.expander("📂 엑셀 파일 업로드 (클릭하여 열기)", expanded=True):
        uploaded_file = st.file_uploader("단가표 엑셀 업로드", type=['xlsx', 'xls'], label_visibility="collapsed")

    if uploaded_file is not None:
        try:
            # ---------------------------------------------------------
            # 데이터 로드 및 전처리
            # ---------------------------------------------------------
            df_raw = pd.read_excel(uploaded_file)
            
            # 컬럼명 유연하게 찾기
            cols = df_raw.columns.tolist()
            vendor_col = next((c for c in cols if '업체' in c or '거래처' in c), None)
            item_col = next((c for c in cols if '품목' in c or '품명' in c), None)
            price_col = next((c for c in cols if '단가' in c or '매입가' in c or '가격' in c), None)
            spec_cols = [c for c in cols if '규격' in c]

            if not (vendor_col and item_col and price_col):
                st.error("엑셀 파일 형식을 확인해주세요. (필수: 업체명, 품목명, 단가)")
                return

            # 규격 통합
            def combine_specs(row):
                specs = [str(row[c]) for c in spec_cols if pd.notna(row[c]) and str(row[c]).strip() != '']
                return ' '.join(specs) if specs else '-'
            df_raw['통합규격'] = df_raw.apply(combine_specs, axis=1)

            # 피벗 테이블 생성
            df_pivot = df_raw.pivot_table(
                index=[item_col, '통합규격'], 
                columns=vendor_col, 
                values=price_col, 
                aggfunc='first'
            ).reset_index()

            # 업체 리스트
            vendors = [c for c in df_pivot.columns if c not in [item_col, '통합규격']]
            if len(vendors) < 2:
                st.warning("비교할 업체가 2개 이상이어야 합니다.")
                return

            st.divider()

            # ---------------------------------------------------------
            # 2. 설정 및 필터링 (업체 선택 + 품목 선택)
            # ---------------------------------------------------------
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                vendor_a = st.selectbox("기준 업체 (A)", vendors, index=0)
            with c2:
                vendor_b = st.selectbox("비교 업체 (B)", vendors, index=1 if len(vendors) > 1 else 0)
            
            # 품목 선택 (멀티셀렉트)
            all_items = df_pivot[item_col].unique().tolist()
            with c3:
                selected_items = st.multiselect(
                    "견적 낼 품목 선택 (여러 개 선택 가능)", 
                    options=all_items,
                    placeholder="품목을 선택해주세요..."
                )

            # ---------------------------------------------------------
            # 3. 통합 테이블 데이터 구성
            # ---------------------------------------------------------
            if not selected_items:
                st.info("👆 위에서 견적을 낼 품목을 선택하면 상세 표가 나타납니다.")
                st.stop()

            # 선택한 품목만 필터링
            df_filtered = df_pivot[df_pivot[item_col].isin(selected_items)].copy()

            # 세션 상태를 활용하여 수량 유지 (새로운 품목이 추가되어도 기존 수량 유지 노력)
            if "quantities" not in st.session_state:
                st.session_state.quantities = {}

            # 현재 필터링된 데이터프레임에 수량 매핑
            # (키: 품목명_규격)
            def get_qty(row):
                key = f"{row[item_col]}_{row['통합규격']}"
                return st.session_state.quantities.get(key, 1) # 기본값 1

            df_filtered['수량'] = df_filtered.apply(get_qty, axis=1)

            # 계산용 컬럼 미리 추가 (화면 표시용)
            df_filtered[f'{vendor_a} 합계'] = df_filtered[vendor_a] * df_filtered['수량']
            df_filtered[f'{vendor_b} 합계'] = df_filtered[vendor_b] * df_filtered['수량']
            df_filtered['차액(절감액)'] = df_filtered[f'{vendor_a} 합계'] - df_filtered[f'{vendor_b} 합계']

            # ---------------------------------------------------------
            # 4. 상단 요약 대시보드 (실시간 계산)
            # ---------------------------------------------------------
            total_saving = df_filtered['차액(절감액)'].sum()
            total_a_sum = df_filtered[f'{vendor_a} 합계'].sum()
            total_b_sum = df_filtered[f'{vendor_b} 합계'].sum()

            st.markdown(f"### 📊 견적 요약 ({len(selected_items)}개 품목)")
            
            m1, m2, m3 = st.columns(3)
            m1.metric(f"{vendor_a} 총 견적", f"{int(total_a_sum):,}원")
            m2.metric(f"{vendor_b} 총 견적", f"{int(total_b_sum):,}원")
            
            # 절감액 색상 처리
            if total_saving > 0:
                m3.metric("총 절감 가능 금액", f"{int(total_saving):,}원", "이득 (B가 더 저렴)", delta_color="normal")
            elif total_saving < 0:
                m3.metric("총 절감 가능 금액", f"{int(total_saving):,}원", "손해 (A가 더 저렴)", delta_color="inverse")
            else:
                m3.metric("총 절감 가능 금액", "0원", "동일")

            # ---------------------------------------------------------
            # 5. 통합 데이터 에디터 (입력 + 결과)
            # ---------------------------------------------------------
            st.markdown("---")
            st.caption("📝 아래 표에서 **수량**을 수정하면 합계와 차액이 자동으로 다시 계산됩니다.")

            # 화면에 보여줄 컬럼 순서 및 설정
            display_df = df_filtered[[
                item_col, '통합규격', '수량', 
                vendor_a, f'{vendor_a} 합계', 
                vendor_b, f'{vendor_b} 합계', 
                '차액(절감액)'
            ]]

            edited_df = st.data_editor(
                display_df,
                column_config={
                    "수량": st.column_config.NumberColumn(
                        "수량 (입력)", help="구매할 수량을 입력하세요", min_value=1, step=1, format="%d"
                    ),
                    vendor_a: st.column_config.NumberColumn(f"{vendor_a} 단가", format="%d원"),
                    f'{vendor_a} 합계': st.column_config.NumberColumn(f"{vendor_a} 합계", format="%d원"),
                    vendor_b: st.column_config.NumberColumn(f"{vendor_b} 단가", format="%d원"),
                    f'{vendor_b} 합계': st.column_config.NumberColumn(f"{vendor_b} 합계", format="%d원"),
                    "차액(절감액)": st.column_config.NumberColumn(
                        "차액 (A-B)", 
                        help="양수면 B가 저렴(이득), 음수면 A가 저렴(손해)", 
                        format="%d원"
                    ),
                },
                # 수량만 수정 가능하게 하고 나머지는 잠금
                disabled=[item_col, '통합규격', vendor_a, f'{vendor_a} 합계', vendor_b, f'{vendor_b} 합계', '차액(절감액)'],
                use_container_width=True,
                hide_index=True,
                height=500
            )

            # ---------------------------------------------------------
            # 6. 수량 변경 감지 및 세션 업데이트
            # ---------------------------------------------------------
            # 사용자가 수량을 바꾸면 edited_df가 업데이트됨 -> 이를 세션에 저장하여 다음 렌더링 때 반영
            for index, row in edited_df.iterrows():
                key = f"{row[item_col]}_{row['통합규격']}"
                if key in st.session_state.quantities:
                    if st.session_state.quantities[key] != row['수량']:
                        st.session_state.quantities[key] = row['수량']
                        st.rerun() # 즉시 재실행하여 합계 컬럼 업데이트
                else:
                    st.session_state.quantities[key] = row['수량']

        except Exception as e:
            st.error("처리 중 오류가 발생했습니다.")
            st.exception(e)

if __name__ == "__main__":
    main()
