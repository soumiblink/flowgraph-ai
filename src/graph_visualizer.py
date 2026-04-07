import os
import sqlite3
import networkx as nx
from pyvis.network import Network

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data.db")
OUTPUT_PATH = os.path.join(BASE_DIR, "graph.html")

NODE_COLORS = {
    "customer": "#9B59B6",  
    "order":    "#4A90D9",  
    "delivery": "#F5A623",  
    "billing":  "#7ED321",  
    "payment":  "#D0021B",  
}


def build_graph_from_db(target_order=None):
    G = nx.DiGraph()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        
        if target_order:
            cur.execute("""
                SELECT DISTINCT soldToParty, salesOrder
                FROM sales_order_headers
                WHERE salesOrder = ?
            """, (target_order,))
        else:
            cur.execute("""
                SELECT DISTINCT soldToParty, salesOrder
                FROM sales_order_headers
                LIMIT 20
            """)
        customer_order = cur.fetchall()

        order_ids = list({o for _, o in customer_order})

        
        if order_ids:
            ph = ",".join("?" * len(order_ids))
            cur.execute(f"""
                SELECT DISTINCT referenceSdDocument, deliveryDocument
                FROM outbound_delivery_items
                WHERE referenceSdDocument IN ({ph})
            """, order_ids)
        else:
            cur.execute("""
                SELECT DISTINCT referenceSdDocument, deliveryDocument
                FROM outbound_delivery_items LIMIT 20
            """)
        order_delivery = cur.fetchall()

        delivery_ids = list({d for _, d in order_delivery})

    
        if delivery_ids:
            ph = ",".join("?" * len(delivery_ids))
            cur.execute(f"""
                SELECT DISTINCT referenceSdDocument, billingDocument
                FROM billing_document_items
                WHERE referenceSdDocument IN ({ph})
            """, delivery_ids)
        else:
            cur.execute("""
                SELECT DISTINCT referenceSdDocument, billingDocument
                FROM billing_document_items LIMIT 20
            """)
        delivery_billing = cur.fetchall()

        billing_ids = list({b for _, b in delivery_billing})

        
        if billing_ids:
            ph = ",".join("?" * len(billing_ids))
            cur.execute(f"""
                SELECT DISTINCT bdh.billingDocument, par.accountingDocument
                FROM billing_document_headers bdh
                JOIN payments_accounts_receivable par
                    ON par.accountingDocument = bdh.accountingDocument
                WHERE bdh.billingDocument IN ({ph})
            """, billing_ids)
        else:
            cur.execute("""
                SELECT DISTINCT bdh.billingDocument, par.accountingDocument
                FROM billing_document_headers bdh
                JOIN payments_accounts_receivable par
                    ON par.accountingDocument = bdh.accountingDocument
                LIMIT 20
            """)
        billing_payment = cur.fetchall()

        conn.close()

    except Exception as e:
        print(f"DB error: {e}")
        return G

    for customer, order in customer_order:
        c_id = f"Customer {customer}"
        o_id = f"Order {order}"
        G.add_node(c_id, color=NODE_COLORS["customer"], title=c_id, label=c_id, ntype="customer")
        G.add_node(o_id, color=NODE_COLORS["order"], title=o_id, label=o_id, ntype="order")
        G.add_edge(c_id, o_id)

    for order, delivery in order_delivery:
        o_id = f"Order {order}"
        d_id = f"Delivery {delivery}"
        if o_id not in G:
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


def visualize_graph(target_order=None, highlight_nodes=None):
    G = build_graph_from_db(target_order=target_order)
    if len(G.nodes) == 0:
        print("No graph data found.")
        return

    highlight_set = set(highlight_nodes) if highlight_nodes else set()

    net = Network(
        height="580px",
        width="100%",
        directed=True,
        bgcolor="#1a1a2e",
        font_color="white",
    )

    net.set_options("""{
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "LR",
          "sortMethod": "directed",
          "levelSeparation": 220,
          "nodeSpacing": 120
        }
      },
      "physics": { "enabled": false },
      "edges": {
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.8 } },
        "color": { "color": "#aaaaaa" },
        "font": { "size": 11, "color": "#dddddd", "align": "middle" },
        "smooth": { "enabled": false }
      },
      "nodes": {
        "font": { "size": 13 },
        "borderWidth": 2
      }
    }""")

    EDGE_LABELS = {
        "customer": "places",
        "order":    "fulfilled by",
        "delivery": "billed as",
        "billing":  "paid via",
    }

    for node, attrs in G.nodes(data=True):
        ntype = attrs.get("ntype", "order")
        raw_id = node.split(" ", 1)[-1]
        label = f"{ntype.capitalize()}: {raw_id}"
        title = f"{ntype.capitalize()} ID: {raw_id}"

        if any(h in node for h in highlight_set):
            color = "#FF4136"
            size = 24
        else:
            color = attrs.get("color", NODE_COLORS.get(ntype, "#4A90D9"))
            size = 18

        net.add_node(node, label=label, title=title, color=color, size=size)

    for src, dst in G.edges():
        src_type = G.nodes[src].get("ntype", "order")
        edge_label = EDGE_LABELS.get(src_type, "")
        net.add_edge(src, dst, label=edge_label, title=edge_label)

    net.write_html(OUTPUT_PATH)



# ---------------------------------------------------------------------------
# Story mode: step-by-step flow for a given order
# ---------------------------------------------------------------------------

def get_order_flow_steps(order_id):
    """Return the O2C chain for an order as ordered step dicts."""
    steps = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Customer + Order
        cur.execute("""
            SELECT soldToParty, salesOrder, totalNetAmount
            FROM sales_order_headers WHERE salesOrder = ? LIMIT 1
        """, (order_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return []
        customer, order, amount = row
        steps.append({"step": "Customer",    "label": f"Customer ID: {customer}"})
        steps.append({"step": "Sales Order", "label": f"Order: {order}  |  Amount: {amount}"})

        # Delivery
        cur.execute("""
            SELECT deliveryDocument FROM outbound_delivery_items
            WHERE referenceSdDocument = ? LIMIT 1
        """, (order_id,))
        row = cur.fetchone()
        delivery = row[0] if row else None
        steps.append({"step": "Delivery", "label": f"Delivery: {delivery}" if delivery else "Delivery: NOT FOUND"})

        # Billing
        billing = None
        if delivery:
            cur.execute("""
                SELECT billingDocument FROM billing_document_items
                WHERE referenceSdDocument = ? LIMIT 1
            """, (delivery,))
            row = cur.fetchone()
            billing = row[0] if row else None
        steps.append({"step": "Billing", "label": f"Billing Doc: {billing}" if billing else "Billing: NOT FOUND"})

        # Payment
        payment = None
        if billing:
            cur.execute("""
                SELECT par.accountingDocument, par.amountInTransactionCurrency
                FROM billing_document_headers bdh
                JOIN payments_accounts_receivable par
                    ON par.accountingDocument = bdh.accountingDocument
                WHERE bdh.billingDocument = ? LIMIT 1
            """, (billing,))
            row = cur.fetchone()
            if row:
                payment = f"Doc: {row[0]}  |  Paid: {row[1]}"
        steps.append({"step": "Payment", "label": payment if payment else "Payment: NOT FOUND"})

        conn.close()
    except Exception as e:
        print(f"Story mode DB error: {e}")

    return steps
