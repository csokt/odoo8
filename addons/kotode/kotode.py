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

############################################################################################################################  Dolgozó  ###
class Megjegyzes(models.Model):
  _name               = 'kotode.megjegyzes'
  _order              = 'name'
  name                = fields.Char(u'Rövidítés')
  megjegyzes          = fields.Char(u'Megjegyzés')

############################################################################################################################  Kötőgép  ###
class Kotogep(models.Model):
  _name               = 'kotode.kotogep'
  _order              = 'name'
  _sql_constraints    = [('azonosito_unique', 'unique(azonosito)', 'Ez az azonosító már létezik!')]
  name                = fields.Char(u'Név', required=True)
  azonosito           = fields.Char(u'Azonosító', required=True)
  kotogepkod          = fields.Integer(u'Kötőgépkód')
  tipus               = fields.Selection([('regi',u'Régi'),('uj',u'Új')], u'Típus', required=True)
  finomsag            = fields.Char(u'Finomság', required=True)
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem', required=True)
  sor                 = fields.Char(u'Sor', required=True)
  min_log_id          = fields.Integer(u'Min log id', default=0)
  max_log_id          = fields.Integer(u'Max log id', default=80)
  megjegyzes_id       = fields.Many2one('kotode.megjegyzes',  u'Megjegyzés')
  allapot             = fields.Selection([('online',u'Elérhető'),('offline',u'Nem elérhető')], u'Állapot', readonly=True)
  jelzes              = fields.Selection([('termel',u'Termel'),('all',u'Áll'),('hiba',u'Hibával áll'),('ki',u'Kikapcsolva')], u'Jelzés', readonly=True)
  aktiv               = fields.Boolean(u'Aktív?', default=True)
  # virtual fields
  # allapot             = fields.Selection([('online',u'Elérhető'),('offline',u'Nem elérhető')], u'Állapot', compute='_compute_allapot')
  # jelzes              = fields.Selection([('termel',u'Termel'),('all',u'Áll'),('hiba',u'Hibával áll'),('ki',u'Kikapcsolva')], u'Jelzés', compute='_compute_jelzes')
  kotogep_log_ids     = fields.One2many('kotode.kotogep_log_view', 'kotogep_id', u'Logok')
  status_log_ids      = fields.One2many('kotode.status_log', 'kotogep_id', u'Státusz logok')

  @api.one
  def _compute_allapot(self):
    self.allapot = self.env['kotode.status_log'].search([('kotogep_id', '=', self.id)], order='id desc', limit=1).jelzes
    # self.allapot = self.status_log_ids[-1].jelzes if len(self.status_log_ids) else False

  @api.one
  def _compute_jelzes(self):
    self.jelzes = self.env['kotode.kotogep_log'].search([('kotogep_id', '=', self.id)], order='id desc', limit=1).jelzes

  # @api.one
  def vissza(self, napok):
    import pytz
    import datetime

    now = datetime.datetime.now(pytz.timezone('Europe/Budapest'))
    today_beginning = datetime.datetime(now.year, now.month, now.day)
    kezd = fields.Datetime.to_string(today_beginning - datetime.timedelta(days=napok) - now.tzinfo.utcoffset(now))
    min_log_id = self.env['kotode.kotogep_log'].search([('datum','>=',kezd), ('kotogep_id','=',self.id)], limit=1, order='id').id
    max_log_id = self.env['kotode.kotogep_log'].search([('kotogep_id','=',self.id)], limit=1, order='id desc').id
    self.min_log_id = min_log_id
    self.max_log_id = max_log_id
    # return True

  @api.one
  def vissza0(self):
    self.vissza(0)
    return True

  @api.one
  def vissza2(self):
    self.vissza(2)
    return True

  @api.one
  def vissza7(self):
    self.vissza(7)
    return True

  @api.one
  def vissza30(self):
    self.vissza(30)
    return True

  @api.one
  def masol(self):
    log_view_ids = self.kotogep_log_ids.mapped('id')
    log_ids = self.env['kotode.kotogep_log'].search([('id','in',log_view_ids)])
    log_ids.write({'megjegyzes_id': self.megjegyzes_id.id})
    if len(self.kotogep_log_ids) > 300:
      raise exceptions.Warning(u'Maximum háromszáz sor módosítható egyidejűleg!')
    return True

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
  jelzes              = fields.Selection([('termel',u'Termel'),('all',u'Áll'),('hiba',u'Hibával áll'),('ki',u'Kikapcsolva')], u'Jelzés', readonly=True)
  datum               = fields.Datetime(u'Dátum', readonly=True, index=True)
  muszak_datum        = fields.Datetime(u'Műszak dátum', readonly=True, index=True)
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem', readonly=True)
  kotogep_id          = fields.Many2one('kotode.kotogep',  u'Kötőgép', readonly=True)
  gepazonosito        = fields.Char(u'Gép azonosító', readonly=True)
  gep                 = fields.Char(u'Gép', readonly=True)
  muszak              = fields.Selection([('1',u'Műszak1'),('2',u'Műszak2'),('3',u'Műszak3')], u'Műszak', readonly=True)
  muszak3             = fields.Selection([('3/1',u'Műszak3/1'),('3/2',u'Műszak3/2')], u'Műszak3', readonly=True)
  idotartam           = fields.Integer(u'Időtartam mp', readonly=True)
  idotartam_perc      = fields.Float(u'Időtartam perc', readonly=True)
  idotartam_ora       = fields.Float(u'Időtartam óra', readonly=True)
  mqtt_log_id         = fields.Integer(u'MQTT log ID', readonly=True, index=True)
  megjegyzes_id       = fields.Many2one('kotode.megjegyzes',  u'Megjegyzés')

############################################################################################################################  Kötőgép log view  ###
class KotogepLogView(models.Model):
  _name = 'kotode.kotogep_log_view'
  _auto = False
  # _rec_name = 'id'
  _order = 'id'
  jelzes              = fields.Selection([('termel',u'Termel'),('all',u'Áll'),('hiba',u'Hibával áll'),('ki',u'Kikapcsolva')], u'Jelzés')
  datum               = fields.Datetime(u'Dátum')
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem')
  kotogep_id          = fields.Many2one('kotode.kotogep',  u'Kötőgép')
  gepazonosito        = fields.Char(u'Gép azonosító')
  gep                 = fields.Char(u'Gép')
  muszak              = fields.Selection([('1',u'Műszak1'),('2',u'Műszak2'),('3',u'Műszak3')], u'Műszak')
  muszak3             = fields.Selection([('3/1',u'Műszak3/1'),('3/2',u'Műszak3/2')], u'Műszak3')
  idotartam           = fields.Integer(u'Időtartam mp')
  idotartam_perc      = fields.Float(u'Időtartam perc')
  idotartam_ora       = fields.Float(u'Időtartam óra')
  mqtt_log_id         = fields.Integer(u'MQTT log ID')
  megjegyzes_id       = fields.Many2one('kotode.megjegyzes',  u'Megjegyzés')

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT log.*
        FROM kotode_kotogep_log AS log
        JOIN kotode_kotogep AS gep ON gep.id = log.kotogep_id AND gep.min_log_id <= log.id AND gep.max_log_id >= log.id
      )"""
      % (self._table)
    )

  @api.multi
  def elso(self):
    self.ensure_one()
    self.kotogep_id.min_log_id = self.id
    return {
      'view_type': 'form',
      'view_mode': 'form',
      'res_model': 'kotode.kotogep',
      'type': 'ir.actions.act_window',
      'res_id': self.kotogep_id.id
    }

  @api.multi
  def utolso(self):
    self.ensure_one()
    self.kotogep_id.max_log_id = self.id
    return {
      'view_type': 'form',
      'view_mode': 'form',
      'res_model': 'kotode.kotogep',
      'type': 'ir.actions.act_window',
      'res_id': self.kotogep_id.id
    }

############################################################################################################################  Státusz log  ###
class StatusLog(models.Model):
  _name               = 'kotode.status_log'
  _order              = 'id'
  jelzes              = fields.Selection([('online',u'Elérhető'),('offline',u'Nem elérhető')], u'Állapot')
  datum               = fields.Datetime(u'Dátum')
  muszak_datum        = fields.Datetime(u'Műszak dátum')
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem')
  kotogep_id          = fields.Many2one('kotode.kotogep',  u'Kötőgép')
  gepazonosito        = fields.Char(u'Gép azonosító')
  gep                 = fields.Char(u'Gép')
  muszak              = fields.Selection([('1',u'Műszak1'),('2',u'Műszak2'),('3',u'Műszak3')], u'Műszak')
  muszak3             = fields.Selection([('3/1',u'Műszak3/1'),('3/2',u'Műszak3/2')], u'Műszak3')
  idotartam           = fields.Integer(u'Időtartam mp')
  idotartam_perc      = fields.Float(u'Időtartam perc')
  idotartam_ora       = fields.Float(u'Időtartam óra')
  mqtt_log_id         = fields.Integer(u'MQTT log ID', index=True)

############################################################################################################################  MQTT log  ###
class MqttLog(models.Model):
  _name               = 'kotode.mqtt_log'
  _order              = 'id'
  topic               = fields.Char(u'Topic')
  payload             = fields.Char(u'Payload')

############################################################################################################################  Munkaszünet  ###
class Munkaszunet(models.TransientModel):
  _name               = 'kotode.munkaszunet'
  kezd                = fields.Datetime(u'Kezdő idő', required=True)
  zar                 = fields.Datetime(u'Záró idő', required=True)
  idotartam           = fields.Char(u'Időtartam', readonly=True)
  sorok               = fields.Integer(u'Módosított sorok száma', readonly=True)
  megjegyzes_id       = fields.Many2one('kotode.megjegyzes',  u'Megjegyzés')

  @api.onchange('kezd', 'zar')
  def onchange_kezd_zar(self):
    if self.kezd and self.zar:
      # self.idotartam = (fields.Datetime.from_string(self.zar) - fields.Datetime.from_string(self.kezd)).total_seconds()
      self.idotartam = fields.Datetime.from_string(self.zar) - fields.Datetime.from_string(self.kezd)
      records = self.env['kotode.kotogep_log'].search([('datum','>=',self.kezd), ('datum','<',self.zar)])
      self.sorok = len(records)

  @api.multi
  def munkaszunet_ir(self):
    self.ensure_one()
    if self.kezd >= self.zar: raise exceptions.Warning(u'A kezdő idő legyen a záró idő előtt!')
    records = self.env['kotode.kotogep_log'].search([('datum','>=',self.kezd), ('datum','<',self.zar)])
    # raise exceptions.Warning(len(records))
    records.write({'megjegyzes_id' : self.megjegyzes_id.id})
    return {
      'type':       'ir.actions.act_window',
      'res_model':  'kotode.kotogep_log',
      'view_mode':  'tree',
    }

