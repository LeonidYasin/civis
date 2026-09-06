# Civis — Republic of Professionals

Civis is a community-driven platform where professionals connect based on trust, values, and shared goals. The project is divided into two main components:

1. **Telegram Bot** — MVP for citizen registration, marketplace, and AI-powered matching.
2. **MCP Server** — Model Context Protocol server for AI-agent integrations.

---

## 🚀 Features

### Telegram Bot (MVP)

- **Registration** — Multi-step onboarding (name, about, values, role, format)
- **Multilingual** — English and Russian support
- **Profile Management** — View and update your profile
- **Citizens List** — Browse all registered citizens
- **Marketplace** — Publish and browse offers and requests
- **AI Matching** — Semantic search and recommendations via embeddings
- **Subscription Plans** — Free, Premium ($9.99/mo), Lifetime ($99)
- **Support** — Contact developer directly via `/support`
- **Admin Notifications** — Support messages forwarded to the admin group

### MCP Server

- **GitHub Actions Tools** — List workflow runs, get latest run ID, fetch logs by step
- **Synapse Protocol** — Publish profiles, search people, propose contacts, index GitHub

---

## 🛠 Tech Stack

- **Bot** — Python 3.10+, pyTelegramBotAPI, SQLite
- **AI** — OpenAI API (embeddings, matching)
- **MCP** — Flask-based MCP server with auto-discovery
- **Deployment** — GitHub Actions, Docker (optional)

---

## 📁 Project Structure

```
civis/
├── civis_bot/                 # Telegram Bot
│   ├── bot.py                 # Entry point
│   ├── config.py              # Configuration & env
│   ├── database.py            # SQLite operations
│   ├── handlers/              # Command handlers (modular)
│   │   ├── commands.py        # All bot commands
│   │   ├── survey.py          # Registration flow
│   │   └── language.py        # Language selection
│   ├── keyboards.py           # Reply keyboards
│   ├── locales.py             # i18n (EN/RU)
│   ├── utils.py               # Helpers (embeddings, matching)
│   └── .env.example           # Environment template
├── mcp_server/                # MCP Server
│   ├── app.py                 # Flask app
│   ├── tools/                 # Auto-discovered tools
│   │   ├── github/            # GitHub Actions tools
│   │   └── synapse/           # Synapse protocol tools
│   └── requirements.txt
├── CHANGELOG.md               # Version history
├── CONTRIBUTING.md            # Contribution guidelines
└── README.md                  # This file
```

---

## 🚦 Getting Started

### Prerequisites

- Python 3.10+
- Telegram Bot Token (from @BotFather)
- OpenAI API Key (optional, for AI matching)

### Installation

```bash
# Clone the repository
git clone https://github.com/LeonidYasin/civis.git
cd civis

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp civis_bot/.env.example civis_bot/.env

# Edit .env with your tokens
nano civis_bot/.env
```

### Running the Bot

```bash
cd civis_bot
python bot.py
```

### Running the MCP Server

```bash
cd mcp_server
python app.py
```

---

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Create or view your profile |
| `/menu` | Show main menu |
| `/profile` | View your profile |
| `/embedding` | View your AI embedding profile |
| `/citizens` | List all citizens |
| `/search` | Search citizens |
| `/offer` | Publish an offer |
| `/request` | Publish a request |
| `/my_offers` | View your offers |
| `/my_requests` | View your requests |
| `/delete_offer` | Delete your offer by ID |
| `/delete_request` | Delete your request by ID |
| `/marketplace` | View marketplace |
| `/subscribe` | View subscription plans |
| `/match` | AI-powered matching |
| `/setkey` | Set OpenAI API key |
| `/language` | Change language |
| `/support` | Contact developer support |
| `/status` | Bot status |
| `/help` | Help |
| `/cancel` | Cancel current operation |
| `/done` | Finish value selection |

---

## 💰 Subscription Plans

| Plan | Price | Features |
|------|-------|----------|
| Free | $0/mo | 3 matches/month, basic profile, view citizens |
| Premium | $9.99/mo | Unlimited matches, priority search, profile export, early access |
| Lifetime | $99 one-time | All Premium features + MCP tools access + lifetime updates |

---

## 🧠 AI Matching

Civis uses OpenAI embeddings to match users based on their profile text:

1. User sets OpenAI API key via `/setkey`
2. Profiles are converted to embeddings
3. `/match` finds semantically similar profiles
4. Results show match score and profile details

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## 📄 License

MIT © Leonid Yasin

---

## 📬 Support

For support, use the `/support` command in the bot or open an issue on GitHub.

---

## 🔮 Future Roadmap

- [ ] Real AI-powered matching with OpenAI
- [ ] Payment integration (Stripe/PayPal)
- [ ] Webhook for serverless deployment
- [ ] Flutter mobile app
- [ ] Corporate accounts and white-labeling
- [ ] Private indexes for companies
