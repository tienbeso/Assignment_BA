import io
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
from db import build_where, check_connection, run_query, sidebar_filters, sql_main, sql_risk

check_connection()
start, end, sizes, status = sidebar_filters()

where, params = build_where(start, end, sizes, status)
query_main = sql_main(where)
query_risk = sql_risk(where)

st.title("Chi tiết khách hàng")

st.subheader("Khách hàng có nguy cơ Churn cao")
st.caption("Điều kiện: có tháng dùng token vượt giới hạn gói, hoặc mở trên 3 support tickets.")

risk = run_query(query_risk, params)
st.write(f"Tìm thấy **{len(risk)}** khách hàng.")
st.dataframe(risk, use_container_width=True)

st.divider()

st.subheader("Xuất dữ liệu đã lọc")
df = run_query(query_main, params)

c1, c2 = st.columns(2)
c1.download_button("Tải CSV", df.to_csv(index=False).encode("utf-8-sig"),
                   file_name="saas_report.csv", mime="text/csv")

buffer = io.BytesIO()
df.to_excel(buffer, index=False)
c2.download_button("Tải Excel", buffer.getvalue(), file_name="saas_report.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.divider()

with st.expander("Xem câu lệnh SQL đang dùng"):
    st.markdown("**Truy vấn dữ liệu chính**")
    st.code(query_main, language="sql")
    st.markdown("**Truy vấn khách hàng nguy cơ cao**")
    st.code(query_risk, language="sql")
    st.markdown("**Giá trị tham số**")
    st.json({k: str(v) for k, v in params.items()})