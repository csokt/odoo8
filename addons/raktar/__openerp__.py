{
  'name': 'Raktár App',
  'description':  'Raktárkészlet és gyártás támogatás',
  'author': 'Csók Tibor',
  'depends':  ['mrp'],
  'application':  True,
  'data': [
    'security/raktar_access_rules.xml',
    'security/ir.model.access.csv',
    'raktar_view.xml',
    'raktar_xls_view.xml',
    'report/raktar_pivot_view.xml',
    'report/raktar_report.xml',
    'data/cron.xml',
  ],
}
