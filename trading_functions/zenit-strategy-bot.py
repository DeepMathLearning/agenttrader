from api_interface import Main, BarData, PriceInformation, str_to_bool, convert_date_time
import datetime
import time
from threading import Timer
import argparse
import logging
import pandas as pd
import numpy as np
import pytz
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots
import yfinance as yf
import ta
from tqdm import tqdm
from openorder import orden_status

logger = logging.getLogger()
logging.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=logging.INFO)

class BotZenitTrendMaster(Main):

    def __init__(self, 
                ip, 
                port, 
                client, 
                symbol, 
                secType, 
                currency, 
                exchange, 
                quantity,  
                stop_limit_ratio,    
                max_safety_orders, 
                safety_order_size, 
                volume_scale,
                safety_order_deviation,  
                account,
                take_profit_percent,
                interval,
                accept_trade,
                threshold_adx,
                multiplier,
                trading_class,
                lastTradeDateOrContractMonth,
                order_type="LIMIT", 
                order_validity="DAY",
                is_paper=True
                 ):
        Main.__init__(self, ip, port, client)
        self.action1 = "BUY"
        self.action2 = "SELL"
        self.ip = ip
        self.port = port
        self.interval = interval
        self.bar_size = self.convert_to_seconds()
        self.historical_bar_size = "{} secs".format(self.bar_size)
        self.is_paper = is_paper
        self.prices = pd.Series() 
        self.start_time = lambda: datetime.datetime.combine(datetime.datetime.now().date(), datetime.time(9))
        self.stop_time = lambda: datetime.datetime.combine(datetime.datetime.now().date(), datetime.time(17))
        self.pnl_time = lambda: datetime.datetime.combine(datetime.datetime.now().date(), datetime.time(15, 1))
        self.account = account
        self.quantity = quantity
        self.contract = self.CONTRACT_CONFIG()
        self.contract.symbol = symbol
        self.contract.secType = secType
        self.contract.currency = currency
        self.contract.exchange = exchange
        if secType == 'FUT':
            self.contract.multiplier = multiplier
            self.contract.tradingClass = trading_class
            self.contract.lastTradeDateOrContractMonth = lastTradeDateOrContractMonth
        self.min_tick = 0.00005
        self.reqContractDetails(10004, self.contract)
        self.take_profit_percent = take_profit_percent
        self.required_take_profit = 0

        #risk indicators
        self.trades_today = 0 # 
        self.today = datetime.datetime.now().date() # 
        self.open_positions = 0 # 

        self.order_type = order_type

        #para el punto 9
        self.stop_limit_ratio = stop_limit_ratio
        self.trailing_stop = None
        self.break_even_triggered = False
        self.order_id = None


        self.order_id_tp = None

        #para el punto 11
        self.max_safety_orders = max_safety_orders
        #self.max_safety_orders = 4
        self.safety_order_size = safety_order_size
        self.volume_scale = volume_scale
        self.safety_order_deviation = safety_order_deviation
        self.active_safety_orders = 0
        self.total_volume = 0
        self.average_purchase_price = 0
        self.hora_ejecucion = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if self.contract.secType == 'FUT':
            self.symbol = self.contract.tradingClass
        else:
            self.symbol = self.contract.symbol

        # Datos para la estrategia
        self.accept_trade = accept_trade
        self.orders_info = {
            "safety_orders": {
                "1h": {
                    'so_1': 0.0005,
                    'so_2': 0.0010,
                    'so_3': 0.0015,
                    'so_4': 0.0020,
                },
                "1d": {
                    "so_1": 0.004,
                    "so_2": 0.008,
                    "so_3": 0.012,
                    "so_4": 0.016,
                },
                "1wk": {
                    "so_1": 0.0088,
                    "so_2": 0.0176,
                    "so_3": 0.0264,
                    "so_4": 0.0352,
                },
                "15m": {
                    "so_1": 0.0006,
                    "so_2": 0.0012,
                    "so_3": 0.0018,
                    "so_4": 0.0024,
                },
                "1m": {
                    "so_1": 0.0002,
                    "so_2": 0.0004,
                    "so_3": 0.0006,
                    "so_4": 0.0008,
                },
            },
            "contracts": {
                "1h": {
                    "so_1": 3,
                    "so_2": 1,
                    "so_3": 0,
                    "so_4": 0,
                },
                "1d": {
                    "so_1": 1,
                    "so_2": 2,
                    "so_3": 2,
                    "so_4": 2,
                },
                "1wk": {
                    "so_1": 1,
                    "so_2": 2,
                    "so_3": 2,
                    "so_4": 2,
                },
                "15m": {
                    "so_1": 2,
                    "so_2": 1,
                    "so_3": 1,
                    "so_4": 1,
                },
                "1m": {
                    "so_1": 3,
                    "so_2": 1,
                    "so_3": 0,
                    "so_4": 0,
                },
            },
            "stops": {
                "1h": 0.001,
                "1d": 0.008,
                "1wk": 0.0175,
                "15m": 0.0006,
                "1m": 0.0006,
            },
        }
        self.stop_loss_percent = self.orders_info['stops'][self.interval]
        # Finance data
        self.fdata = None
        self.volume_df = None
        self.poc_price = None
        self.dict_metrics = None
        self.profit_dict = {'price':[], 'profit':[], 'time':[]}
        self.loss_dict = {'price':[], 'loss':[], 'time':[]}
        self.trades_info = {'action':[], 'time':[], 'price':[]}
        # Definir umbrales y condiciones
        self.threshold_adx = 23

        self.order_n1 = self.orders_info['contracts'][self.interval]['so_1']
        self.order_n2 = self.orders_info['contracts'][self.interval]['so_2']
        self.order_n3 = self.orders_info['contracts'][self.interval]['so_3']
        self.order_n4 = self.orders_info['contracts'][self.interval]['so_4']
        self.orderSum = int(self.quantity) + self.order_n1 + self.order_n2 + self.order_n3 + self.order_n4
        # Position
        self.open_position = False

        # Capital inicial y variables de posición abierta
        self.open_trade_price = 0
        self.open_trade_price1 = 0
        self.open_trade_price2 = 0
        self.open_trade_price3 = 0
        self.open_trade_price4 = 0
        self.operations = 0
        self.successful_trades = 0
        self.profitable_trades = 0
        self.total_profit = 0
        self.risk_free_rate = 0.02
        self.cant_cont = 0 # Cantidad de contratos adquiridos
        self.cont_ven = 0
        self.stoploss_activate = False

        # Candle graph
        self.colors = ['#00FF00', '#FF0000', '#FFFF00', '#0000FF', '#FFA500','#FF0000']
        self.figure = None

        self.order_validity = order_validity
        self.current_price = 0
        self.positions1 = {}
        self.plot_div = None


    def main(self):
        self.initial_balance = self.get_account_balance()
        self.highest_balance = self.initial_balance
        logger.info(f"Initical balance {self.initial_balance}")
        # if datetime.datetime.now() < self.start_time():
        #     seconds_to_wait = (self.start_time() - datetime.datetime.now()).total_seconds()
        #     Timer(seconds_to_wait, self.main).start()
        #     logger.info("Starting later today at: {}".format(self.start_time().time()))
        #     return None

        seconds_to_wait = (self.start_time() - datetime.datetime.now() + datetime.timedelta(days=1)).total_seconds()
        Timer(seconds_to_wait, self.main).start()

        # if datetime.datetime.now().weekday() in [5, 6]:
        #     logging.info("It's the weekend, no trading today")
        #     return None

        seconds_to_wait = (self.pnl_time() - datetime.datetime.now()).total_seconds()
        Timer(seconds_to_wait, self.get_pnl).start()

        if not self.isConnected():
            self.reconnect()
        unique_id = self.get_unique_id()
        logger.info('unique_id',unique_id)
        self.market_data[unique_id] = PriceInformation(self.contract)
        
        if self.is_paper:
            self.reqMarketDataType(3)  # Delayed data
        else:
            self.reqMarketDataType(1)  # Live data

        self.reqMktData(unique_id, self.contract, "", False, False, [])
        self.loop(unique_id)
        self.cancelMktData(unique_id)

    def loop(self, req_id):
        
        while True:
            # time.sleep(self.bar_size)
            logger.info(f'Esperando {self.bar_size} segundos para agregar precios')
            #self.buy(self.open_trade_price, float(self.quantity), "MARKET")
            
            # Bid Price y Ask Price durante un minuto
            try:
                # Obtén la hora actual
                hora_actual = time.localtime()
                segundos_actuales = hora_actual.tm_sec

                # Calcula cuántos segundos quedan hasta el próximo minuto exacto
                segundos_hasta_siguiente_minuto = self.bar_size - segundos_actuales

                # Determina cuánto tiempo durará el bucle en este ciclo
                tiempo_de_espera = min(self.bar_size, segundos_hasta_siguiente_minuto)
                datos_prices = []
                for i in tqdm(range(tiempo_de_espera)):
                    time.sleep(1)
                    try:
                        if self.is_paper:
                            price = (self.market_data[req_id].DelayedBid + self.market_data[req_id].DelayedAsk) / 2
                            market_price = self.market_data[req_id].DelayedAsk
                            sell_market_price = self.market_data[req_id].DelayedBid
                            vol = self.market_data[req_id].DelayedVolume
                        else:
                            print('LIVE DATA')
                            price = (self.market_data[req_id].Bid + self.market_data[req_id].Ask) / 2
                            market_price = self.market_data[req_id].Ask 
                            sell_market_price = self.market_data[req_id].Bid
                            vol = self.market_data[req_id].NotDefined
                        logger.info(f'PRECIO ------------> ${price}')
                        logger.info(f'PRECIO DE MERCADO--> ${market_price}')
                        datos_prices.append(price)

                        # Para cerrar el proceso en caso de existir algunas de estas condiciones
                        if self.open_position and (self.average_purchase_price > 0) and (price > (1 + self.take_profit_percent) * self.average_purchase_price):
                            logger.info('SE HA ENCONTRADO PRECIO ARRIBA DE LA POSICIÓN TOMADA')
                            break
                        elif self.open_position and (self.cant_cont > 0) and (self.active_safety_orders <= self.max_safety_orders):
                            if (self.active_safety_orders == 0) and (price < self.average_purchase_price * (1-self.orders_info['safety_orders'][self.interval]['so_1'])):
                                logger.info('CONDICIONES DE SAFETY ORDER 1')
                                break
                            elif (self.active_safety_orders == 1) and (price < self.average_purchase_price * (1-self.orders_info['safety_orders'][self.interval]['so_2'])):
                                logger.info('CONDICIONES DE SAFETY ORDER 2')
                                break 
                            elif (self.active_safety_orders == 2) and (price < self.average_purchase_price * (1-self.orders_info['safety_orders'][self.interval]['so_3'])):
                                logger.info('CONDICIONES DE SAFETY ORDER 3')
                                break
                            elif (self.active_safety_orders == 3) and (price < self.average_purchase_price * (1-self.orders_info['safety_orders'][self.interval]['so_4'])):
                                logger.info('CONDICIONES DE SAFETY ORDER 4')
                                break
                        if self.open_position and (self.stoploss_activate) and (price < ((1 - self.stop_loss_percent) * self.average_purchase_price)):
                            logger.info('CONDICIONES STOP LOSS')
                            break

                    except TypeError:
                        logger.info(f"Error TypeError, the price is None")

                new_price_info = pd.DataFrame({
                        'Open':[datos_prices[0]], 
                        'High':[max(datos_prices)], 
                        'Low':[min(datos_prices)], 
                        'Close':[datos_prices[-1]], 
                        'Adj Close':[datos_prices[-1]], 
                        'Volume':[vol],
                        },
                        index=[self.redondear_marca_de_tiempo(str(datetime.datetime.now()- datetime.timedelta(minutes=1)))])
                new_price_info['Short_Exit'] = 0
                new_price_info['Open_position'] = 0
                if len(new_price_info) > 0:
                    if self.fdata is None:
                        self.get_data(req_id)
                        logger.info(f'Se descargó data historica, tamaño {self.fdata.shape}')
                        
                    if self.redondear_marca_de_tiempo(str(datetime.datetime.now())) in list(self.fdata.index):    
                        self.fdata = self.fdata[~self.fdata.index.duplicated(keep=False)]
                    
                    if 'Short_Exit' not in self.fdata.columns:
                        self.fdata['Short_Exit'] = 0
                        self.fdata['Open_position'] = 0
                        logger.info('Se agregaron indicadores Short_Exit y Open_position')
                    
                    self.fdata = pd.concat([self.fdata,new_price_info])

                    self.estrategy_jemir()
                    logger.info('CALCULO DE MÉTRICAS ')
                    logger.info(f'Ultima Vela {self.fdata[-1:].T}')
                    
                    try:
                        self.strategy_metrics_jemir(price, market_price, sell_market_price)
                        logger.info('ANALIZANDO ESTRATEGIA')
                        logger.info(f'Métricas de la estrategia {self.dict_metrics}')
                         
                    except Exception as e:
                        logger.info(f'{e}')
                        logger.info('NO cumple con los criterios de la estrategia')
                    
                    self.plot_strategy_jemir()
                    self.html_generate() 
                    # cont += 1                
                        
            except Exception as e:
                logger.info(f'{e}')

    
    def convert_to_seconds(self):
        time_units = {
            'm': 60,     # minutos
            'h': 3600,   # horas
            'd': 86400,  # días
            'wk': 604800,  # semanas
            'mo': 2628000,  # meses (aproximadamente)
            '3mo': 7884000,  # 3 meses (aproximadamente)
        }

        if self.interval in time_units:
            return time_units[self.interval]

        if self.interval.endswith('m'):
            minutes = int(self.interval[:-1])
            return minutes * 60

        if self.interval.endswith('h'):
            hours = int(self.interval[:-1])
            return hours * 3600

        if self.interval.endswith('d'):
            days = int(self.interval[:-1])
            return days * 86400

        raise ValueError("Intervalo de tiempo no válido")

    def redondear_marca_de_tiempo(self, marca_de_tiempo):
        """
        Redondea una marca de tiempo según el formato especificado y la zona horaria.

        Args:
            marca_de_tiempo (str o Timestamp): La marca de tiempo que se va a redondear.
            formato (str): El formato de redondeo ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '1wk', '1mo', '3mo').
            zona_horaria (str): La zona horaria para la marca de tiempo redondeada (por defecto, 'America/New_York').

        Returns:
            Timestamp: La marca de tiempo redondeada en la zona horaria especificada.
        """
        formato = self.interval
        zona_horaria='America/New_York'
        if isinstance(marca_de_tiempo, str):
            # Convierte la cadena a una marca de tiempo si es una cadena
            marca_de_tiempo = pd.to_datetime(marca_de_tiempo)
        
        formatos_validos = ['1m','2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '1wk', '1mo', '3mo']
        
        if formato not in formatos_validos:
            raise ValueError("Formato no válido. Use uno de los formatos siguientes: '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '1wk', '1mo', '3mo'.")
        
        # Convierte a minutos, horas, días o meses según el formato especificado
        if formato.endswith('m'):
            minutos = int(formato[:-1])
            marca_de_tiempo_redondeada = marca_de_tiempo.round(f'{minutos}T')
        elif formato.endswith('h'):
            horas = int(formato[:-1])
            marca_de_tiempo_redondeada = marca_de_tiempo.round(f'{horas}H')
        elif formato.endswith('d'):
            dias = int(formato[:-1])
            marca_de_tiempo_redondeada = marca_de_tiempo.round(f'{dias}D')
        elif formato.endswith('wk'):
            semanas = int(formato[:-2])
            marca_de_tiempo_redondeada = marca_de_tiempo.round(f'{semanas}W')
        elif formato.endswith('mo'):
            meses = int(formato[:-2])
            marca_de_tiempo_redondeada = marca_de_tiempo.round(f'{meses}M')
        
        # Establece la zona horaria
        # marca_de_tiempo_redondeada = marca_de_tiempo_redondeada.tz_localize(pytz.UTC)
        # marca_de_tiempo_redondeada = marca_de_tiempo_redondeada.astimezone(pytz.timezone(zona_horaria))
        
        return marca_de_tiempo_redondeada

    def get_data(self, req_id):
        if self.interval == '1m':
            end_date = pd.to_datetime(datetime.datetime.today().strftime('%Y-%m-%d'))
            start_date = end_date - pd.DateOffset(days=6)
    
        elif self.interval in ['2m', '5m', '15m', '30m']:
            end_date = pd.to_datetime(datetime.datetime.today().strftime('%Y-%m-%d'))
            aux = 0
            while end_date.dayofweek > 4:
                end_date -= pd.DateOffset(days=1)
                aux += 1
            start_date = end_date - pd.DateOffset(days=59 - aux)
    
        elif self.interval in ['60m', '90m', '1h']:
            end_date = pd.to_datetime(datetime.datetime.today().strftime('%Y-%m-%d'))
            aux = 0
            while end_date.dayofweek > 4:
                end_date -= pd.DateOffset(days=1)
                aux += 1
            start_date = end_date - pd.DateOffset(days=720 - aux)
    
        elif self.interval == '1d':
            end_date = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
            start_date = end_date - pd.DateOffset(days=756)
    
        elif self.interval == '1wk':
            end_date = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
            start_date = end_date - pd.DateOffset(days=1260)
    
        elif self.interval == '1mo':
            end_date = pd.to_datetime(datetime.datetime.today().strftime('%Y-%m-%d'))
            start_date = end_date - pd.DateOffset(days=2520)
    
        elif self.interval == '3mo':
            end_date = pd.to_datetime(datetime.datetime.today().strftime('%Y-%m-%d'))
            start_date = end_date - pd.DateOffset(days=7560)

        if 'MES' in self.symbol:
            self.fdata = yf.download('ES=F', start=start_date, end=end_date, interval=self.interval)
        elif 'ES' in self.symbol:
            self.fdata = yf.download('ES=F', start=start_date, end=end_date, interval=self.interval)
        elif 'MNQ' in self.symbol:
            self.fdata = yf.download('NQ=F', start=start_date, end=end_date, interval=self.interval)
        else:
            self.fdata = yf.download(self.symbol, start=start_date, end=end_date, interval=self.interval)
        
        #self.fdata.index = [convert_date_time2(x) for x in self.fdata.index]
        #self.fdata.index = pd.to_datetime(self.fdata.index,  format='%Y-%m-%d %H:%M:%S')
        try:
            duration_str = "1 D"  # Duración de los datos históricos
            if self.interval == '1m':
                bar_size = "1 min"  # Tamaño de las barras
            elif self.interval == '15m':
                bar_size = "15 min"  # Tamaño de las barras
            elif self.interval == '10m':
                bar_size = "10 min"  # Tamaño de las barras
            elif self.interval == '1h':
                bar_size = "1 hour"  # Tamaño de las barras
            elif self.interval == '30m':
                bar_size = "30 min"  # Tamaño de las barras
            

            self.historical_market_data[req_id] = self.get_historical_market_data(self.contract, duration_str, bar_size)
            # print(self.historical_market_data[req_id])
            bar_data_dict_list = [
                                    {"Date": data.date, "Open": data.open, "High": data.high, "Low": data.low, "Close": data.close, "Volume": data.volume}
                                    for data in self.historical_market_data[req_id]
                                ]
            df = pd.DataFrame(bar_data_dict_list, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
            df["Date"] = df["Date"].apply(convert_date_time)
            # df["Date"] = pd.to_datetime(df["Date"],  format='%Y-%m-%d %H:%M:%S')
            logger.info(f'FECHA MINIMA DE DESCARGA IBAPI *** {df["Date"].min()}')
            logger.info(f'FECHA MAXIMA DE DESCARGA IBAPI *** {df["Date"].max()}')
            df.set_index("Date", inplace=True)

            self.fdata = pd.concat([self.fdata,df])
            self.fdata.index = pd.to_datetime(self.fdata.index, format='%Y-%m-%d %H:%M:%S', utc=True)

            # # Make sure self.fdata.index is now a DateTimeIndex before localizing the timezone
            #self.fdata.index = self.fdata.index.tz_localize('US/Central')

            # Set 'Date' column as the index
            self.fdata = self.fdata[~self.fdata.index.duplicated(keep='first')]
            self.fdata = self.fdata[self.fdata['Close']>0].sort_index()
            print(self.fdata)
        except:
            print('No hay data')

    def estrategy_jemir(self):
        self.fdata = self.fdata[self.fdata['Close']>0]
        # Calcular el ADX 
        adx = ta.trend.ADXIndicator(self.fdata['High'],self.fdata['Close'],self.fdata['Low'], window=14, fillna=True)
        self.fdata[f'{self.symbol}_ADX'] = adx.adx().rolling(window=3).mean()
        
        # Calcular Bollinger Bands
        self.fdata['Bollinger_Upper'] = ta.volatility.bollinger_hband(self.fdata['Close'], window=20)
        self.fdata['Bollinger_Lower'] = ta.volatility.bollinger_lband(self.fdata['Close'], window=20)
        
        # Calcular Keltner Channels (usando ATR)
        self.fdata['ATR'] = ta.volatility.average_true_range(self.fdata['High'], self.fdata['Low'], self.fdata['Close'], window=20)
        self.fdata['Keltner_Upper'] = self.fdata['Bollinger_Upper'] + 1.5 * self.fdata['ATR']
        self.fdata['Keltner_Lower'] = self.fdata['Bollinger_Lower'] - 1.5 * self.fdata['ATR']
        
        # Calcular el Squeeze Momentum Indicator (SMI)
        self.fdata['SMI'] = 100 * (self.fdata['Bollinger_Upper'] - self.fdata['Bollinger_Lower']) / self.fdata['Keltner_Upper']
        
        # Calcular estadísticas del SMI para definir umbrales
        smi_mean = self.fdata['SMI'].mean()
        smi_min = self.fdata['SMI'].min()
        smi_max = self.fdata['SMI'].max()
        
        # Definir umbrales en función de las estadísticas del SMI
        threshold_force_bearish = smi_mean - (smi_max - smi_mean) * 0.25
        threshold_momentum_bullish = smi_mean + (smi_max - smi_mean) * 0.1
        threshold_force_bullish = smi_mean + (smi_max - smi_mean) * 0.25
        threshold_momentum_bearish = smi_mean - (smi_max - smi_mean) * 0.1
        
        # Determinar fases en función de los umbrales
        self.fdata['Squeez_Momentum_Phase'] = 'No Phase'
        self.fdata.loc[self.fdata['SMI'] < threshold_force_bearish, 'Squeez_Momentum_Phase'] = 'Impulso Bajista'
        self.fdata.loc[(self.fdata['SMI'] >= threshold_force_bearish) & (self.fdata['SMI'] < threshold_momentum_bearish), 'Squeez_Momentum_Phase'] = 'Fuerza Bajista'
        self.fdata.loc[(self.fdata['SMI'] >= threshold_force_bullish) & (self.fdata['SMI'] < threshold_momentum_bullish), 'Squeez_Momentum_Phase'] = 'Fuerza Alcista'
        self.fdata.loc[(self.fdata['SMI'] >= threshold_momentum_bearish) & (self.fdata['SMI'] <= threshold_momentum_bullish), 'Squeez_Momentum_Phase'] = 'Impulso Alcista'

        # Utilizar los precios de cierre para calcular el Volume Profile
        prices = self.fdata['Close'].to_numpy()
        
        # Calcular el Volume Profile
        hist, bins = np.histogram(prices, bins=20)
        
        # Encontrar el índice del bin con la frecuencia máxima (POC)
        poc_index = np.argmax(hist)
        
        # DataFrame de Volumen con frecuencia
        self.volume_df = pd.DataFrame({'Close':bins[:-1], 'Frecuency': hist})
        
        # Calcular el precio del POC
        self.poc_price = (bins[poc_index] + bins[poc_index + 1]) / 2
        
        ##################################################
        # Estrategia                                     #
        ##################################################
        # Calcular indicadores necesarios
        self.fdata['EMA_55'] = ta.trend.ema_indicator(self.fdata['Close'], window=55)
        self.fdata['Visible_Range_POC'] = self.poc_price # Calcula el POC del Visible Range Volume Profile según tu método
        
        if self.accept_trade == 'a':
        
            # Generar señales de entrada
            self.fdata['Long_EntryA'] = np.where(
                (self.fdata[f'{self.symbol}_ADX'] > self.threshold_adx) &
                (self.fdata['Squeez_Momentum_Phase'] == 'Impulso Alcista') &
                (self.fdata['Close'] > self.fdata['EMA_55']) 
                &
                (self.fdata['Close'] > self.fdata['Visible_Range_POC']),
                1, 0
            )
            self.fdata['Long_EntryB'] = 0
        elif self.accept_trade == 'b':
            self.fdata['Long_EntryB'] = np.where(
                (self.fdata[f'{self.symbol}_ADX'] > self.threshold_adx) &
                (self.fdata['Squeez_Momentum_Phase'] == 'Impulso Alcista') &
                (self.fdata['Close'] > self.fdata['EMA_55']) 
                &
                (self.fdata['Close'] <= self.fdata['Visible_Range_POC']),
                1, 0
            )
            self.fdata['Long_EntryA'] = 0
        elif self.accept_trade == 'ab':
            # Generar señales de entrada
            self.fdata['Long_EntryA'] = np.where(
                (self.fdata[f'{self.symbol}_ADX'] > self.threshold_adx) &
                (self.fdata['Squeez_Momentum_Phase'] == 'Impulso Alcista') &
                (self.fdata['Close'] > self.fdata['EMA_55']) 
                &
                (self.fdata['Close'] > self.fdata['Visible_Range_POC']),
                1, 0
            )
            self.fdata['Long_EntryB'] = np.where(
                (self.fdata[f'{self.symbol}_ADX'] > self.threshold_adx) &
                (self.fdata['Squeez_Momentum_Phase'] == 'Impulso Alcista') &
                (self.fdata['Close'] > self.fdata['EMA_55']) 
                &
                (self.fdata['Close'] <= self.fdata['Visible_Range_POC']),
                1, 0
            )
        
        # Clasificar los trades según las condiciones
        self.fdata['Trade_Classification'] = 'C'
        self.fdata.loc[self.fdata['Long_EntryA'] == 1, 'Trade_Classification'] = 'A'
        self.fdata.loc[(self.fdata['Long_EntryB'] == 1) & (self.fdata['Close'] <= self.fdata['Visible_Range_POC']), 'Trade_Classification'] = 'B'
    
    def strategy_metrics_jemir(self, price, market_price, sell_market_price):
        
        # Iterar a través de los datos para simular la estrategia
        last_row = self.fdata[-1:]
        logger.info(f' * * * * * * Hora de actualización: {last_row.index[0]}')

        self.current_price = price

        if self.fdata['Long_EntryA'][last_row.index[0]] == 1:
            logger.info("* * * * Existe Trade tipo A")
        else: 
            logger.info("* * * * NO existe Trade tipo A")
        
        if self.fdata['Long_EntryB'][last_row.index[0]] == 1:
            logger.info("* * * * Existe Trade tipo B")
        else: 
            logger.info("* * * * NO existe Trade tipo B")

        if self.open_position and (self.active_safety_orders == self.max_safety_orders) and (self.cant_cont == self.orderSum):
            self.stoploss_activate = True
        else:
            self.stoploss_activate = False

        # Abrir una posición si hay señal de entrada y no hay una posición abierta
        if (self.fdata['Long_EntryA'][last_row.index[0]] == 1 or self.fdata['Long_EntryB'][last_row.index[0]] == 1)  and not self.open_position:
                        
            # Fijamos el precio de entrada
            
            self.open_trade_price = self.current_price
            self.buy(self.open_trade_price, float(self.quantity), "LIMIT")
            self.reqPositions()
            time.sleep(5)
            try:
                print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
            except:
                self.positions1[self.symbol]["position"] = 0
                print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
            # Aumentamos la cantidad de contratos adquiridos
            self.cant_cont = self.positions1[self.symbol]["position"]

            if self.cant_cont > 0:
                self.open_position = True
            else:
                tiempo_inicio = time.time()

                for i in tqdm(range(120), desc="Espera, ejecución orden de entrada"):
                    
                    # Actualizar las posiciones y otras variables necesarias
                    self.reqPositions()
                    # Esperar 1 segundo
                    time.sleep(1)
                    print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                    self.cant_cont = self.positions1[self.symbol]["position"]

                    # Verificar si la posición es mayor que 0 para establecer open_position en True y salir del bucle
                    if self.cant_cont > 0:
                        self.open_position = True
                        break

                    # Verificar si ha transcurrido el tiempo límite
                    tiempo_transcurrido = time.time() - tiempo_inicio
                    if tiempo_transcurrido >= 120:
                        # Si ha transcurrido el tiempo límite, cancelar la orden y salir del bucle
                        self.reqGlobalCancel()
                        break


            if self.open_position:
                # Promedio ponderado de precios con peso igual a los contratos adquiridos
                self.average_purchase_price = self.open_trade_price
                self.trades_info['action'].append('Buy')
                self.trades_info['time'].append(last_row.index[0])
                self.trades_info['price'].append(self.open_trade_price)
                self.fdata.loc[last_row.index[0], 'Open_position'] = 1
                logger.info(f"Opened long position at price {self.open_trade_price}.")
            

        elif self.open_position and (self.cant_cont > 0) and (self.active_safety_orders <= self.max_safety_orders):
            
            if (self.active_safety_orders == 0) and (self.current_price < self.average_purchase_price * (1-self.orders_info['safety_orders'][self.interval]['so_1'])):
                                
                # Fijamos el precio de entrada
                self.open_trade_price1 = self.current_price
                self.buy(self.open_trade_price1, self.order_n1, "LIMIT")
                self.reqPositions()
                time.sleep(2)
                print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                # Aumentamos la cantidad de contratos adquiridos
                self.cant_cont = self.positions1[self.symbol]["position"]

                if self.cant_cont == int(self.quantity):
                    tiempo_inicio = time.time()

                    for i in tqdm(range(120), desc="Espera, ejecución safety order 1"):
                        
                        # Actualizar las posiciones y otras variables necesarias
                        self.reqPositions()
                        # Esperar 1 segundo
                        time.sleep(1)
                        print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                        self.cant_cont = self.positions1[self.symbol]["position"]

                        # Verificar si la posición es mayor que 0 para establecer open_position en True y salir del bucle
                        if self.cant_cont > int(self.quantity):
                            break

                        # Verificar si ha transcurrido el tiempo límite
                        tiempo_transcurrido = time.time() - tiempo_inicio
                        if tiempo_transcurrido >= 120:
                            # Si ha transcurrido el tiempo límite, cancelar la orden y salir del bucle
                            self.reqGlobalCancel()
                            break

                if self.cant_cont > int(self.quantity):
                    # Promedio ponderado de precios con peso igual a los contratos adquiridos
                    self.average_purchase_price = ((int(self.quantity) * self.open_trade_price) + 
                                                    (self.order_n1 * self.open_trade_price1)
                                                    ) / (int(self.quantity) + self.order_n1)
                    self.fdata.loc[last_row.index[0], 'Open_position'] = 2
                    
                    logger.info(f"Opened 1 safety position at price {self.open_trade_price1}.")
                    self.active_safety_orders += 1
                    self.trades_info['action'].append('Buy')
                    self.trades_info['time'].append(last_row.index[0])
                    self.trades_info['price'].append(self.open_trade_price1)
                
                
            elif (self.active_safety_orders == 1) and (self.current_price < self.average_purchase_price * (1-self.orders_info['safety_orders'][self.interval]['so_2'])):
                
                self.open_trade_price2 = self.current_price
                # Fijamos el precio de entrada
                self.buy(self.open_trade_price2, self.order_n2, "LIMIT")
                self.reqPositions()
                time.sleep(2)
                print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                # Aumentamos la cantidad de contratos adquiridos
                self.cant_cont = self.positions1[self.symbol]["position"]

                if self.cant_cont <= (int(self.quantity) + self.order_n1):
                    tiempo_inicio = time.time()

                    for i in tqdm(range(120), desc="Espera, ejecución safety order 2"):
                        
                        # Actualizar las posiciones y otras variables necesarias
                        self.reqPositions()
                        # Esperar 1 segundo
                        time.sleep(1)
                        print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                        self.cant_cont = self.positions1[self.symbol]["position"]

                        # Verificar si la posición es mayor que 0 para establecer open_position en True y salir del bucle
                        if self.cant_cont > (int(self.quantity) + self.order_n1):
                            break

                        # Verificar si ha transcurrido el tiempo límite
                        tiempo_transcurrido = time.time() - tiempo_inicio
                        if tiempo_transcurrido >= 120:
                            # Si ha transcurrido el tiempo límite, cancelar la orden y salir del bucle
                            self.reqGlobalCancel()
                            break



                if self.cant_cont > (int(self.quantity) + self.order_n1):
                    # Promedio ponderado de precios con peso igual a los contratos adquiridos
                    self.average_purchase_price = ((int(self.quantity) * self.open_trade_price) + 
                                                    (self.order_n1 * self.open_trade_price1) + 
                                                    (self.order_n2 * self.open_trade_price2)
                                            ) / (int(self.quantity) + self.order_n1 + self.order_n2)
                    
                    self.fdata.loc[last_row.index[0], 'Open_position'] = 3
                    
                    logger.info(f"Opened 2 safety position at price {self.open_trade_price2}.")
                    self.active_safety_orders += 1
                    self.trades_info['action'].append('Buy')
                    self.trades_info['time'].append(last_row.index[0])
                    self.trades_info['price'].append(self.open_trade_price2)
                
            # elif (self.active_safety_orders == 2) and (self.current_price < self.average_purchase_price * (1-self.orders_info['safety_orders'][self.interval]['so_3'])):
               
            #     # Fijamos el precio de entrada
            #     self.open_trade_price3 = self.current_price
            #     self.buy(self.open_trade_price3, self.order_n3, "LIMIT")
            #     self.reqPositions()
            #     time.sleep(2)
            #     print(f'**** POSITION {self.positions1[self.contract.tradingClass]["position"]}')
            #     # Aumentamos la cantidad de contratos adquiridos
            #     self.cant_cont = self.positions1[self.contract.tradingClass]["position"]

            #     if self.cant_cont <= (int(self.quantity) + self.order_n1 + self.order_n2):
            #         tiempo_inicio = time.time()

            #         for i in tqdm(range(120), desc="Espera, ejecución safety order 3"):
                        
            #             # Actualizar las posiciones y otras variables necesarias
            #             self.reqPositions()
            #             # Esperar 1 segundo
            #             time.sleep(1)
            #             print(f'**** POSITION {self.positions1[self.contract.tradingClass]["position"]}')
            #             self.cant_cont = self.positions1[self.contract.tradingClass]["position"]

            #             # Verificar si la posición es mayor que 0 para establecer open_position en True y salir del bucle
            #             if self.cant_cont > (int(self.quantity) + self.order_n1 + self.order_n2):
            #                 break

            #             # Verificar si ha transcurrido el tiempo límite
            #             tiempo_transcurrido = time.time() - tiempo_inicio
            #             if tiempo_transcurrido >= 120:
            #                 # Si ha transcurrido el tiempo límite, cancelar la orden y salir del bucle
            #                 self.reqGlobalCancel()
            #                 break

            #     if self.cant_cont > (int(self.quantity) + self.order_n1 + self.order_n2):
            #         # Promedio ponderado de precios con peso igual a los contratos adquiridos
            #         self.average_purchase_price = ((int(self.quantity) * self.open_trade_price) + 
            #                                         (self.order_n1 * self.open_trade_price1) + 
            #                                         (self.order_n2 * self.open_trade_price2) +
            #                                         (self.order_n3 * self.open_trade_price3)
            #                                 ) / (int(self.quantity) + self.order_n1 + self.order_n2 + self.order_n3)
                    
            #         self.fdata.loc[last_row.index[0], 'Open_position'] = 4
                    
            #         logger.info(f"Opened 3 safety position at price {self.open_trade_price3}.")
            #         self.active_safety_orders += 1
                
            # elif (self.active_safety_orders == 3) and (self.current_price < self.average_purchase_price * (1-self.orders_info['safety_orders'][self.interval]['so_4'])):
                
            #     # Fijamos el precio de entrada
            #     self.open_trade_price4 = self.current_price
            #     self.buy(self.open_trade_price4, self.order_n4, "LIMIT")
            #     self.reqPositions()
            #     time.sleep(2)
            #     print(f'**** POSITION {self.positions1[self.contract.tradingClass]["position"]}')
            #     # Aumentamos la cantidad de contratos adquiridos
            #     self.cant_cont = self.positions1[self.contract.tradingClass]["position"]

            #     if self.cant_cont <= (int(self.quantity) + self.order_n1 + self.order_n2 + self.order_n3):
            #         tiempo_inicio = time.time()

            #         for i in tqdm(range(120), desc="Espera, ejecución safety order 4"):
                        
            #             # Actualizar las posiciones y otras variables necesarias
            #             self.reqPositions()
            #             # Esperar 1 segundo
            #             time.sleep(1)
            #             print(f'**** POSITION {self.positions1[self.contract.tradingClass]["position"]}')
            #             self.cant_cont = self.positions1[self.contract.tradingClass]["position"]

            #             # Verificar si la posición es mayor que 0 para establecer open_position en True y salir del bucle
            #             if self.cant_cont > (int(self.quantity) + self.order_n1 + self.order_n2 + self.order_n3):
            #                 break

            #             # Verificar si ha transcurrido el tiempo límite
            #             tiempo_transcurrido = time.time() - tiempo_inicio
            #             if tiempo_transcurrido >= 120:
            #                 # Si ha transcurrido el tiempo límite, cancelar la orden y salir del bucle
            #                 self.reqGlobalCancel()
            #                 break

            #     if self.cant_cont > (int(self.quantity) + self.order_n1 + self.order_n2 + self.order_n3):
            #         # Promedio ponderado de precios con peso igual a los contratos adquiridos
            #         self.average_purchase_price = ((int(self.quantity) * self.open_trade_price) + 
            #                                         (self.order_n1 * self.open_trade_price1) + 
            #                                         (self.order_n2 * self.open_trade_price2) +
            #                                         (self.order_n3 * self.open_trade_price3) +
            #                                         (self.order_n4 * self.open_trade_price4)
            #                                 ) / (int(self.quantity) + self.order_n1 + self.order_n2 + self.order_n3 + self.order_n4)
                    
            #         self.fdata.loc[last_row.index[0], 'Open_position'] = 5
                    
            #         logger.info(f"Opened 4 safety position at price {self.open_trade_price4}.")
            #         self.active_safety_orders += 1

        if self.open_position:
            # if not self.take_profit_percent:
            #     safety_order_2_percentage = self.orders_info['safety_orders'][self.interval]['so_2']  # Porcentaje de la Safety Order 2
            #     required_take_profit = (1 + safety_order_2_percentage) * self.average_purchase_price
            # else:
            self.required_take_profit = (1 + self.take_profit_percent) * self.average_purchase_price
                
    
            if (self.cant_cont == int(self.quantity)) and (self.current_price > self.required_take_profit):
                
                self.operations += 1
                contracts_to_sell = self.cant_cont
                self.sell(self.required_take_profit, contracts_to_sell, "LIMIT")
                contracts_to_keep = self.cant_cont - contracts_to_sell
                self.cont_ven += contracts_to_sell
                time.sleep(5)
                self.reqPositions()
                
                self.open_position = False
                try:
                    print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                    if self.cant_cont > 0:
                        
                        tiempo_inicio = time.time()

                        for i in tqdm(range(120), desc="Espera, ejecución orden de venta take profit"):
                            
                            # Actualizar las posiciones y otras variables necesarias
                            self.reqPositions()
                            # Esperar 1 segundo
                            time.sleep(1)

                            try:
                                print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                            except:
                                self.positions1[self.symbol]["position"] = 0
                                print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                                
                            self.cant_cont = self.positions1[self.symbol]["position"]
                            # Verificar si la posición es mayor que 0 para establecer open_position en True y salir del bucle
                            if self.cant_cont == 0:
                                break

                            # Verificar si ha transcurrido el tiempo límite
                            tiempo_transcurrido = time.time() - tiempo_inicio
                            if tiempo_transcurrido >= 120:
                                # Si ha transcurrido el tiempo límite, cancelar la orden y salir del bucle
                                self.reqGlobalCancel()
                                self.open_position = True
                                break 
                except:
                    self.positions1[self.symbol]["position"] = 0
                    print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                    # Aumentamos la cantidad de contratos adquiridos
                    self.cant_cont = self.positions1[self.symbol]["position"]
                if self.cant_cont == 0:
                    logger.info(f'se vendieron {contracts_to_sell} quedan {self.cant_cont}')
                    # cap_final += self.current_price
                    self.fdata.loc[last_row.index[0], 'Short_Exit'] = 1
                    logger.info(f"Closed long position at price {self.current_price} based on Safety Order 2 take profit.")
                    # self.profit_dict['price'].append(self.average_purchase_price)
                    # self.profit_dict['profit'].append(self.current_price)
                    trade_profit = (self.current_price - self.average_purchase_price) / self.average_purchase_price
                    logger.info(f'trade profit {trade_profit}')
                    self.total_profit += trade_profit
                    self.active_safety_orders = 0
                    self.trades_info['action'].append('Sell')
                    self.trades_info['time'].append(last_row.index[0])
                    self.trades_info['price'].append(self.current_price)
                    if trade_profit > 0:
                        self.successful_trades += 1
    
            elif (self.cant_cont > int(self.quantity)) and (self.current_price > self.required_take_profit):
                logger.info(f'Contratos en cuenta {self.cant_cont}')

                # Vende el 50% de los contratos
                # contracts_to_sell = self.cant_cont // 2

                # Vende toda la posición
                contracts_to_sell = self.cant_cont

                #logger.info(f'Contratos vendidos {contracts_to_sell} -- Venta del 50% de la posición')

                logger.info(f'Contratos vendidos {contracts_to_sell} -- Venta del 100% de la posición')
                self.sell(self.required_take_profit, contracts_to_sell, "LIMIT")
                contracts_to_keep = self.cant_cont - contracts_to_sell
                self.cont_ven += contracts_to_sell
                time.sleep(5)
                # Consulta de posiciones en cuenta
                self.reqPositions()
                self.open_position = False
                try:
                    print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                    if self.cant_cont > 0:
                        
                        tiempo_inicio = time.time()

                        for i in tqdm(range(120), desc="Espera, ejecución orden de venta take profit con safety orders"):
                            # Esperar 1 segundo
                            time.sleep(1)

                            # Actualizar las posiciones y otras variables necesarias
                            self.reqPositions()
                            try:
                                print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                            except:
                                self.positions1[self.symbol]["position"] = 0
                                print(f'**** POSITION {self.positions1[self.symbol]["position"]}')

                            self.cant_cont = self.positions1[self.symbol]["position"]
                            # Verificar si la posición es mayor que 0 para establecer open_position en True y salir del bucle
                            if self.cant_cont == 0:
                                break

                            # Verificar si ha transcurrido el tiempo límite
                            tiempo_transcurrido = time.time() - tiempo_inicio
                            if tiempo_transcurrido >= 120:
                                # Si ha transcurrido el tiempo límite, cancelar la orden y salir del bucle
                                self.reqGlobalCancel()
                                self.open_position = True
                                break 
                except:
                    self.positions1[self.symbol]["position"] = 0
                    print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                    # Aumentamos la cantidad de contratos adquiridos
                    self.cant_cont = self.positions1[self.symbol]["position"]
                
                # cap_final +=  (contracts_to_sell * self.current_price)
                if self.cant_cont == 0:
                    self.operations += 1
                    self.fdata.loc[last_row.index[0], 'Short_Exit'] = 1
                    logger.info(f"Closed {contracts_to_sell} contracts at price {self.current_price} based on Safety Order 2 take profit.")
                    # self.profit_dict['price'].append(self.open_trade_price)
                    # self.profit_dict['profit'].append(self.current_price)
                    trade_profit = (self.current_price - self.average_purchase_price) / self.average_purchase_price
                    logger.info(f'trade profit {trade_profit}')
                    self.total_profit += trade_profit
                    self.active_safety_orders = 0
                    self.trades_info['action'].append('Sell')
                    self.trades_info['time'].append(last_row.index[0])
                    self.trades_info['price'].append(self.current_price)
                    if trade_profit > 0:
                        self.successful_trades += 1
                    
            # Verificar la regla de cierre basada stop loss
            if (self.stoploss_activate) and (self.current_price < ((1 - self.stop_loss_percent) * self.average_purchase_price)):
                
                self.operations += 1
                # cap_final +=  cant_cont * self.current_price
                self.fdata['Short_Exit'][last_row.index[0]] = 1
                logger.info(f"Closed long position at price {self.current_price} based on stop loss.")
                # self.loss_dict['price'].append(self.average_purchase_price) 
                # self.loss_dict['loss'].append(self.current_price)
                # self.loss_dict['time'].append(last_row.index[0])

                # Calcular ganancias o pérdidas de la operación
                trade_profit = (self.current_price - self.average_purchase_price) / self.average_purchase_price
                logger.info(f'trade profit {trade_profit}')
                self.total_profit += trade_profit
                self.sell(self.current_price, self.cant_cont, "LIMIT")
                
                time.sleep(5)
                # Consulta de posiciones en cuenta
                self.reqPositions()
                self.open_position = False
                try:
                    print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                    if self.cant_cont > 0:
                        
                        tiempo_inicio = time.time()

                        for i in tqdm(range(120), desc="Espera, ejecución orden de venta de stop loss"):
                            
                            # Actualizar las posiciones y otras variables necesarias
                            self.reqPositions()
                            # Esperar 1 segundo
                            time.sleep(1)
                            try:
                                print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                            except:
                                self.positions1[self.symbol]["position"] = 0
                                print(f'**** POSITION {self.positions1[self.symbol]["position"]}')

                            self.cant_cont = self.positions1[self.symbol]["position"]
                            # Verificar si la posición es mayor que 0 para establecer open_position en True y salir del bucle
                            if self.cant_cont == 0:
                                break

                            # Verificar si ha transcurrido el tiempo límite
                            tiempo_transcurrido = time.time() - tiempo_inicio
                            if tiempo_transcurrido >= 120:
                                # Si ha transcurrido el tiempo límite, cancelar la orden y salir del bucle
                                self.reqGlobalCancel()
                                self.open_position = True
                                break 
                except:
                    self.positions1[self.symbol]["position"] = 0
                    print(f'**** POSITION {self.positions1[self.symbol]["position"]}')
                    # Aumentamos la cantidad de contratos adquiridos
                    self.cant_cont = self.positions1[self.symbol]["position"]
                
                self.active_safety_orders = 0
                self.stoploss_activate = False

                if self.cant_cont == 0:
                    logger.info(f'Venta por stop loss, quedan {self.cant_cont} contratos disponibles')
                    if trade_profit > 0:
                        self.successful_trades += 1
                        if trade_profit > self.take_profit_percent:
                            self.profitable_trades += 1
                    self.trades_info['action'].append('Sell')
                    self.trades_info['time'].append(last_row.index[0])
                    self.trades_info['price'].append(self.current_price)
        
        # Calcular métricas generales
        total_trades = self.successful_trades + (self.operations - self.successful_trades)
        win_rate = self.successful_trades / total_trades if total_trades > 0 else 0
        profit_factor = self.total_profit if self.total_profit > 0 else 0
        
        # Calcular el apalancamiento en términos de porcentaje
        # leverage_percentage = (self.total_profit / initial_capital) * 100
        # Calcula el drawdown y el drawdown máximo
        cumulative_max = self.fdata['Close'].cummax()
        drawdown = (self.fdata['Close'] - cumulative_max) / cumulative_max
        max_drawdown = drawdown.min()
        average_trade_duration = total_trades / len(self.fdata)

        # Calcula los rendimientos diarios
        self.fdata['Daily_Return'] = self.fdata['Close'].pct_change()
        
        # Calcula el rendimiento promedio y la desviación estándar de los rendimientos diarios
        # average_daily_return = self.fdata['Daily_Return'].mean()
        # std_daily_return = self.fdata['Daily_Return'].std()
        
        # Calcula el Sharpe Ratio
        # sharpe_ratio = (average_daily_return - self.risk_free_rate) / std_daily_return


        average_win_duration = self.successful_trades / total_trades * average_trade_duration
        average_loss_duration = (total_trades - self.successful_trades) / total_trades * average_trade_duration
        profitable_percentage = self.profitable_trades / total_trades * 100

        cont_com = self.cant_cont + self.cont_ven
        self.dict_metrics = {
            'total_trades':total_trades,
            'win_rate':win_rate,
            'profit_factor':profit_factor,
            # 'leverage_percentage':leverage_percentage,
            'successful_trades':self.successful_trades,
            'drawdown':drawdown,
            'max_drawdown':max_drawdown,
            'average_trade_duration':average_trade_duration,
            # 'sharpe_ratio':sharpe_ratio,
            'average_win_duration':average_win_duration,
            'average_loss_duration':average_loss_duration,
            'profitable_percentage':profitable_percentage,
            'contratos_adquiridos':cont_com,
            'contratos_vendidos': self.cont_ven,
            'contratos_posesion': self.cant_cont
        }


    def buy(self, price, cant, action):
        logger.info("=========================================================== Placing buy order: {}"
              .format(round(price, 5)))

        order_id = self.get_order_id()

        if action == "MARKET":
            order = self.market_order(self.action1, float(cant))
        elif action == "LIMIT":
            order = self.limit_order(self.action1, float(cant), self.min_price_increment(price), self.account)
        else:
            order = self.stop_limit_order(self.action1, float(cant), self.min_price_increment(price), self.account)
        
        self.placeOrder(order_id, self.contract, order)
        

    def sell(self, price, cant, action):
        logger.info("=========================================================== Placing sell order: {}"
              .format(round(price, 5)))

        order_id = self.get_order_id()
        if action == "MARKET":
            order = self.market_order(self.action2, float(cant))
        elif action == "LIMIT":
            order = self.limit_order(self.action2, float(cant), self.min_price_increment(price), self.account)
        else:
            order = self.stop_limit_order(self.action2, float(cant), self.min_price_increment(price), self.account)
 
        self.placeOrder(order_id, self.contract, order)
        
        

        


    def plot_strategy_jemir(self):
        self.figure=make_subplots( 
                        rows = 2,
                        cols=2,
                        shared_xaxes = True,
                        row_heights=[0.7, 0.3],
                        vertical_spacing = 0.06,
        specs=[[{"secondary_y": True}, {"secondary_y": False}], [{"colspan": 2}, None]])
        
        self.figure.update_layout(xaxis2= {'anchor': 'y', 'overlaying': 'x', 'side': 'top'}, xaxis_domain=[0, 0.94])
        
        self.figure.add_trace(go.Candlestick(
                        x = self.fdata.index,
                        open = self.fdata['Open'],
                        high = self.fdata['High'],
                        low = self.fdata['Low'],
                        close = self.fdata['Close'],
                        name=f'Precio de {self.contract.symbol}' 
                        ),
                        col=1,
                        row=1,
                        secondary_y = False,
                        )
        # fig.add_trace( go.Bar(x=[1, 2, 3, 4], y=[7, 4, 5, 6], name='bar', orientation = 'h',opacity = 0.5), secondary_y=True)
        # Agregar el gráfico de barras de volumen en la segunda columna (encima del gráfico de velas)
        volume_bars_trace = go.Bar(
            y=self.volume_df['Close'],
            x=self.volume_df['Frecuency'],
            orientation='h',
            name='Volumen',
            opacity = 0.2
        )
        self.figure.add_trace(volume_bars_trace, secondary_y=True, col=1,row=1)
        
        self.figure.add_trace(
            go.Scatter(
            x= self.fdata.index, 
            y=self.fdata[f'{self.symbol}_ADX'],
            line = dict(color='green',width=2),
            name=f'{self.symbol}_ADX'
            ),
            col=1,
            row=2
            )
        
        self.figure.add_trace(go.Scatter(
                x=self.fdata[self.fdata['Open_position'] == 1].index,
                y=self.fdata['Close'][self.fdata['Open_position'] == 1],
                mode= 'markers',
                name = 'Compra',
                marker=dict(
                    size=15,
                    color='black',
                    symbol='star-triangle-up'
                ) ),col=1,
                    row=1
            )
        
        for i in range(2,6):
            try:
                self.figure.add_trace(go.Scatter(
                            x=self.fdata[self.fdata['Open_position'] == i].index,
                            y=self.fdata['Close'][self.fdata['Open_position'] == i],
                            mode= 'markers',
                            name = f'Safety Order {i-1}',
                            marker=dict(
                                size=15,
                                color= self.colors[i],
                                symbol='star-triangle-up'
                            )
                                                ),
                                
                                col=1,
                                row=1
                        )
            except:
                pass
        
        # Ploteando Señales de VENTA
        self.figure.add_trace(go.Scatter(
            x=self.fdata[self.fdata['Short_Exit'] == 1].index,
            y=self.fdata['Close'][self.fdata['Short_Exit'] == 1],
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
        
        self.figure.add_trace(
        go.Scatter(
        x= self.fdata.index, 
        y=self.fdata['EMA_55'],
        line = dict(color='orange',width=2),
        name='EMA 55'
        ),
        col=1,
        row=1
        )
        
        # Add a horizontal line with title to exit_ind plot
        self.figure.add_shape(
            type="line",
            x0=self.fdata.index[0],
            x1=self.fdata.index[-1],
            y0=self.threshold_adx,
            y1=self.threshold_adx,
            line=dict(color="red", width=2, dash="dash"),
            col=1,
            row=2
        )
       
        self.figure.add_shape(
            type="line",
            x0=self.fdata.index[0],
            x1=self.fdata.index[-1],
            y0=self.poc_price,
            y1=self.poc_price,
            line=dict(color="green", width=3, dash="dash"),
            col=1,
            row=1
        )

        self.figure.data[1].update(xaxis='x2')
        #self.figure.update_yaxes(range=[min(self.fdata['Close']), max(self.fdata['Close'])])
        self.figure.update_layout(xaxis_rangeslider_visible=False)
        self.figure.update_layout(width=1500, height=1000)
        self.figure.update_layout(title=f"Estrategia aplicada a {self.symbol} en el intervalo {self.interval}")

    def html_generate(self):
        logger.info('GENERANDO EL HTML ********')
        self.plot_div = pyo.plot(self.figure, output_type='div', include_plotlyjs='cdn', image_width= 1500)
        
        style = '''
                body * {
                    box-sizing: border-box;
                }
                header {
                    display: block;
                }
                #main-header{
                            background-color: #373a36ff;
                            }
                #main-header .inwrap {
                            width: 100%;
                            max-width: 80em;
                            margin: 0 auto;
                            padding: 1.5em 0;
                            display: -webkit-box;
                            display: -ms-flexbox;
                            display: flex;
                            -webkit-box-pack: justify;
                            -ms-flex-pack: justify;
                            justify-content: space-between;
                            -webkit-box-align: center;
                            -ms-flex-align: center;
                            align-items: center;
                            }
        
        '''
        activity = ''
        for i in range(len(self.trades_info['action'])):
            activity += '<li>Operación: '+ self.trades_info['action'][i] + '; Precio: ' + str(self.trades_info['price'][i])+'; Fecha: ' + str(self.trades_info['time'][i]) + '</li>'
        # Crear el archivo HTML y escribir el código de la gráfica en él
        with open(f"bot_activity/JRBot_{self.interval}_{self.symbol}_{self.hora_ejecucion}.html", "w") as html_file:
            html_file.write(f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Gráfica Plotly</title>
                <!-- Incluir la biblioteca Plotly de CDN -->
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    {style}
                </style>
            </head>
            <body>
                <header id='main-header'>
                    <div class='inwrap'>
                        <img src='zenit_logo_dor.png' width='10%'>
                    </div>
                </header>
                <!-- Div donde se mostrará la gráfica Plotly -->
                <div id="plotly-div" style="width:100%" align="center">{self.plot_div}</div>
                <div>
                    <center>
                        <h2> Operaciones realizadas por el Bot </h2>
                        <ul>
                            {activity}
                        </ul>
                    </center>
                </div>
            </body>
            </html>
            """)

if __name__ == '__main__':
 
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', type=str, default='127.0.0.1', help='IP address')
    parser.add_argument('--port', type=int, default=7496, help='Port number')
    parser.add_argument('--client', type=int, default=2, help='Client ID')
    parser.add_argument('--symbol', type=str, default='SPY', help='symbol example AAPL')
    parser.add_argument('--secType', type=str, default='STK', help='The security type')
    parser.add_argument('--currency', type=str, default='USD', help='currency')
    parser.add_argument('--exchange', type=str, default='SMART', help='exchange')
    parser.add_argument('--quantity', type=str, default='6', help='quantity')
    
    parser.add_argument('--stop_limit_ratio', type=int, default=3, help='stop limit ratio default 3')
    
    parser.add_argument('--max_safety_orders', type=int, default=2, help='max safety orders')
    parser.add_argument('--safety_order_size', type=int, default=2, help='safety order size')
    parser.add_argument('--volume_scale', type=int, default=2, help='volume scale')
    parser.add_argument('--safety_order_deviation', type=float, default=0.05, help='% safety_order_deviation')
    parser.add_argument('--account', type=str, default='DU7774793', help='Account')

    parser.add_argument('--take_profit_percent', type=float, default=0.0006, help='Take profit percentage')
    parser.add_argument('--interval', type=str, default='1m', help='Data Time Frame')
    parser.add_argument('--accept_trade', type=str, default='ab', help='Type of trades for trading')
    parser.add_argument('--threshold_adx', type=float, default=23, help='Limit for ADX indicator')
    parser.add_argument('--multiplier', type=str, default="5", help='The multiplier for futures')
    parser.add_argument('--trading_class', type=str, default="MES", help='The trading_class for futures')
    parser.add_argument('--lastTradeDateOrContractMonth', type=str, default="20231215", help='The expire date for futures')
    parser.add_argument('--order_type', type=str, default="LIMIT", help='The type of the order: LIMIT OR MARKET')
    parser.add_argument('--order_validity', type=str, default="DAY", help='The expiration time of the order: DAY or GTC')
    parser.add_argument('--is_paper', type=str_to_bool, default=True, help='Paper or live trading')
           
    
    
    args = parser.parse_args()
    logger.info(f"args {args}")

    bot = BotZenitTrendMaster(args.ip, 
              args.port, 
              args.client, 
              args.symbol, 
              args.secType, 
              args.currency, 
              args.exchange, 
              args.quantity, 
 
              args.stop_limit_ratio,  

              args.max_safety_orders, 
              args.safety_order_size, 
              args.volume_scale, 
              args.safety_order_deviation,
              args.account,

              args.take_profit_percent,
              args.interval,
              args.accept_trade,
              args.threshold_adx,
              args.multiplier,
              args.trading_class,
              args.lastTradeDateOrContractMonth,
              args.order_type, 
              args.order_validity,
              args.is_paper
              )
    try:
        bot.main()
    except KeyboardInterrupt:
        bot.disconnect()

