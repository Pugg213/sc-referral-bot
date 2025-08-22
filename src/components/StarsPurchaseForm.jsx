import React, { useState, useEffect } from 'react';
import { useTonConnect } from '../hooks/useTonConnect';
import { getRecipient, postTransaction } from '../utils/api';

export default function StarsPurchaseForm() {
    const [quantity, setQuantity] = useState(100);
    const [username, setUsername] = useState('');
    const [userPreview, setUserPreview] = useState(null);
    const [searchingUser, setSearchingUser] = useState(false);
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('');
    const [fee, setFee] = useState(0.03);

    const tonConnect = useTonConnect();

    const presets = [50, 100, 250, 500, 1000, 2500];

    const calculateTotal = () => {
        const basePrice = quantity * 0.013;
        const total = basePrice + (basePrice * fee);
        return total.toFixed(2);
    };

    // Check if wallet is actually connected using multiple methods
    const actualConnected = window.tonConnectUIInstance?.wallet || window.tonConnectWalletState?.wallet;
    
    // Check if form is valid for purchase
    const isFormValid = () => {
        return (
            actualConnected && // Wallet connected
            username.trim().length > 0 && // Username entered
            userPreview && // User found
            quantity >= 1 && quantity <= 1000000 && // Valid quantity
            !loading && // Not currently processing
            !searchingUser // Not searching for user
        );
    };

    // Live user search function
    const searchUser = async (usernameValue) => {
        const cleanUsername = usernameValue.replace('@', '').trim();
        
        if (cleanUsername.length < 3) {
            setUserPreview(null);
            return;
        }

        setSearchingUser(true);
        try {
            const recipient = await getRecipient('stars', cleanUsername);
            console.log('Live search result:', recipient);
            setUserPreview(recipient);
        } catch (error) {
            console.log('User not found:', error.message);
            setUserPreview(null);
        } finally {
            setSearchingUser(false);
        }
    };

    // Debounced user search
    useEffect(() => {
        const timeoutId = setTimeout(() => {
            searchUser(username);
        }, 500);

        return () => clearTimeout(timeoutId);
    }, [username]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        console.log('=== НАЧАЛО ОБРАБОТКИ ФОРМЫ V4 ===');
        console.log('Username:', username);
        console.log('Quantity:', quantity);
        
        console.log('🔍 CHECKING WALLET STATE V4...');
        
        // Force use global wallet state since React hook is not working
        let globalWallet;
        try {
            globalWallet = window.tonConnectWalletState?.wallet || window.tonConnectUIInstance?.wallet;
            console.log('Global wallet found?', !!globalWallet);
            console.log('Global wallet account?', !!globalWallet?.account);
        } catch (walletError) {
            console.error('Error accessing wallet:', walletError);
            globalWallet = null;
        }
        
        console.log('⚡ FORCING WALLET CHECK TO PASS V4 - proceeding...');
        console.log('✅ Wallet check bypassed V4 - proceeding with validation...');

        if (!username.trim()) {
            setStatus('Укажите username получателя');
            return;
        }

        if (quantity < 1 || quantity > 1000000) {
            setStatus('Количество Stars должно быть от 1 до 1,000,000');
            return;
        }

        setLoading(true);
        setStatus('Поиск получателя...');
        console.log('Ищем пользователя:', username);

        try {
            console.log('🔍 Starting recipient search for:', username);
            const recipient = await getRecipient('stars', username);
            console.log('📨 Получен ответ API:', recipient);
            
            if (recipient.name && recipient.recipient) {
                console.log('✅ USER FOUND - displaying info');
                setStatus(`✅ Найден: ${recipient.name} (@${username})`);
                await new Promise(resolve => setTimeout(resolve, 1500));
                console.log('✅ User info displayed, proceeding to transaction creation');
            } else {
                console.error('❌ EMPTY API RESPONSE:', recipient);
                setStatus(`⚠️ Получен пустой ответ от API для @${username}`);
                return;
            }

            setStatus('Создание транзакции Stars...');

            console.log('📡 Creating transaction with data:', {
                recipient: recipient.recipient,
                quantity: quantity
            });

            const transaction = await postTransaction('stars', {
                recipient: recipient.recipient,
                quantity: quantity
            });

            console.log('📋 Transaction API Response:', transaction);
            console.log('📋 Transaction type:', typeof transaction);
            console.log('📋 Transaction keys:', Object.keys(transaction || {}));
            
            if (!transaction) {
                throw new Error('Пустой ответ от сервера транзакций');
            }
            
            if (!transaction.message) {
                console.error('❌ Missing transaction.message:', transaction);
                throw new Error('Отсутствует поле message в ответе сервера');
            }
            
            console.log('✅ Transaction validation passed, proceeding...');

            // Use correct transaction format from API response
            const tonTransaction = {
                validUntil: transaction.validUntil,
                messages: [
                    {
                        address: transaction.message.address,
                        amount: transaction.message.amount.toString(),
                        payload: transaction.message.payload
                    }
                ]
            };

            console.log('Prepared TON transaction:', tonTransaction);
            
            const globalWallet = window.tonConnectWalletState?.wallet;
            if (!globalWallet || !globalWallet.account) {
                throw new Error('Кошелек не подключен. Подключите кошелек и попробуйте снова.');
            }
            
            console.log('Wallet verified, sending transaction...');
            
            let txResult;
            if (window.tonConnectUIInstance?.sendTransaction) {
                console.log('Using global instance sendTransaction');
                txResult = await window.tonConnectUIInstance.sendTransaction(tonTransaction);
            } else if (tonConnect?.tonConnectUI?.sendTransaction) {
                console.log('Using tonConnectUI sendTransaction');
                txResult = await tonConnect.tonConnectUI.sendTransaction(tonTransaction);
            } else {
                throw new Error('Не удается найти функцию отправки транзакции');
            }
            
            console.log('Transaction result:', txResult);

            setStatus(`✅ ${quantity} Stars успешно отправлены @${username}!`);
            setUsername('');
            setQuantity(100);

        } catch (error) {
            console.error('Stars purchase error:', error);
            setStatus('❌ ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="stars-purchase-form">
            <h3>⭐ Купить Telegram Stars</h3>

            <div className="stars-grid">
                {presets.map(preset => (
                    <div
                        key={preset}
                        className={`stars-preset ${quantity === preset ? 'selected' : ''}`}
                        onClick={() => setQuantity(preset)}
                    >
                        {preset}
                    </div>
                ))}
            </div>

            <form onSubmit={handleSubmit}>
                <div className="input-group">
                    <label className="input-label">Количество Stars:</label>
                    <input
                        className="input"
                        type="number"
                        min={1}
                        max={1000000}
                        value={quantity}
                        onChange={e => setQuantity(parseInt(e.target.value) || 1)}
                        required
                    />
                </div>

                <div className="input-group">
                    <input
                        className="input"
                        type="text"
                        placeholder="Введите @username получателя"
                        value={username}
                        onChange={e => {
                            console.log('Username изменен:', e.target.value);
                            setUsername(e.target.value);
                        }}
                        required
                    />
                    
                    {searchingUser && (
                        <div className="user-preview searching">
                            <div className="loading-small"></div>
                            <span>Поиск пользователя...</span>
                        </div>
                    )}
                    
                    {userPreview && !searchingUser && (
                        <div className="user-preview found">
                            <img 
                                src={userPreview.photoUrl} 
                                alt={userPreview.name}
                                className="user-avatar"
                                onError={(e) => e.target.style.display = 'none'}
                            />
                            <div className="user-info">
                                <div className="user-name">{userPreview.name}</div>
                                <div className="user-username">@{username}</div>
                            </div>
                        </div>
                    )}
                </div>



                <button
                    className="button"
                    type="submit"
                    disabled={!isFormValid()}
                    style={{
                        opacity: !isFormValid() ? 0.5 : 1,
                        cursor: !isFormValid() ? 'not-allowed' : 'pointer'
                    }}
                >
                    {loading ? (
                        <>
                            <span className="loading"></span>
                            Обработка...
                        </>
                    ) : (
                        `Купить ${quantity} Stars за $${calculateTotal()}`
                    )}
                </button>
            </form>

            {/* Form validation messages */}
            {!actualConnected && (
                <div className="status-info">
                    ⚠️ Подключите TON кошелек через кнопку "Подключить кошелек" выше
                </div>
            )}
            
            {actualConnected && !username.trim() && (
                <div className="status-info">
                    ℹ️ Введите @username получателя Stars
                </div>
            )}
            
            {actualConnected && username.trim() && !userPreview && !searchingUser && (
                <div className="status-info">
                    ❌ Пользователь @{username} не найден в Telegram
                </div>
            )}
            
            {actualConnected && userPreview && (quantity < 1 || quantity > 1000000) && (
                <div className="status-info">
                    ⚠️ Количество Stars должно быть от 1 до 1,000,000
                </div>
            )}

            {status && (
                <div className={`status-${status.includes('✅') ? 'success' : status.includes('❌') ? 'error' : 'info'}`}>
                    {status}
                </div>
            )}
        </div>
    );
}