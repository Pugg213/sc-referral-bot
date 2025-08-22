import { useState, useEffect } from 'react';
import TonConnectButton from './components/TonConnectButton';
import StarsPurchaseForm from './components/StarsPurchaseForm';
import PremiumPurchaseForm from './components/PremiumPurchaseForm';
import './styles.css';

export default function App() {
    const [activeTab, setActiveTab] = useState('stars');
    const [tgUser, setTgUser] = useState(null);

    useEffect(() => {
        // Initialize Telegram Web App
        if (window.Telegram?.WebApp) {
            const tg = window.Telegram.WebApp;
            tg.ready();
            tg.expand();
            
            // Set theme colors to match design
            tg.setHeaderColor('#1673fa');
            tg.setBackgroundColor('#f8fafc');
            
            // Get user info
            setTgUser(tg.initDataUnsafe?.user);
            
            console.log('TMA initialized:', tg.initDataUnsafe);
        } else {
            // Development mode - simulate user
            setTgUser({ first_name: 'Developer', username: 'dev' });
            console.log('TMA running in development mode');
        }
    }, []);

    const tabs = [
        { id: 'stars', label: '⭐ Stars', component: StarsPurchaseForm },
        { id: 'premium', label: '💎 Premium', component: PremiumPurchaseForm }
    ];

    const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component || StarsPurchaseForm;

    return (
        <div className="container">
            <h1 style={{ 
                textAlign: 'center', 
                fontSize: '24px', 
                fontWeight: '700', 
                color: '#1a3185', 
                marginBottom: '24px',
                marginTop: '12px'
            }}>
                Buy stars & premium
            </h1>

            <TonConnectButton />

            {/* Tab Navigation */}
            <div style={{ 
                display: 'flex', 
                gap: '8px', 
                marginBottom: '24px',
                background: '#fff',
                padding: '8px',
                borderRadius: '12px',
                boxShadow: '0 4px 12px rgba(26, 49, 133, 0.08)'
            }}>
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        className={`button ${activeTab === tab.id ? '' : 'button-secondary'}`}
                        style={{ 
                            flex: 1, 
                            padding: '12px 8px',
                            fontSize: '14px',
                            fontWeight: '600'
                        }}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            <ActiveComponent />


        </div>
    );
}