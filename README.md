# Techno Track 🚀

Techno Track is an intelligent product analysis and tracking platform featuring a multi-agent architecture that elevates the e-commerce experience using AI.

This project aims to help users make smart shopping decisions by offering automated product recognition from images, in-depth price and review analysis, personalized buying advice, and an AI-powered conversational assistant.


## ✨ Key Features

- 🔍 **Visual Product Recognition (Visual Search):** Analyzes uploaded product photos to identify the product in seconds.
- 📊 **In-Depth Product Analysis:** Thoroughly examines technical specifications, pros/cons, and market conditions of products.
- 💬 **Smart Chat Assistant (Chat Widget):** A context-aware AI assistant that allows users to ask questions about products in natural language.
- ⚖️ **Device Comparison:** Places different products side-by-side to provide a detailed comparison of specifications, price, and performance.
- 📉 **Price Tracking & Campaigns:** Tracks the price history of products you're interested in and lists current campaigns (coupons, discounts).
- 🎨 **Modern & Dynamic UI:** A premium design focused on user experience, featuring dark mode support, glassmorphism effects, and fluid animations.

---

## 🤖 Multi-Agent Architecture

At the core of the system are specialized AI agents for specific tasks, coordinated by an Orchestrator. All models are powered by Google's robust **Gemini** infrastructure.

1. **👀 Vision Agent:** Uses the `Gemini 3 Flash` (with `Gemini 2.5 Flash` fallback) model to analyze images, extracting the product's brand, model, and features.
2. **🕵️‍♂️ Detective Agent:** Scours the web to gather up-to-date information, user reviews, and market data related to the product.
3. **🧠 Analyst Agent:** Interprets the gathered data, calculates the product's trust score, develops "buy/wait" strategies, and provides clear recommendations to the user.
4. **⚖️ Compare Agent:** Pulls data for two or more devices to present a comparative report on specifications, price-to-performance ratios, and user reviews.
5. **🎨 Visualizer Agent:** Utilizes `Imagen 3` to visualize how the product would look in different environments (e.g., in a room, with different outfit combinations).
6. **🎼 Orchestrator:** Triggers the appropriate agents based on the user's request, manages the data flow between them, and aggregates the final result to send to the frontend.

---

## 🛠️ Technologies Used

**Frontend (User Interface):**
- **React.js & Vite:** Fast and modern UI development.
- **Tailwind CSS:** Flexible and rapid styling.
- **Framer Motion:** Fluid, dynamic micro-animations and page transitions.
- **Lucide React:** Modern and clean icon set.

**Backend (Server & API):**
- **Python & FastAPI:** High-performance, asynchronous backend architecture.
- **Pydantic:** Data validation and type safety.
- **Uvicorn:** ASGI web server.
- **Google Generative AI SDK:** Access to Gemini models.

**Database & Storage:**
- **Supabase:** Secure and persistent storage of user data, product histories, logs, and agent results.


## 🚀 Installation and Setup

Follow these steps to run the project on your local environment.

### 1. Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- A [Google Gemini API Key](https://aistudio.google.com/)
- A [Supabase](https://supabase.com/) Project

### 2. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv
# For Windows: venv\Scripts\activate
# For Mac/Linux: source venv/bin/activate

# Install required libraries
pip install -r requirements.txt

# Set up environment variables (create a .env file and enter your details)
# Example content:
# GEMINI_API_KEY=your_gemini_api_key
# SUPABASE_URL=your_supabase_url
# SUPABASE_KEY=your_supabase_anon_key

# Start the backend server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Setup

Open a new terminal window and ensure you are in the project root directory.

```bash
# Install dependencies
npm install

# Start the development server
npm run dev
```

You can start using the application by navigating to `http://localhost:5173` (or the port provided by Vite) in your browser! 🎉

Notes: The products shown in the web application are examples. Not all products have been included.
---

## 🤝 Contributing

1. Fork this repository.
2. Create a new feature branch: `git checkout -b feature/new-awesome-feature`
3. Commit your changes: `git commit -m 'Add some awesome feature'`
4. Push to the branch: `git push origin feature/new-awesome-feature`
5. Open a Pull Request.

*If you encounter any issues during development, please feel free to report them in the Issues tab.*
