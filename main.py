from ibapi.common import TickerId
from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
import logging
from time import sleep
from threading import Thread
import atexit

class ToMarket(EWrapper, EClient):
    """
    developed test class for the IBAPI.
    implements:
        - order placement
        - getting available funds in the account as a float
        - using .run() as a thread (should have been obvious before)
        - exit function to disconnect cleanly from application every time

    this class should be used as one continuous object throughout the running of the end-application rather than an
    object instantiated at every trade.
    """
    def __init__(self):
        #null vars
        self.nextValidOrderId = None
        self.orderMade = False
        # necessary instantiations per IBAPI documentation
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)

        # connects app to TWS
        self.connect("127.0.0.1", 7497, 999)

        # creates and starts EReader thread
        run = Thread(target=self.run, daemon=True)
        run.start()

        # ensures that app always disconnects cleanly
        atexit.register(self.end)
        # waits to ensure no EReader based errors occur.
        sleep(2) # this shouldn't be in production file because use-case is such that this error would not occur in the first place.
        self.nextValidOrderId = 0
        self.reqIds(-1)
    def nextValidId(self, orderId: int):
        """
        EWrapper function to receive the new order id and set member variable
        :param orderId: next orderId received from TWS
        :return: None
        """

        super().nextValidId(orderId)
        logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId


    def error(self, reqId:int, errorCode:int, errorString:str):
        """

        :param reqId: error id (-1 indicates notification not error)
        :param errorCode: error code string
        :param errorString: the actual error description
        :return:
        """
        if reqId != -1: # i.e if not a notification
            print(f"ERROR:: Code:{errorCode} - {errorString}")


    def order(self, instrument, direction, quantity):
        """
        function to allow market orders to be created and placed
        :param instrument: the instrument's symbol
        :param direction: i.e BUY or SELL
        :param quantity: number of shares
        :return: True/False for order PLACED (not necessarily successful just placed)
        """
        contract = Contract()
        if len(instrument) == 6: # if it is a forex pair
            sec_type = "CASH"
            symbol = instrument.upper()[0:3]
            currency = instrument.upper()[3:6]

            exchange = "IDEALPRO"
        elif len(instrument) <= 5: # if it is a stock
            sec_type = "STK"
            currency = "USD"
            contract.primaryExchange = "ISLAND"
            exchange = "SMART"
        else: # if it is neither stock or forex pair refuse to place order, return False for failed order.
            return False
        # creates Contract object and fills necessary data

        contract.symbol = symbol
        contract.secType = sec_type
        contract.currency = currency
        contract.exchange = exchange

        # creates order and fills out details
        order = Order()
        order.action = direction
        order.orderType = "MKT"
        order.totalQuantity = quantity
        # gets latest order id
        old_val = self.nextValidOrderId
        self.reqIds(-1)
        while self.nextValidOrderId == old_val and self.orderMade:  # waits until order id updated.
            pass
        # places the order and returns True since no errors would have been raised by this point.
        self.placeOrder(self.nextValidOrderId, contract, order)
        self.orderMade = True
        return True


    def accountSummary(self, reqId:int, account:str, tag:str, value:str,currency:str):
        """
        receives the account summary from TWS
        :param reqId: id supplied by reqAccountSummary
        :param account: if multiple accounts then the account selected
        :param tag: tag requested by EClient
        :param value: value returned from request
        :param currency: currency that value is in.
        :return: None
        """
        if tag == "AvailableFunds": # for getBalanec
            self.balance = float(value)

    def accountSummaryEnd(self, reqId:int):
        """
        confirms if the account summary has been returned and processed such that self.balance has a correct value.
        :param reqId: id request made with
        :return: None
        """
        self.accountSummaryReceived = True

    def getBalance(self):
        """
        gets the available funds for trading from TWS
        :return: float balance of available funds in account for trading
        """
        self.accountSummaryReceived = False
        self.reqAccountSummary(-1, "All","AvailableFunds")
        while not self.accountSummaryReceived: # waits until account summary received to return value
            pass
        return self.balance
    def position(self, account:str, contract:Contract, position:float,avgCost:float):
        if contract.secType == 'STK':
            print(f"symbol: {contract.symbol}")
        elif contract.secType == 'CASH':
            print(f"symbol: {contract.symbol}.{contract.currency}")
        print(f"\tposition: {position}")
        print(f"\tavgCost: {avgCost}")

    def positionEnd(self):
        print("END")
    def end(self):
        """
        exit function to cleanly disconnect from TWS
        :return: None
        """
        print("TRADER DISCONNECTING")
        self.done = True # shuts down EReader thread
        self.disconnect() # disconnects from TWS
