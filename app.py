
import pandas as pd
import plotly.express as px
import streamlit as st

from db import build_where, check_connection, run_query, sidebar_filters, sql_main

st.set_page_config(page_title="SaaS & AI Cost Dashboard", layout="wide")

check_connection()
start, end, sizes, status = sidebar_filters()

# ----- Lấy dữ liệu -----
where, params = build_where(start, end, sizes, status)
df = run_query(sql_main(where), params)
if df.empty:
    st.warning("Không có dữ liệu với bộ lọc hiện tại.")
    st.stop()

df["month"] = pd.to_datetime(df["usage_month"]).dt.to_period("M").dt.to_timestamp()
customers = df.drop_duplicates("customer_id")  # mỗi khách 1 dòng

# ----- KPI -----
st.title("Tổng quan SaaS & Chi phí AI")

is_paying = df["status"].isin(["Active", "Upgraded"])
mrr = customers[customers["status"].isin(["Active", "Upgraded"])]["monthly_price"].sum()
churn_rate = (customers["status"] == "Churned").mean() * 100
net_margin = df["monthly_price"].sum() - df["ai_api_cost"].sum()  # tiền gói - chi phí API
avg_tickets = df["support_tickets_opened"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("MRR", f"${mrr:,.0f}")
k2.metric("Churn Rate", f"{churn_rate:.1f}%")
k3.metric("Net AI Profit Margin", f"${net_margin:,.0f}")
k4.metric("Avg Support Tickets", f"{avg_tickets:.2f}")

st.divider()

# ----- Biểu đồ 1: MRR và Churn theo tháng -----
mrr_by_month = df[is_paying].groupby("month")["monthly_price"].sum()
churn_by_month = df.assign(c=(df["status"] == "Churned")).groupby("month")["c"].mean() * 100
monthly = pd.DataFrame({"MRR": mrr_by_month, "Churn Rate (%)": churn_by_month}).fillna(0)
monthly = monthly.reset_index()

col1, col2 = st.columns(2)
with col1:
    fig1 = px.line(monthly, x="month", y="MRR", markers=True,
                   title="MRR theo tháng: doanh thu có đang tăng?")
    fig1.update_traces(line_color="#2563eb")
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    fig1b = px.line(monthly, x="month", y="Churn Rate (%)", markers=True,
                    title="Churn Rate theo tháng: khách rời bỏ có tăng?")
    fig1b.update_traces(line_color="#dc2626")
    st.plotly_chart(fig1b, use_container_width=True)

# ----- Biểu đồ 2: Token vs Chi phí AI -----
col3, col4 = st.columns(2)
with col3:
    fig2 = px.scatter(df, x="tokens_consumed", y="ai_api_cost", color="plan_name",
                      title="Dùng càng nhiều token, chi phí AI càng cao (theo gói)",
                      labels={"tokens_consumed": "Tokens tiêu thụ",
                              "ai_api_cost": "Chi phí API ($)"})
    st.plotly_chart(fig2, use_container_width=True)

# ----- Biểu đồ 3: Lý do churn -----
with col4:
    churned = customers[customers["status"] == "Churned"]
    if churned.empty:
        st.info("Không có khách Churned trong bộ lọc này.")
    else:
        reasons = churned["churn_reason"].fillna("Không rõ").value_counts().reset_index()
        reasons.columns = ["churn_reason", "so_khach"]
        fig3 = px.bar(reasons, x="so_khach", y="churn_reason", orientation="h",
                      title="Lý do khách hủy dịch vụ phổ biến nhất",
                      color_discrete_sequence=["#f97316"])
        fig3.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig3, use_container_width=True)

# ----- Biểu đồ 4: Heatmap quy mô x trạng thái -----
table = pd.crosstab(customers["company_size"], customers["status"])
fig4 = px.imshow(table, text_auto=True, color_continuous_scale="Reds",
                 title="Quy mô công ty nào có nhiều khách Churned nhất?")
st.plotly_chart(fig4, use_container_width=True)

st.caption("Xem danh sách khách nguy cơ cao, xuất báo cáo và SQL ở trang 'Chi tiet khach hang'.")