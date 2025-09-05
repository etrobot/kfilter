# 因子选择功能实现总结

## 功能概述
实现了点击"运行"按钮时弹出Dialog，用户可以选择要计算的因子，确定后按选择的因子进行计算的功能。

## 实现的功能

### 1. 后端改进
- **新增模型**: `RunRequest` 支持传递选择的因子列表
- **扩展Task模型**: 添加 `selected_factors` 字段记录选择的因子
- **因子选择计算**: 新增 `compute_selected_factors` 函数支持选择性计算因子
- **API更新**: `/run` 接口现在接受 `RunRequest` 对象，支持因子选择

### 2. 前端新增组件
- **FactorSelectionDialog**: 因子选择对话框组件
  - 动态加载可用因子列表
  - 支持全选/全不选操作
  - 至少选择一个因子的验证
  - 显示因子描述信息

### 3. 界面重构
- **删除原运行按钮**: 移除了PageHeader中的原始运行按钮
- **新运行按钮**: 在ResultsTable顶部添加了带图标的运行按钮
- **Dialog集成**: 点击运行时弹出因子选择对话框
- **状态管理**: 运行状态显示和禁用逻辑
- **API调用**: 支持传递选择的因子到后端

## 技术实现细节

### 后端关键文件修改
1. `models.py`: 新增 `RunRequest` 模型，扩展 `Task` 和 `TaskResult`
2. `factors/__init__.py`: 新增 `compute_selected_factors` 函数
3. `data_processor.py`: `compute_factors` 函数支持选择性因子计算
4. `services.py`: 任务创建和执行支持因子选择
5. `api.py`: 更新API接口支持新的请求格式
6. `main.py`: 路由更新

### 前端关键文件修改
1. `types.ts`: 扩展 `TaskResult` 类型
2. `api.ts`: `startAnalysis` 方法支持因子选择参数
3. `FactorSelectionDialog.tsx`: 新增因子选择对话框组件
4. `ResultsTable.tsx`: 集成运行按钮和因子选择功能
5. `lib/utils.ts`: 添加样式工具函数

## 用户体验流程

1. **点击运行**: 用户点击ResultsTable顶部的"运行"按钮
2. **选择因子**: 弹出对话框显示所有可用因子，默认全选
3. **确认选择**: 用户可以取消选择某些因子，至少保留一个
4. **开始计算**: 点击确定后，后端按选择的因子进行计算
5. **显示结果**: 计算完成后更新表格显示

## API示例

### 获取因子列表
```bash
GET /factors
```

### 启动分析（选择特定因子）
```bash
POST /run
Content-Type: application/json

{
  "top_n": 100,
  "selected_factors": ["momentum", "support"]
}
```

### 启动分析（所有因子）
```bash
POST /run
Content-Type: application/json

{
  "top_n": 100
}
```

## 当前可用因子
- **momentum**: 动量因子 
- **support**: 支撑因子 

## 服务状态
- 后端服务: http://localhost:8000 ✅
- 前端服务: http://localhost:5173 ✅
- 因子API: http://localhost:8000/factors ✅

## 扩展性
该实现具有良好的扩展性：
- 新增因子只需在 `backend/factors/` 目录下添加新的因子模块
- 前端会自动识别和显示新的因子选项
- 支持因子的动态加载和选择