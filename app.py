import streamlit as st
import pandas as pd
import io

# --- 1. 기본 설정 ---
st.set_page_config(page_title="💰 멀티 규격 비교기")
st.title("⚖️ 매입처 비교 (품목별 차액 분석)")
st.info("👇 '업체명', '품명', '규격1', '규격2', '단가' 등이 포함된 엑셀을 올려주세요.")

# --- 2. 엑셀 업로드 ---
uploaded_file = st.file_uploader("엑셀 파일 업로드 (xlsx)", type=['xlsx'])

# --- 3. 데이터 로딩 및 가공 ---
if uploaded_file is not None:
    try:
        raw_df = pd.read_excel(uploaded_file)
        raw_df.columns = raw_df.columns.str.strip() # 공백 제거
        
        # [자동 감지] 컬럼 찾기
        cols = raw_df.columns
        vendor_col = next((c for c in cols if '업체' in c), None)
        item_col = next((c for c in cols if '품명' in c or '품목' in c), None)
        price_col = next((c for c in cols if '단가' in c or '가격' in c or '금액' in c), None)
        
        # '규격' 글자가 들어간 모든 컬럼을 찾음 (규격1, 규격2, 색상, 사이즈 등)
        spec_cols = [c for c in cols if '규격' in c]

        if not all([vendor_col, item_col, price_col]):
            st.error("❌ 필수 컬럼('업체명', '품명', '단가')을 찾을 수 없습니다.")
            st.stop()
            
        if not spec_cols:
            st.warning("⚠️ '규격' 컬럼이 감지되지 않았습니다. 품명으로만 구분합니다.")
            
        st.success(f"✅ 감지된 규격 항목: {', '.join(spec_cols)}")

        # 피벗 생성 (품명 + 모든 규격 컬럼을 기준으로 묶음)
        index_cols = [item_col] + spec_cols
        pivot_df = raw_df.pivot_table(
            index=index_cols, 
            columns=vendor_col, 
            values=price_col, 
            aggfunc='first'
        ).reset_index()
        
        # 업체 목록
        vendor_list = [c for c in pivot_df.columns if c not in index_cols]
        
    except Exception as e:
        st.error(f"오류 발생: {e}")
        st.stop()

else:
    # 샘플 데이터 (다중 규격 예시)
    st.warning("아래는 '규격1', '규격2'가 있는 예시입니다.")
    data = [
        {"업체명": "A유통", "품명": "사과", "규격1": "10kg", "규격2": "선물용", "단가": 55000},
        {"업체명": "B농산", "품명": "사과", "규격1": "10kg", "규격2": "선물용", "단가": 53000}, # B가 쌈
        {"업체명": "A유통", "품명": "사과", "규격1": "10kg", "규격2": "가정용", "단가": 35000}, # A가 쌈
        {"업체명": "B농산", "품명": "사과", "규격1": "10kg", "규격2": "가정용", "단가": 37000},
    ]
    raw_df = pd.DataFrame(data)
    vendor_col, item_col, price_col = "업체명", "품명", "단가"
    spec_cols = ["규격1", "규격2"]
    index_cols = [item_col] + spec_cols
    pivot_df = raw_df.pivot_table(index=index_cols, columns=vendor_col, values=price_col, aggfunc='first').reset_index()
    vendor_list = ["A유통", "B농산"]

# --- 4. 비교 계산기 화면 ---
st.divider()
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🛒 담기")
    
    # 1. 품명 선택
    items = pivot_df[item_col].unique()
    selected_item = st.selectbox("품명", items)
    
    # 선택된 품명에 해당하는 데이터만 남김
    filtered_df = pivot_df[pivot_df[item_col] == selected_item]
    
    # 2. 동적 규격 선택창 생성
    selected_specs = {}
    for spec_col in spec_cols:
        options = filtered_df[spec_col].unique()
        choice = st.selectbox(f"{spec_col} 선택", options)
        selected_specs[spec_col] = choice
        filtered_df = filtered_df[filtered_df[spec_col] == choice]
        
    qty = st.number_input("수량", min_value=1, value=10)
    
    if 'cart_multi' not in st.session_state:
        st.session_state.cart_multi = []
        
    if st.button("목록에 추가 ⬇️", use_container_width=True):
        if filtered_df.empty:
            st.error("해당 조건의 상품이 없습니다.")
        else:
            row = filtered_df.iloc[0] # 최종 1개 행 확정
            
            # 최저가 로직
            best_vendor = None
            min_price = float('inf')
            max_price = float('-inf') # 차액 계산용
            line_total = {}
            
            for v in vendor_list:
                u_price = row[v]
                if pd.isna(u_price):
                    line_total[v] = 0
                    continue
                total_price = u_price * qty
                line_total[v] = total_price
                
                if total_price < min_price:
                    min_price = total_price
                    best_vendor = v
                if total_price > max_price:
                    max_price = total_price
            
            # 차액 계산 (가장 비싼 곳 - 가장 싼 곳)
            diff = max_price - min_price

            # 장바구니 데이터 구성
            cart_item = {
                "품명": selected_item,
                "수량": qty,
                "추천": best_vendor,
                "차액": diff, # 개별 품목 차액 추가
                "최저가_합계": min_price # 나중에 최적 조합 계산용
            }
            # 선택한 규격들도 장바구니에 표시
            for k, v in selected_specs.items():
                cart_item[k] = v
                
            cart_item.update(line_total)
            st.session_state.cart_multi.append(cart_item)

with col2:
    st.subheader("📊 최저가 분석 결과")
    
    if st.session_state.cart_multi:
        res_df = pd.DataFrame(st.session_state.cart_multi)
        
        # 화면 표시용 컬럼 정리 (차액 추가)
        display_cols = ["품명"] + spec_cols + ["수량", "추천", "차액"] + vendor_list
        
        # 숫자 포맷팅 (보기 좋게 콤마 찍기) - Streamlit Dataframe 설정
        st.dataframe(
            res_df[display_cols], 
            use_container_width=True, 
            hide_index=True
        )
        
        st.divider()
        
        # 1. 업체별 단순 총액 비교 (몰아주기 전략)
        totals = {}
        for v in vendor_list:
            totals[v] = res_df[v].sum()
            
        best_total_vendor = min(totals, key=totals.get)
        min_total = totals[best_total_vendor]
        
        # 2. 품목별 최적 조합 총액 (찢어주기 전략)
        optimal_total = res_df["최저가_합계"].sum()
        saving_by_split = min_total - optimal_total

        # 결과 카드 표시
        cols = st.columns(len(vendor_list))
        for i, v in enumerate(vendor_list):
            is_best = (v == best_total_vendor)
            delta_color = "normal" if is_best else "off"
            cols[i].metric(f"{v} 총액", f"{int(totals[v]):,}원", delta="최저가" if is_best else None, delta_color=delta_color)
        
        st.markdown("---")
        
        # 핵심: 찢어 보내기 vs 몰아 보내기 비교
        if saving_by_split > 0:
            st.success(f"### 💡 꿀팁: 품목별로 찢어서 보내면 {saving_by_split:,}원 더 아낍니다!")
            st.write(f"👉 **A/B로 나눠서 보낼 때 총액:** **{int(optimal_total):,}원**")
            st.write(f"(한 곳으로 몰아 보낼 때보다 **{saving_by_split:,}원** 이득)")
        else:
            st.info(f"💡 한 곳({best_total_vendor})으로 몰아서 주문해도 가격 차이가 없습니다.")

        if st.button("초기화"):
            st.session_state.cart_multi = []
            st.rerun()
