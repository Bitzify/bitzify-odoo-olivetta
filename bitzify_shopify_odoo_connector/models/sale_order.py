from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Shopify related fields
    shopify_order_id = fields.Char('Shopify Order ID', readonly=True)
    shopify_order_number = fields.Char('Shopify Order Number', readonly=True)
    is_shopify_order = fields.Boolean('Is Shopify Order', default=False, readonly=True)
    shopify_financial_status = fields.Selection([
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('partially_refunded', 'Partially Refunded'),
        ('refunded', 'Refunded'),
        ('voided', 'Voided')
    ], string='Shopify Financial Status', readonly=True)
    shopify_fulfillment_status = fields.Selection([
        ('fulfilled', 'Fulfilled'),
        ('null', 'Unfulfilled'),
        ('partial', 'Partially Fulfilled'),
        ('restocked', 'Restocked')
    ], string='Shopify Fulfillment Status', readonly=True)

    def _get_shopify_status_badge(self):
        """Get badge color for Shopify status"""
        status_colors = {
            'paid': 'success',
            'pending': 'warning',
            'refunded': 'danger',
            'voided': 'secondary',
            'fulfilled': 'success',
            'partial': 'warning',
            'null': 'secondary',
        }
        financial_color = status_colors.get(self.shopify_financial_status, 'secondary')
        fulfillment_color = status_colors.get(self.shopify_fulfillment_status, 'secondary')
        
        return {
            'financial_color': financial_color,
            'fulfillment_color': fulfillment_color
        }

    def action_view_in_shopify(self):
        """Open order in Shopify admin"""
        self.ensure_one()
        if not self.shopify_order_id:
            return
            
        # Find the connector for this order
        connector = self.env['bitzify.shopify.connector'].search([
            ('is_active', '=', True)
        ], limit=1)
        
        if connector:
            shopify_url = f"https://{connector.shopify_store_url}/admin/orders/{self.shopify_order_id}"
            return {
                'type': 'ir.actions.act_url',
                'url': shopify_url,
                'target': 'new',
            }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Shopify related fields
    shopify_line_item_id = fields.Char('Shopify Line Item ID', readonly=True)
