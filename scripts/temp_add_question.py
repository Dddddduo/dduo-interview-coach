#!/usr/bin/env python3
"""Temporary script to add the question to the question bank."""
import sys
sys.path.insert(0, r'C:\Users\28757\dduo-interview-coach\scripts')
from question_manager import QuestionManager

question = "线程、进程、协程相关知识点"

# Read the answer from the output file
answer_path = r'C:\Users\28757\dduo-interview-coach\outputs\面经解答-20260704-线程进程协程.md'
with open(answer_path, 'r', encoding='utf-8') as f:
    answer = f.read()

manager = QuestionManager()
result = manager.add(
    question=question,
    answer=answer,
    tags=["进程", "线程", "协程", "虚拟线程", "并发"],
    difficulty="hard",
    source="/面经助手-20260704"
)
print(f"✅ 添加成功! ID: {result['id']}, 分类: {result['category']}, 难度: {result['difficulty']}")
print(f"   标签: {result['tags']}")
