# 通用任务安排器（vivia_V4）

本项目旨在实现一个可扩展的通用任务安排器。底层采用 OR-Tools 的 CP-SAT 求解器（简称 cp_solver），所有任务都会被翻译为 cp 变量与 cp 模型支持的约束组合，从而进行全局求解与优化。

## 架构概览
- 时间建模：以 `AwareDatetime` 和 `TimeDelta` 表示时间点与时长，通过统一的区间校验混入 `IntervalValidationMixin` 进行合法性验证（`templates.py:80`）。
- 基础单位：`ScheduleInterval` 封装“实际时间区间”和“CP 模型变量”的双向转换，是调度的最小粒度实体（`templates.py:80-159`）。
- 容器与约束：为任务集合提供容器与约束接口，便于批量生成区间、聚合约束以及计算有效调度范围（`templates.py:160-176`）。
- 任务模板：提供“固定日期任务”和“固定周期任务”两类模板，自动生成待调度的 `ScheduleInterval` 列表（`templates.py:193-322`）。

## ScheduleInterval 功能说明
`ScheduleInterval` 是调度器的基础单位，围绕“真实区间”与“CP 变量”提供如下能力（字段均以 `字段名::类型名` 标注）：

- 元数据与标识（`templates.py:82-89`）
  - `name::str`
  - `mandatory::bool`
  - `priority::int`
  - `id::uuid.UUID`
  - `_source_task_id::uuid.UUID | None`

- 区间定义（来自 `IntervalValidationMixin[AwareDatetime, TimeDelta]`）
  - `start_interval::tuple[AwareDatetime, AwareDatetime]`
  - `end_interval::tuple[AwareDatetime, AwareDatetime]`
  - `duration_interval::tuple[TimeDelta, TimeDelta]`

- 真实区间封装 RealInterval（`templates.py:13-41`）
  - `start::AwareDatetime | None`
  - `end::AwareDatetime | None`
  - `duration::TimeDelta | None`
  - 说明：设置了 `start/end` 时自动计算 `duration`，并校验非负；提供 `set_interval`/`clear_interval` 以安全更新或重置。

- CP 模型变量封装 CPModelVariables（`templates.py:43-78`）
  - `start::cp_model.IntVar | None`
  - `end::cp_model.IntVar | None`
  - `presence::cp_model.IntVar | None`
  - `interval::cp_model.IntervalVar | None`
  - 说明：保持一致性（全部为 `None` 或全部存在），并进行类型校验。

- CP 变量创建（离散化与约束注入，`templates.py:91-137`）
  - 方法签名：`create_cp_model_vars(model::cp_model.CpModel, schedule_start::AwareDatetime, schedule_end::AwareDatetime, unit_length::TimeDelta) -> CPModelVariables`
  - 区间校验：要求区间完全包含在总体调度域内，否则报错。
  - 时间离散化策略：左边界上取整、右边界下取整；时长在必要时收缩以避免越界。
  - 变量创建：`start/end/duration::cp_model.IntVar`、`presence::BoolVar`（可选区间 `interval::cp_model.IntervalVar`）。
  - 强制约束：`mandatory==True` 时强制 `presence == 1`。

- 求解结果解释（反向映射，`templates.py:148-159`）
  - 方法签名：`interprete_cp_model_vars(cp_solver::cp_model.CpSolver, schedule_start::AwareDatetime, schedule_end::AwareDatetime, unit_length::TimeDelta) -> RealInterval`
  - 将离散单位转换回实际 `datetime` 并更新 `actual_interval`。

## 容器与约束接口
- `constraint` 抽象类（`templates.py:160-163`）
  - 方法签名：`apply_constraint2cp_model(model::cp_model.CpModel) -> None`

- `Interval_List`（`templates.py:168-176`）
  - `intervals::list[ScheduleInterval]`
  - `constraints::list[constraint]`
  - 属性：`effective_interval::tuple[AwareDatetime, AwareDatetime]`

- `Interval_List_Timestamped`（`templates.py:178-180`）
  - `time_stamp::AwareDatetime`

## 任务模板
- ExactDateTask（固定日期任务，`templates.py:193-221`）
  - `template_type::Literal["exact_date"]`
  - `name::str`
  - `mandatory::bool`
  - `priority::int`
  - `id::uuid.UUID`
  - `repeatition::int`
  - `container::Interval_List`
  - 继承区间定义：`start_interval::tuple[AwareDatetime, AwareDatetime]`、`end_interval::tuple[AwareDatetime, AwareDatetime]`、`duration_interval::tuple[TimeDelta, TimeDelta]`
  - 属性：`effective_interval::tuple[AwareDatetime, AwareDatetime]`
  - 方法：`get_intervals(start::AwareDatetime, end::AwareDatetime) -> list[ScheduleInterval]`

- RelativePeriodItem（相对周期条目，`templates.py:223-227`）
  - `active_index::int`
  - 继承区间定义：`start_interval::tuple[TimeDelta, TimeDelta]`、`end_interval::tuple[TimeDelta, TimeDelta]`、`duration_interval::tuple[TimeDelta, TimeDelta]`

- FixedPeriodTask（固定周期任务，`templates.py:228-322`）
  - `template_type::Literal["fixed_period"]`
  - `name::str`
  - `mandatory::bool`
  - `priority::int`
  - `id::uuid.UUID`
  - `period_unit_len::TimeDelta`
  - `period_unit_num::int`
  - `anchor_date::AwareDatetime`
  - `effective_interval::tuple[AwareDatetime, AwareDatetime]`
  - `period_items::list[RelativePeriodItem]`
  - `container::list[Interval_List_Timestamped]`
  - 私有字段：`_offset_lb::TimeDelta`、`_offset_rb::TimeDelta`、`_period::Period`
  - 属性：`period_len::TimeDelta`、`datetime_stamps::list[AwareDatetime]`
  - 方法：`get_intervals(start::AwareDatetime, end::AwareDatetime) -> list[ScheduleInterval]`

## 使用流程（示意）
1. 选择并实例化任务模板（固定日期/固定周期），得到一组待调度的 `ScheduleInterval`。
2. 设定整体调度域 `schedule_start/schedule_end` 与离散单位 `unit_length`（时间精度与模型规模的折中）。
3. 遍历每个 `ScheduleInterval`，调用 `create_cp_model_vars(...)` 将区间映射为 CP 变量，并注入必要的强制约束。
4. 根据业务需要实现并调用约束接口 `apply_constraint2cp_model(...)`，添加冲突、资源容量、顺序依赖等约束。
5. 运行 cp_solver 求解；随后调用 `interprete_cp_model_vars(...)` 将解反映到 `actual_interval`（实际时间）。

## 时间离散化策略说明
- 左开右收缩：左边界向上取整、右边界向下取整；若离散后不合法，则优先向右“进一”确保可用区间（`templates.py:111-118`）。
- 持续时间收缩：仅在必要时缩小，保持与边界一致，避免越界（`templates.py:121-123`）。
- 影响：单位越小，精度越高但变量与约束数量增加，应结合性能与精度需求选择。

## 扩展建议
- 目标设计：基于 `priority` 构建加权目标，最大化已安排任务数量或最小化加权延迟。
- 约束库：
  - 互斥/冲突（同时间资源唯一性）、前后依赖（precedence）、容量上限、时间窗口偏好等。
- 诊断与弹性：无解时输出冲突集或提供放松策略（如允许少量越窗或延迟）。
- 可视化与导出：将求解结果转为甘特图/时序表，或导出为 CSV/JSON。

## 相关文件
- `templates.py`：核心模型与模板定义（`ScheduleInterval`、容器、任务模板）。
- `model_definitions.py`：`IntervalValidationMixin`、`TimeDelta` 等基础类型与校验。
- `utils.py`：`IntervalUtil`、`Period` 等时间工具。
- `validators.py`：`ensure_all_or_none`、`validate_field_types` 等校验工具。

> 提示：当前代码中对 OR-Tools 的具体 API 调用以概念为主，实际项目中应依据 OR-Tools 版本确认具体方法名与调用方式，并统一在模型层封装。`cp_model.*` 类型在文档中用于说明强类型字段：`CpModel`、`CpSolver`、`IntVar`、`IntervalVar`、`BoolVar`。