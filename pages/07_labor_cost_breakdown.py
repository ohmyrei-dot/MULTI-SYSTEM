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
note_col = next((c for c in df_labor.columns if '비고' in c), '비고')
if note_col not in df_labor.columns: df_labor[note_col] = ""

df_labor[item_col] = df_labor[item_col].fillna("").astype(str)
df_labor[spec_col] = df_labor[spec_col].fillna("").astype(str)
df_labor[note_col] = df_labor[note_col].fillna("").astype(str)

# -----------------------------------------------------------------------------
# 메인 화면
# -----------------------------------------------------------------------------
st.title("🕵️‍♂️ 폭별/로프사양별 인건비 산출")

c1, c2 = st.columns(2)
with c1:
    sel_item = st.selectbox("🕸️ 품명 선택", ['안전망2cm(방염)', '안전망2cm'])

# 전체 데이터를 Melt
id_vars = [c for c in df_labor.columns if '품' in c or '규격' in c or '단위' in c or '업체' in c or '비고' in c or 'Unnamed' in c]
val_vars = [c for c in df_labor.columns if c not in id_vars]

df_melt = df_labor.melt(id_vars=id_vars, value_vars=val_vars, var_name='단가종류', value_name='단가')
df_melt['단가'] = pd.to_numeric(df_melt['단가'].astype(str).str.replace(',', '').str.replace('원', ''), errors='coerce')
df_melt = df_melt[df_melt['단가'].notna()]
df_melt['단가종류'] = df_melt['단가종류'].apply(lambda c: str(c).replace("_단가", "").replace("단가", "").strip())

# 두께 추출 함수
def get_thick(s):
    m = re.search(r'(12|10|8|6)(?:mm|m/m|파이|가공|t)', str(s).lower().replace(" ",""))
    if m: return int(m.group(1))
    m2 = re.search(r'(?<!\d)(12|10|8|6)(?!\d)', str(s))
    if m2: return int(m2.group(1))
    return None

# 로프 데이터 분류
df_rope = df_melt[df_melt[item_col].str.contains('로프', na=False)].copy()
df_rope['thick'] = df_rope[spec_col].apply(get_thick)

# 안전망 데이터 분류 (일반과 방염을 철저하게 분리)
df_net_all = df_melt[df_melt[item_col].str.replace(" ", "").str.contains('안전망2cm', na=False)].copy()

def is_flame(row):
    return '방염' in str(row[item_col]) + str(row[spec_col]) + str(row[note_col])

df_net_all['is_flame'] = df_net_all.apply(is_flame, axis=1)

if '방염' in sel_item:
    df_net = df_net_all[df_net_all['is_flame']].copy()
else:
    df_net = df_net_all[~df_net_all['is_flame']].copy()

df_net['thick'] = df_net[spec_col].apply(get_thick)

kinds_all = sorted(list(set([k for k in df_net['단가종류'].unique() if k and str(k).lower() != 'nan'])))

with c2:
    sel_kinds = st.multiselect("비교할 단가 종류 선택", kinds_all, default=kinds_all)

if not sel_kinds:
    st.warning("단가를 하나 이상 선택해주세요.")
    st.stop()

# -----------------------------------------------------------------------------
# 원가 기본 설정 표
# -----------------------------------------------------------------------------
st.markdown("<br><b>⚙️ 원가 기본 설정 (가공망 매입가, 망 원가, 로프 원가 모두 표시/수정 가능)</b>", unsafe_allow_html=True)

base_idx = [
    '[안전망] 미가공(m²)',
    '[안전망] 6mm가공(m²)',
    '[안전망] 8mm가공(m²)',
    '[안전망] 10mm가공(m²)',
    '[안전망] 12mm가공(m²)',
    '[로프] 6mm(롤)',
    '[로프] 8mm(롤)',
    '[로프] 10mm(롤)',
    '[로프] 12mm(롤]'
]

df_base = pd.DataFrame(0.0, index=base_idx, columns=sel_kinds)

# 데이터 매칭
for _, r in df_net.iterrows():
    t, k, v = r['thick'], r['단가종류'], r['단가']
    if k in df_base.columns:
        val_m2 = v if v < 5000 else v / 50.0
        if pd.isna(t) or r[spec_col].strip() == '-':
            df_base.loc['[안전망] 미가공(m²)', k] = val_m2
        elif t in [6, 8, 10, 12]:
            df_base.loc[f'[안전망] {int(t)}mm가공(m²)', k] = val_m2

for _, r in df_rope.iterrows():
    t, k, v = r['thick'], r['단가종류'], r['단가']
    if pd.notna(t) and int(t) in [6, 8, 10, 12] and k in df_base.columns:
        df_base.loc[f'[로프] {int(t)}mm(롤)', k] = float(v)

c_set1, c_set2 = st.columns([7, 3])
with c_set1:
    edited_base = st.data_editor(df_base, use_container_width=True, height=350)
with c_set2:
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    rope_length_per_roll = st.number_input("1롤당 로프 소요량 (m)", value=126.0, step=1.0)

st.divider()

# -----------------------------------------------------------------------------
# 계산 및 결과 출력
# -----------------------------------------------------------------------------
results = []
widths = [1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0]

for t in [6, 8, 10, 12]:
    for k in sel_kinds:
        proc_price_m2 = edited_base.loc[f'[안전망] {t}mm가공(m²)', k]
        net_price = edited_base.loc['[안전망] 미가공(m²)', k]
        rope_price = edited_base.loc[f'[로프] {t}mm(롤)', k]
        
        if proc_price_m2 <= 0: continue
        
        for w in widths:
            area = w * 50.0
            total_sales = area * proc_price_m2
            net_cost = area * net_price
            rope_cost = (rope_price / 200.0) * rope_length_per_roll
            
            labor_roll = total_sales - net_cost - rope_cost
            labor_m2 = labor_roll / area if area > 0 else 0
            
            # 요청하신 대로 '원' 단어를 제외하고 숫자와 콤마만 표시
            display_text = f"{int(labor_roll):,}\n({int(labor_m2):,}/m²)"
            results.append({'폭(m)': w, '두께(mm)': t, '단가종류': k, '인건비': display_text})

if results:
    df_res = pd.DataFrame(results)
    df_pivot = df_res.pivot_table(index='폭(m)', columns=['두께(mm)', '단가종류'], values='인건비', aggfunc='first')
    df_pivot.index = df_pivot.index.map(lambda x: f"{x:g}m")
    
    df_pivot = df_pivot.sort_index(axis=1, level=0)
    df_pivot.columns = pd.MultiIndex.from_tuples([(f"{int(c[0])}mm", c[1]) for c in df_pivot.columns])
    
    st.subheader("📋 1롤(50m)당 순수인건비 산출 결과")
    st.dataframe(df_pivot, use_container_width=True, height=650)
else:
    st.warning("계산 가능한 가공단가(0원 이상)가 설정표에 없습니다.")
