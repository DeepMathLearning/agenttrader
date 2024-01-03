import math
import datetime
from datetime import timedelta
from threading import Thread
import time

from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.common import BarData
from ibapi.order import Order
from ibapi import order_condition
from ibapi.execution import Execution
import pytz
import pandas as pd
from dateutil import parser

# defining market data types to avoid typos
Bid, Ask, Last, Close, High, Low, Open =\
    'Bid', 'Ask', 'Last', 'Close', 'High', 'Low', 'Open'

# defining (delayed) market data types to avoid typos
DelayedBid, DelayedAsk, DelayedLast, DelayedClose, DelayedHigh, DelayedLow, DelayedOpen, DelayedVolume, DelayedBidSize, DelayedAskSize =\
    'DelayedBid', 'DelayedAsk', 'DelayedLast', 'DelayedClose', 'DelayedHigh', 'DelayedLow', 'DelayedOpen', 'DelayedVolume', 'DelayedBidSize', 'DelayedAskSize'

HIDE_ERROR_CODES = [2104, 2106, 2158, 399]


class PriceInformation:
    """
    Class used to store specific price attributes for contracts.
    """
    def __init__(self, contract):
        self.contract: Contract = contract
        self.Bid = None
        self.Ask = None
        self.Last = None
        self.Close = None
        self.High = None
        self.Low = None
        self.Open = None
        self.LastTime = None

        self.DelayedBid = None
        self.DelayedAsk = None
        self.DelayedLast = None
        self.DelayedClose = None
        self.DelayedHigh = None
        self.DelayedLow = None
        self.DelayedOpen = None
        self.DelayedVolume = None

        self.BidSize = None
        self.AskSize = None
        self.DelayedBidSize = None
        self.Bids = None

        self.NotDefined = None

        self.DelayedLastTimestamp = None

    def __str__(self):
        report_string = ""
        report_string += self.contract.symbol if self.contract.localSymbol == "" else self.contract.localSymbol
        for t in ['Bid', 'Ask', 'Last', 'Close', 'High', 'Low', 'Open','LastTime', 'DelayedBid', 'DelayedAsk', 'DelayedLast', 'DelayedClose', 'DelayedHigh', 'DelayedLow', 'DelayedOpen', 'DelayedVolume', 'BidSize', 'AskSize', 'DelayedBidSize', 'DelayedAskSize','DelayedLastTimestamp']:
            price = getattr(self, t, None)
            if price is not None:
                report_string += f", {t}: {str(price)}"

        return report_string


class OrderInformation:
    def __init__(self, contract=None, order=None, orderstate=None, status=None, filled=None, remaining=None,
                 avgFillPrice=None, permid=None, parentId=None, lastFillPrice=None, clientId=None, whyHeld=None, mktCapPrice=None):
        self.contract = contract
        self.order = order
        self.orderstate = orderstate
        self.status = status
        self.filled = filled
        self.remaining = remaining
        self.avgFillPrice = avgFillPrice
        self.permid = permid
        self.parentId = parentId
        self.lastFillPrice = lastFillPrice
        self.clientId = clientId
        self.whyHeld = whyHeld
        self.mktCapPrice = mktCapPrice

    def __str__(self):
        if self.contract is None or self.order is None:
            return """Order State: {}, Status: {}, Filled: {}, Remaining: {}""". \
                format(self.orderstate, self.status, self.filled, self.remaining)
        else:
            return """Symbol: {}, Order: {}, Order State: {}, Status: {}, Filled: {}, Remaining: {}""".\
                format(self.contract.symbol, self.order.orderType, self.orderstate,
                       self.status, self.filled, self.remaining)


class PositionInfo:
    def __init__(self, contract, pos, account, avgCost):
        self.contract = contract
        self.pos = pos
        self.account = account
        self.avgCost = avgCost


class Wrapper(EWrapper):
    """
    Inherited wrapper function to over(write) our own methods in.
    """
    FINISHED = "FINISHED"

    def __init__(self):
        EWrapper.__init__(self)
        self.market_data = {}
        self.contract_details = {}
        self.historical_market_data = {}
        self.positions_pnl = {}
        self.positions = []
        self.order_details = None
        self.positions_end_flag = False
        self.next_valid_order_id = None
        self.execution_values = None
        self.executions = []

    def contractDetails(self, reqId, contractDetails):
        """
        Function to receive the contracts from the api and store them in Wrapper.contract_details.
        """
        try:
            self.contract_details[reqId].append(contractDetails)
        except KeyError:
            pass

    def contractDetailsEnd(self, reqId):
        """
        Function indicating the end of a contract details callback.
        """
        try:
            self.contract_details[reqId].append(self.FINISHED)
        except KeyError:
            pass

    def tickPrice(self, reqId, tickType, price: float, attrib):
        """
        Function to store market data callbacks in the Wrapper.market_data dict using the PriceInformation class.
        """
        if tickType == 1:
            data_type = Bid
        elif tickType == 2:
            data_type = Ask
        elif tickType == 4:
            data_type = Last
        elif tickType == 9:
            data_type = Close
        elif tickType == 6:
            data_type = High
        elif tickType == 7:
            data_type = Low
        elif tickType == 14:
            data_type = Open
        elif tickType == 66:
            data_type = DelayedBid
        elif tickType == 67:
            data_type = DelayedAsk
        elif tickType == 68:
            data_type = DelayedLast
        elif tickType == 72:
            data_type = DelayedHigh
        elif tickType == 73:
            data_type = DelayedLow
        elif tickType == 75:
            data_type = DelayedClose
        elif tickType == 76:
            data_type = DelayedOpen
        else:
            data_type = "NotDefined"

        try:
            setattr(self.market_data[reqId], data_type, price)
        except KeyError:
            pass

    def tickSize(self, reqId, tickType, price: float):
        """
        Function to store market data callbacks in the Wrapper.market_data dict using the PriceInformation class.
        """
        if tickType == 74:
            data_type = DelayedVolume
        elif tickType == 69:
            data_type= DelayedBidSize
        elif tickType == 70:
            data_type= DelayedAskSize
        
        else:
            data_type = "NotDefined"

        try:
            setattr(self.market_data[reqId], data_type, price)
        except KeyError:
            pass



    def historicalData(self, reqId: int, bar: BarData):
        self.historical_market_data[reqId].append(bar) if reqId in self.historical_market_data.keys() else None
    
    def historicalDataEnd(self, reqId:int, start:str, end:str):
        self.historical_market_data[reqId].append(self.FINISHED) if reqId in self.historical_market_data.keys() else None

    def nextValidId(self, orderId:int):
        self.next_valid_order_id = orderId

    def orderStatus(self, orderId , status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId,
                    whyHeld, mktCapPrice):
        order_details = OrderInformation(status=status, filled=filled, remaining=remaining, avgFillPrice=avgFillPrice,
                                         permid=permId, parentId=parentId, lastFillPrice=lastFillPrice, clientId=clientId,
                                         whyHeld=whyHeld, mktCapPrice=mktCapPrice)
        self.order_details = order_details
        print(order_details)

    def pnlSingle(self, reqId: int, pos: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float, value: float):
        self.positions_pnl[reqId] = pos, dailyPnL, unrealizedPnL, realizedPnL if reqId in self.positions_pnl.keys() else None

    def position(self, account:str, contract:Contract, position:float,
                 avgCost:float):
        self.positions.append(PositionInfo(contract, position, account, avgCost))

    def positionEnd(self):
        self.positions_end_flag = True

    def accountSummary(self, reqId, account, tag, value, currency):
        if tag == "NetLiquidation":
            self.account_balance = float(value)       

    # def execDetails(self, reqId: int, contract: Contract, execution: Execution):
    #     self.execution_values = execution
    #     print("ExecDetails. ReqId:", reqId, "Symbol:", contract.symbol, "SecType:", 
    #          contract.secType, "Currency:", contract.currency, self.execution_values)
    
    def execDetails(self, reqId, contract, execution):
        self.executions.append({
            "execId": execution.execId,
            "symbol": contract.symbol,
            "side": execution.side,
            "quantity": execution.shares,
            "price": execution.price,
            "dateTime": execution.time,
            "currency": contract.currency
        })


class Client(EClient):
    """
    Client class we can use to write our own functions in to request data from the API.
    """
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)
        self.unique_id = 0

    def get_unique_id(self):
        """
        Function to keep track of a unique id for the application.
        """
        self.unique_id =+ 1
        return self.unique_id

    def get_option_chain(self, ltd: str):
        """
        Function to get an ambiguous option contract for the dutch index EOE.
        """
        contract = Contract()
        contract.symbol = "EOE"
        contract.secType = "OPT"
        contract.exchange = "FTA"
        contract.currency = "EUR"
        contract.lastTradeDateOrContractMonth = ltd
        contract.multiplier = "100"
        return contract


    def CONTRACT_CONFIG(self):
        contract = Contract()
        return contract


    def market_order(self, action, quantity):
        order = Order()
        order.eTradeOnly = False
        order.firmQuoteOnly = False
        order.action = action
        order.orderType = "MKT"
        order.totalQuantity = quantity
        order.tif = self.order_validity
        return order

    def limit_order(self, action, quantity, limit_price,account):
        order = Order()
        order.eTradeOnly = False
        order.firmQuoteOnly = False
        order.action = action
        order.orderType = "LMT"
        order.totalQuantity = quantity
        order.lmtPrice = limit_price
        order.tif = self.order_validity
        order.account = account
        return order
    
    def stop_limit_order(self, action, quantity, limit_price,account):
        order = Order()
        order.eTradeOnly = False
        order.firmQuoteOnly = False
        order.action = action
        order.orderType = "STP"
        order.totalQuantity = quantity
        order.lmtPrice = limit_price
        order.tif = self.order_validity
        order.account = account
        return order

    def bracket_order(self, order_id, action: str, quantity, limit_price, take_profit_price, stop_loss_price):
        parent_order = Order()
        parent_order.orderId = order_id
        parent_order.action = action
        parent_order.orderType = "LMT"
        parent_order.totalQuantity = quantity
        parent_order.lmtPrice = limit_price
        parent_order.transmit = False

        take_profit_order = Order()
        take_profit_order.orderId = order_id + 1
        take_profit_order.action = "SELL" if action.upper() == "BUY" else "BUY"
        take_profit_order.orderType = "LMT"
        take_profit_order.totalQuantity = quantity
        take_profit_order.lmtPrice = take_profit_price
        take_profit_order.parentId = order_id
        take_profit_order.transmit = False

        stop_loss_order = Order()
        stop_loss_order.orderId = order_id + 2
        stop_loss_order.action = "SELL" if action.upper() == "BUY" else "BUY"
        stop_loss_order.orderType = "STP"
        stop_loss_order.auxPrice = stop_loss_price
        stop_loss_order.totalQuantity = quantity
        stop_loss_order.parentId = order_id
        stop_loss_order.transmit = True

        return [parent_order, take_profit_order, stop_loss_order]

    def TimeCondition(self, isMore, IsConjunction, time: datetime.datetime=None, delta: datetime.timedelta=None):
        if time is not None:
            condition_time = time.strftime("%Y%m%d %H:%M:%S")
        elif delta is not None:
            condition_time = datetime.datetime.now() + delta
            condition_time = condition_time.strftime("%Y%m%d %H:%M:%S")
        else:
            raise RuntimeError("Time is None and delta is None.")

        time_condition = order_condition.Create(order_condition.OrderCondition.Time)
        time_condition.isMore = isMore
        time_condition.time = condition_time
        time_condition.isConjunctionConnection = IsConjunction

        return time_condition

    def get_account_balance(self):
        self.reqAccountSummary(1, "All", "NetLiquidation")
        time.sleep(1)  # Wait for the callback to be called
        return self.wrapper.account_balance
    
    def get_execution_values(self):
        return Execution



class Main(Wrapper, Client):
    def __init__(self, ip_address, port_id, client_id):
        Wrapper.__init__(self)
        Client.__init__(self, wrapper=self)
        self.ip_address, self.port_id, self.client_id = ip_address, port_id, client_id

        # Connect the first time
        self.hide_error_codes = HIDE_ERROR_CODES
        self.reconnect()


    def reconnect(self):
        """
        This function connects to an instance of the gateway or trader workstation.
        """
        self.connect(self.ip_address, self.port_id, self.client_id)
        thread = Thread(target=self.run).start()
        setattr(self, "_thread", thread)
        time.sleep(2)

    def complete_contract(self, contract: Contract, time_out=10) -> list:
        """
        This function requests the contract details from the api and waits for all the contracts to be received.
        """
        req_id = self.get_unique_id()
        self.contract_details[req_id] = []
        self.reqContractDetails(req_id, contract)

        for i in range(time_out * 100):
            time.sleep(0.01)
            if self.FINISHED in self.contract_details[req_id]:
                self.contract_details[req_id].remove(self.FINISHED)
                return [c.contract for c in self.contract_details[req_id]]
            else:
                continue
        else:
            return []

    def get_market_data(self, contract: Contract, data_types: list, live_data=False, time_out=10) -> PriceInformation:
        """
        This function requests the market data and handles the data callback.
        """
        unique_id = self.get_unique_id()
        self.market_data[unique_id] = PriceInformation(contract)
        self.reqMarketDataType(1) if live_data else self.reqMarketDataType(3)
        self.reqMktData(unique_id, contract, "", True, False, [])

        for i in range(100 * time_out):
            time.sleep(0.01)

            if None in [getattr(self.market_data[unique_id], dt) for dt in data_types]:
                continue
            else:
                break
        return self.market_data.pop(unique_id)

    def get_historical_market_data(self, contract: Contract, duration: str = "1 D", bar_size: str = "1 day", time_out=50, data_type="TRADES") -> list:
        req_id = self.get_unique_id()
        self.historical_market_data[req_id] = []
        end_date_time_utc = datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S")

        self.reqHistoricalData(req_id, contract, end_date_time_utc, duration,bar_size, data_type, 1, 1, False, [])

        for i in range(time_out * 100):
            time.sleep(0.01)

            if self.FINISHED in self.historical_market_data[req_id]:
                self.historical_market_data[req_id].remove(self.FINISHED)
                return self.historical_market_data[req_id]
        else:
            self.cancelHistoricalData(req_id)
            print("failed to retrieve market data.")
            return []


        pass

    def bar_to_datetime(self, bar: BarData):
        print(bar.date)
        datetime_obj = pd.to_datetime(bar.date, format="%Y%m%d %H:%M:%S %Z", errors="coerce")
        if not pd.isnull(datetime_obj):
            datetime_obj = datetime_obj.replace(tzinfo=None)
            return datetime_obj #, datetime_obj.tz.zone
        else:
            datetime_obj = pd.to_datetime(bar.date, format="%Y%m%d", errors="coerce")
            return datetime_obj

    def get_order_id(self, time_out=10):
        self.next_valid_order_id = None
        self.reqIds(-1)

        for i in range(time_out * 100):
            time.sleep(0.01)
            if self.next_valid_order_id is not None:
                return self.next_valid_order_id
            else:
                continue
        else:
            return None

    def get_pnl(self, time_out=10):
        total_pnl = 0
        positions = self.get_positions()
        self.positions_pnl = {}
        contract_for_id = {}

        for position in positions:
            position: PositionInfo = position
            if position.pos == 0:
                continue
            req_id = self.get_unique_id()
            self.positions_pnl[req_id] = None
            self.reqPnLSingle(req_id, position.account, "", position.contract.conId)
            contract_for_id[req_id] = position.contract

        for i in range(time_out * 100):
            time.sleep(0.01)
            if None not in self.positions_pnl.values():
                break

        for key, pnl in self.positions_pnl.items():
            self.cancelPnLSingle(key)
            if pnl is not None:
                pos, dailyPnL, unrealizedPnL, realizedPnL = pnl
                msg = "PnL for contract: {}, is {}.".format(contract_for_id[key], dailyPnL)
                print(msg)
                total_pnl += dailyPnL

        print("total Pnl : {}.".format(total_pnl))
        print(f'Position --- {self.positions_pnl}')

    def get_positions(self, time_out=10):
        self.positions = []
        self.positions_end_flag = False
        self.reqPositions()

        for i in range(time_out * 100):
            time.sleep(0.01)
            if self.positions_end_flag:
                break

        self.cancelPositions()
        return self.positions

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson):
        if errorCode not in self.hide_error_codes:
            print("Error Id: {}, Error Code: {}, String: {}".format(reqId, errorCode, errorString))



    def close_all_positions(self, time_out=10):
        # Request current positions
        positions = self.get_positions()

        for position in positions:
            position: PositionInfo = position
            if position.pos != 0:  # If the position size is not 0
                # Determine the action based on whether position is long (SELL) or short (BUY)
                action = 'SELL' if position.pos > 0 else 'BUY'
                
                # Create a limit order to close the position
                order = self.market_order(action, abs(position.pos))
                
                # Place the order
                self.placeOrder(self.get_order_id(), position.contract, order)
                
        # Allow some time for all orders to be transmitted before ending the function
        time.sleep(time_out)

    def stop_loss_order(self, action: str, quantity: int, stop_price: float) -> Order:
        order = Order()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = "STP LMT"  # Stop Limit Order
        order.auxPrice = stop_price
        order.lmtPrice = stop_price + (0.05 if action == "SELL" else -0.05)  # Adjust limit price slightly to ensure execution
        return order
    
    def contractDetails(self, reqId: int, contractDetails):
        super().contractDetails(reqId, contractDetails)
        print( f"contractDetails, {contractDetails}" )
        print( f"contractDetails Tick , {contractDetails.minTick}" )
        self.min_tick = float(contractDetails.minTick)

    def min_price_increment(self, price: float):
        return round(math.floor(price / self.min_tick) * self.min_tick, 5)
    
    # def execDetails(self, reqId: int, contract: Contract, execution: Execution):
    #     # Esta función se llama cuando se reciben detalles de ejecución
    #     print(f"***** Execution {dir(execution)}:")
    #     print(f"Symbol: {contract.symbol}")
    #     print(f"Side: {execution.side}")
    #     print(f"Shares: {execution.shares}")
    #     print(f"Price: {execution.price}")
    #     print(f"Execution ID: {execution.execId}")
    #     self.execution_price = execution.price

    def execDetails(self, reqId, contract, execution):
        print(f'{dir(execution)}')
        self.executions.append({
            #"execId": execution.execId,
            "symbol": contract.symbol,
            #"side": execution.side,
            #"quantity": execution.shares,
            "price": execution.price,
            "dateTime": execution.time,
            "currency": contract.currency
        })

    def position(self, account, contract, position, avgCost):
        # Este método se llama cuando se reciben datos de posición
        if contract.secType == 'FUT':
            symbol = contract.tradingClass
        else:
            symbol = contract.symbol

        self.positions1[symbol] = {
            "position": position,
            "averageCost": avgCost
        }
        self.position1 = position
        print("Account:", account)
        print("Contract:", contract.symbol)
        print("Position:", position)
        print("Average Cost:", avgCost)
        print("Dict:", self.positions1)
        
        
# Custom function to convert a string to a boolean
def str_to_bool(s):
    if s.lower() in ("true", "t", "yes", "y"):
        return True
    elif s.lower() in ("false", "f", "no", "n"):
        return False
    else:
        raise argparse.ArgumentTypeError("Invalid boolean value")

def convert_date_time(datetime_string):

    # Parse the input datetime string to a datetime object
    initial_datetime = pd.to_datetime(str(datetime_string), format='%Y%m%d %H:%M:%S %Z')
    initial_datetime = initial_datetime - timedelta(hours=4)
    # datetime_string = str(initial_datetime)

    # # Parse the input datetime string to a datetime object
    # initial_datetime = pd.to_datetime(datetime_string, format='%Y-%m-%d %H:%M:%S%z')

    # Convert the time zone from '-05:00' to '-04:00'
    final_datetime = initial_datetime.astimezone(pytz.timezone('Etc/GMT+4'))
    return final_datetime

def convert_date_time2(original_datetime):
    # Create a datetime object from the original string
    fmt = '%Y-%m-%d %H:%M:%S'
    parsed_datetime = datetime.datetime.strptime(str(original_datetime), fmt)

    return parsed_datetime