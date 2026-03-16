"""
@pyne
"""
from pynecore import pine_range
from pynecore.lib import (
    close, color, high, input, location, low, math, na, nz, plot, plotshape,
    script, shape, size, ta, volume
)
from pynecore.types import NA, Persistent, Series


@script.indicator("OBV MACD Indicator", overlay=False)
def main(
    len10=input.int(1, title="OBV Length "),
    type=input.string(defval="DEMA", title="MA Type", options=("TDEMA", "TTEMA", "TEMA", "DEMA", "EMA", "AVG", "THMA", "ZLEMA", "ZLDEMA", "ZLTEMA", "DZLEMA", "TZLEMA", "LLEMA", "NMA")),
    len=input.int(9, title="MA Length "),
    slow_length=input.int(title="MACD Slow Length", defval=26),
    len5=input.int(2),
    showsignal=input.bool(False),
    piv=input.bool(True, "Hide pivots?"),
    xbars=input.int(50, "period", minval=1)
):
    src1 = close
    window_len: int = 28

    v_len: int = 14
    price_spread = ta.stdev(high - low, window_len)

    v = math.sum(math.sign(ta.change(src1)) * volume, 0)
    smooth = ta.sma(v, v_len)
    v_spread = ta.stdev(v - smooth, v_len)
    shadow = (v - smooth) / v_spread * price_spread

    out = high + shadow if shadow > 0 else low + shadow

    obvema = ta.ema(out, len10)

    src = obvema

    showma: bool = True
    showma1: bool = False
    len1: int = 26
    showma2: bool = False
    len2: int = 52

    def nma(src, length1, length2):
        lambda__ = length1 / length2
        alpha = lambda__ * (length1 - 1) / (length1 - lambda__)
        ma1 = ta.ema(src, length1)
        ma2 = ta.ema(ma1, length2)
        return (1 + alpha) * ma1 - alpha * ma2

    def dema(src, len):
        ma1 = ta.ema(src, len)
        ma2 = ta.ema(ma1, len)
        return 2 * ma1 - ma2

    def tema(src, len):
        ma1 = ta.ema(src, len)
        ma2 = ta.ema(ma1, len)
        ma3 = ta.ema(ma2, len)
        return 3 * (ma1 - ma2) + ma3

    def tdema(src, len):
        ma1 = dema(src, len)
        ma2 = dema(ma1, len)
        ma3 = dema(ma2, len)
        return 3 * (ma1 - ma2) + ma3

    def ttema(src, len):
        ma1 = tema(src, len)
        ma2 = tema(ma1, len)
        ma3 = tema(ma2, len)
        return 3 * (ma1 - ma2) + ma3

    def tnma(src, len):
        ma1 = nma(src, len, 3)
        ma2 = nma(ma1, len, 3)
        ma3 = nma(ma2, len, 3)
        return 3 * (ma1 - ma2) + ma3

    def hma(src, len):
        return ta.wma(2 * ta.wma(src, len / 2) - ta.wma(src, len), math.round(math.sqrt(len)))

    def thma(src, len):
        ma1 = hma(src, len)
        ma2 = hma(ma1, len)
        ma3 = hma(ma2, len)
        return 3 * (ma1 - ma2) + ma3

    def zlema(src: Series, len):
        lag = math.round((len - 1) / 2)
        zlsrc = src + (src - src[lag])
        return ta.ema(zlsrc, len)

    def zldema(src: Series, len):
        lag = math.round((len - 1) / 2)
        zlsrc = src + (src - src[lag])
        return dema(zlsrc, len)

    def zltema(src: Series, len):
        lag = math.round((len - 1) / 2)
        zlsrc = src + (src - src[lag])
        return tema(zlsrc, len)

    def dzlema(src, len):
        ma1 = zlema(src, len)
        ma2 = zlema(ma1, len)
        return 2 * ma1 - ma2

    def tzlema(src, len):
        ma1 = zlema(src, len)
        ma2 = zlema(ma1, len)
        ma3 = zlema(ma2, len)
        return 3 * (ma1 - ma2) + ma3

    def llema(src: Series, len):
        srcnew = 0.25 * src + 0.5 * src[1] + 0.25 * src[2]
        return ta.ema(srcnew, len)

    def lltema(src: Series, len):
        srcnew = 0.25 * src + 0.5 * src[1] + 0.25 * src[2]
        return tema(srcnew, len)

    def myma(src, len):
        __block_result__ = na
        if type == 'EMA':
            __block_result__ = ta.ema(src, len)
        elif type == 'DEMA':
            __block_result__ = dema(src, len)
        elif type == 'TEMA':
            __block_result__ = tema(src, len)
        elif type == 'TDEMA':
            __block_result__ = tdema(src, len)
        elif type == 'TTEMA':
            __block_result__ = ttema(src, len)
        elif type == 'THMA':
            __block_result__ = thma(src, len)
        elif type == 'ZLEMA':
            __block_result__ = zlema(src, len)
        elif type == 'ZLDEMA':
            __block_result__ = zldema(src, len)
        elif type == 'ZLTEMA':
            __block_result__ = zltema(src, len)
        elif type == 'DZLEMA':
            __block_result__ = dzlema(src, len)
        elif type == 'TZLEMA':
            __block_result__ = tzlema(src, len)
        elif type == 'LLEMA':
            __block_result__ = llema(src, len)
        elif type == 'NMA':
            __block_result__ = nma(src, len, len1)
        else:
            __block_result__ = math.avg(ttema(src, len), tdema(src, len))
        return __block_result__

    ma = myma(src, len) if showma else na
    src12 = close
    plot(0, linewidth=3, color=color.black)

    slow_ma = ta.ema(src12, slow_length)
    macd = ma - slow_ma

    src5 = macd
    offset: int = 0

    def calcSlope(src5: Series, len5):
        sumX: float = 0.0
        sumY: float = 0.0
        sumXSqr: float = 0.0
        sumXY: float = 0.0
        for i in pine_range(1, len5):
            val = src5[len5 - i]
            per = i + 1.0
            sumX = sumX + per
            sumY = sumY + val
            sumXSqr = sumXSqr + per * per
            sumXY = sumXY + val * per

        slope = (len5 * sumXY - sumX * sumY) / (len5 * sumXSqr - sumX * sumX)
        average = sumY / len5
        intercept = average - slope * sumX / len5 + slope
        return (slope, average, intercept)

    tmp: Persistent[float] = na(float)
    s, a5, i = calcSlope(src5, len5)

    tt1 = i + s * (len5 - offset)

    p: int = 1
    src15 = tt1
    b5: Series[float] = 0.0
    dev5: Series[float] = 0.0
    oc: Series[int] = 0
    n5 = ta.cum(1) - 1
    a15 = ta.cum(math.abs(src15 - nz(b5[1], src15))) / n5 * p
    b5 = src15 if src15 > nz(b5[1], src15) + a15 else src15 if src15 < nz(b5[1], src15) - a15 else nz(b5[1], src15)

    dev5 = a15 if ta.change(b5) else nz(dev5[1], a15)

    oc = 1 if ta.change(b5) > 0 else -1 if ta.change(b5) < 0 else nz(oc[1])

    cs = color.blue if oc == 1 else color.red

    plot(b5, color=cs, linewidth=4, transp=50)

    down = ta.change(oc) < 0
    up = ta.change(oc) > 0
    plot(tt1 if showsignal and up else na, style=plot.style_cross, color=color.blue, linewidth=4, offset=-1)
    plot(tt1 if showsignal and down else na, style=plot.style_cross, color=color.red, linewidth=4, offset=-1)

    upper = tt1
    lower = tt1

    shrt: bool = False
    hb = math.abs(ta.highestbars(upper, xbars))
    lb = math.abs(ta.lowestbars(lower, xbars))

    max: Series = NA(float)
    max_upper: Series = NA(float)
    min: Series = NA(float)
    min_lower: Series = NA(float)
    pivoth = NA(bool)
    pivotl = NA(bool)

    max = close if hb == 0 else close if na(max[1]) else max[1]
    max_upper = upper if hb == 0 else upper if na(max_upper[1]) else max_upper[1]
    min = close if lb == 0 else close if na(min[1]) else min[1]
    min_lower = lower if lb == 0 else lower if na(min_lower[1]) else min_lower[1]

    if close > max:
        max = close
    if upper > max_upper:
        max_upper = upper
    if close < min_lower:
        min_lower = lower
    if lower < min_lower:
        min_lower = lower

    pivoth = True if max_upper == max_upper[2] and max_upper[2] != max_upper[3] else na
    pivotl = True if min_lower == min_lower[2] and min_lower[2] != min_lower[3] else na

    plotshape(na if piv else na if shrt else max_upper + 2 if pivoth else na, location=location.absolute, style=shape.labeldown, color=color.red, size=size.tiny, text='Pivot', textcolor=color.white, offset=0)
    plotshape(na if piv else na if shrt else min_lower - 2 if pivotl else na, location=location.absolute, style=shape.labelup, color=color.blue, size=size.tiny, text='Pivot', textcolor=color.white, offset=0)
