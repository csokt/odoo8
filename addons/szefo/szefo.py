# -*- coding: utf-8 -*-

from  openerp import  models, fields, api, exceptions

############################################################################################################################  Anyagigénylés  ###
class SzefoAnyagigeny(models.Model):
  _name               = 'szefo.anyagigeny'
  _order              = 'id desc'
  state               = fields.Selection([('uj',u'Új igény'),('elutasit',u'Elutasítva'),('jovahagy',u'Jóváhagyva'),('beszerzes',u'Beszerzés alatt'),('kesz',u'Teljesült')], 'Állapot',
                        default='uj',
                        readonly=True
                        )
  anyagigeny          = fields.Char(u'Anyagigény',          required=True, readonly=True, states={'uj': [('readonly', False)]})
  mennyiseg           = fields.Char(u'Mennyiség',           required=True, readonly=True, states={'uj': [('readonly', False)]})
  felhasznalas_helye  = fields.Char(u'Felhasználás helye',  required=True, readonly=True, states={'uj': [('readonly', False)]})
  indoklas            = fields.Char(u'Indoklás',            required=True, readonly=True, states={'uj': [('readonly', False)]})
  megjegyzes          = fields.Char(u'Megjegyzés',          states={'elutasit': [('readonly', True)], 'kesz': [('readonly', True)]})
  kuldott             = fields.Integer(u'Küldött',          readonly=True, states={'beszerzes': [('readonly', False)]})
  raktarrol           = fields.Boolean(u'Raktárról?',       readonly=True, states={'beszerzes': [('readonly', False)]})
  dontes_uid          = fields.Many2one('res.users', u'Döntött',  readonly=True)
  dontes_ideje        = fields.Datetime(u'Döntés ideje',          readonly=True)
  beszerzes_uid       = fields.Many2one('res.users', u'Beszerzést indította', readonly=True)
  beszerzes_ideje     = fields.Datetime(u'Beszerzés indítás ideje',           readonly=True)
  # virtual fields

  @api.one
  def state2elutasit(self):
    self.write({'state': 'elutasit',  'dontes_uid': self.env.user.id,     'dontes_ideje': fields.datetime.now()})
    return True

  @api.one
  def state2jovahagy(self):
    self.write({'state': 'jovahagy',  'dontes_uid': self.env.user.id,     'dontes_ideje': fields.datetime.now()})
    return True

  @api.one
  def state2beszerzes(self):
    self.write({'state': 'beszerzes', 'beszerzes_uid': self.env.user.id,  'beszerzes_ideje': fields.datetime.now()})
    return True

  @api.one
  def state2kesz(self):
    self.state = 'kesz'
    return True

  @api.one
  def statevissza(self):
    igeny_row = False
    if self.state in ('elutasit', 'jovahagy'):
      igeny_row = {'state': 'uj',       'dontes_uid':    False,  'dontes_ideje':    False}
    elif self.state == 'beszerzes':
      igeny_row = {'state': 'jovahagy', 'beszerzes_uid': False,  'beszerzes_ideje': False}
    elif self.state == 'kesz':
      igeny_row = {'state': 'beszerzes'}
    if igeny_row: self.write(igeny_row)
    return True

############################################################################################################################  Adattárház fájlok  ###
class DatawhFiles(models.Model):
  _name               = 'datawh.files'
  _order              = 'id desc'
  _rec_name           = 'filename'
  domain              = fields.Char(u'Tárgykör',                  readonly=True)
  filetype            = fields.Char(u'Fájltípus',                 readonly=True)
  filename            = fields.Char(u'Fájlnév',                   readonly=True)
  path                = fields.Char(u'Elérés',                    readonly=True)
  size                = fields.Integer(u'Méret',                  readonly=True)
  mod_time            = fields.Integer(u'Módosítás időbélyeg',    readonly=True)
  documents_ids       = fields.One2many('datawh.documents', 'files_id', u'Dokumentumok', readonly=True)

class DatawhDocuments(models.Model):
  _name               = 'datawh.documents'
  _order              = 'id'
  _rec_name           = 'id'
  files_id            = fields.Many2one('datawh.files', u'Fájl',  readonly=True,    auto_join=True)
  doctype             = fields.Char(u'Dokumentum típusa',         readonly=True)
  label               = fields.Char(u'Címke',                     readonly=True)
  reject              = fields.Boolean(u'Elvet?')
  imported            = fields.Boolean(u'Importálva?',            readonly=True)
  document            = fields.Text(u'Dokumentum',                readonly=True)
  errors              = fields.Text(u'Hibajegyzék',               readonly=True)
  # virtual fields
  domain              = fields.Char(u'Tárgykör',                  readonly=True,    related='files_id.domain'   )
  filetype            = fields.Char(u'Fájltípus',                 readonly=True,    related='files_id.filetype' )
  path                = fields.Char(u'Elérés',                    readonly=True,    related='files_id.path'     )
  size                = fields.Integer(u'Méret',                  readonly=True,    related='files_id.size'     )
  mod_time            = fields.Integer(u'Módosítás időbélyeg',    readonly=True,    related='files_id.mod_time' )
