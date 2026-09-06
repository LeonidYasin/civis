# Changelog

All notable changes to the Civis project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-09-06

### Added
- **AI Matching** — Initial implementation of AI-powered matching using OpenAI embeddings
- **Subscription System** — Free, Premium ($9.99/mo), and Lifetime ($99) plans
- **OpenAI API Key Management** — `/setkey` command for BYOK (Bring Your Own Key)
- **Support System** — `/support` command with admin forwarding to group/private chat
- **Search** — `/search` command to find citizens by name, role, or values
- **Delete Commands** — `/delete_offer` and `/delete_request` to remove own listings
- **Back Button** — `/back` navigation during registration
- **Modular Handlers** — Reorganized code into `handlers/` package
- **Admin Chat ID** — Configurable `ADMIN_CHAT_ID` for support forwarding
- **Logging** — Enhanced logging with chat ID and group detection
- **Keyboard Layouts** — Optimized with `row_width` for mobile display

### Changed
- **Project Structure** — Monolithic `bot_sync.py` split into modules:
  - `database.py` — All SQLite operations
  - `handlers/commands.py` — Command handlers
  - `handlers/survey.py` — Registration flow
  - `handlers/language.py` — Language selection
  - `keyboards.py` — Reply keyboards
  - `utils.py` — Helper functions (embeddings, matching)
  - `locales.py` — i18n (EN/RU)
  - `config.py` — Configuration and env
- **Roles** — Expanded roles: Executor, Customer, Coordinator, Investor, Seller, Buyer
- **Formats** — Updated: Text, Voice, Video, Any
- **Marketplace** — Added ID display for offers and requests
- **Bot Commands** — Updated command list in sidebar menu
- **Locales** — Added subscription and matching texts for both languages
- **Keyboard** — Added `/support`, `/search`, `/delete_offer`, `/delete_request` buttons

### Fixed
- **Localization** — Fixed Russian language support for roles and formats
- **Keyboard Layout** — Fixed row display (2-3 columns) using `keyboard.row()`
- **Import Errors** — Fixed circular imports and missing `ReplyKeyboardRemove`
- **Support Forward** — Fixed `chat not found` error with group IDs
- **Session Handling** — Fixed state management for registration flow

## [0.2.0] - 2026-09-05

### Added
- **Marketplace** — Offers and requests system (`/offer`, `/request`, `/marketplace`)
- **My Listings** — `/my_offers` and `/my_requests` commands
- **Embedding Profile** — `/embedding` command to view AI-compatible profile
- **Citizens List** — `/citizens` command
- **Profile Management** — Update profile via `/survey`
- **Language Selection** — English and Russian support
- **Status Command** — `/status` with profile and marketplace stats
- **Database** — SQLite with users, sessions, offers, requests tables
- **Proxy Support** — Configurable proxy for Telegram API

### Changed
- **Registration Flow** — Multi-step: name → about → values → role → format
- **Values** — 10 core values: Honesty, Expertise, Initiative, Reliability, Speed, Empathy, Systematic, Creativity, Openness, Ambition
- **Keyboards** — Dynamic keyboards for values, roles, formats

### Fixed
- **Registration** — Fixed profile completion status
- **Session** — Fixed session clearing after completion
- **Error Handling** — Added proper error messages for invalid input

## [0.1.0] - 2026-08-28

### Added
- **Initial Release** — Basic Telegram bot with:
  - User registration (name, about, values, role, format)
  - Profile viewing (`/profile`)
  - Help command (`/help`)
  - Cancel command (`/cancel`)
- **Database** — SQLite with users and sessions tables
- **Locales** — English and Russian text templates
- **Proxy Support** — HTTP/HTTPS/SOCKS5 proxy

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality
- **PATCH** version for backwards-compatible bug fixes

Current version: `0.3.0`

---

## Upcoming (Roadmap)

### 0.4.0 — Planned
- Real AI-powered matching with OpenAI
- Payment integration (Stripe/PayPal)
- Webhook for serverless deployment

### 0.5.0 — Planned
- Flutter mobile app
- Corporate accounts and white-labeling
- Private indexes for companies

### 1.0.0 — Vision
- Full Synapse protocol
- MCP tools for GitHub, Telegram, and more
- Decentralized profile storage (Gist/Repo)
