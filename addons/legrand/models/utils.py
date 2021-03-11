# -*- coding: utf-8 -*-

from openerp import  models, fields, api, exceptions
import hashlib

def log(env, message):
  if 'loglevel' not in message: message['loglevel'] = 'info'
  message['module'] = 'raktar'
  env['szefo.log'].create(message)
#  pub(env, message)

def trim(list):
  ret = []
  for elem in list:
    if type(elem)==unicode or type(elem)==str: ret.append(elem.strip())
    else: ret.append(elem)
  return ret

def calc_cikkek_uid(recordset, field):
  cikkdict = {}
  for record in recordset:
    cikkdict[record[field].upper()] = 1
  cikkek = ' '.join(sorted(cikkdict.keys()))
  return hashlib.md5(cikkek.encode()).hexdigest()
