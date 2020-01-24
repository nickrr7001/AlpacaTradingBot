import requests
import alpaca_trade_api as tradeapi
from finviz.screener import Screener
import finviz
import time
import datetime
skey = "INSERT_S_KEY_HERE"
apiKey = "INSERT_API_KEY_HERE"
apiEndpoint = "https://api.alpaca.markets"
api = tradeapi.REST(apiKey,skey)
stockList = [None]
class stockData:
    def __init__(self,name,short,oss,floatVal):
        self.name = name
        self.short = short
        self.OutStandingShares = oss
        self.floatVal = floatVal
def CheckStock(symbol,days):
    barset = api.get_barset(symbol, 'day', limit=1)
    aapl_bars = barset[symbol]
    week_open = aapl_bars[0].o
    week_close = aapl_bars[-1].c
    percent_change = (week_close - week_open) / week_open * 100
    print( symbol+' moved '+str(percent_change)+'% over the last '+str(days)+' day(s)')
def isMarketOpen():
    clock = api.get_clock()
    return clock.is_open
def stockScreener(shortable,min_s_float,max_s_float,minOSS,maxOSS,PriceLimit):
    filters = ['exch_nasd']
    stock_list = Screener(filters=filters, order='price')
    AcceptedStocks = []
    print (len(stock_list))
    for stock in stock_list:
        #print(stock['Ticker'], stock['Price']) 
        symbol = stock['Ticker']
        sData = GetStockData(symbol)
        price = float(sData['Price'])
        if (price > PriceLimit):
            break
        if ('-' not in sData['Insider Own']):
            if ( float( sData['Insider Own'].replace('%','') ) < 10):
                continue

        stock_shortable = sData['Shortable'] == 'Yes'
        OutStandingShares = sData['Shs Outstand'] 
        Week52Range = sData['52W Range']
        L52 = float(Week52Range[0:Week52Range.index('-')-1])
        H52 = float(Week52Range[Week52Range.index('-')+1::])
        if (H52 > price and 100*(price/H52)>=15):
            continue
        if (price < L52):
            continue
        if OutStandingShares[-1] != 'M':
            continue
        else:
            OutStandingShares = float(OutStandingShares[0:len(OutStandingShares) - 1])
        floatVal = sData['Shs Float']
        if (floatVal == '-'):
            continue
        else:
            try:
                floatVal = float(floatVal[0:len(floatVal) - 1])
                if (floatVal > 5.0):
                    continue
                print("Good Float!")
            except ValueError:
                print ("Float Val Error" + floatVal)
        shortFloat = 0.0
        try:
            shortFloat = float(sData['Short Float'].replace('%',''))
        except ValueError:
            continue
        if (stock_shortable == shortable and shortFloat >= min_s_float and shortFloat <= max_s_float and minOSS <= OutStandingShares and maxOSS >= OutStandingShares):
            AcceptedStocks.append(stockData(symbol,shortFloat,OutStandingShares,floatVal))
            print (symbol + " Meets the requirements")
        else:
            print (symbol + " Does not meet requirements!")
    return AcceptedStocks
def buyStock(sym,amount):
    api.submit_order(
        symbol=sym,
        qty=amount,
        side='buy',
        type='market',
        time_in_force='gtc'
    )
def sellStock(sym,amount):
    api.submit_order(
        symbol=sym,
        qty=amount,
        side='sell',
        type='market',
        time_in_force='opg',
    )
def GetStockData(symbol):
    return (finviz.get_stock(symbol))
def FindTop10(Collection):
    topStocks = [None] * 10
    for item in Collection:
        print( item.name + " is a good stock!" )
        for i in range(len(topStocks)):
            if (CompareItems(item,topStocks[i])):
                topStocks = ShiftArray(item,i,topStocks)
                break
    return topStocks
def ShiftArray(item_to_insert,insert_index,col):
    col.insert(insert_index,item_to_insert)
    return col[0:-1]  
# Returns True if item1 is a better stock then item2
def CompareItems(item1,item2):
    if (item2 == None):
        return True
    if (item1.floatVal == item2.floatVal):
        if (item1.short == item2.short):
            return True
        else:
            return item1.short > item2.short
    else:
        return item1.floatVal < item2.floatVal
def TradingBot():
    while True:
        hour = datetime.datetime.now().hour
        if (isMarketOpen() and hour >= 8):
            #start trading!
            global stockList
            if (stockList[0] == None):
                print ("No Stocks, Wait for close! Checking Sells...")
                stockList = FindTop10(stockScreener(True,0,100,1,10,10))
            stocksToBuy = []
            account = api.get_account()
            buyingpower = float(account.buying_power)
            ownedStocks = api.list_positions()
            for i in ownedStocks:
                ticker = i.symbol
                pos = api.get_position(ticker)
                Profit = float(pos.unrealized_plpc)
                if (Profit >= 3.0 or Profit <= -3.0):
                    print ("Selling stock: " + i.symbol + " @ profit of " + Profit + "%")
                    sellStock(ticker,pos.qty)
            if (buyingpower > 0 and stockList != None and stockList[0] != None):
                for i in stockList:
                    owned = False
                    for j in ownedStocks:
                        if (i.name == j.symbol):
                            owned = True
                            break
                    if (owned == False):
                        stocksToBuy.append(i.name)
                budget = buyingpower / len(stocksToBuy)
                for i in stocksToBuy:
                    price = float(api.get_position(i).current_price)
                    if (price > budget):
                        continue
                    else:
                        print ("Buying Stock: " + i)
                        shares = int(budget/price)
                        buyStock(i,shares)
                stockList = [None]
        elif (stockList == [None]):
            stockList = FindTop10(stockScreener(True,0,100,1,10,10))
        print("Restarting...")

TradingBot()
# Sell Parms
# % gain -> above 3%
# % loss -> loss 3%
# buy parms
# Make sure it's not at it's lowest value
# if theres a 20% increase (off current value) within the past 6 months pass
