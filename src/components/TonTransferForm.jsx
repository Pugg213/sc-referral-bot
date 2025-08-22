import { useState, useEffect } from 'react';
import { getFee } from '../utils/api';
import { useTonConnect } from '../hooks/useTonConnect';

export default function TonTransferForm() {
    const [address, setAddress] = useState('');
    const [amount, setAmount] = useState('');
    const [status, setStatus] = useState('');
    const [loading, setLoading] = useState(false);
    const [fee, setFee] = useState(0);
    
    const tonConnect = useTonConnect();
    const { connected, sendTransaction } = tonConnect || { connected: false, sendTransaction: null };

    // Predefined amounts in TON
    const presets = ['0.1', '0.5', '1', '5', '10'];

    useEffect(() => {
        // Load fee information
        getFee().then(data => {
            setFee(data.fee || 0);
        }).catch(error => {
            console.error('Failed to load fee:', error);
        });
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!connected) {
            setStatus('Сначала подключите кошелек');
            return;
        }

        if (!address.trim()) {
            setStatus('Укажите адрес получателя');
            return;
        }

        const amountValue = parseFloat(amount);
        if (isNaN(amountValue) || amountValue <= 0) {
            setStatus('Укажите корректную сумму');
            return;
        }

        setLoading(true);
        setStatus('Создание транзакции TON...');

        try {
            // Convert TON to nanoTON (1 TON = 1e9 nanoTON)
            const nanoAmount = Math.floor(amountValue * 1e9);

            const tonTransaction = {
                validUntil: Math.floor(Date.now() / 1000) + 300, // 5 minutes
                messages: [{
                    address: address.trim(),
                    amount: nanoAmount.toString()
                }]
            };

            await sendTransaction(tonTransaction);

            setStatus(`✅ ${amount} TON успешно отправлены!`);
            setAddress('');
            setAmount('');

        } catch (error) {
            console.error('TON transfer error:', error);
            setStatus(`❌ Ошибка: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="main-panel">
            <div className="panel-title">
                <span className="panel-icon">💎</span>
                Перевод TON
            </div>

            <div className="stars-grid">
                {presets.map(preset => (
                    <div
                        key={preset}
                        className={`stars-preset ${amount === preset ? 'selected' : ''}`}
                        onClick={() => setAmount(preset)}
                    >
                        {preset} TON
                    </div>
                ))}
            </div>

            <form onSubmit={handleSubmit}>
                <div className="input-group">
                    <label className="input-label">Сумма (TON):</label>
                    <input
                        className="input"
                        type="number"
                        step="0.01"
                        min="0.01"
                        value={amount}
                        onChange={e => setAmount(e.target.value)}
                        placeholder="0.1"
                        required
                    />
                </div>

                <div className="input-group">
                    <label className="input-label">Адрес получателя:</label>
                    <input
                        className="input"
                        type="text"
                        placeholder="EQ... или UQ..."
                        value={address}
                        onChange={e => setAddress(e.target.value)}
                        required
                    />
                </div>

                {fee > 0 && (
                    <div className="fee-info">
                        Комиссия сети: ~{(fee * 100).toFixed(1)}%
                    </div>
                )}

                <button
                    className="button"
                    type="submit"
                    disabled={!connected || loading}
                >
                    {loading ? (
                        <>
                            <span className="loading"></span>
                            Отправка...
                        </>
                    ) : (
                        `Отправить ${amount || '0'} TON`
                    )}
                </button>
            </form>

            {status && (
                <div className={`status-${status.includes('✅') ? 'success' : status.includes('❌') ? 'error' : 'info'}`}>
                    {status}
                </div>
            )}
        </div>
    );
}