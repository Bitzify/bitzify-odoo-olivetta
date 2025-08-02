from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class BitzifyShopifyController(http.Controller):

    @http.route('/bitzify/shopify/webhook', type='json', auth='public', csrf=False, methods=['POST'])
    def shopify_webhook(self, **kwargs):
        """Endpoint to receive Shopify webhooks"""
        try:
            _logger.info('Bitzify Shopify webhook received')
            
            # Get webhook headers
            headers = request.httprequest.headers
            hmac_header = headers.get('X-Shopify-Hmac-Sha256')
            topic = headers.get('X-Shopify-Topic')
            shop_domain = headers.get('X-Shopify-Shop-Domain')
            
            if not hmac_header:
                _logger.warning('Missing HMAC header in webhook')
                return {'error': 'Missing HMAC header'}
                
            if not topic:
                _logger.warning('Missing topic header in webhook')
                return {'error': 'Missing topic header'}
                
            # Find the connector for this shop
            connector = request.env['bitzify.shopify.connector'].sudo().search([
                ('shopify_store_url', '=', shop_domain),
                ('is_active', '=', True)
            ], limit=1)
            
            if not connector:
                _logger.error(f'No active connector found for shop {shop_domain}')
                return {'error': 'Connector not found'}
                
            # Get webhook data
            webhook_data = request.jsonrequest
            
            # Verify webhook signature if secret is configured
            if connector.webhook_secret:
                raw_data = request.httprequest.get_data()
                if not connector.verify_webhook(raw_data, hmac_header):
                    _logger.error('Webhook signature verification failed')
                    return {'error': 'Invalid signature'}
                    
            # Process webhook based on topic
            if topic in ['orders/create', 'orders/updated', 'orders/paid']:
                return self._process_order_webhook(connector, webhook_data, topic)
            elif topic == 'orders/cancelled':
                return self._process_order_cancellation(connector, webhook_data)
            else:
                _logger.info(f'Ignoring webhook topic: {topic}')
                return {'status': 'ignored', 'topic': topic}
                
        except Exception as e:
            _logger.error(f'Error processing Shopify webhook: {e}', exc_info=True)
            return {'error': 'Internal server error'}

    def _process_order_webhook(self, connector, order_data, topic):
        """Process order-related webhooks"""
        try:
            order = connector.sudo()._process_shopify_order(order_data)
            
            return {
                'status': 'success',
                'topic': topic,
                'order_id': order.id,
                'order_name': order.name
            }
            
        except Exception as e:
            _logger.error(f'Error processing order webhook: {e}', exc_info=True)
            return {'error': f'Error processing order: {str(e)}'}

    def _process_order_cancellation(self, connector, order_data):
        """Process order cancellation webhook"""
        try:
            shopify_order_id = str(order_data.get('id'))
            
            # Find existing order
            order = request.env['sale.order'].sudo().search([
                ('shopify_order_id', '=', shopify_order_id)
            ], limit=1)
            
            if order:
                # Cancel the order if it's not already done
                if order.state not in ['done', 'cancel']:
                    order.action_cancel()
                    
                # Update Shopify status  
                order.write({
                    'shopify_financial_status': 'voided',
                    'shopify_fulfillment_status': 'restocked'
                })
                
                return {
                    'status': 'success',
                    'topic': 'orders/cancelled',
                    'order_id': order.id,
                    'message': 'Order cancelled successfully'
                }
            else:
                return {
                    'status': 'not_found',
                    'topic': 'orders/cancelled',
                    'message': 'Order not found in Odoo'
                }
                
        except Exception as e:
            _logger.error(f'Error processing order cancellation: {e}', exc_info=True)
            return {'error': f'Error cancelling order: {str(e)}'}

    @http.route('/bitzify/shopify/test', type='http', auth='public', csrf=False)
    def test_endpoint(self):
        """Simple test endpoint to verify the controller is working"""
        return "Bitzify Shopify Connector is active!"

    @http.route('/bitzify/shopify/webhook/info', type='json', auth='user', csrf=False)
    def webhook_info(self):
        """Provide webhook configuration information"""
        base_url = request.httprequest.url_root.rstrip('/')
        webhook_url = f"{base_url}/bitzify/shopify/webhook"
        
        return {
            'webhook_url': webhook_url,
            'supported_events': [
                'orders/create',
                'orders/updated', 
                'orders/paid',
                'orders/cancelled'
            ],
            'format': 'JSON',
            'api_version': '2023-10'
        }
