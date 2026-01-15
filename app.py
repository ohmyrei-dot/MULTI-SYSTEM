import streamlit as st
import pandas as pd

# --- 1. 기본 설정 ---
st.set_page_config(page_title="💰 바로 쓰는 비교기")
st.title("⚖️ 매입처 단가 비교 (테스트용)")

# --- 2. 테스트 데이터 (사과, 배 미리 입력해둠) ---
# 사장님이 엑셀 없이 바로 눌러볼 수 있게 데이터를 여기다 넣었습니다.
data = [
    {"품명": "사과(부사)", "규격": "10kg", "A업체_단가": 35000, "B업체_단가": 33000}, # B가 더 쌈
    {"품명": "사과(부사)", "규격": "5kg",  "A업체_단가": 18000, "B업체_단가": 19000}, # A가 더 쌈
    {"품명": "배(나주)",   "규격": "15kg", "A업체_단가": 45000, "B업체_단가": 47000}, # A가 더 쌈
    {"품명": "포장박스",   "규격": "1개",  "A업체_단가": 500,   "B업체_단가": 450},   # B가 더 쌈
]
df = pd.DataFrame(data)

st.info("👇 엑셀 없이 바로 테스트 가능합니다. 아래 품목을 선택해보세요.")

# --- 3. 비교 계산기 화면 ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🛒 담기")
    
    # 품명 선택
    item_list = df["품명"].unique()
    item = st.selectbox("품명 선택", item_list)
    
    # 규격 선택
    spec_list = df[df["품명"] == item]["규격"].unique()
    spec = st.selectbox("규격 선택", spec_list)
    
    qty = st.number_input("수량", min_value=1, value=10)
    
    # 장바구니 (임시 저장소)
    if 'cart_test' not in st.session_state:
        st.session_state.cart_test = []
        
    if st.button("목록에 추가 ⬇️", use_container_width=True):
        # 데이터에서 단가 찾아오기
        row = df[(df["품명"] == item) & (df["규격"] == spec)].iloc[0]
        
        price_a = int(row["A업체_단가"])
        price_b = int(row["B업체_단가"])
        
        st.session_state.cart_test.append({
            "품명": item,
            "규격": spec,
            "수량": qty,
            "A업체": price_a * qty,
            "B업체": price_b * qty,
            "승자": "A업체" if price_a < price_b else "B업체"
        })

with col2:
    st.subheader("📊 결과 분석")
    
    if st.session_state.cart_test:
        res_df = pd.DataFrame(st.session_state.cart_test)
        
        # 내역 보여주기
        st.dataframe(res_df[["품명", "규격", "수량", "A업체", "B업체", "승자"]], hide_index=True)
        
        # 총액 계산
        total_a = res_df["A업체"].sum()
        total_b = res_df["B업체"].sum()
        diff = abs(total_a - total_b)
        
        c1, c2 = st.columns(2)
        c1.metric("A업체 총액", f"{total_a:,}원")
        c2.metric("B업체 총액", f"{total_b:,}원")
        
        st.divider()
        
        # 최종 결론
        if total_a < total_b:
            st.success(f"### 🎉 [A업체]가 {diff:,}원 더 쌉니다!")
        elif total_b < total_a:
            st.success(f"### 🎉 [B업체]가 {diff:,}원 더 쌉니다!")
        else:
            st.info("금액이 동일합니다.")
            
        if st.button("초기화"):
            st.session_state.cart_test = []
            st.rerun()
    else:
        st.caption("왼쪽에서 '목록에 추가' 버튼을 눌러보세요.")
