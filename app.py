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
# 2. 매입 견적 비교 시스템
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
        # [수정 1] 시트 이름 변경: 'Purchase_매입단가'
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
# 3. 매출 단가 조회 시스템 (규칙 정렬 및 그래프 기능 추가)
# -----------------------------------------------------------------------------
def run_sales_system():
    st.title("📈 매출 단가 조회")
    st.markdown("매출 단가를 확인하고 과거 변동 내역을 조회합니다.")
    
    file_path = '단가표.xlsx'
    
    if not os.path.exists(file_path):
        st.error(f"🚨 '{file_path}' 파일이 없습니다.")
        return

    try:
        # [수정 1] 시트 이름 변경: 'Sales_매출단가'
        df_sales = pd.read_excel(file_path, sheet_name='Sales_매출단가')
        
        # [수정 2] 품목 정렬 로직 (Custom Sorting)
        # 1. 품목 우선순위 목록
        priority_items = ['안전망1cm', '안전망2cm', 'pp로프', '와이어로프', '와이어클립', '멀티망', '럿셀망', '케이블타이']
        priority_map = {item: i for i, item in enumerate(priority_items)}

        # 2. 비고 우선순위 목록
        # [KS] -> [빈값/None] -> [KS로프가공] -> [로프가공]
        def get_note_rank(note):
            note = str(note).strip()
            if note == 'KS': return 0
            if note == 'nan' or note == '' or note == 'None': return 1
            if note == 'KS로프가공': return 2
            if note == '로프가공': return 3
            return 4 # 그 외

        # 3. 규격 숫자 추출 (오름차순용)
        def extract_spec_number(spec):
            if pd.isna(spec): return float('inf')
            # 문자열에서 첫 번째 숫자(정수 혹은 소수) 추출
            match = re.search(r'\d+(\.\d+)?', str(spec))
            if match:
                return float(match.group())
            return float('inf') # 숫자가 없으면 뒤로 보냄

        # 정렬을 위한 임시 컬럼 생성
        df_sales['temp_item_rank'] = df_sales['품목'].map(lambda x: priority_map.get(x, 999)) # 없으면 999
        
        # '비고' 컬럼이 있는지 확인 후 랭크 매핑
        if '비고' in df_sales.columns:
            df_sales['temp_note_rank'] = df_sales['비고'].apply(get_note_rank)
        else:
            df_sales['temp_note_rank'] = 1 # 비고 없으면 기본값

        # '규격' 컬럼이 있는지 확인 후 숫자 추출
        if '규격' in df_sales.columns:
            df_sales['temp_spec_num'] = df_sales['규격'].apply(extract_spec_number)
        else:
            df_sales['temp_spec_num'] = 0

        # 정렬 적용 (품목우선순위 -> 비고순 -> 규격숫자순)
        df_sales = df_sales.sort_values(
            by=['temp_item_rank', 'temp_note_rank', 'temp_spec_num'],
            ascending=[True, True, True]
        )

        # 임시 컬럼 제거 (화면에 안보이게)
        df_display = df_sales.drop(columns=['temp_item_rank', 'temp_note_rank', 'temp_spec_num'])

        # --- 필터링 UI ---
        st.sidebar.header("🔍 검색 필터")
        
        # 품목 필터 (정렬된 순서대로 표시)
        all_items = df_sales['품목'].unique().tolist() # 이미 정렬됨
        # '전체' 옵션을 맨 앞에 추가
        filter_item = st.sidebar.selectbox("품목 선택", ["전체"] + all_items)
        
        if filter_item != "전체":
            df_display = df_display[df_display['품목'] == filter_item]
            # 규격 필터는 품목 선택 시에만 해당 품목의 규격으로 좁힘
            if '규격' in df_display.columns:
                available_specs = df_display['규격'].unique().tolist()
                filter_spec = st.sidebar.selectbox("규격 선택", ["전체"] + list(map(str, available_specs)))
                if filter_spec != "전체":
                    df_display = df_display[df_display['규격'].astype(str) == filter_spec]

        # --- [수정 3] 화면 구성 및 선택 기능 ---
        st.subheader("📋 매출 단가표 (행을 선택하면 그래프가 표시됩니다)")
        
        # 데이터프레임 표시 (선택 가능하게 설정)
        event = st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",  # 선택 시 리런
            selection_mode="single-row" # 한 줄만 선택
        )

        # --- [수정 3-1] 그래프 그리기 ---
        if event.selection.rows:
            selected_index = event.selection.rows[0]
            # 필터링된 데이터프레임(df_display) 기준으로 행 추출
            # 주의: df_display는 인덱스가 재설정되지 않았을 수 있으므로 iloc 사용
            selected_row = df_display.iloc[selected_index]
            
            st.divider()
            st.subheader(f"📈 단가 변동 그래프: {selected_row.get('품목', '품목')} {selected_row.get('규격', '')}")
            
            # 날짜 형식의 컬럼만 찾아서 그래프 데이터 생성
            # (컬럼명이 날짜로 변환 가능한 경우를 찾음)
            date_price_data = {}
            for col in df_display.columns:
                # 품목, 규격, 비고 등 메타데이터 컬럼 제외
                if str(col) in ['품목', '규격', '비고', '단위', '업체']:
                    continue
                
                # 컬럼명이 날짜인지 확인
                try:
                    # 엑셀 날짜 헤더는 보통 datetime 객체거나 '2024-01-01' 같은 문자열
                    dt = pd.to_datetime(col)
                    val = selected_row[col]
                    # 값이 숫자일 때만 추가
                    if pd.notnull(val) and isinstance(val, (int, float)):
                        date_price_data[dt] = val
                except:
                    continue # 날짜가 아니면 패스

            if date_price_data:
                chart_df = pd.DataFrame(list(date_price_data.items()), columns=['날짜', '단가'])
                chart_df = chart_df.sort_values('날짜')
                st.line_chart(chart_df.set_index('날짜'))
            else:
                st.info("이 품목은 날짜별 단가 데이터(열)가 없습니다.")

    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")

# -----------------------------------------------------------------------------
# 4. 메인 실행 컨트롤러
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    menu = st.sidebar.selectbox("기능 선택", ["매입 견적 비교", "매출 단가 조회"])
    
    if menu == "매입 견적 비교":
        run_purchase_system()
    elif menu == "매출 단가 조회":
        run_sales_system()
