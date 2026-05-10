/**
 * Cross-Platform Fetch Wrapper
 * Browser-standard fetch wrapper for the BioDockify Research Workstation.
 */

/**
 * Universal fetch wrapper for browser environment
 */
export function isTauri(): boolean {
    return false;
}

interface FetchOptions {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
    headers?: Record<string, string>;
    body?: string | object;
    timeout?: number;
}

interface FetchResult {
    ok: boolean;
    status: number;
    data: any;
    json: () => Promise<any>;
}

/**
 * Universal fetch that works in browser environments
 */
export async function universalFetch(url: string, options: FetchOptions = {}): Promise<FetchResult> {
    const { method = 'GET', headers = {}, body, timeout = 5000 } = options;

    // Standard browser fetch
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...headers
            },
            body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        const data = await response.json().catch(() => null);

        return {
            ok: response.ok,
            status: response.status,
            data,
            json: async () => data
        };
    } catch (e) {
        clearTimeout(timeoutId);
        throw e;
    }
}

