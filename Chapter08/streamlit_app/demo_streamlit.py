import streamlit as st
import pandas as pd
#from pandas_profiling import ProfileReport
#from streamlit_pandas_profiling import st_profile_report

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime as dt

order_main = pd.read_csv('./data/olist_orders_dataset.csv')
products_in_order = pd.read_csv('./data/olist_order_items_dataset.csv')
order_payments = pd.read_csv('./data/olist_order_payments_dataset.csv')
product_info = pd.read_csv('./data/olist_products_dataset.csv')
order_reviews = pd.read_csv('./data/olist_order_reviews_dataset.csv')
customer_info = pd.read_csv('./data/olist_customers_dataset.csv')
category_translation = pd.read_csv('./data/product_category_name_translation.csv')

# sidebar
option = st.sidebar.radio('Select...',
                          ['pandas_profiling', 'preprocessing steps',
                           'analysis'])

if option == 'pandas_profiling':
    # description
    st.title('An eCommerce Company Evaluation')
    st.subheader('The Prompt')
    '''
    You’re a Data Scientist / Business Analyst working for a new eCommerce company 
    called A&B Co. (similar to Amazon) and you’ve been asked to prepare a presentation for the 
    Vice President of Sales and the Vice President of Operations that summarizes sales and operations thus far. 
    The summary should include (at a minimum) a summary of current state the business, current customer satisfaction, and a 
    proposal of 2-3 areas where the company can improve.
    '''
    st.subheader('Executive summary')
    st.write("The data does not have null value. Data with time related needs to be reformatted from object type"
             "to date type")

    st.subheader('First look into the data with pandas_profiling')
    selected_table = st.selectbox("What file do you want to see first?",
                                  ['olist_orders_dataset.csv',
                                   'olist_order_items_dataset.csv',
                                   'olist_order_payments_dataset.csv',
                                   'olist_products_dataset.csv',
                                   'olist_order_reviews_dataset.csv',
                                   'olist_customers_dataset.csv',
                                   'product_category_name_translation.csv'
                                   ])
    df = pd.read_csv(selected_table)
    st.write(df.head())
    st.write(df.dtypes)

    #olist_profile = ProfileReport(df, explorative=True)
    #st_profile_report(olist_profile)


# the following are executed outside of the if loop to make sure that the effect is carried to other page
def o2d(df, columns):
    for column in columns:
        df[column] = pd.to_datetime(df[column], format='%Y-%m-%d %H:%M:%S')


# apply the function
o2d(order_main, ['order_purchase_timestamp', 'order_approved_at',
                 'order_delivered_carrier_date', 'order_delivered_customer_date',
                 'order_estimated_delivery_date'])
order_main['estimated_vs_actual'] = order_main.order_delivered_customer_date - order_main.order_estimated_delivery_date

if option == 'preprocessing steps':
    st.subheader('Executive summary')
    st.write("The convert of data type is applied. Feature engineering applied to calculate"
             "the delay in delivery time. The gap definitely needs to be closed")

    st.title('Preprocessing steps')
    st.write('From the previous step, we do not have NA to deal with. One thing stands out though is '
             'that most of the data are in object format. We need to convert the relevant columns from object to date '
             'format with the following helper function')

    with st.echo():
        # convert object to date format
        def o2d(df, columns):
            for column in columns:
                df[column] = pd.to_datetime(df[column], format='%Y-%m-%d %H:%M:%S')
    # apply the function
    o2d(order_main, ['order_purchase_timestamp', 'order_approved_at',
                     'order_delivered_carrier_date', 'order_delivered_customer_date',
                     'order_estimated_delivery_date'])

    st.write('Now we can see the company delivery performance by comparing estimated delivery time')
    with st.echo():
        order_main[
            'estimated_vs_actual'] = order_main.order_delivered_customer_date - order_main.order_estimated_delivery_date
    st.write(order_main['estimated_vs_actual'].describe())
    st.write('The median and the mean are the same at this case. which is at 12 days later than expectation. '
             'That is quite bad. Let do some deeper analysis')

if option == 'analysis':
    st.subheader('Executive summary')
    st.write("The company has very low customer retention rate, at 3% only. Most of the growth in revenue is fueled"
             "by new customers. Despite the delivery speed, customers' satisfaction is relatively high. Low retention "
             "can be attributed to the longevity of the category of product bought")

    st.subheader('Analysis on revenue and number of order')
    st.write("we will first need to merge olist_orders_dataset, order_reviews and order_payments together,"
             "then to see the value of each order, we will group them by order_id")

    with st.echo():
        # merge the df together
        order_customer = order_main.merge(customer_info, how="left", on="customer_id")
        order_customer_review = order_customer.merge(order_reviews, how="left", on='order_id')
        all_order = order_customer.merge(order_payments, how='left', on='order_id')

        order_total = all_order.groupby('order_id').agg({'payment_value': 'sum'}).reset_index()
        order_total.columns = ['order_id', 'total_order_value']
        all_order = all_order.merge(order_total, how='left', on="order_id")

        # it was noted that the "current time" is September 2018. Therefore anytime after August will be dropped
        all_order = all_order[all_order['order_purchase_timestamp'] < pd.to_datetime(dt.date(2018, 9, 1))]

    st.write(all_order.head())
    st.write('Let now divide all the order purchase by the month that they were purchased. we will also put '
             'the year first for ease of sorting later')

    with st.echo():
        # get month of order purchase
        all_order['order_purchase_timestamp_month'] = all_order['order_purchase_timestamp'].dt.strftime('%Y %m')
        # separate df to see more clearly the revenue per item and its corresponding month
        revenue = all_order[['order_purchase_timestamp_month', 'payment_value', 'order_id']]

        revenue = revenue.groupby('order_purchase_timestamp_month').agg({'payment_value': 'sum'}).reset_index()

    revenue = revenue.sort_values('order_purchase_timestamp_month')
    fig, ax = plt.subplots()

    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5000))
    ax = plt.plot(revenue['order_purchase_timestamp_month'],
                  revenue['payment_value'])
    st.pyplot(fig)

    st.write("From the graph, we can see better that lately the revenue seem to have flatten, and then decline. "
             "Let's look into that further")

    st.subheader('Analysis on Customer Order Pattern')
    # quick look at our "super users"
    with st.echo():
        customer_summary = all_order.groupby('customer_unique_id').agg(
            {'payment_value': 'sum', 'order_id': pd.Series.nunique,
             'order_purchase_timestamp_month': 'min'}).reset_index()
        customer_summary.columns = ['customer_unique_id', 'total_spend', 'time_ordered', 'first_purchase']
    st.write(customer_summary.sort_values('time_ordered', ascending=False).head())

    # group customers by the number of time they ordered
    with st.echo():
        customer_by_n_order = customer_summary.groupby('time_ordered').agg(
            {'customer_unique_id': 'count', 'total_spend': 'sum'})
        customer_by_n_order.columns = ['number_of_id', 'total_spend']
    st.write(customer_by_n_order)

    st.write('all time retention percentage: {:10.2f}'.format((len(customer_summary) - 93103) / 93103))
    st.write("The number of customers who have used our service for more than 1 order is 3%. This is not necessarrily "
             "bad since the company inception was January 2017. With large increase of customer base, the percentage of "
             "recurring customer tends to be dwell down. Nonetheless, this figures alone reflects on a reality of the"
             " company's revenue: It is fueled by new customers. Therefore, with the same retention performance, a drop "
             "of new imcoming customers would likely result in a drop of revenue if the average order spent decrease."
             "let verify that")

    # plot both number of new customer per month and revenue per month on the same graph
    with st.echo():
        n_customer_first_perchase_month = customer_summary.groupby('first_purchase')[
            'customer_unique_id'].count().reset_index()

        fig, ax = plt.subplots()

        ax.plot(n_customer_first_perchase_month['first_purchase'],
                n_customer_first_perchase_month['customer_unique_id'],
                label='new customer per month')

        ax2 = ax.twinx()
        ax2.plot(revenue['order_purchase_timestamp_month'],
                 revenue['payment_value'], 'g--',
                 label='revenue per month')
        ax.axis('off')
        ax2.axis('off')
    st.pyplot(fig)
    st.write('As expected, the 2 lines follow the same trend')

    # analyse articles bought
    st.subheader('Deeper look into the articles bought')
    with st.echo():
        # merge of product category and product info
        product_info_category = product_info.merge(category_translation, how='left', on="product_category_name")
        # merge product info with order info
        product_info_category_order = products_in_order.merge(product_info_category, how='left', on='product_id')

        all_order_with_customer_history = all_order.merge(customer_summary, how='left', on="customer_unique_id")
        all_order_with_customer_history = all_order_with_customer_history.drop(['order_purchase_timestamp',
                                                                                'order_approved_at',
                                                                                'order_delivered_carrier_date',
                                                                                'order_delivered_customer_date',
                                                                                'order_estimated_delivery_date',
                                                                                'customer_zip_code_prefix',
                                                                                'customer_city',
                                                                                'customer_state', 'order_status',
                                                                                'payment_sequential', 'payment_type',
                                                                                'payment_installments', 'payment_value',
                                                                                'estimated_vs_actual'], axis=1)
        all_order_with_customer_history = all_order_with_customer_history.drop_duplicates()
        all_order_with_customer_history.rename(columns={'total_order_value_x': 'total_order_value'}, inplace=True)
        all_order_info_with_item_customer_info = all_order_with_customer_history.merge(product_info_category_order,
                                                                                       how='left', on="order_id")
        all_order_info_with_item_customer_info['item_total_price'] = \
            all_order_info_with_item_customer_info['price'] + all_order_info_with_item_customer_info['freight_value']

        # look at number of item per order
        items_per_order = all_order_info_with_item_customer_info.groupby(
            ['order_id', 'time_ordered', 'total_order_value']). \
            agg({'product_id': 'count', 'item_total_price': 'mean'}).reset_index()
        items_per_order.columns = ['order_id', 'time_ordered', 'total_order_value', 'num_items', 'avg_price']
        items_by_num_items = items_per_order.groupby(['num_items']).agg({'avg_price': 'mean',
                                                                         'total_order_value': 'mean',
                                                                         'order_id': pd.Series.nunique}).reset_index()
    st.write(items_by_num_items.head())
    st.write('It looks like the average price of item bought is much higher when an user buys only 1 item vs when they '
             'buy more than 1 item.')

    st.subheader('Top selling categories')
    top_selling_cat = all_order_info_with_item_customer_info.groupby('product_category_name_english')['order_id']. \
        count().reset_index()
    top_selling_cat.columns = ['product_category_name_english', 'number of order']
    st.write(top_selling_cat.sort_values('number of order', ascending=False).head())

    st.subheader('Customer satisfaction analysis')
    '''
    As seen previously, the overall retention rate is very low. Therefore, we should analyze more in depth about 
    customers' reviews after the first purchase, to see whether the low retention is caused by 
    our products or our performance of some sort
    '''

    with st.echo():
        # check review by category
        orders_review = all_order_info_with_item_customer_info.merge(order_reviews, how='left', on='order_id')
        orders_review.drop(['review_id', 'review_comment_title', 'review_comment_message', 'review_answer_timestamp'],
                           axis=1)

        review_per_category = orders_review.groupby(['product_category_name_english']). \
            agg({'review_score': ['mean', 'median', 'count', np.std], 'order_id': pd.Series.nunique}). \
            reset_index()
    st.write(review_per_category.head())

    with st.echo():
        # check review change through time
        review_through_time = orders_review.groupby(['order_purchase_timestamp_month']). \
            agg({'review_score': ['mean', 'median', 'count', np.std]}).reset_index()
        review_through_time.tail(10)