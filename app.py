import streamlit as st
import pandas as pd
import os
import re
import numpy as np

# -----------------------------------------------------------------------------
# 1. 페이지 공통 설정 (전역 설정)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="스마트 견적서 및 단가 관리",
    page_icon="📊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# [Helper] 공통 정렬 및 유틸리티 함수
# -----------------------------------------------------------------------------
def robust_natural_sort_key(s):
    """
    [강력한 Natural Sort]
    문자열과 숫자가 섞여 있어도 에러 없이(TypeError 방지) 비교 가능하도록 변환
    """
    text = str(s).strip()
    
    # 1. 키워드 우선순위: KS(0) > 일반(1) > 가공(2)
    if 'KS' in text: keyword_rank = 0
    elif '가공' in text: keyword_rank = 2
    else: keyword_rank = 1

    # 2. 숫자/문자 분리
    def convert(text):
        return float(text) if text.replace('.', '', 1).isdigit() else text.lower()
    
    alphanum_key = [convert(c) for c in re.split('([0-9.]+)', text) if c]
    
    return (keyword_rank, tuple(alphanum_key))

def natural_sort_key_simple(s):
    """매입견적용 단순 정렬 (기존 유지)"""
    text = str(s).strip()
    match = re.search(r'(\d+(\.\d+)?)', text)
    num_val = float(match.group(1)) if match else float('inf')
    
    if 'KS' in text: k_rank = 0
    elif '가공' in text: k_rank = 2
    else: k_rank = 1
    return (num_val, k_rank, text)

def extract_number_safe(text):
    if pd.isna(text): return float('inf')
    match = re.search(r'(\d+(\.\d+)?)', str(text))
    if match: return float(match.group(1))
    return float('inf')

def format_price_safe(val):
    try:
        if pd.isna(val) or val == "" or val == 0: return ""
        return f"{int(float(val)):,}"
    except: return str(val)

# -----------------------------------------------------------------------------
# 2. 매입 견적 비교 시스템 (기존 기능 유지)
# -----------------------------------------------------------------------------
def run_purchase_estimate_system():
    st.markdown("""<style>h1 { word-break: keep-all; }</style>""", unsafe_allow_html=True)
    st.title("📝 스마트\u00A0견적서 작성\u00A0시스템")
    st.markdown("원하는 품목을 **직접 선택**하여 견적서에 추가하세요.")

    if 'quote_list' not in st.session_state: st.session_state.quote_list = []
    file_path = '단가표.xlsx'
    if not os.path.exists(file_path): st.error(f"🚨 '{file_path}' 없음"); return

    try:
        df_raw = pd.read_excel(file_path, sheet_name='Purchase_매입단가')
        cols = df_raw.columns.tolist()
        vendor_col = next((c for c in cols if '업체' in c or '거래처' in c), None)
        item_col = next((c for c in cols if '품목' in c or '품명' in c), None)
        price_col = next((c for c in cols if '단가' in c or '매입가' in c or '가격' in c), None)
        spec_cols = [c for c in cols if '규격' in c]

        if not (vendor_col and item_col and price_col): st.error("필수 컬럼 없음"); return
        def combine_specs(row):
            specs = [str(row[c]) for c in spec_cols if pd.notna(row[c]) and str(row[c]).strip() != '']
            return ' '.join(specs) if specs else '-'
        df_raw['통합규격'] = df_raw.apply(combine_specs, axis=1)
        df_pivot = df_raw.pivot_table(index=[item_col, '통합규격'], columns=vendor_col, values=price_col, aggfunc='first').reset_index()
        vendors = [c for c in df_pivot.columns if c not in [item_col, '통합규격']]

        st.divider()
        c1, c2 = st.columns(2)
        idx_a = list(vendors).index('솔트룩스') if '솔트룩스' in vendors else 0
        with c1: vendor_a = st.selectbox("기준 업체 (A)", vendors, index=idx_a)
        idx_b = list(vendors).index('태양산자') if '태양산자' in vendors else (1 if len(vendors)>1 else 0)
        with c2: vendor_b = st.selectbox("비교 업체 (B)", vendors, index=idx_b)

        st.divider()
        st.subheader("➕ 품목 추가하기")
        with st.container():
            col_input1, col_input2, col_input3, col_btn = st.columns([2, 2, 1, 1])
            raw_items = df_pivot[item_col].unique().tolist()
            priority_keywords = ['안전망', 'PP로프', '와이어로프', '와이어클립', '멀티망', '럿셀망', '케이블타이', 'PE로프']
            sorted_items = []
            used_items = set()
            for kw in priority_keywords:
                matches = sorted([x for x in raw_items if kw in str(x) and x not in used_items], key=natural_sort_key_simple)
                sorted_items.extend(matches); used_items.update(matches)
            others = sorted([x for x in raw_items if x not in used_items], key=natural_sort_key_simple)
            final_item_list = sorted_items + others
            
            selected_item = col_input1.selectbox("품목 선택", final_item_list, key="sel_item")
            available_specs = df_pivot[df_pivot[item_col] == selected_item]['통합규격'].unique().tolist()
            available_specs = sorted(available_specs, key=natural_sort_key_simple)
            selected_spec = col_input2.selectbox("규격 선택", available_specs, key="sel_spec")
            input_qty = col_input3.number_input("수량", min_value=1, value=1, step=1, key="in_qty")

            if col_btn.button("품목 추가", type="primary", use_container_width=True):
                new_entry = {'id': f"{selected_item}_{selected_spec}", item_col: selected_item, '통합규격': selected_spec, '수량': input_qty}
                existing_idx = next((i for i, x in enumerate(st.session_state.quote_list) if x['id'] == new_entry['id']), -1)
                if existing_idx != -1: st.session_state.quote_list[existing_idx]['수량'] += input_qty
                else: st.session_state.quote_list.append(new_entry)
                st.toast(f"✅ '{selected_item}' 추가 완료!")

        st.divider()
        st.subheader(f"📋 견적 리스트 ({len(st.session_state.quote_list)}건)")
        if st.session_state.quote_list:
            df_quote = pd.DataFrame(st.session_state.quote_list)
            df_merged = pd.merge(df_quote, df_pivot[[item_col, '통합규격', vendor_a, vendor_b]], on=[item_col, '통합규격'], how='left')
            df_merged[f'{vendor_a} 단가'] = df_merged[vendor_a].fillna(0)
            df_merged[f'{vendor_b} 단가'] = df_merged[vendor_b].fillna(0)
            df_merged['단가 차액'] = df_merged[f'{vendor_b} 단가'] - df_merged[f'{vendor_a} 단가']
            df_merged[f'{vendor_a} 합계'] = df_merged[f'{vendor_a} 단가'] * df_merged['수량']
            df_merged[f'{vendor_b} 합계'] = df_merged[f'{vendor_b} 단가'] * df_merged['수량']
            df_merged['총 차액'] = df_merged[f'{vendor_a} 합계'] - df_merged[f'{vendor_b} 합계']
            
            total_a = df_merged[f'{vendor_a} 합계'].sum()
            total_b = df_merged[f'{vendor_b} 합계'].sum()
            total_diff = total_a - total_b

            view_mode = st.radio("화면 모드 선택", ["🖥️ PC (표)", "📱 모바일 (카드)"], horizontal=True, label_visibility="collapsed")
            if view_mode == "🖥️ PC (표)":
                ratio = [0.5, 1.5, 1.2, 0.7, 1, 1, 1, 1.1, 1.1, 1.1]
                h = st.columns(ratio)
                h[0].markdown("**삭제**"); h[1].markdown("**품목**"); h[2].markdown("**규격**"); h[3].markdown("**수량**")
                h[4].markdown(f"**{vendor_a}<br>단가**", unsafe_allow_html=True)
                h[5].markdown(f"**{vendor_b}<br>단가**", unsafe_allow_html=True)
                h[6].markdown("**단가<br>차액**", unsafe_allow_html=True)
                h[7].markdown(f"**{vendor_a}<br>합계**", unsafe_allow_html=True)
                h[8].markdown(f"**{vendor_b}<br>합계**", unsafe_allow_html=True)
                h[9].markdown("**총 차액<br>(이득)**", unsafe_allow_html=True)
                st.markdown("---")
                for idx, row in df_merged.iterrows():
                    c = st.columns(ratio)
                    if c[0].button("🗑️", key=f"del_{row['id']}"):
                        st.session_state.quote_list = [x for x in st.session_state.quote_list if x['id'] != row['id']]
                        st.rerun()
                    c[1].text(row[item_col]); c[2].text(row['통합규격']); c[3].text(f"{row['수량']:,}")
                    c[4].text(f"{int(row[f'{vendor_a} 단가']):,}원"); c[5].text(f"{int(row[f'{vendor_b} 단가']):,}원")
                    ud = row['단가 차액']
                    c[6].markdown(f":red[+{int(ud):,}원]" if ud > 0 else f":blue[{int(ud):,}원]")
                    c[7].text(f"{int(row[f'{vendor_a} 합계']):,}원"); c[8].text(f"{int(row[f'{vendor_b} 합계']):,}원")
                    td = row['총 차액']
                    c[9].markdown(f":blue[**+{int(td):,}원**]" if td > 0 else f":red[{int(td):,}원]")
            else:
                for idx, row in df_merged.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([8,2])
                        c1.markdown(f"**{row[item_col]}**"); 
                        if c2.button("🗑️", key=f"del_m_{row['id']}"):
                            st.session_state.quote_list = [x for x in st.session_state.quote_list if x['id'] != row['id']]
                            st.rerun()
                        st.text(f"규격: {row['통합규격']} | 수량: {row['수량']:,}개")
                        st.markdown("---")
                        c3, c4 = st.columns(2)
                        with c3: st.markdown(f"**{vendor_a}**"); st.markdown(f"단가: {int(row[f'{vendor_a} 단가']):,}원 | 합계: {int(row[f'{vendor_a} 합계']):,}원")
                        with c4: st.markdown(f"**{vendor_b}**"); st.markdown(f"단가: {int(row[f'{vendor_b} 단가']):,}원 | 합계: {int(row[f'{vendor_b} 합계']):,}원")
            
            st.markdown("---")
            _, del_col = st.columns([5, 1])
            if del_col.button("🗑️ 리스트 전체 비우기", type="secondary"):
                st.session_state.quote_list = []; st.rerun()

            with st.container():
                c1, c2 = st.columns(2)
                c1.metric(f"{vendor_a} 총 합계", f"{int(total_a):,}원")
                c2.metric(f"{vendor_b} 총 합계", f"{int(total_b):,}원")
                if total_diff > 0: st.success(f"### 🎉 최종 결론: [{vendor_b}]에서 구매 시 [{int(total_diff):,}원] 더 이득입니다!")
                else: st.error(f"### 🚨 최종 결론: [{vendor_b}]가 [{int(abs(total_diff)):,}원] 더 비쌉니다. [{vendor_a}] 추천!")
        else:
            st.info("견적서가 비어있습니다.")
    except Exception as e:
        st.error(f"오류 발생: {e}")

# -----------------------------------------------------------------------------
# 3. 매출 단가 조회 시스템 (기존 로직 유지)
# -----------------------------------------------------------------------------
def run_sales_system():
    st.title("📈 매출 단가 조회")
    st.markdown("품목별 매출 단가를 한눈에 비교하고 히스토리를 확인합니다.")
    
    file_path = '단가표.xlsx'
    if not os.path.exists(file_path): st.error(f"🚨 '{file_path}' 파일 없음"); return

    try:
        df_sales = pd.read_excel(file_path, sheet_name='Sales_매출단가')
        note_col = '비고 1' if '비고 1' in df_sales.columns else '비고'
        if note_col not in df_sales.columns: df_sales[note_col] = ""
        if '단위' not in df_sales.columns: df_sales['단위'] = ""
        current_price_col = next((c for c in df_sales.columns if '현재매출단가' in str(c)), None)
        if not current_price_col: st.error("필수 컬럼 없음"); return

        price_mode = st.radio("단가 표시 방식", ["기본 단가", "단위당 단가"], index=1, horizontal=True)

        priority_items = ['안전망1cm', '안전망2cm', 'pp로프', '와이어로프', '와이어클립', '멀티망', '럿셀망', '케이블타이']
        priority_map = {item: i for i, item in enumerate(priority_items)}
        def get_note_rank(note):
            s = str(note).strip()
            if s == 'KS로프가공': return 2
            if s == '로프가공': return 3
            if 'KS' in s: return 0
            return 1

        df_sales['rank_item'] = df_sales['품목'].map(lambda x: priority_map.get(x, 999))
        df_sales['rank_note'] = df_sales[note_col].apply(get_note_rank)
        df_sales['rank_num'] = df_sales[note_col].apply(extract_number_safe)
        
        df_sorted = df_sales.sort_values(by=['rank_item', 'rank_note', 'rank_num', '규격'], ascending=True)

        st.subheader("🔍 데이터 필터")
        all_vendors = sorted(df_sales['매출업체'].dropna().unique().astype(str))
        def_v = ['가온건설', '신영산업안전', '네오이앤씨', '동원', '우주안전', '세종스틸', '제이엠산업개발', '전진산업안전', '씨에스산업건설', '타포', '경원안전', '토우코리아']
        sel_v_raw = st.multiselect("🏢 조회할 업체 선택", ['전체 선택'] + all_vendors, default=[v for v in def_v if v in all_vendors])
        sel_v = all_vendors if '전체 선택' in sel_v_raw else sel_v_raw

        c1, c2, c3 = st.columns(3)
        all_items = df_sorted['품목'].unique().tolist()
        with c1: sel_i_raw = st.multiselect("📦 품목", ['전체 선택']+all_items, default=[])
        df_step1 = df_sorted if not sel_i_raw or '전체 선택' in sel_i_raw else df_sorted[df_sorted['품목'].isin(sel_i_raw)]
        all_specs = df_step1['규격'].unique().tolist()
        with c2: sel_s_raw = st.multiselect("📏 규격", ['전체 선택']+all_specs, default=[])
        df_step2 = df_step1 if not sel_s_raw or '전체 선택' in sel_s_raw else df_step1[df_step1['규격'].isin(sel_s_raw)]
        all_notes = df_step2[note_col].unique().tolist()
        with c3: sel_n_raw = st.multiselect("📝 비고", ['전체 선택']+all_notes, default=[])
        df_final = df_step2 if not sel_n_raw or '전체 선택' in sel_n_raw else df_step2[df_step2[note_col].isin(sel_n_raw)]

        if not df_final.empty:
            df_pivot = df_final.pivot_table(index=['품목', '규격', note_col, '단위'], columns='매출업체', values=current_price_col, aggfunc='first')
            clean_targets = [str(v).replace(' ', '') for v in sel_v]
            valid_cols = [c for c in df_pivot.columns if str(c).replace(' ', '') in clean_targets]
            df_display = df_pivot[valid_cols]
            df_display = df_display[df_display.replace(0, pd.NA).notna().any(axis=1)]

            if price_mode == "단위당 단가":
                def unit_calc(row):
                    iname = str(row.name[0]); spec = str(row.name[1]); div = 1.0
                    if any(x in iname for x in ['안전망', '멀티망']):
                        nums = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', spec)]; div = np.prod(nums) if nums else 1.0
                    elif '와이어로프' in iname:
                        m = re.search(r'\*\s*(\d+)', spec); div = float(m.group(1)) if m else 1.0
                    elif '와이어클립' in iname:
                        m = re.search(r'(\d+)', spec); div = float(m.group(1)) if m else 1.0
                    return row.apply(lambda x: x / div if pd.notnull(x) and isinstance(x, (int, float)) and div != 0 else x)
                df_calc = df_display.apply(unit_calc, axis=1).reset_index().drop(columns=['규격'])
                df_display = df_calc.groupby(['품목', note_col, '단위'], sort=False).first()

            st.divider()
            sort_opts = ["선택 안함"]
            row_map = {}
            for idx in df_display.index:
                label = str(idx)
                if isinstance(idx, tuple):
                    label = f"{idx[0]} ({idx[1]})" if price_mode=="단위당 단가" else f"{idx[0]} ({idx[2]})"
                sort_opts.append(label); row_map[label] = idx

            cs1, cs2 = st.columns([2, 1])
            with cs1: s_opt = st.selectbox("📊 열 정렬 기준 품목", sort_opts)
            with cs2: s_ord = st.radio("정렬 순서", ["낮은 가격순", "높은 가격순"], horizontal=True)

            if s_opt != "선택 안함" and s_opt in row_map:
                try:
                    t_idx = row_map[s_opt]
                    t_row = df_display.loc[t_idx]
                    if isinstance(t_row, pd.DataFrame): t_row = t_row.iloc[0]
                    is_rev = "높은" in s_ord
                    def s_key(c): v = t_row[c]; return float('inf') if pd.isna(v) or v==0 or v=="" else v
                    sorted_cols = sorted(df_display.columns, key=lambda c: -s_key(c) if is_rev and s_key(c)!=float('inf') else s_key(c))
                    if is_rev:
                        cols_val = [c for c in df_display.columns if s_key(c) != float('inf')]
                        cols_nan = [c for c in df_display.columns if s_key(c) == float('inf')]
                        sorted_cols = sorted(cols_val, key=s_key, reverse=True) + cols_nan
                    else: sorted_cols = sorted(df_display.columns, key=s_key)
                    df_display = df_display[sorted_cols]
                    st.toast("정렬 완료")
                except: pass

            st.subheader("📋 업체별 현재 매출단가 비교")
            st.dataframe(df_display.applymap(format_price_safe), use_container_width=True)
    except Exception as e: st.error(f"오류: {e}")

# -----------------------------------------------------------------------------
# 4. [신규] 업체별 매입단가 시스템 (수동 추가형, 가로 비교)
# -----------------------------------------------------------------------------
def run_vendor_purchase_system():
    st.title("📉 업체별 매입단가 조회")
    st.markdown("매입처별 단가를 한눈에 비교하고 **필요 없는 행은 체크하여 삭제**하세요.")
    
    # 세션 상태: 비교할 항목 리스트
    if 'vendor_cart' not in st.session_state:
        st.session_state.vendor_cart = []
    
    # 세션 상태: 삭제된 행 추적 (row_id 튜플 저장)
    if 'vendor_comp_deleted' not in st.session_state:
        st.session_state.vendor_comp_deleted = set()

    file_path = '단가표.xlsx'
    if not os.path.exists(file_path): st.error(f"🚨 '{file_path}' 파일 없음"); return

    try:
        # 데이터 로드
        df_purch = pd.read_excel(file_path, sheet_name='Purchase_매입단가')
        
        # 컬럼 정규화
        col_map = {}
        if '규격1' in df_purch.columns: col_map['규격1'] = 'calc_spec'
        elif '규격' in df_purch.columns: col_map['규격'] = 'calc_spec'
        else: df_purch['calc_spec'] = ""
        if '규격2' in df_purch.columns: col_map['규격2'] = 'display_spec'
        else: df_purch['display_spec'] = df_purch.get('calc_spec', "")
        if '단위' in df_purch.columns: col_map['단위'] = 'unit_col'
        else: df_purch['unit_col'] = ""
        
        df_purch = df_purch.rename(columns=col_map)
        df_purch['calc_spec'] = df_purch['calc_spec'].fillna("").astype(str)
        df_purch['display_spec'] = df_purch['display_spec'].fillna("").astype(str)
        df_purch['품목'] = df_purch['품목'].fillna("").astype(str)

        # 업체 컬럼 식별
        fixed_cols = ['품목', 'calc_spec', 'display_spec', 'unit_col', '비고', '비고 1']
        all_cols = df_purch.columns.tolist()
        vendor_cols = [c for c in all_cols if c not in fixed_cols and not str(c).startswith('Unnamed')]
        
        # 정렬 로직 (Natural Sort)
        def get_base_score(name):
            n = str(name).strip()
            if '안전망' in n: return 0
            if '멀티망' in n: return 1
            if '럿셀망' in n: return 2
            if 'PP로프' in n: return 3
            if '와이어로프' in n: return 4
            if '와이어클립' in n: return 5
            return 6
            
        df_purch['Sort_Base'] = df_purch['품목'].apply(get_base_score)
        
        # 기본 데이터 정렬 (선택박스 순서용)
        df_sorted = df_purch.sort_values(
            by=['Sort_Base', '품목', 'calc_spec', 'display_spec'],
            key=lambda x: x.map(robust_natural_sort_key) if x.name in ['calc_spec', 'display_spec'] else x,
            ascending=True
        )

        # -----------------------------------------------------------
        # 1. 상단: 업체 선택 (멀티)
        # -----------------------------------------------------------
        st.subheader("1️⃣ 업체 선택")
        all_vendors = sorted(vendor_cols)
        
        # 기본 선택 (있는 업체 중)
        defaults = ['가온건설', '신영산업안전', '토우코리아']
        default_vendors = [v for v in defaults if v in all_vendors]
        
        sel_vendors = st.multiselect("비교할 매입처를 선택하세요 (가로 열)", ['전체 선택']+all_vendors, default=default_vendors)
        target_vendors = all_vendors if not sel_vendors or '전체 선택' in sel_vendors else sel_vendors

        # -----------------------------------------------------------
        # 2. 품목 추가 (수동)
        # -----------------------------------------------------------
        st.subheader("2️⃣ 품목 추가")
        
        c_add1, c_add2, c_add3 = st.columns([1.5, 2, 0.8])
        
        all_items = df_sorted['품목'].unique().tolist()
        with c_add1:
            add_item = st.selectbox("품목", all_items, key="vp_item")
            
        # 해당 품목의 규격 조합
        item_df = df_sorted[df_sorted['품목'] == add_item]
        # calc_spec, display_spec 조합
        spec_combinations = item_df[['calc_spec', 'display_spec']].drop_duplicates()
        spec_combinations = spec_combinations.sort_values(
            by=['calc_spec', 'display_spec'],
            key=lambda x: x.map(robust_natural_sort_key)
        )
        
        spec_opts = []
        spec_map = {} 
        for _, row in spec_combinations.iterrows():
            s1, s2 = row['calc_spec'], row['display_spec']
            label = f"{s1} | {s2}" if s2 and s2!=s1 else s1
            spec_opts.append(label)
            spec_map[label] = (s1, s2)
            
        with c_add2:
            add_spec_label = st.selectbox("규격 (규격1 | 규격2)", spec_opts, key="vp_spec")
            
        with c_add3:
            if st.button("➕ 목록에 추가", use_container_width=True):
                if add_spec_label:
                    s1, s2 = spec_map[add_spec_label]
                    # 중복 체크
                    exists = any(
                        x['item'] == add_item and x['s1'] == s1 and x['s2'] == s2 
                        for x in st.session_state.vendor_cart
                    )
                    if not exists:
                        st.session_state.vendor_cart.append({
                            'item': add_item, 's1': s1, 's2': s2
                        })
                        st.toast(f"✅ {add_item} ({s1}) 추가됨")
                    else:
                        st.toast("⚠️ 이미 목록에 있습니다.")

        # -----------------------------------------------------------
        # 3. 데이터 처리 및 표시
        # -----------------------------------------------------------
        st.divider()
        st.subheader(f"📋 비교 리스트 ({len(st.session_state.vendor_cart)}건)")
        
        if st.session_state.vendor_cart:
            # 1) 카트 데이터를 DF로 변환
            cart_df = pd.DataFrame(st.session_state.vendor_cart)
            cart_df.rename(columns={'item': '품목', 's1': 'calc_spec', 's2': 'display_spec'}, inplace=True)
            
            # 2) 원본 데이터에서 단가 정보 매핑 (Merge)
            # 원본 df_sorted는 이미 Wide Format (업체명 컬럼 존재)
            # 품목, calc_spec, display_spec 기준으로 Join
            
            # 원본에서 중복 행 제거 (키 기준 첫번째 값)
            df_unique = df_sorted.groupby(['품목', 'calc_spec', 'display_spec'])[vendor_cols].first().reset_index()
            
            # Merge
            merged_view = pd.merge(
                cart_df, 
                df_unique, 
                on=['품목', 'calc_spec', 'display_spec'], 
                how='left'
            )
            
            # 3) 단위당 단가 계산 (강제 지침)
            def apply_unit_calc(row):
                item = str(row['품목'])
                spec1 = str(row['calc_spec'])
                divisor = 1.0
                
                # 럿셀망 제외
                if '럿셀망' in item:
                    divisor = 1.0
                elif any(x in item for x in ['안전망', '멀티망']):
                    nums = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', spec1)]
                    if len(nums) >= 2: divisor = nums[0] * nums[1] # 면적
                    elif len(nums) == 1: divisor = nums[0]
                elif any(x in item for x in ['와이어로프', '와이어클립']):
                    # 숫자 1개 추출 (여러 개면 마지막 숫자 - 보통 길이/수량)
                    # 와이어로프 200m -> 200
                    # 와이어클립 100pcs -> 100
                    nums = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', spec1)]
                    if nums: divisor = nums[-1]
                
                if divisor == 0: divisor = 1.0
                
                # 선택된 업체 컬럼만 계산
                for v in target_vendors:
                    if v in row:
                        val = row[v]
                        try:
                            val_num = float(val)
                            row[v] = val_num / divisor
                        except: pass
                return row

            df_calc = merged_view.apply(apply_unit_calc, axis=1)
            
            # 4) 식별자 생성 및 삭제 필터링
            # 튜플 키 사용
            df_calc['row_id'] = list(zip(df_calc['품목'], df_calc['calc_spec'], df_calc['display_spec']))
            
            # 삭제된 행 제외
            df_final = df_calc[~df_calc['row_id'].isin(st.session_state.vendor_comp_deleted)].copy()
            
            # 5) 최종 출력 구성
            # 컬럼: 삭제, 품목, 규격1, 규격2, 업체들
            cols_show = ['품목', 'calc_spec', 'display_spec'] + [v for v in target_vendors if v in df_final.columns]
            df_out = df_final[cols_show].copy()
            df_out.rename(columns={'calc_spec': '규격1', 'display_spec': '규격2'}, inplace=True)
            
            df_out.insert(0, "삭제", False)
            df_out.index = df_final['row_id']
            
            # Data Editor
            edited_df = st.data_editor(
                df_out,
                use_container_width=True,
                column_config={
                    "삭제": st.column_config.CheckboxColumn("삭제", width="small", default=False),
                    "품목": st.column_config.TextColumn("품목", width="medium", disabled=True),
                    "규격1": st.column_config.TextColumn("규격1", width="medium", disabled=True),
                    "규격2": st.column_config.TextColumn("규격2", width="medium", disabled=True),
                },
                disabled=target_vendors,
                hide_index=True,
                key="vendor_manual_editor_final"
            )
            
            # 삭제 처리
            deleted_keys = edited_df[edited_df['삭제']].index.tolist()
            if deleted_keys:
                for k in deleted_keys:
                    st.session_state.vendor_comp_deleted.add(k)
                    # 리스트 동기화 (선택사항)
                    st.session_state.vendor_cart = [
                        x for x in st.session_state.vendor_cart 
                        if (x['item'], x['s1'], x['s2']) != k
                    ]
                st.rerun()

            # 복구 버튼
            if len(st.session_state.vendor_comp_deleted) > 0:
                if st.button("🗑️ 삭제된 행 모두 복구"):
                    st.session_state.vendor_comp_deleted = set()
                    st.rerun()

        else:
            if not target_vendors:
                st.info("👆 먼저 상단에서 비교할 '매입처'를 선택해주세요.")
            else:
                st.info("👇 품목을 선택하고 [추가] 버튼을 눌러 리스트를 작성하세요.")

    except Exception as e:
        st.error(f"오류 발생: {e}")

# -----------------------------------------------------------------------------
# 5. 메인 실행 컨트롤러
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    menu = st.sidebar.selectbox("기능 선택", ['매출단가 조회', '업체별 매입단가', '매입견적 비교'])
    if menu == "매입견적 비교": run_purchase_estimate_system()
    elif menu == "매출단가 조회": run_sales_system()
    elif menu == "업체별 매입단가": run_vendor_purchase_system()
