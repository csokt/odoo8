{
  'name': 'SZEFO Admin App',
  'description':  'SZEFO alapadatok és beállítások',
  'author': 'Csók Tibor',
  'depends':  ['base'],
  'application':  True,
  'data': [
    'security/szefo_access_rules.xml',
    'security/ir.model.access.csv',
    'szefo_view.xml',
#    'data/szefo.parameter.csv',
  ],
}
