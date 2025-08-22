import { useState, useEffect } from 'react';
import { getRecipient, postTransaction } from '../utils/api';
import { useTonConnect } from '../hooks/useTonConnect';
import { formatTonAddress, truncateAddress } from '../utils/address';

export default function PremiumPurchaseForm() {
    const [username, setUsername] = useState('');
    const [recipient, setRecipient] = useState(null);
    const [duration, setDuration] = useState(3);
    const [status, setStatus] = useState('');
    const [loading, setLoading] = useState(false);
    const [searchingUser, setSearchingUser] = useState(false);
    const [userPreview, setUserPreview] = useState(null);
    const { connected, wallet, sendTransaction, tonConnect } = useTonConnect();

    // Check actual wallet connection from global state
    const actualConnected = window.tonConnectWalletState?.wallet?.account;

    // Live search user when username changes (like in Stars)
    const searchUser = async (usernameValue) => {
        if (!usernameValue.trim()) {
            setUserPreview(null);
            setRecipient(null);
            return;
        }

        setSearchingUser(true);
        try {
            const cleanUsername = usernameValue.replace('@', '');
            console.log('Live search for Premium user:', cleanUsername);
            
            const data = await getRecipient('premium', cleanUsername);
            console.log('Live Premium search result:', data);
            
            if (data && data.name && data.recipient) {
                const userData = {
                    username: cleanUsername,
                    firstName: data.name,
                    lastName: '',
                    photo: data.photoUrl,
                    recipient: data.recipient
                };
                setUserPreview(userData);
                setRecipient(userData);
            } else {
                setUserPreview(null);
                setRecipient(null);
            }
        } catch (error) {
            console.log('Premium user not found:', error.message);
            setUserPreview(null);
            setRecipient(null);
        } finally {
            setSearchingUser(false);
        }
    };

    // Debounced user search (like in Stars)
    useEffect(() => {
        const timeoutId = setTimeout(() => {
            searchUser(username);
        }, 500); // Wait 500ms after user stops typing

        return () => clearTimeout(timeoutId);
    }, [username]);

    const handlePremiumPurchase = async (e) => {
        e.preventDefault();
        
        console.log('=== НАЧАЛО ОБРАБОТКИ Premium V5 ===');
        console.log('Username:', username);
        console.log('Duration:', duration);
        console.log('Recipient:', recipient);
        
        console.log('🔍 CHECKING WALLET STATE Premium V5...');
        
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
        
        console.log('⚡ FORCING WALLET CHECK TO PASS Premium V5 - proceeding...');
        console.log('✅ Wallet check bypassed Premium V5 - proceeding with validation...');

        if (!recipient) {
            setStatus('❌ Выберите получателя Premium');
            return;
        }

        try {
            setLoading(true);
            setStatus('Создание транзакции Premium...');

            console.log('📡 Creating Premium transaction with data:', {
                recipient: recipient.recipient,
                months: duration
            });

            // Create transaction with correct recipient field
            const transaction = await postTransaction('premium', {
                recipient: recipient.recipient, // Use the recipient ID from API
                months: duration
            });

            console.log('📋 Premium Transaction API Response:', transaction);
            console.log('📋 Premium Transaction type:', typeof transaction);
            console.log('📋 Premium Transaction keys:', Object.keys(transaction || {}));

            // Validate transaction response
            if (!transaction) {
                throw new Error('Пустой ответ от сервера Premium транзакций');
            }
            
            if (!transaction.message) {
                console.error('❌ Missing transaction.message in Premium:', transaction);
                throw new Error('Отсутствует поле message в ответе Premium сервера');
            }
            
            console.log('✅ Premium Transaction validation passed, proceeding...');

            // Use same structure as Stars (message field)
            const txData = transaction.message;
            
            if (!txData.address) {
                throw new Error('Отсутствует адрес в транзакции Premium: ' + JSON.stringify(transaction));
            }
            
            if (!txData.amount && txData.amount !== 0) {
                throw new Error('Отсутствует сумма в транзакции Premium: ' + JSON.stringify(transaction));
            }

            setStatus('Отправка транзакции в TON...');

            // Use correct transaction format from API response (same as Stars)
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

            console.log('Prepared Premium TON transaction:', tonTransaction);
            
            // Force check wallet connection before sending
            const globalWallet = window.tonConnectWalletState?.wallet;
            if (!globalWallet || !globalWallet.account) {
                throw new Error('Кошелек не подключен. Подключите кошелек и попробуйте снова.');
            }
            
            console.log('Wallet verified, sending Premium transaction...');
            
            // Use the most reliable method - direct access to global instance
            let txResult;
            if (window.tonConnectUIInstance?.sendTransaction) {
                console.log('Using global instance sendTransaction');
                txResult = await window.tonConnectUIInstance.sendTransaction(tonTransaction);
            } else if (tonConnect?.tonConnectUI?.sendTransaction) {
                console.log('Using tonConnectUI sendTransaction');
                txResult = await tonConnect.tonConnectUI.sendTransaction(tonTransaction);
            } else if (sendTransaction && typeof sendTransaction === 'function') {
                console.log('Using hook sendTransaction');
                txResult = await sendTransaction(tonTransaction);
            } else {
                throw new Error('Не удается найти функцию отправки транзакции');
            }
            
            console.log('Premium transaction result:', txResult);

            setStatus('✅ Транзакция Premium отправлена в кошелек!');
            
        } catch (error) {
            console.error('Premium purchase error:', error);
            setStatus('❌ ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    // Calculate price - Official Rhombis API pricing
    const calculatePrice = (months) => {
        const prices = {
            3: 11.99,   // 3 months - $11.99
            6: 15.99,   // 6 months - $15.99  
            12: 28.99   // 12 months - $28.99
        };
        return prices[months] || 11.99;
    };

    return (
        <div className="premium-purchase-form">
            <h3>🌟 Купить Telegram Premium</h3>
            
            {/* User Search with Live Preview */}
            <div className="input-group">
                <input
                    className="input"
                    type="text"
                    placeholder="Введите @username получателя"
                    value={username}
                    onChange={e => {
                        console.log('Premium username изменен:', e.target.value);
                        setUsername(e.target.value);
                    }}
                    required
                />
                
                {/* User Preview (same as Stars) */}
                {searchingUser && (
                    <div className="user-preview searching">
                        <div className="loading-small"></div>
                        <span>Поиск пользователя...</span>
                    </div>
                )}
                
                {userPreview && !searchingUser && (
                    <div className="user-preview found">
                        <img 
                            src={userPreview.photo} 
                            alt={userPreview.firstName}
                            className="user-avatar"
                            onError={(e) => e.target.style.display = 'none'}
                        />
                        <div className="user-info">
                            <div className="user-name">{userPreview.firstName}</div>
                            <div className="user-username">@{username}</div>
                        </div>
                    </div>
                )}
            </div>

            {/* Recipient Preview */}
            {recipient && (
                <div className="recipient-preview">
                    {recipient.photo && (
                        <img 
                            src={recipient.photo} 
                            alt="User" 
                            className="user-avatar"
                        />
                    )}
                    <div className="user-info">
                        <div className="user-name">
                            {recipient.firstName} {recipient.lastName}
                        </div>
                        <div className="user-username">@{recipient.username}</div>
                    </div>
                </div>
            )}

            {/* Duration Selection - Block style */}
            <div style={{ marginBottom: '20px' }}>
                <label style={{ 
                    display: 'block', 
                    marginBottom: '12px', 
                    fontWeight: '600', 
                    color: '#374151' 
                }}>
                    Выберите длительность Premium подписки:
                </label>
                <div style={{ 
                    display: 'grid', 
                    gap: '8px', 
                    gridTemplateColumns: 'repeat(3, 1fr)' 
                }}>
                    {[
                        { months: 3, label: '3 месяца', price: calculatePrice(3) },
                        { months: 6, label: '6 месяцев', price: calculatePrice(6) },
                        { months: 12, label: '12 месяцев', price: calculatePrice(12) }
                    ].map(option => (
                        <div
                            key={option.months}
                            onClick={() => setDuration(option.months)}
                            style={{
                                padding: '12px',
                                background: duration === option.months ? '#1673fa' : '#f8fafc',
                                border: `2px solid ${duration === option.months ? '#1673fa' : '#e2e8f0'}`,
                                borderRadius: '12px',
                                cursor: 'pointer',
                                textAlign: 'center',
                                transition: 'all 0.2s ease',
                                color: duration === option.months ? '#fff' : '#1a3185'
                            }}
                        >
                            <div style={{ 
                                fontWeight: '600', 
                                fontSize: '14px',
                                marginBottom: '2px'
                            }}>
                                {option.label}
                            </div>
                            <div style={{ 
                                fontSize: '13px',
                                opacity: 0.8
                            }}>
                                ${option.price}
                            </div>
                        </div>
                    ))}
                </div>
            </div>



            {/* Purchase Form */}
            <form onSubmit={handlePremiumPurchase}>
                <button
                    type="submit"
                    className="purchase-button"
                    disabled={!actualConnected || loading || !recipient}
                    style={{
                        width: '100%',
                        padding: '12px 20px',
                        backgroundColor: '#1a3185',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        fontSize: '16px',
                        fontWeight: '600',
                        marginTop: '16px',
                        transition: 'all 0.2s ease',
                        opacity: (!actualConnected || loading || !recipient) ? 0.5 : 1,
                        cursor: (!actualConnected || loading || !recipient) ? 'not-allowed' : 'pointer'
                    }}
                    onClick={(e) => {
                        console.log('Premium кнопка нажата!');
                        console.log('Connected:', connected);
                        console.log('ActualConnected:', actualConnected);
                        console.log('Loading:', loading);
                        console.log('Recipient:', recipient);
                        if (!actualConnected || loading || !recipient) {
                            e.preventDefault();
                            console.log('Premium кнопка заблокирована');
                        }
                    }}
                >
                    {loading ? 'Обработка...' : (
                        recipient ? `Купить Premium ${duration} мес. за $${calculatePrice(duration)}` 
                                  : 'Выберите получателя'
                    )}
                </button>
            </form>

            {!actualConnected && !loading && (
                <div className="status-info">
                    ⚠️ Подключите TON кошелек через кнопку "Connect Wallet" выше, чтобы купить Premium
                </div>
            )}

            {/* Status */}
            {status && (
                <div className={`status ${status.startsWith('✅') ? 'success' : status.startsWith('❌') ? 'error' : 'info'}`}>
                    {status}
                </div>
            )}
        </div>
    );
}