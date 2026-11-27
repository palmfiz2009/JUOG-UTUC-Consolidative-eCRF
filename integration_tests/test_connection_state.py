import unittest
from datetime import date
from isolated_connection_state import preserve, restore, BACKUP

class ConnectionState(unittest.TestCase):
 def test_widget_cleanup_during_outage_restores_same_actor_values(self):
  state={'_integration_actor':'actor-A','_integration_subject':'JUOG-901','_integration_page':'30日','peri_registration_id':'JUOG-901','peri_operation_date':date(2026,1,10),'password':'not-backed-up','_integration_versions':{'keep':2}}
  preserve(state)
  self.assertNotIn('password',state[BACKUP]['values'])
  self.assertNotIn('_integration_versions',state[BACKUP]['values'])
  for k in list(state[BACKUP]['values']):state.pop(k,None)
  preserve(state) # A second outage must not replace surviving backup with blanks.
  restore(state)
  self.assertEqual(state['_integration_subject'],'JUOG-901')
  self.assertEqual(state['peri_operation_date'],date(2026,1,10))
  self.assertEqual(state['_integration_versions'],{'keep':2})
  self.assertNotIn(BACKUP,state)
 def test_changed_or_halted_actor_never_restores(self):
  for change in ({'_integration_actor':'actor-B'},{'auth_connect_halted':True}):
   state={'_integration_actor':'actor-A','_integration_subject':'JUOG-901'};preserve(state)
   state.pop('_integration_subject');state.update(change);restore(state)
   self.assertNotIn('_integration_subject',state);self.assertNotIn(BACKUP,state)
 def test_no_actor_no_backup(self):
  state={'_integration_subject':'JUOG-901'};preserve(state);self.assertNotIn(BACKUP,state)

 def test_streamlit_widget_cleanup_and_reconnect(self):
  from streamlit.testing.v1 import AppTest
  source = """
import streamlit as st
from isolated_connection_state import preserve, restore
st.session_state.setdefault('_integration_actor', 'actor-A')
if st.session_state.get('outage'):
    preserve(st.session_state)
    st.error('Unconfirmed; writes stopped')
    st.stop()
restore(st.session_state)
st.text_input('Case', key='_integration_subject')
st.date_input('Operation', key='peri_operation_date')
"""
  app=AppTest.from_string(source).run()
  app.text_input[0].set_value('JUOG-901').run()
  app.date_input[0].set_value(date(2026,1,10)).run()
  app.session_state['outage']=True;app.run();app.run()
  self.assertEqual(len(app.text_input),0)
  app.session_state['outage']=False;app.run()
  self.assertEqual(len(app.exception),0)
  self.assertEqual(app.text_input[0].value,'JUOG-901')
  self.assertEqual(app.date_input[0].value,date(2026,1,10))
