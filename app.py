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

    # [Helper] 매입 견적용 Natural Sort Key 함수
    def purchase_sort_key(s):
        text = str(s).strip()
        match = re.search(r'(\d+(\.\d+)?)', text)
        if match:
            num_val = float(match.group(1))
        else:
            num_val = float('inf')
            
        if 'KS' in text:
            keyword_rank = 0
        elif '가공' in text:
            keyword_rank = 2
        else:
            keyword_rank = 1
            
        return (num_val, keyword_rank, text)

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

            # 1) 품목 선택 (Natural Sort 적용)
            raw_items = df_pivot[item_col].unique().tolist()
            priority_keywords = ['안전망', 'PP로프', '와이어로프', '와이어클립', '멀티망', '럿셀망', '케이블타이', 'PE로프']
            
            sorted_items = []
            used_items = set()

            for kw in priority_keywords:
                matches = sorted(
                    [x for x in raw_items if kw in str(x) and x not in used_items],
                    key=purchase_sort_key
                )
                sorted_items.extend(matches)
                used_items.update(matches)
            
            others = sorted(
                [x for x in raw_items if x not in used_items],
                key=purchase_sort_key
            )
            final_item_list = sorted_items + others

            selected_item = col_input1.selectbox("품목 선택", final_item_list, key="sel_item")

            # 2) 규격 선택 (Natural Sort 적용)
            available_specs = df_pivot[df_pivot[item_col] == selected_item]['통합규격'].unique().tolist()
            available_specs = sorted(available_specs, key=purchase_sort_key)
            
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
# 3. 매출 단가 조회 시스템 (열 정렬 기능 추가)
# -----------------------------------------------------------------------------
def run_sales_system():
    st.title("📈 매출 단가 조회")
    st.markdown("품목별 매출 단가를 한눈에 비교하고 히스토리를 확인합니다.")
    
    file_path = '단가표.xlsx'
    if not os.path.exists(file_path):
        st.error(f"🚨 '{file_path}' 파일이 없습니다.")
        return

    try:
        # 1. 데이터 로드
        df_sales = pd.read_excel(file_path, sheet_name='Sales_매출단가')
        
        # 컬럼 처리
        note_col = '비고 1' if '비고 1' in df_sales.columns else '비고'
        if note_col not in df_sales.columns: df_sales[note_col] = ""
        if '단위' not in df_sales.columns: df_sales['단위'] = ""

        # '현재매출단가' 열 찾기
        current_price_col = next((c for c in df_sales.columns if '현재매출단가' in str(c)), None)
            
        required_cols = ['품목', '규격', '매출업체']
        if not all(col in df_sales.columns for col in required_cols):
            st.error("엑셀 파일에 필수 컬럼(품목, 규격, 매출업체)이 없습니다.")
            return
        if not current_price_col:
            st.error("엑셀 파일에 '현재매출단가'가 포함된 열을 찾을 수 없습니다.")
            return

        # -----------------------------------------------------------
        # [모드 선택]
        # -----------------------------------------------------------
        price_mode = st.radio("단가 표시 방식", ["기본 단가", "단위당 단가"], horizontal=True)

        # -----------------------------------------------------------
        # 2. 정렬 로직 (Natural Sort)
        # -----------------------------------------------------------
        priority_items = ['안전망1cm', '안전망2cm', 'pp로프', '와이어로프', '와이어클립', '멀티망', '럿셀망', '케이블타이']
        priority_map = {item: i for i, item in enumerate(priority_items)}
        
        def get_note_type_rank(note):
            s = str(note).strip()
            if s == 'KS로프가공': return 2
            if s == '로프가공': return 3
            if 'KS' in s: return 0
            return 1

        def extract_number(text):
            if pd.isna(text): return float('inf')
            match = re.search(r'\d+(\.\d+)?', str(text))
            if match:
                return float(match.group())
            return float('inf')

        # 랭크 컬럼 생성
        df_sales['rank_item'] = df_sales['품목'].map(lambda x: priority_map.get(x, 999))
        df_sales['rank_note_type'] = df_sales[note_col].apply(get_note_type_rank)
        df_sales['rank_note_num'] = df_sales[note_col].apply(extract_number)
        df_sales['rank_spec_num'] = df_sales['규격'].apply(extract_number)

        # 전체 데이터 정렬
        df_sorted = df_sales.sort_values(
            by=['rank_item', 'rank_note_type', 'rank_note_num', 'rank_spec_num'],
            ascending=[True, True, True, True]
        )

        # -----------------------------------------------------------
        # 3. 데이터 필터 (PC 레이아웃 & 전체 선택 기능)
        # -----------------------------------------------------------
        st.subheader("🔍 데이터 필터")
        
        # (1) 상단: 업체 선택
        all_vendors = sorted(df_sales['매출업체'].dropna().unique().astype(str))
        vendor_options = ['전체 선택'] + all_vendors
        
        # 기본 선택 (토우코리아 포함)
        default_targets = ['가온건설', '신영산업안전', '네오이앤씨', '동원', '우주안전', '세종스틸', '제이엠산업개발', '전진산업안전', '씨에스산업건설', '타포', '경원안전', '토우코리아']
        default_vendor_selection = [v for v in default_targets if v in all_vendors]

        selected_vendors_raw = st.multiselect(
            "🏢 조회할 업체 선택",
            options=vendor_options,
            default=default_vendor_selection
        )

        if '전체 선택' in selected_vendors_raw:
            final_selected_vendors = all_vendors
        else:
            final_selected_vendors = selected_vendors_raw

        # (2) 하단: 품목 / 규격 / 비고 (3분할)
        fc1, fc2, fc3 = st.columns(3)
        
        # -- 품목 --
        all_items_sorted = df_sorted['품목'].unique().tolist()
        item_options = ['전체 선택'] + all_items_sorted
        
        with fc1:
            selected_items_raw = st.multiselect(
                "📦 품목",
                options=item_options,
                default=[]
            )
        
        if not selected_items_raw or '전체 선택' in selected_items_raw:
            df_filtered_step1 = df_sorted # 전체
        else:
            df_filtered_step1 = df_sorted[df_sorted['품목'].isin(selected_items_raw)]

        # -- 규격 --
        available_specs = df_filtered_step1['규격'].unique().tolist()
        spec_options = ['전체 선택'] + available_specs
        
        with fc2:
            selected_specs_raw = st.multiselect(
                "📏 규격",
                options=spec_options,
                default=[]
            )
        
        if not selected_specs_raw or '전체 선택' in selected_specs_raw:
            df_filtered_step2 = df_filtered_step1
        else:
            df_filtered_step2 = df_filtered_step1[df_filtered_step1['규격'].isin(selected_specs_raw)]

        # -- 비고 --
        available_notes = df_filtered_step2[note_col].unique().tolist()
        note_options = ['전체 선택'] + available_notes
        
        with fc3:
            selected_notes_raw = st.multiselect(
                "📝 비고",
                options=note_options,
                default=[]
            )
        
        if not selected_notes_raw or '전체 선택' in selected_notes_raw:
            df_final = df_filtered_step2
        else:
            df_final = df_filtered_step2[df_filtered_step2[note_col].isin(selected_notes_raw)]

        # -----------------------------------------------------------
        # 4. 피벗 테이블 및 데이터 존재 행 필터링
        # -----------------------------------------------------------
        unique_keys = df_final[['품목', '규격', note_col, '단위']].drop_duplicates()
        
        if not df_final.empty:
            df_pivot = df_final.pivot_table(
                index=['품목', '규격', note_col, '단위'],
                columns='매출업체',
                values=current_price_col,
                aggfunc='first'
            )
            
            # 인덱스 순서 복구
            target_index = pd.MultiIndex.from_frame(unique_keys)
            final_index = target_index.intersection(df_pivot.index)
            final_index = target_index[target_index.isin(final_index)]
            
            df_pivot = df_pivot.reindex(final_index)
            df_pivot.index.names = ['품목', '규격', note_col, '단위']

            # 업체 필터링
            pivot_columns = df_pivot.columns
            valid_columns = []
            clean_selected_vendors = [str(v).replace(' ', '') for v in final_selected_vendors]
            
            for col in pivot_columns:
                if str(col).replace(' ', '') in clean_selected_vendors:
                    valid_columns.append(col)
            
            df_display = df_pivot[valid_columns]

            # 데이터 존재 행 필터링
            df_check = df_display.replace(0, pd.NA)
            df_display = df_display[df_check.notna().any(axis=1)]

            # -----------------------------------------------------------
            # [조건부 계산] 단위당 단가 계산 (4개 품목 한정, Grouping)
            # -----------------------------------------------------------
            if price_mode == "단위당 단가":
                def apply_unit_price_calculation(row):
                    item_name = str(row.name[0])
                    spec = str(row.name[1])
                    divisor = 1.0
                    
                    if any(x in item_name for x in ['안전망', '멀티망']):
                        nums = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', spec)]
                        if nums:
                            temp_div = 1.0
                            for n in nums: temp_div *= n
                            divisor = temp_div
                    elif '와이어로프' in item_name:
                        match = re.search(r'\*\s*(\d+(?:\.\d+)?)', spec)
                        if match: divisor = float(match.group(1))
                    elif '와이어클립' in item_name:
                        match = re.search(r'(\d+(?:\.\d+)?)', spec)
                        if match: divisor = float(match.group(1))
                    
                    if divisor == 0: divisor = 1.0
                    
                    return row.apply(lambda x: x / divisor if pd.notnull(x) and isinstance(x, (int, float)) else x)

                df_calc = df_display.apply(apply_unit_price_calculation, axis=1)
                
                df_reset = df_calc.reset_index()
                df_reset = df_reset.drop(columns=['규격'])
                df_grouped = df_reset.groupby(['품목', note_col, '단위'], sort=False).first()
                df_display = df_grouped

            # -----------------------------------------------------------
            # [신규] 열 정렬 기준 품목 선택 및 동적 재배치
            # -----------------------------------------------------------
            st.divider()
            
            # 정렬 옵션 생성
            sort_target_options = ["선택 안함"]
            rows_map = {}
            
            for idx in df_display.index:
                # idx는 MultiIndex 튜플
                if isinstance(idx, tuple):
                    # 기본 단가: ['품목', '규격', note_col, '단위']
                    # 단위당: ['품목', note_col, '단위']
                    item = str(idx[0])
                    if price_mode == "기본 단가":
                        spec = str(idx[1])
                        note = str(idx[2])
                        label = f"{item} ({note})" # 요청대로 품목+비고1만 표시 (규격은 내부적으로 식별에 사용)
                    else:
                        note = str(idx[1])
                        label = f"{item} ({note})"
                else:
                    label = str(idx)
                
                # 중복 방지를 위해 고유 ID 추가 등 처리가 필요할 수 있으나, 
                # 여기서는 마지막 항목이 덮어쓰는 구조임. 
                # UI상 구분을 위해 라벨에 규격을 추가하는 것이 좋으나 사용자 요청 준수.
                # 다만, 식별을 위해 옵션 값에 규격 정보도 살짝 포함시킴.
                if price_mode == "기본 단가":
                    label = f"{item} ({note}) - {idx[1]}"
                
                sort_target_options.append(label)
                rows_map[label] = idx

            col_sort, _ = st.columns([1, 2])
            with col_sort:
                selected_sort_option = st.selectbox(
                    "📊 열 정렬 기준 품목 선택 (가격 낮은 순)", 
                    sort_target_options
                )

            # 정렬 로직 실행
            if selected_sort_option != "선택 안함" and selected_sort_option in rows_map:
                target_idx = rows_map[selected_sort_option]
                try:
                    target_row = df_display.loc[target_idx]
                    # Series인지 DataFrame(중복)인지 확인
                    if isinstance(target_row, pd.DataFrame):
                        target_row = target_row.iloc[0]
                        
                    # 정렬: 값 오름차순, NaN/0/빈값은 맨 뒤로
                    def get_sort_val(val):
                        if pd.isna(val) or val == "" or val == 0:
                            return float('inf')
                        return val

                    sorted_cols = sorted(
                        df_display.columns,
                        key=lambda col: get_sort_val(target_row[col])
                    )
                    
                    df_display = df_display[sorted_cols]
                    st.toast(f"✅ '{selected_sort_option}' 기준 최저가 순 정렬 완료")
                except Exception as e:
                    pass

            # 포맷팅
            def format_price_int(val):
                if pd.isna(val) or val == "" or val == 0: return ""
                try: return f"{int(val):,}"
                except: return str(val)

            df_display_formatted = df_display.applymap(format_price_int)

            st.subheader("📋 업체별 현재 매출단가 비교")
            st.caption(f"💡 기준: {price_mode} (소수점 제거됨)")
            
            cols_cfg = {
                note_col: st.column_config.TextColumn(note_col, width=None, help="비고 사항")
            }
            
            st.dataframe(
                df_display_formatted,
                use_container_width=True,
                column_config=cols_cfg
            )
        else:
            st.info("조건에 맞는 데이터가 없습니다.")
        
        st.divider()

        # -----------------------------------------------------------
        # 6. 하단: 업체별 히스토리
        # -----------------------------------------------------------
        st.subheader("📜 업체별 단가 변동 히스토리")
        
        hc1, hc2, hc3, hc4 = st.columns(4)
        
        with hc1:
            sel_vendor = st.selectbox("업체 (단일 선택)", all_vendors)
            
        mask_vendor = df_sorted['매출업체'].astype(str).str.replace(' ', '') == str(sel_vendor).replace(' ', '')
        vendor_df = df_sorted[mask_vendor]

        v_items = vendor_df['품목'].unique().tolist()
        v_item_opts = ['전체 선택'] + v_items
        
        with hc2:
            sel_hist_items = st.multiselect("품목 (다중)", v_item_opts, default=[])
            
        if not sel_hist_items or '전체 선택' in sel_hist_items:
            hist_df_step1 = vendor_df
        else:
            hist_df_step1 = vendor_df[vendor_df['품목'].isin(sel_hist_items)]

        v_specs = hist_df_step1['규격'].unique().tolist()
        v_spec_opts = ['전체 선택'] + v_specs
        
        with hc3:
            sel_hist_specs = st.multiselect("규격 (다중)", v_spec_opts, default=[])
            
        if not sel_hist_specs or '전체 선택' in sel_hist_specs:
            hist_df_step2 = hist_df_step1
        else:
            hist_df_step2 = hist_df_step1[hist_df_step1['규격'].isin(sel_hist_specs)]

        v_notes = hist_df_step2[note_col].unique().tolist()
        v_note_opts = ['전체 선택'] + v_notes
        
        with hc4:
            sel_hist_notes = st.multiselect("비고 (다중)", v_note_opts, default=[])

        if not sel_hist_notes or '전체 선택' in sel_hist_notes:
            hist_df_final = hist_df_step2
        else:
            hist_df_final = hist_df_step2[hist_df_step2[note_col].isin(sel_hist_notes)]

        is_item_selected = bool(sel_hist_items)
        is_spec_selected = bool(sel_hist_specs)
        is_note_selected = bool(sel_hist_notes)
        
        if not (is_item_selected or is_spec_selected or is_note_selected):
            st.info("👆 조회할 품목, 규격, 또는 비고를 선택해주세요.")
        else:
            history_cols = [c for c in df_sales.columns if '과거매출단가' in str(c)]
            
            if not history_cols:
                st.warning("과거 단가 데이터(열)가 없습니다.")
            elif hist_df_final.empty:
                st.warning("조건에 맞는 데이터가 없습니다.")
            else:
                id_cols = ['품목', '규격', note_col, '단위']
                target_df = hist_df_final[id_cols + history_cols].copy()
                
                melted = target_df.melt(id_vars=id_cols, value_vars=history_cols, var_name='raw_date', value_name='price')
                melted['date_str'] = melted['raw_date'].astype(str).str.replace('과거매출단가', '').str.replace('_', ' ').str.strip()
                melted = melted.dropna(subset=['price'])
                melted = melted[melted['price'] != 0]
                melted = melted[melted['price'] != ""]
                
                if melted.empty:
                    st.info("해당 조건의 과거 단가 기록이 없습니다.")
                else:
                    hist_pivot = melted.pivot_table(
                        index=id_cols,
                        columns='date_str',
                        values='price',
                        aggfunc='first'
                    )
                    
                    date_cols = hist_pivot.columns.tolist()
                    try:
                        sorted_dates = sorted(date_cols, key=lambda x: pd.to_datetime(x, format='%y/%m/%d', errors='ignore'))
                    except:
                        sorted_dates = sorted(date_cols)
                        
                    hist_pivot = hist_pivot[sorted_dates]
                    
                    row_order = hist_df_final[id_cols].drop_duplicates()
                    target_idx = pd.MultiIndex.from_frame(row_order)
                    final_idx = target_idx.intersection(hist_pivot.index)
                    final_idx = target_idx[target_idx.isin(final_idx)]
                    
                    hist_pivot = hist_pivot.reindex(final_idx)
                    hist_pivot.index.names = ['품목', '규격', note_col, '단위']
                    
                    hist_pivot_display = hist_pivot.applymap(format_price_int)
                    
                    st.dataframe(hist_pivot_display, use_container_width=True)

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
