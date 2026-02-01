# Wordy (Anki German Helper) 🤖📚

**Master German faster with AI-powered flashcards.**

Wordy is a smart assistant that automates the creation of high-quality Anki cards. It monitors your clipboard, uses advanced AI (Ollama/OpenRouter) to provide perfect translations and context, and adds them to Anki with just one click.

![License](https://img.shields.io/badge/license-Personal%20Use-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

---

## ✨ Features

- 🤖 **AI Translations** — Powered by Llama 3, GPT-4, or any model via Ollama/OpenRouter.
- 📋 **Seamless Workflow** — Clip text in your browser, and Wordy instantly prepares it for Anki.
- 📚 **Anki Integration** — Adds cards directly via AnkiConnect.
- 🔊 **Instant Audio (TTS)** — High-quality text-to-speech for perfect pronunciation.
- 🎨 **Modern Interface** — Clean, dark/light theme support.
- 🌍 **Localized** — Fully supports English and Russian.

---

## 🚀 Quick Start

### 1. Requirements
- **Python 3.8+**
- **Anki** with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on installed.
- (Optional) [Ollama](https://ollama.ai/) for free, local AI processing.

### 2. Installation
```bash
git clone https://github.com/nimmaypum-jpg/Anki-card-andder.git wordy
cd wordy
pip install -r requirements.txt
```

### 3. Run
```bash
python main.py
```

---

## 🛠️ Usage

1. Open **Anki**.
2. Open **Ollama**
3.  Start **Wordy**.
4. **Copy** any German word or phrase.
5. Wordy will automatically generate translation and context.
6. Click **"To Anki"** — and you're done!

---

## ⚙️ AI Configuration

### Local (Ollama)
- Install Ollama and run: `ollama pull llama3.2`
- In Wordy settings, select **Ollama** as the provider.

### Cloud (OpenRouter)
- Get an API Key at [openrouter.ai](https://openrouter.ai/).
- Enter the key in settings and choose your preferred model.

---

## 📄 License

This project is for **Personal Use Only**. Commercial distribution or resale is prohibited. See the [LICENSE](LICENSE) file for details.

---

[🇷🇺 Читать на русском](README.ru.md)
