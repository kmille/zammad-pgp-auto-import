#from zammad_pgp_import import app
#from fastapi.testclient import TestClient
#
#client = TestClient(app)
#
#
#def test_read_status():
#    response = client.get("/status")
#    assert response.status_code == 200
#    assert response.json == {'status': 'ok'}

#    zammad: Zammad
#
#    def setup_class(self):
#        self.zammad = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
#        self.zammad.delete_pgp_key(test_key_email)
#
#    def teardown_class(self):
#        self.zammad.delete_pgp_key(test_key_email)
#
#    def test_zammad_pgp_import(self):
#        # first, let's import test key
#        self.zammad.import_pgp_key(test_key_data)
#
#        key = PGPHandler.parse_pgp_key(test_key_data)
#        assert key.fingerprint == test_key_fingerprint
#        assert test_key_email in key.emails
#
#        # then, let's check it's really there
#        imported_keys = self.zammad.get_all_imported_pgp_keys()
#        assert key.fingerprint in [k['fingerprint'] for k in imported_keys]
#        assert set(key.emails) in ([set(e['email_addresses']) for e in imported_keys])
#
#    def test_zammad_pgp_deletion(self):
#        try:
#            self.zammad.import_pgp_key(test_key_data)
#        except ZammadError:
#            # key already exists
#            pass
#
#        # delete it
#        self.zammad.delete_pgp_key(test_key_email)
#        # check it does not exist any more
#        imported_keys = self.zammad.get_all_imported_pgp_keys()
#        assert test_key_fingerprint not in [k['fingerprint'] for k in imported_keys]

