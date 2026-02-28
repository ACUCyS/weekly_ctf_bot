<div>
  <h1>Weekly CTF Bot</h1>
  <p>
    A Discord bot designed to help host weekly CTF challenges for ACUCyS.
  </p>
</div>

## 📂 Project Structure

```
weekly_ctf_bot/
├── src/
│   └── weekly_ctf_bot/   # Project source root
│       ├── cogs/         # Discord slash commands
│       ├── config.py     # Configuration handler
│       ├── database.py   # Abstraction for database models and access
│       ├── errors.py     # Project error definitions
│       ├── __init__.py   # Main bot code
│       └── __main__.py   # Bot entrypoint
│
├── .env                  # Environment variables
├── CONTRIBUTING.md       # Contributing guide
├── LICENSE               # Project software license
├── pyproject.toml        # Project metadata & dependencies
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- [Poetry 1.8.0 or higher](https://python-poetry.org/docs/#installation).
- Python 3.14 or higher.

### 1. Clone Repository

```bash
git clone https://github.com/acucys/weekly_ctf_bot.git
cd weekly_ctf_bot
```

### 2. Install Dependencies

```bash
# Change `3.14` if you wish to use a different Python version
poetry env use 3.14
poetry install
```

### 3. Configure Environment

Create a `.env` file using the provided `.env.example` template:

```bash
cp .env.example .env
```

Fill in required values:

- `BOT_MODE=dev` _(or prod)_
- `BOT_TOKEN=<your Discord bot token>`
- `DATABASE_URL=<the url for your SQL database, with auth included>`

### 4. Run Bot

```bash
poetry run weekly_ctf_bot
```

This starts the discord bot in development mode.

## 🤝 Contributing

Please refer to the [contributing guide](CONTRIBUTING.md) for more details.
