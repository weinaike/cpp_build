import traceback
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.model_context import UnboundedChatCompletionContext
from autogen_agentchat.messages import TextMessage
from autogen_core.models import UserMessage, ModelInfo, SystemMessage, LLMMessage, CreateResult

from dotenv import load_dotenv
from pathlib import Path
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
from wr124 import SessionParam, SessionStateManager
# 临时修复 autogen_ext 不支持 extra_body 的问题
from autogen_ext.models.openai import _openai_client
_openai_client.create_kwargs.update(['extra_body', 'extra_headers', 'extra_query'])
from autogen_ext.models.anthropic import AnthropicChatCompletionClient
use_claude = False


class MessageProcessor:
    """消息处理器：既显示Console输出，又进行逻辑判断"""
    
    def __init__(self, iteration: int):
        self.iteration = iteration
        self.build_completed = False
        self.build_failed = False
        self.result = None
    
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

                self.result = msg



summary_prompt = '''
You are a helpful assistant
Please conduct a structured analysis and extraction of the provided long conversation history, outputting according to the following format:

## Analysis Requirements

### 1. Overall Task Objectives
- Identify and describe the main task objectives in the conversation
- Clarify the final expected results of the task

### 2. Specific Execution Actions and Result Analysis
For this task, record in detail the specific actions taken and results obtained
- Action:1 : Direct Success
    - **Sub-goal**: [Specific description]
    - **Execution Actions**: [Detailed list of actions taken]
    - **Result Content**: [Specific results successfully obtained]
    - **Success Key Points**: [Critical success factors]
- Action2 : Success After Multiple Attempts
    - **Sub-goal**: [Specific description]
    - **Number of Attempts**: [X times]
    - **Methods Used**:
    - Method 1: [Description] → [Result/Problem]
    - Method 2: [Description] → [Result/Problem]
    - ...
    - Final Successful Method: [Description]
    - **Problems Resolved**:
    - Problem 1: [Description and solution]
    - Problem 2: [Description and solution]
    - **Final Result**: [Specific results successfully obtained]
    - **Experience Summary**: [Key experiences learned from multiple attempts]
- Action3: Failure After Multiple Attempts
    - **Sub-goal**: [Specific description]
    - **Number of Attempts**: [X times]
    - **Methods Used and Effects**:
    - Method 1: [Description] → [Effect evaluation] → [Failure reason]
    - Method 2: [Description] → [Effect evaluation] → [Failure reason]
    - ...
    - **Confirmed Effective Results**:
    - [List aspects that produced positive effects although not fully successful]
    - **Remaining Problem Details**:
    - Problem 1: [Detailed description]
        - Error Log: [Specific error information]
        - Symptom Manifestation: [Specific manifestations of the problem]
        - Possible Causes: [Analyzed potential causes]
    - Problem 2: [Detailed description]
        - Error Log: [Specific error information]
        - Symptom Manifestation: [Specific manifestations of the problem]
        - Possible Causes: [Analyzed potential causes]

## Output Format Requirements
- Use clear title hierarchy structure
- For technical issues, provide specific error logs and code snippets
- Accurately mark quantitative information (such as number of attempts, time consumption, etc.)
- Maintain objectivity, distinguish between factual description and don't subjective analysis

Please analyze the conversation history based on the above framework.

'''
merge_instruction = '''
# Merge Instructions

Please intelligently merge the multiple fragment summaries above according to chronological logic to form a complete and coherent conversation summary.

## Merge Strategy Requirements:

### 1. Content Integration Principles
- **Deduplication and Merging**: Identify and merge identical or similar content to avoid redundant descriptions
- **Status Updates**: When multiple fragments contain different states of the same task/problem, use the chronologically latest state as the standard
- **Logical Coherence**: Ensure the merged content is logically coherent and contextually connected

### 2. Task Status Handling
- **Progress Tracking**: Work mentioned as "in progress" or "incomplete" in earlier fragments should be updated to the final completion status if completed in later fragments
- **Problem Resolution**: Problems mentioned in earlier fragments that are resolved in later fragments should record the resolution process and final results
- **Persistent Problems**: Unresolved problems should be retained and all related attempts and analyses should be consolidated

### 3. Output Format Requirements
- Maintain the original structured format 
- Integrate all relevant technical details, error logs, and code snippets
- Accurately count final quantitative information (such as total number of attempts, final number of successful/failed tasks, etc.)
- Highlight key experience summaries and lessons learned

### 4. Quality Standards
- **Completeness**: Do not omit any important information
- **Accuracy**: Ensure technical details and status descriptions are accurate
- **Conciseness**: Remove redundancy and keep content concise
- **Practicality**: Highlight key information that has guiding value for subsequent work

Please merge these fragments into a high-quality complete conversation summary based on the above requirements.
'''

async def download_history(project_id, session_id=None, agent_name="cpp_builder") -> list[dict]:
    if session_id is None:
        session_id = str(uuid.uuid4())
    param= SessionParam(
            project_id=project_id,
            session_id=session_id,
            api_url="http://localhost/api",
            timeout=30
        )
    client = SessionStateManager(param)
    
    # 构建查询参数
    query = {
        "name_pattern": agent_name,
        "document_type": "session_state",
        "tags": ["session_state"],
        "sort_by": "created_at",
        "sort_order": 1  # 降序，最新的在前
    }

    status, docs = await client._download_documents(query)
    if status == "success":
        return docs
    else:
        return []

async def call_llm(messages:list[LLMMessage]) -> CreateResult:
    if use_claude:
        client = AnthropicChatCompletionClient(api_key=os.environ.get("ANTHROPIC_API_KEY",''), 
                                               base_url=os.environ.get("ANTHROPIC_BASE_URL", ''), 
                                        model_info=ModelInfo(
                                            vision=False,
                                            function_calling=True,
                                            json_output=True,
                                            family='claude-4-sonnet',
                                            structured_output=False,
                                            multiple_system_messages=False,
                                        ), 
                                        model='glm-4.5',
                                        timeout=300,
                                        temperature=0.6,
                                        max_retries=3,
                            )

        response = await client.create(
            messages=messages,
            tools=[],
            tool_choice="none",
        )
        return response
    else:        
        client = OpenAIChatCompletionClient(api_key=os.environ.get("ZHIPU_API_KEY", ''),
                            base_url=os.environ.get("ZHIPU_BASE_URL", ''), 
                            model_info=ModelInfo(
                                vision=False,
                                function_calling=True,
                                json_output=True,
                                family='gpt-4o',
                                structured_output=False,
                                multiple_system_messages=True,
                            ), 
                            model='glm-4.5',
                            timeout=300,
                            temperature=0.6,
                            max_retries=3,

                            )  # 请填写您自己的 API Key
    
        response = await client.create(
            messages=messages,
            extra_create_args={"extra_body":{
                    "thinking": {
                        "type": "enabled",
                    },
                }}
        )
        return response
async def summary_exec_history(project, docs) -> list[str]:
    
    files:list[str]= []

    for doc in docs:
        id = doc.get('_id')
        time = doc.get('created_at')
        name = doc.get('name','unknown')
        content = doc.get('content',[])
        
        llm_context = content.get('llm_context')
           
        print(id, time, name)
        os.makedirs(Path(__file__).parent / "summary", exist_ok=True)
        summary_file = str(Path(__file__).parent / "summary" / f"{project}_{id}.md")
        files.append(summary_file)
        if os.path.exists(summary_file):
            print(f"Summary file {summary_file} already exists, skipping...")
            continue

        context = UnboundedChatCompletionContext()
        await context.load_state(llm_context)
        llm_messages = await context.get_messages()

        all_messages = llm_messages + [SystemMessage(content=summary_prompt), 
                                    UserMessage(content="Please conduct a structured analysis and extraction of the provided long conversation history", source='user')]
        
        response = await call_llm(all_messages)
            
        # 获取完整回复
        print(response.usage.prompt_tokens, response.usage.completion_tokens, flush=True)
        with open(summary_file, 'w', encoding='utf-8') as f:
            if isinstance(response.content,str):
                f.write(response.content)
        

    return files

async def merge_summaries(files:list[str]):
    prompt = ''
    for i, file in enumerate(files):
        f = open(file)
        content = f.read()
        prompt += f'# Summary of the {i+1}th fragment of long conversation history:\n\n {content} \n{"=" * 50}\n'


    prompt += "Please merge these fragments into a high-quality complete conversation summary."

    messages = [SystemMessage(content=merge_instruction), 
                UserMessage(content=prompt, source='user')]
    response = await call_llm(messages)
    if isinstance(response.content, str):
        return response.content
    else:
        return ''

async def builder_history_summary(project):
    docs = await download_history(project)
    print(project, len(docs))
    summary_files = await summary_exec_history(project,docs)
    merged_summary = await merge_summaries(summary_files)

    summary_file = str(Path(__file__).parent / "summary" / f"{project}_merged.md")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(merged_summary)
    return merged_summary


async def deep_researcher_proposal(project, session_id):
    docs = await download_history(project, session_id, agent_name="deep_researcher")
    doc = docs[-1] if len(docs)>0 else None
    if doc:
        id = doc.get('_id')
        file = str(Path(__file__).parent / "summary" / f"{project}_proposal_{id}.md")
        if os.path.exists(file):
            print(f"Proposal file {file} already exists, skipping...")
            with open(file, 'r', encoding='utf-8') as f:
                return f.read()

        content = doc.get('content',[])        
        llm_context = content.get('llm_context')

        context = UnboundedChatCompletionContext()
        await context.load_state(llm_context)
        llm_messages = await context.get_messages()

        all_messages = llm_messages + [SystemMessage(content='You are a helpful assistant, please provide practical and reliable suggestions based on the long conversation history of deep_researcher agent.'), 
                                    UserMessage(content="Reading comprehension: Please read the above long conversation history and tell me what impportant recommendations were finally provided for cpp_builder for problems currently encountered, ", source='user')]
        response = await call_llm(all_messages)
        if isinstance(response.content, str):
            with open(file, 'w', encoding='utf-8') as f:
                f.write(response.content)
            return response.content
    return ''


async def run_deep_researcher(project, session_id, task):

    os.makedirs(Path(__file__).parent / "mcps", exist_ok=True)
    research_mcp_file = str(Path(__file__).parent / "mcps" / f"mcp_{project}_r.json")
    # 获取GitHub token
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("警告: 未找到 GITHUB_TOKEN 环境变量，GitHub API功能可能无法使用")
        github_token = ""
    
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
                    "Authorization": f"Bearer {github_token}"
                }
            }
        },
        "allowedMcpServers": ["command", "github"]
    }
    with open(research_mcp_file, "w") as f:
        json.dump(json_config, f, indent=4)

    
    # 创建研究智能体的参数
    research_args = Namespace()
    research_args.task = task
    research_args.agent = str(Path(__file__).parent / "deep_researcher.md")
    research_args.project_id = project
    research_args.env_file = None
    research_args.interactive = True
    research_args.debug = False
    research_args.resume = False
    research_args.session_id = session_id
    research_args.config_file = research_mcp_file
    research_args.claude = use_claude

    # 使用消息处理器处理研究智能体的输出
    processor = MessageProcessor(0)
    await Console(processor.process_messages(run_team(research_args)))
    return processor

async def run_cpp_builder(project, session_id, task):
    build_mcp_file = str(Path(__file__).parent / "mcps" / f"mcp_{project}_b.json")
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

    
    # 创建构建智能体的参数
    build_args = Namespace()
    build_args.task = task
    build_args.agent = str(Path(__file__).parent / "cpp_builder.md")
    build_args.project_id = project
    build_args.env_file = None
    build_args.interactive = True
    build_args.debug = False
    build_args.resume = True
    build_args.session_id = session_id
    build_args.config_file = build_mcp_file
    build_args.claude = use_claude
    
    # 使用消息处理器同时处理Console输出和逻辑判断
    processor = MessageProcessor(0)
    await Console(processor.process_messages(run_team(build_args)))
    return processor

async def run_build_first(project, session_id):
    
    """
    执行项目构建，包含5次迭代逻辑
    每次迭代执行两个智能体：deep_research（生成指南）和 cpp_build_engineer（执行构建）
    """
    print(f"=== 开始执行项目构建迭代: {project} ===")
    research_task = (
        f"# Task: Generate Comprehensive Build Guide for {project}\n\n"
        f"## Objective\n"
        f"Create a detailed compilation and installation guide specifically tailored for this operating system environment.\n\n"
        f"## Research Scope\n"
        f"1. **Documentation Analysis**: Thoroughly examine project documentation in {project}_doc/, doc/, README, INSTALL, COMPILE files\n"
        f"2. **Online Resources**: Search for experience blogs, tutorials, and community solutions for compile or build issues\n"
        f"3. **Build System Investigation**: Analyze what build system this {project} uses from docs or community best practices for ubuntu 22.04 \n"
        f"4. **Dependency Analysis**: Identify all required libraries, tools, and system dependencies from build/readme docs or configure file\n\n"
        f"## Deliverable\n"
        f"Generate a comprehensive BUILD.md file in the project root directory (/root/project/) containing:\n"
        f"- Step-by-step compilation instructions for ubuntu\n"
        f"- Dependency installation commands\n"
        f"- Build configuration options\n"
        f"- Troubleshooting common issues\n"
        f"- Verification steps for successful build\n\n"
        f"## Important Notes\n"
        f"- **Check first**: If BUILD.md already exists, skip this task\n"
        f"- **Focus**: Generate guide only, do NOT execute compilation\n"
        f"- **Target**: Ensure compatibility with current operating system\n"
        f"- **Quality**: Provide actionable, tested instructions"
    )
    await run_deep_researcher(project, session_id, research_task)
    print(f"✅ 构建编译指南完成")
    
    # 等待一段时间，确保文件系统同步
    print("等待10秒，确保研究结果同步...")
    time.sleep(10)

    # 第二步：执行 cpp_build_engineer 智能体
    print(f"\n--- 步骤 2: 执行构建工程师智能体  ---")

    build_task = (
        f"# Task: Execute C++ Project Compilation and Build\n\n"
        f"## Project Information\n"
        f"- **Location**: /root/project/\n"
        f"- **Build Guide**: BUILD.md (located in project root directory)\n\n"
        f"## Objective\n"
        f"Complete the compilation and build process for this C++ project from source code, following the BUILD.md guide that has been generated for this system environment.\n\n"
        f"## Core Build Principles\n"
        f"1. **System-Native Tools Priority**:\n"
        f"   - Prioritize system-native compiler versions (gcc/clang)\n"
        f"   - Use system-provided standard library versions\n"
        f"   - Prefer system package manager for third-party libraries\n\n"
        f"2. **Environment-First Approach**:\n"
        f"   - This is a mature, well-established codebase\n"
        f"   - Focus on resolving issues through system environment adjustments\n"
        f"   - Adjust build configurations and dependency versions as needed\n"
        f"   - **Avoid source code modifications** whenever possible\n\n"
        f"## Execution Strategy\n"
        f"1. Follow the BUILD.md guide step-by-step\n"
        f"2. Resolve dependency issues through package management\n"
        f"3. Configure build parameters for system compatibility\n"
        f"4. Handle compilation errors through environment optimization\n"
        f"5. Verify successful build completion\n\n"
        f"## Expected Deliverables\n"
        f"- Successfully compiled binaries\n"
        f"- Functional build environment\n"
        f"- Documentation of any environment-specific adjustments made"
    )

    processor = await run_cpp_builder(project, session_id, build_task)
    return processor
    

async def run_build_iter(project, session_id):
    summary = await builder_history_summary(project)

    print(f"=== 开始执行项目构建迭代: {project} ===")
    
    task = '''**Primary Objective**: Establish a complete C++ development environment through source code compilation and build.

**Project Details**:
- **Location**: /root/project/
- **Target**: System-compatible build environment
- **Approach**: Source code compilation with system integration

**Core Build Principles**:
1. **System-Native Tool Priority**:
   - Utilize system-native compiler versions (gcc/clang)
   - Leverage system-provided standard libraries
   - Prefer system package managers for third-party dependencies

2. **Environment-First Strategy**:
   - Treat this as a mature, production-ready codebase
   - Resolve issues through system environment optimization
   - Adjust build configurations and dependency versions strategically
   - **Minimize source code modifications** to preserve codebase integrity'''

    research_task = (
        f"# Task: Strategic Analysis and Recommendations for cpp_builder\n\n"
        f"## Context Overview\n"
        f"You are acting as a **deep_researcher** to provide recommendations for the cpp_builder agent.\n\n"
        f"## cpp_builder Agent Objectives\n"
        f"{task}\n\n"
        f"## cpp_builder Current Work Summary\n"
        f"```\n{summary}\n```\n\n"
        f"## Research Mission & Analysis Framework\n"
        f"Provide actionable recommendations for cpp_builder's current challenges through systematic analysis:\n\n"
        f"1. **Current Strategy Assessment**\n"
        f"   - Evaluate current build approach effectiveness and feasibility\n"
        f"   - Identify successful patterns and problematic failure points\n"
        f"2. **Problem-Specific Recommendations**\n"
        f"   - Address specific compilation errors and build failures\n"
        f"   - Provide systematic troubleshooting and resolution strategies\n"
        f"   - Recommend environment-specific optimizations\n\n"
        f"## Deliverable\n"
        f"Comprehensive analysis report with actionable recommendations that enable cpp_builder to overcome current obstacles and achieve successful project compilation.\n\n"
        f"## Important Reminder\n"
        f"**Your role is advisory only** - provide recommendations, do NOT execute compilation or build tasks directly."
    )

    processor = await run_deep_researcher(project, session_id, research_task)
    proposal = await deep_researcher_proposal(project, session_id)

    print(f"✅ 建议获取完成")
    build_task = f'Objective: {task}\n Regarding the current build issues, recommendations are as follows:\n{proposal}\n Continue to complete the source code compilation and build based on these recommendations.'
    processor = await run_cpp_builder(project, session_id, build_task)
    return processor.build_completed


async def run_build(project, session_id):
    docs = await download_history(project, session_id)

    if len(docs)==0:
        completed = await run_build_first(project, session_id)
        if completed:
            return True
    for i in range(3):
        completed = await run_build_iter(project, session_id)
        if completed:
            return True
    return False

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
            build_success = await run_build(project, session_id=str(uuid.uuid4()))
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
        build_success = await run_build(project_name, session_id=str(uuid.uuid4()))
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
    load_dotenv()  # 加载环境变量
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
    if len(sys.argv) == 2:
        project_name = sys.argv[1]
        asyncio.run(build_single_project(project_name))    
    elif len(sys.argv) > 2:
        start = int(sys.argv[1])
        end = int(sys.argv[2])
        selected_projects = projects[start-1:end]
        print(f"构建项目范围: {start} 到 {end}, 共 {len(selected_projects)} 个项目")
        asyncio.run(build_all(selected_projects))
    else:
        print("构建所有项目")
        asyncio.run(build_all(projects))