import requests
import pandas as pd
import streamlit as st
import snowflake.connector

SEMANTIC_VIEW = "ENPAL_DB.ANALYTICS.ENPAL_OPERATIONS_SEMANTIC_VIEW"

st.set_page_config(
    page_title="Enpal One+ Ops Copilot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- CLEAN UI ----------
st.markdown("""
<style>
.stApp {
    background: #F6F8FB;
}

.block-container {
    max-width: 1180px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

section[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #E5EAF0;
}

h1, h2, h3 {
    color: #082B4C !important;
}

.small-muted {
    color: #65758B !important;
    font-size: 0.95rem;
}

.answer-card {
    background: #FFFFFF;
    border: 1px solid #E5EAF0;
    border-left: 4px solid #FFC400;
    border-radius: 10px;
    padding: 1.1rem 1.25rem;
    margin-bottom: 1rem;
    color: #082B4C !important;
    line-height: 1.6;
}

.answer-card * {
    color: #082B4C !important;
}

[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E5EAF0;
    border-radius: 10px;
    padding: 1rem;
}

[data-testid="metric-container"] * {
    color: #082B4C !important;
}

.stButton > button {
    border-radius: 8px;
    font-weight: 600;
}

.stDownloadButton > button {
    border-radius: 8px;
}

[data-testid="stDataFrame"] {
    border-radius: 10px;
    border: 1px solid #E5EAF0;
}

div[data-testid="stExpander"] {
    border-radius: 10px;
    border: 1px solid #E5EAF0;
    background: #FFFFFF;
}

#MainMenu, footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)


EXAMPLE_QUESTIONS = [
    "Why are Berlin installations delayed?",
    "Why are Hamburg installations delayed?",
    "Why are Munich installations delayed?",
    "What is the main delay reason in Munich?",
    "What is the main delay reason in Berlin?",
    "Which city has the highest number of delayed installations?",
    "Show delayed installations caused by missing documents.",
    "Show delayed installations caused by customer unavailable.",
    "Show delayed installations caused by shipment delay.",
    "Which delays are older than 7 days?",
    "Which city should operations prioritize this week?",
    "Show high-risk installations by city.",
    "Which delayed installations also have offline smart meters?",
    "Which operational issue affects the most customers?",
    "What are the top three bottlenecks across Germany?",
    "Which issue should operations fix first?",
    "Generate a management report for today's operations.",
    "Give me an operational summary for Berlin.",
    "Give me an operational summary for Hamburg.",
    "Give me an operational summary for Munich.",
    "Which shipments are delayed?",
    "How many battery shipments are currently delayed?",
    "Show delayed shipments by city.",
    "Which component has the most delayed shipments?",
    "Are shipment delays blocking installations?",
    "How many offline smart meters do we have?",
    "Which city has the highest number of offline smart meters?",
    "Investigate smart meter failures in Hamburg.",
    "Are smart meter failures causing delays?",
    "Show customers affected by offline smart meters.",
    "Which installer teams are overloaded?",
    "Show teams operating above capacity.",
    "Which city has the highest installer workload?",
    "Which installer teams have the biggest capacity gap?",
    "How many batteries are waiting for installation?",
    "Show battery inventory by city.",
    "Which city has the most pending batteries?",
    "How many wallboxes are pending installation?",
    "Show wallbox installation backlog.",
    "Which customers are waiting for EV charger installation?",
]


@st.cache_resource
def get_conn():
    return snowflake.connector.connect(
        user=st.secrets["SNOWFLAKE_USER"],
        password=st.secrets["SNOWFLAKE_PASSWORD"],
        account=st.secrets["SNOWFLAKE_ACCOUNT"],
        warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
        database=st.secrets["SNOWFLAKE_DATABASE"],
        schema=st.secrets["SNOWFLAKE_SCHEMA"],
        role=st.secrets.get("SNOWFLAKE_ROLE"),
    )


def get_cortex_url():
    account = st.secrets["SNOWFLAKE_ACCOUNT"]
    return f"https://{account}.snowflakecomputing.com/api/v2/cortex/analyst/message"


def test_snowflake_connection():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            CURRENT_ACCOUNT(),
            CURRENT_REGION(),
            CURRENT_ROLE(),
            CURRENT_DATABASE(),
            CURRENT_SCHEMA()
    """)
    return cur.fetchone()


def run_sql(sql):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetch_pandas_all()


def ask_cortex_analyst(question):
    conn = get_conn()
    token = conn.rest.token

    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question}
                ],
            }
        ],
        "semantic_view": SEMANTIC_VIEW,
        "stream": False,
    }

    headers = {
        "Authorization": f'Snowflake Token="{token}"',
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    cortex_url = get_cortex_url()

    try:
        response = requests.post(
            cortex_url,
            headers=headers,
            json=body,
            timeout=60,
        )
    except Exception as e:
        return None, None, f"""
REQUEST EXCEPTION:
{type(e).__name__}

CORTEX URL:
{cortex_url}

ERROR:
{str(e)}
"""

    if response.status_code != 200:
        return None, None, f"""
STATUS CODE:
{response.status_code}

CORTEX URL:
{cortex_url}

RESPONSE TEXT:
{response.text}
"""

    try:
        data = response.json()
    except Exception as e:
        return None, None, f"""
JSON PARSE ERROR:
{type(e).__name__}

RESPONSE TEXT:
{response.text}
"""

    content = data.get("message", {}).get("content", [])

    answer_parts = []
    sql_statement = None
    suggestions = []

    for item in content:
        if item.get("type") == "text":
            answer_parts.append(item.get("text", ""))
        elif item.get("type") == "sql":
            sql_statement = item.get("statement")
        elif item.get("type") == "suggestion":
            if "suggestions" in item:
                suggestions.extend(item.get("suggestions", []))
            elif "suggestion" in item:
                suggestions.append(item.get("suggestion"))

    return "\n".join(answer_parts), sql_statement, suggestions


def render_chart(df):
    if df.empty:
        st.info("No data available for chart.")
        return

    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if len(numeric_cols) == 0:
        st.info("No numeric columns available for chart.")
        return

    category_cols = [col for col in df.columns if col not in numeric_cols]

    chart_type = st.selectbox(
        "Select chart type",
        ["Bar chart", "Line chart", "Area chart"],
        index=1
    )

    y_col = st.selectbox(
        "Select value column",
        numeric_cols,
        index=0
    )

    if category_cols:
        x_col = st.selectbox(
            "Select label column",
            category_cols,
            index=0
        )
        chart_df = df[[x_col, y_col]].set_index(x_col)
    else:
        chart_df = df[[y_col]]

    if chart_type == "Bar chart":
        st.bar_chart(chart_df)

    elif chart_type == "Line chart":
        st.line_chart(chart_df)

    elif chart_type == "Area chart":
        st.area_chart(chart_df)

# ---------- SESSION ----------
if "question" not in st.session_state:
    st.session_state.question = "Which city should operations prioritize this week?"


# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("## Enpal.")
    st.caption("One+ Ops Copilot")

    st.divider()

    st.subheader("Connection")

    if st.button("Test Snowflake", use_container_width=True):
        try:
            result = test_snowflake_connection()
            st.success("Connected")
            st.write(result)
        except Exception as e:
            st.error("Connection failed")
            st.code(str(e))

    st.divider()

    st.subheader("Example Questions")

    selected_question = st.selectbox(
        "Choose an example",
        EXAMPLE_QUESTIONS,
        index=EXAMPLE_QUESTIONS.index("Which city should operations prioritize this week?"),
        label_visibility="collapsed",
    )

    if st.button("Use Example", use_container_width=True):
        st.session_state.question = selected_question

    st.divider()

    with st.expander("Debug"):
        st.caption("Cortex URL")
        st.code(get_cortex_url())


# ---------- MAIN ----------
st.title("⚡ Enpal One+ Operations Copilot")
st.markdown(
    '<div class="small-muted">AI-powered operations intelligence using Snowflake Cortex Analyst.</div>',
    unsafe_allow_html=True,
)

st.divider()

col_input, col_button = st.columns([5, 1])

with col_input:
    question = st.text_input(
        "Ask Cortex Analyst",
        key="question",
        placeholder="Ask about delays, shipments, smart meters, installer capacity..."
    )

with col_button:
    st.write("")
    st.write("")
    run_clicked = st.button("Run", type="primary", use_container_width=True)


if run_clicked:
    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()

    with st.spinner("Calling Cortex Analyst..."):
        answer, sql, error_or_suggestions = ask_cortex_analyst(question)

    if answer is None:
        st.error("Cortex Analyst API failed")

        with st.expander("Error details", expanded=True):
            st.code(str(error_or_suggestions))

        st.stop()

    st.markdown("### Answer")

    if answer:
        st.markdown(
            f'<div class="answer-card">{answer}</div>',
            unsafe_allow_html=True
        )

    if not sql:
        if error_or_suggestions:
            st.info("Cortex Analyst returned suggestions.")
            st.write(error_or_suggestions)
        else:
            st.info("No SQL was generated.")
        st.stop()

    try:
        df = run_sql(sql)
    except Exception as e:
        st.error("SQL execution failed")
        with st.expander("Generated SQL", expanded=True):
            st.code(sql, language="sql")
        st.code(str(e))
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows returned", len(df))
    col2.metric("Columns returned", len(df.columns))
    col3.metric("Status", "Success")

    with st.expander("Generated SQL", expanded=False):
        st.code(sql, language="sql")

    st.subheader("Results")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False)

    st.download_button(
        "Download CSV",
        csv,
        file_name="enpal_ops_result.csv",
        mime="text/csv",
    )

    st.subheader("Chart")
    render_chart(df)