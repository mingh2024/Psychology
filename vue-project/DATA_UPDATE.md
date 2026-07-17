# 知识图谱数据更新说明

后续课程大纲、课程增删改、知识点映射或关系变化时，优先维护 Excel 数据表，不需要直接改 `App.vue` 里的图谱代码。

## 默认更新流程

1. 修改 Excel：
   `/Users/lmh/Desktop/副本心理学知识图谱项目数据底表_v2_full.xltx`

2. 重新生成前端数据：

   ```bash
   npm run generate:data
   ```

3. 检查项目能否正常构建：

   ```bash
   npm run build
   ```

4. 本地预览：

   ```bash
   npm run dev
   ```

## 如果 Excel 文件换了位置

可以把新 Excel 路径传给脚本：

```bash
python3 scripts/generate_graph_data.py /你的新路径/心理学知识图谱项目数据底表.xlsx
```

## 生成结果

脚本会自动更新：

```text
src/data/graph-data.ts
```

`App.vue` 只负责展示、布局和交互，不再维护大段课程/关系数据。
