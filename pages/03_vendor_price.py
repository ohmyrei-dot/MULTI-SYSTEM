import streamlit as st
import pandas as pd
import re
import os
import numpy as np

st.set_page_config(page_title="업체별 매입단가 조회", page_icon="📉", layout="wide")

# -----------------------------------------------------------------------------
# [데이터 강제 로드 로직] 세션에 데이터가 없으면 불러오기
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
# [Helper] 유틸리티 함수
# -----------------------------------------------------------------------------
def robust_natural_sort_key(s):
    text = str(s).strip()
    if 'KS' in text: keyword_rank = 0
    elif '가공' in text: keyword_rank = 2
    else: keyword_rank = 1

    def convert(t):
        return float(t) if t.replace('.', '', 1).isdigit() else t.lower()
    
    alphanum_key = [convert(c) for c in re.split('([0-9.]+)', text) if c]
    return (keyword_rank, tuple(alphanum_key))

def format_price_safe(val):
    try:
        if pd.isna(val) or val == "" or val == 0: return ""
        return f"{int(float(val)):,}"
    except: return str(val)

# -----------------------------------------------------------------------------
# 메인 로직
# -----------------------------------------------------------------------------
st.markdown("""
<style>
div[data-testid="stColumn"] { align-items: center; }
.stButton button { border: none; background: transparent; padding: 0; color: #ff4b4b; font-size: 1.2rem; }
.stButton button:hover { color: #ff0000; background: transparent; }
</style>
""", unsafe_allow_html=True)

st.title("📉 업체별 매입단가 조회")
st.markdown("매입처별 단가를 한눈에 비교하고 목록을 작성하세요.")
st.caption("💡 멀티 셀렉트 박스에서 선택한 순서대로 표에 나열됩니다.")

if 'vendor_cart_new' not in st.session_state: st.session_state.vendor_cart_new = []
if 'vendor_deleted_set_new' not in st.session_state: st.session_state.vendor_deleted_set_new = set()
if 'vp_saved_vendors' not in st.session_state: st.session_state.vp_saved_vendors = []

try:
    df_purch = st.session_state['df_purch'].copy()
    vendor_col = next((c for c in df_purch.columns if '매입업체' in str(c)), next((c for c in df_purch.columns if '업체' in str(c)), None))
    price_col = next((c for c in df_purch.columns if '매입단가' in str(c)), next((c for c in df_purch.columns if '단가' in str(c) or '가격' in str(c)), None))
    if not vendor_col or not price_col: 
        st.error("필수 컬럼 없음"); st.stop()

    col_map = {}
    if '규격1' in df_purch.columns: col_map['규격1'] = 'calc_spec'
    elif '규격' in df_purch.columns: col_map['규격'] = 'calc_spec'
    else: df_purch['calc_spec'] = ""
    if '규격2' in df_purch.columns: col_map['규격2'] = 'display_spec'
    else: df_purch['display_spec'] = df_purch.get('calc_spec', "")
    
    df_purch = df_purch.rename(columns=col_map)
    df_purch['calc_spec'] = df_purch['calc_spec'].fillna("").astype(str)
    df_purch['display_spec'] = df_purch['display_spec'].fillna("").astype(str)
    df_purch['품목'] = df_purch['품목'].fillna("").astype(str)
    
    st.subheader("1️⃣ 업체 선택")
    all_vendors = sorted(df_purch[vendor_col].dropna().unique().astype(str))
    
    defaults = ['가온건설', '신영산업안전', '토우코리아']
    default_vendors = [v for v in defaults if v in all_vendors]
    
    if not st.session_state.vp_saved_vendors: current_default = default_vendors
    else: current_default = [v for v in st.session_state.vp_saved_vendors if v in ['전체 선택'] + all_vendors]
    
    sel_vendors = st.multiselect("비교할 매입처를 선택하세요 (가로 열)", ['전체 선택'] + all_vendors, default=current_default)
    st.session_state.vp_saved_vendors = sel_vendors
    
    if not sel_vendors: target_vendors = []
    elif '전체 선택' in sel_vendors: target_vendors = all_vendors
    else: target_vendors = sel_vendors

    st.subheader("2️⃣ 품목 추가")
    c_add1, c_add2, c_add3 = st.columns([1.5, 2, 0.8])
    
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
    df_sorted = df_purch.sort_values(
        by=['Sort_Base', '품목', 'calc_spec', 'display_spec'],
        key=lambda x: x.map(robust_natural_sort_key) if x.name in ['calc_spec', 'display_spec'] else x,
        ascending=True
    )

    all_items = df_sorted['품목'].unique().tolist()
    with c_add1:
        add_item = st.selectbox("품목", all_items, index=None, placeholder="품목을 선택하세요...", key="vp_new_item")
        
    spec_opts = []; spec_map = {}
    if add_item:
        item_df = df_sorted[df_sorted['품목'] == add_item]
        spec_combinations = item_df[['calc_spec', 'display_spec']].drop_duplicates().sort_values(by=['calc_spec', 'display_spec'], key=lambda x: x.map(robust_natural_sort_key))
        for _, row in spec_combinations.iterrows():
            s1, s2 = row['calc_spec'], row['display_spec']
            label = f"{s1} | {s2}" if s2 and s2!=s1 else s1
            spec_opts.append(label); spec_map[label] = (s1, s2)
            
    with c_add2:
        add_spec_labels = st.multiselect(
            "규격 (규격1 | 규격2)", spec_opts, 
            placeholder="규격을 선택하세요..." if add_item else "품목을 먼저 선택하세요", 
            key="vp_new_spec", disabled=not add_item
        )
        
    with c_add3:
        if st.button("➕ 목록에 추가", use_container_width=True, key="vp_new_add", disabled=not (add_item and add_spec_labels)):
            if add_item and add_spec_labels:
                added_cnt = 0
                dup_cnt = 0
                for label in add_spec_labels:
                    s1, s2 = spec_map[label]
                    key = (add_item, s1, s2)
                    
                    if key in st.session_state.vendor_deleted_set_new:
                        st.session_state.vendor_deleted_set_new.remove(key)
                        added_cnt += 1
                    elif any((x['item'], x['s1'], x['s2']) == key for x in st.session_state.vendor_cart_new):
                        dup_cnt += 1
                    else:
                        st.session_state.vendor_cart_new.append({'item': add_item, 's1': s1, 's2': s2})
                        added_cnt += 1
                
                if added_cnt > 0: st.toast(f"✅ {added_cnt}건 추가됨")
                if dup_cnt > 0: st.toast(f"⚠️ {dup_cnt}건 중복 제외")

    st.divider()
    active_cart = [x for x in st.session_state.vendor_cart_new if (x['item'], x['s1'], x['s2']) not in st.session_state.vendor_deleted_set_new]
    st.subheader(f"📋 비교 리스트 ({len(active_cart)}건)")
    
    if active_cart and target_vendors:
        cart_df = pd.DataFrame(active_cart)
        cart_df['__order'] = range(len(cart_df)) 
        cart_df.rename(columns={'item': '품목', 's1': 'calc_spec', 's2': 'display_spec'}, inplace=True)
        
        df_pivot_base = df_purch.pivot_table(index=['품목', 'calc_spec', 'display_spec'], columns=vendor_col, values=price_col, aggfunc='first').reset_index()
        merged_view = pd.merge(cart_df, df_pivot_base, on=['품목', 'calc_spec', 'display_spec'], how='left')
        
        pivot_cols = df_pivot_base.columns
        clean_to_real = {}
        for c in pivot_cols:
            if c not in ['품목', 'calc_spec', 'display_spec']: clean_to_real[str(c).replace(' ', '')] = c
        
        ordered_matched_cols = []
        for t in target_vendors:
            clean_t = str(t).replace(' ', '')
            if clean_t in clean_to_real: ordered_matched_cols.append(clean_to_real[clean_t])

        def apply_unit_calc(row):
            item = str(row['품목']); spec1 = str(row['calc_spec']); divisor = 1.0
            if '럿셀망' in item: divisor = 1.0
            elif any(x in item for x in ['안전망', '멀티망']):
                nums = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', spec1)]
                if len(nums) >= 2: divisor = nums[0] * nums[1]
                elif len(nums) == 1: divisor = nums[0]
            elif any(x in item for x in ['와이어로프', '와이어클립']):
                nums = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', spec1)]
                if nums: divisor = nums[-1]
            if divisor == 0: divisor = 1.0
            
            for v in ordered_matched_cols:
                if v in row:
                    val = row[v]
                    try: row[v] = float(val) / divisor
                    except: pass
            return row

        df_calc = merged_view.apply(apply_unit_calc, axis=1)
        df_out = df_calc.sort_values('__order').reset_index(drop=True)
        df_out['row_id'] = list(zip(df_out['품목'], df_out['calc_spec'], df_out['display_spec']))
        
        # 품목, 규격 합쳐서 공간 절약
        def combine_info(row):
            res = str(row['품목'])
            extras = []
            if str(row['calc_spec']).strip(): extras.append(str(row['calc_spec']))
            if str(row['display_spec']).strip() and str(row['display_spec']) != str(row['calc_spec']): extras.append(str(row['display_spec']))
            if extras:
                res += f" ({' / '.join(extras)})"
            return res
            
        df_out['품목정보'] = df_out.apply(combine_info, axis=1)
        
        # 출력용 데이터프레임 구성
        df_show = df_out[['품목정보'] + ordered_matched_cols].copy()
        for c in ordered_matched_cols:
            df_show[c] = df_show[c].apply(format_price_safe)
            
        # 삭제 체크박스 컬럼 추가
        df_show.insert(0, '삭제', False)
        
        # 열 너비 설정
        cols_config = {
            "삭제": st.column_config.CheckboxColumn("삭제", width="small"),
            "품목정보": st.column_config.TextColumn("품목정보", width=200)
        }
        for c in ordered_matched_cols:
            cols_config[c] = st.column_config.TextColumn(c, width=90)
            
        # 데이터 에디터로 출력 (가로 스크롤 활성화)
        edited_df = st.data_editor(
            df_show,
            hide_index=True,
            use_container_width=True,
            column_config=cols_config,
            disabled=['품목정보'] + ordered_matched_cols # 삭제 체크박스 빼고 수정 금지
        )
        
        # 삭제 동작 감지 시 즉시 세션 반영 후 새로고침
        if edited_df['삭제'].any():
            deleted_indices = edited_df[edited_df['삭제']].index
            for idx in deleted_indices:
                st.session_state.vendor_deleted_set_new.add(df_out.loc[idx, 'row_id'])
            st.rerun()

        st.markdown("---")
        _, del_col = st.columns([5, 1])
        if del_col.button("🗑️ 출력된 항목 전체삭제", type="secondary", key="vp_clear_all_btn"):
            st.session_state.vendor_cart_new = []
            st.session_state.vendor_deleted_set_new = set()
            st.rerun()
    else:
        if not target_vendors: st.info("👆 먼저 상단에서 비교할 '매입처'를 선택해주세요.")
        else: st.info("👇 품목을 선택하고 [추가] 버튼을 눌러 리스트를 작성하세요.")

except Exception as e: st.error(f"오류: {e}")
