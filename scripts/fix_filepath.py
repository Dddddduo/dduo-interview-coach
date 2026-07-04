import json

with open('questions/index.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Fix q0028 - correct file path to point to the right file
for q in data['questions']:
    if q['id'] == 'q0028':
        old_file = q['file']
        # Point to the existing file
        q['file'] = 'questions/database/mysql/垂直分表和水平分表的区别.md'
        print(f'Fixed q0028 file: {old_file} -> {q["file"]}')

with open('questions/index.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Done!')
