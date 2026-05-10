import { useState, useEffect } from "react";

/**
 * Hook to track network connectivity status.
 * Returns true if online, false if offline.
 */
export function useOnlineStatus() {
    // Assume online by default (SSR safe)
    const [isOnline, setIsOnline] = useState(true);

    useEffect(() => {
        // Client-side check
        setIsOnline(navigator.onLine);

        const handleOnline = () => setIsOnline(true);
        const handleOffline = () => setIsOnline(false);

        window.addEventListener("online", handleOnline);
        window.addEventListener("offline", handleOffline);

        return () => {
            window.removeEventListener("online", handleOnline);
            window.removeEventListener("offline", handleOffline);
        };
    }, []);

    return isOnline;
}
