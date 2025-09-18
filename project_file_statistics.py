#!/usr/bin/env python3
"""
项目文件统计脚本
统计指定项目在'/media/wnk/projects/'目录下的文件数量
包括：
1. 每个项目的总文件数量（递归统计）
2. 每个项目一级目录下的文件数量
"""

import os
import sys
from pathlib import Path

# 项目列表
projects = [
    "arangodb",
    "blender",
    "codelite",
    "codon",
    "foundationdb",
    "qt-creator",
    "rpcs3",
    "seq",
    "serenity",
    "shotcut",
    "treefrog-framework",
    "userver",
    "vireo",
    "wav2letter",
    "xtd"
]

# 项目根目录
base_dir = '/media/wnk/projects/'

def count_files_recursive(directory):
    """递归统计目录下所有文件数量"""
    try:
        count = 0
        for root, dirs, files in os.walk(directory):
            count += len(files)
        return count
    except (OSError, PermissionError) as e:
        print(f"错误：无法访问目录 {directory}: {e}")
        return 0

def count_files_first_level_dirs(directory):
    """统计一级目录及其包含的所有文件数量（递归）"""
    try:
        path = Path(directory)
        if not path.exists():
            return {}, 0
        
        first_level_stats = {}
        total_count = 0
        
        # 统计根目录下的文件
        root_files = [f for f in path.iterdir() if f.is_file()]
        if root_files:
            first_level_stats['(根目录)'] = len(root_files)
            total_count += len(root_files)
        
        # 统计每个一级子目录下的所有文件（递归）
        for item in path.iterdir():
            if item.is_dir():
                dir_count = count_files_recursive(item)
                if dir_count > 0:
                    first_level_stats[item.name] = dir_count
                    total_count += dir_count
        
        return first_level_stats, total_count
    except (OSError, PermissionError) as e:
        print(f"错误：无法访问目录 {directory}: {e}")
        return {}, 0

def format_number(num):
    """格式化数字，添加千位分隔符"""
    return f"{num:,}"

def main():
    print("=" * 100)
    print(f"项目文件统计报告")
    print(f"基础目录: {base_dir}")
    print("=" * 100)
    
    total_recursive = 0
    existing_projects = []
    missing_projects = []
    
    # 检查基础目录是否存在
    if not os.path.exists(base_dir):
        print(f"错误：基础目录 {base_dir} 不存在！")
        sys.exit(1)
    
    print(f"{'项目名称':<25} {'递归文件总数':<15} {'状态'}")
    print("-" * 100)
    
    for project in projects:
        project_path = os.path.join(base_dir, project)
        
        if os.path.exists(project_path) and os.path.isdir(project_path):
            # 统计递归文件数量
            recursive_count = count_files_recursive(project_path)
            
            # 统计一级目录文件数量及详情
            first_level_stats, first_level_total = count_files_first_level_dirs(project_path)
            
            print(f"{project:<25} {format_number(recursive_count):<15} {'存在'}")
            
            # 显示一级目录详情
            if first_level_stats:
                print(f"  一级目录分布:")
                for dir_name, count in sorted(first_level_stats.items()):
                    print(f"    {dir_name:<30} {format_number(count):>10} 文件")
                print()
            
            total_recursive += recursive_count
            existing_projects.append(project)
        else:
            print(f"{project:<25} {'N/A':<15} {'不存在'}")
            missing_projects.append(project)
    
    print("-" * 100)
    print(f"{'总计':<25} {format_number(total_recursive):<15}")
    print("=" * 100)
    
    # 统计摘要
    print(f"\n统计摘要:")
    print(f"  - 总项目数: {len(projects)}")
    print(f"  - 存在的项目数: {len(existing_projects)}")
    print(f"  - 缺失的项目数: {len(missing_projects)}")
    print(f"  - 总文件数（递归）: {format_number(total_recursive)}")
    
    if missing_projects:
        print(f"\n缺失的项目:")
        for project in missing_projects:
            print(f"  - {project}")
    
    print(f"\n说明:")
    print(f"  - 递归文件总数: 包括项目目录下所有子目录中的文件")
    print(f"  - 一级目录分布: 显示每个一级目录及其包含的所有文件数量（包括子目录）")

if __name__ == "__main__":
    main()