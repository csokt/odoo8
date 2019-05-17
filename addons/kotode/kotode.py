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
  _order              = 'azonosito'
  _sql_constraints    = [('azonosito_unique', 'unique(azonosito)', 'Ez az azonosító már létezik!')]
  name                = fields.Char(u'Név', required=True)
  azonosito           = fields.Char(u'Azonosító', required=True)
  tipus               = fields.Selection([('regi',u'Régi'),('uj',u'Új')], u'Típus', required=True)
  finomsag            = fields.Char(u'Finomság', required=True)
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem', required=True)
  sor                 = fields.Char(u'Sor', required=True)
  min_log_id          = fields.Integer(u'Min log id', default=0)
  max_log_id          = fields.Integer(u'Max log id', default=80)
  megjegyzes_id       = fields.Many2one('kotode.megjegyzes',  u'Megjegyzés')
  active              = fields.Boolean(u'Aktív?', default=True)
  # virtual fields
  kotogep_log_ids     = fields.One2many('kotode.kotogep_log_view', 'kotogep_id', u'Logok')

  @api.one
  def ma(self):
    # import datetime
    # dt = datetime.datetime
    kezd = fields.Date.datetime.datetime.combine(fields.Date.context_today(), fields.Date.datetime.time(0,0,0))
    # kezd = fields.Date.context_today(self)
    raise exceptions.Warning(type(kezd))
    log_id = self.env['kotode.kotogep_log'].search([('datum','>',kezd)], limit=1, order='datum, id').id
    raise exceptions.Warning(log_id)
    return True

  @api.one
  def vissza1(self):
    return True

  @api.one
  def vissza7(self):
    return True

  @api.one
  def masol(self):
    log_view_ids = self.kotogep_log_ids.mapped('id')
    log_ids = self.env['kotode.kotogep_log'].search([('id','in',log_view_ids)])
    log_ids.write({'megjegyzes_id': self.megjegyzes_id.id})
    if len(self.kotogep_log_ids) > 10:
      raise exceptions.Warning(u'Maximum tíz sor módosítható egyidejűleg!')
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
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem', readonly=True)
  kotogep_id          = fields.Many2one('kotode.kotogep',  u'Kötőgép')
  gepazonosito        = fields.Char(u'Gép azonosító', readonly=True)
  gep                 = fields.Char(u'Gép', readonly=True)
  muszak              = fields.Selection([('1',u'Műszak1'),('2',u'Műszak2'),('3/1',u'Műszak3/1'),('3/2',u'Műszak3/2')], u'Műszak', readonly=True)
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
  jelzes              = fields.Selection([('termel',u'Termel'),('all',u'Áll'),('hiba',u'Hibával áll'),('ki',u'Kikapcsolva')], u'Jelzés', readonly=True)
  datum               = fields.Datetime(u'Dátum', readonly=True, index=True)
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem', readonly=True)
  kotogep_id          = fields.Many2one('kotode.kotogep',  u'Kötőgép')
  gepazonosito        = fields.Char(u'Gép azonosító', readonly=True)
  gep                 = fields.Char(u'Gép', readonly=True)
  muszak              = fields.Selection([('1',u'Műszak1'),('2',u'Műszak2'),('3/1',u'Műszak3/1'),('3/2',u'Műszak3/2')], u'Műszak', readonly=True)
  idotartam           = fields.Integer(u'Időtartam mp', readonly=True)
  idotartam_perc      = fields.Float(u'Időtartam perc', readonly=True)
  idotartam_ora       = fields.Float(u'Időtartam óra', readonly=True)
  mqtt_log_id         = fields.Integer(u'MQTT log ID', readonly=True, index=True)
  megjegyzes_id       = fields.Many2one('kotode.megjegyzes',  u'Megjegyzés')

  def init(self, cr):
    tools.drop_view_if_exists(cr, self._table)
    cr.execute(
      """CREATE or REPLACE VIEW %s as (
        SELECT log.*
        FROM kotode_kotogep_log AS log
        JOIN kotode_kotogep AS gep ON gep.id = log.kotogep_id AND gep.min_log_id <= log.id AND gep.max_log_id >= log.id
        WHERE active
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
  jelzes              = fields.Selection([('online',u'Elérhető'),('offline',u'Nem elérhető')], u'Jelzés')
  datum               = fields.Datetime(u'Dátum')
  uzem                = fields.Selection([('kor',u'Körkötő'),('sik',u'Síkkötő')], u'Üzem')
  kotogep_id          = fields.Many2one('kotode.kotogep',  u'Kötőgép')
  gepazonosito        = fields.Char(u'Gép azonosító')
  gep                 = fields.Char(u'Gép')
  muszak              = fields.Selection([('1',u'Műszak1'),('2',u'Műszak2'),('3/1',u'Műszak3/1'),('3/2',u'Műszak3/2')], u'Műszak')
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
