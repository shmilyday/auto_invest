from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.technical import ma
import datetime,sys,json

# Load the config files                                                                                                                                                
with open('Configs/config.json','r') as f:                                                                                                                             
    config = json.loads(f.read().replace(r'\n','')) 

class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, sDate):
        strategy.BacktestingStrategy.__init__(self, feed, 500000)
        self.__sma = ma.SMA(feed[instrument].getCloseDataSeries(), 250)
        self.__instrument = instrument
	self.__position = None
	self.__biasParam = 0.0      #the bias for 60 days average
        self.__fundMax = 0
	self.__fundTotal = 0
	self.__sDate = sDate
	self.__aver_FundTotal = 0 # average fundTotal for one day
	self.__aver_Days = 0 # days for fundTotal
        self.__baseMoney = int(config['baseMoney'])

    def onStart(self):
	if self.__sDate == 0:
		self.__sDate = self.getFeed().getNextBars().getDateTime().strftime('%Y-%m-%d')
	print "OnBegin from %s" % self.__sDate
	print "OnStart: Initial Fund Value %.2f" % self.getBroker().getEquity()
	print "Tag,   Date,      profit,  bias, price,     shares,   buyMoney,TotalShares, TotalValue,  TotalFund"

    def onEnterOk(self, position):
	execInfo = position.getEntryOrder().getExecutionInfo()
	print "%s: BUY at $%.2f" % (execInfo.getDateTime(), execInfo.getPrice())

    def onEnterCanceled(self, position):
	pass

    def onExitOk(self, position):
	execInfo = position.getExitOrder().getExecutionInfo()
	print "%s: SELL at $%.2f" % (execInfo.getDateTime(), execInfo.getPrice())
	self.__position = None

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        self.__position.exit()

    def onBars(self, bars):
        bar = bars[self.__instrument]
	sma_value = self.__sma[-1]

        self.__aver_FundTotal += self.__fundTotal
        self.__aver_Days += 1

	if self.__sDate != 0 and bar.getDateTime() < datetime.datetime.strptime(self.__sDate,"%Y-%m-%d"):
		return

	if (sma_value is None):
		smaFt = 0
		sma_bias = 0
	else:
		smaFt = float(sma_value)
		sma_bias = (bar.getClose() - float(sma_value))/bar.getClose()

        # the total value of the share holder
        shareValue = self.getBroker().getShares(self.__instrument)*bar.getClose()
        if self.__fundTotal != 0:
                profitPer = (shareValue - self.__fundTotal) / self.__fundTotal
        else:
                profitPer = 0

	# the invest for each months, double invest if the negative bias is reached.
	if self.enterLongSignal(bar):
		# default, buy zero
		buyMoney = 0

                if (sma_bias <= self.__biasParam) and (self.__fundTotal < int(config['zone4_unit']) * self.__baseMoney):  
                    if (self.__fundTotal < (int(config['zone1_unit']) - 4) * self.__baseMoney):
                        buyMoney = self.__baseMoney
                    elif (profitPer <= float(config['buy_bias'])):
                        buyMoney = self.__baseMoney

		share = int(buyMoney/bar.getClose()) 

		self.marketOrder(self.__instrument, share, False, False)
		self.__fundTotal += buyMoney
		self.printStatusPost(sma_bias, profitPer, bar, "buy  ", share)
		return

	# zone1 profit reached and sell all of the shares
	if profitPer >= float(config['zone1_profit']):
		share = self.getBroker().getShares(self.__instrument)
		shareToSell = share
		self.marketOrder(self.__instrument, -shareToSell, False, False)
		self.__fundTotal -= self.__fundTotal
		self.printStatusPost(sma_bias, profitPer, bar, "zone1", -shareToSell)
		return
        
        # zone2 profit reached and sell zone2 shares
	if profitPer >= float(config['zone2_profit']) and self.__fundTotal > self.__baseMoney * int(config['zone1_unit']):
		share = self.getBroker().getShares(self.__instrument)
		shareToSell = share * (self.__fundTotal - self.__baseMoney * int(config['zone1_unit']))/self.__fundTotal
		self.marketOrder(self.__instrument, -shareToSell, False, False)
		self.__fundTotal = self.__baseMoney * int(config['zone1_unit'])
		self.printStatusPost(sma_bias, profitPer, bar, "zone2", -shareToSell)

        # zone3 profit reached and sell zone3 shares
	if profitPer >= float(config['zone3_profit']) and self.__fundTotal > self.__baseMoney * int(config['zone2_unit']):
		share = self.getBroker().getShares(self.__instrument)
                shareToSell = share * (self.__fundTotal - self.__baseMoney * int(config['zone2_unit']))/self.__fundTotal
                self.marketOrder(self.__instrument, -shareToSell, False, False)
                self.__fundTotal = self.__baseMoney * int(config['zone2_unit'])
                self.printStatusPost(sma_bias, profitPer, bar, "zone3", -shareToSell)

        # zone4 profit reached and sell zone4 shares
        if profitPer >= float(config['zone4_profit']) and self.__fundTotal > self.__baseMoney * int(config['zone3_unit']):
                share = self.getBroker().getShares(self.__instrument)
                shareToSell = share * (self.__fundTotal - self.__baseMoney * int(config['zone3_unit']))/self.__fundTotal
                self.marketOrder(self.__instrument, -shareToSell, False, False)
                self.__fundTotal = self.__baseMoney * int(config['zone3_unit'])
                self.printStatusPost(sma_bias, profitPer, bar, "zone4", -shareToSell)

    def printStatusPost(self, sma_bias, profit, bar, tag, share):
	print "%s, %s, %5.2f, %5.2f, %5.2f, %10.2f, %10.2f, %10.2f, %10.2f, %10.2f  " % (tag, bar.getDateTime().strftime('%Y-%m-%d'), profit, sma_bias, bar.getClose(), share, share*bar.getClose(), self.getBroker().getShares(self.__instrument) + share, (self.getBroker().getShares(self.__instrument) + share)*bar.getClose(), self.__fundTotal)
	if self.__fundMax < self.__fundTotal:
		self.__fundMax = self.__fundTotal

    def onFinish(self, position):
	print "OnFinish: Final Fund Value $%.2f" % self.getBroker().getEquity()
	year = int(self.getCurrentDateTime().strftime('%Y')) - int(self.__sDate[:4])
	aver = self.__aver_FundTotal / self.__aver_Days
	#print "fundtotal: aver days: %3.0f, %4.0f" % (self.__aver_FundTotal, self.__aver_Days)
	bonus = (self.getBroker().getEquity() - 500000) / year
	print "profit: %.2f and years: %.2f" % ((self.getBroker().getEquity() - 500000), year)
	print "Simple,   %3.0f,    %8.2f,  %9.2f,  %9.2f,     %5.1f%%" % (year, bonus , self.__fundMax, aver, 100 * bonus / aver)

    def enterLongSignal(self, bar):
	day = bar.getDateTime().strftime('%d')
	week = bar.getDateTime().strftime('%w')
	return day == '08' or (day == '09' and week == '1') or (day == '10' and week == '1')

    def exitLongSignal(self, bar):
        return bar.getClose() > self.__exitSMA[-1]

    def enterShortSignal(self, bar):
        return bar.getClose() < self.__entrySMA[-1] and self.__rsi[-1] >= self.__overBoughtThreshold

    def exitShortSignal(self, bar):
        return bar.getClose() < self.__exitSMA[-1]

if __name__ == '__main__':
	try:
		sDate = sys.argv[2]
	except:
		sDate = 0
	try:
		sFile = sys.argv[1]
	except:
                print "At least one csv File!"
		print "Usage: python ./auto_invest.py ./Data/CSV_file [Date]"

                exit(-1)

	# Load the yahoo feed from the CSV file
	feed = yahoofeed.Feed()
	feed.addBarsFromCSV("example", sFile)

	# Evaluate the strategy with the feed's bars.
	myStrategy = MyStrategy(feed, "example", sDate)
	myStrategy.run()
