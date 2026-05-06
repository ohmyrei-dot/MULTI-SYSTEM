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
        st.session_state['df_labor'] = pd.read_excel(file_path, sheet_name='labor_cost')
    except ValueError:
        try:
            if 'df_labor' not in st.session_state:
                st.session_state['df_labor'] = pd.read_excel(file_path, sheet_name='Purchase_매입단가')
        except:
            st.error(f"🚨 '{file_path}' 파일에 데이터를 읽을 수 있는 시트가 없습니다.")
            st.stop()
else:
    st.error(f"🚨 '{file_path}' 파일이 존재하지 않습니다.")
    st.stop()

# -----------------------------------------------------------------------------
# 메인 로직
# -----------------------------------------------------------------------------
st.title("🕵️‍♂️ Labor Cost Breakdown")
st.markdown("폭(Width)별, 단가별(기존/신규) 매입단가를 분석하여 **1롤당 순수 가공 인건비 마진**을 비교합니다.")

try:
    df_labor = st.session_state['df_labor'].copy()
    df_labor.columns = df_labor.columns.astype(str).str.strip().str.replace(" ", "")

    item_col = next((c for c in df_labor.columns if '품명' in c or '품목' in c), '품명')
    spec_col = next((c for c in df_labor.columns if '규격' in c), '규격')
    note_col = next((c for c in df_labor.columns if '비고' in c), '비고')
    if note_col not in df_labor.columns: df_labor[note_col] = ""
    
    df_labor[item_col] = df_labor[item_col].fillna("").astype(str)
    df_labor[spec_col] = df_labor[spec_col].fillna("").astype(str)
    df_labor[note_col] = df_labor[note_col].fillna("").astype(str)

    # 1. 설정 영역
    st.subheader("1. 분석 조건 설정")
    c1, c2 = st.columns(2)
    with c1:
        sel_item = st.selectbox("🕸️ 품명 선택", ['안전망2cm', '안전망2cm(방염)'])
    with c2:
        st.info("💡 'labor_cost' 시트의 규격에 `-` 가 표시된 항목을 미가공 원가로 자동 인식합니다.")

    # --- 품명 필터링 ---
    sel_item_clean = sel_item.replace(" ", "").lower()
    df_matched = df_labor[df_labor[item_col].str.replace(" ", "").str.lower() == sel_item_clean].copy()

    # --- 단가 열 멜트 ---
    id_vars = [c for c in df_matched.columns if '품' in c or '규격' in c or '단위' in c or '업체' in c or '비고' in c]
    val_vars = [c for c in df_matched.columns if c not in id_vars]

    df_melt = df_matched.melt(id_vars=id_vars, value_vars=val_vars, var_name='단가종류', value_name='단가')
    df_melt['단가'] = pd.to_numeric(df_melt['단가'].astype(str).str.replace(',', '').str.replace('원', ''), errors='coerce')
    df_melt = df_melt[df_melt['단가'].notna()]

    # 미가공 단가 추출
    net_rows = df_melt[df_melt[spec_col].str.strip() == '-']
    default_net_price_m2 = 830.0
    if not net_rows.empty:
        raw_net = float(net_rows['단가'].iloc[0])
        if raw_net > 5000: default_net_price_m2 = raw_net / 50.0
        else: default_net_price_m2 = raw_net

    st.markdown("<br><b>⚙️ 기준 원자재 단가 및 로프 소요량 (자유롭게 수정 가능)</b>", unsafe_allow_html=True)
    
    rope_base = {6: 12000, 8: 20000, 10: 30000, 12: 43000}
    r1, r2, r3, r4, r5, r6 = st.columns(6)
    with r1: net_price = st.number_input(f"{sel_item} 미가공 (원/m²)", value=float(default_net_price_m2), step=10.0)
    with r2: r_price_6 = st.number_input("6mm 로프 (200m/롤)", value=float(rope_base[6]), step=500.0)
    with r3: r_price_8 = st.number_input("8mm 로프 (200m/롤)", value=float(rope_base[8]), step=500.0)
    with r4: r_price_10 = st.number_input("10mm 로프 (200m/롤)", value=float(rope_base[10]), step=500.0)
    with r5: r_price_12 = st.number_input("12mm 로프 (200m/롤)", value=float(rope_base[12]), step=500.0)
    with r6: rope_length_per_roll = st.number_input("1롤 로프 소요량 (m)", value=126.0, step=1.0)

    rope_prices = {6: r_price_6, 8: r_price_8, 10: r_price_10, 12: r_price_12}
    
    st.divider()

    # 2. 데이터 추출
    st.subheader(f"2. [{sel_item}] 인건비 구조 분석 결과")

    def extract_details(row):
        s_str = str(row[spec_col]).lower().replace(" ", "")
        n_str = str(row[note_col]).lower().replace(" ", "")
        full_txt = s_str + "|" + n_str
        
        # 두께 파악 (매우 관대하게 스캔)
        thick = None
        t_match = re.search(r'(12|10|8|6)(?:mm|m/m|파이|가공|t)', full_txt)
        if t_match: 
            thick = int(t_match.group(1))
        else:
            for t in [12, 10, 8, 6]:
                if re.search(rf'(?<!\d){t}(?!\d)', full_txt):
                    thick = t
                    break

        # 폭 파악 (1*50, 1.5 등)
        width = None
        w_match = re.search(r'(?<!\d)(\d+(?:\.\d+)?)\s*(?:m|m/m)?\s*[*xX]', s_str)
        if w_match: width = float(w_match.group(1))
        else:
            w_match2 = re.search(r'^(?<!\d)(\d+(?:\.\d+)?)(?:m)?$', s_str)
            if w_match2: width = float(w_match2.group(1))
            
        return pd.Series({'width': width, 'thick': thick})

    if not df_melt.empty:
        df_melt[['width', 'thick']] = df_melt.apply(extract_details, axis=1)
        df_calc = df_melt[(df_melt['width'].notna()) & (df_melt['thick'].isin(rope_prices.keys()))].copy()
    else:
        df_calc = pd.DataFrame()

    if df_calc.empty:
        st.warning(f"{sel_item} 가공품 데이터(폭, 두께)를 추출할 수 없습니다. 엑셀의 '규격'과 '비고'란을 확인해주세요.")
    else:
        results = []
        for _, row in df_calc.iterrows():
            raw_price = row['단가']
            if raw_price <= 0: continue
            
            width = row['width']
            thick = row['thick']
            col_name = str(row['단가종류'])
            area = width * 50.0
            
            # 매입총액 산출 (롤단가 vs 해배단가 자동분류)
            purchase_total_roll = raw_price if raw_price > 5000 else raw_price * area
            
            # 원가 산출
            net_cost_roll = area * net_price
            rope_cost_roll = (rope_prices[thick] / 200.0) * rope_length_per_roll
            total_cost_roll = net_cost_roll + rope_cost_roll
            
            labor_roll = purchase_total_roll - total_cost_roll
            
            results.append({
                '폭(m)': width,
                '두께(mm)': thick,
                '단가종류': col_name,
                '순수인건비 (1롤)': labor_roll
            })

        if not results:
            st.warning("계산 가능한 가공품 단가 데이터가 없습니다.")
        else:
            df_res = pd.DataFrame(results)
            
            st.markdown("#### 📊 폭 vs [두께 & 단가종류] 별 [1롤당 순수인건비] 비교표")
            
            # 2단 피벗 테이블 구성
            df_pivot = df_res.pivot_table(index='폭(m)', columns=['두께(mm)', '단가종류'], values='순수인건비 (1롤)', aggfunc='first')
            df_pivot.index = df_pivot.index.map(lambda x: f"{x:g}m")
            
            # 컬럼을 멀티인덱스(2단 구조)로 변환하여 깔끔하게 표시
            df_pivot.columns = pd.MultiIndex.from_tuples(
                [(f"{int(c[0])}mm 가공", str(c[1])) for c in df_pivot.columns]
            )
            
            st.dataframe(
                df_pivot.style.format(lambda x: f"🔥 {int(x):,}원" if pd.notna(x) else "-"), 
                use_container_width=True
            )
            
            st.info("💡 **분석 포인트:** 가로줄이 '로프 두께'와 '기존/신규 단가' 2단으로 나뉘어 출력됩니다. 폭이 넓어질수록 마진이 어떻게 변하는지 확인하세요.")

except Exception as e:
    st.error(f"오류 발생: {e}")
