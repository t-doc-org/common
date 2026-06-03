// Copyright 2026 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

// Return the greatest common divisor of two natural numbers.
export function gcd(a, b) {
    while (b != 0) [a, b] = [b, a % b];
    return a;
}

// Add v to sum, using Neumaier's algorithm.
// https://en.wikipedia.org/wiki/Kahan_summation_algorithm#Further_enhancements
export function add(v, sum, e = 0) {
    const t = sum + v;
    return Math.abs(sum) >= Math.abs(v) ? [t, e + (sum - t) + v]
                                        : [t, e + (v - t) + sum];
}

// Return the sum of the values of an iterable, using Neumaier's algorithm.
// https://en.wikipedia.org/wiki/Kahan_summation_algorithm#Further_enhancements
export function sum(values) {
    let sum = 0, e = 0;
    for (const v of values) [sum, e] = add(v, sum, e);
    return sum;
}

// A statistical sample.
export class Sample {
    constructor(values) {
        values.sort((a, b) => a - b);
        this.values = values;
        this._cache = {};
    }

    get length() { return this.values.length; }
    [Symbol.iterator]() { return this.values[Symbol.iterator](); }

    get count() { return this.values.length; }
    get min() { return this.values[0]; }
    get max() { return this.values[this.values.length - 1]; }
    get range() { return this.max - this.min; }
    get median() { return this.quantile(0.5); }
    quartile(k) { return this.quantile(k / 4); }
    percentile(p) { return this.quantile(p / 100); }

    quantile(p) {
        const len = this.values.length;
        if (len === 0) return NaN;
        const ri = (len - 1) * p, i = Math.floor(ri), f = ri - i;
        return (1 - f) * this.values[i] + (f > 0 ? f * this.values[i + 1] : 0);
    }

    get mean() {
        if (this._cache.mean !== undefined) return this._cache.mean;
        if (this.values.length < 1) return this._cache.mean = NaN;
        return this._cache.mean = sum(this.values) / this.values.length;
    }

    get variance() {
        if (this._cache.variance !== undefined) return this._cache.variance;
        const values = this.values;
        if (values.length < 2) return this._cache.variance = NaN;
        const m = this.mean;
        function* gen() {
            for (const v of values) yield Math.pow(v - m, 2);
        }
        return this._cache.variance = sum(gen()) / (values.length - 1);
    }

    get stdDev() { return Math.sqrt(this.variance); }

    avgDev(m) {
        const values = this.values;
        if (values.length < 1) return NaN;
        function* gen() {
            for (const v of values) yield Math.abs(v - m);
        }
        return sum(gen()) / values.length;
    }

    // Compute a distribution from the sample, using the given bins.
    distribution(bins) {
        const dist = new Distribution(bins);
        dist.add(this);
        return dist;
    }

    // Compute the cumulative distribution function. Returns a strictly
    // increasing array of [value, cumulative_frequency] pairs.
    cumulativeDistributionFunction(normalize = true) {
        const cdf = [];
        for (const v of this.values) {
            const last = cdf[cdf.length - 1];
            if (last === undefined) {
                cdf.push([v, 1]);
            } else if (v === last[0]) {
                ++last[1];
            } else {
                cdf.push([v, last[1] + 1]);
            }
        }
        if (normalize) {
            const len = this.values.length;
            for (let i = 0; i < cdf.length; ++i) cdf[i][1] /= len;
        }
        return cdf;
    }
}

// A set of distribution bins.
export class Bins {
    static custom({bins, sample}) {
        bins.sort((a, b) => a - b);
        if (sample && sample.min < bins[0]) bins.unshift(sample.min);
        if (sample && sample.max > bins[bins.length - 1]) bins.push(sample.max);
        return new Bins(bins);
    }

    static uniform({min, max, width, count, origin, sample}) {
        if (max === undefined || max < sample.max) max = sample.max;
        if (width === undefined) {
            if (min === undefined || sample.min < min) min = sample.min;
            if (count === undefined) {
                count = Math.ceil(Math.sqrt(sample.length));
            }
            width = (max - min) / count;
            if (width <= 0) width = 1;
        } else {
            if (min === undefined) {
                const bo = origin ?? 0;
                min = bo + Math.floor((sample.min - bo) / width) * width;
            }
            count = Math.max(count ?? 0, Math.ceil((max - min) / width));
        }
        const bins = [];
        for (let i = 0; i < count + 1; ++i) bins.push(min + i * width);
        return new Bins(bins);
    }

    constructor(bins) { this.bins = bins; }

    get length() { return this.bins.length - 1; }
    get lowerBound() { return this.bins[0]; }
    get upperBound() { return this.bins[this.bins.length - 1]; }
    bounds(i) { return [this.bins[i], this.bins[i + 1]]; }

    get minWidth() {
        let res = Infinity;
        const bins = this.bins, len = bins.length - 1;
        for (let i = 0; i < len; ++i) {
            const w = bins[i + 1] - bins[i];
            if (w < res) res = w;
        }
        return res;
    }

    find(v) {
        if (v < this.lowerBound || v > this.upperBound) {
            throw new Error(`\
Value is out of bounds [${this.lowerBound}; ${this.upperBound}]: ${v}`);
        }
        const bins = this.bins;
        let lo = 0, hi = bins.length;
        while (lo < hi) {
            const m = (lo + hi) >> 1;
            if (v < bins[m]) {
                hi = m;
            } else {
                lo = m + 1;
            }
        }
        return Math.min(lo - 1, bins.length - 2);
    }
}

// A statistical distribution.
export class Distribution {
    static from(data) {
        const bins = Bins.custom({bins: data.map(it => it[0])});
        const dist = new Distribution(bins);
        const counts = dist.counts;
        for (const [v, c] of data) {
            if (c !== undefined) counts[bins.find(v)] += c;
        }
        return dist;
    }

    constructor(bins) {
        this.bins = bins;
        this.counts = Array(bins.length).fill(0);
        this._cache = {};
    }

    add(value) {
        const bins = this.bins, counts = this.counts;
        if (typeof value === 'number') {
            ++counts[bins.find(value)];
        } else if (Array.isArray(value) || value instanceof Sample) {
            for (const v of value) ++counts[bins.find(v)];
        } else {
            throw new Error(`Unsupported sample value type: ${value}`);
        }
        this._cache = {};
    }

    get length() { return this.bins.length; }

    *[Symbol.iterator]() {
        const bins = this.bins, counts = this.counts, len = counts.length;
        for (let i = 0; i < len; ++i) yield [...bins.bounds(i), counts[i]];
    }

    map(fn) {
        const res = [];
        for (const [lo, hi, c] of this) res.push(fn(lo, hi, c));
        return res;
    }

    normalize() {
        const sum = this.sum, counts = this.counts;
        for (let i = 0; i < counts.length; ++i) counts[i] /= sum;
        this._cache = {};
    }

    get count() {
        if (this._cache.count !== undefined) return this._cache.count;
        return this._cache.count = sum(this.counts);
    }

    get min() {
        if (this._cache.min !== undefined) return this._cache.min;
        for (const [i, c] of this.counts.entries()) {
            if (c <= 0) continue;
            const res = this._cache.min = this.bins.bounds(i)[0];
            return res;
        }
        return this._cache.min = NaN;
    }

    get max() {
        const counts = this.counts;
        for (let i = counts.length - 1; i >= 0; --i) {
            const c = counts[i];
            if (c <= 0) continue;
            const res = this._cache.max = this.bins.bounds(i)[1];
            return res;
        }
        return this._cache.max = NaN;
    }

    get range() { return this.max - this.min; }
    get median() { return this.quantile(0.5); }
    quartile(k) { return this.quantile(k / 4); }
    percentile(p) { return this.quantile(p / 100); }

    quantile(p) {
        const count = this.count;
        if (count === 0) return NaN;
        const th = p * count, counts = this.counts;
        let cnt = 0, e = 0;
        for (let i = 0; i < counts.length; ++i) {
            const c = counts[i];
            [cnt, e] = add(c, cnt, e);
            if (c === 0 || cnt < th) continue;
            const [lo, hi] = this.bins.bounds(i);
            const f = (cnt - th) / c;
            return f * lo + (1 - f) * hi;
        }
        return NaN;
    }

    get mean() {
        if (this._cache.mean !== undefined) return this._cache.mean;
        const count = this.count;
        if (count === 0) return this._cache.mean = NaN;
        const bins = this.bins, counts = this.counts;
        function* gen() {
            for (let i = 0; i < counts.length; ++i) {
                const [lo, hi] = bins.bounds(i);
                yield counts[i] * 0.5 * (lo + hi);
            }
        };
        return this._cache.mean = sum(gen()) / count;
    }

    get variance() {
        if (this._cache.variance !== undefined) return this._cache.variance;
        const count = this.count;
        if (count < 2) return this._cache.variance = NaN;
        const m = this.mean, bins = this.bins, counts = this.counts;
        function* gen() {
            for (let i = 0; i < counts.length; ++i) {
                const [lo, hi] = bins.bounds(i);
                yield counts[i] * Math.pow(0.5 * (lo + hi) - m, 2);
            }
        };
        return this._cache.variance = sum(gen()) / (count - 1);
    }

    get stdDev() { return Math.sqrt(this.variance); }

    avgDev(m) {
        const count = this.count;
        if (count < 1) return NaN;
        const bins = this.bins, counts = this.counts;
        function* gen() {
            for (let i = 0; i < counts.length; ++i) {
                const [lo, hi] = bins.bounds(i);
                yield counts[i] * Math.abs(0.5 * (lo + hi) - m);
            }
        };
        return sum(gen()) / count;
    }
}
