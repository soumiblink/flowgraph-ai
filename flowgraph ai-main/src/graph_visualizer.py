import os
import sqlite3
import networkx as nx
from pyvis.network import Network

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data.db")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "graph.html")

NODE_COLORS = {
    "order":    "#4A90D9",  # blue
    "delivery": "#F5A623",  # orange
    "billing":  "#7ED321",  # green
    "payment":  "#D0021B",  # red
}


def build_graph_from_db() -> nx.DiGraph:
    G = nx.DiGraph()

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Order → Delivery (via outbound_delivery_items.referenceSdDocument)
        cur.execute("""
            SELECT DISTINCT
                soh.salesOrder,
                odi.deliveryDocument
            FROM sales_order_headers soh
            JOIN outbound_delivery_items odi
                ON odi.referenceSdDocument = soh.salesOrder
            LIMIT 30
        """)
        order_delivery = cur.fetchall()

        # Delivery → Billing (via billing_document_items.referenceSdDocument)
        cur.execute("""
            SELECT DISTINCT
                odi.deliveryDocument,
                bdi.billingDocument
            FROM outbound_delivery_items odi
            JOIN billing_document_items bdi
                ON bdi.referenceSdDocument = odi.deliveryDocument
            LIMIT 30
        """)
        delivery_billing = cur.fetchall()

        # Billing → Payment (via billing_document_headers.accountingDocument)
        cur.execute("""
            SELECT DISTINCT
                bdh.billingDocument,
                par.accountingDocument
            FROM billing_document_headers bdh
            JOIN payments_accounts_receivable par
                ON par.accountingDocument = bdh.accountingDocument
            LIMIT 30
        """)
        billing_payment = cur.fetchall()

        conn.close()

    except Exception as e:
        print(f"DB error: {e}")
        return G

    for order, delivery in order_delivery:
        o_id = f"Order {order}"
        d_id = f"Delivery {delivery}"
        G.add_node(o_id, color=NODE_COLORS["order"], title=o_id, label=o_id)
        G.add_node(d_id, color=NODE_COLORS["delivery"], title=d_id, label=d_id)
        G.add_edge(o_id, d_id)

    for delivery, billing in delivery_billing:
        d_id = f"Delivery {delivery}"
        b_id = f"Billing {billing}"
        if d_id not in G:
            G.add_node(d_id, color=NODE_COLORS["delivery"], title=d_id, label=d_id)
        G.add_node(b_id, color=NODE_COLORS["billing"], title=b_id, label=b_id)
        G.add_edge(d_id, b_id)

    for billing, payment in billing_payment:
        b_id = f"Billing {billing}"
        p_id = f"Payment {payment}"
        if b_id not in G:
            G.add_node(b_id, color=NODE_COLORS["billing"], title=b_id, label=b_id)
        G.add_node(p_id, color=NODE_COLORS["payment"], title=p_id, label=p_id)
        G.add_edge(b_id, p_id)

    return G


def visualize_graph():
    G = build_graph_from_db()

    if len(G.nodes) == 0:
        print("No graph data found.")
        return

    net = Network(height="560px", width="100%", directed=True, bgcolor="#1a1a2e", font_color="white")
    net.toggle_physics(True)
    net.set_options("""
    {
      "edges": {
        "smooth": { "type": "curvedCW", "roundness": 0.2 },
        "arrows": { "to": { "enabled": true } }
      },
      "physics": {
        "stabilization": { "iterations": 150 }
      }
    }
    """)

    for node, attrs in G.nodes(data=True):
        net.add_node(
            node,
            label=attrs.get("label", node),
            title=attrs.get("title", node),
            color=attrs.get("color", "#888888"),
        )

    for src, dst in G.edges():
        net.add_edge(src, dst)

    net.write_html(OUTPUT_PATH)
    print("Graph visualization implemented with real data connections")
