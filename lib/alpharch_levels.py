"""Deterministic concentrations, separated by data type, instrument and expiry.

A concentration is evidence about a supplied metric, never a support/resistance
prediction or a claim about dealer inventory. No model and no order interface.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone
import math
from statistics import median


def concentrations(rows, *, source, timestamp, instrument, metric,
                   threshold=3.0, expiry=None, side=None, minimum_samples=3):
    clean = [(float(p), float(v)) for p, v in rows
             if math.isfinite(float(p)) and math.isfinite(float(v)) and float(v)>0]
    if len(clean)<minimum_samples:
        return []
    baseline=median(v for _,v in clean)
    return [{'id':f'{source}:{instrument}:{metric}:{expiry}:{side}:{p}',
             'source':source,'timestamp':timestamp,'instrument':instrument,
             'metric':metric,'expiry':expiry,'side':side,'price':p,'value':v,
             'baseline':baseline,'baseline_method':'median of positive levels in this snapshot/group',
             'samples':len(clean),'threshold':threshold,'ratio':v/baseline}
            for p,v in clean if v>=baseline*threshold]


def options_levels(chain, *, timestamp, now, threshold=3.0, max_age=120):
    if now-timestamp>max_age:
        return []
    groups=defaultdict(list)
    for row in chain:
        try:
            underlying,date,strike,side=row['instrument_name'].split('-')
            expiry=datetime.strptime(date,'%d%b%y').replace(hour=8,tzinfo=timezone.utc).timestamp()
            oi=float(row.get('open_interest') or 0)
            if expiry<=now or side not in ('C','P') or not math.isfinite(oi):
                continue
            groups[(underlying,date,side)].append((float(strike),oi))
        except (ValueError,KeyError,TypeError):
            continue
    result=[]
    for (instrument,expiry,side),rows in groups.items():
        result.extend(concentrations(rows,source='Deribit REST',timestamp=timestamp,
                                     instrument=instrument,metric='options_open_interest',
                                     expiry=expiry,side=side,threshold=threshold))
    return result


class LevelTracker:
    def __init__(self, cooldown=60, material_change=.25):
        self.active={}
        self.last_alert={}
        self.history=deque(maxlen=500)
        self.cooldown=cooldown
        self.material_change=material_change

    def update(self, levels, now, max_age=120):
        current={x['id']:x for x in levels if 0<=now-x['timestamp']<=max_age}
        notifications=[]
        for key,old in self.active.items():
            if key not in current:
                self.history.append({'event':'retired','time':now,'level':old,
                                     'reason':'stale or absent from current supplied snapshot'})
        for key,value in current.items():
            old=self.active.get(key)
            event='appeared' if old is None else 'changed'
            changed=old is None or abs(value['value']-old['value'])/max(old['value'],1e-12)>=self.material_change
            if changed:
                evidence={'event':event,'time':now,'level':value}
                self.history.append(evidence)
                if now-self.last_alert.get(key,float('-inf'))>=self.cooldown:
                    notifications.append(evidence)
                    self.last_alert[key]=now
        self.active=current
        return notifications
