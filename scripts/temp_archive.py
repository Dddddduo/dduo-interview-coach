#!/usr/bin/env python3
"""Temp script to archive the question."""
import sys
sys.path.insert(0, r'C:\Users\28757\dduo-interview-coach\scripts')
from question_manager import QuestionManager
from pathlib import Path

question = "如何保证信息不重复消费 — 消息幂等性方案深度解答"
answer_path = Path(r'C:\Users\28757\dduo-interview-coach\outputs\面经解答-20260704-消息幂等性深度解答.md')
answer = answer_path.read_text(encoding='utf-8')

mgr = QuestionManager()
entry = mgr.add(
    question=question,
    answer=answer,
    category='distributed',
    tags=['幂等性', '消息队列', 'Redis', 'Kafka'],
    difficulty='hard',
    source='/面经助手-20260704'
)
print(f"Done: {entry['id']} - {entry['question'][:40]}")
