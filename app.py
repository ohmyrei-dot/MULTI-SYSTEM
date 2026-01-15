import streamlit as st
import pandas as pd

# 페이지 기본 설정
st.set_page_config(
    page_title="스마트 견적서 작성 시스템",
    page_icon="📝",
    layout="wide"
)

def main():
    st.title("📝 스마트 견적서 작성 시스템")
    st.markdown("원하는 품목을 **직접 선택**하여 견적서에 추가하세요.")

    # 세션 상태 초기화 (견적 리스트 저장용)
    if 'quote_list' not in st.session_state:
        st.session_state.quote_list = []

    # 1. 파일 업로드 섹션
    with st.expander("📂 단가표 엑셀 파일 관리 (클릭)", expanded=True):
        uploaded_file = st.file_uploader("단가표 엑셀 업로드", type=['xlsx', 'xls'], label_visibility="collapsed")

    if uploaded_file is not None:
        try:
            # ---------------------------------------------------------
            # 데이터 로드 및 전처리
            # ---------------------------------------------------------
            df_raw = pd.read_excel(uploaded_file)
            
            # 컬럼명 자동 감지
            cols = df_raw.columns.tolist()
            vendor_col = next((c for c in cols if '업체' in c or '거래처' in c), None)
            item_col = next((c for c in cols if '품목' in c or '품명' in c), None)
            price_col = next((c for c in cols if '단가' in c or '매입가' in c or '가격' in c), None)
            spec_cols = [c for c in cols if '규격' in c]

            if not (vendor_col and item_col and price_col):
                st.error("엑셀 파일 형식을 확인해주세요. (필수: 업체명, 품목명, 단가)")
                return

            # 규격 통합 함수
            def combine_specs(row):
                specs = [str(row[c]) for c in spec_cols if pd.notna(row[c]) and str(row[c]).strip() != '']
                return ' '.join(specs) if specs else '-'
            df_raw['통합규격'] = df_raw.apply(combine_specs, axis=1)

            # 피벗 테이블
            df_pivot = df_raw.pivot_table(
                index=[item_col, '통합규격'], 
                columns=vendor_col, 
                values=price_col, 
                aggfunc='first'
            ).reset_index()

            vendors = [c for c in df_pivot.columns if c not in [item_col, '통합규격']]
            if len(vendors) < 2:
                st.warning("비교할 업체가 2개 이상이어야 합니다.")
                return

            st.divider()

            # ---------------------------------------------------------
            # 2. 업체 설정 (기본값: 솔트룩스, 태양산자)
            # ---------------------------------------------------------
            c1, c2 = st.columns(2)
            
            def get_index(options, target):
                try:
                    return list(options).index(target)
                except ValueError:
                    return 0

            # 업체 A (기본: 솔트룩스)
            idx_a = get_index(vendors, '솔트룩스')
            with c1:
                vendor_a = st.selectbox("기준 업체 (A)", vendors, index=idx_a)

            # 업체 B (기본: 태양산자)
            # 태양산자가 없으면 리스트의 두 번째나 0번째 선택
            target_b = '태양산자'
            if target_b not in vendors:
                idx_b = 1 if len(vendors) > 1 else 0
            else:
                idx_b = get_index(vendors, target_b)
                
            with c2:
                vendor_b = st.selectbox("비교 업체 (B)", vendors, index=idx_b)

            st.divider()

            # ---------------------------------------------------------
            # 3. 품목 추가 인터페이스 (우선순위 정렬 적용)
            # ---------------------------------------------------------
            st.subheader("➕ 품목 추가하기")
            
            with st.container():
                col_input1, col_input2, col_input3, col_btn = st.columns([2, 2, 1, 1])

                # 1) 품목 선택 (정렬 로직 적용)
                raw_items = df_pivot[item_col].unique().tolist()
                
                # 우선순위 키워드 목록
                priority_keywords = ['안전망', 'PP로프', '와이어로프', '와이어클립', '멀티망', '럿셀망', '케이블타이', 'PE로프']
                
                sorted_items = []
                used_items = set()

                # 키워드 순서대로 아이템 추출
                for kw in priority_keywords:
                    # 해당 키워드를 포함하는 아이템 찾기
                    matches = sorted([x for x in raw_items if kw in str(x) and x not in used_items])
                    sorted_items.extend(matches)
                    used_items.update(matches)
                
                # 나머지 아이템들 (가나다순)
                others = sorted([x for x in raw_items if x not in used_items])
                final_item_list = sorted_items + others

                selected_item = col_input1.selectbox("품목 선택", final_item_list, key="sel_item")

                # 2) 규격 선택
                available_specs = df_pivot[df_pivot[item_col] == selected_item]['통합규격'].unique().tolist()
                selected_spec = col_input2.selectbox("규격 선택", available_specs, key="sel_spec")

                # 3) 수량 입력
                input_qty = col_input3.number_input("수량", min_value=1, value=1, step=1, key="in_qty")

                # 4) 추가 버튼
                if col_btn.button("품목 추가", type="primary", use_container_width=True):
                    new_entry = {
                        'id': f"{selected_item}_{selected_spec}",
                        item_col: selected_item,
                        '통합규격': selected_spec,
                        '수량': input_qty
                    }
                    
                    existing_idx = next((i for i, x in enumerate(st.session_state.quote_list) if x['id'] == new_entry['id']), -1)
                    
                    if existing_idx != -1:
                        st.session_state.quote_list[existing_idx]['수량'] += input_qty
                        st.toast(f"✅ '{selected_item}' 수량이 추가되었습니다.")
                    else:
                        st.session_state.quote_list.append(new_entry)
                        st.toast(f"✅ '{selected_item}' 추가 완료!")

            # ---------------------------------------------------------
            # 4. 견적 리스트 (결과 테이블)
            # ---------------------------------------------------------
            st.divider()
            st.subheader(f"📋 견적 리스트 ({len(st.session_state.quote_list)}건)")

            if st.session_state.quote_list:
                df_quote = pd.DataFrame(st.session_state.quote_list)

                # 단가 정보 병합
                df_merged = pd.merge(
                    df_quote, 
                    df_pivot[[item_col, '통합규격', vendor_a, vendor_b]], 
                    on=[item_col, '통합규격'], 
                    how='left'
                )

                # 계산 로직
                df_merged[f'{vendor_a} 단가'] = df_merged[vendor_a].fillna(0)
                df_merged[f'{vendor_b} 단가'] = df_merged[vendor_b].fillna(0)
                
                # 단가 차액 추가 (B - A)
                df_merged['단가 차액'] = df_merged[f'{vendor_b} 단가'] - df_merged[f'{vendor_a} 단가']
                
                df_merged[f'{vendor_a} 합계'] = df_merged[f'{vendor_a} 단가'] * df_merged['수량']
                df_merged[f'{vendor_b} 합계'] = df_merged[f'{vendor_b} 단가'] * df_merged['수량']
                
                # 총 차액 (합계 기준: A - B -> 양수면 B가 저렴)
                df_merged['총 차액'] = df_merged[f'{vendor_a} 합계'] - df_merged[f'{vendor_b} 합계']

                # 총계 계산
                total_a = df_merged[f'{vendor_a} 합계'].sum()
                total_b = df_merged[f'{vendor_b} 합계'].sum()
                total_diff = total_a - total_b

                # 화면 표시용 컬럼
                display_cols = [
                    item_col, '통합규격', '수량', 
                    f'{vendor_a} 단가', f'{vendor_b} 단가', '단가 차액',
                    f'{vendor_a} 합계', f'{vendor_b} 합계', 
                    '총 차액'
                ]
                
                # 테이블 출력 (모바일 최적화 use_container_width=True)
                st.dataframe(
                    df_merged[display_cols].style.format({
                        f'{vendor_a} 단가': "{:,.0f}원",
                        f'{vendor_b} 단가': "{:,.0f}원",
                        '단가 차액': "{:+,.0f}원",
                        f'{vendor_a} 합계': "{:,.0f}원",
                        f'{vendor_b} 합계': "{:,.0f}원",
                        '총 차액': "{:+,.0f}원"
                    }).map(lambda x: 'color: blue; font-weight: bold' if x > 0 else ('color: red' if x < 0 else 'color: gray'), subset=['총 차액'])
                      .map(lambda x: 'color: red' if x > 0 else ('color: blue' if x < 0 else 'color: gray'), subset=['단가 차액']), # 단가차액은 B가 더 비싸면(양수) 빨강
                    use_container_width=True,
                    hide_index=True
                )

                # 리스트 초기화 버튼
                if st.button("🗑️ 전체 삭제", type="secondary", use_container_width=True):
                    st.session_state.quote_list = []
                    st.rerun()

                # ---------------------------------------------------------
                # 5. 최종 결과 요약 (화면 하단 배치)
                # ---------------------------------------------------------
                st.markdown("---")
                st.markdown("### 📊 최종 견적 비교 결과")
                
                result_container = st.container()
                
                # 시각적으로 강조된 박스 스타일
                with result_container:
                    c_res1, c_res2 = st.columns(2)
                    c_res1.metric(label=f"{vendor_a} 총 합계", value=f"{int(total_a):,}원")
                    c_res2.metric(label=f"{vendor_b} 총 합계", value=f"{int(total_b):,}원")

                    # 결론 메시지 박스
                    if total_diff > 0:
                        st.success(f"### 🎉 최종 결론: [{vendor_b}]에서 구매 시 [{int(total_diff):,}원] 더 이득입니다!")
                    elif total_diff < 0:
                        st.error(f"### 🚨 최종 결론: [{vendor_b}]가 [{int(abs(total_diff)):,}원] 더 비쌉니다. [{vendor_a}] 추천!")
                    else:
                        st.info(f"### ⚖️ 최종 결론: 두 업체의 견적 금액이 동일합니다.")

            else:
                st.info("견적서가 비어있습니다. 위에서 품목을 추가해주세요.")

        except Exception as e:
            st.error("처리 중 오류가 발생했습니다.")
            st.exception(e)

if __name__ == "__main__":
    main()
