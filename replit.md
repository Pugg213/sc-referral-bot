# Overview

SC Referral Bot is a Telegram bot with a capsule-based referral system, anti-fraud mechanisms, and a Telegram Mini App (TMA) for purchasing Telegram Stars. The project combines a Python-based Telegram bot backend with a React-based frontend TMA, featuring off-chain SC token rewards, subscription gating, and integrated payment processing through the Rhombis API and TON blockchain.

# User Preferences

Preferred communication style: Simple, everyday language.

# Critical Agent Instructions ⚠️

## WEBHOOK CONFIGURATION - DO NOT MODIFY
- **NEVER change webhook URL** from: `https://a6f5cf38-d982-4526-a2b2-00e47ba5cb81-00-128py9dcpc4h7.picard.replit.dev/webhook`
- **NEVER restore** old webhook configurations from checkpoints or agent state
- **NEVER switch** to production domains like `music-generator-makalskii.replit.app`
- The bot requires the EXACT development domain for proper functionality
- Changing webhook breaks all bot button responses and user interactions

## PROTECTED FILES - HANDLE WITH CARE  
- `main.py` - Contains critical webhook protection logic, do not revert
- `run.py` - Fixed deployment mode detection, do not restore old versions
- Database files - Contain 55+ real user accounts, never reset or clear

# Recent Changes

## 2025-08-21: WEBHOOK SWITCHING PERMANENTLY ELIMINATED ✅
- ✅ **ROOT CAUSE ELIMINATED:** Complete removal of webhook auto-switching mechanisms
  - deploy.py: Removed all forced production environment variables (REPL_DEPLOYMENT, REPLIT_DEPLOYMENT)
  - main.py: Removed auto_fix_webhook_if_needed() and auto_fix_production_webhook() functions
  - Webhook now set once at startup and remains completely stable
- ✅ **WEBHOOK LOCKED & STABLE:**
  - Development: https://a6f5cf38-d982-4526-a2b2-00e47ba5cb81-00-128py9dcpc4h7.picard.replit.dev/webhook
  - No more automatic switching to wrong domains (music-generator-makalskii.replit.app)
  - System will properly detect deployment mode without forced flags
- ✅ **FULL SYSTEM FUNCTIONALITY:**
  - Bot @scReferalbot (ID: 7393209394) responding to all user interactions
  - New user registration working (user 364908039 registered successfully)
  - Database operations stable with 55+ users
  - TMA integration functional with React components
  - Error handling prevents application crashes
- 🎯 **STATUS: WEBHOOK ISSUES PERMANENTLY RESOLVED**
  - Problem source identified and completely eliminated
  - Development environment stable and ready for production deployment
  - All automatic webhook switching mechanisms removed

## 2025-08-21: TMA UI/UX Enhancements
- ✅ Removed pricing display ("$1.34 USD включая комиссию") from Stars purchase form
- ✅ Created multifunctional wallet connection button with modern design
- ✅ Enhanced user experience: gradients, animations, loading states, visual feedback
- ✅ Improved wallet status display with address truncation and clear state indicators

# System Architecture

## Backend Architecture
- **Framework**: Python with aiogram 3.x for Telegram bot handling
- **Database**: SQLite for persistent data storage with connection pooling
- **State Management**: FSM (Finite State Machine) for user onboarding flows
- **Background Processing**: Asyncio-based validation loop for referral verification
- **Configuration**: Environment-based settings with dotenv support

## Frontend Architecture
- **Framework**: React 19.x with Vite as the build tool
- **UI Components**: Modern component-based architecture for TMA interface
- **State Management**: React hooks for local state management
- **Build System**: Vite for development and production builds

## Key Design Patterns
- **Context Pattern**: Global dependency injection for database and configuration access
- **Router Pattern**: Modular handler organization using aiogram routers
- **Service Layer**: Separate services for capsules, captcha, scoring, and API integrations
- **Middleware**: Subscription guard middleware for access control
- **Repository Pattern**: Database abstraction layer with connection management

## Security and Anti-Fraud
- **Risk Scoring**: Multi-factor risk assessment including account age, captcha performance, and activity patterns
- **Quarantine System**: Time-based restrictions for new referrals
- **Captcha Verification**: Mathematical challenges with timing analysis
- **Subscription Gating**: Mandatory channel/group membership verification

## Data Storage
- **User Management**: Comprehensive user profiles with referral tracking, earnings, and risk scores
- **Transaction Tracking**: Capsule openings, rewards, and payment history
- **Task System**: Dynamic partner tasks with completion tracking
- **Session Management**: Captcha sessions and user state persistence

## Payment Integration
- **TON Blockchain**: TON Connect integration for wallet connectivity
- **Rhombis API**: Third-party payment processor for Telegram Stars purchases
- **Off-chain Balancing**: Internal SC token accounting with batch payouts

# External Dependencies

## Third-Party APIs
- **Telegram Bot API**: Core bot functionality and webhook handling
- **Rhombis API**: Payment processing for Telegram Stars and Premium subscriptions
- **TON Connect**: Blockchain wallet integration for payments

## Development Tools
- **Aiogram 3.x**: Modern async Telegram bot framework
- **Vite**: Frontend build tool and development server
- **Python-dotenv**: Environment configuration management

## Deployment Infrastructure
- **Replit**: Primary hosting platform with automatic domain management
- **SQLite**: Embedded database requiring no external setup
- **Webhook System**: Production webhook configuration with automatic URL updates

## Blockchain Integration
- **@ton/core**: TON blockchain interaction library
- **@tonconnect/ui**: User interface components for wallet connections
- **Buffer polyfill**: Node.js compatibility for browser environments

## Payment Dependencies
- **Stripe Libraries**: React Stripe components for payment UI (@stripe/react-stripe-js, @stripe/stripe-js)
- **OpenID Client**: Authentication integration capabilities