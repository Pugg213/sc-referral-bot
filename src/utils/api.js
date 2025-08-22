// Rhombis API Integration
const BASE_URL = 'https://api.rhombis.app';

export async function getFee() {
    try {
        const response = await fetch(`${BASE_URL}/fee`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fee API error:', error);
        throw error;
    }
}

export async function getRecipient(type, username) {
    try {
        // Clean username (remove @ if present) but ensure we have content
        const cleanUsername = username.replace(/^@+/, '').trim();
        
        if (!cleanUsername) {
            throw new Error('Username не может быть пустым');
        }
        
        console.log(`🔍 Searching for user: @${cleanUsername} via ${type} API`);
        
        // Use GET with username parameter (according to official API docs)
        const response = await fetch(`${BASE_URL}/${type}/recipient?username=${encodeURIComponent(cleanUsername)}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36'
            },
            mode: 'cors'
        });
        
        console.log(`📡 API Response status: ${response.status}`);
        
        if (!response.ok) {
            // Parse error response to get detailed message
            let errorMessage;
            try {
                const errorData = await response.json();
                console.log('❌ API Error Response:', errorData);
                errorMessage = errorData.message || errorData.error || `HTTP ${response.status}`;
            } catch {
                errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            }
            
            // Provide user-friendly error messages based on API documentation
            if (response.status === 404) {
                throw new Error(`Пользователь @${cleanUsername} не найден в Telegram`);
            } else if (response.status === 400) {
                if (errorMessage.includes('username assigned to a user')) {
                    throw new Error(`@${cleanUsername} не найден. Проверьте правильность написания username.`);
                } else if (errorMessage.includes('No Telegram users found')) {
                    throw new Error(`@${cleanUsername} не найден в Telegram`);
                }
                throw new Error(`Неверный формат username: ${cleanUsername}`);
            } else {
                throw new Error(`Ошибка API: ${errorMessage}`);
            }
        }
        
        const data = await response.json();
        console.log(`✅ API Response for @${cleanUsername}:`, data);
        
        // According to API docs, response should contain: recipient, photoUrl, name
        return data;
    } catch (error) {
        console.error(`Recipient API error (${type}):`, error);
        throw error;
    }
}

export async function postTransaction(type, payload) {
    try {
        const response = await fetch(`${BASE_URL}/${type}/transaction`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Transaction API error (${type}):`, error);
        throw error;
    }
}

// Pricing constants from Rhombis API documentation
export const PRICING = {
    STARS: 0.015, // $0.015 per star
    PREMIUM: {
        3: 11.99,  // 3 months - $11.99
        6: 15.99,  // 6 months - $15.99  
        12: 28.99  // 12 months - $28.99
    }
};

// TON address formatting utilities
export function formatTonAddress(address) {
    if (!address) return '';
    
    // If already in EQ/UQ format, return as is
    if (address.startsWith('EQ') || address.startsWith('UQ')) {
        return address;
    }
    
    // For raw hex addresses, add EQ prefix (most common)
    if (address.length === 64 && /^[0-9a-fA-F]+$/.test(address)) {
        return `EQ${address}`;
    }
    
    return address;
}

export function truncateAddress(address, startLength = 6, endLength = 4) {
    if (!address) return '';
    if (address.length <= startLength + endLength) return address;
    
    return `${address.slice(0, startLength)}...${address.slice(-endLength)}`;
}