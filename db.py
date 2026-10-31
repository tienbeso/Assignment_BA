import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

DB_USER = "root"
DB_PASS = ""
DB_HOST = "localhost"
DB_NAME = "saas_ai_db"


@st.cache_resource
def get_engine():
    return create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")


@st.cache_data
def run_query(sql, params):
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def check_connection():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        st.error(f"Không kết nối được MySQL. Hãy bật MySQL trong XAMPP.\nChi tiết: {e}")
        st.stop()


def sidebar_filters():
    st.sidebar.title("Bộ lọc")

    limits = run_query("SELECT MIN(usage_month) AS d1, MAX(usage_month) AS d2 FROM UsageLogs", {})
    if limits["d1"][0] is None:
        st.warning("Bảng UsageLogs đang trống, hãy thêm dữ liệu trước.")
        st.stop()

    picked = st.sidebar.date_input(
        "Khoảng thời gian",
        value=(limits["d1"][0], limits["d2"][0]),
        min_value=limits["d1"][0],
        max_value=limits["d2"][0],
        key="date_range",
    )
    if len(picked) != 2:
        st.info("Hãy chọn đủ ngày bắt đầu và ngày kết thúc.")
        st.stop()

    sizes = st.sidebar.multiselect(
        "Quy mô công ty",
        ["Startup", "SMB", "Enterprise"],
        default=["Startup", "SMB", "Enterprise"],
        key="sizes",
    )
    status = st.sidebar.selectbox(
        "Trạng thái", ["Tất cả", "Active", "Churned", "Upgraded"], key="status"
    )

    if not sizes:
        st.warning("Hãy chọn ít nhất 1 quy mô công ty.")
        st.stop()

    return picked[0], picked[1], sizes, status


def build_where(start, end, sizes, status):
    where = " WHERE 1=1 AND u.usage_month BETWEEN :start AND :end"
    params = {"start": start, "end": end}

    names = []
    for i, s in enumerate(sizes):
        params[f"size{i}"] = s
        names.append(f":size{i}")
    where += f" AND c.company_size IN ({', '.join(names)})"

    if status != "Tất cả":
        where += " AND s.status = :status"
        params["status"] = status
    return where, params


JOINS = """
FROM UsageLogs u
JOIN Customers c     ON u.customer_id = c.customer_id
JOIN Plans p         ON c.plan_id = p.plan_id
JOIN Subscriptions s ON c.customer_id = s.customer_id
"""


def sql_main(where):
    return f"""
SELECT c.customer_id, c.customer_name, c.company_size, p.plan_name,
       p.monthly_price, p.ai_token_limit, u.usage_month,
       u.tokens_consumed, u.ai_api_cost, u.support_tickets_opened,
       s.status, s.churn_reason
{JOINS}{where}
"""


def sql_risk(where):
    return f"""
SELECT c.customer_id, c.customer_name, c.company_size, p.plan_name, s.status,
       p.ai_token_limit,
       MAX(u.tokens_consumed)        AS max_tokens_in_month,
       MAX(u.support_tickets_opened) AS max_tickets_in_month,
       SUM(u.ai_api_cost)            AS total_ai_cost
{JOINS}{where}
GROUP BY c.customer_id, c.customer_name, c.company_size, p.plan_name,
         s.status, p.ai_token_limit
HAVING MAX(u.tokens_consumed) > p.ai_token_limit
    OR MAX(u.support_tickets_opened) > 3
"""