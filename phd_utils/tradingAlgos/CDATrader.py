# -*- coding: utf-8 -*-
"""
Created on Thu Aug 20 01:17:47 2015

@author: Desmond
"""

from __future__ import division
import numpy as np
import pandas as pd
import copy
from phd_utils.options.EuropeanOption import *
from phd_utils.assetPricing.models import *
from phd_utils.optionPricing.qntyModels import *
from phd_utils.optionPricing.models import *
from phd_utils.options.EuropeanCompoundOption import *
import scipy.optimize as optim
import scipy.stats as stats
import matplotlib.pyplot as plt

class CDATrader(object):
    def __init__(self, id,  **kwargs):
        self.id=id        
        self.assetPricingModel=kwargs['AssetPricingModel'] if 'AssetPricingModel' in kwargs else BrownianPricing(0.01, 0.05)
        self.optPricingModel=kwargs['OptionPricingModel'] if 'OptionPricingModel' in kwargs else MonteCarloPricing(self.assetPricingModel, 100)
        self.quantityModel=kwargs['QuantityModel'] if 'QuantityModel' in kwargs else RandomQuantity((-20,20))
        self.proxyTradingModel=kwargs['ProxyTradingModel'] if 'ProxyTradingModel' in kwargs else ZIPProxyAlgo()
        self.orders=None
        
    def updateOption(self, optionType):
        opt=copy.copy(optionType)
        self.orders=pd.DataFrame(self.optPricingModel.getPrices(opt, 1))        
        self.orders=self.quantityModel.getQuantities(self.orders, opt)
        self.orders.columns=['price', 'quantity', 'isLong']
        self.proxyTradingModel.option=opt
        self.proxyTradingModel.updateOptionPrice(self.orders['price'][0])
        
    def updateLastOrder(self, trades, lOrder):
        lastOrder=copy.copy(lOrder)
        lastOrder['ratio']=copy.copy(lastOrder['price'])/self.proxyTradingModel.price
        for t in trades:
            traderId1, side1, _=t['party1']
            traderId2, side2, _=t['party2']
            if traderId1==self.id:
                self.proxyTradingModel.cash-=float(t['quantity'])*float(t['price'])
                self.proxyTradingModel.utility+=float(t['quantity'])*self.proxyTradingModel.price-float(t['quantity'])*float(t['price'])
                self.proxyTradingModel.options+=t['quantity']
            if traderId2==self.id:
                self.proxyTradingModel.cash+=float(t['quantity'])*float(t['price'])
                self.proxyTradingModel.utility+=float(t['quantity'])*float(t['price'])-float(t['quantity'])*self.proxyTradingModel.price
                self.proxyTradingModel.options-=t['quantity']
        self.proxyTradingModel.update(trades, lastOrder)        
        
    def getOrder(self):
        qnty=np.random.randint(-2000, 2000)
        quote=self.proxyTradingModel.getBid() if qnty>0 else self.proxyTradingModel.getAsk()
        if np.isnan(quote): quote=0.001
            
        if hasattr(self.proxyTradingModel, 'action'):
            action=self.proxyTradingModel.action
        else:
            action='bid' if qnty>0 else 'ask'
        
        return {'type' : 'limit', 
                'side' : action, 
                'quantity' : abs(qnty)+1, 
                'price' : max(quote, 0.001),
                'trade_id' : self.id}

class BSProxyAlgo(object):
    def __init__(self, id):
        self.cash=0.0
        self.options=0
        self.utility=0.0
        self.trades=[]
        self.acceptedAsks=[]
        self.asks=[]
        self.rejectedAsks=[]
        self.acceptedBids=[]
        self.bids=[]
        self.rejectedBids=[]
        self.price=0
        self.id=id
        self.ob=None
        self.curAsk=0
        self.curBid=0
    
    def reset(self):
        self.cash=0.0
        self.options=0
        self.utility=0.0
        self.trades=[]
        self.acceptedAsks=[]
        self.asks=[]
        self.rejectedAsks=[]
        self.acceptedBids=[]
        self.bids=[]
        self.rejectedBids=[]
        self.price=0
        self.ob=None
        self.curAsk=0
        self.curBid=0
        
        
    def updateOptionPrice(self, price):
        self.price=price
    
    def update(self, trades, lOrder):
        pass
    
    def getBid(self):
        return self.price
    
    def getAsk(self):
        return self.price

class InformedProxyAlgo(object):
    def __init__(self, id, val, action):
        self.cash=0.0
        self.options=0
        self.utility=0.0
        self.value=val
        self.action=action
        self.trades=[]
        self.acceptedAsks=[]
        self.asks=[]
        self.rejectedAsks=[]
        self.acceptedBids=[]
        self.bids=[]
        self.rejectedBids=[]
        self.price=0
        self.id=id
        self.ob=None
        self.curAsk=0
        self.curBid=0
        
    def updateOptionPrice(self, price):
        self.price=price
    
    def update(self, trades, lOrder):
        pass
    
    def getBid(self):
        return self.value
    
    def getAsk(self):
        return self.value

class CopelandProxyAlgo(object):
    def __init__(self, id, theta):
        self.cash=0.0
        self.options=0
        self.utility=0.0
        self.theta=theta
        self.trades=[]
        self.acceptedAsks=[]
        self.asks=[]
        self.rejectedAsks=[]
        self.acceptedBids=[]
        self.bids=[]
        self.rejectedBids=[]
        self.price=0
        self.id=id
        self.ob=None
        self.curAsk=0
        self.curBid=0
    
    def reset(self):
        self.cash=0.0
        self.options=0
        self.utility=0.0
        self.trades=[]
        self.acceptedAsks=[]
        self.asks=[]
        self.rejectedAsks=[]
        self.acceptedBids=[]
        self.bids=[]
        self.rejectedBids=[]
        self.price=0
        self.ob=None
        self.curAsk=0
        self.curBid=0
        
    def updateOptionPrice(self, price):
        self.price=price
    
    def update(self, trades, lastOrder):
        if lastOrder['side']=='ask':
            self.asks.append(lastOrder)
            if lastOrder['isFilled']:
                self.acceptedAsks.append(lastOrder)
            else:
                self.rejectedAsks.append(lastOrder)
        else:
            self.bids.append(lastOrder)
            if lastOrder['isFilled']:
                self.acceptedBids.append(lastOrder)
            else:
                self.rejectedBids.append(lastOrder)

    def getLambdaAsk(self, ratio):
        return 5-(5/self.price)*(ratio*self.price-self.price)
    
    def getLambdaBid(self, ratio):
        return (5/self.price)*(ratio*self.price-self.price)
    
    def getPrices(self):
        def copelandObjective(ratios):
            r_a, r_b=ratios
            p_a, p_b=self.price*r_a, self.price*r_b
#            phi_b=float(max(1.5-r_a,0)/1.5)
#            phi_a=r_b
            puni=np.array([p_a-self.price, self.price-p_b])
            pinf=np.array([max(euroCompound(self.option.S0, self.option.K, p_a, self.option.r, self.option.T-0.0001, self.option.T, self.option.sigma, 1),0), max(euroCompound(self.option.S0, self.option.K, p_b, self.option.r, self.option.T-0.0001, self.option.T, self.option.sigma, 3),0)])
            lambdas=np.array([self.getLambdaAsk(r_a), self.getLambdaBid(r_b)])
            obj=np.dot((1-self.theta)*puni-self.theta*pinf, lambdas)
            return -obj
            
        r_a, r_b=optim.fmin(copelandObjective, [1.05,0.95], disp=0)
        p_a, p_b=self.price*r_a, self.price*r_b
        puni=np.array([(p_a-self.price), (self.price-p_b)])
        pinf=np.array([max(euroCompound(self.option.S0, self.option.K, p_a, self.option.r, self.option.T-0.0001, self.option.T, self.option.sigma, 1),0), max(euroCompound(self.option.S0, self.option.K, p_b, self.option.r, self.option.T-0.0001, self.option.T, self.option.sigma, 3),0)])
        obj=(1-self.theta)*sum(puni)-self.theta*sum(pinf)
        
        #print r_a, r_b, puni, pinf, obj
        self.curAsk=p_a
        self.curBid=max(p_b,0)
    
    def getBid(self):
        self.getPrices()
        return self.curBid
    
    def getAsk(self):
        self.getPrices()
        return self.curAsk

                
class GarmanProxyAlgo(object):
    def __init__(self, id, cash, options):
        self.initCash=cash
        self.initOptions=options
        self.cash=cash
        self.options=options
        self.utility=0
        self.trades=[]
        self.acceptedAsks=[]
        self.asks=[]
        self.rejectedAsks=[]
        self.acceptedBids=[]
        self.bids=[]
        self.rejectedBids=[]
        self.price=0
        self.id=id
        self.ob=None
        self.curAsk=0
        self.curBid=0
    
    def reset(self):
        self.cash=self.initCash
        self.options=self.initOptions
        self.utility=0
        self.trades=[]
        self.acceptedAsks=[]
        self.asks=[]
        self.rejectedAsks=[]
        self.acceptedBids=[]
        self.bids=[]
        self.rejectedBids=[]
        self.price=0
        self.ob=None
        self.curAsk=0
        self.curBid=0
        
    def updateOptionPrice(self, price):
        self.price=price
    
    def update(self, trades, lastOrder):
        if lastOrder['side']=='ask':
            self.asks.append(lastOrder)
            if lastOrder['isFilled']:
                self.acceptedAsks.append(lastOrder)
            else:
                self.rejectedAsks.append(lastOrder)
        else:
            self.bids.append(lastOrder)
            if lastOrder['isFilled']:
                self.acceptedBids.append(lastOrder)
            else:
                self.rejectedBids.append(lastOrder)

    def getLambdaAsk(self, ratio):
        return float(max(4000.0-2000.0*ratio,0))
    
    def getLambdaBid(self, ratio):
        return float(2000.0*ratio)
        
    def getPrices(self):
        def garmanObjective(ratios):
            r_a, r_b=ratios
            p_a, p_b=self.price*r_a, self.price*r_b
            if np.any(np.array([p_a, p_b])==0):
                return 1.0
            elif p_a*self.getLambdaAsk(r_a) < p_b*self.getLambdaBid(r_b):
                return 1.0
            elif self.getLambdaBid(r_b) < self.getLambdaAsk(r_a):
                return 1.0
            else:
                return 0.5*(((self.getLambdaBid(r_b)*p_b)/(self.getLambdaAsk(r_a)*p_a))**(self.cash/self.price)+(self.getLambdaAsk(r_a)/self.getLambdaBid(r_b))**float(self.options))
        r_a, r_b =optim.fmin(garmanObjective, [1.05,1], disp=0)
        self.curAsk=self.price*r_a
        self.curBid=self.price*r_b
    
    def getBid(self):
        self.getPrices()
        return self.curBid
    
    def getAsk(self):
        self.getPrices()
        return self.curAsk
        
class GDProxyAlgo(object):
    def __init__(self, id):
        self.cash=0.0
        self.options=0
        self.utility=0.0
        self.price=0
        self.acceptedAsks=[]
        self.asks=[]
        self.rejectedAsks=[]
        self.acceptedBids=[]
        self.bids=[]
        self.rejectedBids=[]
        self.ob=None
        self.id=id
        self.curAsk=0
        self.curBid=0

    def reset(self):
        self.cash=0.0
        self.options=0
        self.utility=0.0
        self.price=0
        self.acceptedAsks=[]
        self.asks=[]
        self.rejectedAsks=[]
        self.acceptedBids=[]
        self.bids=[]
        self.rejectedBids=[]
        self.ob=None
        self.curAsk=0
        self.curBid=0

    def updateOptionPrice(self, price):
        self.price=price
        
    def update(self, trades, lastOrder):
        if lastOrder['side']=='ask':
            self.asks.append(lastOrder)
            if lastOrder['isFilled']:
                self.acceptedAsks.append(lastOrder)
            else:
                self.rejectedAsks.append(lastOrder)
        else:
            self.bids.append(lastOrder)
            if lastOrder['isFilled']:
                self.acceptedBids.append(lastOrder)
            else:
                self.rejectedBids.append(lastOrder)
    
    def totalAcceptedBids(self, ratio):
        return len([o for o in self.acceptedBids if ratio<=o['ratio']])
    
    def totalRejectedBids(self, ratio):
        return len([o for o in self.rejectedBids if ratio>=o['ratio']])
        
    def totalBids(self, ratio):
        return len([o for o in self.bids if ratio>=o['ratio']])        

    def totalAcceptedAsks(self, ratio):
        return len([o for o in self.acceptedAsks if ratio>=o['ratio']])
    
    def totalRejectedAsks(self, ratio):
        return len([o for o in self.rejectedAsks if ratio<=o['ratio']])

    def totalAsks(self, ratio):
        return len([o for o in self.asks if ratio<=o['ratio']])
    
    def getCurBounds(self):
        bestAsk=self.ob.get_best_ask() if self.ob.get_best_ask() else self.price*np.random.uniform(1.00, 1.05)
        bestBid=self.ob.get_best_bid() if self.ob.get_best_bid() else self.price*np.random.uniform(0.95, 1.00)
        if bestBid>bestAsk: bestBid=bestAsk*np.random.uniform(0.95, 1.00)
        return bestBid/self.price, bestAsk/self.price
        
    def getBidSuccessProb(self, ratio):
        denom=self.totalAcceptedBids(ratio)+self.totalAsks(ratio)+self.totalRejectedBids(ratio)
        numer=self.totalAcceptedBids(ratio)+self.totalAsks(ratio)
        
        if denom==0: return 0
        return numer/denom
    
    def getAskSuccessProb(self, ratio):
        denom=self.totalAcceptedAsks(ratio)+self.totalBids(ratio)+self.totalRejectedAsks(ratio)
        numer=self.totalAcceptedAsks(ratio)+self.totalBids(ratio)
        
        if denom==0: return 0
        return numer/denom
    
    def getBid(self):
        def objFunc(ratio):
            #if ratio>=1: return 0
            return -(1-ratio)*self.price*self.getBidSuccessProb(ratio)
        b1, b2=self.getCurBounds()
        bestRatio=optim.fminbound(objFunc, b1, b2)
        self.curBid=bestRatio*self.price
        return self.curBid
    
    def getAsk(self):
        def objFunc(ratio):
            #if ratio<=1: return 0
            return -(ratio-1)*self.price*self.getAskSuccessProb(ratio)       
        #maxRatio=np.max([o['ratio'] for o in self.bids]) if len(self.bids) else 2
        b1, b2=self.getCurBounds()
        bestRatio=optim.fminbound(objFunc, b1, b2)
        self.curAsk=bestRatio*self.price
        return self.curAsk
        
class ZIPProxyAlgo(object):
    def __init__(self, id, beta=0, gamma=0):
        self.cash=0.0
        self.options=0
        self.utility=0.0
        self.price=0
        self.id=id
        self.curBid=None
        self.curAsk=None
        self.curBidMargin=np.random.uniform(0.1, 0.5)
        self.curAskMargin=np.random.uniform(0.1, 0.5)
        self.curBidGamma=0
        self.curAskGamma=0
        self.beta=np.random.uniform(0.1,0.5) if not beta else beta ## learning coef
        self.gamma=np.random.uniform(0.0,1.0) if not gamma else gamma ## momentum on trend
    
    def reset(self):
        self.cash=0.0
        self.options=0
        self.utility=0.0
        self.price=0
        self.curBid=None
        self.curAsk=None
        self.curBidMargin=np.random.uniform(0.1, 0.5)
        self.curAskMargin=np.random.uniform(0.1, 0.5)
        self.curBidGamma=0
        self.curAskGamma=0
        self.beta=np.random.uniform(0.1,0.5) ## learning coef
        self.gamma=np.random.uniform(0.0,1.0) ## momentum on trend
    
    def updateOptionPrice(self, price):
        self.price=price+0.001
        self.curBid=price
        self.curAsk=price
        self.curBidMargin=np.random.uniform(0.1, 0.5)
        self.curAskMargin=np.random.uniform(0.1, 0.5)
        self.curBidGamma=0
        self.curAskGamma=0
    
    def update(self, trades, lastOrder):
        if (lastOrder['isFilled']):
            if self.curBid>lastOrder['price']:
                self.decreaseBid(lastOrder['price'])
            if lastOrder['side']=='ask' and self.curBid<lastOrder['price']:
                self.increaseBid(lastOrder['price'])
        else:
            if lastOrder['side']=='bid' and self.curBid<lastOrder['price']:
                self.increaseBid(lastOrder['price'])

        if (lastOrder['isFilled']):
            if self.curAsk<lastOrder['price']:
                self.increaseAsk(lastOrder['price'])
            if lastOrder['side']=='bid' and self.curAsk>lastOrder['price']:
                self.decreaseAsk(lastOrder['price'])
        else:
            if lastOrder['side']=='ask' and self.curAsk<lastOrder['price']:
                self.decreaseAsk(lastOrder['price'])
    
    def getBid(self):
        return self.curBid
        
    def getAsk(self):
        return self.curAsk
    
    def decreaseBid(self, p):
        self.curBidGamma=self.gamma*self.curBidGamma+(1-self.gamma)*self.getDelta(p, True)
        self.curBidMargin=(self.curBid+self.curBidGamma)/self.price-1
        self.curBid=self.price*(1+self.curBidMargin)
    
    def increaseBid(self, p):
        bidGamma=self.gamma*self.curBidGamma+(1-self.gamma)*self.getDelta(p, False)
        bidMargin=(self.curBid+bidGamma)/self.price-1
        self.curBidGamma=bidGamma
        self.curBidMargin=bidMargin
        self.curBid=self.price*(1+self.curBidMargin)
        
    def decreaseAsk(self, p):
        askGamma=self.gamma*self.curAskGamma+(1-self.gamma)*self.getDelta(p, True)
        askMargin=(self.curAsk+askGamma)/self.price-1
        self.curAskGamma=askGamma
        self.curAskMargin=askMargin
        self.curAsk=self.price*(1+self.curAskMargin)
        
    def increaseAsk(self, p):
        self.curAskGamma=self.gamma*self.curAskGamma+(1-self.gamma)*self.getDelta(p, False)
        self.curAskMargin=(self.curAsk+self.curAskGamma)/self.price-1
        self.curAsk=self.price*(1+self.curAskMargin)
    
    def getDelta(self, p, isUp):
        return self.beta*(self.getTau(p, isUp)-p)
    
    def getTau(self, p, isUp):
        if (isUp):
            R=np.random.uniform(1.0, 1.05)
            A=np.random.uniform(0.0, 0.05)
        else:
            R=np.random.uniform(0.95, 1)
            A=np.random.uniform(-0.05, 0)
            
        return R*p+A