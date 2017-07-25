{
  'name': 'Leltár App',
  'description':  'Eszközök leltározása és mozgatása',
  'author': 'Csók Tibor',
  'depends':  ['szefo_admin', 'hr'],
  'application':  True,
  'data': [
    'security/leltar_access_rules.xml',
    'security/ir.model.access.csv',
    'leltar_view.xml',
    'leltar_report.xml',
#    'data/leltar.csoport.csv',
#    'data/leltar.korzet.csv',
#    'data/leltar.ds_felelos.csv',
  ],
}
