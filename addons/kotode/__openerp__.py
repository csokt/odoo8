{
  'name': 'Kötöde App',
  'description':  'Kötöde nyilvántartás',
  'author': 'Csók Tibor',
  'depends':  ['szefo_admin'],
  'application':  True,
  'data': [
    'security/kotode_access_rules.xml',
    'security/ir.model.access.csv',
    'kotode_view.xml',
#    'report/kotode_pivot_view.xml',
#    'report/kotode_report.xml',
#    'data/cron.xml',
  ],
}
