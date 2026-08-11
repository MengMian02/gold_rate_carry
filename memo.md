# Memo

This strategy tests the simple economic intuition that gold and interest-bearing assets are substitutes in portfolio construction. Gold can be modelled as a bond that generates no coupon and no maturity date. Following the formula of price = 1/(1+r)^T, price sensitivity to a change in r grows with T.

The real yield is the relevant rate since it isolates the opportunity cost channel specifically (Barsky & Summers, 1988). The nominal yield bundles the real yield and the inflation expectations, which affect the gold price in opposite directions. Using DFII10 removes the offsetting channel. The strategy tests over a chosen lookback window, whether the fall in real yield is followed by gold returns that beat a randomly timed benchmark with matched market exposure.

However, the assumption of the negative correlation between gold price and real interest rate may break down, as evidenced by a report by the European Central Bank that documented this occurrence in 2022 following the Russia’s invasion of Ukraine. Both real yield and gold prices increased during the same period of time due to geopolitical concerns as central banks in economies like China began adding more gold to their reserves for fear of sanctions (World Gold Council).

The results of the project support the earlier argument, as implementing the strategy between 2008 and 2021 achieved a positive Sharpe ratio that ranked at the 98.2nd percentile of exposure-matched random timing alternatives. However, the result between 2022 and 2024 showed otherwise, beating 8.8%, with Sharpe ratio statistically indistinguishable from 0. The mechanism fails to add value once central-bank buying plausibly became a dominant competing driver.

A main limitation of this test is that the 2022 regime separation boundary was chosen with this breakdown already publicly documented, rather than discovered independently from data. This result therefore should be interpreted as a confirmation of a known structural break. In the actual implementation, it is important to follow updated economic research on trends in the industry.

Persistence depends on whether central bank buying reflects a temporary geopolitical response or a structural shift in the reserve management. Continuous high demand in the recent two years shows that it is not something that fades easily. Whether it will become a new norm is worth analysing.

Verdict: Monitor. The mechanism is real and statistically supported in the regime where it was tested, but it is currently dominated by a force outside of the model’s scope. The strategy should not be pursued outright in the current economic condition.
