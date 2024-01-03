#!/bin/bash
# Set the title (if applicable)
# Title LONG 100 EMAS1055 ES 1m Bot account

# Set environment variables
python_file="trading_functions/zenit-EMAS-strategy.py"
port="7497"
symbol="MESZ3"
exchange="CME"
secType="FUT"
account="DU7774793"
client="98"
is_paper="True"
order_type="MARKET"
interval="1m"
trading_class="MES"
multiplier="5"
accept_trade="long100"

# Execute the Python script with specified parameters
python "$python_file" --port "$port" --symbol "$symbol" --exchange "$exchange" --secType "$secType" --accept_trade "$accept_trade" --account "$account" --client "$client" --is_paper "$is_paper" --order_type "$order_type" --interval "$interval" --trading_class "$trading_class" --multiplier "$multiplier"
