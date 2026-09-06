"""Shared public feeds with explicit browser and recorder ownership."""
import asyncio
from alpharch_public import Market

class Streams:
    def __init__(self, factory=Market):
        self.factory=factory
        self.markets={}
        self.tasks={}
        self.owners={}

    async def set(self, owner, keys):
        self.owners[owner]=set(keys)
        wanted=set().union(*self.owners.values()) if self.owners else set()
        for key in wanted-self.markets.keys():
            self.markets[key]=self.factory(*key.split(':'))
            self.tasks[key]=asyncio.create_task(self.markets[key].run())
        obsolete=[]
        for key in self.markets.keys()-wanted:
            obsolete.append(self.tasks.pop(key));self.markets.pop(key)
        for task in obsolete:task.cancel()
        await asyncio.gather(*obsolete,return_exceptions=True)

    async def remove(self, owner):
        self.owners.pop(owner,None)
        # Reconcile without retaining a placeholder owner.
        token=object();await self.set(token,set());self.owners.pop(token,None)

    async def close(self):
        self.owners.clear()
        await self.set(None,set());self.owners.clear()
