import pandas as pd
import taipy.gui.builder as tgb
from taipy.gui import Gui
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


def initialize(data, geodata, selected_year="2018", selected_state="AC"):
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
    filtered_gdf = geodata[geodata["order_year"] == int(selected_year)]
    filtered_df = data[data["order_year"] == int(selected_year)]
    daily_sales = filtered_df.groupby("order_date")["price"].sum().reset_index()
    sales_by_city, best_products = filter_by_city(filtered_df, selected_state)
    return filtered_df, filtered_gdf, daily_sales, sales_by_city, best_products


def filter_by_city(filtered_df, selected_state="AC"):
    sales_by_city = (
        filtered_df[filtered_df["customer_state"] == selected_state]
        .groupby("customer_city")["price"]
        .sum()
        .reset_index()
    )
    best_products = (
        filtered_df.groupby("product_category_name")["price"].sum().reset_index()
    )

    return sales_by_city, best_products


# Initialization
selected_year = 2018
selected_state = "AC"

# Load data
df = load_data()
gdf = load_geo_data(df)

filtered_df, filtered_gdf, daily_sales, sales_by_city, best_products = initialize(
    df, gdf
)


def create_choropleth(gdf: gpd.GeoDataFrame) -> px.choropleth:
    """
    Create a choropleth map using Plotly Express.

    Args:
        gdf (gpd.GeoDataFrame): GeoDataFrame containing geographical and order data.
        geojson_data (dict): Dictionary containing GeoJSON data for the map.

    Returns:
        px.choropleth: A Plotly Express choropleth figure.
    """

    geojson_data = json.loads(gdf.to_json())
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
        template="plotly_white",
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


def create_bar_chart(data: pd.DataFrame, y: str) -> px.bar:
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
        template="plotly_white",
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
            template="plotly_white",
        )
        .update_layout(showlegend=False)
        .update_traces(textposition="inside", textinfo="percent+label")
    )


def change_year(state):
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
        state.best_products,
    ) = initialize(df, gdf, state.selected_year, state.selected_state)


def change_state(state):
    """
    Update the dashboard state when user selections change.

    Args:
        state: The current state of the Taipy application.
    """
    (
        state.sales_by_city,
        state.best_products,
    ) = filter_by_city(state.filtered_df, state.selected_state)


with tgb.Page() as page:
    tgb.toggle(theme=True)

    with tgb.layout("1 4", gap="25px"):
        with tgb.part("sidebar"):
            tgb.text("#### Filters", mode="md")
            tgb.text("Select year:")
            tgb.selector(
                "{selected_year}",
                lov=sorted(gdf["order_year"].astype("str").unique()),
                dropdown=True,
                on_change=change_year,
                label="Year",
            )

            tgb.text("Select state:")
            tgb.selector(
                "{selected_state}",
                lov=sorted(gdf["customer_state"].unique()),
                dropdown=True,
                on_change=change_state,
                label="State",
            )

        with tgb.part("text-center"):
            tgb.text("# My first dashboard with Taipy", mode="md")
            with tgb.layout("1 1 1", gap="25px"):
                with tgb.part("card"):
                    tgb.text("**Total Revenue:**", mode="md")
                    tgb.text(
                        lambda filtered_gdf: f'${filtered_gdf["price"].sum():,.2f}',
                        class_name="h3 color-primary",
                    )

                with tgb.part("card"):
                    tgb.text("**Average order value (AOV):**", mode="md")
                    tgb.text(
                        lambda filtered_gdf: f'${filtered_gdf["price"].mean():,.2f}',
                        class_name="h3 color-primary",
                    )

                with tgb.part("card"):
                    tgb.text(
                        "**Unique customers:**",
                        mode="md",
                    )
                    tgb.text(
                        lambda filtered_gdf: f'{filtered_gdf["customer_id"].nunique()}',
                        class_name="h3 color-primary",
                    )

            tgb.html("br")

            with tgb.layout("1 2", gap="25px"):
                tgb.chart(
                    figure=lambda filtered_gdf: create_choropleth(filtered_gdf),
                )

                tgb.chart(
                    figure=lambda daily_sales: create_line_chart(daily_sales),
                )

            tgb.html("br")

            with tgb.layout("1 1 1", gap="25px"):
                tgb.chart(
                    figure=lambda filtered_gdf: create_bar_chart(
                        filtered_gdf, "customer_state"
                    ),
                )
                tgb.chart(
                    figure=lambda best_products: create_bar_chart(
                        best_products, "product_category_name"
                    ),
                )
                tgb.chart(
                    figure=lambda sales_by_city: create_pie_chart(sales_by_city),
                )

            tgb.html("br")

            tgb.text(
                lambda df, APP_VERSION: f"Last dashboard update: {datetime.now().strftime('%Y-%m-%d')} - "
                f"Data freshness: {df['order_date'].max().strftime('%Y-%m-%d')} - "
                f"App version: {APP_VERSION}"
            )


if __name__ == "__main__":
    page = Gui(page)
    # tp.Core().run() # You do not use Taipy Core here to manage data, pipelines, caching, user management, etc
    page.run(title="New Taipy Dashboard", dark_mode=False, margin="0px")
