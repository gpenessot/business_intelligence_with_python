import pandas as pd
from taipy.gui import Markdown, Gui
import taipy as tp
import geopandas as gpd
import plotly.express as px
from datetime import datetime
from typing import Tuple
import json

"""
Taipy Dashboard Application

This script creates a dashboard using Taipy, Plotly, and Pandas to visualize sales data.
It includes various charts and maps to represent sales information across different
states and cities in Brazil.
"""

# Constants
LOGO_PATH = "../app_img/logo.png"
APP_VERSION = "v1.0.0"
DATA_PATHS = {
    "orders": "../data/olist_orders_dataset.csv",
    "customers": "../data/olist_customers_dataset.csv",
    "order_items": "../data/olist_order_items_dataset.csv",
    "products": "../data/olist_products_dataset.csv",
    "geojson": "../data/brazil-states.geojson",
}

# Initialization
selected_year = 2018
selected_state = 'AC'
total_price = '$0.0'
average_price = '$0.0'
unique_customers = '0'
fig1 = None
fig2 = None
fig3 = None
fig4 = None
fig5 = None

# Page parameters
layout = {'barmode':'stack', "hovermode":"x"}
options = {"unselected":{"marker":{"opacity":0.5}}}

def load_data() -> pd.DataFrame:
    """
    Load and preprocess data from CSV files.

    Returns:
        pd.DataFrame: A DataFrame containing merged and preprocessed data from various CSV files.
    """
    orders = pd.read_csv(DATA_PATHS["orders"], usecols=[0, 1, 2, 3, 4, 6, 7])
    customers = pd.read_csv(DATA_PATHS["customers"])
    order_items = pd.read_csv(DATA_PATHS["order_items"], usecols=[0, 1, 2, 3, 5, 6])
    products = pd.read_csv(DATA_PATHS["products"], usecols=[0, 1])

    df = (
        orders.merge(customers, on="customer_id")
        .merge(order_items, on="order_id")
        .merge(products, on="product_id")
    )

    date_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    df[date_columns] = df[date_columns].apply(pd.to_datetime)

    df["order_year"] = df["order_purchase_timestamp"].dt.year
    df["order_month"] = df["order_purchase_timestamp"].dt.month_name()
    df["order_date"] = df["order_purchase_timestamp"].dt.date

    return df

def load_geo_data(df: pd.DataFrame) -> Tuple[gpd.GeoDataFrame, dict]:
    """
    Load and process geographical data.

    Args:
        df (pd.DataFrame): The preprocessed DataFrame containing order data.

    Returns:
        Tuple[gpd.GeoDataFrame, dict]: A tuple containing a GeoDataFrame with merged geographical
        and order data, and a dictionary with GeoJSON data.
    """
    gdf = gpd.read_file(DATA_PATHS["geojson"])[["name", "sigla", "geometry"]]
    gdf_by_year = (
        df.groupby(["order_year", "customer_state"])
        .agg({"price": "sum", "customer_id": lambda x: x.nunique()})
        .reset_index()
    )
    gdf_by_year = gdf.merge(gdf_by_year, left_on="sigla", right_on="customer_state")

    return gdf_by_year


def create_choropleth(gdf: gpd.GeoDataFrame, geojson_data: dict) -> px.choropleth:
    """
    Create a choropleth map using Plotly Express.

    Args:
        gdf (gpd.GeoDataFrame): GeoDataFrame containing geographical and order data.
        geojson_data (dict): Dictionary containing GeoJSON data for the map.

    Returns:
        px.choropleth: A Plotly Express choropleth figure.
    """
    fig = px.choropleth(
        gdf,
        geojson=geojson_data,
        locations="name",
        featureidkey="properties.name",
        color="price",
        title="Total revenue by State",
        hover_name="name",
        hover_data=[
            "sigla",
            "price",
            "order_year",
            "customer_state",
            "customer_id",
        ],
        center={"lat": -14.2350, "lon": -51.9253},
        color_continuous_scale="plasma",
    )
    fig.update_geos(fitbounds="locations", visible=False)
    # fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


def create_line_chart(daily_sales: pd.DataFrame) -> px.line:
    """
    Create a line chart for daily sales.

    Args:
        daily_sales (pd.DataFrame): DataFrame containing daily sales data.

    Returns:
        px.line: A Plotly Express line chart figure.
    """
    fig = px.line(
        daily_sales,
        x="order_date",
        y="price",
        color_discrete_sequence=px.colors.sequential.Plasma,
        title="Daily revenue",
        labels={"order_date": "Date", "price": "Revenue"},
        template='plotly_white'
    )
    average_sales = daily_sales["price"].mean()
    fig.add_hline(
        y=average_sales,
        line_dash="dash",
        line_color="orange",
        annotation_text="average daily revenue",
        annotation_position="top left",
    )
    return fig


def create_bar_chart(data: pd.DataFrame, x: str, y: str) -> px.bar:
    """
    Create a horizontal bar chart.

    Args:
        data (pd.DataFrame): DataFrame containing the data to be plotted.
        x (str): Column name for the x-axis values.
        y (str): Column name for the y-axis values.

    Returns:
        px.bar: A Plotly Express horizontal bar chart figure.
    """
    return px.bar(
        data.nlargest(5, "price").sort_values(by="price", ascending=False),
        x="price",
        text="price",
        y=y,
        orientation="h",
        title=f"Total revenue by {y}",
        color=y,
        color_discrete_sequence=px.colors.sequential.Plasma,
        template='plotly_white'
    ).update_layout(showlegend=False)


def create_pie_chart(data: pd.DataFrame) -> px.pie:
    """
    Create a pie chart.

    Args:
        data (pd.DataFrame): DataFrame containing the data to be plotted.

    Returns:
        px.pie: A Plotly Express pie chart figure.
    """
    return (
        px.pie(
            data.nlargest(5, "price").sort_values(by="price", ascending=False),
            values="price",
            names="customer_city",
            color="customer_city",
            title="Top 5 cities for selected State",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Plasma,
            template='plotly_white'
        )
        .update_layout(showlegend=False)
        .update_traces(textposition="inside", textinfo="percent+label")
    )

# Load data
df = load_data()
gdf= load_geo_data(df)

years = sorted(gdf["order_year"].astype('str').unique())
states = sorted(gdf["customer_state"].unique())

# Prepare dates and version info
last_update_date = datetime.now().strftime("%Y-%m-%d")
data_freshness_date = df['order_date'].max().strftime("%Y-%m-%d")


def initialize(data, geodata, selected_year='2018', selected_state='AC'):
    """
    Initialize the dashboard data based on selected year and state.

    Args:
        data (pd.DataFrame): The main DataFrame containing all order data.
        geodata (gpd.GeoDataFrame): GeoDataFrame containing geographical data.
        selected_year (str, optional): The year to filter data by. Defaults to '2018'.
        selected_state (str, optional): The state to filter data by. Defaults to 'AC'.

    Returns:
        tuple: A tuple containing filtered DataFrames and processed data for various charts.
    """
    filtered_gdf = geodata[geodata['order_year'] == int(selected_year)]
    filtered_df = data[data['order_year'] == int(selected_year)]
    daily_sales = filtered_df.groupby('order_date')['price'].sum().reset_index()
    sales_by_city = filtered_df[filtered_df['customer_state'] == selected_state].groupby('customer_city')['price'].sum().reset_index()
    best_products = filtered_df.groupby('product_category_name')['price'].sum().reset_index()

    return filtered_df, filtered_gdf, daily_sales, sales_by_city, best_products

filtered_df, filtered_gdf, daily_sales, sales_by_city, best_products = initialize(df, gdf)

def on_change(state):
    """
    Update the dashboard state when user selections change.

    Args:
        state: The current state of the Taipy application.
    """
    (
        state.filtered_df,
        state.filtered_gdf,
        state.daily_sales,
        state.sales_by_city,
        state.best_products
    ) = initialize(df, gdf, state.selected_year, state.selected_state)

    state.total_price = f'${state.filtered_gdf["price"].sum():,.2f}'
    state.average_price = f'${state.filtered_gdf["price"].mean():,.2f}'
    state.unique_customers = f'{state.filtered_gdf["customer_id"].nunique()}'
    state.fig1 = create_choropleth(state.filtered_gdf, json.loads(state.filtered_gdf.to_json()))
    state.fig2 = create_line_chart(state.daily_sales)
    state.fig3 = create_bar_chart(state.filtered_gdf, "price", "customer_state")
    state.fig4 = create_bar_chart(state.best_products, "price", "product_category_name")
    state.fig5 = create_pie_chart(state.sales_by_city)


page_md = Markdown('layout.md')

if __name__ == '__main__':
    page = Gui(page_md)
    tp.Core().run()
    page.run(title="New Taipy Dashboard", dark_mode=False)
