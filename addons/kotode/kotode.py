# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api, exceptions

############################################################################################################################  Mecmor  ###
class Mecmor(models.Model):
  _name               = 'kotode.mecmor'
  _order              = 'datum'
  cimke               = fields.Selection([('szedes',u'Szedés'),('allas',u'Szedés állás'),('hiba',u'Hiba')], u'Címke')
  datum               = fields.Datetime(u'Dátum')
  gep                 = fields.Char(u'Gép')
  kod                 = fields.Char(u'Kód')
  adat1               = fields.Char(u'Adat1')
  adat2               = fields.Char(u'Adat2')
  adat3               = fields.Char(u'Adat3')
  muszak              = fields.Char(u'Műszak')
  eltelt_ido          = fields.Integer(u'Eltelt idő mp')
  eltelt_ido_perc     = fields.Float(u'Eltelt idő perc')
  azonosito           = fields.Char(u'Azonosító', index=True)

############################################################################################################################  Kötőgép  ###
class Kotogep(models.Model):
  _name               = 'kotode.kotogep'
  _rec_name           = 'azonosito'
  _order              = 'azonosito'
  _sql_constraints    = [('azonosito_unique', 'unique(azonosito)', 'Ez az azonosító már létezik!')]
  azonosito           = fields.Char(u'Azonosító', required=True)
  tipus               = fields.Selection([('regi',u'Régi'),('uj',u'Új')], u'Típus', required=True)
  finomsag            = fields.Char(u'Finomság', required=True)
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem', required=True)
  sor                 = fields.Char(u'Sor', required=True)
  active              = fields.Boolean(u'Aktív?', default=True)

############################################################################################################################  Dolgozó  ###
class Dolgozo(models.Model):
  _name               = 'kotode.dolgozo'
  _order              = 'name'
  name                = fields.Char(u'Név')
  erv_kezd            = fields.Datetime(u'Érvényesség kezdete', required=True)
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem', required=True)
  muszak              = fields.Selection([('1',u'Műszak1'),('2',u'Műszak2'),('3',u'Műszak3')], u'Műszak', required=True)
  kotogep_ids         = fields.Many2many('kotode.kotogep', string=u'Kötőgépek', domain=[('uzem', '=', 'uzem')])

############################################################################################################################  Beosztás  ###
class Beosztas(models.Model):
  _name               = 'kotode.beosztas'
  _order              = 'id'
  dolgozo_id          = fields.Many2one('kotode.dolgozo',  u'Dolgozó', auto_join=True)

############################################################################################################################  Kötőgép log  ###
class KotogepLog(models.Model):
  _name               = 'kotode.kotogep_log'
  _order              = 'id'
  jelzes              = fields.Selection([('termel',u'Termel'),('all',u'Áll'),('hiba',u'Hibával áll'),('online',u'Elérhető'),('offline',u'Nem elérhető')], u'Jelzés', index=True)
  datum               = fields.Datetime(u'Dátum', index=True)
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem')
  gep                 = fields.Char(u'Gép', index=True)
  muszak              = fields.Char(u'Műszak')
  idotartam           = fields.Integer(u'Időtartam mp')
  idotartam_perc      = fields.Float(u'Időtartam perc')
