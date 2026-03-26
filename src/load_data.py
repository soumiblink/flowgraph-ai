import pandas as pd
import sqlite3
import os
import glob
import json

BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sap-o2c-data")


def load_folder(folder_name: str) -> pd.DataFrame:
    folder_path = os.path.join(BASE_PATH, folder_name)

    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return pd.DataFrame()

    files = glob.glob(os.path.join(folder_path, "*.jsonl"))

    if not files:
        print(f"No JSONL files found in {folder_path}")
        return pd.DataFrame()

    df_list = []
    for file in files:
        try:
            df = pd.read_json(file, lines=True)
            df_list.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if not df_list:
        return pd.DataFrame()

    return pd.concat(df_list, ignore_index=True)


def setup_database():
    conn = sqlite3.connect("data.db")

    entity_folders = {
        "sales_order_headers": "sales_order_headers",
        "sales_order_items": "sales_order_items",
        "sales_order_schedule_lines": "sales_order_schedule_lines",
        "outbound_delivery_headers": "outbound_delivery_headers",
        "outbound_delivery_items": "outbound_delivery_items",
        "billing_document_headers": "billing_document_headers",
        "billing_document_items": "billing_document_items",
        "billing_document_cancellations": "billing_document_cancellations",
        "payments_accounts_receivable": "payments_accounts_receivable",
        "journal_entry_items_accounts_receivable": "journal_entry_items_accounts_receivable",
        "business_partners": "business_partners",
        "business_partner_addresses": "business_partner_addresses",
        "customer_company_assignments": "customer_company_assignments",
        "customer_sales_area_assignments": "customer_sales_area_assignments",
        "products": "products",
        "product_descriptions": "product_descriptions",
        "product_plants": "product_plants",
        "product_storage_locations": "product_storage_locations",
        "plants": "plants",
    }

    for table_name, folder_name in entity_folders.items():
        print(f"Loading {folder_name}...")

        df = load_folder(folder_name)

        if df.empty:
            print(f"Skipping {table_name}, no data found.")
            continue

        print(f"  {table_name} shape: {df.shape}")
        print(f"  {table_name} columns: {df.columns.tolist()}")

        # Serialize any columns containing dicts/lists to JSON strings
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)

        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"  -> Loaded into SQLite table '{table_name}'")

    conn.close()
    print("\nDatabase created successfully!")


if __name__ == "__main__":
    setup_database()
