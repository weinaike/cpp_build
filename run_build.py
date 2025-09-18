
from argparse import Namespace
import os
import subprocess
import asyncio
import sys
import uuid
import json
import time
import gc
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult
# 导入 wr124 模块
from wr124 import run_team, STOP_REASON


class MessageProcessor:
    """消息处理器：既显示Console输出，又进行逻辑判断"""
    
    def __init__(self, iteration: int):
        self.iteration = iteration
        self.build_completed = False
        self.build_failed = False
    
    async def process_messages(self, message_stream):
        """处理消息流"""
        async for msg in message_stream:
            # 继续yield消息给Console显示
            yield msg
            
            # 同时进行逻辑判断
            if isinstance(msg, TaskResult):
                if msg.stop_reason == STOP_REASON.COMPLETED:
                    print(f"✅ 迭代 {self.iteration} 构建成功")
                    self.build_completed = True

                elif msg.stop_reason == STOP_REASON.ERROR:
                    print(f"❌ 迭代 {self.iteration} 构建出错")
                    self.build_failed = True



async def build_one(project, session_id=None):
    """
    执行项目构建，包含5次迭代逻辑
    每次迭代执行两个智能体：deep_research（生成指南）和 cpp_build_engineer（执行构建）
    """

    research_mcp_file = f"./cpp_build_new/mcps/mcp_{project}_r.json"
    json_config = {
        "mcpServers": {
                "command": {
                "command": "docker",
                "args": ["exec", "-i", project, "node", "/usr/src/app/dist/index.js"],
                "read_timeout_seconds": 600
                },
                "github": {
                "type": "streamable_http",
                "url": "https://api.githubcopilot.com/mcp",
                "headers": {
                    "Authorization": "Bearer ${GITHUB_TOKEN}"
                }
            }
        },
        "allowedMcpServers": ["command", "github"]
    }
    with open(research_mcp_file, "w") as f:
        json.dump(json_config, f, indent=4)


    build_mcp_file = f"./cpp_build_new/mcps/mcp_{project}_b.json"
    json_config = {
        "mcpServers": {
            "command": {
            "command": "docker",
            "args": ["exec", "-i", project, "node", "/usr/src/app/dist/index.js"],
            "read_timeout_seconds": 600
            }
        },
        "allowedMcpServers": ["command"]
    }
    with open(build_mcp_file, "w") as f:
        json.dump(json_config, f, indent=4)

    print(f"=== 开始执行项目构建迭代: {project} ===")
    
    max_iterations = 3
    
    for iteration in range(1, max_iterations + 1):
        print(f"\n{'='*60}")
        print(f"第 {iteration} 次迭代开始 - 项目: {project}")
        print(f"{'='*60}")
        
        try:
            # 第一步：执行 deep_research 智能体
            print(f"\n--- 步骤 1: 执行深度研究智能体 (迭代 {iteration}) ---")
            if iteration == 1:
                research_task = (
                    f"深入研究代码库，分析其所提供的说明文档、安装文档、设计指南以及散落在互联网上的各开发者的经验博客。"
                    f"要求输出一份适合本操作系统使用的代码库编译安装指南（要求输出指南文档，包含所有编译、构建、安装所涉及的各个环节），"
                    f"将文档写到项目根目录下: BUILD.md "
                    f"如果BUILD.md已经存在，则说明该任务已经完成，跳过该任务。"
                    f"代码库地址/root/project/."
                )
            else:
                research_task = (
                    f"基于上次迭代生成的编译安装指南（BUILD.md）和构建报告issues 目录下最新的的（build_report_x.md），"
                    f"结合代码库现状，重新审视编译安装方案."
                    f"如果发现上次方案中存在问题或遗漏，或者有更优的方案，请更新编译安装指南（BUILD.md）。注意详细说明修改点和原因。"
                    f"代码库地址/root/project/."
                )
            
            # 创建研究智能体的参数
            research_args = Namespace()
            research_args.task = research_task
            research_args.agent = "cpp_build_new/deep_researcher.md"
            research_args.project_id = project
            research_args.env_file = None
            research_args.interactive = True
            research_args.debug = False
            research_args.resume = False
            research_args.session_id = session_id
            research_args.config_file = research_mcp_file

            # 使用消息处理器处理研究智能体的输出
            await Console(run_team(research_args))

            print(f"✅ 迭代 {iteration} 深度研究完成")
            
            # 等待一段时间，确保文件系统同步
            print("等待10秒，确保研究结果同步...")

            time.sleep(10)
            
            # 清理可能的残留资源，为下一个智能体做准备
            gc.collect()
            
            # 第二步：执行 cpp_build_engineer 智能体
            print(f"\n--- 步骤 2: 执行构建工程师智能体 (迭代 {iteration}) ---")
            
            build_task = (
                f"项目地址:/root/project/. 帮我完成该项目的cpp代码编译构建。"
                f"适于本系统环境的编译构建指南 BUILD.md 已经生成在项目根目录下，遵循该指南完成编译构建工作。"
                f"编译构建过程中可能遇到各类问题：比如编译器版本、标准库版本、第三方库版本等，"
                f"这些问题解决思路：先收集信息制定方案，方案确定后再开展具体修复工作。"
                f"该代码库是一个成熟代码库，优先从系统环境、编译环境、依赖问题等方面，版本依赖可以根据需要调整，尽量避免代码修改。"
            )
            
            # 创建构建智能体的参数
            build_args = Namespace()
            build_args.task = build_task
            build_args.agent = "cpp_build_new/cpp_builder.md"
            build_args.project_id = project
            build_args.env_file = None
            build_args.interactive = True
            build_args.debug = False
            build_args.resume = False
            build_args.session_id = session_id
            build_args.config_file = build_mcp_file
            
            # 使用消息处理器同时处理Console输出和逻辑判断
            processor = MessageProcessor(iteration)
            await Console(processor.process_messages(run_team(build_args)))
            if processor.build_completed:
                print(f"✅ 迭代 {iteration} 构建成功")
                break  # 结束迭代
        except Exception as e:
            print(f"[错误] 迭代 {iteration} 执行过程中发生异常: {e}")

            

    
    print(f"\n{'='*60}")
    print(f"项目 {project} 所有迭代完成")
    print(f"{'='*60}")
    
    return True

def start_docker(project):
    """启动或创建Docker容器，返回是否需要停止容器的标志"""
    container_name = project
    project_dir = f"/media/wnk/projects/{project}"
    
    print(f"正在检查容器: {container_name}")
    print(f"项目目录: {project_dir}")
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        print(f"错误: 项目目录 {project_dir} 不存在")
        return False, False
    
    should_stop_container = False
    
    try:
        # 检查容器是否已经存在并正在运行
        result = subprocess.run([
            "docker", "ps", "-q", "-f", f"name={container_name}"
        ], capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            print(f"容器 {container_name} 已在运行中，直接使用")
            return True, should_stop_container
        
        # 检查容器是否存在但未启动
        result = subprocess.run([
            "docker", "ps", "-a", "-q", "-f", f"name={container_name}"
        ], capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            print(f"容器 {container_name} 存在但未启动，启动容器")
            subprocess.run(["docker", "start", container_name], check=True)
            should_stop_container = True
            print(f"容器 {container_name} 已启动")
            # 等待容器完全启动
            time.sleep(2)
        else:
            print("容器不存在，创建并启动容器")
            should_stop_container = True
            
            # 启动容器（后台运行，保持运行状态）
            subprocess.run([
                "docker", "run", "-d", "--name", container_name,
                "-v", f"{project_dir}:/root/project",
                "-v", "/usr/local/cuda-12.1:/usr/local/cuda",
                "-v", "/home/wnk/.ssh:/root/.ssh",
                "-e", "MCP_CLIENT_DOCKER=True",
                "-e", "TZ=Asia/Shanghai",
                "-e", "CUDA_HOME=/usr/local/cuda",
                "--hostname", container_name,
                "--workdir", "/root/project",
                "--gpus", "all",
                "cppbuild:latest",
                "tail", "-f", "/dev/null"
            ], check=True)
            
            print(f"容器 {container_name} 已创建并启动")
            
            # 等待容器完全启动
            time.sleep(2)
        
        return True, should_stop_container
        
    except subprocess.CalledProcessError as e:
        print(f"启动容器时出错: {e}")
        return False, should_stop_container

def stop_docker(project, should_stop):
    """智能停止容器：只在需要时停止容器"""
    container_name = project
    
    if should_stop:
        try:
            print(f"停止容器: {container_name}")
            subprocess.run(["docker", "stop", container_name], check=True)
            print(f"容器 {container_name} 已停止")
        except subprocess.CalledProcessError as e:
            print(f"停止容器时出错: {e}")
    else:
        print(f"容器 {container_name} 保持运行状态（原本就在运行）")

async def build_all(projects):
    """遍历所有项目进行构建"""
    for project in projects:
        print(f"\n{'='*50}")
        print(f"开始处理项目: {project}")
        print(f"{'='*50}")
        
        # 启动Docker容器
        success, should_stop = start_docker(project)
        if not success:
            print(f"项目 {project} 容器启动失败，跳过")
            continue
        
        try:
            # 执行构建
            build_success = await build_one(project, session_id=str(uuid.uuid4()))
            if build_success:
                print(f"项目 {project} 构建成功")
            else:
                print(f"项目 {project} 构建失败")
        except Exception as e:
            print(f"项目 {project} 构建过程中发生错误: {e}")
        finally:
            # 清理容器（如果需要的话）
            stop_docker(project, should_stop)
        
        print(f"项目 {project} 处理完成\n")


async def build_single_project(project_name: str):
    """构建单个项目的函数，用于测试"""
    print(f"\n{'='*50}")
    print(f"开始处理单个项目: {project_name}")
    print(f"{'='*50}")
    
    # 启动Docker容器
    success, should_stop = start_docker(project_name)
    if not success:
        print(f"项目 {project_name} 容器启动失败")
        return False
    
    try:
        # 执行构建
        build_success = await build_one(project_name, session_id=str(uuid.uuid4()))
        if build_success:
            print(f"✅ 项目 {project_name} 构建成功")
        else:
            print(f"❌ 项目 {project_name} 构建失败")
        return build_success
    except Exception as e:
        print(f"项目 {project_name} 构建过程中发生错误: {e}")
        return False
    finally:
        # 清理容器（如果需要的话）
        stop_docker(project_name, should_stop)
        print(f"项目 {project_name} 处理完成")


if __name__ == "__main__":    
    
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

    # 支持命令行参数指定单个项目
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        asyncio.run(build_single_project(project_name))
    else:
        print("构建所有项目")
        asyncio.run(build_all(projects))