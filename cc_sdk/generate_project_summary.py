#!/usr/bin/env python3
"""
按项目汇总统计脚本
从summary_report.csv生成项目级别的汇总报告
"""

import csv
from collections import defaultdict
from pathlib import Path


def generate_project_summary(csv_path):
    """生成项目级别的汇总统计"""
    
    # 读取CSV文件
    projects = defaultdict(lambda: {
        'count': 0,
        'total_tokens': 0,
        'total_input': 0,
        'total_output': 0,
        'total_messages': 0,
        'total_time': 0.0
    })
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            project = row['项目目录']
            projects[project]['count'] += 1
            projects[project]['total_tokens'] += int(row['总tokens'])
            projects[project]['total_input'] += int(row['总输入tokens'])
            projects[project]['total_output'] += int(row['总输出tokens'])
            projects[project]['total_messages'] += int(row['消息数'])
            projects[project]['total_time'] += float(row['时间间隔(秒)'])
    
    # 按总tokens排序
    sorted_projects = sorted(projects.items(), key=lambda x: x[1]['total_tokens'], reverse=True)
    
    # 打印控制台报告
    print('=' * 140)
    print('项目级别汇总统计')
    print('=' * 140)
    print(f"{'项目目录':<45} {'会话数':<8} {'总消息数':<10} {'总时间(分)':<12} {'总输入':<15} {'总输出':<12} {'总Tokens':<15}")
    print('-' * 140)
    
    total_sessions = 0
    total_msgs = 0
    total_tks = 0
    total_inp = 0
    total_out = 0
    total_time = 0.0
    
    for project, stats in sorted_projects:
        print(f"{project:<45} "
              f"{stats['count']:<8} "
              f"{stats['total_messages']:<10,} "
              f"{stats['total_time']/60:<12.2f} "
              f"{stats['total_input']:<15,} "
              f"{stats['total_output']:<12,} "
              f"{stats['total_tokens']:<15,}")
        total_sessions += stats['count']
        total_msgs += stats['total_messages']
        total_tks += stats['total_tokens']
        total_inp += stats['total_input']
        total_out += stats['total_output']
        total_time += stats['total_time']
    
    print('-' * 140)
    print(f"{'总计':<45} "
          f"{total_sessions:<8} "
          f"{total_msgs:<10,} "
          f"{total_time/60:<12.2f} "
          f"{total_inp:<15,} "
          f"{total_out:<12,} "
          f"{total_tks:<15,}")
    print('=' * 140)
    print(f'\n统计: 共有 {len(projects)} 个不同的项目')
    
    # 生成项目级别CSV
    output_path = Path(csv_path).parent / 'project_summary.csv'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("项目目录,会话数,总消息数,总时间(秒),总时间(分钟),总输入tokens,总输出tokens,总tokens,平均每会话tokens,平均每消息tokens\n")
        for project, stats in sorted_projects:
            avg_tokens_per_session = stats['total_tokens'] / stats['count']
            avg_tokens_per_message = stats['total_tokens'] / stats['total_messages'] if stats['total_messages'] > 0 else 0
            f.write(f"{project},"
                   f"{stats['count']},"
                   f"{stats['total_messages']},"
                   f"{stats['total_time']:.2f},"
                   f"{stats['total_time']/60:.2f},"
                   f"{stats['total_input']},"
                   f"{stats['total_output']},"
                   f"{stats['total_tokens']},"
                   f"{avg_tokens_per_session:.2f},"
                   f"{avg_tokens_per_message:.2f}\n")
    
    print(f'\n已生成项目级别汇总: {output_path}')
    
    # 生成统计报告
    print('\n项目分类统计:')
    print('-' * 60)
    
    # 按token使用量分类
    huge_projects = [p for p, s in projects.items() if s['total_tokens'] > 10_000_000]
    large_projects = [p for p, s in projects.items() if 5_000_000 < s['total_tokens'] <= 10_000_000]
    medium_projects = [p for p, s in projects.items() if 1_000_000 < s['total_tokens'] <= 5_000_000]
    small_projects = [p for p, s in projects.items() if s['total_tokens'] <= 1_000_000]
    
    print(f'超大型项目 (>10M tokens): {len(huge_projects)} 个')
    print(f'大型项目 (5M-10M tokens): {len(large_projects)} 个')
    print(f'中型项目 (1M-5M tokens): {len(medium_projects)} 个')
    print(f'小型项目 (<1M tokens): {len(small_projects)} 个')
    
    # 按会话数分类
    multi_session = [p for p, s in projects.items() if s['count'] >= 4]
    standard_session = [p for p, s in projects.items() if 2 <= s['count'] < 4]
    single_session = [p for p, s in projects.items() if s['count'] == 1]
    
    print(f'\n多次会话项目 (≥4次): {len(multi_session)} 个')
    print(f'标准会话项目 (2-3次): {len(standard_session)} 个')
    print(f'单次会话项目 (1次): {len(single_session)} 个')


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = 'projects/summary_report.csv'
    
    if not Path(csv_path).exists():
        print(f'错误: 文件不存在: {csv_path}')
        sys.exit(1)
    
    generate_project_summary(csv_path)
