完美！让我做一个最终的总结：

## xtd 源码编译构建完成！

我已成功完成了以下任务：

### 1. ✅ 分析项目结构和现有构建配置
- xtd 是一个现代C++20框架，支持控制台、GUI和单元测试应用
- 使用CMake构建系统，依赖wxWidgets 3.2+
- 项目包含核心库(xtd.core)、绘图库(xtd.drawing)、窗体库(xtd.forms)和单元测试库(xtd.tunit)

### 2. ✅ 查找现有构建文档和脚本
- 发现了现有的安装脚本 `scripts/install/install.sh`
- 分析了CMakeLists.txt配置文件
- 了解了项目的构建选项和依赖关系

### 3. ✅ 编写适合Linux系统的源码编译构建指南
- 创建了详细的 `BUILD_GUIDE_LINUX.md` 文档
- 包含系统要求、依赖安装、编译步骤、验证方法等
- 提供了故障排除和性能优化建议

### 4. ✅ 安装依赖库
- 系统已安装所有必需的依赖：build-essential、cmake、doxygen、libasound2-dev、libgsound-dev、libgtk-3-dev
- wxWidgets 3.2.2 已正确安装

### 5. ✅ 编译源码
- 配置了Release版本构建
- 成功编译了所有组件：xtd.core、xtd.drawing、xtd.forms、xtd.tunit
- 编译了工具：xtdc、xtdc-gui、guidgen、keycodes等

### 6. ✅ 验证编译结果
- 成功安装到 `/usr/local/` 目录
- 头文件、库文件和工具都正确安装
- 创建并运行了测试程序，成功输出 "Hello, World!"
- 验证了xtdc命令行工具正常工作

### 构建成果总结：

**编译成功的组件：**
- xtd.core (核心库)
- xtd.drawing (绘图库) 
- xtd.forms (窗体库)
- xtd.tunit (单元测试库)
- 所有原生实现库
- 开发工具(xtdc、xtdc-gui等)

**安装位置：**
- 头文件：`/usr/local/include/xtd/`
- 库文件：`/usr/local/lib/libxtd*.a`
- 工具：`/usr/local/bin/xtdc*`
- 资源和示例：`/usr/local/share/xtd/`

**验证结果：**
- 测试程序成功编译和运行
- xtdc工具正常工作
- 环境变量已正确设置

xtd框架现在可以在您的Linux系统上正常使用，可以开始开发跨平台的C++应用程序了！
