#/bin/bash

total=0
num=0
echo "  code, Simple, years, profitPyear,    fundMax,   averFund,  ratePyear" 

#for i in 000725 630005 601857 601288 600795 600276 600023 150023 100032 000018 000021 600190 000100 000016 601600 600383 160416 160719 510050 510880 159915 513100 159902 159920
#for i in 000725 630005 601857 601288 600795 600276 600023 100032 000018 000021 600190 000100 000016 601600 600383 160416 160719 510050 510880 159915 513100 159902 159920
#for i in 160416 160719 510050 510880 159902 159920
for i in `ls Data`
do
    result=`python auto_invest.py ./Data/$i |grep Simple`
    var=${result##*,}
    total=$(echo "$total+${var%?}"|bc)
    num=$(echo "$num+1"|bc)
    echo "$i, $result"
done

average=$(echo "scale=2;$total/$num"|bc)
echo "AVERAGE PROFIT:                                                 $average%"
