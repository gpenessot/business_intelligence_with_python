# etl_functions.py
import os
import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi
from loguru import logger
import sqlite3

def extract(destination_folder="./data/raw/"):
    """Downloads the Olist dataset from Kaggle and extracts it to the specified folder.

    Args:
        destination_folder (str, optional): The path to the folder where the data should be stored. Defaults to "./data/raw/".

    Returns:
        str: The path to the folder where the data has been extracted.
    """
    api = KaggleApi()
    api.authenticate()

    os.makedirs(destination_folder, exist_ok=True)

    api.dataset_download_files('olistbr/brazilian-ecommerce', path=destination_folder, unzip=True)

    logger.info(f"The Olist dataset has been downloaded and extracted to {destination_folder}")
    return destination_folder

def clean_olist_data(df):
    """Performs basic cleaning on the Olist dataset for analysis relevant to France or Europe.

    Args:
        df (pd.DataFrame): The Olist dataset as a Pandas DataFrame.

    Returns:
        pd.DataFrame: The cleaned DataFrame.
    """
    irrelevant_columns = [
        'seller_zip_code_prefix', 'customer_zip_code_prefix', 
        'geolocation_zip_code_prefix', 'product_category_name_english'  
    ]
    df = df.drop(columns=irrelevant_columns, errors='ignore')

    date_columns = ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date', 'order_delivered_customer_date', 'order_estimated_delivery_date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    return df

def transform(raw_data_dir="./data/raw", processed_data_dir="./data/processed"):
    """Cleans the specified Olist CSV files and saves the cleaned versions.

    Args:
        raw_data_dir (str, optional): Directory containing the raw Olist CSV files. Defaults to "./data/raw".
        processed_data_dir (str, optional): Directory to save the cleaned CSV files. Defaults to "./data/processed".

    Returns:
        str: The path to the directory containing the processed data.
    """
    files_to_clean = [
        'olist_customers_dataset.csv',
        'olist_geolocation_dataset.csv',
        'olist_order_items_dataset.csv',
        'olist_order_payments_dataset.csv',
        'olist_order_reviews_dataset.csv',
        'olist_orders_dataset.csv',
        'olist_products_dataset.csv',
        'olist_sellers_dataset.csv'
    ]

    os.makedirs(processed_data_dir, exist_ok=True)

    for file_name in files_to_clean:
        raw_file_path = os.path.join(raw_data_dir, file_name)

        if os.path.exists(raw_file_path):
            logger.info(f"Cleaning {file_name}...")
            try:
                df = pd.read_csv(raw_file_path)
                df_cleaned = clean_olist_data(df)

                processed_file_path = os.path.join(processed_data_dir, file_name)
                df_cleaned.to_csv(processed_file_path, index=False)
                logger.info(f"Cleaned {file_name} saved to {processed_file_path}")
            except Exception as e:
                logger.error(f"Error cleaning {file_name}: {e}")
        else:
            logger.warning(f"File not found: {raw_file_path}")
    
    return processed_data_dir

def load_processed_data(processed_data_dir="./data/processed"):
    """Loads the cleaned Olist CSV files into a dictionary of Pandas DataFrames.

    Args:
        processed_data_dir (str, optional): Directory containing the cleaned CSV files. Defaults to "./data/processed".

    Returns:
        dict: A dictionary where keys are file names (without extension) and values are the corresponding Pandas DataFrames.
    """
    data = {}
    for file_name in os.listdir(processed_data_dir):
        if file_name.endswith('.csv'):
            file_path = os.path.join(processed_data_dir, file_name)
            try:
                df = pd.read_csv(file_path)
                data[file_name[:-4]] = df
                logger.info(f"Loaded {file_name} into DataFrame.")
            except Exception as e:
                logger.error(f"Error loading {file_name}: {e}")
    return data

def load_to_database(processed_data_dir, db_name="olist.db"):
    """Loads the cleaned Olist data into a SQLite database.

    Args:
        processed_data_dir (str): Directory containing the cleaned CSV files.
        db_name (str, optional): Name of the SQLite database file. Defaults to "olist.db".
    """
    data = load_processed_data(processed_data_dir)
    conn = sqlite3.connect(db_name)

    for table_name, df in data.items():
        try:
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            logger.info(f"Loaded {table_name} into {db_name}.")
        except Exception as e:
            logger.error(f"Error loading {table_name}: {e}")

    conn.close()
