import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import streamlit as st
import streamlit.components.v1 as components
from src.graph import app, extract_order_id, get_key_insights
from src.graph_visualizer import visualize_graph, get_order_flow_steps

GRAPH_HTML = os.path.join(parent_dir, "graph.html")

st.set_page_config(page_title="FlowGraph AI", layout="wide")


def render_legend():
    st.markdown(
        """
        <div style="display:flex;gap:18px;margin-bottom:8px;font-size:13px;">
          <span><span style="background:#9B59B6;padding:2px 10px;border-radius:4px;">&nbsp;</span> Customer</span>
          <span><span style="background:#4A90D9;padding:2px 10px;border-radius:4px;">&nbsp;</span> Order</span>
          <span><span style="background:#F5A623;padding:2px 10px;border-radius:4px;">&nbsp;</span> Delivery</span>
          <span><span style="background:#7ED321;padding:2px 10px;border-radius:4px;">&nbsp;</span> Billing</span>
          <span><span style="background:#D0021B;padding:2px 10px;border-radius:4px;">&nbsp;</span> Payment</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_graph():
    if os.path.exists(GRAPH_HTML):
        with open(GRAPH_HTML, "r", encoding="utf-8") as f:
            html = f.read()
        components.html(html, height=600)
    else:
        st.error("Graph could not be generated.")


def main():
    
    with st.sidebar:
        st.title("Query History")
        if "history" not in st.session_state:
            st.session_state.history = []
        if st.session_state.history:
            for i, q in enumerate(reversed(st.session_state.history[-10:]), 1):
                st.markdown(f"{i}. {q}")
        else:
            st.caption("No queries yet.")

    st.title("FlowGraph AI")
    st.caption("Natural language queries over SAP Order-to-Cash data, powered by Groq + SQLite.")

    
    user_input = st.text_area("Ask a question about your data:", height=120,
                               placeholder="e.g. Which customers generate the highest revenue?")

    st.markdown("### 💡 Try these questions:")
    st.write("- Which customers generate highest revenue?")
    st.write("- Show incomplete flows")
    st.write("- Trace full flow for order 740506")

    col_run, col_trace, col_graph = st.columns([1, 1, 1])

    with col_run:
        run_clicked = st.button("Run Query", use_container_width=True)
    with col_trace:
        trace_clicked = st.button("Trace Order Flow", use_container_width=True)
    with col_graph:
        graph_clicked = st.button("Show Graph", use_container_width=True)

    story_mode = st.checkbox("🎬 Enable Step-by-Step Flow View")

    
    if run_clicked:
        if user_input:
            st.session_state.history.append(user_input)
            with st.spinner("Analyzing your query..."):
                response = app(user_input)
            if response["sql"]:
                st.subheader("Generated SQL")
                st.code(response["sql"], language="sql")
            st.subheader("Answer")
            if isinstance(response["result"], str) and response["result"].startswith("Query failed"):
                st.error("⚠️ Unable to process this query. Try rephrasing.")
            else:
                st.write(response["result"])
            if response.get("explanation"):
                st.info(response["explanation"])
            # Key insights (only for standard SQL results stored as raw_result)
            raw = response.get("raw_result")
            if raw:
                insights = get_key_insights(raw)
                if insights:
                    st.subheader("📊 Key Insights")
                    st.write(f"Total Records: {insights.get('total_records')}")
                    if insights.get("total_amount"):
                        st.write(f"Total Amount: {insights.get('total_amount')}")
                    if insights.get("top_customer"):
                        st.write(f"Top Entity: {insights.get('top_customer')}")
        else:
            st.warning("Please enter a question.")

    
    if trace_clicked:
        if user_input:
            order_id = extract_order_id(user_input)
            if order_id:
                with st.spinner(f"Tracing full flow for order {order_id}..."):
                    response = app(f"trace full flow for order {order_id}")
                st.subheader(f"O2C Flow — Order {order_id}")
                st.text(response["result"])
                st.divider()
                render_legend()
                with st.spinner("Building graph..."):
                    visualize_graph(target_order=order_id)
                render_graph()
            else:
                st.warning("No order ID found in your query. Include a 5+ digit order number.")
        else:
            st.warning("Enter a query with an order ID first.")

   
    if graph_clicked:
        order_id = extract_order_id(user_input) if user_input else None

        if story_mode and order_id:
            st.subheader(f"🎬 Step-by-Step Flow — Order {order_id}")
            steps = get_order_flow_steps(order_id)
            if steps:
                for i, step in enumerate(steps, 1):
                    st.markdown(f"### Step {i}: {step['step']}")
                    if "NOT FOUND" in step["label"]:
                        st.error(step["label"])
                    else:
                        st.success(step["label"])
                    st.divider()
            else:
                st.warning(f"No flow data found for order {order_id}.")
        else:
            label = f"Showing flow for Order {order_id}" if order_id else "Showing full business flow graph"
            highlight = [order_id] if order_id else []
            with st.spinner(label + "..."):
                visualize_graph(target_order=order_id, highlight_nodes=highlight)
            st.subheader("Business Flow Graph: Customer → Order → Delivery → Billing → Payment")
            render_legend()
            render_graph()

    
    with st.expander("Example queries"):
        st.markdown("""
- Which customers generate the highest revenue?
- Which products appear in the most billing documents?
- Show incomplete flows — orders with no delivery or payment
- Trace full flow for sales order 740506
- Which orders have been delivered but not billed?
- Top 10 orders by net amount
        """)


if __name__ == "__main__":
    main()
