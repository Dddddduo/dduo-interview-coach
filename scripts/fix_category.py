import json

with open('questions/index.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Fix q0028 - change category from spring to mysql
for q in data['questions']:
    if q['id'] == 'q0028':
        print('Before:', q)
        q['category'] = 'mysql'
        q['tags'] = ['分表', '分片', 'Sharding', '数据库优化', '垂直分表', '水平分表']
        # Construct correct file path using parts
        filename = q['file'].replace('\\', '/').split('/')[-1]
        q['file'] = 'questions/database/mysql/' + filename
        print('After:', q)

# Update category counts
cat_count = {}
for q2 in data['questions']:
    c = q2.get('category', 'java')
    cat_count[c] = cat_count.get(c, 0) + 1
for cat in data['categories']:
    data['categories'][cat]['count'] = cat_count.get(cat, 0)

with open('questions/index.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Done!')
