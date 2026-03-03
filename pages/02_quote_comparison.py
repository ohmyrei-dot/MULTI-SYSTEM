import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="매입견적 비교", page_icon="📝", layout="wide")

# -----------------------------------------------------------------------------
# [Helper] 유틸리티 함수
# -----------------------------------------------------------------------------
def natural_sort_key_simple(s):
    text = str(s).strip()
    match = re.search(r'(\d+(\.\d+)?)', text)
    num_val = float(match.group(1)) if match else float('inf')
    if 'KS' in text: k_rank = 0
    elif '가공' in text: k_rank = 2
    else: k_rank = 1
    return (num_val, k_rank, text)

# -----------------------------------------------------------------------------
# 메인 로직
# -----------------------------------------------------------------------------
st.title("📝 매입견적 비교")
st.markdown("원하는 품목을 **직접 선택**하여 견적서에 추가하세요.")

if 'df_purch' not in st.session_state:
    st.warning("데이터가 로드되지 않았습니다. 메인 화면(app.py)으로 이동해 데이터를 불러와주세요.")
    st.stop()

if 'quote_list' not in st.session_state: 
    st.session_state.quote_list = []

try:
    df_raw = st.session_state['df_purch'].copy()
    cols = df_raw.columns.tolist()
    vendor_col = next((c for c in cols if '업체' in c or '거래처' in c), None)
    item_col = next((c for c in cols if '품목' in c or '품명' in c), None)
    price_col = next((c for c in cols if '단가' in c or '매입가' in c or '가격' in c), None)
    spec_cols = [c for c in cols if '규격' in c]

    if not (vendor_col and item_col and price_col): 
        st.error("필수 컬럼 없음"); st.stop()
        
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
