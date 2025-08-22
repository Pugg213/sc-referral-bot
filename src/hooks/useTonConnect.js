import { useEffect, useState } from 'react';
import { TonConnectUI } from '@tonconnect/ui';

export function useTonConnect() {
    const [tonConnectUI, setTonConnectUI] = useState(null);
    const [wallet, setWallet] = useState(null);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        try {
            // Check if TON Connect is already initialized
            if (window.tonConnectUIInstance) {
                console.log('TON Connect already initialized, reusing...');
                const ui = window.tonConnectUIInstance;
                setTonConnectUI(ui);
                
                // Force check wallet connection status
                const currentWallet = ui.wallet;
                console.log('Existing wallet found:', currentWallet);
                
                // Force update state immediately
                if (currentWallet) {
                    setWallet(currentWallet);
                    setConnected(true);
                    console.log('FORCED wallet state update - Connected: true');
                } else {
                    setWallet(null);
                    setConnected(false);
                    console.log('FORCED wallet state update - Connected: false');
                }
                return;
            }

            const ui = new TonConnectUI({
                manifestUrl: window.location.origin + '/tonconnect-manifest-short.json'
            });

            ui.onStatusChange((walletInfo) => {
                console.log('TON Connect status changed:', !!walletInfo, 'Wallet:', walletInfo);
                setWallet(walletInfo);
                setConnected(!!walletInfo);
                
                // Force re-render by updating window state
                window.tonConnectWalletState = {
                    wallet: walletInfo,
                    connected: !!walletInfo,
                    timestamp: Date.now()
                };
                console.log('Updated global wallet state:', window.tonConnectWalletState);
            });

            // Check initial wallet state
            const initialWallet = ui.wallet;
            if (initialWallet) {
                console.log('Initial wallet found:', initialWallet);
                setWallet(initialWallet);
                setConnected(true);
            }

            // Store instance globally to prevent double initialization
            window.tonConnectUIInstance = ui;
            setTonConnectUI(ui);
        } catch (error) {
            console.error('TON Connect initialization failed:', error);
            // Set dummy state for development
            setTonConnectUI(null);
            setWallet(null);
            setConnected(false);
        }

        return () => {
            // Don't cleanup the global instance on unmount to prevent re-registration
        };
    }, []);

    const connect = async () => {
        if (tonConnectUI) {
            await tonConnectUI.openModal();
        }
    };

    const disconnect = async () => {
        if (tonConnectUI) {
            await tonConnectUI.disconnect();
        }
    };

    const sendTransaction = async (transaction) => {
        if (!tonConnectUI || !connected) {
            throw new Error('Wallet not connected');
        }
        return await tonConnectUI.sendTransaction(transaction);
    };

    return {
        tonConnectUI,
        wallet,
        connected,
        connect,
        disconnect,
        sendTransaction
    };
}