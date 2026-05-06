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

# 전체 데이터를 먼저 Melt (로프 데이터도 가져오기 위함)
id_vars = [c for c in df_labor.columns if '품' in c or '규격' in c or '단위' in c or '업체' in c or '비고' in c or 'Unnamed' in c]
val_vars = [c for c in df_labor.columns if c not in id_vars]

df_melt = df_labor.melt(id_vars=id_vars, value_vars=val_vars, var_name='단가종류', value_name='단가')
df_melt['단가'] = pd.to_numeric(df_melt['단가'].astype(str).str.replace(',', '').str.replace('원', ''), errors='coerce')
df_melt = df_melt[df_melt['단가'].notna()]
df_melt['단가종류'] = df_melt['단가종류'].apply(lambda c: str(c).replace("_단가", "").replace("단가", "").strip())

# 로프 데이터 추출
df_rope = df_melt[df_melt[item_col].str.contains('로프', na=False)].copy()
df_rope['thick'] = df_rope[spec_col].apply(lambda s: int(m.group(1)) if (m := re.search(r'(12|10|8|6)(?:mm|m/m|파이|가공|t)', str(s).lower().replace(" ",""))) else None)

# 선택된 안전망 데이터 추출
df_net = df_melt[df_melt[item_col].str.replace(" ", "").str.lower() == sel_item.replace(" ", "").lower()].copy()
df_net['thick'] = df_net[spec_col].apply(lambda s: int(m.group(1)) if (m := re.search(r'(12|10|8|6)(?:mm|m/m|파이|가공|t)', str(s).lower().replace(" ",""))) else None)

# 단가종류 목록 (기존가, 신규가1 등)
kinds = [k for k in df_net['단가종류'].unique() if k and k != 'nan']

# --- 원가 기본 설정 표 (단가종류별 매핑) ---
st.markdown("<br><b>⚙️ 원가 기본 설정 (엑셀 자동 추출, 아래 표에서 직접 숫자 수정 가능)</b>", unsafe_allow_html=True)

base_idx = ['미가공(m²)', '6mm로프(롤)', '8mm로프(롤)', '10mm로프(롤)', '12mm로프(롤)']
df_base = pd.DataFrame(0, index=base_idx, columns=kinds)

# 미가공 원가 세팅
net_raw = df_net[df_net['thick'].isna() | (df_net[spec_col].str.strip() == '-')]
for _, r in net_raw.iterrows():
    if r['단가종류'] in df_base.columns:
        v = r['단가']
        df_base.loc['미가공(m²)', r['단가종류']] = v if v < 5000 else v / 50.0

# 로프 원가 세팅
for _, r in df_rope.iterrows():
    t, k, v = r['thick'], r['단가종류'], r['단가']
    if t in [6, 8, 10, 12] and k in df_base.columns:
        df_base.loc[f'{t}mm로프(롤)', k] = v

c_set1, c_set2 = st.columns([7, 3])
with c_set1:
    edited_base = st.data_editor(df_base, use_container_width=True)
with c_set2:
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    rope_length_per_roll = st.number_input("1롤당 로프 소요량 (m)", value=126.0, step=1.0)

st.divider()

# -----------------------------------------------------------------------------
# 계산 및 결과 출력
# -----------------------------------------------------------------------------
df_calc = df_net[df_net['thick'].notna()].copy()

if df_calc.empty:
    st.warning("가공품(6mm, 8mm 등) 단가 데이터가 엑셀에 없습니다.")
else:
    results = []
    widths = [1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0]
    
    for _, row in df_calc.iterrows():
        thick = row['thick']
        kind = row['단가종류']
        # 단가종류별 안전망/로프 원가를 편집된 표에서 가져옴
        net_price = edited_base.loc['미가공(m²)', kind]
        rope_price = edited_base.loc[f'{thick}mm로프(롤)', kind]
        
        proc_price_m2 = row['단가'] if row['단가'] < 5000 else row['단가'] / 50.0
        
        for w in widths:
            area = w * 50.0
            total_sales = area * proc_price_m2
            net_cost = area * net_price
            rope_cost = (rope_price / 200.0) * rope_length_per_roll
            
            labor_roll = total_sales - net_cost - rope_cost
            labor_m2 = labor_roll / area if area > 0 else 0
            
            # 해배당 단가도 괄호안에 같이 표시
            display_text = f"{int(labor_roll):,}원\n(m²당 {int(labor_m2):,}원)"
            
            results.append({'폭(m)': w, '두께(mm)': thick, '단가종류': kind, '인건비': display_text})

    if results:
        df_res = pd.DataFrame(results)
        df_pivot = df_res.pivot_table(index='폭(m)', columns=['두께(mm)', '단가종류'], values='인건비', aggfunc='first')
        df_pivot.index = df_pivot.index.map(lambda x: f"{x:g}m")
        
        # 컬럼 포맷팅
        df_pivot.columns = pd.MultiIndex.from_tuples([(f"{int(c[0])}mm", c[1]) for c in df_pivot.columns])
        
        st.subheader("📋 1롤(50m)당 순수인건비 산출 결과")
        # 줄바꿈(\n) 적용 및 포맷팅 (글씨체 설정)
        st.dataframe(df_pivot, use_container_width=True, height=600)
