import unittest
from scripts.prepare_data import centro_geometria, combinar_elementos, obtener_elementos

class TestData(unittest.TestCase):
    def test_point(self):
        self.assertEqual(centro_geometria({'type':'Point','coordinates':[-8,42]}), [-8,42])
    def test_deduplication(self):
        a = {'type':'node','id':1}
        self.assertEqual(combinar_elementos([a],[a]), [a])
    def test_empty(self):
        with self.assertRaises(ValueError):
            obtener_elementos({'elements':[]})
