# -*- coding: utf-8 -*-

from  openerp import  models, fields, api, exceptions

def trim(list):
  ret = []
  for elem in list:
    if type(elem)==unicode or type(elem)==str: ret.append(elem.strip())
    else: ret.append(elem)
  return ret

class SzefoParameter(models.Model):
  _name  = 'szefo.parameter'
#  akt_ev   = fields.Integer(u'Aktuális év')

  @api.one
  def import_nexon(self):
    import pymssql
    mssql_conn = pymssql.connect(server='192.168.0.2\\PROLIANTML350', user='informix', password='informix', database='Nexon')

    Szemely = self.env['nexon.szemely']
    Log = self.env['szefo.log']

    ut_SzemelyId = Szemely.search([], limit=1, order='SzemelyId desc').SzemelyId
    if not ut_SzemelyId: ut_SzemelyId = 0
    cursor = mssql_conn.cursor()
    cursor.execute('SELECT Szemely.SzemelyId, AktEloNev, AktCsaladNev, AktUtoNev, AktNevAzon, SzulIdo FROM Nexon.dbo.Szemely JOIN Nexon.dbo.DolgJogv ON Szemely.SzemelyId = DolgJogv.SzemelyId WHERE Szemely.SzemelyId > %s AND JogvIg IS NULL ORDER BY Szemely.SzemelyId' % ut_SzemelyId)
    row = cursor.fetchone()
    while row:
      SzemelyId, AktEloNev, AktCsaladNev, AktUtoNev, AktNevAzon, SzulIdo = trim(row)
      Szemely.create({'SzemelyId': SzemelyId, 'AktEloNev': AktEloNev, 'AktCsaladNev': AktCsaladNev, 'AktUtoNev': AktUtoNev, 'AktNevAzon': AktNevAzon, 'SzulIdo': SzulIdo})
      row = cursor.fetchone()

    Log.create({'loglevel': 'info', 'name': 'Nexon személy import', 'module': 'szefo_admin'})
    return True

class SzefoLog(models.Model):
  _name   = 'szefo.log'
  _order  = 'id desc'
  loglevel= fields.Char(u'Log level')
  name    = fields.Char(u'Event')
  value   = fields.Char(u'Value')
  module  = fields.Char(u'Module')
  table   = fields.Char(u'Table')
  rowid   = fields.Integer(u'Row Id')

class SzefoTelephely(models.Model):
  _name   = 'szefo.telephely'
  name    = fields.Char(u'Telephely', compute='_compute_name', store=True)
  kod     = fields.Char(u'Kód',  required=True)
  helyseg = fields.Char(u'Helység',  required=True)
  cim     = fields.Char(u'Cím',  required=True)
  irszam  = fields.Char(u'Irányítószám',  required=True)
  ge_kod  = fields.Char(u'ge kód',  required=False)
  active  = fields.Boolean(u'Aktív?', default=True)

  @api.one
  @api.depends('helyseg', 'cim')
  def _compute_name(self):
    self.name = self.helyseg+', '+self.cim

class NexonSzemely(models.Model):
  _name         = 'nexon.szemely'
  name          = fields.Char(u'Teljes név', compute='_compute_name', store=True)
  SzemelyId     = fields.Integer(u'SzemelyId',  required=True, index=True)
  AktEloNev     = fields.Char(u'AktEloNev')
  AktCsaladNev  = fields.Char(u'AktCsaladNev')
  AktUtoNev     = fields.Char(u'AktUtoNev')
  AktNevAzon    = fields.Char(u'AktNevAzon')
  SzulIdo       = fields.Date('Születési dátum')
  employee_id   = fields.Many2one('hr.employee',  u'VIR alkalmazott')
  active        = fields.Boolean(u'Aktív?', default=True)

  @api.one
  @api.depends('AktEloNev', 'AktCsaladNev', 'AktUtoNev', 'AktNevAzon')
  def _compute_name(self):
    AktEloNev, AktNevAzon = '', ''
    if self.AktEloNev:  AktEloNev  = self.AktEloNev + ' '
    if self.AktNevAzon: AktNevAzon =  ' ' + self.AktNevAzon
    self.name = AktEloNev+self.AktCsaladNev+' '+self.AktUtoNev+AktNevAzon

  @api.one
  def copy_szemely(self):
    if self.employee_id: raise exceptions.Warning('Az alkalmazott már át van véve!')
    Employee = self.env['hr.employee']
    self.employee_id = Employee.create({'name': self.name, 'otherid': self.SzemelyId, 'birthday': self.SzulIdo}).id
    return True

class res_users(models.Model):
  _inherit  = 'res.users'
  security_clearance  = fields.Integer(u'Biztonsági engedély', default=0)
  sajat_raktar_id     = fields.Many2one('raktar.mozgasnem', u'Saját raktár')




############################################################################################################################  Jogosultság  ###
"""
delete from szefo_jogosultsagnev ;
insert into szefo_jogosultsagnev(name,active,create_uid,create_date,write_uid,write_date) select distinct jogosultsag_neve,true,6,now(),6,now() from szefo_jogosultsag order by jogosultsag_neve ;

update szefo_jogosultsag as jog set jogosultsagnev_id = nev.id from szefo_jogosultsagnev as nev where jog.jogosultsag_neve = nev.name ;
update szefo_jogosultsag_log as jog set jogosultsagnev_id = nev.id from szefo_jogosultsagnev as nev where jog.jogosultsag_neve = nev.name ;
"""

class SzefoJogosultsagNev(models.Model):
  _name               = 'szefo.jogosultsagnev'
  name                = fields.Char(u'Jogosultság neve', required=True)
  active              = fields.Boolean(u'Aktív?', default=True)

class SzefoJogosultsagTemplate(models.AbstractModel):
  _name               = 'szefo.jogosultsag_template'
  _order              = 'id desc'
  felhasznalo_id      = fields.Many2one('hr.employee', u'Felhasználó', required=True)
  jogosultsag_csoport = fields.Selection([('fileserver', u'Fájlszerver'), ('email', u'E-mail'), ('nexon', u'Nexon'), ('matrix', u'Mátrix'), ('termeles', u'Termelési program'),
                        ('pendrive', u'Pendrive'), ('bank', u'Banki terminál'), ('internet', u'Internet használat') ], u'Jogosultság csoport', required=True)
#  jogosultsag_neve    = fields.Char(u'Jogosultság neve', required=False)
  jogosultsagnev_id   = fields.Many2one('szefo.jogosultsagnev', u'Jogosultság neve', required=True)
  allapot             = fields.Selection([('enged',u'Aktív jogosultság'),('tilt',u'Törölt jogosultság')], 'Állapot', default='enged', required=True)
  engedelyezo_id      = fields.Many2one('hr.employee', u'Engedélyező', required=True)

class SzefoJogosultsag(models.Model):
  _name               = 'szefo.jogosultsag'
  _inherit            = 'szefo.jogosultsag_template'
  jogosultsag_log_ids = fields.One2many('szefo.jogosultsag_log', 'jogosultsag_id', u'Jogosultság történet', readonly=True)

  @api.multi
  def write(self, vals):
#    if 'kuldott_db' in vals and 'kapott_db' in vals:
#      raise exceptions.Warning(u'Küldés és fogadás egyszerre nem lehetséges!')
    old = self.read()[0]
    del old['id']
    old['jogosultsag_id']     = self.id
    old['felhasznalo_id']     = self.felhasznalo_id.id
    old['jogosultsagnev_id']  = self.jogosultsagnev_id.id
    old['engedelyezo_id']     = self.engedelyezo_id.id
    old['rogzito_uid']        = self.write_uid.id
    old['rogzitesi_ido']      = self.write_date
    self.env['szefo.jogosultsag_log'].create(old)
    super(SzefoJogosultsag, self).write(vals)
    return True

class SzefoJogosultsagLog(models.Model):
  _name               = 'szefo.jogosultsag_log'
  _inherit            = 'szefo.jogosultsag_template'
  jogosultsag_id      = fields.Many2one('szefo.jogosultsag',   u'Jogosultság', required=True)
  rogzito_uid         = fields.Many2one('res.users', u'Rögzítette')
  rogzitesi_ido       = fields.Datetime(u'Rögzítés ideje')

class SzefoJogosultsagMasol(models.Model):
  _name               = 'szefo.jogosultsag_masol'
  _inherit            = 'szefo.jogosultsag_template'

  @api.one
  def jogosultsag_masol_update(self):
    ids = self.env['szefo.jogosultsag_masol'].search([])
    ids.write({'felhasznalo_id': self.felhasznalo_id.id, 'engedelyezo_id': self.engedelyezo_id.id})
    return True

  @api.one
  def jogosultsag_import(self):
    for jog in self.env['szefo.jogosultsag_masol'].search([]):
      sor_row = {
        'felhasznalo_id'      : jog.felhasznalo_id.id,
        'jogosultsag_csoport' : jog.jogosultsag_csoport,
        'jogosultsagnev_id'   : jog.jogosultsagnev_id.id,
        'allapot'             : jog.allapot,
        'engedelyezo_id'      : jog.engedelyezo_id.id,
      }
      self.env['szefo.jogosultsag'].create(sor_row)
    return True
