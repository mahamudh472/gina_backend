# Stripe Setup Guide

This guide details how to configure subscription products/prices in the Stripe Dashboard and set up local webhook forwarding to test checkout flows on your local development server.

---

## 1. Setting up Products & Prices in Stripe

1.  **Switch to Test Mode**: Go to your [Stripe Dashboard](https://dashboard.stripe.com/) and toggle **Test mode** (top-right corner).
2.  **Add Subscription Products**:
    *   Navigate to **Product Catalog** -> **Add Product**.
    *   Create the following three products:
        
        #### **Plan 1: Basic**
        *   **Name**: `Basic`
        *   **Price**: `9.90`
        *   **Currency**: `EUR` (or matching your config)
        *   **Billing Frequency**: `Recurring` -> `Monthly`
        
        #### **Plan 2: Core**
        *   **Name**: `Core`
        *   **Price**: `29.90`
        *   **Currency**: `EUR`
        *   **Billing Frequency**: `Recurring` -> `Monthly`
        
        #### **Plan 3: Pro**
        *   **Name**: `Pro`
        *   **Price**: `89.90`
        *   **Currency**: `EUR`
        *   **Billing Frequency**: `Recurring` -> `Monthly`
        
3.  **Retrieve Price & Product IDs**:
    *   After saving each product, open its details page.
    *   Copy the **Product ID** (starts with `prod_...`) and the **Price ID** (starts with `price_...`).
4.  **Sync Stripe IDs to Database**:
    *   Open `/apps/finance/management/commands/seed_plans.py` and replace the placeholder `stripe_price_id` and `stripe_product_id` keys with your actual Stripe Price/Product IDs.
    *   Run the command to update your DB records:
        ```bash
        python manage.py seed_plans
        ```

---

## 2. Testing Stripe Webhooks Locally (Stripe CLI)

Stripe webhooks require Stripe to send HTTP POST requests directly to your backend. Since `localhost` is not publicly accessible, we use the official **Stripe CLI** to forward events locally.

### Step 1: Install the Stripe CLI
*   **Debian/Ubuntu**:
    ```bash
    curl -s https://packages.stripe.dev/keyring.gpg | sudo gpg --dearmor -o /usr/share/keyrings/stripe.gpg
    echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main" | sudo tee /etc/apt/sources.list.d/stripe.list
    sudo apt-get update
    sudo apt-get install stripe
    ```
*   **macOS (Homebrew)**:
    ```bash
    brew install stripe/stripe-cli/stripe
    ```
*   **Windows**: Download the zip binary from [Stripe CLI Github Releases](https://github.com/stripe/stripe-cli/releases).

### Step 2: Authenticate Stripe CLI
In your terminal, run:
```bash
stripe login
```
Follow the browser prompt to log in to your Stripe account and authorize the CLI.

### Step 3: Forward webhook events
Start forwarding webhook events directly to your local Django endpoint:
```bash
stripe listen --forward-to http://localhost:8000/api/v1/webhooks/stripe/
```
The CLI will log a webhook signing secret in the output (starts with `whsec_...`). For example:
> `Your webhook signing secret is whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Step 4: Configure environment variables
Add the following keys to your `.env` file (updating placeholders with your actual keys and the CLI webhook secret):
```env
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

---

## 3. Production Webhook Setup

When preparing the project for staging or production:
1.  Go to the [Stripe Dashboard](https://dashboard.stripe.com/) -> **Developers** -> **Webhooks**.
2.  Click **Add Endpoint**.
3.  Set the **Endpoint URL** to:
    `https://yourdomain.com/api/v1/webhooks/stripe/`
4.  Configure the events to listen to:
    *   `checkout.session.completed`
    *   `invoice.paid`
    *   `customer.subscription.updated`
    *   `customer.subscription.deleted`
5.  Click **Add Endpoint**.
6.  Copy the signing secret (`whsec_...`) and configure it on your production server environment as `STRIPE_WEBHOOK_SECRET`.
