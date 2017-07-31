{
  'name': 'Legrand App',
  'description':  'Legrand raktárkészlet és gyártás támogatás',
  'author': 'Csók Tibor',
  'depends':  ['szefo_admin'],
  'application':  True,
  'data': [
    'security/legrand_access_rules.xml',
    'security/ir.model.access.csv',
    'legrand_view.xml',
    'data/legrand.hely.csv',
    'data/legrand.parameter.csv',
    'report/legrand_pivot_view.xml',
    'report/legrand_report.xml',
#    'data/cron.xml',
  ],
}