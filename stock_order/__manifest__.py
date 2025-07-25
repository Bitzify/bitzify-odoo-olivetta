{
    'name': 'Create Stock Order',
    'version': '1.0',
    'category': 'Stock',
    'summary': 'Integration with BDynamic Logistics Warehouse API',
    'description': """
        This module integrates Odoo stock.quant with BDynamic Logistics Warehouse API.
        When a stock quant is created, it automatically sends the data to BDynamic API.
    """,
    'author': 'Bitzify',
    'depends': ['stock', 'base'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'external_dependencies': {
        'python': ['requests'],
    },
}