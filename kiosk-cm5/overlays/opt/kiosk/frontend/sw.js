/**
 * Service Worker for Offline Functionality
 * Provides offline-first capabilities for the kiosk application
 */

const CACHE_NAME = 'kiosk-v1';
const CACHE_URLS = [
    '/',
    '/index.html',
    '/css/app.css',
    '/js/app.js',
    '/manifest.json'
];

// Install event - cache resources
self.addEventListener('install', (event) => {
    console.log('Service Worker installing');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Caching app resources');
                return cache.addAll(CACHE_URLS);
            })
            .then(() => {
                return self.skipWaiting();
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== CACHE_NAME) {
                            console.log('Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Handle API requests
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Return response if successful
                    if (response.ok) {
                        return response;
                    }
                    throw new Error('API request failed');
                })
                .catch(() => {
                    // Return offline response for API requests
                    return new Response(
                        JSON.stringify({
                            error: 'Offline',
                            message: 'API not available offline'
                        }),
                        {
                            status: 503,
                            headers: {
                                'Content-Type': 'application/json'
                            }
                        }
                    );
                })
        );
        return;
    }
    
    // Handle WebSocket requests
    if (url.pathname === '/ws') {
        // WebSocket connections cannot be cached
        event.respondWith(fetch(request));
        return;
    }
    
    // Handle static resources with cache-first strategy
    event.respondWith(
        caches.match(request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    console.log('Serving from cache:', request.url);
                    return cachedResponse;
                }
                
                // If not in cache, fetch from network
                return fetch(request)
                    .then((response) => {
                        // Don't cache if not successful
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Clone response for caching
                        const responseToCache = response.clone();
                        
                        caches.open(CACHE_NAME)
                            .then((cache) => {
                                cache.put(request, responseToCache);
                            });
                        
                        return response;
                    })
                    .catch(() => {
                        // Return offline page for navigation requests
                        if (request.mode === 'navigate') {
                            return caches.match('/index.html');
                        }
                        
                        // Return generic offline response
                        return new Response(
                            'Offline - Resource not available',
                            {
                                status: 503,
                                statusText: 'Service Unavailable'
                            }
                        );
                    });
            })
    );
});

// Background sync for when connection is restored
self.addEventListener('sync', (event) => {
    console.log('Background sync triggered');
    
    if (event.tag === 'network-sync') {
        event.waitUntil(
            // Perform any pending operations when network is restored
            syncPendingOperations()
        );
    }
});

// Message handler for communication with main app
self.addEventListener('message', (event) => {
    console.log('Service Worker received message:', event.data);
    
    if (event.data && event.data.type === 'CACHE_UPDATE') {
        // Force cache update
        event.waitUntil(
            caches.open(CACHE_NAME)
                .then((cache) => {
                    return cache.addAll(CACHE_URLS);
                })
        );
    }
});

// Sync pending operations when network is available
async function syncPendingOperations() {
    try {
        // Check if network is available
        const response = await fetch('/api/network/connectivity');
        if (response.ok) {
            console.log('Network restored, syncing operations');
            
            // Notify main application
            const clients = await self.clients.matchAll();
            clients.forEach(client => {
                client.postMessage({
                    type: 'NETWORK_RESTORED'
                });
            });
        }
    } catch (error) {
        console.log('Network still unavailable');
    }
}