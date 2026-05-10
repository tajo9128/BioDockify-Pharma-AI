
export interface CleanedWebPage {
    title: string;
    content: string; // HTML content (simplified)
    textContent: string; // Pure text for LLM
    length: number;
    metadata: {
        url?: string;
        fetchedAt: string;
    };
}

export function cleanHtml(html: string, url?: string): CleanedWebPage {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    // 1. Remove clutter
    const removeSelectors = [
        'script', 'style', 'noscript', 'iframe', 'svg', 'object', 'embed', 'form',
        'nav', 'footer', 'header', 'aside',
        '.ad', '.ads', '.advertisement', '.banner',
        '#cookie-banner', '#newsletter',
        '.social-share', '.related-posts'
    ];

    removeSelectors.forEach(selector => {
        const elements = doc.querySelectorAll(selector);
        elements.forEach(el => el.remove());
    });

    // 2. Extract Title
    const title = doc.querySelector('title')?.textContent || doc.querySelector('h1')?.textContent || 'Untitled Page';

    // 3. Extract Main Content (heuristics)
    // Try to find the main article body
    let mainContent = doc.querySelector('main') || doc.querySelector('article') || doc.querySelector('#content') || doc.body;

    // 4. Convert to Simplified HTML & Text
    // We want to keep headings and paragraphs for structure
    let simplifiedHtml = '';
    let textContent = '';

    const meaningfulTags = ['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'li', 'blockquote'];

    // Recursive extraction helper
    const extractText = (element: Element) => {
        // Skip hidden elements check (simple version)

        if (meaningfulTags.includes(element.tagName.toLowerCase())) {
            const text = element.textContent?.trim();
            if (text && text.length > 20) { // arbitrary filter for very short lines
                const tag = element.tagName.toLowerCase();
                simplifiedHtml += `<${tag}>${text}</${tag}>\n`;
                textContent += `${text}\n\n`;
            }
        }

        Array.from(element.children).forEach(child => extractText(child));
    };

    if (mainContent) {
        // If we found a main container, extract from it
        // A better approach for text content: simple iteration over paragraphs
        const paragraphs = mainContent.querySelectorAll('p, h1, h2, h3, li');
        paragraphs.forEach(p => {
            const text = p.textContent?.trim();
            if (text && text.length > 20) {
                const tag = p.tagName.toLowerCase();
                simplifiedHtml += `<${tag}>${text}</${tag}>\n`;
                textContent += `${text}\n\n`;
            }
        });

        // Fallback if structured extraction failed (empty)
        if (textContent.length < 100) {
            textContent = mainContent.textContent || '';
            // Basic cleanup of raw text
            textContent = textContent.replace(/\s+/g, ' ').trim();
        }
    }

    return {
        title: title.trim(),
        content: simplifiedHtml,
        textContent: textContent.trim(),
        length: textContent.length,
        metadata: {
            url,
            fetchedAt: new Date().toISOString()
        }
    };
}
