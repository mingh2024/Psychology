from pathlib import Path
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

DEFAULT_EXCEL = "/Users/lmh/Desktop/副本心理学知识图谱项目数据底表_v2_full.xltx"
OUTPUT = Path("src/data/graph-data.ts")
NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    value = 0
    for ch in letters:
        value = value * 26 + ord(ch.upper()) - ord("A") + 1
    return value - 1


def js_string(value: str) -> str:
    return repr(value).replace('"', '\\"')


def read_workbook(path: str) -> dict[str, list[list[str]]]:
    with zipfile.ZipFile(path) as workbook:
        shared_strings: list[str] = []
        shared_root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
        for item in shared_root.findall("a:si", NS):
            shared_strings.append("".join(text.text or "" for text in item.findall(".//a:t", NS)))

        def cell_value(cell: ET.Element) -> str:
            value = cell.find("a:v", NS)
            if value is None:
                return ""
            raw = value.text or ""
            if cell.attrib.get("t") == "s":
                return shared_strings[int(raw)]
            return raw

        workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
        rel_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        rels = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rel_root}

        sheets: dict[str, list[list[str]]] = {}
        for sheet in workbook_root.findall("a:sheets/a:sheet", NS):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = "xl/" + rels[rel_id]
            sheet_root = ET.fromstring(workbook.read(target))
            rows: list[list[str]] = []
            for row in sheet_root.findall(".//a:sheetData/a:row", NS):
                values: list[str] = []
                for cell in row.findall("a:c", NS):
                    index = col_index(cell.attrib.get("r", "A1"))
                    while len(values) <= index:
                        values.append("")
                    values[index] = cell_value(cell)
                if any(values):
                    rows.append(values)
            sheets[name] = rows
        return sheets


def records(rows: list[list[str]]) -> list[dict[str, str]]:
    headers = rows[0]
    output: list[dict[str, str]] = []
    for row in rows[1:]:
        item = {header: row[index] if index < len(row) else "" for index, header in enumerate(headers)}
        if any(item.values()):
            output.append(item)
    return output


def split_list(value: str) -> list[str]:
    value = value.strip()
    if not value or value == "无":
        return []
    return [part.strip() for part in re.split(r"[、,，;；]", value) if part.strip() and part.strip() != "无"]


def to_int(value: str) -> int:
    try:
        return int(float(value))
    except ValueError:
        return 0


def main() -> None:
    excel_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXCEL
    sheets = read_workbook(excel_path)
    node_rows = records(sheets["节点表"])
    relation_rows = records(sheets["关系表"])
    course_rows = records(sheets["课程映射"])

    node_name_by_id = {row["Node_ID"]: row["名称"] for row in node_rows if row.get("Node_ID")}

    courses = []
    for row in course_rows:
        covered_ids = split_list(row.get("覆盖节点ID", ""))
        prerequisites = split_list(row.get("前置课程", ""))
        courses.append(
            {
                "id": row.get("Course_ID", ""),
                "name": row.get("课程名称", ""),
                "category": row.get("课程类别", ""),
                "stage": row.get("建议阶段", ""),
                "order": to_int(row.get("推荐排序", "")),
                "prerequisites": prerequisites,
                "coveredCount": to_int(row.get("覆盖节点数", "")),
                "coveredIds": covered_ids,
                "coveredNames": [node_name_by_id.get(node_id, node_id) for node_id in covered_ids],
                "description": row.get("课程说明", ""),
                "time": row.get("时间节点", ""),
            }
        )

    seen_relations = set()
    extra_relations = []
    for row in relation_rows:
        relation = row.get("关系类型", "")
        if relation in ("", "覆盖", "前置于"):
            continue
        source = row.get("Source_ID", "")
        target = row.get("Target_ID", "")
        key = (source, target, relation)
        if not source or not target or key in seen_relations:
            continue
        seen_relations.add(key)
        extra_relations.append({"source": source, "target": target, "name": relation})

    lines = [
        "export type NodeCategory = '课程' | '领域' | '构念' | '方法' | '理论' | '应用场景'",
        "",
        "export type CourseRecord = {",
        "  id: string",
        "  name: string",
        "  category: string",
        "  stage: string",
        "  order: number",
        "  prerequisites: string[]",
        "  coveredCount: number",
        "  coveredIds: string[]",
        "  coveredNames: string[]",
        "  description: string",
        "  time: '大一' | '大二' | '大三' | '大三或大四' | '大四'",
        "}",
        "",
        "export type GraphLink = {",
        "  source: string",
        "  target: string",
        "  name: string",
        "}",
        "",
        "export const timelineSlots = [",
        "  { year: '总览' },",
        "  { year: '大一' },",
        "  { year: '大二' },",
        "  { year: '大三' },",
        "  { year: '大四' },",
        "] as const",
        "",
        "export const courseData: CourseRecord[] = [",
    ]

    for course in courses:
        lines.extend(
            [
                "  {",
                f"    id: {js_string(course['id'])},",
                f"    name: {js_string(course['name'])},",
                f"    category: {js_string(course['category'])},",
                f"    stage: {js_string(course['stage'])},",
                f"    order: {course['order']},",
                "    prerequisites: [" + ", ".join(js_string(item) for item in course["prerequisites"]) + "],",
                f"    coveredCount: {course['coveredCount']},",
                "    coveredIds: [" + ", ".join(js_string(item) for item in course["coveredIds"]) + "],",
                "    coveredNames: [" + ", ".join(js_string(item) for item in course["coveredNames"]) + "],",
                f"    description: {js_string(course['description'])},",
                f"    time: {js_string(course['time'])} as CourseRecord['time'],",
                "  },",
            ]
        )
    lines.extend(["]", "", "export const extraRelations: GraphLink[] = ["])
    for relation in extra_relations:
        lines.append(
            f"  {{ source: {js_string(relation['source'])}, target: {js_string(relation['target'])}, name: {js_string(relation['name'])} }},"
        )
    lines.append("]")
    lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {OUTPUT} from {excel_path}")
    print(f"Courses: {len(courses)}, extra relations: {len(extra_relations)}")


if __name__ == "__main__":
    main()
