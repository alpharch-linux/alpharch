"""Event bars from actual retained trades; no splitting or invented prints."""
from decimal import Decimal


def event_bars(trades,kind,size,tick):
    size=Decimal(str(size));tick=Decimal(str(tick))
    if kind not in ('ticks','volume','range') or not size.is_finite() or size<=0 or size>1000000:
        raise ValueError('Invalid event bar setting')
    if kind in ('ticks','range') and size!=size.to_integral_value():raise ValueError('Use whole trades or ticks.')
    result=[];bar=None;cells={}
    def pack(bar,cells):
        row={k:float(v) if isinstance(v,Decimal) else v for k,v in bar.items()}
        row['footprint']=[[float(p),float(q[0]),float(q[1])] for p,q in sorted(cells.items())]
        return row
    for trade in trades:
        p,q,side=trade['p'],trade['q'],trade['side']
        if bar is None:
            bar={'startId':str(trade.get('id',trade['t'])),'t':trade['t'],'end':trade['t'],'o':p,'h':p,'l':p,'c':p,'v':Decimal(0),'buy':Decimal(0),'sell':Decimal(0),'pv':Decimal(0),'trades':0,'complete':False};cells={}
        bar['end']=trade['t'];bar['h']=max(bar['h'],p);bar['l']=min(bar['l'],p);bar['c']=p;bar['v']+=q;bar['pv']+=p*q;bar['trades']+=1
        if side is None:bar['buy']=None;bar['sell']=None
        else:
            if bar[side] is not None:bar[side]+=q
            cells.setdefault(p,[Decimal(0),Decimal(0)])[0 if side=='sell' else 1]+=q
        complete=bar['trades']>=size if kind=='ticks' else bar['v']>=size if kind=='volume' else bar['h']-bar['l']>=size*tick
        if complete:
            bar['complete']=True;result.append(pack(bar,cells));bar=None
    if bar:result.append(pack(bar,cells))
    return result
