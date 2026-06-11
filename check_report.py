import json

with open('output/risk_report.json', encoding='utf-8') as f:
    r = json.load(f)

print('Total accounts in report:', len(r['accounts']))
print()

for a in r['accounts'][:8]:
    summary = a.get('narrative_summary', '')
    has_real = summary and 'narrative generation failed' not in summary
    has_flags = bool(a.get('risk_flags'))
    print(
        a['account_name'].ljust(30),
        a['risk_tier'].ljust(7),
        'narrative=' + ('YES' if has_real else 'NO '),
        'csm_flags=' + ('YES' if has_flags else 'NO'),
    )

print()
print('Portfolio insights:', 'YES' if r.get('portfolio_insights', {}).get('insights') else 'NO')
print()
print('Sample narrative:', r['accounts'][0].get('narrative_summary', '')[:120])
