#!/usr/bin/env python3
"""
JSONL文件分析脚本
分析会话消息的时间间隔和token使用情况
支持单个文件或整个目录的批量分析
"""

import json
import sys
from datetime import datetime
from pathlib import Path
import statistics
import os


def parse_timestamp(ts_str):
    """解析时间戳字符串"""
    try:
        # 支持ISO 8601格式: 2025-09-24T01:06:22.982Z
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except:
        return None


def analyze_jsonl(file_path, output_csv=True):
    """分析JSONL文件"""
    
    messages = []
    
    # 读取所有消息
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    messages.append(data)
                except json.JSONDecodeError as e:
                    # 静默跳过无法解析的行
                    continue
    except Exception as e:
        print(f"错误: 无法读取文件 {file_path}: {e}")
        return None
    
    if not messages:
        return None
    
    # 1. 统计时间间隔
    timestamps = []
    for msg in messages:
        if 'timestamp' in msg:
            ts = parse_timestamp(msg['timestamp'])
            if ts:
                timestamps.append(ts)
    
    time_interval_seconds = 0
    first_timestamp = None
    last_timestamp = None
    
    if len(timestamps) >= 2:
        time_interval_seconds = (timestamps[-1] - timestamps[0]).total_seconds()
        first_timestamp = timestamps[0]
        last_timestamp = timestamps[-1]
    
    # 2. 统计token使用情况
    token_stats = []
    
    for i, msg in enumerate(messages, 1):
        if 'message' in msg and 'usage' in msg['message']:
            usage = msg['message']['usage']
            
            input_tokens = usage.get('input_tokens', 0)
            cache_read_tokens = usage.get('cache_read_input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            # 总输入token = input_tokens + cache_read_input_tokens
            total_input = input_tokens + cache_read_tokens
            
            token_stats.append({
                'message_num': i,
                'input_tokens': input_tokens,
                'cache_read_tokens': cache_read_tokens,
                'total_input': total_input,
                'output_tokens': output_tokens,
                'timestamp': msg.get('timestamp', 'N/A'),
                'role': msg.get('message', {}).get('role', 'N/A'),
                'type': msg.get('type', 'N/A')
            })
    
    if not token_stats:
        return None
    
    # 计算统计数据
    avg_total_input = statistics.mean([s['total_input'] for s in token_stats])
    avg_output = statistics.mean([s['output_tokens'] for s in token_stats])
    total_input_sum = sum([s['total_input'] for s in token_stats])
    total_output_sum = sum([s['output_tokens'] for s in token_stats])
    
    # 返回分析结果
    return {
        'file_path': str(file_path),
        'total_messages': len(messages),
        'messages_with_usage': len(token_stats),
        'first_timestamp': first_timestamp,
        'last_timestamp': last_timestamp,
        'time_interval_seconds': time_interval_seconds,
        'avg_total_input': avg_total_input,
        'avg_output': avg_output,
        'total_input_sum': total_input_sum,
        'total_output_sum': total_output_sum,
        'total_tokens': total_input_sum + total_output_sum,
        'token_stats': token_stats
    }


def print_single_file_report(result, output_csv=True):
    """打印单个文件的详细报告"""
    if not result:
        return
    
    print(f"\n文件: {result['file_path']}")
    print(f"共读取 {result['total_messages']} 条消息\n")
    
    # 打印时间统计
    if result['first_timestamp'] and result['last_timestamp']:
        print("=" * 80)
        print("时间统计")
        print("=" * 80)
        print(f"第一条消息时间: {result['first_timestamp']}")
        print(f"最后一条消息时间: {result['last_timestamp']}")
        print(f"总时间间隔: {result['time_interval_seconds']:.2f} 秒 ({result['time_interval_seconds']/60:.2f} 分钟)")
        print()
    
    # 打印Token统计
    print("=" * 80)
    print("Token使用统计")
    print("=" * 80)
    print(f"平均每条消息输入token: {result['avg_total_input']:.2f}")
    print(f"平均每条消息输出token: {result['avg_output']:.2f}")
    print(f"总输入token: {result['total_input_sum']:,}")
    print(f"总输出token: {result['total_output_sum']:,}")
    print(f"总token使用: {result['total_tokens']:,}")
    print()
    
    # 打印详细表格
    token_stats = result['token_stats']
    print("=" * 120)
    print("详细Token使用表")
    print("=" * 120)
    print(f"{'消息#':<8} {'类型':<12} {'角色':<10} {'input_tokens':<15} {'cache_read':<15} {'总输入':<15} {'输出tokens':<15}")
    print("-" * 120)
    
    for stat in token_stats:
        print(f"{stat['message_num']:<8} "
              f"{stat['type']:<12} "
              f"{stat['role']:<10} "
              f"{stat['input_tokens']:<15,} "
              f"{stat['cache_read_tokens']:<15,} "
              f"{stat['total_input']:<15,} "
              f"{stat['output_tokens']:<15,}")
    
    print("-" * 120)
    print(f"{'总计':<8} {'':<12} {'':<10} "
          f"{sum(s['input_tokens'] for s in token_stats):<15,} "
          f"{sum(s['cache_read_tokens'] for s in token_stats):<15,} "
          f"{result['total_input_sum']:<15,} "
          f"{result['total_output_sum']:<15,}")
    print("=" * 120)
    
    # 生成CSV文件
    if output_csv:
        csv_path = Path(result['file_path']).with_suffix('.csv')
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("消息编号,类型,角色,input_tokens,cache_read_input_tokens,总输入tokens,输出tokens,时间戳\n")
            for stat in token_stats:
                f.write(f"{stat['message_num']},"
                       f"{stat['type']},"
                       f"{stat['role']},"
                       f"{stat['input_tokens']},"
                       f"{stat['cache_read_tokens']},"
                       f"{stat['total_input']},"
                       f"{stat['output_tokens']},"
                       f"{stat['timestamp']}\n")
        
        print(f"\n已导出CSV文件到: {csv_path}")


def analyze_directory(directory_path):
    """分析目录中的所有JSONL文件"""
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"错误: 目录不存在: {directory_path}")
        return
    
    # 查找所有.jsonl文件
    jsonl_files = list(directory.rglob('*.jsonl'))
    
    if not jsonl_files:
        print(f"错误: 在 {directory_path} 中没有找到.jsonl文件")
        return
    
    print(f"找到 {len(jsonl_files)} 个JSONL文件")
    print("=" * 120)
    
    results = []
    
    for file_path in jsonl_files:
        result = analyze_jsonl(file_path, output_csv=True)
        if result:
            results.append(result)
    
    if not results:
        print("错误: 没有成功分析的文件")
        return
    
    # 打印汇总报告
    print("\n\n")
    print("=" * 120)
    print("汇总报告")
    print("=" * 120)
    print(f"{'文件名':<50} {'消息数':<10} {'时间(秒)':<12} {'总输入':<15} {'总输出':<15} {'总Token':<15}")
    print("-" * 120)
    
    total_messages = 0
    total_time = 0
    total_input = 0
    total_output = 0
    
    for result in results:
        file_name = Path(result['file_path']).name
        total_messages += result['total_messages']
        total_time += result['time_interval_seconds']
        total_input += result['total_input_sum']
        total_output += result['total_output_sum']
        
        print(f"{file_name:<50} "
              f"{result['messages_with_usage']:<10} "
              f"{result['time_interval_seconds']:<12.2f} "
              f"{result['total_input_sum']:<15,} "
              f"{result['total_output_sum']:<15,} "
              f"{result['total_tokens']:<15,}")
    
    print("-" * 120)
    print(f"{'总计':<50} "
          f"{total_messages:<10} "
          f"{total_time:<12.2f} "
          f"{total_input:<15,} "
          f"{total_output:<15,} "
          f"{total_input + total_output:<15,}")
    print("=" * 120)
    
    # 生成汇总CSV - 按项目目录分组，只保留输入token最大的记录
    from collections import defaultdict
    
    # 按项目目录分组
    projects_dict = defaultdict(list)
    for result in results:
        file_path = Path(result['file_path'])
        project_dir = file_path.parent.name
        # 去掉前缀 -home-wnk-cc-projects-
        if project_dir.startswith('-home-wnk-cc-projects-'):
            project_dir = project_dir.replace('-home-wnk-cc-projects-', '')
        result['clean_project_dir'] = project_dir
        projects_dict[project_dir].append(result)
    
    # 对每个项目，只保留总输入token最大的记录
    filtered_results = []
    for project_dir, project_results in projects_dict.items():
        # 按总输入token排序，取最大的
        max_result = max(project_results, key=lambda x: x['total_input_sum'])
        filtered_results.append(max_result)
    
    # 按总tokens降序排序
    filtered_results.sort(key=lambda x: x['total_tokens'], reverse=True)
    
    summary_csv_path = directory / 'summary_report.csv'
    with open(summary_csv_path, 'w', encoding='utf-8') as f:
        f.write("文件名,项目目录,消息数,时间间隔(秒),时间间隔(分钟),总输入tokens,总输出tokens,总tokens,平均输入,平均输出,第一条消息时间,最后一条消息时间\n")
        for result in filtered_results:
            file_path = Path(result['file_path'])
            file_name = file_path.name
            project_dir = result['clean_project_dir']
            f.write(f"{file_name},"
                   f"{project_dir},"
                   f"{result['messages_with_usage']},"
                   f"{result['time_interval_seconds']:.2f},"
                   f"{result['time_interval_seconds']/60:.2f},"
                   f"{result['total_input_sum']},"
                   f"{result['total_output_sum']},"
                   f"{result['total_tokens']},"
                   f"{result['avg_total_input']:.2f},"
                   f"{result['avg_output']:.2f},"
                   f"{result['first_timestamp']},"
                   f"{result['last_timestamp']}\n")
    
    print(f"\n已生成汇总报告: {summary_csv_path}")


def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_jsonl.py <jsonl文件路径或目录路径>")
        print("示例: python analyze_jsonl.py file.jsonl")
        print("示例: python analyze_jsonl.py projects/")
        sys.exit(1)
    
    path = sys.argv[1]
    path_obj = Path(path)
    
    if not path_obj.exists():
        print(f"错误: 路径不存在: {path}")
        sys.exit(1)
    
    if path_obj.is_file():
        # 分析单个文件
        result = analyze_jsonl(path_obj)
        if result:
            print_single_file_report(result)
        else:
            print(f"无法分析文件: {path}")
    elif path_obj.is_dir():
        # 分析整个目录
        analyze_directory(path_obj)
    else:
        print(f"错误: 无效的路径: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
