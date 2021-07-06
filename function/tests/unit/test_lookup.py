## https://github.com/dsmorgan/yacgb
import pytest

import os, datetime, time
from datetime import timezone

from yacgb.lookup import ohlcvLookup
from yacgb.ohlcv_sync import save_candles, key_time
from model.market import Market, market_init
from model.ohlcv import OHLCV, ohlcv_init

local_dynamo_avail = pytest.mark.skipif(os.environ.get('DYNAMODB_HOST') == None, 
                        reason="No local dynamodb, e.g. export DYNAMODB_HOST=http://localhost:8000")


@pytest.fixture
def setup_market():
    test_market_symbols = ['XXX1/USD', 'YYY1/USD', 'ZZZ1/USD', 'XXX2/USD', 'YYY2/USD', 'ZZZ2/USD', 'XXX3/USD', 'YYY3/USD', 'ZZZ3/USD']
    test_exchange = 'pytest'
    nowdt = datetime.datetime.now(timezone.utc)
    thisminute = nowdt.replace(second=0, microsecond=0)
    
    market_init()
    
    for test_market in test_market_symbols:
        market_item = Market(test_exchange, 
                        test_market,
                        precision_base=0, 
                        precision_quote=0,
                        maker=0.016,
                        taker=0.026,
                        limits_amount_max=1000,
                        limits_amount_min=0.01,
                        limits_cost_max=100000,
                        limits_cost_min=0.01,
                        limits_price_max=100000,
                        limits_price_min=0)
        market_item.start_timestamp = int(nowdt.timestamp())
        market_item.start = str(nowdt)
        market_item.last_timestamp = int(thisminute.timestamp())
        market_item.last = str(nowdt)
        print ("Create market: ", test_exchange, test_market)
        market_item.save()
        
    yield (test_exchange, test_market_symbols)
    
    for test_market in test_market_symbols:
        print ("Delete market: ", test_exchange, test_market)
        m = Market(exchange=test_exchange, market=test_market)
        m.delete()

    
@local_dynamo_avail
def test_ohlcvLookup_market(setup_market):
    exch = setup_market[0]
    mkts = setup_market[1]
    testm = mkts.copy()
    testm.pop()
    x = ohlcvLookup(0.01,0.01,10,10)
    
    for mkt in mkts:
        print (exch, mkt)
        t = x.get_market(exch, mkt)
        assert t.exchange == 'pytest'
        assert t.market in mkts
    
    # changing sleep value allows for manipulation of caching
    #print("sleep")
    #time.sleep(1)
    t = x.get_market(exch, mkts[1])
    
    for mkt in testm:
        print (exch, mkt)
        t = x.get_market(exch, mkt)
        assert t.exchange == 'pytest'
        assert t.market in testm
    #assert len(testm) == 7
 
    
@pytest.fixture
def setup_ohlcv():
    ohlcv_init()
    ohlcv_list=[]
    nowdt = datetime.datetime.now(timezone.utc)
    ohlcv_path = "function/tests/unit/ohlcv_data/"
    included_extensions = ['.csv']
    file_names = [fn for fn in os.listdir(ohlcv_path)
              if any(fn.endswith(ext) for ext in included_extensions)]
    #print (file_names)
    for f in file_names:
        array = []
        with open(ohlcv_path + f, 'r') as fl:
            while line := fl.readline():
                #convert to 1 int and 5 floats
                l = line.rstrip().split(',', 5)
                l[0]=int(l[0])
                for x in [1,2,3,4,5]:
                    l[x]=float(l[x])
                array.append(l)
        #print (array)
        exchange = f.split('_', 1)[0]
        temp = f.split('_', 1)[1]
        ma = temp.split('__', 1)[0]
        mz = temp.split('__', 1)[1]
        mb = mz.split('_', 1)[0]
        market_symbol = ma + '/' + mb.split('_', 1)[0]
        timeframe = mz.split('_', 1)[1].rstrip('.csv')
        print (exchange, market_symbol, timeframe)
        #collect all OHLCV entries created by save_candles so they could be deleted later
        ohlcv_list += save_candles(exchange, market_symbol, timeframe, nowdt, array)
    
    print (len(ohlcv_list))
    # return list of exchange/market_symbol/timeframe and timestamps
    yield (ohlcv_list)
    
    #cleanup/delete all ohlvc entries created by save_candles
    for ol in ohlcv_list:
        i = OHLCV.get(ol[0], ol[1])
        i.delete()
        
@local_dynamo_avail
def test_ohlcvsync_savecandles(setup_ohlcv): 
    assert len(setup_ohlcv) == 228
    
    # Lookup each entry created
    for to in setup_ohlcv:
        exchange = to[0].split('_',2)[0]
        market_symbol = to[0].split('_',2)[1]
        timeframe = to[0].split('_',2)[2]
        ut = OHLCV.get(to[0], to[1])
        to1_dt = datetime.datetime.fromtimestamp(to[1]/1000, tz=timezone.utc)
        array0_dt = datetime.datetime.fromtimestamp(ut.array[0][0]/1000, tz=timezone.utc)

        # Will this always be true? Not if the 1st entry is missing! Future fix
        assert key_time(timeframe, to1_dt) == array0_dt
        
        if timeframe == '1m':
            assert len(ut.array) <=60
        elif timeframe == '1h':
            assert len(ut.array) <=24
        elif timeframe == '1d':
            assert len(ut.array) <=31
        else:
            #we should never get here
            print ("Invalid, bad timeframe:", timeframe)
            print ("to:", str(to))
            assert len(ut.array) <=-1
            
@local_dynamo_avail
def test_ohlcvLookup_ohlcv(setup_ohlcv):
    x = ohlcvLookup(1,1,10,10)
    
    # Lookup each entry created
    for to in setup_ohlcv[::20]:
        exchange = to[0].split('_',2)[0]
        market_symbol = to[0].split('_',2)[1]
        timeframe = to[0].split('_',2)[2]
        stime = to[1]
        result = x.get_ohlcv(exchange, market_symbol, timeframe, stime)
        
        # Will this always be true? Not if the 1st entry is missing! Future fix
        assert stime == result.array[0][0]

    # Lookup each entry created
    for to in setup_ohlcv[::10]:
        exchange = to[0].split('_',2)[0]
        market_symbol = to[0].split('_',2)[1]
        timeframe = to[0].split('_',2)[2]
        stime = to[1]
        result = x.get_ohlcv(exchange, market_symbol, timeframe, stime)
        
        # Will this always be true? Not if the 1st entry is missing! Future fix
        assert stime == result.array[0][0]
    
    timeframe = '1h'
    t = x.get_candle(exchange, market_symbol, timeframe, '20210704 18:12')
    assert t.valid == True
    assert t.open == 1.4484
    t = x.get_candle(exchange, market_symbol, timeframe, '20210704 20:14') 
    assert t.valid == True
    assert t.open == 1.4665
    assert t.high == 1.4687
    assert t.low == 1.4581
    assert t.close == 1.465
    assert t.volume == 1278500.92
    #after available ohlcv
    t = x.get_candle(exchange, market_symbol, timeframe, '20210705 20:00')
    assert t.valid == False
    assert t.open == 0
    #before available ohlcv
    t = x.get_candle(exchange, market_symbol, timeframe, '20210605 20:00')
    assert t.valid == False
    assert t.close == 0
    timeframe='1d'
    t = x.get_candle(exchange, market_symbol, timeframe, '20210605 20:00')
    assert t.valid == True
    assert t.close == 1.657
    timeframe='1m'
    #in source/file, but not in dynamodb
    t = x.get_candle(exchange, market_symbol, timeframe, '20210704 22:59')
    assert t.valid == False
    t = x.get_candle(exchange, market_symbol, timeframe, '20210704 23:14')
    assert t.valid == True
    assert t.close == 1.4602
    t = x.get_candle(exchange, market_symbol, timeframe, '20210704 23:17')
    #dump cache contents
    #print (x)
    assert t.valid == True
    assert t.close == 1.4654
    
    
        
        
    
    

    
    
    
    
    
    
    
     
