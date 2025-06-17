import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from registry import filter_registry_by_status, status_counts, RegistryStatus


def test_filter_registry_by_status():
    df = pd.DataFrame({
        'pdf_id': ['a', 'b', 'c', 'd'],
        'status': ['live', 'new_tagged', 'live_for_deletion', 'live']
    })
    live_rows = filter_registry_by_status(df, RegistryStatus.LIVE)
    assert live_rows['pdf_id'].tolist() == ['a', 'd']


def test_status_counts():
    df = pd.DataFrame({'status': ['live', 'new_tagged', 'live', 'live_for_deletion']})
    counts = status_counts(df)
    assert counts.get('live') == 2
    assert counts.get('new_tagged') == 1
