// Copyright 2026 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

// Return the greatest common divisor of two natural numbers.
export function gcd(a, b) {
    while (b != 0) [a, b] = [b, a % b];
    return a;
}

// A statistical sample.
export class Sample {
    constructor(dataset) {
        dataset.sort((a, b) => a - b);
        this.dataset = dataset;
    }

    get length() { return this.dataset.length; }
    [Symbol.iterator]() { return this.dataset[Symbol.iterator](); }

    // Generate a distribution from the sample, using the given bins.
    distribution(bins) {
        const dist = new Distribution(bins);
        dist.add(this);
        return dist;
    }

    get min() { return this.dataset[0]; }
    get max() { return this.dataset[this.dataset.length - 1]; }
    get median() { return this.quantile(0.5); }
    quartile(k) { return this.quantile(k / 4); }
    percentile(p) { return this.quantile(p / 100); }

    quantile(p) {
        // TODO: Improve
        const len = this.dataset.length;
        if (len === 0) return NaN;
        if (len === 1) return this.dataset[0];
        const ri = (len - 1) * p, i = Math.floor(ri), f = ri - i;
        if (i === len - 1) return this.dataset[len - 1];
        return (1 - f) * this.dataset[i] + f * this.dataset[i + 1];
    }

    get mean() {
        if (this.dataset.length < 1) return NaN;
        if (this._mean !== undefined) return this._mean;
        let res = 0;
        for (const v of this.dataset) res += v;
        res = this._mean = res / this.dataset.length;
        return res;
    }

    get variance() {
        if (this.dataset.length < 2) return NaN;
        if (this._variance !== undefined) return this._variance;
        const m = this.mean;
        let res = 0;
        for (const v of this.dataset) res += Math.pow(v - m, 2);
        res = this._variance = res / (this.dataset.length - 1);
        return res;
    }

    get stdDev() { return Math.sqrt(this.variance); }

    avgDev(m) {
        if (this.dataset.length < 1) return NaN;
        let res = 0;
        for (const v of this.dataset) res += Math.abs(v - m);
        return res / this.dataset.length;
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
    constructor(bins) {
        this.bins = bins;
        this.counts = Array(bins.length).fill(0);
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

    // TODO: Add the same props and methods as Sample, but computed on the
    // distribution
}
