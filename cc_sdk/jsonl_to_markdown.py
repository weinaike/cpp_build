#!/usr/bin/env python3
"""
JSONL到Markdown转换器
将JSONL文件中的聊天对话内容转换为易读的Markdown格式
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
import re


class JsonlToMarkdownConverter:
    def __init__(self):
        self.message_count = 0
        
    def format_timestamp(self, timestamp_str):
        """格式化时间戳"""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return timestamp_str
    
    def clean_text(self, text):
        """清理文本内容，处理特殊字符"""
        if not text:
            return ""
        # 转义Markdown特殊字符
        text = text.replace('\\', '\\\\')
        return text
    
    def format_message_content(self, content):
        """格式化消息内容"""
        if isinstance(content, str):
            return self.clean_text(content)
        elif isinstance(content, list):
            formatted_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        formatted_parts.append(self.clean_text(item.get('text', '')))
                    elif item.get('type') == 'tool_use':
                        tool_name = item.get('name', 'Unknown Tool')
                        tool_id = item.get('id', '')
                        input_data = item.get('input', {})
                        formatted_parts.append(f"\n**🔧 工具调用: {tool_name}**\n")
                        formatted_parts.append(f"- ID: `{tool_id}`\n")
                        if input_data:
                            formatted_parts.append("- 输入参数:")
                            formatted_parts.append(f"```json\n{json.dumps(input_data, indent=2, ensure_ascii=False)}\n```")
                    elif item.get('type') == 'tool_result':
                        tool_use_id = item.get('tool_use_id', '')
                        content = item.get('content', '')
                        is_error = item.get('is_error', False)
                        formatted_parts.append(f"\n**📤 工具结果** (ID: `{tool_use_id}`)\n")
                        if is_error:
                            formatted_parts.append("⚠️ **错误**:")
                        formatted_parts.append(f"```\n{content}\n```")
                else:
                    formatted_parts.append(str(item))
            return '\n'.join(formatted_parts)
        else:
            return str(content)
    
    def format_usage_info(self, usage):
        """格式化token使用信息"""
        if not usage:
            return ""
        
        info = []
        if 'input_tokens' in usage:
            info.append(f"输入: {usage['input_tokens']}")
        if 'output_tokens' in usage:
            info.append(f"输出: {usage['output_tokens']}")
        if 'cache_read_input_tokens' in usage:
            info.append(f"缓存读取: {usage['cache_read_input_tokens']}")
        
        return f"*Token使用: {', '.join(info)}*" if info else ""
    
    def format_tool_use_result(self, tool_result):
        """格式化工具使用结果"""
        if not tool_result:
            return ""
        
        parts = []
        if 'stdout' in tool_result:
            parts.append(f"**标准输出:**\n```\n{tool_result['stdout']}\n```")
        if 'stderr' in tool_result:
            parts.append(f"**标准错误:**\n```\n{tool_result['stderr']}\n```")
        if 'oldTodos' in tool_result or 'newTodos' in tool_result:
            parts.append("**Todo列表更新:**")
            if 'oldTodos' in tool_result:
                parts.append(f"- 旧项目数: {len(tool_result['oldTodos'])}")
            if 'newTodos' in tool_result:
                parts.append(f"- 新项目数: {len(tool_result['newTodos'])}")
        
        return '\n'.join(parts) if parts else ""
    
    def process_jsonl_file(self, input_file):
        """处理JSONL文件"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"错误: 无法读取文件 {input_file}: {e}")
            return None
        
        messages = []
        session_info = {}
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)
                messages.append(data)
                
                # 提取会话信息
                if not session_info:
                    session_info = {
                        'sessionId': data.get('sessionId', 'Unknown'),
                        'cwd': data.get('cwd', 'Unknown'),
                        'version': data.get('version', 'Unknown'),
                        'gitBranch': data.get('gitBranch', 'Unknown')
                    }
                    
            except json.JSONDecodeError as e:
                print(f"警告: 第{line_num}行JSON解析错误: {e}")
                continue
        
        return self.generate_markdown(messages, session_info)
    
    def generate_markdown(self, messages, session_info):
        """生成Markdown内容"""
        markdown_lines = []
        
        # 添加标题和会话信息
        markdown_lines.append("# 聊天对话记录\n")
        markdown_lines.append("## 会话信息\n")
        markdown_lines.append(f"- **会话ID**: `{session_info.get('sessionId', 'Unknown')}`")
        markdown_lines.append(f"- **工作目录**: `{session_info.get('cwd', 'Unknown')}`")
        markdown_lines.append(f"- **版本**: `{session_info.get('version', 'Unknown')}`")
        markdown_lines.append(f"- **Git分支**: `{session_info.get('gitBranch', 'Unknown')}`")
        markdown_lines.append("")
        
        # 统计信息
        user_messages = len([m for m in messages if m.get('type') == 'user'])
        assistant_messages = len([m for m in messages if m.get('type') == 'assistant'])
        markdown_lines.append("## 统计信息\n")
        markdown_lines.append(f"- **总消息数**: {len(messages)}")
        markdown_lines.append(f"- **用户消息**: {user_messages}")
        markdown_lines.append(f"- **助手消息**: {assistant_messages}")
        markdown_lines.append("")
        
        markdown_lines.append("---\n")
        markdown_lines.append("## 对话内容\n")
        
        # 处理每条消息
        for i, msg in enumerate(messages, 1):
            self.message_count += 1
            
            # 消息头部信息
            msg_type = msg.get('type', 'unknown')
            timestamp = self.format_timestamp(msg.get('timestamp', ''))
            uuid = msg.get('uuid', '')
            parent_uuid = msg.get('parentUuid', '')
            
            # 根据消息类型设置图标和标题
            if msg_type == 'user':
                icon = "👤"
                title = "用户"
            elif msg_type == 'assistant':
                icon = "🤖"
                title = "助手"
            else:
                icon = "❓"
                title = msg_type.capitalize()
            
            markdown_lines.append(f"### {icon} {title} #{i}")
            markdown_lines.append(f"**时间**: {timestamp}")
            markdown_lines.append(f"**UUID**: `{uuid}`")
            if parent_uuid:
                markdown_lines.append(f"**父UUID**: `{parent_uuid}`")
            
            # 处理消息内容
            message_data = msg.get('message', {})
            if message_data:
                role = message_data.get('role', '')
                content = message_data.get('content', '')
                
                if role:
                    markdown_lines.append(f"**角色**: {role}")
                
                # 处理AI模型信息
                if 'model' in message_data:
                    markdown_lines.append(f"**模型**: {message_data['model']}")
                
                # 处理消息内容
                if content:
                    markdown_lines.append("\n**内容**:")
                    formatted_content = self.format_message_content(content)
                    markdown_lines.append(formatted_content)
                
                # 处理使用统计
                usage = message_data.get('usage')
                if usage:
                    usage_info = self.format_usage_info(usage)
                    if usage_info:
                        markdown_lines.append(f"\n{usage_info}")
            
            # 处理工具使用结果
            tool_result = msg.get('toolUseResult')
            if tool_result:
                result_info = self.format_tool_use_result(tool_result)
                if result_info:
                    markdown_lines.append(f"\n**工具执行结果**:\n{result_info}")
            
            # 处理其他字段
            other_fields = {}
            for key, value in msg.items():
                if key not in ['type', 'timestamp', 'uuid', 'parentUuid', 'message', 'toolUseResult']:
                    other_fields[key] = value
            
            if other_fields:
                markdown_lines.append("\n**其他信息**:")
                for key, value in other_fields.items():
                    if isinstance(value, (dict, list)):
                        markdown_lines.append(f"- **{key}**: ```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```")
                    else:
                        markdown_lines.append(f"- **{key}**: `{value}`")
            
            markdown_lines.append("\n---\n")
        
        return '\n'.join(markdown_lines)


def main():
    parser = argparse.ArgumentParser(description='将JSONL文件转换为Markdown格式')
    parser.add_argument('input_file', help='输入的JSONL文件路径')
    parser.add_argument('-o', '--output', help='输出的Markdown文件路径 (默认: input_file.md)')
    parser.add_argument('--stdout', action='store_true', help='输出到标准输出而不是文件')
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"错误: 文件 {args.input_file} 不存在")
        return 1
    
    # 创建转换器实例
    converter = JsonlToMarkdownConverter()
    
    # 处理文件
    print(f"正在处理文件: {args.input_file}")
    markdown_content = converter.process_jsonl_file(args.input_file)
    
    if markdown_content is None:
        print("转换失败")
        return 1
    
    # 输出结果
    if args.stdout:
        print(markdown_content)
    else:
        output_file = args.output or f"{input_path.stem}.md"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"转换完成! 输出文件: {output_file}")
            print(f"处理了 {converter.message_count} 条消息")
        except Exception as e:
            print(f"错误: 无法写入文件 {output_file}: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())