"""Test Stage 5 consistency analysis logic."""
import sys
sys.path.insert(0, '.')

from routes.bills import (
    _compute_consistency_analysis,
    _parse_billing_period,
    _compute_stream_score_simple,
)

# Test 1: parse billing periods
assert _parse_billing_period('January 2024') == (2024, 1)
assert _parse_billing_period('2024-03') == (2024, 3)
assert _parse_billing_period('Mar 2024') == (2024, 3)
assert _parse_billing_period('') is None
print('[OK] _parse_billing_period works')

# Test 2: 3 months no gaps, low variance
periods = ['January 2024', 'February 2024', 'March 2024']
amounts = [8500, 8500, 8700]
r = _compute_consistency_analysis(periods, amounts)
print(f'[OK] 3 months no gaps: months={r["months_covered"]}, streak={r["streak"]}, gaps={r["num_gaps"]}, variance={r["variance"]}, flag={r["amount_variance_flag"]}')
assert r['months_covered'] == 3
assert r['streak'] == 3
assert r['num_gaps'] == 0
assert not r['amount_variance_flag']  # low variance, should not flag
print(f'     Timeline: {r["timeline"]}')

# Test 3: gap in the middle (Feb missing)
periods2 = ['January 2024', 'March 2024']
amounts2 = [8500, 8500]
r2 = _compute_consistency_analysis(periods2, amounts2)
print(f'[OK] Gap detected: months={r2["months_covered"]}, streak={r2["streak"]}, gaps={r2["num_gaps"]}')
assert r2['num_gaps'] == 1
assert r2['streak'] == 1   # max streak = 1 since no consecutive pair

# Test 4: high variance (1000 -> 9000 -> 500)
periods3 = ['Jan 2024', 'Feb 2024', 'Mar 2024']
amounts3 = [1000, 9000, 500]
r3 = _compute_consistency_analysis(periods3, amounts3)
print(f'[OK] Variance flag: {r3["amount_variance_flag"]}, variance={r3["variance"]}')
assert r3['amount_variance_flag']

# Test 5: gap penalty reduces score
score_clean = _compute_stream_score_simple('rent_receipt', 6, 8000, 'document_uploaded', num_gaps=0)
score_gaps  = _compute_stream_score_simple('rent_receipt', 6, 8000, 'document_uploaded', num_gaps=2)
print(f'[OK] Gap penalty: score_clean={score_clean}, score_with_2_gaps={score_gaps}')
assert score_gaps < score_clean

# Test 6: year-boundary streak (Nov 2023 -> Dec 2023 -> Jan 2024)
periods4 = ['November 2023', 'December 2023', 'January 2024']
r4 = _compute_consistency_analysis(periods4, [])
print(f'[OK] Year-boundary streak: streak={r4["streak"]}, gaps={r4["num_gaps"]}')
assert r4['streak'] == 3
assert r4['num_gaps'] == 0

print()
print('=== ALL STAGE 5 TESTS PASSED ===')
