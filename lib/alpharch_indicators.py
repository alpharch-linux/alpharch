"""Indicator arithmetic over supplied bars. None explicitly means warming up.

EMA seeds with an n-bar SMA; RMA uses Wilder's 1/n smoothing. Bollinger bands
use population standard deviation. Flat RSI is 50. No candle-derived delta.
"""
from math import sqrt


def sma(values, period):
    result=[]
    for i in range(len(values)):
        window=values[max(0,i-period+1):i+1]
        result.append(sum(window)/period if len(window)==period and all(v is not None for v in window) else None)
    return result


def smooth(values, period, alpha):
    out=[];seed=[];previous=None
    for value in values:
        if value is None:
            out.append(None);continue
        if previous is None:
            seed.append(value)
            if len(seed)==period:previous=sum(seed)/period
        else:previous=alpha*value+(1-alpha)*previous
        out.append(previous)
    return out


def ema(values,period):return smooth(values,period,2/(period+1))
def rma(values,period):return smooth(values,period,1/period)


def calculate(bars, name, period=14, source='close', multiplier=2):
    if type(period) is not int or not 2<=period<=200:
        raise ValueError('period must be 2–200')
    if source not in ('close','open','high','low','hlc3'):
        raise ValueError('unsupported price source')
    if not 0<multiplier<=10:
        raise ValueError('multiplier must be greater than 0 and at most 10')
    values=[(b['high']+b['low']+b['close'])/3 if source=='hlc3' else b[source] for b in bars]
    if name=='sma':return {'value':sma(values,period)}
    if name=='ema':return {'value':ema(values,period)}
    if name=='bollinger':
        mid=sma(values,period);deviation=[sqrt(sum((x-mid[i])**2 for x in values[i-period+1:i+1])/period) if mid[i] is not None else None for i in range(len(values))]
        return {'value':mid,'upper':[m+multiplier*d if m is not None else None for m,d in zip(mid,deviation)],'lower':[m-multiplier*d if m is not None else None for m,d in zip(mid,deviation)]}
    if name=='atr':
        tr=[b['high']-b['low'] if i==0 else max(b['high']-b['low'],abs(b['high']-bars[i-1]['close']),abs(b['low']-bars[i-1]['close'])) for i,b in enumerate(bars)]
        return {'value':rma(tr,period)}
    if name=='rsi':
        changes=[values[i]-values[i-1] for i in range(1,len(values))]
        gains=rma([max(v,0) for v in changes],period);losses=rma([max(-v,0) for v in changes],period)
        result=[None] if values else []
        result += [None if g is None else 50 if g==0 and l==0 else 100 if l==0 else 100-100/(1+g/l) for g,l in zip(gains,losses)]
        return {'value':result}
    if name=='macd':
        fast,slow=ema(values,12),ema(values,26)
        macd=[a-b if a is not None and b is not None else None for a,b in zip(fast,slow)]
        signal=ema(macd,9)
        return {'value':macd,'signal':signal,'histogram':[a-b if a is not None and b is not None else None for a,b in zip(macd,signal)]}
    if name=='stochastic':
        k=[]
        for i,b in enumerate(bars):
            if i+1<period:k.append(None);continue
            window=bars[i-period+1:i+1];low=min(x['low'] for x in window);high=max(x['high'] for x in window)
            k.append(50 if high==low else 100*(b['close']-low)/(high-low))
        return {'value':k,'signal':sma(k,3)}
    if name=='volume':return {'value':[b['volume'] for b in bars]}
    raise ValueError('unsupported indicator')
