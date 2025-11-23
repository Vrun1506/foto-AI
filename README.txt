# FotoAI

FotoAI is an advanced photo editing application powered by AI technology. It is designed to effortlessly enhance and transform your images, offering powerful tools for both professional photographers and casual users. Whether you're fine-tuning a photo or creating stunning visual effects, FotoAI helps you achieve impressive results with ease.

## Table of Contents

1. [Installation](#installation)
2. [Running the Service](#running-the-service)
3. [Tech Stack](#tech-stack)
4. [Contributing](#contributing)
5. [License](#license)

---

## Installation

To set up FotoAI on your local machine, follow the instructions below.

### Prerequisites

Before you begin, make sure you have the following software installed:

* [Node.js](https://nodejs.org/) (v14 or higher)
* [Python](https://www.python.org/) (v3.8 or higher)
* [Oracle Agent Spec](https://www.oracle.com/), which powers the core API interactions
* [Wayflow Core](https://www.wayflow.ai/) for enhanced flow management

### Steps

1. **Clone the repository:**

   First, clone the project to your local machine:

   ```bash
   git clone https://github.com/Vrun1506/FotoAI.git
   cd FotoAI
   ```

2. **Install Node.js dependencies:**

   Navigate to the frontend directory and install the necessary dependencies:

   ```bash
   cd frontend
   npm install
   ```

3. **Install Python dependencies:**

   In the backend directory, install the required Python libraries:

   ```bash
   cd adb-mcp
   pip install -r requirements.txt
   ```

   In the overall directory, install the required Python libraries:

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables:**

   Copy the example environment file and update the variables with your credentials:

   ```bash
   cp .env.example .env
   ```

   Make sure to configure any relevant API keys, database settings, or other environment variables as needed.

---

## Running the Service

Now that you've set up the project, follow the steps below to start both the frontend and backend services.

### 1. Start the Backend (API Server)

From the `backend/api` directory, start the server using:

```bash
python server.py
```

This will run the backend API service, which will be available at `http://localhost:5001` by default.

On the `adb-mcp/adb-proxy-socket` directory, start the ADB proxy socket server using:
```bash
node proxy.js
```

This will run the ADB proxy socket server, which will be available at `http://localhost:3001` by default.

### 2. Start the Frontend (UI)

From the `frontend` directory, run:

```bash
npm run dev
```

This will launch the React app, and you can access the UI in your browser at `http://localhost:5173`.

Both the frontend and backend should now be running and connected. You can interact with the FotoAI service through the user interface.

---

## Tech Stack

FotoAI is built using a robust stack that includes the following technologies:

* **Oracle Agent Spec**: Core AI-powered logic for image enhancement.
* **React**: Frontend framework for building the user interface.
* **Wayflow Core**: Manages application workflows and integrations.
* **JavaScript**: For handling client-side interactions and logic.
* **Python**: Backend service for image processing and AI model execution.

---
