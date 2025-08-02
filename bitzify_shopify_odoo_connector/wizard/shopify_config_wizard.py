from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests


class ShopifyConfigWizard(models.TransientModel):
    _name = 'bitzify.shopify.config.wizard'
    _description = 'Shopify Configuration Wizard'

    # Step 1: Basic Configuration
    name = fields.Char('Configuration Name', required=True, default='My Shopify Store')
    shopify_store_url = fields.Char('Shopify Store URL', required=True, 
                                   help='Your store URL (e.g., mystore.myshopify.com)')
    api_access_token = fields.Char('API Access Token', required=True,
                                  help='Private app access token from Shopify Admin')
    webhook_secret = fields.Char('Webhook Secret', 
                                help='Optional: Webhook verification secret')
    
    # Step 2: Order Import Settings
    auto_import_orders = fields.Boolean('Auto Import Orders', default=True)
    import_interval_minutes = fields.Integer('Import Interval (minutes)', default=30)
    import_from_date = fields.Datetime('Import Orders From Date',
                                      help='Only import orders created after this date')
    
    # Step 3: Processing Settings
    auto_confirm_paid_orders = fields.Boolean('Auto Confirm Paid Orders', default=True)
    create_customers = fields.Boolean('Create Customers Automatically', default=True)
    default_product_id = fields.Many2one('product.product', 'Default Product',
                                        help='Product to use when Shopify product is not found')
    
    # Wizard state
    step = fields.Selection([
        ('basic', 'Basic Configuration'),
        ('import', 'Import Settings'),
        ('processing', 'Processing Settings'),
        ('summary', 'Summary & Test')
    ], default='basic', string='Current Step')
    
    # Test results
    connection_test_result = fields.Text('Connection Test Result', readonly=True)
    connection_test_success = fields.Boolean('Connection Test Success', readonly=True)

    def action_next_step(self):
        """Move to next configuration step"""
        if self.step == 'basic':
            # Test connection before proceeding
            self._test_connection()
            if self.connection_test_success:
                self.step = 'import'
            else:
                raise UserError(_('Please fix the connection issues before proceeding.'))
        elif self.step == 'import':
            self.step = 'processing'
        elif self.step == 'processing':
            self.step = 'summary'
        
        return self._return_wizard_view()

    def action_previous_step(self):
        """Move to previous configuration step"""
        if self.step == 'import':
            self.step = 'basic'
        elif self.step == 'processing':
            self.step = 'import'
        elif self.step == 'summary':
            self.step = 'processing'
            
        return self._return_wizard_view()

    def action_test_connection(self):
        """Test Shopify API connection"""
        self._test_connection()
        return self._return_wizard_view()

    def _test_connection(self):
        """Internal method to test Shopify connection"""
        try:
            if not self.shopify_store_url or not self.api_access_token:
                self.connection_test_result = 'Please fill in Store URL and API Access Token'
                self.connection_test_success = False
                return
                
            # Clean up store URL
            store_url = self.shopify_store_url.strip().lower()
            if not store_url.endswith('.myshopify.com'):
                if '.' not in store_url:
                    store_url = f"{store_url}.myshopify.com"
                    self.shopify_store_url = store_url
                    
            headers = {
                'X-Shopify-Access-Token': self.api_access_token,
                'Content-Type': 'application/json'
            }
            
            url = f"https://{store_url}/admin/api/2023-10/shop.json"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                shop_data = response.json().get('shop', {})
                shop_name = shop_data.get('name', 'Unknown')
                plan_name = shop_data.get('plan_name', 'Unknown')
                
                self.connection_test_result = f"""
Connection Successful!
- Shop Name: {shop_name}
- Plan: {plan_name}
- Domain: {shop_data.get('domain', 'Unknown')}
- Timezone: {shop_data.get('timezone', 'Unknown')}
                """.strip()
                self.connection_test_success = True
                
                # Update name if it's still default
                if self.name == 'My Shopify Store':
                    self.name = f"{shop_name} Connector"
                    
            elif response.status_code == 401:
                self.connection_test_result = 'Authentication failed. Please check your API Access Token.'
                self.connection_test_success = False
            elif response.status_code == 404:
                self.connection_test_result = 'Store not found. Please check your Store URL.'
                self.connection_test_success = False
            else:
                self.connection_test_result = f'Connection failed: {response.status_code} - {response.text}'
                self.connection_test_success = False
                
        except requests.exceptions.Timeout:
            self.connection_test_result = 'Connection timeout. Please try again.'
            self.connection_test_success = False
        except requests.exceptions.RequestException as e:
            self.connection_test_result = f'Connection error: {str(e)}'
            self.connection_test_success = False
        except Exception as e:
            self.connection_test_result = f'Unexpected error: {str(e)}'
            self.connection_test_success = False

    def action_create_connector(self):
        """Create the Shopify connector configuration"""
        if not self.connection_test_success:
            raise UserError(_('Please test the connection successfully before creating the connector.'))
            
        # Create the connector
        connector_vals = {
            'name': self.name,
            'shopify_store_url': self.shopify_store_url,
            'api_access_token': self.api_access_token,
            'webhook_secret': self.webhook_secret,
            'auto_import_orders': self.auto_import_orders,
            'import_interval_minutes': self.import_interval_minutes,
            'import_from_date': self.import_from_date,
            'auto_confirm_paid_orders': self.auto_confirm_paid_orders,
            'create_customers': self.create_customers,
            'default_product_id': self.default_product_id.id if self.default_product_id else False,
            'is_active': True,
        }
        
        connector = self.env['bitzify.shopify.connector'].create(connector_vals)
        
        # Show success message and redirect to connector
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shopify Connector',
            'res_model': 'bitzify.shopify.connector',
            'res_id': connector.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_import_orders_now(self):
        """Import orders immediately after creating connector"""
        connector = self.env['bitzify.shopify.connector'].search([
            ('shopify_store_url', '=', self.shopify_store_url)
        ], limit=1)
        
        if connector:
            return connector.import_orders_manual()
        else:
            raise UserError(_('Connector not found. Please create the connector first.'))

    def _return_wizard_view(self):
        """Return wizard view for multi-step process"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bitzify.shopify.config.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def get_webhook_info(self):
        """Get webhook configuration information"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        webhook_url = f"{base_url}/bitzify/shopify/webhook"
        
        return {
            'webhook_url': webhook_url,
            'events': [
                'orders/create',
                'orders/updated',
                'orders/paid', 
                'orders/cancelled'
            ]
        }
