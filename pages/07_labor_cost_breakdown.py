import streamlit as st
import pandas as pd
import re
import os

st.set_page_config(page_title="Labor Cost Breakdown", page_icon="🕵️‍♂️", layout="wide")

# -----------------------------------------------------------------------------
# [데이터 강제 로드 로직] 세션에 데이터가 없으면 불러오기
# -----------------------------------------------------------------------------
file_path = 'price_list.xlsx'
if 'df_purch' not in st.session_state:
    if os.path.exists(file_path):
        st.session_state['df_purch'] = pd.read_excel(file_path, sheet_name='Purchase_매입단가')
    else:
        st.error(f"🚨 '{file_path}' 파일이 존재하지 않습니다.")
        st.stop()

# -----------------------------------------------------------------------------
# 메인 로직
# -----------------------------------------------------------------------------
st.title("🕵️‍♂️ Labor Cost Breakdown")
st.markdown("매입업체의 폭(Width)별 매입단가를 분석하여, **원가(망+로프)를 제외한 순수 가공 인건비**가 어떻게 변하는지 추적합니다.")

try:
    df_purch = st.session_state['df_purch'].copy()
    
    # 컬럼명 공백 완벽 제거 (예: '규격1 ' -> '규격1')
    df_purch.columns = df_purch.columns.astype(str).str.strip().str.replace(" ", "")

    vendor_col = next((c for c in df_purch.columns if '매입업체' in c or '업체' in c), '매입업체')
    price_col = next((c for c in df_purch.columns if '단가' in c or '금액' in c), '현재매입단가')
    item_col = next((c for c in df_purch.columns if '품목' in c or '품명' in c), '품목')
    
    spec_col = '규격1' if '규격1' in df_purch.columns else '규격' if '규격' in df_purch.columns else '규격'
    note_col = '규격2' if '규격2' in df_purch.columns else '비고1' if '비고1' in df_purch.columns else '비고'
    
    if spec_col not in df_purch.columns: df_purch[spec_col] = ""
    if note_col not in df_purch.columns: df_purch[note_col] = ""
    
    df_purch[spec_col] = df_purch[spec_col].fillna("").astype(str)
    df_purch[note_col] = df_purch[note_col].fillna("").astype(str)
    df_purch[item_col] = df_purch[item_col].fillna("").astype(str)

    all_vendors = sorted(df_purch[vendor_col].dropna().unique().astype(str))
    
    # 1. 설정 영역
    st.subheader("1. 분석 조건 설정")
    c1, c2 = st.columns(2)
    with c1:
        sel_vendor = st.selectbox("🏢 분석할 매입업체 선택", all_vendors, index=all_vendors.index('태양산자') if '태양산자' in all_vendors else 0)
    with c2:
        sel_item = st.selectbox("🕸️ 안전망 종류 선택", ['안전망2cm', '안전망2cm KS망', '안전망1cm', '안전망1cm KS망'])

    st.markdown("<br><b>⚙️ 기준 원자재 단가 (인건비 역산용)</b>", unsafe_allow_html=True)
    st.caption("해당 업체의 미가공 단가를 자동으로 불러옵니다. (없으면 기본값 적용)")
    
    # --- 유연한 필터링 로직 ---
    target_cm = "2cm" if "2cm" in sel_item else "1cm"
    target_ks = "KS" in sel_item

    def is_target_item(row):
        item_str = str(row[item_col]).replace(" ", "").upper()
        full_str = (item_str + "|" + str(row[spec_col]) + "|" + str(row[note_col])).replace(" ", "").upper()
        
        if target_cm == "2CM":
            if "1CM" in item_str: return False
        else:
            if "1CM" not in item_str: return False
        
        has_ks = 'KS' in full_str
        if target_ks and not has_ks: return False
        if not target_ks and has_ks: return False
        
        return True

    df_v = df_purch[df_purch[vendor_col] == sel_vendor].copy()
    df_v_matched = df_v[df_v.apply(is_target_item, axis=1)].copy()
    
    # 미가공 단가 추출 ('-', 비어있음, '미가공' 모두 인식)
    def is_net_only(r):
        s = str(r[note_col]).replace(' ', '').lower()
        return s in ['', '-', 'nan'] or ('미가공' in s and not re.search(r'\d+mm', s))

    net_base_row = df_v_matched[df_v_matched.apply(is_net_only, axis=1)]
    
    default_net_price_m2 = 830.0
    if not net_base_row.empty:
        base_raw_str = str(net_base_row.iloc[0][price_col]).replace(",", "").replace("원", "").strip()
        try:
            base_raw_price = float(base_raw_str)
            if base_raw_price > 5000:
                spec_str = str(net_base_row.iloc[0][spec_col]).replace(" ", "").lower()
                w_match = re.search(r'(\d+(?:\.\d+)?)[a-z]*[*x]\s*50', spec_str)
                if w_match:
                    area = float(w_match.group(1)) * 50.0
                    default_net_price_m2 = base_raw_price / area
            else:
                default_net_price_m2 = base_raw_price
        except:
            pass

    # PP로프 단가 설정
    rope_base = {6: 12000, 8: 20000, 10: 30000, 12: 43000}
    
    r1, r2, r3, r4, r5 = st.columns(5)
    with r1: net_price = st.number_input(f"{sel_item} 미가공 (원/m²)", value=float(default_net_price_m2), step=10.0)
    with r2: r_price_6 = st.number_input("6mm 로프 (200m/롤)", value=float(rope_base[6]), step=500.0)
    with r3: r_price_8 = st.number_input("8mm 로프 (200m/롤)", value=float(rope_base[8]), step=500.0)
    with r4: r_price_10 = st.number_input("10mm 로프 (200m/롤)", value=float(rope_base[10]), step=500.0)
    with r5: r_price_12 = st.number_input("12mm 로프 (200m/롤)", value=float(rope_base[12]), step=500.0)

    rope_prices = {6: r_price_6, 8: r_price_8, 10: r_price_10, 12: r_price_12}
    rope_length_per_roll = 126.0 # 50m 기준 1롤당 가공 로프 소요량

    st.divider()

    # 2. 데이터 추출 및 계산
    st.subheader(f"2. [{sel_vendor}] 인건비 구조 분석 결과")
    
    def extract_details(row):
        spec1_str = str(row[spec_col]).replace(" ", "").lower()
        spec2_str = str(row[note_col]).replace(" ", "").lower()
        full_str = spec1_str + "|" + spec2_str
        
        # 로프 두께 파악 (8mm, 8가공, 8파이 등)
        thick = None
        t_match = re.search(r'(\d+)(?:mm|m/m|파이|가공)', full_str)
        if t_match:
            thick = int(t_match.group(1))
        else:
            for t in [12, 10, 8, 6]:
                if str(t) in spec2_str:
                    thick = t
                    break
        
        # 폭 파악 (1m*50, 1.5, 등 첫 숫자 추출)
        width = None
        w_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:m|m/m)?\s*[*xX]\s*\d+', spec1_str)
        if w_match:
            width = float(w_match.group(1))
        else:
            w_match2 = re.search(r'(\d+(?:\.\d+)?)', spec1_str)
            if w_match2:
                width = float(w_match2.group(1))
            
        return pd.Series({'width': width, 'thick': thick})

    if not df_v_matched.empty:
        details = df_v_matched.apply(extract_details, axis=1)
        df_target = pd.concat([df_v_matched, details], axis=1)
        # 폭과 두께가 추출된 데이터만 필터
        df_target = df_target[(df_target['width'].notna()) & (df_target['thick'].isin(rope_prices.keys()))]
    else:
        df_target = pd.DataFrame()

    if df_target.empty:
        st.warning(f"선택한 업체({sel_vendor})의 {sel_item} 데이터에서 폭(m)과 로프 두께(mm)를 확인할 수 없습니다.")
        st.info(f"💡 엑셀의 '{spec_col}' 칸에 폭(예: 1m*50), '{note_col}' 칸에 두께(예: 8mm가공)가 있는지, 그리고 선택한 종류(KS 여부)가 맞는지 확인해주세요.")
    else:
        results = []
        for _, row in df_target.iterrows():
            raw_price_str = str(row[price_col]).replace(",", "").replace("원", "").strip()
            try:
                raw_price = float(raw_price_str)
            except:
                continue
                
            if raw_price == 0: continue
            
            width = row['width']
            thick = row['thick']
            area = width * 50.0
            
            # 매입단가가 롤 단위인지 m2 단위인지 자동 판별 (>5000이면 롤단위로 취급)
            if raw_price > 5000:
                purchase_total_roll = raw_price
                purchase_m2_price = raw_price / area
            else:
                purchase_total_roll = raw_price * area
                purchase_m2_price = raw_price
            
            # 원가 및 인건비 계산
            net_cost_roll = area * net_price
            rope_cost_roll = (rope_prices[thick] / 200.0) * rope_length_per_roll
            total_cost_roll = net_cost_roll + rope_cost_roll
            
            labor_roll = purchase_total_roll - total_cost_roll
            labor_m2 = labor_roll / area if area > 0 else 0
            
            results.append({
                '폭(m)': width,
                '두께(mm)': thick,
                '매입단가(환산 m²)': purchase_m2_price,
                '1롤 면적 (m²)': area,
                '망+로프 원가 (1롤)': total_cost_roll,
                '매입총액 (1롤)': purchase_total_roll,
                '순수인건비 (m²)': labor_m2,
                '순수인건비 (1롤)': labor_roll
            })

        if not results:
            st.warning("계산 가능한 단가 데이터가 없습니다.")
        else:
            df_res = pd.DataFrame(results)
            # 중복 시 첫 번째 값 유지 (안전장치)
            df_res = df_res.drop_duplicates(subset=['폭(m)', '두께(mm)'])
            df_res = df_res.sort_values(by=['폭(m)', '두께(mm)']).reset_index(drop=True)
            
            # -------------------------------------------------------------
            # 📊 피벗 테이블 (폭 vs 두께별 인건비)
            # -------------------------------------------------------------
            st.markdown("#### 📊 폭 vs 로프두께별 [1롤당 순수인건비] 비교표")
            
            df_pivot = df_res.pivot_table(index='폭(m)', columns='두께(mm)', values='순수인건비 (1롤)', aggfunc='first')
            df_pivot.index = df_pivot.index.map(lambda x: f"{x:g}m")
            df_pivot.columns = [f"{int(c)}mm 가공" for c in df_pivot.columns]
            
            st.dataframe(
                df_pivot.style.format(lambda x: f"🔥 {int(x):,}원" if pd.notna(x) else "-")
                              .background_gradient(cmap='Reds', axis=None), 
                use_container_width=True
            )
            
            # -------------------------------------------------------------
            # 📝 상세 분석 데이터
            # -------------------------------------------------------------
            st.markdown("<br>#### 📝 상세 분석 데이터", unsafe_allow_html=True)
            
            df_show = df_res.copy()
            df_show['폭(m)'] = df_show['폭(m)'].apply(lambda x: f"{x:g}m")
            df_show['두께(mm)'] = df_show['두께(mm)'].apply(lambda x: f"{x}mm")
            df_show['매입단가(환산 m²)'] = df_show['매입단가(환산 m²)'].apply(lambda x: f"{int(x):,}원")
            df_show['1롤 면적 (m²)'] = df_show['1롤 면적 (m²)'].apply(lambda x: f"{x:g}m²")
            df_show['망+로프 원가 (1롤)'] = df_show['망+로프 원가 (1롤)'].apply(lambda x: f"{int(x):,}원")
            df_show['매입총액 (1롤)'] = df_show['매입총액 (1롤)'].apply(lambda x: f"{int(x):,}원")
            df_show['순수인건비 (m²)'] = df_show['순수인건비 (m²)'].apply(lambda x: f"⚠️ {int(x):,}원")
            df_show['순수인건비 (1롤)'] = df_show['순수인건비 (1롤)'].apply(lambda x: f"🔥 {int(x):,}원")
            
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
            st.info("""
            💡 **분석 포인트**
            - 태양산자처럼 해배당 매입단가가 폭에 상관없이 일정하다면, 위의 표에서 **폭이 넓어질수록(아래로 갈수록) 1롤당 순수인건비가 눈덩이처럼 폭발적으로 증가**하는 것을 직관적으로 확인할 수 있습니다.
            """)

except Exception as e:
    st.error(f"오류 발생: {e}")
