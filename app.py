import streamlit as st
import pandas as pd

# 페이지 기본 설정
st.set_page_config(
    page_title="최저가 견적 산출기",
    page_icon="⚖️",
    layout="wide"
)

def main():
    st.title("⚖️ 최저가 견적 산출기")
    st.markdown("엑셀 파일을 업로드하고 **수량**을 입력하면 업체별 견적을 비교해줍니다.")

    # 1. 파일 업로드 섹션
    with st.container():
        uploaded_file = st.file_uploader("단가표 엑셀 업로드 (xlsx, xls)", type=['xlsx', 'xls'])

    if uploaded_file is not None:
        try:
            # 2. 데이터 로드 및 전처리
            df_raw = pd.read_excel(uploaded_file)
            
            # 컬럼명 유연하게 찾기
            cols = df_raw.columns.tolist()
            vendor_col = next((c for c in cols if '업체' in c or '거래처' in c), None)
            item_col = next((c for c in cols if '품목' in c or '품명' in c), None)
            price_col = next((c for c in cols if '단가' in c or '매입가' in c or '가격' in c), None)
            
            # 규격 컬럼 찾기 (여러 개일 수 있음)
            spec_cols = [c for c in cols if '규격' in c]

            if not (vendor_col and item_col and price_col):
                st.error(f"필수 컬럼을 찾을 수 없습니다. (현재 컬럼: {cols})")
                st.info("엑셀 파일에 '업체명', '품목명', '단가' 컬럼이 포함되어 있어야 합니다.")
                return

            # 규격 합치기 (규격1 + 규격2...)
            def combine_specs(row):
                specs = [str(row[c]) for c in spec_cols if pd.notna(row[c]) and str(row[c]).strip() != '']
                return ' '.join(specs) if specs else '-'

            df_raw['통합규격'] = df_raw.apply(combine_specs, axis=1)

            # 피벗 테이블 생성 (세로형 데이터 -> 가로형 데이터)
            # 인덱스: 품목명, 통합규격 / 컬럼: 업체명 / 값: 단가
            df_pivot = df_raw.pivot_table(
                index=[item_col, '통합규격'], 
                columns=vendor_col, 
                values=price_col, 
                aggfunc='first' # 중복 시 첫 번째 값 사용
            ).reset_index()

            # 수량 컬럼 추가 (기본값 1)
            if '수량' not in df_pivot.columns:
                df_pivot.insert(2, '수량', 1)

            # 업체 목록 추출
            vendors = [c for c in df_pivot.columns if c not in [item_col, '통합규격', '수량']]

            if len(vendors) < 2:
                st.warning("비교할 업체가 2개 이상 필요합니다.")
                return

            st.divider()

            # 3. 업체 선택 섹션
            c1, c2 = st.columns(2)
            with c1:
                vendor_a = st.selectbox("비교 업체 1 (기준)", vendors, index=0)
            with c2:
                vendor_b = st.selectbox("비교 업체 2 (비교)", vendors, index=1 if len(vendors) > 1 else 0)

            st.divider()

            # 4. 수량 입력 및 데이터 편집 (Data Editor)
            st.subheader("📋 견적 시뮬레이션")
            st.caption("아래 표의 '수량' 컬럼을 더블 클릭하여 수정하세요.")

            # 화면에 보여줄 컬럼 순서 정리
            # 품목명 | 규격 | 수량 | 업체A단가 | 업체B단가
            display_cols = [item_col, '통합규격', '수량', vendor_a, vendor_b]
            
            # 편집 가능한 데이터프레임 표시
            edited_df = st.data_editor(
                df_pivot[display_cols],
                column_config={
                    "수량": st.column_config.NumberColumn(
                        "수량 (Qty)",
                        help="필요한 수량을 입력하세요",
                        min_value=0,
                        step=1,
                        format="%d"
                    ),
                    vendor_a: st.column_config.NumberColumn(f"{vendor_a} 단가", format="%d원"),
                    vendor_b: st.column_config.NumberColumn(f"{vendor_b} 단가", format="%d원"),
                },
                disabled=[item_col, '통합규격', vendor_a, vendor_b], # 수량만 수정 가능하게 설정
                use_container_width=True,
                hide_index=True,
                height=400
            )

            # 5. 계산 로직
            # NaN(빈값)은 0으로 처리하여 계산
            total_a = (edited_df['수량'] * edited_df[vendor_a].fillna(0)).sum()
            total_b = (edited_df['수량'] * edited_df[vendor_b].fillna(0)).sum()
            diff = total_a - total_b # 양수면 A가 더 비쌈(B가 저렴), 음수면 A가 더 저렴

            # 6. 결과 요약 표시
            st.divider()
            st.subheader("📊 견적 비교 결과")
            
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric(label=f"{vendor_a} 총 견적", value=f"{int(total_a):,}원")
            with m2:
                st.metric(
                    label=f"{vendor_b} 총 견적", 
                    value=f"{int(total_b):,}원",
                    delta=f"{int(-diff):,}원" if diff != 0 else "동일",
                    delta_color="inverse" # 저렴한 게 초록색(positive)으로 보이게 반전
                )
            with m3:
                if diff > 0:
                    st.success(f"✅ **{vendor_b}**가 **{int(diff):,}원** 더 저렴합니다!")
                elif diff < 0:
                    st.error(f"🚨 **{vendor_b}**가 **{int(abs(diff)):,}원** 더 비쌉니다.")
                else:
                    st.info("가격이 동일합니다.")

            # 7. 상세 분석표 (차액 계산 포함)
            st.subheader("🔍 상세 차액 분석")
            
            analysis_df = edited_df.copy()
            analysis_df['단가차이'] = analysis_df[vendor_b].fillna(0) - analysis_df[vendor_a].fillna(0)
            analysis_df['총차액'] = analysis_df['단가차이'] * analysis_df['수량']
            
            # 추천 업체 로직
            def recommend(row):
                if row['총차액'] < 0: return vendor_b
                if row['총차액'] > 0: return vendor_a
                return '-'
            
            analysis_df['추천'] = analysis_df.apply(recommend, axis=1)

            # 보기 좋게 컬럼 정리
            final_view = analysis_df[[item_col, '통합규격', '수량', vendor_a, vendor_b, '단가차이', '총차액', '추천']]
            
            # 스타일링 (음수는 파란색/초록색, 양수는 빨간색 등)
            st.dataframe(
                final_view.style.format({
                    vendor_a: "{:,.0f}",
                    vendor_b: "{:,.0f}",
                    '단가차이': "{:,.0f}",
                    '총차액': "{:,.0f}"
                }).map(lambda x: 'color: blue; font-weight: bold' if x < 0 else ('color: red' if x > 0 else 'color: gray'), subset=['총차액', '단가차이']),
                use_container_width=True,
                hide_index=True
            )

        except Exception as e:
            st.error("오류가 발생했습니다. 엑셀 파일 형식을 확인해주세요.")
            st.exception(e)

if __name__ == "__main__":
    main()
