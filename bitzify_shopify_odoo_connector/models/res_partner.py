from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Shopify related fields
    shopify_customer_id = fields.Char('Shopify Customer ID', readonly=True)
    is_shopify_customer = fields.Boolean('Is Shopify Customer', readonly=True)
