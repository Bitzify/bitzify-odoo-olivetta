{
    'name': 'Bitzify Shopify Order Connector',
    'version': '17.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Import order data from Shopify to Odoo 17',
    'description': """
Bitzify Shopify Order Connector
===============================

This module provides a simplified Shopify integration focused specifically on order data import.

Key features:
* Import orders from Shopify via webhook and API
* Automatic customer creation
* Order status synchronization
* Real-time webhook processing
* Scheduled order synchronization
    """,
    'author': 'Bitzify',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/shopify_connector_views.xml',
        'views/sale_order_views.xml',
        'views/menu_views.xml',
        'data/cron_jobs.xml',
        'data/demo_data.xml',
        'wizard/shopify_config_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bitzify_shopify_odoo_connector/static/src/css/shopify_style.css',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
