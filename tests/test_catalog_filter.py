import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.filter import catalog_filter


def test_catalog_filter_excludes_expired():
    df = pd.read_excel('tests/CATALOG_sample.xlsx')
    all_ids = catalog_filter(df, {'scope': 'national'})
    filtered_ids = catalog_filter(df, {'scope': 'national', 'exclude_expired': True})
    assert len(filtered_ids) < len(all_ids)
    assert set(filtered_ids).issubset(set(all_ids))
    assert all(isinstance(x, str) for x in filtered_ids)
