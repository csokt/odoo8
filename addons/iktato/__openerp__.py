{
  'name': 'Iktató App',
  'description':  'Levelek iktatása',
  'author': 'Csók Tibor',
  'depends':  ['mail'],
  'application':  True,
  'data': [
    'security/iktato_access_rules.xml',
    'security/ir.model.access.csv',
    'iktato_view.xml',
    'iktato_report.xml',
  ],
}
