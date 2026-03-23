import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import streamlit as st
import streamlit.components.v1 as components
from src.graph import app
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
            st.subheader("Answer:")
            st.write(response)
        else:
            st.warning("Please enter a question.")

    st.divider()

    # --- Graph section ---
    st.subheader("Business Flow Graph: Order → Delivery → Billing → Payment")
    st.caption(
        "Visualizes real relationships between sales orders, deliveries, "
        "billing documents, and payments from the database."
    )

    if st.button("Show Business Flow Graph"):
        with st.spinner("Building graph from database..."):
            visualize_graph()

        if os.path.exists(GRAPH_HTML):
            with open(GRAPH_HTML, "r", encoding="utf-8") as f:
                html = f.read()
            components.html(html, height=600)
        else:
            st.error("graph.html could not be generated.")


if __name__ == "__main__":
    main()
