# -*- coding: utf-8 -*-

from openerp import  models, fields, api, exceptions
import time, datetime, json
import paho.mqtt.publish as publish

def pub(env, message):
  if type(message) is dict:
    message['database'] = env.cr.dbname
    message['utc']      = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    message['user']     = env.user.name
    if 'name' in message:
      message['event']  = message.pop('name')
    # topic: /log/program/database
  elif type(message) is int:
    message = {'state': message, 'timestamp': time.time()}
  elif type(message) is str:
    message = {'message': message, 'timestamp': time.time()}
  else:
    return
  topic   = "log/vir/"+env.cr.dbname
  try:
    payload = json.dumps(message).encode('utf-8')
  except Exception, e:
#    payload = json.dumps(u'json.dumps exception').encode('utf-8')
    payload = json.dumps(str(type(message))).encode('utf-8')
  publish.single(topic, payload, hostname='mqtt.szefo.local')

def log(env, message):
  if 'loglevel' not in message: message['loglevel'] = 'info'
  message['module'] = 'chance'
  env['szefo.log'].create(message)
#  pub(env, message)

############################################################################################################################  Paraméter  ###
class ChanceParameter(models.Model):
  _name  = 'chance.parameter'


