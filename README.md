<div align="center">

<h1>TikTok Live Recorder (Refactored)</h1>
<p>
  <b>An advanced, asynchronous, and modular tool for recording TikTok Live streams.</b>
</p>

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Asyncio](https://img.shields.io/badge/Asyncio-Powered-green?style=for-the-badge&logo=python)](https://docs.python.org/3/library/asyncio.html)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-red?style=for-the-badge&logo=ffmpeg)](https://ffmpeg.org/)

</div>

---

## 🚀 Overview

This project is a complete rewrite of the original TikTok Live Recorder, designed for **high performance** and **extensibility**. It shifts from a synchronous, multi-process architecture to a modern **asynchronous event-driven** system.

### Key Features

- **⚡ Asynchronous Core**: Built on `asyncio` and `aiohttp` for efficient resource usage, allowing you to monitor and record multiple streams simultaneously without heavy overhead.
- **🕵️ Stealth Requests**: Utilizes `curl_cffi` to mimic real browser fingerprints (Chrome 120+), significantly reducing the chance of being blocked/WAF'd by TikTok.
- **🧩 Modular Architecture**:
  - **Event Bus**: Decoupled components enable easy extension.
  - **Interface-based Recorders**: Currently supports **FFmpeg** for high-quality, direct stream copying (`-c copy`).
- **🔧 Type-Safe Config**: Configuration managed via `pydantic`, ensuring validation and easy setup via environment variables or `cookies.json`.

---

## 🛠️ Installation

### Prerequisites

- **Python 3.10+**
- **FFmpeg** installed and added to your system PATH.

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/SaharatM864/tiktok-live-recorder.git
    cd tiktok-live-recorder
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r src/requirements.txt
    ```

3.  **Prepare Cookies (Optional but Recommended):**
    - Export your `cookies.json` from your browser using a "EditThisCookie" extension.
    - Place it in the `src/` directory.

---

## 💻 Usage

Run the main application:

```bash
python src/main.py --user <username> --mode automatic
```

### Arguments

| Argument | Description | Default |
| :--- | :--- | :--- |
| `-u`, `--user` | TikTok username(s) to record. Can be multiple. | Required |
| `-m`, `--mode` | Recording mode: `manual` or `automatic`. | `manual` |
| `-r`, `--room-id` | Specific Room ID (optional). | None |
| `--proxy` | HTTP/HTTPS proxy URL. | None |
| `-o`, `--output` | Output directory for recordings. | `.` |
| `--duration` | Maximum recording duration (seconds). | Unlimited |

### Examples

**Record a specific user in automatic mode:**
```bash
python src/main.py -u some_user -m automatic
```

**Record multiple users:**
```bash
python src/main.py -u user1 user2 -m automatic
```

---

## 🏗️ Architecture

- **`src/core/monitor.py`**: The brain of the operation. Continuously checks live status using async loops.
- **`src/core/tiktok_api_async.py`**: Handles communication with TikTok's internal APIs asynchronously.
- **`src/core/events.py`**: Publishes events like `RECORDING_STARTED` and `RECORDING_FINISHED`.
- **`src/core/recorders/`**: Contains recorder implementations (e.g., `FFmpegRecorder`).

## ⚠️ Legal Disclaimer

This tool is for educational purposes only. Do not use it to infringe on copyright or violate TikTok's Terms of Service. The developers are not responsible for misuse.
