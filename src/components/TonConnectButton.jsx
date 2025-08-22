import { useTonConnect } from '../hooks/useTonConnect';
import { formatTonAddress, truncateAddress } from '../utils/address';
import { useState } from 'react';

export default function TonConnectButton() {
    const { wallet, connected, connect, disconnect } = useTonConnect();
    const [isLoading, setIsLoading] = useState(false);
    
    // Defensive programming for component safety
    if (!connect || !disconnect) {
        return (
            <div className="wallet-container">
                <div className="status-info">Инициализация TON Connect...</div>
            </div>
        );
    }

    const handleWalletAction = async () => {
        setIsLoading(true);
        try {
            if (connected) {
                await disconnect();
            } else {
                await connect();
            }
        } catch (error) {
            console.error('Wallet action error:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const getDisplayAddress = () => {
        const address = wallet?.account?.address;
        if (!address) return 'Адрес недоступен';
        
        // If already in UQ format, use it directly
        if (address.startsWith('UQ') || address.startsWith('EQ')) {
            return truncateAddress(address, 6, 4);
        }
        
        // Otherwise convert hex format
        return truncateAddress(formatTonAddress(address), 6, 4);
    };

    return (
        <div className="wallet-container">
            <button 
                className={`wallet-multifunctional-button ${connected ? 'connected' : 'disconnected'} ${isLoading ? 'loading' : ''}`}
                onClick={handleWalletAction}
                disabled={isLoading}
            >
                <div className="wallet-button-content">
                    {isLoading ? (
                        <>
                            <div className="wallet-spinner"></div>
                            <div className="wallet-button-info">
                                <span className="wallet-button-title">Обработка...</span>
                            </div>
                        </>
                    ) : connected ? (
                        <>
                            <div className="wallet-button-icon connected-icon">●</div>
                            <div className="wallet-button-info">
                                <span className="wallet-button-title">Кошелек подключен</span>
                                <span className="wallet-button-subtitle">{getDisplayAddress()}</span>
                            </div>
                            <div className="wallet-button-action">•••</div>
                        </>
                    ) : (
                        <>
                            <div className="wallet-button-icon disconnected-icon">○</div>
                            <div className="wallet-button-info">
                                <span className="wallet-button-title">Подключить TON кошелек</span>
                                <span className="wallet-button-subtitle">Для покупки Stars и Premium</span>
                            </div>
                            <div className="wallet-button-action">→</div>
                        </>
                    )}
                </div>
            </button>
        </div>
    );
}