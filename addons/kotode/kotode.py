# -*- coding: utf-8 -*-

from openerp import tools, models, fields, api, exceptions

############################################################################################################################  Mecmor  ###
class Mecmor(models.Model):
  _name               = 'kotode.mecmor'
  datum               = fields.Datetime(u'Dátum')
  gep                 = fields.Char(u'Gép')
  kod                 = fields.Char(u'Kód')
  adat1               = fields.Char(u'Adat1')
  adat2               = fields.Char(u'Adat2')
  adat3               = fields.Char(u'Adat3')
  muszak              = fields.Char(u'Műszak')
  kodintervallum      = fields.Integer(u'Kód ismétlődés ideje')
  azonosito           = fields.Char(u'Azonosító', index=True)
