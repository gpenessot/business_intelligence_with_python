import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import json
import base64
from datetime import datetime
from typing import Tuple

from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.grid import grid
from streamlit_extras.add_vertical_space import add_vertical_space

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

# Set page configuration
st.set_page_config(layout="wide")


def get_base64_encoded_image(image_path: str) -> str:
    """Read an image file and return its Base64 encoded string."""
    with open(image_path, "rb") as file:
        return base64.b64encode(file.read()).decode()


def create_centered_logo_html(logo_base64: str) -> str:
    """Create HTML for a centered logo using a Base64 encoded image."""
    return f"""
    <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
        <img src="data:image/png;base64,{logo_base64}" style="max-width: 100%;">
    </div>
    <br><br>
    """


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load and preprocess data from CSV files."""
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


@st.cache_data
def load_geo_data(df: pd.DataFrame) -> Tuple[gpd.GeoDataFrame, dict]:
    """Load and process geographical data."""
    gdf = gpd.read_file(DATA_PATHS["geojson"])[["name", "sigla", "geometry"]]
    gdf_by_year = (
        df.groupby(["order_year", "customer_state"])
        .agg({"price": "sum", "customer_id": lambda x: x.nunique()})
        .reset_index()
    )
    gdf_by_year = gdf.merge(gdf_by_year, left_on="sigla", right_on="customer_state")

    return gdf_by_year


def create_choropleth(gdf: gpd.GeoDataFrame, geojson_data: dict) -> px.choropleth:
    """Create a choropleth map using Plotly Express."""
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
    """Create a line chart for daily sales."""
    fig = px.line(
        daily_sales,
        x="order_date",
        y="price",
        color_discrete_sequence=px.colors.sequential.Plasma,
        title="Daily revenue",
        labels={"order_date": "Date", "price": "Revenue"},
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
    """Create a horizontal bar chart."""
    return px.bar(
        data.nlargest(5, "price").sort_values(by="price", ascending=False),
        x="price",
        text="price",
        y=y,
        orientation="h",
        title=f"Total revenue by {y}",
        color=y,
        color_discrete_sequence=px.colors.sequential.Plasma,
    ).update_layout(showlegend=False)


def create_pie_chart(data: pd.DataFrame) -> px.pie:
    """Create a pie chart."""
    return (
        px.pie(
            data.nlargest(5, "price").sort_values(by="price", ascending=False),
            values="price",
            names="customer_city",
            color="customer_city",
            title="Top 5 cities for selected State",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Plasma,
        )
        .update_layout(showlegend=False)
        .update_traces(textposition="inside", textinfo="percent+label")
    )


def main():
    # Load data
    df = load_data()
    gdf = load_geo_data(df)

    # Prepare dates and version info
    last_update_date = datetime.now().strftime("%Y-%m-%d")
    data_freshness_date = df["order_date"].max().strftime("%Y-%m-%d")

    # Prepare logo
    logo_base64 = get_base64_encoded_image(LOGO_PATH)
    centered_logo_html = create_centered_logo_html(logo_base64)

    # Set up page layout
    st.markdown(
        "<h1 align='center'>My very first dashboard with Streamlit</h1><br>",
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        st.markdown(centered_logo_html, unsafe_allow_html=True)
        st.title("Filters")

        years = sorted(gdf["order_year"].unique())
        selected_year = st.selectbox("Select Order Year", years, index=2)

        states = sorted(gdf["customer_state"].unique())
        selected_state = st.selectbox("Select a State", states)

        add_vertical_space(30)
        st.markdown(
            f"""
            <div style='width: 100%; text-align: center; font-size: 12px; color: grey;'>
                <hr style='margin: 5px 0;'>
                <p>Last dashboard update: {last_update_date}<br>
                   Data freshness date: {data_freshness_date}<br>
                   Application version: {APP_VERSION}<br>
                   Contact: <a href="mailto:email@company.com">email@company.com</a></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Filter data
    filtered_gdf = gdf[gdf["order_year"] == selected_year]
    daily_sales = (
        df[df["order_year"] == selected_year]
        .groupby("order_date")["price"]
        .sum()
        .reset_index()
    )

    sales_by_city = (
        df[
            (df["order_year"] == selected_year)
            & (df["customer_state"] == selected_state)
        ]
        .groupby("customer_city")["price"]
        .sum()
        .reset_index()
    )

    best_products = (
        df[df["order_year"] == selected_year]
        .groupby("product_category_name")["price"]
        .sum()
        .reset_index()
    )

    # Calculate metrics
    total_price = filtered_gdf["price"].sum()
    average_price = filtered_gdf["price"].mean().round(2)
    unique_customers = filtered_gdf["customer_id"].nunique()

    # Create charts
    fig1 = create_choropleth(filtered_gdf, json.loads(filtered_gdf.to_json()))
    fig2 = create_line_chart(daily_sales)
    fig3 = create_bar_chart(
        gdf[gdf["order_year"] == selected_year], "price", "customer_state"
    )
    fig4 = create_bar_chart(best_products, "price", "product_category_name")
    fig5 = create_pie_chart(sales_by_city)

    # Display dashboard
    my_grid = grid(3, [1, 2], 3, vertical_align="bottom")

    # Row 1: Metrics
    my_grid.metric(label="Total Revenue", value=f"${total_price:,.2f}")
    my_grid.metric(label="Average order value (AOV)", value=f"${average_price:,.2f}")
    my_grid.metric(label="Number of Customers", value=unique_customers)
    style_metric_cards(
        background_color="#FFFFFF",
        border_left_color="#686664",
        border_color="#000000",
        box_shadow="#F71938",
    )

    # Row 2: Maps and charts
    my_grid.plotly_chart(fig1)
    my_grid.plotly_chart(fig2)

    # Row 3: Additional charts
    my_grid.plotly_chart(fig3)
    my_grid.plotly_chart(fig4)
    my_grid.plotly_chart(fig5)


if __name__ == "__main__":
    main()
