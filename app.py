
import streamlit as st
import pandas as pd
import requests
import openai

MONDAY_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjYzMTAxNjgyNywiYWFpIjoxMSwidWlkIjoxMDA4MTM2MTUsImlhZCI6IjIwMjYtMDMtMTBUMDY6NDE6MDUuMDAwWiIsInBlciI6Im1lOndyaXRlIiwiYWN0aWQiOjM0MTUzNTYyLCJyZ24iOiJhcHNlMiJ9.m3eK4DTC8TaPlJJk2dNWQ6aNlnbsCJYctuFGlWxXbmI"
DEALS_BOARD_ID = "5027109784"
WORK_BOARD_ID = "5027110288"
URL = "https://api.monday.com/v2"

OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

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

    # Debug print if needed
    st.write("Raw Monday.com API response:", data)

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


st.title(" Skylark BI Agent")
st.write("This agent reads data from Monday.com and answers founder-level questions.")

# Load data button
if st.button("Load Monday.com Data"):
    with st.spinner("Loading Deals and Work Orders data..."):
        deals = get_board_data(DEALS_BOARD_ID)
        work_orders = get_board_data(WORK_BOARD_ID)
    st.success("Data loaded successfully!")

    if not deals.empty:
        st.subheader(" Deals Data (Top 50 rows)")
        st.dataframe(deals.head(50))
    else:
        st.warning("Deals data is empty.")

    if not work_orders.empty:
        st.subheader(" Work Orders Data (Top 50 rows)")
        st.dataframe(work_orders.head(50))
    else:
        st.warning("Work Orders data is empty.")

# Ask a question
question = st.text_input("Ask a business question (e.g., How is our energy sector pipeline this quarter?)")

if question:
    if 'deals' not in globals() or 'work_orders' not in globals() or deals.empty or work_orders.empty:
        st.warning("Please load Monday.com data first by clicking the button above.")
    else:
        with st.spinner("Analyzing data and generating answer..."):
            # Convert top 50 rows of each dataframe to string
            deals_str = deals.head(50).to_string()
            work_str = work_orders.head(50).to_string()

            # Prepare prompt for GPT
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
            # Get GPT response
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            answer = response.choices[0].message.content

        st.subheader("Answer")
        st.write(answer)