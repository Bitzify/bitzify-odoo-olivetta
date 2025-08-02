# Bitzify Shopify Order Connector

A streamlined Shopify integration for Odoo 17 focused specifically on order data import.

## Features

### 🛒 Order Management
- **Real-time Order Import**: Receive orders instantly via Shopify webhooks
- **Scheduled Synchronization**: Automatic order import at configurable intervals
- **Order Status Tracking**: Monitor financial and fulfillment status from Shopify
- **Customer Auto-Creation**: Automatically create customer records from Shopify data

### 🔧 Easy Configuration
- **Setup Wizard**: Step-by-step configuration guide
- **Connection Testing**: Verify Shopify API credentials before setup
- **Flexible Settings**: Customize import behavior and processing rules

### 🔄 Real-time Updates
- **Webhook Support**: Instant notifications for order changes
- **Status Synchronization**: Keep order statuses in sync between platforms
- **Secure Verification**: HMAC-SHA256 webhook signature verification

## Installation

1. **Download/Clone** this module to your Odoo addons directory
2. **Update Apps List** in Odoo
3. **Install** the "Bitzify Shopify Order Connector" module
4. **Run the Setup Wizard** from the Shopify menu

## Quick Setup

### Step 1: Create a Private App in Shopify

1. Go to your **Shopify Admin** → **Apps and sales channels**
2. Click **"Develop apps"** → **"Create an app"**
3. Give your app a name (e.g., "Odoo Integration")
4. Click **"Configure Admin API scopes"**

### Step 2: Configure API Permissions

Enable the following scopes:
- `read_orders` - To read order data
- `write_orders` - To update order status (optional)
- `read_customers` - To read customer data
- `write_customers` - To create/update customers (optional)

### Step 3: Install the App

1. Click **"Install app"**
2. Copy the **Admin API access token**
3. Keep this token secure - you'll need it for Odoo configuration

### Step 4: Configure in Odoo

1. Go to **Bitzify Shopify** → **Configuration** → **Quick Setup**
2. Follow the setup wizard:
   - Enter your store URL (e.g., `mystore.myshopify.com`)
   - Paste the API access token
   - Configure import and processing settings
3. Test the connection
4. Complete the setup

## Webhook Configuration (Recommended)

For real-time order updates, configure webhooks in Shopify:

1. Go to **Settings** → **Notifications** in Shopify Admin
2. Scroll to **"Webhooks"** section
3. Click **"Create webhook"**
4. Use URL: `https://yourdomain.com/bitzify/shopify/webhook`
5. Select **JSON** format
6. Choose these events:
   - `orders/create`
   - `orders/updated`
   - `orders/paid`
   - `orders/cancelled`

## Configuration Options

### Import Settings
- **Auto Import Orders**: Enable automatic order synchronization
- **Import Interval**: How often to check for new orders (minutes)
- **Import From Date**: Only import orders after this date

### Processing Settings
- **Auto Confirm Paid Orders**: Automatically confirm orders marked as paid in Shopify
- **Create Customers**: Automatically create customer records for new Shopify customers
- **Default Product**: Product to use when Shopify products aren't found in Odoo

## Usage

### Manual Order Import
1. Go to **Bitzify Shopify** → **Configuration** → **Shopify Connectors**
2. Open your connector configuration
3. Click **"Import Orders Now"**

### View Shopify Orders
1. Go to **Bitzify Shopify** → **Orders** → **Shopify Orders**
2. View all orders imported from Shopify
3. Check order status and financial information

### Order Status Indicators
- **Financial Status**: Shows payment status (Paid, Pending, Refunded, etc.)
- **Fulfillment Status**: Shows shipping status (Fulfilled, Unfulfilled, Partial)

## Troubleshooting

### Connection Issues
- Verify your store URL format (should include `.myshopify.com`)
- Check that your API access token is correct
- Ensure required API scopes are enabled

### Missing Orders
- Check the "Import From Date" setting
- Verify webhook configuration
- Review the connector's sync status and error messages

### Webhook Problems
- Verify webhook URL is accessible from the internet
- Check webhook secret configuration
- Review Odoo logs for webhook processing errors

## Technical Details

### Models
- `bitzify.shopify.connector` - Main connector configuration
- Extended `sale.order` - Added Shopify-specific fields
- Extended `res.partner` - Added Shopify customer ID tracking

### Controllers
- `/bitzify/shopify/webhook` - Webhook endpoint for real-time updates
- `/bitzify/shopify/test` - Simple connectivity test endpoint

### Scheduled Actions
- **Import Orders Cron**: Runs every 30 minutes by default (configurable)

## Security

- HMAC-SHA256 webhook signature verification
- API tokens stored securely in database
- Public webhook endpoint with signature validation

## Requirements

- Odoo 17.0
- Python `requests` library
- Internet connectivity for Shopify API access
- Valid Shopify store with Admin API access

## Support

For issues, feature requests, or contributions:
1. Check the connector's sync status in Odoo
2. Review Odoo server logs for detailed error messages
3. Verify Shopify API credentials and permissions

## License

LGPL-3
