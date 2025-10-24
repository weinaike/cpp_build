#!/usr/bin/env python3
"""
check_markdown.py - 构建指南检查脚本

该脚本使用 OpenAI GPT-4o 模型来分析项目构建指南文档，
判断项目构建是否成功。构建成功的条件是构建和测试都正常通过。
如果存在遗留问题，如部分未编译通过、缺少依赖库或函数等，则认为构建不成功。

作者: AI Assistant
日期: 2024-09-24
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
try:
    from openai import OpenAI
except ImportError:
    print("错误: 需要安装 openai 库")
    print("请运行: pip install openai")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('check_markdown.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    """构建结果数据类"""
    project_name: str
    is_successful: bool
    confidence_score: float  # 置信度 0-1
    summary: str
    details: str
    issues: List[str]
    success_indicators: List[str]
    file_path: str


class MarkdownChecker:
    """Markdown构建指南检查器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化检查器"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = os.getenv('API_BASE_URL', 'http://localhost:4141/')
        if not self.api_key:
            raise ValueError("需要设置 OPENAI_API_KEY 环境变量或传入 API 密钥")
        
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.logs_dir = Path("/home/wnk/code/wr124/cpp_build_new/cc_sdk/logs_glm4.6")
        self.projects_file = Path("/home/wnk/code/wr124/cpp_build_new/cc_sdk/projects_hard.txt")
        
        # 系统提示词
        self.system_prompt = """你是一个专业的C/C++项目构建分析专家。你的任务是分析项目构建指南文档，判断项目是否构建成功。

构建成功的判断标准：
1. 编译过程完全完成，生成了可执行文件或库文件
2. 所有测试用例通过（如果有测试）
3. 没有未解决的致命错误或链接问题
4. 核心功能能够正常工作

构建失败的判断标准：
1. 编译过程中断或失败
2. 测试用例失败
3. 存在未解决的依赖缺失问题
4. 关键组件无法构建
5. 存在严重的运行时错误

请基于以下格式返回JSON响应：
{
    "is_successful": boolean,
    "confidence_score": float (0-1),
    "summary": "简短的构建结果总结",
    "details": "详细的分析说明",
    "issues": ["问题列表"],
    "success_indicators": ["成功指标列表"]
}
"""

    def load_projects(self) -> List[str]:
        """加载项目列表"""
        try:
            with open(self.projects_file, 'r', encoding='utf-8') as f:
                projects = [line.strip() for line in f if line.strip()]
            logger.info(f"加载了 {len(projects)} 个项目")
            return projects
        except Exception as e:
            logger.error(f"加载项目列表失败: {e}")
            return []

    def find_build_guide(self, project_name: str) -> Optional[Path]:
        """查找项目的构建指南文件"""
        possible_files = [
            f"{project_name}_build_guide.md",
            f"{project_name}.md",
            f"{project_name}_guide.md"
        ]
        
        for filename in possible_files:
            file_path = self.logs_dir / filename
            if file_path.exists():
                return file_path
        
        return None

    def read_markdown_content(self, file_path: Path) -> str:
        """读取 Markdown 文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"读取文件 {file_path} 失败: {e}")
            return ""

    def analyze_build_guide(self, project_name: str, content: str) -> Dict:
        """使用 GPT-4o 分析构建指南"""
        try:
            user_prompt = f"""请分析以下 {project_name} 项目的构建指南文档内容，判断构建是否成功：

文档内容：
```markdown
{content}
```

请仔细分析文档中的关键信息：
- 构建过程的完成情况
- 测试结果
- 是否生成了可执行文件
- 是否存在未解决的问题
- 构建的完整性

请返回 JSON 格式的分析结果。"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            if result_text is None:
                logger.error("API 返回的内容为空")
                return self._create_error_result("API返回内容为空")
            
            result_text = result_text.strip()
            
            # 尝试解析 JSON
            try:
                # 去除可能的 markdown 代码块标记
                if result_text.startswith('```json'):
                    result_text = result_text[7:]
                if result_text.startswith('```'):
                    result_text = result_text[3:]
                if result_text.endswith('```'):
                    result_text = result_text[:-3]
                
                result = json.loads(result_text.strip())
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败: {e}")
                logger.error(f"原始响应: {result_text}")
                return self._create_error_result("JSON解析失败")
                
        except Exception as e:
            logger.error(f"API 调用失败: {e}")
            return self._create_error_result(f"API调用失败: {str(e)}")

    def _create_error_result(self, error_msg: str) -> Dict:
        """创建错误结果"""
        return {
            "is_successful": False,
            "confidence_score": 0.0,
            "summary": f"分析失败: {error_msg}",
            "details": error_msg,
            "issues": [error_msg],
            "success_indicators": []
        }

    def check_single_project(self, project_name: str) -> Optional[BuildResult]:
        """检查单个项目"""
        logger.info(f"检查项目: {project_name}")
        
        # 查找构建指南文件
        guide_file = self.find_build_guide(project_name)
        if not guide_file:
            logger.warning(f"未找到 {project_name} 的构建指南文件")
            return None
        
        # 读取文件内容
        content = self.read_markdown_content(guide_file)
        if not content:
            logger.warning(f"文件 {guide_file} 内容为空")
            return None
        
        # 使用 GPT-4o 分析
        analysis = self.analyze_build_guide(project_name, content)
        
        # 创建结果对象
        result = BuildResult(
            project_name=project_name,
            is_successful=analysis.get('is_successful', False),
            confidence_score=analysis.get('confidence_score', 0.0),
            summary=analysis.get('summary', ''),
            details=analysis.get('details', ''),
            issues=analysis.get('issues', []),
            success_indicators=analysis.get('success_indicators', []),
            file_path=str(guide_file)
        )
        
        return result

    def check_all_projects(self, project_filter: Optional[List[str]] = None) -> List[BuildResult]:
        """检查所有项目或指定项目"""
        projects = self.load_projects()
        
        if project_filter:
            projects = [p for p in projects if p in project_filter]
            
        results = []
        total = len(projects)
        
        for i, project in enumerate(projects, 1):
            logger.info(f"进度: {i}/{total} - 检查 {project}")
            
            try:
                result = self.check_single_project(project)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"检查项目 {project} 时出错: {e}")
                continue
        
        return results

    def generate_report(self, results: List[BuildResult], output_file: str = "build_check_report.md"):
        """生成检查报告"""
        if not results:
            logger.warning("没有结果可生成报告")
            return
        
        # 统计数据
        successful = [r for r in results if r.is_successful]
        failed = [r for r in results if not r.is_successful]
        success_rate = len(successful) / len(results) * 100 if results else 0
        
        # 生成报告
        report = []
        report.append("# 项目构建检查报告")
        report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"检查项目总数: {len(results)}")
        report.append(f"构建成功: {len(successful)} 个")
        report.append(f"构建失败: {len(failed)} 个")
        report.append(f"成功率: {success_rate:.1f}%")
        
        # 成功项目列表
        if successful:
            report.append("\n## ✅ 构建成功的项目")
            for result in sorted(successful, key=lambda x: x.confidence_score, reverse=True):
                report.append(f"\n### {result.project_name}")
                report.append(f"**置信度**: {result.confidence_score:.2f}")
                report.append(f"**总结**: {result.summary}")
                if result.success_indicators:
                    report.append("**成功指标**:")
                    for indicator in result.success_indicators:
                        report.append(f"- {indicator}")
        
        # 失败项目列表
        if failed:
            report.append("\n## ❌ 构建失败的项目")
            for result in sorted(failed, key=lambda x: x.confidence_score, reverse=True):
                report.append(f"\n### {result.project_name}")
                report.append(f"**置信度**: {result.confidence_score:.2f}")
                report.append(f"**总结**: {result.summary}")
                if result.issues:
                    report.append("**存在问题**:")
                    for issue in result.issues:
                        report.append(f"- {issue}")
        
        # 详细结果
        report.append("\n## 📊 详细分析结果")
        for result in results:
            status = "✅ 成功" if result.is_successful else "❌ 失败"
            report.append(f"\n### {result.project_name} {status}")
            report.append(f"**文件路径**: `{result.file_path}`")
            report.append(f"**置信度**: {result.confidence_score:.2f}")
            report.append(f"**详细分析**: {result.details}")
        
        # 写入文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report))
            logger.info(f"报告已生成: {output_file}")
        except Exception as e:
            logger.error(f"生成报告失败: {e}")

    def generate_json_report(self, results: List[BuildResult], output_file: str = "build_check_report.json"):
        """生成 JSON 格式报告"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_projects": len(results),
            "successful_count": len([r for r in results if r.is_successful]),
            "failed_count": len([r for r in results if not r.is_successful]),
            "success_rate": len([r for r in results if r.is_successful]) / len(results) * 100 if results else 0,
            "results": [
                {
                    "project_name": r.project_name,
                    "is_successful": r.is_successful,
                    "confidence_score": r.confidence_score,
                    "summary": r.summary,
                    "details": r.details,
                    "issues": r.issues,
                    "success_indicators": r.success_indicators,
                    "file_path": r.file_path
                }
                for r in results
            ]
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"JSON 报告已生成: {output_file}")
        except Exception as e:
            logger.error(f"生成 JSON 报告失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="检查项目构建指南文档")
    parser.add_argument("--projects", "-p", nargs="+", help="指定要检查的项目名称")
    parser.add_argument("--output", "-o", default="build_check_report", help="输出报告文件前缀")
    parser.add_argument("--api-key", help="OpenAI API 密钥")
    parser.add_argument("--json-only", action="store_true", help="仅生成 JSON 报告")
    parser.add_argument("--list-projects", action="store_true", help="列出所有可用项目")
    
    args = parser.parse_args()
    
    try:
        checker = MarkdownChecker(api_key=args.api_key)
        
        if args.list_projects:
            projects = checker.load_projects()
            print("可用项目列表:")
            for project in projects:
                guide_file = checker.find_build_guide(project)
                status = "✅" if guide_file else "❌"
                print(f"  {status} {project}")
            return
        
        # 检查项目
        results = checker.check_all_projects(args.projects)
        
        if not results:
            logger.error("没有找到可检查的项目")
            return
        
        # 生成报告
        if not args.json_only:
            checker.generate_report(results, f"{args.output}.md")
        checker.generate_json_report(results, f"{args.output}.json")
        
        # 打印统计信息
        successful = len([r for r in results if r.is_successful])
        total = len(results)
        success_rate = successful / total * 100 if total > 0 else 0
        
        print(f"\n检查完成!")
        print(f"总项目数: {total}")
        print(f"成功: {successful} 个")
        print(f"失败: {total - successful} 个")
        print(f"成功率: {success_rate:.1f}%")
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    load_dotenv()
    main()