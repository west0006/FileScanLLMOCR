#!/bin/bash
# ES 索引初始化 — 创建档案索引 mapping 和 IK 分词器配置
# 用法: bash scripts/init_es.sh

ES_HOST="${ES_HOST:-localhost:9200}"
INDEX="${ES_INDEX:-archive_fulltext}"

echo "=== 创建 ES 索引: $INDEX ==="

curl -X PUT "http://${ES_HOST}/${INDEX}" -H 'Content-Type: application/json' -d '{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 0,
    "refresh_interval": "5s",
    "analysis": {
      "analyzer": {
        "ik_smart_synonym": {
          "type": "custom",
          "tokenizer": "ik_smart",
          "filter": ["archive_synonym"]
        }
      },
      "filter": {
        "archive_synonym": {
          "type": "synonym",
          "synonyms": [
            "学生,学籍,在校生",
            "毕业,校友,毕业生",
            "成绩,成绩单,学业成绩",
            "招生,录取,入学",
            "教职工,教工,教师",
            "档案,案卷,卷宗",
            "归口,归口单位,主管部门"
          ]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "archive_id":        { "type": "keyword" },
      "title":             { "type": "text", "analyzer": "ik_max_word", "boost": 3.0 },
      "full_text":         { "type": "text", "analyzer": "ik_smart_synonym" },
      "year":              { "type": "integer" },
      "category":          { "type": "keyword" },
      "department":        { "type": "keyword" },
      "fonds_id":          { "type": "keyword" },
      "retention_period":  { "type": "keyword" },
      "security_level":    { "type": "keyword" },
      "open_status":       { "type": "keyword" },
      "ocr_confidence":    { "type": "float" },
      "file_count":        { "type": "integer" },
      "created_at":        { "type": "date" },
      "ocr_text_quality":  { "type": "keyword" }
    }
  }
}'

echo ""
echo "=== 索引创建完成 ==="
curl "http://${ES_HOST}/${INDEX}/_mapping?pretty"
