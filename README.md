# 🦝 Mise

> *Everything in its place* - Your AI-powered cooking companion

Mise (pronounced "MEEZ") is a voice-first cooking assistant that guides you through recipes hands-free. Named after the French culinary term "mise en place," it helps you stay organized in the kitchen with your friendly raccoon sous chef, Bruno.

## ✨ Features

- 🎤 **Voice-First Interface** - Hands-free cooking guidance (no touching your phone with messy hands!)
- 🍳 **Smart Recipe Search** - Find recipes based on ingredients you have
- 📝 **Kitchen History** - Track what you've cooked and your modifications
- 🧠 **Context Aware** - Remembers your dietary preferences and ingredient dislikes
- 📱 **Mobile-First Design** - Built for use in the kitchen
- 🔄 **Session Resumption** - Disconnected? Pick up right where you left off

## 🏗️ Architecture

- **frontend/** - SvelteKit application (Svelte 5, TypeScript) with MCP integration
- **PocketBase/** - Docker-based PocketBase backend service

## 🛠️ Tech Stack

- **Frontend:** SvelteKit + Svelte 5 + TypeScript + Tailwind CSS
- **Backend:** PocketBase (auth + database)
- **Voice Agent:** LiveKit Agents + OpenAI GPT-4
- **APIs:** Spoonacular (recipes), Deepgram (STT), ElevenLabs (TTS)
- **Deployment:** Nginx reverse proxy

## 🚀 Quick Start

### Prerequisites

- Node.js v23+
- Docker & Docker Compose

### Frontend Setup

```bash
cd frontend
npm install --force   # --force needed for Node v23
npm run dev           # Start dev server at http://localhost:5173
```

### Backend Setup

```bash
cd PocketBase
docker compose up -d  # Start PocketBase container
```

PocketBase admin dashboard: `https://mise.elianrenteria.dev/_/`

### Available Commands

**Frontend:**
```bash
npm run dev           # Start dev server
npm run build         # Build for production
npm run preview       # Preview production build
npm run check         # Type-check with svelte-check
npm run check:watch   # Type-check in watch mode
```

**Backend:**
```bash
docker compose up -d    # Start PocketBase container
docker compose down     # Stop PocketBase container
docker compose logs -f  # View logs
```

## 📱 Features in Detail

### Voice-Guided Cooking
Tell Bruno what ingredients you have, and he'll suggest recipes and guide you through each step.

### Kitchen History
Every cooking session is saved with your modifications, ratings, and notes. Easily cook the same recipe again.

### Smart Learning
Mise remembers if you're vegetarian, hate cilantro, or prefer Greek yogurt over sour cream - and automatically filters suggestions.

### Session Resumption
Phone died mid-recipe? No problem. Rejoin and Bruno will remember exactly where you left off.

## 🦝 Meet Bruno

Bruno is your resourceful raccoon sous chef who helps you make the most of what you have. Organized, encouraging, and always ready to help you cook something delicious.

## 📄 License

MIT

## 🤝 Contributing

Contributions welcome!

---

Built with ❤️ by Elian Renteria