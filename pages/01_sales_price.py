import streamlit as st
import pandas as pd
import re
import os

st.set_page_config(page_title="매출단가 조회", page_icon="📈", layout="wide")

# -----------------------------------------------------------------------------
# [데이터 강제 로드 로직]
# -----------------------------------------------------------------------------
file_path = 'price_list.xlsx'
if 'df_sales' not in st.session_state or 'df_purch' not in st.session_state:
    if os.path.exists(file_path):
        st.session_state['df_sales'] = pd.read_excel(file_path, sheet_name='Sales_매출단가')
        st.session_state['df_purch'] = pd.read_excel(file_path, sheet_name='Purchase_매입단가')
    else:
        st.error(f"🚨 '{file_path}' 파일이 존재하지 않습니다.")
        st.stop()

# -----------------------------------------------------------------------------
# [Helper] 완벽한 자연어 정렬을 위한 무적 함수
# -----------------------------------------------------------------------------
def make_sortable_string(s):
    """문자열 내의 숫자를 10자리 소수점 포맷으로 변환하여 완벽한 문자열 정렬 지원"""
    def pad_num(match):
        return f"{float(match.group()):010.3f}"
    return re.sub(r'\d+(\.\d+)?', pad_num, str(s))

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
# 메인 로직
# -----------------------------------------------------------------------------
st.title("📈 매출단가 조회")

try:
    df_sales = st.session_state['df_sales'].copy()
    
    note_col = '비고 1' if '비고 1' in df_sales.columns else '비고'
    if note_col not in df_sales.columns: df_sales[note_col] = ""
    
    df_sales[note_col] = df_sales[note_col].fillna("").astype(str)
    if '규격' in df_sales.columns:
        df_sales['규격'] = df_sales['규격'].fillna("").astype(str)
    if '단위' not in df_sales.columns: df_sales['단위'] = ""
    
    current_price_col = next((c for c in df_sales.columns if '현재매출단가' in str(c)), None)
    if not current_price_col: 
        st.error("필수 컬럼 없음"); st.stop()

    price_mode = st.radio("단가 표시 방식", ["기본 단가", "단위당 단가"], index=1, horizontal=True)

    priority_items = [
        '안전망1cm', '안전망2cm', '안전망', 
        '멀티망', '럿셀망', 
        'PE로프', 'pp로프', 'PP로프', 
        '와이어로프', '와이어', 
        '와이어클립', '케이블타이'
    ]
    
    def get_item_priority(name):
        name_str = str(name).strip()
        for i, key in enumerate(priority_items):
            if key in name_str: return i
        return 999

    def get_note_rank(note):
        s = str(note).strip()
        if s == 'KS로프가공': return 2
        if s == '로프가공': return 3
        if 'KS' in s: return 0
        return 1

    df_sales['rank_item'] = df_sales['품목'].apply(get_item_priority)
    df_sales['rank_note'] = df_sales[note_col].apply(get_note_rank)
    df_sales['rank_num'] = df_sales[note_col].apply(extract_number_safe)
    
    # 완벽한 규격 정렬 키 생성
    df_sales['규격_sort'] = df_sales['규격'].apply(make_sortable_string)
    
    df_sorted = df_sales.sort_values(
        by=['rank_item', 'rank_note', 'rank_num', '규격_sort'],
        ascending=True
    )

    st.subheader("🔍 데이터 필터")
    all_vendors = sorted(df_sales['매출업체'].dropna().unique().astype(str))
    def_v = ['가온건설', '신영산업안전', '네오이앤씨', '동원', '우주안전', '세종스틸', '제이엠산업개발', '전진산업안전', '씨에스산업건설', '타포', '경원안전', '토우코리아']
    sel_v_raw = st.multiselect("🏢 조회할 업체 선택", ['전체 선택'] + all_vendors, default=[v for v in def_v if v in all_vendors])
    sel_v = all_vendors if '전체 선택' in sel_v_raw else sel_v_raw

    c1, c2, c3 = st.columns(3)
    all_items = df_sorted['품목'].unique().tolist()
    
    with c1: sel_i_raw = st.multiselect("📦 품목", ['전체 선택'] + all_items, default=[])
    
    if not sel_i_raw or '전체 선택' in sel_i_raw:
        df_step1 = df_sorted
    else:
        df_step1 = df_sorted[df_sorted['품목'].isin(sel_i_raw)].copy()
        sorter_index = dict(zip(sel_i_raw, range(len(sel_i_raw))))
        df_step1['select_rank'] = df_step1['품목'].map(sorter_index)
        df_step1 = df_step1.sort_values(['select_rank', 'rank_note', 'rank_num', '규격_sort'])

    # 셀렉트박스 리스트 정렬
    all_specs = sorted(df_step1['규격'].unique().tolist(), key=make_sortable_string)
    with c2: sel_s_raw = st.multiselect("📏 규격", ['전체 선택'] + all_specs, default=[])
    df_step2 = df_step1 if not sel_s_raw or '전체 선택' in sel_s_raw else df_step1[df_step1['규격'].isin(sel_s_raw)]
    
    all_notes = df_step2[note_col].unique().tolist()
    with c3: sel_n_raw = st.multiselect("📝 비고", ['전체 선택'] + all_notes, default=[])
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

        # 출력 직전 피벗 테이블 100% 강제 재정렬
        df_display = df_display.reset_index()
        df_display['rank_item'] = df_display['품목'].apply(get_item_priority)
        df_display['rank_note'] = df_display[note_col].apply(get_note_rank)
        df_display['rank_num'] = df_display[note_col].apply(extract_number_safe)
        df_display['규격_sort'] = df_display['규격'].apply(make_sortable_string) if '규격' in df_display.columns else ""
        
        sort_keys = []
        if sel_i_raw and '전체 선택' not in sel_i_raw:
            sorter_dict = dict(zip(sel_i_raw, range(len(sel_i_raw))))
            df_display['select_rank'] = df_display['품목'].map(sorter_dict)
            sort_keys = ['select_rank', 'rank_note', 'rank_num']
        else:
            sort_keys = ['rank_item', 'rank_note', 'rank_num']

        if '규격' in df_display.columns:
            sort_keys.append('규격_sort')

        df_display = df_display.sort_values(by=sort_keys, ascending=True)

        drop_cols = ['rank_item', 'rank_note', 'rank_num', '규격_sort']
        if 'select_rank' in df_display.columns: drop_cols.append('select_rank')
        df_display = df_display.drop(columns=[c for c in drop_cols if c in df_display.columns])

        idx_cols = [c for c in ['품목', '규격', note_col, '단위'] if c in df_display.columns]
        df_display = df_display.set_index(idx_cols)

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
        cols_config = {
            note_col: st.column_config.TextColumn(note_col, width=None)
        }
        st.dataframe(
            df_display.applymap(format_price_safe), 
            use_container_width=True,
            column_config=cols_config
        )
except Exception as e: 
    st.error(f"오류: {e}")
