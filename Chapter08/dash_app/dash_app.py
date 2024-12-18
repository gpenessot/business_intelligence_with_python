import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import geopandas as gpd
import plotly.express as px
import json
from datetime import datetime
from typing import Tuple
import base64

# Constants
LOGO_PATH = "../app_img/logo.png"
APP_VERSION = "v1.0.0"
DATA_PATHS = {
    'orders': '../data/olist_orders_dataset.csv',
    'customers': '../data/olist_customers_dataset.csv',
    'order_items': '../data/olist_order_items_dataset.csv',
    'products': '../data/olist_products_dataset.csv',
    'geojson': '../data/brazil-states.geojson'
}

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

def get_base64_encoded_image(image_path: str) -> str:
    """Read an image file and return its Base64 encoded string."""
    with open(image_path, 'rb') as file:
        return base64.b64encode(file.read()).decode()

def load_data() -> pd.DataFrame:
    """Load and preprocess data from CSV files."""
    orders = pd.read_csv(DATA_PATHS['orders'], usecols=[0,1,2,3,4,6,7])
    customers = pd.read_csv(DATA_PATHS['customers'])
    order_items = pd.read_csv(DATA_PATHS['order_items'], usecols=[0,1,2,3,5,6])
    products = pd.read_csv(DATA_PATHS['products'], usecols=[0,1])
    
    df = (orders.merge(customers, on='customer_id')
                .merge(order_items, on='order_id')
                .merge(products, on='product_id'))
    
    date_columns = ['order_purchase_timestamp', 'order_approved_at', 
                    'order_delivered_customer_date', 'order_estimated_delivery_date']
    df[date_columns] = df[date_columns].apply(pd.to_datetime)
    
    df['order_year'] = df['order_purchase_timestamp'].dt.year
    df['order_month'] = df['order_purchase_timestamp'].dt.month_name()
    df['order_date'] = df['order_purchase_timestamp'].dt.date
    
    return df

def load_geo_data(df: pd.DataFrame) -> Tuple[gpd.GeoDataFrame, dict]:
    """Load and process geographical data."""
    gdf = gpd.read_file(DATA_PATHS['geojson'])[['name', 'sigla', 'geometry']]
    gdf_by_year = df.groupby(['order_year', 'customer_state']).agg({
        'price': 'sum', 
        'customer_unique_id': lambda x: x.nunique()
    }).reset_index()
    gdf_by_year = gdf.merge(gdf_by_year, left_on='sigla', right_on='customer_state')
    geojson_data = json.loads(gdf_by_year.to_json())
    
    return gdf_by_year, geojson_data

# Load data
df = load_data()
gdf, geo_data = load_geo_data(df)

# Prepare dates and version info
last_update_date = datetime.now().strftime("%Y-%m-%d")
data_freshness_date = df['order_date'].max().strftime("%Y-%m-%d")

# Encode logo
logo_base64 = get_base64_encoded_image(LOGO_PATH)

# Layout
app.layout = dbc.Container([
    dbc.Row([
        # Sidebar
        dbc.Col([
            html.Br(),
            html.Div(
                html.Img(src=f"data:image/png;base64,{logo_base64}", style={"width": "70%"}),
                style={'text-align':'center'}
            ),
            html.Br(),
            html.H5("Filters"),
            html.Br(),
            html.P('Select Order Year'),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': str(year), 'value': year} for year in sorted(gdf['order_year'].unique())],
                value=gdf['order_year'].min()
            ),
            html.Br(),
            html.P('Select a State'),
            dcc.Dropdown(
                id='state-dropdown',
                options=[{'label': state, 'value': state} for state in sorted(gdf['customer_state'].unique())],
                value=gdf['customer_state'].iloc[0]
            ),
        ], width=2, className="vh-100", style={'backgroundColor':"#F0F2F6"}),
        
        # Main content
        dbc.Col([
            dbc.Row([
                dbc.Col(
                    html.B(
                        html.H1("My very first dashboard with Dash", className="text-center mb-4")), width=12)
            ]),
            dbc.Row([
                dbc.Col(dbc.Card(id="total-revenue-card", body=True), width=4),
                dbc.Col(dbc.Card(id="average-order-value-card", body=True), width=4),
                dbc.Col(dbc.Card(id="number-of-customers-card", body=True), width=4),
            ], className="mb-4"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="choropleth-map"), width=6),
                dbc.Col(dcc.Graph(id="line-chart"), width=6),
            ], className="mb-4"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="bar-chart-states"), width=4),
                dbc.Col(dcc.Graph(id="bar-chart-products"), width=4),
                dbc.Col(dcc.Graph(id="pie-chart-cities"), width=4),
            ]),
            dbc.Row([
                dbc.Col(html.Footer(f"Last dashboard update: {last_update_date} | Data freshness date: {data_freshness_date} | Application version: {APP_VERSION} | Contact: email@company.com"), style={'text-align':'center'}, width=12)
            ]),
        ], width=10)
    ]),
], fluid=True, className="vh-100")

# Update the callback
@app.callback(
    [Output("total-revenue-card", "children"),
     Output("average-order-value-card", "children"),
     Output("number-of-customers-card", "children"),
     Output("choropleth-map", "figure"),
     Output("line-chart", "figure"),
     Output("bar-chart-states", "figure"),
     Output("bar-chart-products", "figure"),
     Output("pie-chart-cities", "figure")],
    [Input("year-dropdown", "value"),
     Input("state-dropdown", "value")]
)
def update_charts(selected_year, selected_state):
    filtered_gdf = gdf[gdf['order_year'] == selected_year]
    filtered_df = df[df['order_year'] == selected_year]
    daily_sales = filtered_df.groupby('order_date')['price'].sum().reset_index()
    sales_by_city = filtered_df[filtered_df['customer_state'] == selected_state].groupby('customer_city')['price'].sum().reset_index()
    best_products = filtered_df.groupby('product_category_name')['price'].sum().reset_index()

    total_price = filtered_gdf['price'].sum()
    average_price = filtered_gdf['price'].mean()
    unique_customers = filtered_gdf['customer_unique_id'].nunique()

    # KPI Cards
    total_revenue_card = [
        html.H4("Total Revenue"),
        html.H2(f"${total_price:,.2f}")
    ]
    average_order_value_card = [
        html.H4("Average Order Value (AOV)"),
        html.H2(f"${average_price:,.2f}")
    ]
    number_of_customers_card = [
        html.H4("Number of Customers"),
        html.H2(f"{unique_customers:,}")
    ]

    # Choropleth map
    fig1 = px.choropleth(
        filtered_gdf,
        geojson=json.loads(filtered_gdf.to_json()),
        locations='name',
        featureidkey="properties.name",
        color='price',
        hover_name='name',
        hover_data=['sigla', 'price', 'order_year', 'customer_state', 'customer_unique_id'],
        center={"lat": -14.2350, "lon": -51.9253},
        color_continuous_scale="plasma"
    )
    fig1.update_geos(fitbounds="locations", visible=False)
    fig1.update_layout(margin={"r":0, "t":0, "l":0, "b":0})

    # Line chart
    fig2 = px.line(
        daily_sales, 
        x='order_date', 
        y='price', 
        color_discrete_sequence=px.colors.sequential.Plasma,
        title='Sum of prices by day',
        labels={'order_date': 'Date', 'price': 'Sum of prices'},
        template='plotly_white'
    )
    average_sales = daily_sales['price'].mean()
    fig2.add_hline(
        y=average_sales, 
        line_dash="dash", 
        line_color="orange",
        annotation_text="average sales",
        annotation_position="top left"
    )

    # Bar charts
    fig3 = px.bar(
        filtered_gdf.nlargest(5, 'price').sort_values(by='price', ascending=False),
        x='price',
        y='customer_state',
        orientation='h',
        color='customer_state',
        color_discrete_sequence=px.colors.sequential.Plasma,
        title="Top 5 States by Sales",
        template='plotly_white'
    )

    fig4 = px.bar(
        best_products.nlargest(5, 'price').sort_values(by='price', ascending=False),
        x='price',
        y='product_category_name',
        orientation='h',
        color='product_category_name',
        color_discrete_sequence=px.colors.sequential.Plasma,
        title="Top 5 Product Categories",
        template='plotly_white'
    )

    # Pie chart
    fig5 = px.pie(
        sales_by_city.nlargest(5, 'price').sort_values(by='price', ascending=False),
        values='price',
        names='customer_city',
        color='customer_city',
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Plasma,
        title=f"Top 5 Cities in {selected_state}"
    )

    return total_revenue_card, average_order_value_card, number_of_customers_card, fig1, fig2, fig3, fig4, fig5


if __name__ == "__main__":
    app.run_server(debug=True)
