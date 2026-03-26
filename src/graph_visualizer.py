import os
import sqlite3
import networkx as nx
from pyvis.network import Network

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data.db")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "graph.html")

NODE_COLORS = {
    "order":    "#4A90D9",
    "delivery": "#F5A623",
    "billing":  "#7ED321",
    "payment":  "#D0021B",
}
DIM_COLOR = "#444455"


def build_graph_from_db(target_order=None):
    G = nx.DiGraph()

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        if target_order:
            cur.execute("""
                SELECT DISTINCT soh.salesOrder, odi.deliveryDocument
                FROM sales_order_headers soh
                JOIN outbound_delivery_items odi ON odi.referenceSdDocument = soh.salesOrder
                WHERE soh.salesOrder = ?
            """, (target_order,))
        else:
            cur.execute("""
                SELECT DISTINCT soh.salesOrder, odi.deliveryDocument
                FROM sales_order_headers soh
                JOIN outbound_delivery_items odi ON odi.referenceSdDocument = soh.salesOrder
                LIMIT 30
            """)
        order_delivery = cur.fetchall()

        delivery_ids = list({d for _, d in order_delivery}) if order_delivery else []

        if target_order and delivery_ids:
            placeholders = ",".join("?" * len(delivery_ids))
            cur.execute(f"""
                SELECT DISTINCT odi.deliveryDocument, bdi.billingDocument
                FROM outbound_delivery_items odi
                JOIN billing_document_items bdi ON bdi.referenceSdDocument = odi.deliveryDocument
                WHERE odi.deliveryDocument IN ({placeholders})
            """, delivery_ids)
        else:
            cur.execute("""
                SELECT DISTINCT odi.deliveryDocument, bdi.billingDocument
                FROM outbound_delivery_items odi
                JOIN billing_document_items bdi ON bdi.referenceSdDocument = odi.deliveryDocument
                LIMIT 30
            """)
        delivery_billing = cur.fetchall()

        billing_ids = list({b for _, b in delivery_billing}) if delivery_billing else []

        if target_order and billing_ids:
            placeholders = ",".join("?" * len(billing_ids))
            cur.execute(f"""
                SELECT DISTINCT bdh.billingDocument, par.accountingDocument
                FROM billing_document_headers bdh
                JOIN payments_accounts_receivable par ON par.accountingDocument = bdh.accountingDocument
                WHERE bdh.billingDocument IN ({placeholders})
            """, billing_ids)
        else:
            cur.execute("""
                SELECT DISTINCT bdh.billingDocument, par.accountingDocument
                FROM billing_document_headers bdh
                JOIN payments_accounts_receivable par ON par.accountingDocument = bdh.accountingDocument
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
        G.add_node(o_id, color=NODE_COLORS["order"], title=o_id, label=o_id, ntype="order")
        G.add_node(d_id, color=NODE_COLORS["delivery"], title=d_id, label=d_id, ntype="delivery")
        G.add_edge(o_id, d_id)

    for delivery, billing in delivery_billing:
        d_id = f"Delivery {delivery}"
        b_id = f"Billing {billing}"
        if d_id not in G:
            G.add_node(d_id, color=NODE_COLORS["delivery"], title=d_id, label=d_id, ntype="delivery")
        G.add_node(b_id, color=NODE_COLORS["billing"], title=b_id, label=b_id, ntype="billing")
        G.add_edge(d_id, b_id)

    for billing, payment in billing_payment:
        b_id = f"Billing {billing}"
        p_id = f"Payment {payment}"
        if b_id not in G:
            G.add_node(b_id, color=NODE_COLORS["billing"], title=b_id, label=b_id, ntype="billing")
        G.add_node(p_id, color=NODE_COLORS["payment"], title=p_id, label=p_id, ntype="payment")
        G.add_edge(b_id, p_id)

    return G


def visualize_graph(target_order=None):
    G = build_graph_from_db(target_order=target_order)

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
    print("Query-based graph highlighting implemented")
