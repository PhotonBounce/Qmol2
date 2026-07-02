import json, urllib.request

API_BASE = 'http://127.0.0.1:8000/v1'
ADMIN = 'e7486611d2f8a0faf0bf7bd696a444fa49b9eda24ed4b654a988408939e9de3c'

# 1. Create dataset
req = urllib.request.Request(
    f'{API_BASE}/harvest/datasets',
    data=json.dumps({
        'name': 'Drug-Like Candidates',
        'description': 'Molecules with QED >= 0.5, Lipinski pass, no PAINS',
        'filter_sql': 'qed >= 0.5 AND lipinski_pass = 1 AND pains_hit = 0',
        'max_molecules': 1000
    }).encode(),
    headers={'Content-Type': 'application/json', 'x-admin-token': ADMIN},
    method='POST',
)
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode())
    print('=== DATASET CREATED ===')
    print(f'  ID: {data["dataset_id"]}')
    print(f'  Name: {data["name"]}')
    print(f'  Count: {data["molecule_count"]}')
    print(f'  Price: ${data["price_usd"]}')
    print()
    ds_id = data['dataset_id']

# 2. Export as CSV
req2 = urllib.request.Request(
    f'{API_BASE}/harvest/datasets/{ds_id}/csv',
    headers={'x-admin-token': ADMIN},
)
with urllib.request.urlopen(req2, timeout=10) as resp2:
    csv = resp2.read().decode()
    print('=== CSV EXPORT (first 10 lines) ===')
    for line in csv.splitlines()[:10]:
        print(line)
    print(f'... total {len(csv.splitlines())} lines')

# 3. Save CSV to file
out_path = 'data/dataset_1.csv'
with open(out_path, 'w') as f:
    f.write(csv)
print(f'\nSaved to: {out_path}')
