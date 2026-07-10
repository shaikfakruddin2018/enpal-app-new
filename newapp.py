import re
import time

import pandas as pd
import plotly.express as px
import requests
import snowflake.connector
import streamlit as st
from openai import OpenAI

SEMANTIC_VIEW = "ENPAL_DB.ANALYTICS.ENPAL_OPERATIONS_SEMANTIC_VIEW"

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(
    page_title="Enpal One+ Operations Copilot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS: Claude UI merged into live app ────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #0f1117; color: #e8eaf0; }
.block-container { max-width: 1240px; padding-top: 2rem; padding-bottom: 3rem; }

[data-testid="stSidebar"], section[data-testid="stSidebar"] {
    background-color: #161b27 !important;
    border-right: 1px solid #1e2535;
}
[data-testid="stSidebar"] * { color: #c8cdd8 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stToggle label {
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #7a8299 !important;
}

h1 { font-weight: 700; letter-spacing: -0.02em; color: #f0f2f8 !important; }
h2 { font-weight: 600; color: #d8dbe8 !important; }
h3 { font-weight: 500; color: #c0c4d4 !important; }

.small-muted {
    font-size: 1rem;
    color: #6b7a9a !important;
    margin-top: -8px;
    margin-bottom: 28px;
}

.copilot-card {
    background: #161b27;
    border: 1px solid #1e2a40;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 18px;
}
.copilot-card-accent {
    background: linear-gradient(135deg, #0d1f3c 0%, #142240 100%);
    border: 1px solid #1d3560;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 18px;
}
.answer-card {
    background: linear-gradient(135deg, #0d1f3c 0%, #142240 100%);
    border: 1px solid #1d3560;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 18px;
    color: #c8d0e8 !important;
    line-height: 1.65;
}
.answer-card * { color: #c8d0e8 !important; }

.kpi-card {
    background: #161b27;
    border: 1px solid #1e2a40;
    border-radius: 10px;
    padding: 18px 20px;
    text-align: center;
}
.kpi-value {
    font-size: 1.65rem;
    font-weight: 700;
    color: #4d9fff;
    line-height: 1.1;
    letter-spacing: -0.02em;
}
.kpi-label {
    font-size: 0.72rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6b7490;
    margin-top: 6px;
}

.pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.pill-green  { background: #0d2e1a; color: #3ddc84; border: 1px solid #1a5c35; }
.pill-blue   { background: #0d1f3c; color: #4d9fff; border: 1px solid #1d3a6e; }
.pill-orange { background: #2e1a0d; color: #f5a623; border: 1px solid #5c3a1a; }
.pill-red    { background: #2e0d0d; color: #ff5f5f; border: 1px solid #6e1d1d; }

.conn-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #3ddc84;
    box-shadow: 0 0 6px #3ddc84;
    margin-right: 7px;
    vertical-align: middle;
}
.arch-flow {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    font-size: 0.72rem;
    color: #6b7490;
    font-family: 'JetBrains Mono', monospace;
    margin-top: 12px;
}
.arch-node {
    background: #0f1624;
    border: 1px solid #1e2a40;
    border-radius: 6px;
    padding: 4px 9px;
    color: #94a3d0;
    font-size: 0.68rem;
    white-space: nowrap;
}
.arch-arrow { color: #2d3a5e; font-size: 0.85rem; }

.sql-block, .debug-block {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    line-height: 1.6;
    color: #a8c0f0;
    background: #0a0f1a;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 16px 20px;
    overflow-x: auto;
    white-space: pre-wrap;
}
.debug-block { font-size: 0.73rem; color: #7a8fba; background: #090d16; border-color: #141e30; }
.section-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #4d9fff;
    margin-bottom: 10px;
}
.subtle-divider { border: none; border-top: 1px solid #1e2535; margin: 22px 0; }

.stButton > button, .stDownloadButton > button {
    background: linear-gradient(135deg, #1a4fa0 0%, #1060c0 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 2px 12px rgba(26, 79, 160, 0.4) !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: linear-gradient(135deg, #1e5ab8 0%, #1470d8 100%) !important;
    box-shadow: 0 4px 18px rgba(26, 79, 160, 0.6) !important;
}
.stTextInput input, .stTextArea textarea {
    background: #0f1624 !important;
    border: 1px solid #1e2a40 !important;
    border-radius: 8px !important;
    color: #d8dbe8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #2d5fa0 !important;
    box-shadow: 0 0 0 2px rgba(45, 95, 160, 0.25) !important;
}
[data-testid="stExpander"], div[data-testid="stExpander"] {
    background: #0f1624 !important;
    border: 1px solid #1e2a40 !important;
    border-radius: 8px !important;
}
[data-testid="stDataFrame"] { border-radius: 8px !important; overflow: hidden; border: 1px solid #1e2a40; }
.stSelectbox label, .stSlider label, .stTextInput label, .stTextArea label {
    font-size: 0.78rem;
    font-weight: 500;
    color: #8892ad !important;
}
#MainMenu, footer { visibility: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

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

if "question" not in st.session_state:
    st.session_state.question = "Which city should operations prioritize this week?"
if "last_result" not in st.session_state:
    st.session_state.last_result = None


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
    cur.execute(
        """
        SELECT
            CURRENT_ACCOUNT(),
            CURRENT_REGION(),
            CURRENT_ROLE(),
            CURRENT_DATABASE(),
            CURRENT_SCHEMA()
        """
    )
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
                "content": [{"type": "text", "text": question}],
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
        response = requests.post(cortex_url, headers=headers, json=body, timeout=60)
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


def generate_ai_summary(question, answer, df, model_name):
    if df.empty:
        return "No records were returned."

    data_preview = df.head(20).to_string(index=False)
    prompt = f"""
You are a senior operations analyst at Enpal.

User question:
{question}

Cortex Analyst interpretation:
{answer}

Snowflake results:
{data_preview}

Write a concise executive summary.

Return exactly:

## Key Finding
What happened?

## Operational Impact
Why does it matter?

## Recommended Action
What should operations do next?

Keep it manager-friendly.
Maximum 150 words.
Do not mention SQL.
Do not mention dataframe.
"""

    response = client.responses.create(model=model_name, input=prompt)
    return response.output_text


def section_label(text: str) -> str:
    return f'<div class="section-label">{text}</div>'


def render_kpis(row_count: int, col_count: int, status: str, exec_ms: int | None, model_name: str):
    cols = st.columns(4)
    items = [
        (str(row_count), "Rows Returned"),
        (str(col_count), "Columns"),
        (status, "Status"),
        (f"{exec_ms} ms" if exec_ms is not None else model_name, "Execution Time" if exec_ms is not None else "AI Model"),
    ]
    for col, (val, label) in zip(cols, items):
        with col:
            color = "#3ddc84" if str(val).lower() == "success" else "#4d9fff"
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-value" style="color:{color}">{val}</div>
                    <div class="kpi-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_sql(sql: str):
    html_sql = sql.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    keywords = [
        "SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "LIMIT", "JOIN", "LEFT", "RIGHT",
        "INNER", "OUTER", "ON", "AND", "OR", "NOT IN", "IN", "AS", "COUNT", "SUM", "AVG", "MAX",
        "MIN", "ROUND", "OVER", "DATE_TRUNC", "DATEADD", "CURRENT_DATE", "CASE", "WHEN", "THEN", "END",
    ]
    for kw in keywords:
        html_sql = re.sub(rf"\b{re.escape(kw)}\b", f'<span style="color:#7ec8f8;font-weight:600;">{kw}</span>', html_sql)
    html_sql = re.sub(r"'([^']*)'", r'<span style="color:#a8e6a3">\'\1\'</span>', html_sql)
    html_sql = re.sub(r"\b(\d+\.?\d*)\b", r'<span style="color:#f5a623">\1</span>', html_sql)
    st.markdown(f'<div class="sql-block">{html_sql}</div>', unsafe_allow_html=True)


def render_chart(df: pd.DataFrame):
    if df.empty:
        st.info("No data available for chart.")
        return

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        st.info("No numeric columns available for chart.")
        return

    all_cols = df.columns.tolist()
    category_cols = [col for col in all_cols if col not in numeric_cols]

    c1, c2, c3 = st.columns([1.4, 2, 2])
    with c1:
        chart_type = st.selectbox("Chart type", ["Bar", "Line", "Area"], key="chart_type")
    with c2:
        label_options = category_cols or all_cols
        label_col = st.selectbox("Label column (X)", label_options, index=0, key="chart_label")
    with c3:
        val_col = st.selectbox("Value column (Y)", numeric_cols, index=0, key="chart_value")

    chart_df = df[[label_col, val_col]].dropna()
    plot_kwargs = dict(
        data_frame=chart_df,
        x=label_col,
        y=val_col,
        color_discrete_sequence=["#4d9fff"],
        template="plotly_dark",
    )

    if chart_type == "Bar":
        fig = px.bar(**plot_kwargs)
        fig.update_traces(marker_color="#4d9fff", opacity=0.85)
    elif chart_type == "Line":
        fig = px.line(**plot_kwargs)
        fig.update_traces(line=dict(color="#4d9fff", width=2.5))
    else:
        fig = px.area(**plot_kwargs)
        fig.update_traces(line=dict(color="#4d9fff"), fillcolor="rgba(77,159,255,0.18)")

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10,15,26,0.9)",
        font=dict(family="Inter", color="#9aa3b8"),
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(gridcolor="#1a2540", tickfont=dict(size=11)),
        yaxis=dict(gridcolor="#1a2540", tickfont=dict(size=11)),
        hoverlabel=dict(bgcolor="#161b27", bordercolor="#1e2a40", font_size=12),
        height=340,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ Enpal One+")
    st.markdown("**Operations Copilot**")
    st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)

    st.markdown("**Connection**")
    st.markdown(
        '<span class="conn-dot"></span><span style="font-size:0.8rem;font-weight:500;">Snowflake · Configured</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.7rem;color:#4a5570;margin-top:3px;padding-left:17px;">'
        'Cortex Analyst · Semantic View</div>',
        unsafe_allow_html=True,
    )

    if st.button("Test Snowflake", use_container_width=True):
        try:
            result = test_snowflake_connection()
            st.success("Connected")
            st.code(str(result))
        except Exception as e:
            st.error("Connection failed")
            st.code(str(e))

    st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)
    st.markdown("**Example Questions**")
    selected_question = st.selectbox(
        "Select a sample question",
        EXAMPLE_QUESTIONS,
        index=EXAMPLE_QUESTIONS.index("Which city should operations prioritize this week?"),
        label_visibility="collapsed",
        key="example_select",
    )
    if st.button("Use Example →", use_container_width=True):
        st.session_state.question = selected_question
        st.rerun()

    st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)
    st.markdown("**AI Model**")
    selected_model = st.selectbox(
        "Model selector",
        ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o"],
        index=0,
        label_visibility="collapsed",
        key="model_select",
    )

    st.markdown("**Debug Mode**")
    debug_mode = st.toggle("Show debug trace", value=False, key="debug_toggle")

    st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)
    st.markdown("**Architecture**")
    st.markdown(
        """
        <div class="arch-flow">
            <div class="arch-node">Streamlit</div>
            <span class="arch-arrow">→</span>
            <div class="arch-node">Cortex Analyst</div>
            <span class="arch-arrow">→</span>
            <div class="arch-node">Semantic View</div>
            <span class="arch-arrow">→</span>
            <div class="arch-node">Snowflake</div>
            <span class="arch-arrow">→</span>
            <div class="arch-node">OpenAI Summary</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if debug_mode:
        st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)
        st.caption("Cortex URL")
        st.code(get_cortex_url())

    st.markdown('<br><div style="font-size:0.65rem;color:#3a4260;">Enpal Internal · Live backend</div>', unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown("# ⚡ Enpal One+ Operations Copilot")
st.markdown(
    '<div class="small-muted">Natural language operations intelligence using Snowflake Cortex Analyst.</div>',
    unsafe_allow_html=True,
)

question = st.text_area(
    "Ask an operations question",
    key="question",
    placeholder="Ask about delays, shipments, smart meters, installer capacity...",
    height=90,
    label_visibility="collapsed",
)

btn_col, hint_col = st.columns([2, 8])
with btn_col:
    run_clicked = st.button("⚡ Run Analysis", type="primary", use_container_width=True)
with hint_col:
    st.markdown(
        '<div style="font-size:0.78rem;color:#4a5570;padding-top:12px;">'
        'Choose an example from the sidebar or enter your own operations query.</div>',
        unsafe_allow_html=True,
    )

if run_clicked:
    if not question.strip():
        st.warning("Please enter a question or choose an example from the sidebar.")
        st.stop()

    started = time.perf_counter()
    with st.spinner("Running analysis · querying Cortex Analyst…"):
        answer, sql, error_or_suggestions = ask_cortex_analyst(question)

    if answer is None:
        st.error("Cortex Analyst API failed")
        with st.expander("Error details", expanded=True):
            st.code(str(error_or_suggestions))
        st.stop()

    if not sql:
        st.info("No SQL was generated." if not error_or_suggestions else "Cortex Analyst returned suggestions.")
        if error_or_suggestions:
            st.write(error_or_suggestions)
        st.stop()

    try:
        df = run_sql(sql)
    except Exception as e:
        st.error("SQL execution failed")
        with st.expander("Generated SQL", expanded=True):
            st.code(sql, language="sql")
        st.code(str(e))
        st.stop()

    exec_ms = int((time.perf_counter() - started) * 1000)

    with st.spinner("Generating executive summary…"):
        try:
            ai_summary = generate_ai_summary(question, answer, df, selected_model)
        except Exception as e:
            ai_summary = f"AI summary generation failed: {str(e)}"

    st.session_state.last_result = {
        "question": question,
        "answer": answer,
        "sql": sql,
        "df": df,
        "ai_summary": ai_summary,
        "exec_ms": exec_ms,
        "model": selected_model,
    }


result = st.session_state.last_result

if result:
    df = result["df"]
    st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)

    st.markdown(section_label("🔍 Executive Summary"), unsafe_allow_html=True)
    st.markdown(
        f'<div class="answer-card">{result["ai_summary"].replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(section_label("📈 Query Metrics"), unsafe_allow_html=True)
    render_kpis(len(df), len(df.columns), "Success", result["exec_ms"], result["model"])

    st.markdown(section_label("🧠 Cortex Analyst Interpretation"), unsafe_allow_html=True)
    with st.expander("View Cortex interpretation", expanded=False):
        st.markdown(f'<div class="copilot-card">{result["answer"]}</div>', unsafe_allow_html=True)

    st.markdown(section_label("🗄️ Generated SQL"), unsafe_allow_html=True)
    with st.expander("View generated SQL query", expanded=False):
        render_sql(result["sql"])

    st.markdown(section_label("📋 Results Table"), unsafe_allow_html=True)
    st.dataframe(
        df,
        use_container_width=True,
        height=min(60 + 40 * max(len(df), 1), 380),
        hide_index=True,
    )

    csv = df.to_csv(index=False)
    st.download_button(
        "Download CSV",
        csv,
        file_name="enpal_ops_result.csv",
        mime="text/csv",
        use_container_width=False,
    )

    st.markdown('<div class="copilot-card">', unsafe_allow_html=True)
    st.markdown(section_label("📊 Interactive Chart"), unsafe_allow_html=True)
    render_chart(df)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("debug_toggle", False):
        st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)
        st.markdown(section_label("🛠️ Debug · Query Trace"), unsafe_allow_html=True)
        trace = f"""USER QUESTION    : {result['question']}
SELECTED MODEL   : {result['model']}
SEMANTIC VIEW    : {SEMANTIC_VIEW}
CORTEX URL       : {get_cortex_url()}
ROWS x COLUMNS   : {len(df)} x {len(df.columns)}
EXECUTION TIME   : {result['exec_ms']} ms
"""
        st.markdown(f'<div class="debug-block">{trace}</div>', unsafe_allow_html=True)
else:
    st.markdown(
        """
        <div class="copilot-card" style="text-align:center;padding:52px 28px;">
            <div style="font-size:2.4rem;margin-bottom:14px;">🔍</div>
            <div style="font-size:1rem;font-weight:600;color:#6b7a9a;margin-bottom:8px;">No analysis running</div>
            <div style="font-size:0.84rem;color:#4a5570;max-width:420px;margin:0 auto;line-height:1.6;">
                Select an example question from the sidebar or type your own operations query, then click <strong>Run Analysis</strong>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
