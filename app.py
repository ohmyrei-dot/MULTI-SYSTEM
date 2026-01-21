import streamlit as st
import pandas as pd
import os
import re

# -----------------------------------------------------------------------------
# 1. 페이지 공통 설정 (전역 설정)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="스마트 견적서 및 단가 관리",
    page_icon="📊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 매입 견적 비교 시스템 (기존 로직 유지)
# -----------------------------------------------------------------------------
def run_purchase_system():
    # CSS: 제목 줄바꿈 설정
    st.markdown("""
    <style>
    h1 { word-break: keep-all; }
    </style>
    """, unsafe_allow_html=True)

    st.title("📝 스마트\u00A0견적서 작성\u00A0시스템")
    st.markdown("원하는 품목을 **직접 선택**하여 견적서에 추가하세요.")

    if 'quote_list' not in st.session_state:
        st.session_state.quote_list = []

    file_path = '단가표.xlsx'
    
    if not os.path.exists(file_path):
        st.error(f"🚨 '{file_path}' 파일을 찾을 수 없습니다.")
        st.info("깃허브 저장소의 최상위 경로에 '단가표.xlsx' 파일을 업로드해주세요.")
        return

    try:
        # [데이터 로드] 매입 견적 시트
        df_raw = pd.read_excel(file_path, sheet_name='Purchase_매입단가')
        
        cols = df_raw.columns.tolist()
        vendor_col = next((c for c in cols if '업체' in c or '거래처' in c), None)
        item_col = next((c for c in cols if '품목' in c or '품명' in c), None)
        price_col = next((c for c in cols if '단가' in c or '매입가' in c or '가격' in c), None)
        spec_cols = [c for c in cols if '규격' in c]

        if not (vendor_col and item_col and price_col):
            st.error("엑셀 파일 형식을 확인해주세요. (필수 컬럼: 업체명, 품목명, 단가)")
            return

        def combine_specs(row):
            specs = [str(row[c]) for c in spec_cols if pd.notna(row[c]) and str(row[c]).strip() != '']
            return ' '.join(specs) if specs else '-'
        df_raw['통합규격'] = df_raw.apply(combine_specs, axis=1)

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

        c1, c2 = st.columns(2)
        
        def get_index(options, target):
            try:
                return list(options).index(target)
            except ValueError:
                return 0

        idx_a = get_index(vendors, '솔트룩스')
        with c1:
            vendor_a = st.selectbox("기준 업체 (A)", vendors, index=idx_a)

        target_b = '태양산자'
        idx_b = get_index(vendors, target_b) if target_b in vendors else (1 if len(vendors) > 1 else 0)
        with c2:
            vendor_b = st.selectbox("비교 업체 (B)", vendors, index=idx_b)

        st.divider()
        st.subheader("➕ 품목 추가하기")
        
        with st.container():
            col_input1, col_input2, col_input3, col_btn = st.columns([2, 2, 1, 1])

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

            available_specs = df_pivot[df_pivot[item_col] == selected_item]['통합규격'].unique().tolist()
            selected_spec = col_input2.selectbox("규격 선택", available_specs, key="sel_spec")

            input_qty = col_input3.number_input("수량", min_value=1, value=1, step=1, key="in_qty")

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

        st.divider()
        st.subheader(f"📋 견적 리스트 ({len(st.session_state.quote_list)}건)")

        if st.session_state.quote_list:
            df_quote = pd.DataFrame(st.session_state.quote_list)

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

            view_mode = st.radio(
                "화면 모드 선택", 
                ["🖥️ PC (표)", "📱 모바일 (카드)"], 
                horizontal=True, 
                label_visibility="collapsed"
            )

            if view_mode == "🖥️ PC (표)":
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
                for idx, row in df_merged.iterrows():
                    with st.container(border=True):
                        mc1, mc2 = st.columns([8, 2])
                        mc1.markdown(f"**{row[item_col]}**")
                        if mc2.button("🗑️", key=f"del_mo_{row['id']}"):
                            st.session_state.quote_list = [x for x in st.session_state.quote_list if x['id'] != row['id']]
                            st.rerun()
                        
                        st.text(f"규격: {row['통합규격']} | 수량: {row['수량']:,}개")
                        st.markdown("---")
                        
                        mc3, mc4 = st.columns(2)
                        with mc3:
                            st.markdown(f"**{vendor_a}**")
                            st.markdown(f"단가: {int(row[f'{vendor_a} 단가']):,}원 | 합계: {int(row[f'{vendor_a} 합계']):,}원")
                        with mc4:
                            st.markdown(f"**{vendor_b}**")
                            st.markdown(f"단가: {int(row[f'{vendor_b} 단가']):,}원 | 합계: {int(row[f'{vendor_b} 합계']):,}원")
                        
                        t_diff = row['총 차액']
                        if t_diff > 0:
                            st.success(f"💰 {vendor_b}가 {int(t_diff):,}원 더 저렴함 (이득)")
                        elif t_diff < 0:
                            st.error(f"💸 {vendor_b}가 {int(abs(t_diff)):,}원 더 비쌈 (손해)")
                        else:
                            st.info("가격 동일")

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


# -----------------------------------------------------------------------------
# 3. 매출 단가 조회 시스템 (구조 개편)
# -----------------------------------------------------------------------------
def run_sales_system():
    st.title("📈 매출 단가 조회")
    st.markdown("품목별 매출 단가를 한눈에 비교하고 히스토리를 확인합니다.")
    
    file_path = '단가표.xlsx'
    if not os.path.exists(file_path):
        st.error(f"🚨 '{file_path}' 파일이 없습니다.")
        return

    try:
        # 1. 데이터 로드 (시트명: Sales_매출단가)
        df_sales = pd.read_excel(file_path, sheet_name='Sales_매출단가')
        
        # 컬럼명 유효성 검사 (사용자 요청 컬럼: 품목, 규격, 비고 1, 매출업체, 현재매출단가)
        # '비고 1'이 없을 경우 '비고'로 대체 처리
        note_col = '비고 1' if '비고 1' in df_sales.columns else '비고'
        if note_col not in df_sales.columns:
            # 비고 컬럼이 아예 없으면 빈 컬럼 생성
            df_sales[note_col] = ""
            
        required_cols = ['품목', '규격', '매출업체', '현재매출단가']
        missing_cols = [c for c in required_cols if c not in df_sales.columns]
        
        if missing_cols:
            st.error(f"엑셀 파일에 필수 컬럼이 없습니다: {missing_cols}")
            return

        # -----------------------------------------------------------
        # 2. 정렬 로직 (엄격한 규칙 적용)
        # -----------------------------------------------------------
        
        # (1) 품목 우선순위
        priority_items = ['안전망1cm', '안전망2cm', 'pp로프', '와이어로프', '와이어클립', '멀티망', '럿셀망', '케이블타이']
        priority_map = {item: i for i, item in enumerate(priority_items)}
        
        # (2) 비고 우선순위 (KS포함 -> KS없는것 -> KS로프가공 -> 로프가공)
        def get_note_rank(note):
            s = str(note).strip()
            if s == 'KS로프가공': return 2
            if s == '로프가공': return 3
            if 'KS' in s: return 0  # KS 포함
            return 1  # KS 없는 것 (nan 등 포함)

        # (3) 규격 오름차순 (숫자 추출)
        def extract_spec_number(spec):
            if pd.isna(spec): return float('inf')
            match = re.search(r'\d+(\.\d+)?', str(spec))
            if match:
                return float(match.group())
            return float('inf')

        # 정렬용 임시 컬럼 생성
        df_sales['rank_item'] = df_sales['품목'].map(lambda x: priority_map.get(x, 999))
        df_sales['rank_note'] = df_sales[note_col].apply(get_note_rank)
        df_sales['rank_spec'] = df_sales['규격'].apply(extract_spec_number)

        # 원본 데이터 정렬
        df_sorted = df_sales.sort_values(
            by=['rank_item', 'rank_note', 'rank_spec'],
            ascending=[True, True, True]
        )

        # -----------------------------------------------------------
        # 3. 피벗 테이블 생성 및 레이아웃
        # -----------------------------------------------------------
        
        # 피벗 생성 (인덱스: 품목, 규격, 비고 / 컬럼: 매출업체 / 값: 현재매출단가)
        # pivot_table을 쓰면 정렬이 인덱스 알파벳순으로 바뀔 수 있으므로 주의 필요
        # 따라서 위에서 정렬한 순서(index)를 기억했다가 reindex로 복구하거나
        # 정렬된 유니크 키 리스트를 만들어야 함.
        
        # 정렬된 순서대로 유니크한 인덱스 키 추출 (중복 제거하되 순서 유지)
        unique_keys = df_sorted[['품목', '규격', note_col]].drop_duplicates()
        
        # 피벗 테이블 생성
        df_pivot = df_sorted.pivot_table(
            index=['품목', '규격', note_col],
            columns='매출업체',
            values='현재매출단가',
            aggfunc='first' # 중복 시 첫 번째 값
        )
        
        # 피벗 후 인덱스가 자동 정렬되어버리므로, 아까 추출한 unique_keys 순서대로 재정렬(Reindex)
        # unique_keys를 MultiIndex로 변환
        target_index = pd.MultiIndex.from_frame(unique_keys)
        # reindex 수행 (존재하는 키만 사용)
        df_pivot = df_pivot.reindex(target_index)
        
        # 인덱스 이름 정리
        df_pivot.index.names = ['품목', '규격', note_col]

        # -----------------------------------------------------------
        # 4. 화면 출력 (피벗 테이블)
        # -----------------------------------------------------------
        st.subheader("📋 업체별 현재 매출단가 비교")
        st.caption("💡 가로로 스크롤하여 업체별 단가를 비교하세요.")
        
        # 컬럼 설정 (비고 너비 확보 등)
        # Streamlit Dataframe 설정
        st.dataframe(
            df_pivot,
            use_container_width=True,
            column_config={
                note_col: st.column_config.TextColumn(
                    note_col,
                    width="medium", # 너비 확보
                    help="비고 사항"
                )
            }
        )
        
        st.divider()

        # -----------------------------------------------------------
        # 5. 업체별 히스토리 조회 (하단 영역)
        # -----------------------------------------------------------
        st.subheader("📜 업체별 단가 변동 히스토리")
        
        hc1, hc2 = st.columns(2)
        
        # (1) 업체 선택
        all_vendors = sorted(df_sales['매출업체'].unique().astype(str))
        with hc1:
            sel_vendor = st.selectbox("업체 선택", all_vendors)
            
        # (2) 품목 선택 (해당 업체의 품목만 필터링 or 전체 품목)
        # 편의를 위해 정렬된 순서대로 품목 리스트 제공
        vendor_items_df = df_sorted[df_sorted['매출업체'] == sel_vendor]
        # 품목+규격+비고를 합쳐서 보여주면 선택이 쉬움
        vendor_items_df['display_name'] = vendor_items_df.apply(
            lambda x: f"{x['품목']} | {x['규격']} ({x[note_col]})", axis=1
        )
        
        item_options = vendor_items_df['display_name'].unique().tolist()
        
        with hc2:
            sel_item_display = st.selectbox("품목 선택 (규격/비고 포함)", item_options)

        if sel_vendor and sel_item_display:
            # 선택한 정보로 해당 행 찾기
            selected_row = vendor_items_df[vendor_items_df['display_name'] == sel_item_display].iloc[0]
            
            st.markdown(f"**[{sel_vendor}]** - **{sel_item_display}** 의 과거 단가 내역")
            
            # 과거 단가 컬럼 찾기 및 데이터 추출
            # 규칙: 컬럼명에 날짜가 있거나 '과거매출단가'가 포함된 열
            history_data = {}
            
            for col in df_sales.columns:
                # 메타 데이터 제외
                if col in ['품목', '규격', note_col, '매출업체', '현재매출단가', 'rank_item', 'rank_note', 'rank_spec']:
                    continue
                
                # 값 가져오기
                val = selected_row.get(col)
                if pd.isna(val) or val == 0:
                    continue
                
                # 컬럼명 정제 (사용자 요청: '과거매출단가' 문구 제거)
                # 예: '과거매출단가_24/10/01' -> '24/10/01'
                # 단순히 문자열 치환 or 정규식 사용
                clean_col_name = str(col).replace('과거매출단가', '').replace('_', ' ').strip()
                
                # 날짜 형식으로 변환 시도 (그래프 정렬용)
                # 단순 문자열로 저장하되, 딕셔너리 키로 사용
                history_data[clean_col_name] = val

            # 현재 단가도 그래프에 포함할지 여부 -> 보통 히스토리는 과거+현재
            # 현재 단가 추가 (날짜가 오늘이라 가정하거나 '현재'로 표시)
            # 여기서는 과거 내역만 보여달라는 요청에 집중하되, 데이터가 있으면 표시
            
            if history_data:
                # 데이터프레임 변환
                hist_df = pd.DataFrame(list(history_data.items()), columns=['날짜', '단가'])
                
                # 날짜 컬럼을 실제 datetime으로 변환하여 정렬 시도
                # 변환 실패하는 텍스트(예: '비고2')는 제외하거나 맨 뒤로
                def try_parse_date(x):
                    try:
                        return pd.to_datetime(x, format='%y/%m/%d', errors='ignore') # 포맷은 예시
                    except:
                        return x

                # 정렬을 위해 임시 변환
                hist_df['dt'] = pd.to_datetime(hist_df['날짜'], errors='coerce')
                hist_df = hist_df.sort_values(by='dt')
                
                # 차트 그리기
                st.line_chart(hist_df.set_index('날짜')['단가'])
                
                # 표로도 보여주기 (가로로)
                st.dataframe(hist_df[['날짜', '단가']].T, use_container_width=True)
            else:
                st.info("과거 단가 기록이 없습니다.")

    except Exception as e:
        st.error(f"오류 발생: {e}")

# -----------------------------------------------------------------------------
# 4. 메인 실행 컨트롤러
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    menu = st.sidebar.selectbox("기능 선택", ["매입 견적 비교", "매출 단가 조회"])
    
    if menu == "매입 견적 비교":
        run_purchase_system()
    elif menu == "매출 단가 조회":
        run_sales_system()
