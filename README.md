# Restaurant Order Web Application

This project is an end-to-end restaurant order web application built with Flask. It starts from a simple web form to handle customer orders and progresses through several levels of complexity, including database integration, payment processing, and cloud deployment.

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Levels of Complexity](#levels-of-complexity)
  - [Level 1: Basic Web Form](#level-1-basic-web-form)
  - [Level 2: Order Viewing and Validation](#level-2-order-viewing-and-validation)
  - [Level 3: Payment Integration](#level-3-payment-integration)
  - [Level 4: Cloud Deployment and Logging](#level-4-cloud-deployment-and-logging)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Project Overview

This application allows restaurant customers to place orders online. It begins as a simple form where users can enter their order details and gradually evolves to include features like order history, payment integration, and cloud deployment.

## Features

- Simple web form to collect order details.
- Local database to store and retrieve orders.
- Input validation for order details.
- Payment processing with third-party API integration (Stripe).
- Cloud deployment with support for multiple users.
- Basic logging for tracking orders and errors.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/restaurant_order.git
   cd restaurant_order
   ```

2. Set up a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

## Project Structure

```plaintext
restaurant_order/
│
├── app.py               # Main application file
├── templates/           # HTML templates
│   ├── base.html
│   ├── index.html
│   └── order.html
├── static/              # Static files like CSS
│   └── style.css
└── requirements.txt     # Python dependencies
```

## Levels of Complexity

### Level 1: Basic Web Form

- **Objective:** Build a simple web form using Flask where users can input an order for a restaurant.
- **Details:** Collect basic order details such as customer name, phone number, and order items.
- **Database:** Use SQLite for local storage of order details.

### Level 2: Order Viewing and Validation

- **Objective:** Enhance the form to allow users to view past orders.
- **Details:** Implement basic validation to ensure that order details are correctly entered before submission.
- **Features:** Display a list of past orders stored in the database.

### Level 3: Payment Integration

- **Objective:** Integrate the application with a third-party API (like Stripe) for handling payments.
- **Details:** Ensure that order details are securely processed and payments are handled using the Stripe API.

### Level 4: Cloud Deployment and Logging

- **Objective:** Deploy the application to a cloud service (like Render) ensuring it can handle multiple simultaneous users.
- **Details:** Add basic logging to track orders and application errors. Set up environment variables for sensitive information like API keys.

## Usage

After installing and running the application, navigate to `http://127.0.0.1:5000` in your browser to start placing orders.
