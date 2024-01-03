from binance import Client
from tqdm.autonotebook import tqdm
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import json
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import ta
from tqdm import tqdm
from time import sleep

def get_binance_data(ticker, interval, start='1 Jan 2018', end=None):
  client = Client()
  intervals = {
      '15m': Client.KLINE_INTERVAL_15MINUTE,
      '1h':  Client.KLINE_INTERVAL_1HOUR,      
      '4h':  Client.KLINE_INTERVAL_4HOUR,
      '1d':  Client.KLINE_INTERVAL_1DAY,
      '1m':  Client.KLINE_INTERVAL_1MINUTE
  }
  interval = intervals.get(interval)
#   print(f'Historical interval {interval}')
  klines = client.futures_historical_klines(symbol=ticker, interval=interval, start_str=start, end_str=end)
  data = pd.DataFrame(klines)
  data.columns = ['open_time','Open', 'High', 'Low', 'Close', 'Volume','close_time', 'qav','num_trades','taker_base_vol','taker_quote_vol', 'ignore']
 
  data.index = [(
                    pd.to_datetime(x, unit='ms') - pd.Timedelta(hours=4)
                ).strftime('%Y-%m-%d %H:%M:%S') for x in data.open_time
               ]

  usecols=['Open', 'High', 'Low', 'Close', 'Volume', 'qav','num_trades','taker_base_vol','taker_quote_vol']
  data = data[usecols]
  data = data.astype('float')
  return data

def get_data_yf(symbol,interval, start_date=None, end_date=None):
    if start_date is None:
        if interval == '1m':
            end_date = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
            start_date = end_date - pd.DateOffset(days=7)
            days = 7
    
        elif interval in ['2m', '5m','10m', '15m', '30m']:
            end_date = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
            aux = 0
            while end_date.dayofweek > 4:
                end_date -= pd.DateOffset(days=1)
                aux += 1
            start_date = end_date - pd.DateOffset(days=59 - aux)
            days = 59
            
        elif interval in ['60m', '90m', '1h']:
            end_date = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
            aux = 0
            while end_date.dayofweek > 4:
                end_date -= pd.DateOffset(days=1)
                aux += 1
            start_date = end_date - pd.DateOffset(days=720 - aux)
            days = 720
    
        elif interval == '1d':
            end_date = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
            start_date = end_date - pd.DateOffset(days=756)
            days = 756
    
        elif interval == '1wk':
            end_date = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
            start_date = end_date - pd.DateOffset(days=1260)
            days = 1260
    
        elif interval == '1mo':
            end_date = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
            start_date = end_date - pd.DateOffset(days=2520)
            days = 2520
    
        elif interval == '3mo':
            end_date = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
            start_date = end_date - pd.DateOffset(days=7560)
            days = 7560

    if interval=='10m':
        interval1 = '5m'
    else:
        interval1 = interval
    
    data1 = yf.download(symbol, start=start_date, end=end_date, interval=interval1)
    if interval=='10m':
        # Cambiar la frecuencia a 10 minutos usando resample
        data1 = data1['Close'].resample('10T').ohlc()
        data1.columns = [x.capitalize() for x in data1.columns]
        
    return data1, days

colors = ['#00FF00', '#FF0000', '#FFFF00', '#0000FF', '#FFA500','#FF0000']
def plot_strategy_jemir(data1, symbol, volume_df, poc_price, interval, threshold_adx):
    fig=make_subplots( 
                    rows = 2,
                    cols=2,
                    shared_xaxes = True,
                    row_heights=[0.7, 0.3],
                    vertical_spacing = 0.06,
    specs=[[{"secondary_y": True}, {"secondary_y": False}], [{"colspan": 2}, None]])
    
    fig.update_layout(xaxis2= {'anchor': 'y', 'overlaying': 'x', 'side': 'top'}, xaxis_domain=[0, 0.94]);
    
    fig.add_trace(go.Candlestick(
                    x = data1.index,
                    open = data1['Open'],
                    high = data1['High'],
                    low = data1['Low'],
                    close = data1['Close'],
                    name=f'Precio de {symbol}' 
                    ),
                    col=1,
                    row=1,
                     secondary_y = False,
                     )
    
    # fig.add_trace( go.Bar(x=[1, 2, 3, 4], y=[7, 4, 5, 6], name='bar', orientation = 'h',opacity = 0.5), secondary_y=True)
    # Agregar el gráfico de barras de volumen en la segunda columna (encima del gráfico de velas)
    volume_bars_trace = go.Bar(
        y=volume_df['Close'],
        x=volume_df['Frecuency'],
        orientation='h',
        name='Volumen',
        opacity = 0.2
    )
    fig.add_trace(volume_bars_trace, secondary_y=True, col=1,row=1)
    
    fig.add_trace(
        go.Scatter(
        x= data1.index, 
        y=data1[f'{symbol}_ADX'],
        line = dict(color='green',width=2),
         name=f'{symbol}_ADX'
        ),
        col=1,
        row=2
        )
    
    fig.add_trace(go.Scatter(
            x=data1[data1['Open_position'] == 1].index,
            y=data1['Close'][data1['Open_position'] == 1],
            mode= 'markers',
            name = 'Compra',
            marker=dict(
                size=15,
                color='black',
                symbol='star-triangle-up'
            )
                                  ),
                  
                  col=1,
                  row=1
        )
    for i in range(2,6):
        fig.add_trace(go.Scatter(
                    x=data1[data1['Open_position'] == i].index,
                    y=data1['Close'][data1['Open_position'] == i],
                    mode= 'markers',
                    name = f'Safety Order {i-1}',
                    marker=dict(
                        size=15,
                        color= colors[i],
                        symbol='star-triangle-up'
                    )
                                          ),
                          
                          col=1,
                          row=1
                )

    # Ploteando Señales de VENTA
    fig.add_trace(go.Scatter(
        x=data1[data1['Short_Exit'] == 1].index,
        y=data1['Close'][data1['Short_Exit'] == 1],
        mode= 'markers',
        name = 'Venta',
        marker=dict(
            size=15,
            color='cyan',
            symbol='star-triangle-down'
        )
                              ),
                  col = 1,
                  row = 1
    )

    fig.add_trace(
    go.Scatter(
    x= data1.index, 
    y=data1['EMA_55'],
    line = dict(color='orange',width=2),
     name='EMA 55'
    ),
    col=1,
    row=1
    )

    # Add a horizontal line with title to exit_ind plot
    fig.add_shape(
        type="line",
        x0=min(data1.index),
        x1=max(data1.index),
        y0=threshold_adx,
        y1=threshold_adx,
        line=dict(color="red", width=2, dash="dash"),
        col=1,
        row=2
    )
    
    fig.add_shape(
        type="line",
        x0=min(data1.index),
        x1=max(data1.index),
        y0=poc_price,
        y1=poc_price,
        line=dict(color="green", width=3, dash="dash"),
        col=1,
        row=1
    )

    # Agrega la imagen en el encabezado
    fig.add_layout_image(
        source='Documents/git_repo/zenit_backtesting/',
        x=0,  # Coordenada x en la que deseas ubicar la imagen
        y=1,  # Coordenada y en la que deseas ubicar la imagen
        xref='paper',
        yref='paper',
        sizex=0.2,  # Ancho de la imagen (ajusta según tus necesidades)
        sizey=0.2,  # Alto de la imagen (ajusta según tus necesidades)
        opacity=1.0
    )
    
    fig.data[1].update(xaxis='x2')
    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_layout(width=1100, height=800)
    fig.update_layout(title=f"Estrategia aplicada a {symbol} en el intervalo {interval}")
    return fig

def calcular_ema(data, window):
    return data['Close'].ewm(span=window, adjust=False).mean()

def estrategia_trading(data,symbol, threshold_adx):
    data['EMA5'] = calcular_ema(data, 5)
    data['EMA12'] = calcular_ema(data, 12)
    data['EMA34'] = calcular_ema(data, 34)
    data['EMA50'] = calcular_ema(data, 50)

     # Calcular el ADX 
    adx = ta.trend.ADXIndicator(data['High'], data['Low'], data['Close'], window=14, fillna=True)
    data[f'{symbol}_ADX'] = adx.adx().rolling(window=3).mean()
    
    # Calcular Bollinger Bands
    data['Bollinger_Upper'] = ta.volatility.bollinger_hband(data['Close'], window=20)
    data['Bollinger_Lower'] = ta.volatility.bollinger_lband(data['Close'], window=20)
    
    # Calcular Keltner Channels (usando ATR)
    data['ATR'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window=20)
    data['Keltner_Upper'] = data['Bollinger_Upper'] + 1.5 * data['ATR']
    data['Keltner_Lower'] = data['Bollinger_Lower'] - 1.5 * data['ATR']
    
    # Calcular el Squeeze Momentum Indicator (SMI)
    data['SMI'] = 100 * (data['Bollinger_Upper'] - data['Bollinger_Lower']) / data['Keltner_Upper']
    
    # Calcular estadísticas del SMI para definir umbrales
    smi_mean = data['SMI'].mean()
    smi_min = data['SMI'].min()
    smi_max = data['SMI'].max()
    
    # Definir umbrales en función de las estadísticas del SMI
    threshold_force_bearish = smi_mean - (smi_max - smi_mean) * 0.25
    threshold_momentum_bullish = smi_mean + (smi_max - smi_mean) * 0.1
    threshold_force_bullish = smi_mean + (smi_max - smi_mean) * 0.25
    threshold_momentum_bearish = smi_mean - (smi_max - smi_mean) * 0.1
    
    # Determinar fases en función de los umbrales
    data['Squeez_Momentum_Phase'] = 'No Phase'
    data.loc[data['SMI'] < threshold_force_bearish, 'Squeez_Momentum_Phase'] = 'Impulso Bajista'
    data.loc[(data['SMI'] >= threshold_force_bearish) & (data['SMI'] < threshold_momentum_bearish), 'Squeez_Momentum_Phase'] = 'Fuerza Bajista'
    data.loc[(data['SMI'] >= threshold_force_bullish) & (data['SMI'] < threshold_momentum_bullish), 'Squeez_Momentum_Phase'] = 'Fuerza Alcista'
    data.loc[(data['SMI'] >= threshold_momentum_bearish) & (data['SMI'] <= threshold_momentum_bullish), 'Squeez_Momentum_Phase'] = 'Impulso Alcista'
        
    # Utilizar los precios de cierre para calcular el Volume Profile
    prices = data['Close'].to_numpy()
    
    # Calcular el Volume Profile
    hist, bins = np.histogram(prices, bins=20)
    
    # Encontrar el índice del bin con la frecuencia máxima (POC)
    poc_index = np.argmax(hist)
    
    # DataFrame de Volumen con frecuencia
    volume_df = pd.DataFrame({'Close':bins[:-1], 'Frecuency': hist})
    
    # Calcular el precio del POC
    poc_price = (bins[poc_index] + bins[poc_index + 1]) / 2
    
    ##################################################
    # Estrategia
    #################################################
    # Calcular indicadores necesarios
    data['Visible_Range_POC'] = poc_price # Calcula el POC del Visible Range Volume Profile según tu método
    

    
    # Señales de trading
    data['Long_Signal'] = np.where(
                                    (data['EMA5'] > data['EMA12']) & 
                                    (data['EMA5'] > data['EMA34']) & 
                                    (data['EMA34'] > data['EMA50']) &
                                    (data[f'{symbol}_ADX'] > threshold_adx) &
                                    (data['Squeez_Momentum_Phase'] == 'Impulso Alcista') &
                                    ((data['Close'] > data['Visible_Range_POC']) |
                                    (data['Close'] < data['Visible_Range_POC'])),1,0)
    data['Short_Signal'] = np.where(
                                    (data['EMA5'] < data['EMA12']) & 
                                    (data['EMA5'] < data['EMA34']) & 
                                    (data['EMA34'] < data['EMA50']) &
                                    (data[f'{symbol}_ADX'] < threshold_adx) &
                                    (data['Squeez_Momentum_Phase'] == 'Fuerza Bajista') &
                                    ((data['Close'] > data['Visible_Range_POC']) |
                                    (data['Close'] < data['Visible_Range_POC'])),1,0)

    return data, volume_df, poc_price
    
def graficar_estrategia(data, symbol, volume_df, poc_price, interval, threshold_adx):
    fig=make_subplots( 
                    rows = 2,
                    cols=2,
                    shared_xaxes = True,
                    row_heights=[0.7, 0.3],
                    vertical_spacing = 0.06,
    specs=[[{"secondary_y": True}, {"secondary_y": False}], [{"colspan": 2}, None]])
    
    fig.update_layout(xaxis2= {'anchor': 'y', 'overlaying': 'x', 'side': 'top'}, xaxis_domain=[0, 0.94]);
    
    fig.add_trace(go.Candlestick(
                    x = data.index,
                    open = data['Open'],
                    high = data['High'],
                    low = data['Low'],
                    close = data['Close'],
                    name=f'Precio de {symbol}' 
                    ),
                    col=1,
                    row=1,
                     secondary_y = False,
                     )
    volume_bars_trace = go.Bar(
        y=volume_df['Close'],
        x=volume_df['Frecuency'],
        orientation='h',
        name='Volumen',
        opacity = 0.2
    )
    fig.add_trace(volume_bars_trace, secondary_y=True, col=1,row=1)
    
    fig.add_trace(
        go.Scatter(
        x= data.index, 
        y=data[f'{symbol}_ADX'],
        line = dict(color='green',width=2),
         name=f'{symbol}_ADX'
        ),
        col=1,
        row=2
        )
    
    
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA5'], mode='lines', name='EMA 5', line_shape='spline'))
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA12'], mode='lines', name='EMA 12', line_shape='spline'))
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA34'], mode='lines', name='EMA 34', line_shape='spline'))
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], mode='lines', name='EMA 50', line_shape='spline'))

    fig.add_trace(go.Scatter(x=data['Close'][data['long_position']==1].index, y=data['Close'][data['long_position']==1], mode='markers', marker=dict(color='black', size=10, symbol ='star-triangle-up'), name='Long Signal'))
    fig.add_trace(go.Scatter(x=data['Close'][data['short_position']==1].index, y=data['Close'][data['short_position']==1], mode='markers', marker=dict(color='cyan', size=10, symbol='star-triangle-down'), name='Short Signal'))
    # Add a horizontal line with title to exit_ind plot
    fig.add_shape(
        type="line",
        x0=min(data.index),
        x1=max(data.index),
        y0=threshold_adx,
        y1=threshold_adx,
        line=dict(color="red", width=2, dash="dash"),
        col=1,
        row=2
    )
    
    fig.add_shape(
        type="line",
        x0=min(data.index),
        x1=max(data.index),
        y0=poc_price,
        y1=poc_price,
        line=dict(color="green", width=3, dash="dash"),
        col=1,
        row=1
    )
    fig.update_layout(title=f'Estrategia de Trading aplicada a {symbol} en el intervalo {interval}', xaxis_title='Fecha', yaxis_title='Precio')
    fig.update_layout(width=1100, height=800)
    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.data[1].update(xaxis='x2')
    #fig.show()
    return fig
    
def strategy_metrics(data, 
                     symbol, 
                     interval, 
                     quantity, 
                     threshold_adx, 
                     tp, 
                     days, 
                     trade_type='long'):

    
    data, volume_df, poc_price = estrategia_trading(data, symbol, threshold_adx)
    
    # Calcular la volatilidad
    daily_returns = data['Close'].pct_change().dropna()  # Calcular los retornos diarios
    volatility = daily_returns.std()/days # Calcular la volatilidad anualizada (252 días hábiles)
    
     # Capital inicial y variables de posición abierta
    initial_capital = 100000  
    open_position = False
    open_trade_price = 0
    total_volume = 0
    average_purchase_price = 0
    operations = 0
    successful_trades = 0
    profitable_trades = 0
    total_profit = 0
    data['Short_Exit'] = 0
    data['Open_position'] = 0
    risk_free_rate = 0.02
    profit_dict = {'price':[], 'profit':[], 'time':[]}
    loss_dict = {'price':[], 'loss':[], 'time':[]}
    trades_info = {'action':[], 'time':[], 'price':[]}
    cant_cont = 0 # Cantidad de contratos adquiridos
    active_safety_orders = 0 # ordenes seguras activas
    cap_final = initial_capital
    cont_ven = 0
    
    data['long_position'] = 0
    data['short_position'] = 0
    position = False
    for index, row in data.iterrows():
        current_price = row['Close']
        if trade_type == 'long':
            if not position and row['Long_Signal'] == 1 and (row['Close'] >= row['EMA5']):
                open_price = row['Close']
                data.loc[index, 'long_position'] = 1
                position = True
                cant_cont += quantity
                # Restamos el monto de la compra del contrato al capital inicial
                cap_final = cap_final - (open_price * quantity)
                trades_info['action'].append('Buy')
                trades_info['time'].append(index)
                trades_info['price'].append(open_price)
                #print(f"Opened long position at price {open_trade_price}.")
    
            # Toma de ganancias
            elif (position and (row['Close'] > row['EMA5']) and 
                     (row['Close'] > open_price * (1 + tp) or row['High'] > open_price * (1 + tp))
                     ):
                data.loc[index, 'short_position'] = 1
                position = False
                operations += 1
                contracts_to_sell = cant_cont
                
                cont_ven += contracts_to_sell
                contracts_to_keep = cant_cont - contracts_to_sell
                cant_cont = 0
                #print(f'se vendieron {contracts_to_sell} quedan {cant_cont}')
                cap_final += current_price * quantity
                
                #print(f"Closed long position at price {current_price} based take profit.")
                profit_dict['price'].append(open_price)
                profit_dict['profit'].append(current_price)
                trade_profit = (current_price - open_price) / open_price
                #print(f'trade profit {trade_profit}')
                total_profit += trade_profit
                active_safety_orders = 0
                trades_info['action'].append('Sell')
                trades_info['time'].append(index)
                trades_info['price'].append(open_price)
                if trade_profit > 0:
                    successful_trades += 1
    
            # 1 Close Criteria
            elif (position and (row['Close'] < row['EMA50']) and 
                     (row['Close'] <= open_price * (1 - tp))
                     ):
                data.loc[index, 'short_position'] = 1
                position = False
                operations += 1
                contracts_to_sell = cant_cont
                
                cont_ven += contracts_to_sell
                contracts_to_keep = cant_cont - contracts_to_sell
                cant_cont = 0
                #print(f'se vendieron {contracts_to_sell} quedan {cant_cont}')
                cap_final += current_price * quantity
                
                #print(f"Closed long position at price {current_price} based take profit.")
                profit_dict['price'].append(open_price)
                profit_dict['profit'].append(current_price)
                trade_profit = (current_price - open_price) / open_price
                #print(f'trade profit {trade_profit}')
                total_profit += trade_profit
                active_safety_orders = 0
                trades_info['action'].append('Sell')
                trades_info['time'].append(index)
                trades_info['price'].append(open_price)
                if trade_profit > 0:
                    successful_trades += 1

            # 2 Close Criteria
            elif (position and (row['EMA5'] < row['EMA12']) and 
                     (row['Close'] <= open_price * (1 - tp))
                     ):
                data.loc[index, 'short_position'] = 1
                position = False
                operations += 1
                contracts_to_sell = cant_cont
                
                cont_ven += contracts_to_sell
                contracts_to_keep = cant_cont - contracts_to_sell
                cant_cont = 0
                #print(f'se vendieron {contracts_to_sell} quedan {cant_cont}')
                cap_final += current_price * quantity
                
                #print(f"Closed long position at price {current_price} based take profit.")
                profit_dict['price'].append(open_price)
                profit_dict['profit'].append(current_price)
                trade_profit = (current_price - open_price) / open_price
                #print(f'trade profit {trade_profit}')
                total_profit += trade_profit
                active_safety_orders = 0
                trades_info['action'].append('Sell')
                trades_info['time'].append(index)
                trades_info['price'].append(open_price)
                if trade_profit > 0:
                    successful_trades += 1
                    
        elif trade_type == 'short':
            if not position and row['Short_Signal'] == 1 and (row['Close'] <= row['EMA5']):
                open_price = row['Close']
                data.loc[index, 'short_position'] = 1
                position = True
                cant_cont += quantity
                # Restamos el monto de la compra del contrato al capital inicial
                cap_final = cap_final - (open_price * quantity)
                trades_info['action'].append('Buy')
                trades_info['time'].append(index)
                trades_info['price'].append(open_price)
                #print(f"Opened long position at price {open_trade_price}.")
    
            # Toma de ganancias
            elif (position and (row['Close'] < row['EMA5']) and 
                     (row['Close'] < open_price * (1 - tp))
                     ):
                data.loc[index, 'long_position'] = 1
                position = False
                operations += 1
                contracts_to_sell = cant_cont
                
                cont_ven += contracts_to_sell
                contracts_to_keep = cant_cont - contracts_to_sell
                cant_cont = 0
                #print(f'se vendieron {contracts_to_sell} quedan {cant_cont}')
                cap_final += current_price * quantity
                
                #print(f"Closed long position at price {current_price} based take profit.")
                profit_dict['price'].append(open_price)
                profit_dict['profit'].append(current_price)
                trade_profit =  (open_price - current_price) / current_price
                #print(f'trade profit {trade_profit}')
                total_profit += trade_profit
                active_safety_orders = 0
                trades_info['action'].append('Sell')
                trades_info['time'].append(index)
                trades_info['price'].append(open_price)
                if trade_profit > 0:
                    successful_trades += 1
    
            # 1 Close Criteria
            elif (position and (row['Close'] > row['EMA50']) and 
                     (row['Close'] >= open_price * (1 - tp))
                     ):
                data.loc[index, 'long_position'] = 1
                position = False
                operations += 1
                contracts_to_sell = cant_cont
                
                cont_ven += contracts_to_sell
                contracts_to_keep = cant_cont - contracts_to_sell
                cant_cont = 0
                #print(f'se vendieron {contracts_to_sell} quedan {cant_cont}')
                cap_final += current_price * quantity
                
                #print(f"Closed long position at price {current_price} based take profit.")
                profit_dict['price'].append(open_price)
                profit_dict['profit'].append(current_price)
                trade_profit = (open_price - current_price) / current_price
                #print(f'trade profit {trade_profit}')
                total_profit += trade_profit
                active_safety_orders = 0
                trades_info['action'].append('Sell')
                trades_info['time'].append(index)
                trades_info['price'].append(open_price)
                if trade_profit > 0:
                    successful_trades += 1
                    
            # 2 Close Criteria
            elif (position and (row['EMA5'] > row['EMA12']) and 
                     (row['Close'] >= open_price * (1 - tp))
                     ):
                data.loc[index, 'long_position'] = 1
                position = False
                operations += 1
                contracts_to_sell = cant_cont
                
                cont_ven += contracts_to_sell
                contracts_to_keep = cant_cont - contracts_to_sell
                cant_cont = 0
                #print(f'se vendieron {contracts_to_sell} quedan {cant_cont}')
                cap_final += current_price * quantity
                
                #print(f"Closed long position at price {current_price} based take profit.")
                profit_dict['price'].append(open_price)
                profit_dict['profit'].append(current_price)
                trade_profit = (open_price - current_price) / current_price
                #print(f'trade profit {trade_profit}')
                total_profit += trade_profit
                active_safety_orders = 0
                trades_info['action'].append('Sell')
                trades_info['time'].append(index)
                trades_info['price'].append(open_price)
                if trade_profit > 0:
                    successful_trades += 1
       
        
    # Calcular métricas generales
    total_trades = successful_trades + (operations - successful_trades)
    win_rate = successful_trades / total_trades if total_trades > 0 else 0
    profit_factor = total_profit if total_profit > 0 else 0
    
    # Calcular el capital final y el apalancamiento
    final_capital = initial_capital + (total_profit * initial_capital * quantity)
    # Calcular el apalancamiento en términos de porcentaje
    leverage_percentage = (total_profit / initial_capital) * 100
    # Calcula el drawdown y el drawdown máximo
    cumulative_max = data['Close'].cummax()
    drawdown = (data['Close'] - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()
    average_trade_duration = total_trades / len(data)
    
    # Calcula los rendimientos diarios
    data['Daily_Return'] = data['Close'].pct_change()
    
    # Calcula el rendimiento promedio y la desviación estándar de los rendimientos diarios
    average_daily_return = data['Daily_Return'].mean()
    std_daily_return = data['Daily_Return'].std()
    
    # Calcula el Sharpe Ratio
    sharpe_ratio = (average_daily_return - risk_free_rate) / std_daily_return
    
    
    average_win_duration = successful_trades / total_trades * average_trade_duration
    average_loss_duration = (total_trades - successful_trades) / total_trades * average_trade_duration
    profitable_percentage = profitable_trades / total_trades * 100
    
    cont_com = cant_cont + cont_ven
    metrics = {
        'total_trades':total_trades,
        'win_rate':win_rate,
        'profit_factor':profit_factor,
        'final_capital':final_capital,
        'leverage_percentage':leverage_percentage,
        'successful_trades':successful_trades,
        'drawdown':drawdown,
        'max_drawdown':max_drawdown,
        'average_trade_duration':average_trade_duration,
        'sharpe_ratio':sharpe_ratio,
        'average_win_duration':average_win_duration,
        'average_loss_duration':average_loss_duration,
        'profitable_percentage':profitable_percentage,
        'capital_final': cap_final,
        'contratos_adquiridos':cont_com,
        'contratos_vendidos': cont_ven,
        'contratos_posesion': cant_cont,
        'Volatilidad_TP': volatility
    }
    return data, metrics, volume_df, poc_price
    
def get_data(symbol, interval, source='binance'):
    if source=='binance':
        threshold_adx = 20
        # Obtener la fecha actual
        fecha_actual = datetime.now()
        if interval == '15m':
            days = 6
        elif interval == '1m': 
            days = 3
        else: 
            days = 30
            
        fecha_actual = fecha_actual - timedelta(days)
        # Formatear la fecha en el formato deseado
        fecha_formateada = fecha_actual.strftime("%d %b %Y")
        
        data = get_binance_data(symbol, interval, fecha_formateada)
    else:
        threshold_adx = 23
        data, days = get_data_yf(symbol,interval)
        
    return data, days, threshold_adx

def backtest_results(lis_simbol, l_tp, trade_types, intervals, quantity):
    results_list = []
    
    for symbol in lis_simbol:
        for trade_type in trade_types:
            for interval in intervals:
                data, days, threshold_adx = get_data(symbol, interval)
                for tp in tqdm(l_tp, desc=f"Processing {symbol}, {trade_type}, {interval}"):
                    try:
                        data, metrics, volume_df, poc_price = strategy_metrics(data, symbol, interval, quantity, threshold_adx,tp, days, trade_type)
                        fig = graficar_estrategia(data, symbol, volume_df, poc_price, interval, threshold_adx)
                        win_rate = round(metrics['win_rate'], 3)
                        profit_factor = round(metrics['profit_factor'], 5)
                        results_list.append({
                            'symbol': symbol,
                            'trade_type': trade_type,
                            'interval': interval,
                            'tp': tp,
                            'win_rate': win_rate,
                            'profit_factor': profit_factor,
                            'total_trades': metrics['total_trades'],
                            'fig': fig
                        })
                    except:
                        continue
    df_results = pd.DataFrame(results_list)
    return df_results

def best_profit(df_results):
    df_most_profit = df_results.loc[df_results.groupby('symbol')['profit_factor'].idxmax()].reset_index(drop=True)
    return df_most_profit