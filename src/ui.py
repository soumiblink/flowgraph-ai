import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import streamlit as st
import streamlit.components.v1 as components
from src.graph import app, extract_order_id
from src.graph_visualizer import visualize_graph

GRAPH_HTML = os.path.join(parent_dir, "graph.html")


def main():
    st.title("FlowGraph AI")

    # --- Chat section ---
    user_input = st.text_area("Ask a question about your data:", height=150)

    if st.button("Run"):
        if user_input:
            with st.spinner("Thinking..."):
                response = app(user_input)
            st.subheader("Generated SQL:")
            st.code(response["sql"], language="sql")
            st.subheader("Answer:")
            if isinstance(response["result"], str) and response["result"].startswith("Query failed"):
                st.error(response["result"])
            else:
                st.write(response["result"])
            if response.get("explanation"):
                st.subheader("Explanation:")
                st.write(response["explanation"])
        else:
            st.warning("Please enter a question.")

    st.divider()

    # --- Graph section ---
    st.subheader("Business Flow Graph: Order → Delivery → Billing → Payment")
    st.caption(
        "Visualizes real relationships between sales orders, deliveries, "
        "billing documents, and payments. Enter a query above and click "
        "'Show Graph for this Query' to highlight a specific order flow."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Show Business Flow Graph"):
            with st.spinner("Building full graph from database..."):
                visualize_graph()
            _render_graph()

    with col2:
        if st.button("Show Graph for this Query"):
            order_id = extract_order_id(user_input) if user_input else None
            if order_id:
                st.info(f"Highlighting flow for Order {order_id}")
            else:
                st.info("No specific order found in query — showing full graph.")
            with st.spinner("Building graph..."):
                visualize_graph(target_order=order_id)
            _render_graph()


def _render_graph():
    if os.path.exists(GRAPH_HTML):
        with open(GRAPH_HTML, "r", encoding="utf-8") as f:
            html = f.read()
        components.html(html, height=600)
    else:
        st.error("graph.html could not be generated.")


if __name__ == "__main__":
    main()
