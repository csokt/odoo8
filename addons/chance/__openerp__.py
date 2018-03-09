{
  'name': 'Chance App',
  'description':  'Chance raktárkészlet nyilvántartás',
  'author': 'Csók Tibor',
  'depends':  ['szefo_admin'],
  'application':  True,
  'data': [
    'security/chance_access_rules.xml',
    'security/ir.model.access.csv',
    'chance_view.xml',
#    'report/chance_pivot_view.xml',
    'report/chance_report.xml',
#    'data/cron.xml',
  ],
}
