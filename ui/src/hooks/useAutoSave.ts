import { useEffect } from "react";

/**
 * Hook to auto-save specific value to localStorage.
 * @param key unique persistent key
 * @param value value to save
 * @param delay debounce delay in ms
 */
export function useAutoSave<T>(key: string, value: T, delay: number = 1000) {
    useEffect(() => {
        const handler = setTimeout(() => {
            try {
                if (value) {
                    localStorage.setItem(key, JSON.stringify(value));
                }
            } catch (e) {
                console.error("AutoSave Failed:", e);
            }
        }, delay);

        return () => clearTimeout(handler);
    }, [key, value, delay]);
}

/**
 * Hook to load initial value from localStorage
 */
export function useAutoLoad<T>(key: string, defaultValue: T): T {
    if (typeof window === "undefined") return defaultValue;
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
        return defaultValue;
    }
}
