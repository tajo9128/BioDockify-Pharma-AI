import { cleanHtml, CleanedWebPage } from './html_cleaner';



// Configuration for HeadlessX
// TODO: Move these to App Settings in a future update
const HEADLESSX_CONFIG = {
    baseUrl: '/api', // Default via Next.js proxy
    endpoint: '/api/v1/scrape',
    token: '', // Add your token here if configured
    enabled: true // Set to false to disable attempts
};

// Universal fetch that works in browser environments
async function universalHttpFetch(url: string, options: {
    method?: 'GET' | 'POST';
    timeout?: number;
    headers?: Record<string, string>;
    body?: any;
}): Promise<{ ok: boolean; status: number; data: any }> {
    const { method = 'GET', timeout = 10000, headers = {}, body } = options;

    // Browser/Docker fallback
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...headers
            },
            body: body ? JSON.stringify(body) : undefined,
            signal: controller.signal
        });

        clearTimeout(timeoutId);
        const data = await response.text();

        return {
            ok: response.ok,
            status: response.status,
            data
        };
    } catch (e) {
        clearTimeout(timeoutId);
        throw e;
    }
}

/**
 * Fetches and cleans a public web page.
 * In Tauri: Uses native HTTP client to bypass CORS.
 * In Docker/Browser: Uses standard fetch (works for same-origin or CORS-enabled endpoints).
 * 
 * Strategy:
 * 1. Attempt HeadlessX (if enabled) for anti-detect/dynamic scraping.
 * 2. Fallback to Simple Fetch if HeadlessX is unreachable or fails.
 */
export async function fetchWebPage(url: string): Promise<CleanedWebPage> {
    console.log(`[WebFetcher] Fetching: ${url}`);

    // 1. Try HeadlessX
    if (HEADLESSX_CONFIG.enabled) {
        try {
            console.log('[WebFetcher] Attempting HeadlessX scrape...');
            const result = await fetchWithHeadlessX(url);
            if (result) {
                console.log('[WebFetcher] HeadlessX success!');
                // HeadlessX usually returns rendered HTML. We still clean it.
                return cleanHtml(result.content, url);
            }
        } catch (e) {
            console.warn('[WebFetcher] HeadlessX failed or unreachable, falling back to standard fetch.');
        }
    }

    // 2. Fallback to Standard Fetch
    try {
        const response = await universalHttpFetch(url, {
            method: 'GET',
            timeout: 10000,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }

        const html = response.data as string;
        return cleanHtml(html, url);

    } catch (e: any) {
        console.error(`[WebFetcher] Error fetching ${url}:`, e);
        throw new Error(`Failed to fetch webpage: ${e.message || 'Unknown error'}`);
    }
}

/**
 * Connector for HeadlessX Scraper
 */
async function fetchWithHeadlessX(targetUrl: string): Promise<{ content: string } | null> {
    const apiUrl = `${HEADLESSX_CONFIG.baseUrl}${HEADLESSX_CONFIG.endpoint}`;

    try {
        const response = await universalHttpFetch(apiUrl, {
            method: 'POST',
            timeout: 30000, // Longer timeout for browser rendering
            headers: {
                'Content-Type': 'application/json',
                ...(HEADLESSX_CONFIG.token ? { 'Authorization': `Bearer ${HEADLESSX_CONFIG.token}` } : {})
            },
            body: {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                },
                url: targetUrl,
                options: {
                    content: true,
                    screenshot: false, // We don't need screenshots yet
                    premium_proxy: false // Use if available
                }
            }
        });

        console.log(`[HeadlessX] Status: ${response.status}`);

        if (!response.ok) {
            return null; // Let fallback handle it
        }

        // Parse response (Assuming standard Scraping/HeadlessX format)
        const data = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;

        // Handle varying API response structures safely
        if (data.content) return { content: data.content };
        if (data.data?.content) return { content: data.data.content };
        if (typeof data === 'string') return { content: data };

        return null;

    } catch (error) {
        // Quietly fail (connection refused usually)
        throw error;
    }
}

/**
 * Performs a lightweight search by scraping a privacy-friendly search engine (DuckDuckGo HTML).
 * This is a "No-API" fallback for finding URLs.
 */
export async function searchWeb(query: string): Promise<string[]> {
    console.log(`[WebFetcher] Searching: ${query}`);
    // Using DuckDuckGo HTML version which is easier to parse and intended for low-bandwidth
    const searchUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;

    try {
        const response = await universalHttpFetch(searchUrl, {
            method: 'GET',
            timeout: 10000,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        });

        if (!response.ok) return [];

        const html = response.data as string;

        // Simple regex extraction for result links
        // DDG HTML links usually look like: <a class="result__a" href="...">
        const linkRegex = /class="result__a" href="([^"]+)"/g;
        const matches = [...html.matchAll(linkRegex)];

        // Extract URLs and decode them
        const urls = matches.map(m => {
            let url = m[1];
            // DDG sometimes wraps URLs like /l/?kh=-1&uddg=...
            if (url.startsWith('//duckduckgo.com/l/')) {
                const urlParams = new URLSearchParams(url.split('?')[1]);
                return urlParams.get('uddg') || '';
            }
            return url;
        }).filter(u => u && u.startsWith('http') && !u.includes('duckduckgo.com'));

        return [...new Set(urls)].slice(0, 3); // Return top 3 unique URLs

    } catch (e) {
        console.error('[WebFetcher] Search failed:', e);
        return [];
    }
}
