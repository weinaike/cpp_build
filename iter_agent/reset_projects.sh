#!/bin/bash

# 项目重置脚本 - Bash版本
# 对指定的项目目录执行 git reset --hard HEAD 命令

# 项目列表
projects=(
    "arangodb"
    "blender"
    "codelite"
    "codon"
    "foundationdb"
    "qt-creator"
    "rpcs3"
    "seq"
    "serenity"
    "shotcut"
    "treefrog-framework"
    "userver"
    "vireo"
    "wav2letter"
    "xtd"
)

# 项目基础目录
BASE_DIR="/media/wnk/projects"

# 统计变量
success_count=0
failed_count=0
skipped_count=0
total_count=${#projects[@]}

echo "开始重置项目，基础目录: $BASE_DIR"
echo "共有 $total_count 个项目需要处理"
echo "=================================================="

# 检查基础目录是否存在
if [ ! -d "$BASE_DIR" ]; then
    echo "❌ 错误: 基础目录 $BASE_DIR 不存在"
    exit 1
fi

# 逐个处理项目
for i in "${!projects[@]}"; do
    project="${projects[$i]}"
    project_path="$BASE_DIR/$project"
    current=$((i + 1))
    
    echo ""
    echo "[$current/$total_count] 正在处理项目: $project"
    echo "项目路径: $project_path"
    
    # 检查项目目录是否存在
    if [ ! -d "$project_path" ]; then
        echo "❌ 错误: 项目目录 $project_path 不存在"
        ((failed_count++))
        continue
    fi
    
    # 检查是否为git仓库
    if [ ! -d "$project_path/.git" ]; then
        echo "⚠️  警告: $project_path 不是Git仓库，跳过"
        ((skipped_count++))
        continue
    fi
    
    # 切换到项目目录并执行git reset
    cd "$project_path" || {
        echo "❌ 失败: 无法切换到目录 $project_path"
        ((failed_count++))
        continue
    }
    
    if git reset --hard HEAD; then
        echo "✅ 成功: $project 已重置"
        
        # 检查并添加对应的_docs目录
        docs_dir="${project}_docs"
        if [ -d "$docs_dir" ]; then
            echo "📁 发现 $docs_dir 目录，正在添加到git..."
            if git add "$docs_dir/"; then
                echo "✅ 成功添加 $docs_dir/ 到git"
            else
                echo "❌ 添加 $docs_dir/ 失败"
            fi
        else
            echo "ℹ️  未找到 $docs_dir 目录"
        fi
        git clean -fd
        ((success_count++))
    else
        echo "❌ 失败: $project 重置失败"
        ((failed_count++))
    fi
done

# 输出统计结果
echo ""
echo "=================================================="
echo "执行完成！统计结果:"
echo "✅ 成功: $success_count 个项目"
echo "❌ 失败: $failed_count 个项目"
echo "⚠️  跳过: $skipped_count 个项目（非Git仓库）"
echo "📊 总计: $total_count 个项目"

# 如果有失败的项目，以非零状态码退出
if [ $failed_count -gt 0 ]; then
    exit 1
fi