#!/usr/bin/env python3
"""
测试构建脚本的简单测试
"""
import sys
from pathlib import Path
import asyncio
from dotenv import load_dotenv
# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from run_build import build_single_project

async def test_single_project():
    """测试单个项目构建"""
    # 选择一个较小的项目进行测试
    test_project = "seq"  # 通常比较小的项目
    
    print(f"开始测试项目: {test_project}")
    result = await build_single_project(test_project)
    
    if result:
        print(f"✅ 测试项目 {test_project} 构建成功")
    else:
        print(f"❌ 测试项目 {test_project} 构建失败")
    
    return result

if __name__ == "__main__":
    load_dotenv()  # 加载环境变量
    asyncio.run(test_single_project())
