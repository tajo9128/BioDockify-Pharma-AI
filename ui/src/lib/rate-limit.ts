import { NextRequest, NextResponse } from 'next/server';

interface RateLimitStore {
    [key: string]: {
        count: number;
        resetTime: number;
    };
}

const store: RateLimitStore = {};

export async function rateLimit(
    req: NextRequest,
    limit: number = 100,
    windowMs: number = 60 * 1000
) {
    const ip = req.headers.get('x-forwarded-for') || 'anonymous';
    const now = Date.now();

    if (!store[ip] || now > store[ip].resetTime) {
        store[ip] = {
            count: 0,
            resetTime: now + windowMs,
        };
    }

    store[ip].count++;

    if (store[ip].count > limit) {
        return new NextResponse('Too Many Requests', {
            status: 429,
            headers: {
                'Retry-After': Math.ceil((store[ip].resetTime - now) / 1000).toString(),
            },
        });
    }

    return null;
}
