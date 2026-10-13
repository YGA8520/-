#!/usr/bin/env python3
"""Sharpen a scan of handwriting: deconvolution (Richardson-Lucy, gaussian blur model) of the luminance, a stronger ink contrast, and a crisp 2x enlargement.
usage: python sharpen_facsimile.py in.jpg out.jpg [sigma=1.3] [iterations=18]"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage, signal


def gauss_kernel(sigma):
    r = int(3 * sigma + 1)
    x = np.arange(-r, r + 1)
    k = np.exp(-(x[:, None] ** 2 + x[None, :] ** 2) / (2 * sigma ** 2))
    return (k / k.sum()).astype(np.float32)


def rl(lum, sigma, iters):
    k = gauss_kernel(sigma)
    kf = k[::-1, ::-1]
    est = np.clip(lum, 1e-3, 1).astype(np.float32)
    obs = est.copy()
    for _ in range(iters):
        conv = signal.fftconvolve(est, k, mode='same')
        rel = obs / np.maximum(conv, 1e-3)
        est = est * signal.fftconvolve(rel, kf, mode='same')
        est = np.clip(est, 1e-3, 1.2)
    return np.clip(est, 0, 1)


def sharpen(src, dst, sigma=1.3, iters=18, scale=2):
    im = Image.open(src).convert('RGB')
    im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)           # work on the enlarged image: the strokes get a smooth edge to deconvolve
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    new = rl(lum, sigma * scale, iters)
    # the colour of the ink stays: the chroma of every pixel is kept, only its luminance is the sharpened one (ink strokes get darker and thinner edges, not black)
    chroma = a - lum[..., None]
    out = np.clip(new[..., None] + chroma * 1.15, 0, 1)
    lo, hi = 0.06, 0.94
    out = np.clip((out - lo) / (hi - lo), 0, 1) ** 1.10
    res = Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGB').filter(ImageFilter.UnsharpMask(radius=1.4, percent=35, threshold=3))
    res.save(dst, quality=95, subsampling=0, optimize=True)
    return res.size


if __name__ == '__main__':
    s = float(sys.argv[3]) if len(sys.argv) > 3 else 1.3
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 18
    print(sharpen(sys.argv[1], sys.argv[2], s, n))
