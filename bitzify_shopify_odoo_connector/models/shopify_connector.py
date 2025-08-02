from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import json
import logging
import hmac
import hashlib
import base64
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ShopifyConnector(models.Model):
    _name = 'bitzify.shopify.connector'
    _description = 'Bitzify Shopify Order Connector Configuration'
    _rec_name = 'name'

    name = fields.Char('Configuration Name', required=True)
    shopify_store_url = fields.Char(
        'Shopify Store URL', 
        required=True, 
        help='Your Shopify store URL (e.g., mystore.myshopify.com)'
    )
    api_access_token = fields.Char(
        'API Access Token', 
        required=True,
        help='Private app access token from Shopify Admin API'
    )
    webhook_secret = fields.Char(
        'Webhook Secret',
        help='Webhook verification secret from Shopify'
    )
    api_version = fields.Char(
        'API Version', 
        default='2023-10', 
        required=True,
        help='Shopify API version (e.g., 2023-10)'
    )
    is_active = fields.Boolean('Active', default=True)
    
    # Order import settings
    auto_import_orders = fields.Boolean('Auto Import Orders', default=True)
    import_interval_minutes = fields.Integer('Import Interval (minutes)', default=30)
    last_order_import = fields.Datetime('Last Order Import')
    import_from_date = fields.Datetime(
        'Import Orders From Date',
        help='Only import orders created after this date'
    )
    
    # Order processing settings
    auto_confirm_paid_orders = fields.Boolean('Auto Confirm Paid Orders', default=True)
    create_customers = fields.Boolean('Create Customers', default=True)
    default_product_id = fields.Many2one(
        'product.product',
        'Default Product',
        help='Product to use when Shopify product is not found in Odoo'
    )
    
    # Statistics
    total_orders_imported = fields.Integer('Total Orders Imported', readonly=True)
    last_sync_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('pending', 'Pending')
    ], string='Last Sync Status', readonly=True)
    last_sync_message = fields.Text('Last Sync Message', readonly=True)

    @api.constrains('shopify_store_url')
    def _check_store_url(self):
        for record in self:
            if record.shopify_store_url:
                url = record.shopify_store_url.strip().lower()
                if not url.endswith('.myshopify.com'):
                    if not '.' in url:
                        record.shopify_store_url = f"{url}.myshopify.com"
                    
    def test_connection(self):
        """Test connection to Shopify API"""
        self.ensure_one()
        try:
            headers = {
                'X-Shopify-Access-Token': self.api_access_token,
                'Content-Type': 'application/json'
            }
            
            url = f"https://{self.shopify_store_url}/admin/api/{self.api_version}/shop.json"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                shop_data = response.json().get('shop', {})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Successful'),
                        'message': _('Successfully connected to %s') % shop_data.get('name', 'Shopify store'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Connection failed: %s') % response.text)
                
        except requests.exceptions.RequestException as e:
            raise UserError(_('Connection error: %s') % str(e))
        except Exception as e:
            raise UserError(_('Unexpected error: %s') % str(e))

    def import_orders_manual(self):
        """Manual order import trigger"""
        self.ensure_one()
        try:
            imported_count = self._import_orders()
            self.last_sync_status = 'success'
            self.last_sync_message = f'Successfully imported {imported_count} orders'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Complete'),
                    'message': _('Imported %s orders successfully') % imported_count,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            self.last_sync_status = 'error'
            self.last_sync_message = str(e)
            raise UserError(_('Import failed: %s') % str(e))

    def _import_orders(self):
        """Import orders from Shopify"""
        self.ensure_one()
        
        headers = {
            'X-Shopify-Access-Token': self.api_access_token,
            'Content-Type': 'application/json'
        }
        
        # Build URL with parameters
        url = f"https://{self.shopify_store_url}/admin/api/{self.api_version}/orders.json"
        params = {
            'status': 'any',
            'limit': 250
        }
        
        # Add date filter if specified
        if self.import_from_date:
            params['created_at_min'] = self.import_from_date.isoformat()
        elif self.last_order_import:
            params['updated_at_min'] = self.last_order_import.isoformat()
            
        imported_count = 0
        page_info = None
        
        while True:
            if page_info:
                current_url = f"{url}?page_info={page_info}"
                response = requests.get(current_url, headers=headers, timeout=30)
            else:
                response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                raise UserError(_('API Error: %s') % response.text)
                
            data = response.json()
            orders = data.get('orders', [])
            
            for order_data in orders:
                try:
                    self._process_shopify_order(order_data)
                    imported_count += 1
                except Exception as e:
                    _logger.error(f"Error processing order {order_data.get('id')}: {e}")
                    
            # Check for pagination
            link_header = response.headers.get('Link', '')
            if 'rel="next"' in link_header:
                # Extract page_info from link header
                import re
                match = re.search(r'page_info=([^&>]+)', link_header)
                if match:
                    page_info = match.group(1)
                else:
                    break
            else:
                break
                
        self.last_order_import = fields.Datetime.now()
        self.total_orders_imported += imported_count
        
        return imported_count

    def _process_shopify_order(self, order_data):
        """Process a single Shopify order"""
        shopify_order_id = str(order_data['id'])
        
        # Check if order already exists
        existing_order = self.env['sale.order'].search([
            ('shopify_order_id', '=', shopify_order_id)
        ], limit=1)
        
        if existing_order:
            # Update existing order status if needed
            self._update_order_status(existing_order, order_data)
            return existing_order
            
        # Create or find customer
        partner = self._find_or_create_customer(order_data)
        
        # Create sale order
        order_vals = {
            'partner_id': partner.id,
            'shopify_order_id': shopify_order_id,
            'shopify_order_number': order_data.get('name', ''),
            'is_shopify_order': True,
            'shopify_financial_status': order_data.get('financial_status', 'pending'),
            'shopify_fulfillment_status': order_data.get('fulfillment_status', 'unfulfilled'),
            'date_order': fields.Datetime.from_string(order_data['created_at']),
            'note': order_data.get('note', ''),
            'client_order_ref': order_data.get('name', ''),
        }
        
        # Set shipping address if different
        shipping_address = order_data.get('shipping_address')
        if shipping_address:
            shipping_partner = self._create_shipping_address(partner, shipping_address)
            if shipping_partner:
                order_vals['partner_shipping_id'] = shipping_partner.id
        
        sale_order = self.env['sale.order'].create(order_vals)
        
        # Create order lines
        for line_item in order_data.get('line_items', []):
            self._create_order_line(sale_order, line_item)
            
        # Add shipping costs if any
        shipping_lines = order_data.get('shipping_lines', [])
        for shipping_line in shipping_lines:
            self._create_shipping_line(sale_order, shipping_line)
            
        # Auto-confirm if paid and setting is enabled
        if (self.auto_confirm_paid_orders and 
            order_data.get('financial_status') == 'paid'):
            try:
                sale_order.action_confirm()
            except Exception as e:
                _logger.warning(f"Could not auto-confirm order {sale_order.name}: {e}")
                
        return sale_order

    def _find_or_create_customer(self, order_data):
        """Find existing customer or create new one"""
        email = order_data.get('email')
        customer_data = order_data.get('customer', {})
        billing_address = order_data.get('billing_address', {})
        
        # Try to find existing customer by email
        if email:
            partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
            if partner:
                return partner
                
        # Try to find by Shopify customer ID
        shopify_customer_id = customer_data.get('id')
        if shopify_customer_id:
            partner = self.env['res.partner'].search([
                ('shopify_customer_id', '=', str(shopify_customer_id))
            ], limit=1)
            if partner:
                return partner
                
        # Create new customer if setting is enabled
        if not self.create_customers:
            # Return a default customer or raise an error
            default_partner = self.env.ref('base.public_partner', raise_if_not_found=False)
            if default_partner:
                return default_partner
            raise UserError(_('Customer creation is disabled and no default customer found'))
            
        # Create new customer
        partner_vals = {
            'name': billing_address.get('name') or customer_data.get('first_name', '') + ' ' + customer_data.get('last_name', ''),
            'email': email,
            'phone': billing_address.get('phone') or customer_data.get('phone', ''),
            'is_company': False,
            'customer_rank': 1,
            'shopify_customer_id': str(shopify_customer_id) if shopify_customer_id else False,
        }
        
        # Add address information
        if billing_address:
            partner_vals.update({
                'street': billing_address.get('address1', ''),
                'street2': billing_address.get('address2', ''),
                'city': billing_address.get('city', ''),
                'zip': billing_address.get('zip', ''),
            })
            
            # Find country
            country_code = billing_address.get('country_code')
            if country_code:
                country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
                if country:
                    partner_vals['country_id'] = country.id
                    
                    # Find state
                    province_code = billing_address.get('province_code')
                    if province_code:
                        state = self.env['res.country.state'].search([
                            ('code', '=', province_code),
                            ('country_id', '=', country.id)
                        ], limit=1)
                        if state:
                            partner_vals['state_id'] = state.id
                            
        return self.env['res.partner'].create(partner_vals)

    def _create_shipping_address(self, partner, shipping_address):
        """Create shipping address if different from billing"""
        if not shipping_address:
            return None
            
        # Check if shipping address is the same as billing
        if (partner.street == shipping_address.get('address1', '') and
            partner.city == shipping_address.get('city', '') and
            partner.zip == shipping_address.get('zip', '')):
            return None
            
        shipping_vals = {
            'name': shipping_address.get('name', partner.name),
            'parent_id': partner.id,
            'type': 'delivery',
            'street': shipping_address.get('address1', ''),
            'street2': shipping_address.get('address2', ''),
            'city': shipping_address.get('city', ''),
            'zip': shipping_address.get('zip', ''),
            'phone': shipping_address.get('phone', ''),
        }
        
        # Find country and state
        country_code = shipping_address.get('country_code')
        if country_code:
            country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
            if country:
                shipping_vals['country_id'] = country.id
                
                province_code = shipping_address.get('province_code')
                if province_code:
                    state = self.env['res.country.state'].search([
                        ('code', '=', province_code),
                        ('country_id', '=', country.id)
                    ], limit=1)
                    if state:
                        shipping_vals['state_id'] = state.id
                        
        return self.env['res.partner'].create(shipping_vals)

    def _create_order_line(self, sale_order, line_item):
        """Create sale order line from Shopify line item"""
        product = self._find_product_for_line_item(line_item)
        
        line_vals = {
            'order_id': sale_order.id,
            'product_id': product.id,
            'name': line_item.get('name', 'Shopify Product'),
            'product_uom_qty': float(line_item.get('quantity', 1)),
            'price_unit': float(line_item.get('price', 0)),
            'shopify_line_item_id': str(line_item.get('id', '')),
        }
        
        return self.env['sale.order.line'].create(line_vals)

    def _create_shipping_line(self, sale_order, shipping_line):
        """Create shipping line as order line"""
        # Find or create shipping product
        shipping_product = self.env['product.product'].search([
            ('default_code', '=', 'SHIPPING'),
            ('type', '=', 'service')
        ], limit=1)
        
        if not shipping_product:
            shipping_product = self.env['product.product'].create({
                'name': 'Shipping',
                'default_code': 'SHIPPING',
                'type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
            })
            
        line_vals = {
            'order_id': sale_order.id,
            'product_id': shipping_product.id,
            'name': shipping_line.get('title', 'Shipping'),
            'product_uom_qty': 1,
            'price_unit': float(shipping_line.get('price', 0)),
        }
        
        return self.env['sale.order.line'].create(line_vals)

    def _find_product_for_line_item(self, line_item):
        """Find or create product for line item"""
        # Try to find by SKU first
        sku = line_item.get('sku')
        if sku:
            product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
            if product:
                return product
                
        # Try to find by product title
        product_title = line_item.get('name', '')
        if product_title:
            product = self.env['product.product'].search([
                ('name', 'ilike', product_title)
            ], limit=1)
            if product:
                return product
                
        # Use default product if configured
        if self.default_product_id:
            return self.default_product_id
            
        # Create a new product
        product_vals = {
            'name': line_item.get('name', 'Shopify Product'),
            'default_code': line_item.get('sku', ''),
            'type': 'product',
            'sale_ok': True,
            'purchase_ok': False,
            'list_price': float(line_item.get('price', 0)),
        }
        
        return self.env['product.product'].create(product_vals)

    def _update_order_status(self, sale_order, order_data):
        """Update existing order status"""
        financial_status = order_data.get('financial_status', 'pending')
        fulfillment_status = order_data.get('fulfillment_status', 'unfulfilled')
        
        updates = {}
        if sale_order.shopify_financial_status != financial_status:
            updates['shopify_financial_status'] = financial_status
            
        if sale_order.shopify_fulfillment_status != fulfillment_status:
            updates['shopify_fulfillment_status'] = fulfillment_status
            
        if updates:
            sale_order.write(updates)
            
        # Auto-confirm if became paid
        if (financial_status == 'paid' and 
            sale_order.state == 'draft' and 
            self.auto_confirm_paid_orders):
            try:
                sale_order.action_confirm()
            except Exception as e:
                _logger.warning(f"Could not auto-confirm order {sale_order.name}: {e}")

    def verify_webhook(self, data, hmac_header):
        """Verify Shopify webhook signature"""
        if not self.webhook_secret:
            return True  # Skip verification if no secret configured
            
        calculated_hmac = base64.b64encode(
            hmac.new(
                self.webhook_secret.encode('utf-8'),
                data,
                hashlib.sha256
            ).digest()
        ).decode()
        
        return hmac.compare_digest(calculated_hmac, hmac_header)

    @api.model
    def cron_import_orders(self):
        """Cron job to import orders automatically"""
        active_connectors = self.search([
            ('is_active', '=', True),
            ('auto_import_orders', '=', True)
        ])
        
        for connector in active_connectors:
            try:
                connector._import_orders()
                _logger.info(f"Successfully imported orders for connector {connector.name}")
            except Exception as e:
                _logger.error(f"Error importing orders for connector {connector.name}: {e}")
                connector.write({
                    'last_sync_status': 'error',
                    'last_sync_message': str(e)
                })

    def action_view_orders(self):
        """View orders imported by this connector"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Orders from {self.name}',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('is_shopify_order', '=', True)],
            'context': {'search_default_is_shopify_order': 1},
        }

    def get_webhook_url(self):
        """Get the webhook URL for this Odoo instance"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/bitzify/shopify/webhook"

    @api.model
    def get_api_version_options(self):
        """Get available Shopify API versions"""
        return [
            ('2023-10', '2023-10 (Recommended)'),
            ('2023-07', '2023-07'),
            ('2023-04', '2023-04'),
            ('2023-01', '2023-01'),
            ('2022-10', '2022-10'),
        ]
