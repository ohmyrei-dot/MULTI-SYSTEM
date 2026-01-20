import streamlit as st
import pandas as pd
import os

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

    # ---------------------------------------------------------
    # 1. 데이터 자동 로드 (단가표.xlsx)
    # ---------------------------------------------------------
    file_path = '단가표.xlsx'
    
    # 파일 존재 여부 확인 및 로드
    if not os.path.exists(file_path):
        st.error(f"🚨 '{file_path}' 파일을 찾을 수 없습니다.")
        st.info("깃허브 저장소의 최상위 경로에 '단가표.xlsx' 파일을 업로드해주세요.")
        return

    try:
        # 데이터 로드
        df_raw = pd.read_excel(file_path)
        
        # 컬럼명 자동 감지
        cols = df_raw.columns.tolist()
        vendor_col = next((c for c in cols if '업체' in c or '거래처' in c), None)
        item_col = next((c for c in cols if '품목' in c or '품명' in c), None)
        price_col = next((c for c in cols if '단가' in c or '매입가' in c or '가격' in c), None)
        spec_cols = [c for c in cols if '규격' in c]

        if not (vendor_col and item_col and price_col):
            st.error("엑셀 파일 형식을 확인해주세요. (필수 컬럼: 업체명, 품목명, 단가)")
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
            priority_keywords = ['안전망', 'PP로프', '와이어로프', '와이어클립', '멀티망', '럿셀망', '케이블타이', 'PE로프']
            
            sorted_items = []
            used_items = set()

            for kw in priority_keywords:
                matches = sorted([x for x in raw_items if kw in str(x) and x not in used_items])
                sorted_items.extend(matches)
                used_items.update(matches)
            
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
        # 4. 견적 리스트 (반응형 디자인 적용)
        # ---------------------------------------------------------
        st.divider()
        st.subheader(f"📋 견적 리스트 ({len(st.session_state.quote_list)}건)")

        if st.session_state.quote_list:
            df_quote = pd.DataFrame(st.session_state.quote_list)

            # 데이터 병합 및 계산
            df_merged = pd.merge(
                df_quote, 
                df_pivot[[item_col, '통합규격', vendor_a, vendor_b]], 
                on=[item_col, '통합규격'], 
                how='left'
            )

            df_merged[f'{vendor_a} 단가'] = df_merged[vendor_a].fillna(0)
            df_merged[f'{vendor_b} 단가'] = df_merged[vendor_b].fillna(0)
            df_merged['단가 차액'] = df_merged[f'{vendor_b} 단가'] - df_merged[f'{vendor_a} 단가']
            df_merged[f'{vendor_a} 합계'] = df_merged[f'{vendor_a} 단가'] * df_merged['수량']
            df_merged[f'{vendor_b} 합계'] = df_merged[f'{vendor_b} 단가'] * df_merged['수량']
            df_merged['총 차액'] = df_merged[f'{vendor_a} 합계'] - df_merged[f'{vendor_b} 합계']

            total_a = df_merged[f'{vendor_a} 합계'].sum()
            total_b = df_merged[f'{vendor_b} 합계'].sum()
            total_diff = total_a - total_b

            # 보기 모드 선택 (기본값을 PC로 변경)
            view_mode = st.radio(
                "화면 모드 선택", 
                ["🖥️ PC (표)", "📱 모바일 (카드)"], 
                horizontal=True, 
                label_visibility="collapsed"
            )

            if view_mode == "🖥️ PC (표)":
                # --- PC 버전: 기존 표 형태 유지 ---
                ratio = [0.5, 1.5, 1.2, 0.7, 1, 1, 1, 1.1, 1.1, 1.1]
                h_cols = st.columns(ratio)
                h_cols[0].markdown("**삭제**")
                h_cols[1].markdown("**품목**")
                h_cols[2].markdown("**규격**")
                h_cols[3].markdown("**수량**")
                h_cols[4].markdown(f"**{vendor_a}<br>단가**", unsafe_allow_html=True)
                h_cols[5].markdown(f"**{vendor_b}<br>단가**", unsafe_allow_html=True)
                h_cols[6].markdown("**단가<br>차액**", unsafe_allow_html=True)
                h_cols[7].markdown(f"**{vendor_a}<br>합계**", unsafe_allow_html=True)
                h_cols[8].markdown(f"**{vendor_b}<br>합계**", unsafe_allow_html=True)
                h_cols[9].markdown("**총 차액<br>(이득)**", unsafe_allow_html=True)
                st.markdown("---")

                for idx, row in df_merged.iterrows():
                    cols = st.columns(ratio)
                    
                    if cols[0].button("🗑️", key=f"del_pc_{row['id']}"):
                        st.session_state.quote_list = [x for x in st.session_state.quote_list if x['id'] != row['id']]
                        st.rerun()

                    cols[1].text(row[item_col])
                    cols[2].text(row['통합규격'])
                    cols[3].text(f"{row['수량']:,}")
                    cols[4].text(f"{int(row[f'{vendor_a} 단가']):,}원")
                    cols[5].text(f"{int(row[f'{vendor_b} 단가']):,}원")
                    
                    u_diff = row['단가 차액']
                    if u_diff > 0: cols[6].markdown(f":red[+{int(u_diff):,}원]")
                    elif u_diff < 0: cols[6].markdown(f":blue[{int(u_diff):,}원]")
                    else: cols[6].text("-")

                    cols[7].text(f"{int(row[f'{vendor_a} 합계']):,}원")
                    cols[8].text(f"{int(row[f'{vendor_b} 합계']):,}원")

                    t_diff = row['총 차액']
                    if t_diff > 0: cols[9].markdown(f":blue[**+{int(t_diff):,}원**]") 
                    elif t_diff < 0: cols[9].markdown(f":red[{int(t_diff):,}원]")
                    else: cols[9].text("-")

            else:
                # --- 모바일 버전: 카드(Card) 형태 ---
                for idx, row in df_merged.iterrows():
                    with st.container(border=True):
                        # 헤더: 품목명 + 삭제 버튼
                        mc1, mc2 = st.columns([8, 2])
                        mc1.markdown(f"**{row[item_col]}**")
                        if mc2.button("🗑️", key=f"del_mo_{row['id']}"):
                            st.session_state.quote_list = [x for x in st.session_state.quote_list if x['id'] != row['id']]
                            st.rerun()
                        
                        # 규격 및 수량
                        st.text(f"규격: {row['통합규격']} | 수량: {row['수량']:,}개")
                        st.markdown("---")
                        
                        # 업체별 가격 비교 (단가/합계 한줄 표시)
                        mc3, mc4 = st.columns(2)
                        with mc3:
                            st.markdown(f"**{vendor_a}**")
                            st.markdown(f"단가: {int(row[f'{vendor_a} 단가']):,}원 | 합계: {int(row[f'{vendor_a} 합계']):,}원")
                        
                        with mc4:
                            st.markdown(f"**{vendor_b}**")
                            st.markdown(f"단가: {int(row[f'{vendor_b} 단가']):,}원 | 합계: {int(row[f'{vendor_b} 합계']):,}원")
                        
                        # 최종 차액 강조
                        t_diff = row['총 차액']
                        if t_diff > 0:
                            st.success(f"💰 {vendor_b}가 {int(t_diff):,}원 더 저렴함 (이득)")
                        elif t_diff < 0:
                            st.error(f"💸 {vendor_b}가 {int(abs(t_diff)):,}원 더 비쌈 (손해)")
                        else:
                            st.info("가격 동일")

            # ---------------------------------------------------------
            # 5. 최종 결과 요약 (화면 하단 배치)
            # ---------------------------------------------------------
            st.markdown("---")
            
            _, del_col = st.columns([5, 1])
            if del_col.button("🗑️ 리스트 전체 비우기", type="secondary"):
                st.session_state.quote_list = []
                st.rerun()

            st.markdown("### 📊 최종 견적 비교 결과")
            result_container = st.container()
            
            with result_container:
                c_res1, c_res2 = st.columns(2)
                c_res1.metric(label=f"{vendor_a} 총 합계", value=f"{int(total_a):,}원")
                c_res2.metric(label=f"{vendor_b} 총 합계", value=f"{int(total_b):,}원")

                if total_diff > 0:
                    st.success(f"### 🎉 최종 결론: [{vendor_b}]에서 구매 시 [{int(total_diff):,}원] 더 이득입니다!")
                elif total_diff < 0:
                    st.error(f"### 🚨 최종 결론: [{vendor_b}]가 [{int(abs(total_diff)):,}원] 더 비쌉니다. [{vendor_a}] 추천!")
                else:
                    st.info(f"### ⚖️ 최종 결론: 두 업체의 견적 금액이 동일합니다.")

        else:
            st.info("견적서가 비어있습니다. 위에서 품목을 추가해주세요.")

    except Exception as e:
        st.error("오류가 발생했습니다.")
        st.error(f"상세 내용: {str(e)}")

if __name__ == "__main__":
    main()
