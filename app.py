import streamlit as st
import pandas as pd
import requests
import openai
import re

# ---- API Keys (directly in code) ----
MONDAY_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjYzMTAxNjgyNywiYWFpIjoxMSwidWlkIjoxMDA4MTM2MTUsImlhZCI6IjIwMjYtMDMtMTBUMDY6NDE6MDUuMDAwWiIsInBlciI6Im1lOndyaXRlIiwiYWN0aWQiOjM0MTUzNTYyLCJyZ24iOiJhcHNlMiJ9.m3eK4DTC8TaPlJJk2dNWQ6aNlnbsCJYctuFGlWxXbmI"
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

# ---- Board IDs ----
DEALS_BOARD_ID = "5027109784"
WORK_BOARD_ID = "5027110288"
URL = "https://api.monday.com/v2"

# ---- Functions ----
def get_board_data(board_id):
    query = """
    query ($board_id: [ID!]!) {
      boards(ids: $board_id) {
        items_page {
          items {
            name
            column_values {
              text
              column {
                title
              }
            }
          }
        }
      }
    }
    """
    variables = {"board_id": board_id}
    response = requests.post(
        URL,
        json={"query": query, "variables": variables},
        headers={"Authorization": MONDAY_API_KEY},
    )

    try:
        data = response.json()
    except Exception as e:
        st.error(f"Failed to parse JSON from Monday.com: {e}")
        return pd.DataFrame()

    if not data or "data" not in data or not data["data"].get("boards"):
        st.error("No data returned from Monday.com. Check API key and Board ID.")
        return pd.DataFrame()

    rows = []
    for item in data["data"]["boards"][0]["items_page"].get("items", []):
        row = {"Name": item.get("name", "")}
        for col in item.get("column_values", []):
            title = col.get("column", {}).get("title", "")
            row[title] = col.get("text", "")
        rows.append(row)
    return pd.DataFrame(rows)

# ---- Local AI-like answers for common queries ----
def local_answer(df, question):
    question_lower = question.lower()

    # Count by status
    match = re.search(r"how many deals are (.*)", question_lower)
    if match:
        status = match.group(1).strip().title()  # capitalize to match column values
        if 'Status' in df.columns:
            count = df['Status'].value_counts().get(status, 0)
            return f"Number of deals with status '{status}': {count}"
        else:
            return "No 'Status' column in the Deals data."

    # Sum of a numeric column
    match_sum = re.search(r"total (.*) in deals", question_lower)
    if match_sum:
        col = match_sum.group(1).strip().title()
        if col in df.columns:
            try:
                total = pd.to_numeric(df[col], errors='coerce').sum()
                return f"Total {col} in Deals: {total}"
            except:
                return f"Cannot calculate total for column '{col}'."
        else:
            return f"Column '{col}' not found in Deals data."

    # If no local rule matched, return None
    return None

# ---- Fallback to OpenAI ----
def get_ai_answer(deals_df, work_df, question):
    deals_str = deals_df.head(10).to_string()  # reduced to 10 rows
    work_str = work_df.head(10).to_string()
    prompt = f"""
You are a business intelligence assistant.
I have two datasets:

DEALS:
{deals_str}

WORK ORDERS:
{work_str}

Answer the following question based on the data above.
If data is missing, mention it.

Question: {question}
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content
    except openai.error.RateLimitError:
        return "OpenAI quota exceeded. Unable to answer complex questions at the moment."

# ---- Streamlit UI ----
st.title("Skylark BI Agent (Chatbot)")
st.write("Ask questions about your Monday.com data!")

# Initialize session state
if "deals" not in st.session_state:
    st.session_state.deals = pd.DataFrame()
if "work_orders" not in st.session_state:
    st.session_state.work_orders = pd.DataFrame()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Load data automatically if not loaded
if st.session_state.deals.empty or st.session_state.work_orders.empty:
    with st.spinner("Loading Monday.com data..."):
        st.session_state.deals = get_board_data(DEALS_BOARD_ID)
        st.session_state.work_orders = get_board_data(WORK_BOARD_ID)
    st.success("Data loaded successfully!")

# Display top 10 rows
st.subheader("Deals Data (Top 10 rows)")
st.dataframe(st.session_state.deals.head(10))
st.subheader("Work Orders Data (Top 10 rows)")
st.dataframe(st.session_state.work_orders.head(10))

# Chat input
question = st.text_input("Ask a business question:")

if question:
    with st.spinner("Analyzing your question..."):
        # Try local answer first
        answer = local_answer(st.session_state.deals, question)
        if not answer:  # fallback to OpenAI
            answer = get_ai_answer(st.session_state.deals, st.session_state.work_orders, question)
        # Save to chat history
        st.session_state.chat_history.append({"question": question, "answer": answer})

# Display chat history (latest on top)
for chat in st.session_state.chat_history[::-1]:
    st.markdown(f"**You:** {chat['question']}")
    st.markdown(f"**BI Agent:** {chat['answer']}")
    st.markdown("---")

