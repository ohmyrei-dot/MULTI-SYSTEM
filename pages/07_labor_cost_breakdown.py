import streamlit as st
import pandas as pd
import re
import os

st.set_page_config(page_title="Labor Cost Breakdown", page_icon="🕵️‍♂️", layout="wide")

# -----------------------------------------------------------------------------
# [데이터 로드]
# -----------------------------------------------------------------------------
file_path = 'price_list.xlsx'
if os.path.exists(file_path):
    try:
        df_raw = pd.read_excel(file_path, sheet_name='labor_cost')
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        st.stop()
else:
    st.error("price_list.xlsx 파일이 없습니다.")
    st.stop()

# -----------------------------------------------------------------------------
# 헤더 자동 파싱 (병합셀 완벽 대응)
# -----------------------------------------------------------------------------
header_mask = df_raw.apply(lambda r: r.astype(str).str.replace(" ", "").str.contains('^품명$|^품목$').any(), axis=1)
header_idx = df_raw[header_mask].index

if len(header_idx) > 0:
    idx = header_idx[0]
    if idx > 0:
        top_row = df_raw.iloc[idx-1].copy().ffill()
        top_list = [str(x).strip() if pd.notna(x) and str(x).strip().lower() not in ['nan', 'none'] else "" for x in top_row]
        bot_list = [str(x).strip() if pd.notna(x) and str(x).strip().lower() not in ['nan', 'none'] else "" for x in df_raw.iloc[idx]]
        
        new_cols = []
        for t, b in zip(top_list, bot_list):
            b_clean = b.replace(" ", "")
            t_clean = t.replace(" ", "")
            
            if b_clean in ['품명', '단위', '규격', '품목', '비고']: new_cols.append(b_clean)
            elif t_clean and b_clean: new_cols.append(f"{t_clean}_{b_clean}")
            elif t_clean: new_cols.append(t_clean)
            elif b_clean: new_cols.append(b_clean)
            else: new_cols.append("Unnamed")
        
        df_labor = df_raw.iloc[idx+1:].copy()
        df_labor.columns = new_cols
    else:
        df_labor = df_raw.iloc[idx+1:].copy()
        df_labor.columns = [str(x).strip().replace(" ", "") for x in df_raw.iloc[idx]]
else:
    df_labor = df_raw.copy()
    df_labor.columns = [str(x).strip().replace(" ", "") for x in df_labor.columns]

item_col = next((c for c in df_labor.columns if '품명' in c or '품목' in c), '품명')
spec_col = next((c for c in df_labor.columns if '규격' in c), '규격')

df_labor[item_col] = df_labor[item_col].fillna("").astype(str)
df_labor[spec_col] = df_labor[spec_col].fillna("").astype(str)

# -----------------------------------------------------------------------------
# 메인 화면
# -----------------------------------------------------------------------------
st.title("🕵️‍♂️ 폭별/로프사양별 인건비 산출")

c1, c2 = st.columns(2)
with c1:
    sel_item = st.selectbox("🕸️ 품명 선택", ['안전망2cm(방염)', '안전망2cm'])

# 1. 품목 필터링 및 멜트
df_matched = df_labor[df_labor[item_col].str.replace(" ", "").str.lower() == sel_item.replace(" ", "").lower()].copy()

id_vars = [c for c in df_matched.columns if '품' in c or '규격' in c or '단위' in c or '업체' in c or '비고' in c or 'Unnamed' in c]
val_vars = [c for c in df_matched.columns if c not in id_vars]

df_melt = df_matched.melt(id_vars=id_vars, value_vars=val_vars, var_name='단가종류', value_name='단가')
df_melt['단가'] = pd.to_numeric(df_melt['단가'].astype(str).str.replace(',', '').str.replace('원', ''), errors='coerce')
df_melt = df_melt[df_melt['단가'].notna()]

# 두께 파악
df_melt['thick'] = df_melt[spec_col].apply(lambda s: int(m.group(1)) if (m := re.search(r'(12|10|8|6)(?:mm|m/m|파이|가공|t)', str(s).lower().replace(" ",""))) else None)

# 미가공 단가
net_rows = df_melt[df_melt['thick'].isna() | (df_melt[spec_col].str.strip() == '-')]
default_net = float(net_rows['단가'].iloc[0]) if not net_rows.empty else 830.0
if default_net > 5000: default_net /= 50.0

st.markdown("<br><b>⚙️ 원가 기본 설정 (수정 가능)</b>", unsafe_allow_html=True)

# 2. 로프 단가 및 소요량 입력
rope_base = {6: 12000, 8: 20000, 10: 30000, 12: 43000}
r1, r2, r3, r4, r5, r6 = st.columns(6)
with r1: net_price = st.number_input(f"{sel_item} 미가공 (원/m²)", value=float(default_net), step=10.0)
with r2: r_price_6 = st.number_input("6mm 로프 (원/롤)", value=float(rope_base[6]), step=500.0)
with r3: r_price_8 = st.number_input("8mm 로프 (원/롤)", value=float(rope_base[8]), step=500.0)
with r4: r_price_10 = st.number_input("10mm 로프 (원/롤)", value=float(rope_base[10]), step=500.0)
with r5: r_price_12 = st.number_input("12mm 로프 (원/롤)", value=float(rope_base[12]), step=500.0)
with r6: rope_length_per_roll = st.number_input("1롤당 로프 소요량 (m)", value=126.0, step=1.0)

rope_prices = {6: r_price_6, 8: r_price_8, 10: r_price_10, 12: r_price_12}
st.divider()

# 3. 계산 및 결과 출력
df_calc = df_melt[df_melt['thick'].notna()].copy()

if df_calc.empty:
    st.warning("가공품(6mm, 8mm 등) 단가 데이터가 엑셀에 없습니다.")
else:
    results = []
    widths = [1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0]
    
    for _, row in df_calc.iterrows():
        thick = row['thick']
        kind = row['단가종류']
        proc_price_m2 = row['단가'] if row['단가'] < 5000 else row['단가'] / 50.0
        
        for w in widths:
            area = w * 50.0
            total_sales = area * proc_price_m2
            net_cost = area * net_price
            rope_cost = (rope_prices[thick] / 200.0) * rope_length_per_roll
            labor_cost = total_sales - net_cost - rope_cost
            
            results.append({'폭(m)': w, '두께(mm)': thick, '단가종류': kind, '인건비': labor_cost})

    if results:
        df_res = pd.DataFrame(results)
        df_pivot = df_res.pivot_table(index='폭(m)', columns=['두께(mm)', '단가종류'], values='인건비', aggfunc='first')
        df_pivot.index = df_pivot.index.map(lambda x: f"{x:g}m")
        
        def clean_col(c): return str(c).replace("_단가", "").replace("단가", "").strip()
        df_pivot.columns = pd.MultiIndex.from_tuples([(f"{int(c[0])}mm", clean_col(c[1])) for c in df_pivot.columns])
        
        st.subheader("📋 1롤당 순수인건비 산출 결과")
        st.dataframe(df_pivot.style.format("{:,.0f}원", na_rep="-"), use_container_width=True, height=550)
