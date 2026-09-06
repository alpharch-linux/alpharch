"""Observed market facts and separately sourced public options concentrations."""
import asyncio
from decimal import Decimal
import time
from alpharch_levels import concentrations, options_levels
from alpharch_public import request_json


def observations(market):
    bars, profile, trades=market.trade_data()
    buy=sum((q[0] for q in profile.values()),Decimal(0))
    sell=sum((q[1] for q in profile.values()),Decimal(0))
    unknown=sum((q[2] for q in profile.values()),Decimal(0))
    volume=buy+sell+unknown
    pv=sum((p*sum(q) for p,q in profile.items()),Decimal(0))
    now=time.time()
    fresh=market.connected and market.book_received is not None and now-market.book_received<=15
    levels=[]
    if fresh:
        for side, book in (('bid',market.bids),('ask',market.asks)):
            levels.extend(concentrations(sorted(book.items(),reverse=side=='bid')[:100],source=market.provider,
                          timestamp=market.book_time,instrument=market.symbol,metric='displayed_depth',side=side))
    levels=sorted(levels,key=lambda r:r['ratio'],reverse=True)[:12]
    return {'source':market.provider,'symbol':market.symbol,'asOf':now,'trades':len(trades),
            'from':trades[0]['t'] if trades else None,'to':trades[-1]['t'] if trades else None,
            'high':str(max(profile)) if profile else None,'low':str(min(profile)) if profile else None,
            'buy':str(buy) if not unknown else None,'sell':str(sell) if not unknown else None,'volume':str(volume),'delta':str(buy-sell) if not unknown else None,'unclassifiedVolume':str(unknown),
            'vwap':str(pv/volume) if volume else None,'partial':market.gap,'levels':levels,
            'definitions':{'scope':'Retained captured trades only, at most 30,000; not an exchange-wide session total.',
                'delta':'Buyer-aggressor quantity minus seller-aggressor quantity in base asset units.',
                'level':'Displayed quantity at least three times the median positive level quantity on the same side, among the nearest 100 available levels. Orders can be cancelled; this is not a support/resistance prediction.'}}


class Options:
    def __init__(self):self.cache={};self.locks={}
    async def get(self,asset):
        if asset not in ('BTC','ETH'):raise ValueError('Deribit options context is available for BTC and ETH.')
        lock=self.locks.setdefault(asset,asyncio.Lock())
        async with lock:
            now=time.time();cached=self.cache.get(asset)
            if cached and now-cached['fetchedAt']<60:return cached
            try:
                data=await asyncio.to_thread(request_json,'https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency='+asset+'&kind=option')
                rows=data['result'];stamp=time.time()
                result={'asset':asset,'source':'Deribit public options','fetchedAt':stamp,'status':'receiving',
                        'instruments':len(rows),'levels':sorted(options_levels(rows,timestamp=stamp,now=stamp),key=lambda v:v['ratio'],reverse=True)[:100],
                        'definition':'Open-interest concentrations ≥3× median within the same underlying, expiry and put/call group. OI uses provider instrument amount units. Not dealer positioning, gamma exposure or a trading signal.'}
            except Exception:
                result={'asset':asset,'source':'Deribit public options','fetchedAt':time.time(),'status':'unavailable','levels':[],
                        'definition':'Public options request failed; no prior levels are presented as fresh.'}
            self.cache[asset]=result
            return result
