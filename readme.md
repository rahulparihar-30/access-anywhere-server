<div align="center" style="margin: 0px auto; padding: 20px; border-radius: 10px; width: 60%;">
<img src="./icon.png" alt="Icon" height="150px" width="150px" />
<h2 style="margin: 0;">Access Anywhere</h2>
<p>A cross-platform mobile application that allows you to remotely access, preview, and manage files on your desktop or laptop directly from your iOS or Android device. No need to be in front of your computer your files are always with you.</p><br/>
<a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
</a>
<a href="https://github.com/rahulparihar-30/access-anywhere-server/graphs/contributors">
    <img src="https://img.shields.io/github/contributors/rahulparihar-30/access-anywhere-server" alt="Contributors">
</a>
<a href="https://github.com/rahulparihar-30/access-anywhere-server/issues">
    <img src="https://img.shields.io/github/issues/rahulparihar-30/access-anywhere-server" alt="Issues">
</a>
</div>

# 🎉 Hacktoberfest Participation

This repository is participating in **Hacktoberfest**! 🎃🍂
This repository serves as the **backend** for the **Access Anywhere** application. It is responsible for handling file management operations, secure communication, and real-time synchronization between the desktop and mobile app.

The backend repository can be found here: [Access Anywhere Server](https://github.com/rahulparihar-30/access-anywhere-server)
## 🌟 Key Features

This application focuses on providing a secure, seamless, and user-friendly experience for remote file management.

- **Cross-Platform Compatibility**: A single codebase for both **iOS and Android** using React Native.
- **Complete File Management**: Securely **browse, upload, download, rename, and delete** files on your remote computer.
- **Real-Time Synchronization**: Instantly see file changes on your mobile device as they happen on the desktop.
- **Robust Security**: Built with strong **AES-256 encryption** to ensure your data is always protected during transfers.
- **Optimized Performance**: Engineered for **low latency** and includes **offline access** to files you've previously viewed.

## 🛠️ Tech Stack & Architecture

The project is built with a modern, scalable technology stack.

- **Frontend (Mobile App)**: **React Native**
- **Backend (Server)**: **Python** with the **FastAPI** framework
- **Communication**: Secure **HTTPS** and **WebSocket** protocols for real-time communication

The system uses a simple client-server architecture where the desktop runs a lightweight Python server, and the mobile app acts as the client to manage files.

## 🚀 Getting Started

Follow these instructions to get a local copy up and running for development and testing.

### Prerequisites

- Node.js & npm
- Python 3.8+ & pip
- React Native development environment (Xcode or Android Studio)

### Backend Setup

### Quick Start Guide for Flask API Server

Follow these steps to set up and run the Flask API server locally:

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/rahulparihar-30/access-anywhere-server.git
    cd access-anywhere-server
    ```

2. **Set Up a Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Run the Server**:
    ```bash
    python app.py
    ```

5. **Access the API**:
    Open your browser or API client (e.g., Postman) and navigate to:
    ```
    http://localhost:3000
    htttp://<your-ip-address>:3000
    http://127.0.0.1:3000
    ```

You're now ready to use the Flask API server for development and testing!

### Frontend Setup

- Refer the frontend repository: [Access Anywhere Frontend](https://github.com/rahulparihar-30/access-anywhere)


## 🗺️ Project Roadmap

This project is actively being developed. Here are some of the planned future enhancements:

- **Enhanced Security**: Implement **end-to-end encryption** for all file transfers to ensure robust security without relying on third-party cloud services.
- **Direct Access Methods**: Replace QR code-based access with a simpler **PIN-based authentication** or **device pairing** for seamless connectivity.
- **Faster File Transfers**: Optimize the file transfer protocol to achieve **high-speed performance** even on low-bandwidth networks.
- **No Cloud Dependency**: Ensure all file transfers and management occur directly between devices, maintaining **complete user privacy**.
- **User-Friendly Setup**: Simplify the initial setup process to make it more intuitive for non-technical users.
- **Customizable Access Permissions**: Allow users to define specific access permissions for connected devices.
- **Cross-Network Connectivity**: Enable file access across different networks using **NAT traversal** or **peer-to-peer connections**.

## 🎨 User-Friendly UI Enhancements

To ensure a seamless and intuitive user experience, the following UI improvements are planned:

- **Modern Design**: Implement a clean and responsive UI using **Material Design** principles for a consistent look and feel across devices.
- **Dark Mode**: Provide a **dark mode** option for better usability in low-light environments.
- **Drag-and-Drop Support**: Enable **drag-and-drop functionality** for file uploads and organization.
- **Interactive Tutorials**: Add **onboarding tutorials** to guide new users through the app's features.
- **Customizable Themes**: Allow users to personalize the app with **custom themes** and color schemes.
- **Accessibility Features**: Ensure the app is accessible to all users by adding **screen reader support**, **high-contrast mode**, and **scalable text sizes**.
- **Real-Time Notifications**: Display **real-time notifications** for file transfers, errors, and updates.
- **Search and Filters**: Introduce a **search bar** and advanced **filtering options** to quickly locate files.

These enhancements aim to make the application more engaging and user-centric. Feedback is always welcome to further refine the user experience!

Have an idea? Feel free to open an issue to discuss it\!

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

If you find this project helpful, please consider giving it a ⭐ on GitHub! It helps others discover the project and motivates us to keep improving it.

---
