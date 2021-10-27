{
    'name': "Ooops Stock Quantity Difference ",
    'summary':
        """Create report for stock quantity difference between
        Qty Available and Stock Move. Allow to fix it if found.""",
    'author': "Ooops",
    'contributors': ['Giovanni Serra - GSLab.it'],
    'license': 'LGPL-3',
    'website': "https://www.ooops404.com",
    'category': 'Stock',
    'version': '12.0.2.1.0',
    'depends': [
        'stock',
        'queue_job',
        'web_notify',
        'web_list_view_general_button',
        'web_refresher',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/report_stock_difference_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False
}
