import requests
import pandas as pd
import streamlit as st
import snowflake.connector

SEMANTIC_VIEW = "ENPAL_DB.ANALYTICS.ENPAL_OPERATIONS_SEMANTIC_VIEW"

st.set_page_config(page_title="Enpal Cortex Analyst App", page_icon="⚡", layout="wide")

st.title("⚡ Enpal One+ Cortex Analyst")
st.caption("Local Streamlit app → Cortex Analyst REST API → Semantic View → Snowflake")


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

    try:
        token = conn.rest.token
    except Exception as e:
        return None, None, f"""
TOKEN ERROR:
{type(e).__name__}

ERROR:
{str(e)}
"""

    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": question
                    }
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
        "X-Snowflake-Authorization-Token-Type": "Snowflake",
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


with st.sidebar:
    st.header("Connection Test")

    if st.button("Test Snowflake"):
        try:
            result = test_snowflake_connection()
            st.success("Snowflake connection successful")
            st.write(result)
        except Exception as e:
            st.error("Snowflake connection failed")
            st.code(str(e))

    st.markdown("---")
    st.caption("Debug")
    try:
        st.write("Cortex URL:")
        st.code(get_cortex_url())
    except Exception:
        pass


question = st.text_input(
    "Ask Cortex Analyst",
    value="Which city should operations prioritize based on delayed installations, shipment issues, and installer overload?",
)


if st.button("Ask"):
    with st.spinner("Calling Cortex Analyst..."):
        answer, sql, error_or_suggestions = ask_cortex_analyst(question)

    if answer is None:
        st.error("Cortex Analyst API failed")
        st.markdown("### Debug error")
        st.write(error_or_suggestions)
        st.markdown("### Raw error")
        st.code(str(error_or_suggestions))

    else:
        st.subheader("🤖 Cortex Analyst Answer")
        st.write(answer)

        if sql:
            st.subheader("Generated SQL")
            st.code(sql, language="sql")

            try:
                df = run_sql(sql)

                st.subheader("Snowflake Result")
                st.dataframe(df, use_container_width=True)

                if not df.empty and len(df.columns) >= 2:
                    numeric_cols = df.select_dtypes(include="number").columns

                    if len(numeric_cols) > 0:
                        st.bar_chart(df.set_index(df.columns[0])[numeric_cols[0]])

            except Exception as e:
                st.error("SQL execution failed")
                st.code(str(e))

        elif error_or_suggestions:
            st.subheader("Suggestions")
            st.write(error_or_suggestions)