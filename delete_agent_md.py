#!/usr/bin/env python3
"""
删除指定项目的Agent.md文件脚本
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

def delete_agent_md_files():
    """删除指定项目的Agent.md文件"""
    
    print("=" * 80)
    print("删除项目Agent.md文件")
    print(f"基础目录: {base_dir}")
    print("=" * 80)
    
    # 检查基础目录是否存在
    if not os.path.exists(base_dir):
        print(f"错误：基础目录 {base_dir} 不存在！")
        sys.exit(1)
    
    deleted_count = 0
    not_found_count = 0
    project_not_exist_count = 0
    
    print(f"{'项目名称':<25} {'Agent.md状态':<20} {'操作结果'}")
    print("-" * 80)
    
    for project in projects:
        project_path = os.path.join(base_dir, project)
        agent_md_path = os.path.join(project_path, "Agent.md")
        
        if not os.path.exists(project_path):
            print(f"{project:<25} {'项目目录不存在':<20} {'跳过'}")
            project_not_exist_count += 1
            continue
            
        if os.path.exists(agent_md_path):
            try:
                os.remove(agent_md_path)
                print(f"{project:<25} {'文件存在':<20} {'已删除'}")
                deleted_count += 1
            except Exception as e:
                print(f"{project:<25} {'文件存在':<20} {'删除失败: {str(e)}'}")
        else:
            print(f"{project:<25} {'文件不存在':<20} {'无需操作'}")
            not_found_count += 1
    
    print("-" * 80)
    print(f"\n操作摘要:")
    print(f"  - 总项目数: {len(projects)}")
    print(f"  - 项目目录不存在: {project_not_exist_count}")
    print(f"  - 成功删除Agent.md: {deleted_count}")
    print(f"  - Agent.md不存在: {not_found_count}")
    print("=" * 80)

def main():
    # 确认操作
    print("即将删除以下项目的Agent.md文件：")
    for i, project in enumerate(projects, 1):
        print(f"  {i:2d}. {project}")
    
    print(f"\n基础目录: {base_dir}")
    
    confirm = input("\n确认要删除这些Agent.md文件吗？(y/N): ").lower().strip()
    
    if confirm in ['y', 'yes']:
        delete_agent_md_files()
    else:
        print("操作已取消。")

if __name__ == "__main__":
    main()