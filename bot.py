import time,logging
from binance.client import Client
from binance.enums import *
import pandas as pd
import ta
API_KEY="DBeCiuznieFtjYoXUaqbIdjLKYtKQ9IUY7OVNOV0FGTQgalWbLPRVyvt4uCL7WHP"
API_SECRET="Dt2fZUQP8rakkz9pZO8bDYWNvCtC24QkeS4c0ZPCB8tupU2j3Y5zJaub8KOdnwew"
SYMBOL="BTCUSDT"
LEVERAGE=5
TIMEFRAME="4h"
USDT_PER_TRADE=20
ATR_SL=1.5
ATR_TP=3.0
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s",handlers=[logging.FileHandler("bot.log"),logging.StreamHandler()])
log=logging.getLogger(__name__)
client=Client(API_KEY,API_SECRET)
def setup():
 try:
  client.futures_change_leverage(symbol=SYMBOL,leverage=LEVERAGE)
  client.futures_change_margin_type(symbol=SYMBOL,marginType="ISOLATED")
  log.info("OK")
 except:pass
def get_data():
 k=client.futures_klines(symbol=SYMBOL,interval=TIMEFRAME,limit=300)
 df=pd.DataFrame(k,columns=["t","o","h","l","c","v","ct","qv","tr","tbb","tbq","i"])
 for x in ["o","h","l","c"]:df[x]=pd.to_numeric(df[x])
 df["e21"]=ta.trend.ema_indicator(df["c"],window=21)
 df["e55"]=ta.trend.ema_indicator(df["c"],window=55)
 df["e200"]=ta.trend.ema_indicator(df["c"],window=200)
 df["rsi"]=ta.momentum.rsi(df["c"],window=14)
 df["atr"]=ta.volatility.average_true_range(df["h"],df["l"],df["c"],window=14)
 df["rs"]=df["rsi"].diff(3)
 return df
def get_pos():
 for p in client.futures_position_information(symbol=SYMBOL):
  a=float(p["positionAmt"])
  if a!=0:return a,float(p["entryPrice"])
 return 0,0
def get_qty(price):
 info=client.futures_exchange_info()
 for s in info["symbols"]:
  if s["symbol"]==SYMBOL:
   step=float([f for f in s["filters"] if f["filterType"]=="LOT_SIZE"][0]["stepSize"])
   qty=(USDT_PER_TRADE*LEVERAGE)/price
   return round(qty-(qty%step),8)
def long(price,atr):
 qty=get_qty(price)
 sl=round(price-ATR_SL*atr,2)
 tp=round(price+ATR_TP*atr,2)
 log.info("LONG "+str(price))
 client.futures_create_order(symbol=SYMBOL,side=SIDE_BUY,type=ORDER_TYPE_MARKET,quantity=qty)
 client.futures_create_order(symbol=SYMBOL,side=SIDE_SELL,type=FUTURE_ORDER_TYPE_STOP_MARKET,stopPrice=sl,closePosition=True)
 client.futures_create_order(symbol=SYMBOL,side=SIDE_SELL,type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,stopPrice=tp,closePosition=True)
def short(price,atr):
 qty=get_qty(price)
 sl=round(price+ATR_SL*atr,2)
 tp=round(price-ATR_TP*atr,2)
 log.info("SHORT "+str(price))
 client.futures_create_order(symbol=SYMBOL,side=SIDE_SELL,type=ORDER_TYPE_MARKET,quantity=qty)
 client.futures_create_order(symbol=SYMBOL,side=SIDE_BUY,type=FUTURE_ORDER_TYPE_STOP_MARKET,stopPrice=sl,closePosition=True)
 client.futures_create_order(symbol=SYMBOL,side=SIDE_BUY,type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,stopPrice=tp,closePosition=True)
def run():
 log.info("BOT STARTED")
 setup()
 while True:
  try:
   df=get_data()
   last=df.iloc[-1]
   prev=df.iloc[-3]
   c,e21,e55,e200,rsi,rs,atr=last["c"],last["e21"],last["e55"],last["e200"],last["rsi"],last["rs"],last["atr"]
   pos,entry=get_pos()
   cup=prev["e21"]<prev["e55"] and e21>e55
   cdn=prev["e21"]>prev["e55"] and e21<e55
   lsig=c>e200 and cup and 30<rsi<55 and rs>0
   ssig=c<e200 and cdn and 45<rsi<70 and rs<0
   log.info(str(c)+" RSI:"+str(round(rsi,1)))
   if pos==0:
    if lsig:long(c,atr)
    elif ssig:short(c,atr)
    else:log.info("waiting...")
   else:
    pnl=round((c-entry)/entry*100*LEVERAGE,2)
    log.info("pnl:"+str(pnl)+"%")
   time.sleep(300)
  except KeyboardInterrupt:break
  except Exception as e:log.error(str(e));time.sleep(60)
if __name__=="__main__":run()
