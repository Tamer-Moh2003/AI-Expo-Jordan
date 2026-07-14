import unittest
import os
import pandas as pd

class TestScatsParser(unittest.TestCase):
    
    def test_output_file_exists(self):
        self.assertTrue(os.path.exists('parsed_scats.csv'), "Error: parsed_scats.csv is missing!")
        self.assertTrue(os.path.exists('parsed_signal_phase.csv'), "Error: parsed_signal_phase.csv is missing!")

    def test_scats_columns(self):
        df = pd.read_csv('parsed_scats.csv')
        expected_columns = ['timestamp', 'detector_id', 'vehicle_count']
        
        for col in expected_columns:
            self.assertIn(col, df.columns, f"Error: Missing required column '{col}' in SCATS data")

    def test_scats_data_types(self):
        df = pd.read_csv('parsed_scats.csv')
        self.assertTrue(pd.api.types.is_numeric_dtype(df['vehicle_count']), "Error: vehicle_count must be a number")

if __name__ == '__main__':
    unittest.main()