#!/bin/bash

# 使用说明函数
usage() {
    echo "用法: $0 [参数]"
    echo "  无参数: 执行所有项目"
    echo "  单参数: $0 <数字> - 执行指定序号的项目"
    echo "  双参数: $0 <开始序号> <结束序号> - 执行指定范围内的项目"
    echo "  项目序号从1开始"
    echo "  特殊选项: $0 --list 或 $0 -l - 显示所有项目列表及序号"
    exit 1
}

# 显示项目列表函数
show_project_list() {
    echo "项目列表 (共 $total_projects 个项目):"
    echo "----------------------------------------"
    for ((i=0; i<total_projects; i++)); do
        printf "%3d. %s\n" $((i+1)) "${filtered_projects[$i]}"
    done
    echo "----------------------------------------"
    exit 0
}

# 读取项目列表文件
PROJECTS_FILE="projects.txt"
BASE_DIR="/home/wnk/cc_projects"
OUTPUT_DIR="/home/wnk/cc_sdk/logs"

# 检查projects.txt文件是否存在
if [[ ! -f "$PROJECTS_FILE" ]]; then
    echo "错误: 项目列表文件 $PROJECTS_FILE 不存在"
    exit 1
fi

# 读取所有项目到数组中
mapfile -t projects < "$PROJECTS_FILE"

# 过滤掉空行
filtered_projects=()
for project in "${projects[@]}"; do
    if [[ -n "$project" ]]; then
        filtered_projects+=("$project")
    fi
done

total_projects=${#filtered_projects[@]}

# 检查是否是显示列表的请求
if [[ "$1" == "--list" ]] || [[ "$1" == "-l" ]]; then
    show_project_list
fi

# 解析命令行参数
start_index=1
end_index=$total_projects

case $# in
    0)
        # 无参数：执行所有项目
        echo "执行模式: 处理所有项目 (共 $total_projects 个)"
        ;;
    1)
        # 单参数：执行指定序号的项目
        if ! [[ "$1" =~ ^[0-9]+$ ]] || [[ $1 -lt 1 ]] || [[ $1 -gt $total_projects ]]; then
            echo "错误: 项目序号必须是 1 到 $total_projects 之间的数字"
            usage
        fi
        start_index=$1
        end_index=$1
        echo "执行模式: 处理第 $1 个项目 (${filtered_projects[$((start_index-1))]})"
        ;;
    2)
        # 双参数：执行指定范围的项目
        if ! [[ "$1" =~ ^[0-9]+$ ]] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
            echo "错误: 参数必须是数字"
            usage
        fi
        if [[ $1 -lt 1 ]] || [[ $1 -gt $total_projects ]] || [[ $2 -lt 1 ]] || [[ $2 -gt $total_projects ]]; then
            echo "错误: 项目序号必须是 1 到 $total_projects 之间的数字"
            usage
        fi
        if [[ $1 -gt $2 ]]; then
            echo "错误: 开始序号不能大于结束序号"
            usage
        fi
        start_index=$1
        end_index=$2
        echo "执行模式: 处理第 $1 到第 $2 个项目"
        ;;
    *)
        echo "错误: 参数数量不正确"
        usage
        ;;
esac

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 生成带时间标签的日志文件名
timestamp=$(date +"%Y%m%d_%H%M%S")
process_log_file="$OUTPUT_DIR/process_log_${timestamp}.txt"

# 记录总体开始时间
total_start_time=$(date +%s)
echo "开始处理项目列表，时间：$(date)" | tee "$process_log_file"
echo "处理项目范围: 第 $start_index 到第 $end_index 个项目" | tee -a "$process_log_file"

# 处理指定范围的项目
for ((i=start_index-1; i<end_index; i++)); do
    project="${filtered_projects[$i]}"
    project_number=$((i+1))
    
    # 记录项目开始时间
    project_start_time=$(date +%s)
    echo "正在处理项目 [$project_number/$total_projects]: $project" | tee -a "$process_log_file"
    echo "项目 $project 开始时间：$(date)" | tee -a "$process_log_file"
    
    # 执行claude命令并将输出重定向到文件
    output_file="$OUTPUT_DIR/${project}_build_guide.md"

    # 检查输出文件是否已存在
    if [[ -f "$output_file" ]]; then
        echo "项目 $project 的输出文件已存在，跳过处理: $output_file" | tee -a "$process_log_file"
        echo "----------------------------------------" | tee -a "$process_log_file"
        continue
    fi

    # 切换到项目目录
    project_dir="$BASE_DIR/$project"
    if [[ -d "$project_dir" ]]; then
        cd "$project_dir"
        echo "已切换到目录: $project_dir" | tee -a "$process_log_file"

        # 检查是否为git仓库并重置到初始状态
        if [[ -d ".git" ]]; then
            echo "检测到git仓库，正在重置到初始状态..." | tee -a "$process_log_file"
            
            # 重置所有更改到HEAD
            git reset --hard HEAD 2>&1 | tee -a "$process_log_file"
            if [[ $? -eq 0 ]]; then
                echo "git reset --hard HEAD 执行成功" | tee -a "$process_log_file"
            else
                echo "警告: git reset 执行失败" | tee -a "$process_log_file"
            fi
            
            # 清理未跟踪的文件和目录
            git clean -fd 2>&1 | tee -a "$process_log_file"
            if [[ $? -eq 0 ]]; then
                echo "git clean -fd 执行成功" | tee -a "$process_log_file"
            else
                echo "警告: git clean 执行失败" | tee -a "$process_log_file"
            fi
        else
            echo "当前目录不是git仓库，跳过git重置操作" | tee -a "$process_log_file"
        fi
        

        echo "开始为项目 $project 生成构建指南..." | tee -a "$process_log_file"
        
        claude "1.查找资料编写适合于本操作系统的基于源码的编译构建指南2.基于指南分步开展具体的编译构建，包括依赖库安装、源码编译、编译结果验证，直到确认构建成功" \
            --permission-mode bypassPermissions \
            -p \
            --output-format text \
            --dangerously-skip-permissions > "$output_file" 2>&1
        
        if [[ $? -eq 0 ]]; then
            echo "项目 $project 处理完成，输出保存到: $output_file" | tee -a "$process_log_file"
        else
            echo "项目 $project 处理失败" | tee -a "$process_log_file"
        fi
    else
        echo "警告: 项目目录不存在: $project_dir" | tee -a "$process_log_file"
    fi
    
    # 记录项目结束时间并计算执行时间
    project_end_time=$(date +%s)
    project_duration=$((project_end_time - project_start_time))
    echo "项目 $project 结束时间：$(date)" | tee -a "$process_log_file"
    echo "项目 $project 执行时长：$project_duration 秒 ($(echo "scale=2; $project_duration/60" | bc 2>/dev/null || echo "$project_duration/60") 分钟)" | tee -a "$process_log_file"
    
    echo "----------------------------------------" | tee -a "$process_log_file"
    
done

# 计算总体执行时间
total_end_time=$(date +%s)
total_duration=$((total_end_time - total_start_time))
echo "所有项目处理完成，时间：$(date)" | tee -a "$process_log_file"
echo "总体执行时长：$total_duration 秒 ($(echo "scale=2; $total_duration/60" | bc 2>/dev/null || echo "$total_duration/60") 分钟)" | tee -a "$process_log_file" 