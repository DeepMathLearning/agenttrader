from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import *
import threading
import time

def orden_status(ip,port):
    class IBapi(EWrapper, EClient):
        order_dic = {}
        order_list =[]
        
        def __init__(self):
            EClient.__init__(self, self)

        def nextValidId(self, orderId):
            self.nextValidId = orderId
            self.start()

        def start(self):
            self.reqAllOpenOrders()
    
        def openOrder(self, orderId, contract: Contract, order: Order,orderState):
            super().openOrder(orderId, contract, order, orderState)
            self.order_dic['PermId'] = order.permId
            self.order_dic['ClientId'] = order.clientId
            self.order_dic['OrderIdrderId'] = orderId
            self.order_dic['Account'] = order.account
            self.order_dic['Symbol'] = contract.symbol
            self.order_dic['SecType'] = contract.secType
            self.order_dic['Exchange'] = contract.exchange
            self.order_dic['Action'] = order.action
            self.order_dic['OrderType'] = order.orderType
            self.order_dic['TotalQty'] = order.totalQuantity
            self.order_dic['CashQty'] = order.cashQty
            self.order_dic['LmtPrice'] = order.lmtPrice
            self.order_dic['AuxPrice'] = order.auxPrice
            self.order_dic['Status'] = orderState.status
            self.order_list.append([
                order.permId,
                order.clientId,
                orderId,
                order.account,
                contract.symbol,
                contract.secType,
                contract.exchange,
                order.action,
                order.orderType,
                order.totalQuantity,
                order.cashQty,
                order.lmtPrice,
                orderState.status,
        ])
 
    def run_loop():
        app.run()

    app = IBapi()
    app.connect(ip, port, 4)

    # Inicie el socket en un hilo
    api_thread = threading.Thread(target=run_loop, daemon=True)
    api_thread.start()

    time.sleep(3)
    ordenes_nav = app.order_list
    app.disconnect()
    print("aqui voy")
    print(app.order_list)
    return(app.order_list)