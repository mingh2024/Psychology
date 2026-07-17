# 知识图谱数据更新说明

后续课程大纲、课程增删改、知识点映射或关系变化时，只维护项目里的 Excel 数据表，不需要直接改 `App.vue`。

## Excel 位置

默认读取项目内这份文件：

```text
data/副本心理学知识图谱项目数据底表_v2_full.xltx
```

领导后续更新时，保持文件名和位置不变即可。可以直接覆盖这份 Excel。

## 默认更新流程

1. 修改或替换 Excel：

   ```text
   data/副本心理学知识图谱项目数据底表_v2_full.xltx
   ```

2. 重新生成前端数据：

   ```bash
   npm run generate:data
   ```

3. 本地预览：

   ```bash
   npm run dev
   ```

4. 正式构建：

   ```bash
   npm run build
   ```

`npm run build` 已经会自动先执行 `npm run generate:data`，所以部署时会自动用最新 Excel 生成图谱数据。

## 如果 Excel 文件名或位置变了

可以临时传入新路径：

```bash
python3 scripts/generate_graph_data.py /你的新路径/心理学知识图谱项目数据底表.xlsx
```

## 自动生成结果

脚本会自动更新：

```text
src/data/graph-data.ts
```

这份文件是生成产物，不建议手动编辑。`App.vue` 只负责展示、布局和交互。
