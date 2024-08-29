<|toggle|theme|>
# My first dashboard with Taipy {: .text-center}

<br/>

<|layout|columns=1 1 8|
<|{selected_year}|selector|lov={years}|on_change=on_change|dropdown|label=Year|>

<|{selected_state}|selector|lov={states}|on_change=on_change|dropdown|label=State|>
|>

<br/>

<|layout|columns=4 4 4|gap=25px|columns[mobile]=1|
<|card|
**Total Revenue**
<|{total_price}|text|class_name=h3|>
|>

<|card|
**Average order value (AOV)**
<|{average_price}|text|class_name=h3|>
|>

<|card|
**Number of Customers**
<|{unique_customers}|text|class_name=h3|>
|>
|>
<br/>

<|layout|columns=1 2|gap=25px|columns[mobile]=1|
<|chart|figure={fig1}|title=Total revenue by State|>

<|chart|figure={fig2}|title=Daily revenue|>
|>

<br/>

<|layout|columns=1 1 1|gap=25px|columns[mobile]=1|
<|chart|figure={fig3}|title=Total revenue by customer_state|>

<|chart|figure={fig4}|title=Total revenue by product_category_name|>

<|chart|figure={fig5}|title=Top 5 cities for selected State|>
|>

<br/>

<|Last dashboard update: {last_update_date} - |>
<|Data freshness date: {data_freshness_date} - |>
<|Application version: {APP_VERSION} - |> 
Contact: email@company.com"

