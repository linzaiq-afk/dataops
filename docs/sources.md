# Источники данных

| Источник | Тип | URL / путь | Что забираем | Частота | Техполя при загрузке |
|---|---|---|---|---|---|
| Olist → PostgreSQL | РСУБД | PostgreSQL: shop (планируется) | customers, orders, payments | daily | ingestion_ts, source, batch_id |
| DummyJSON | API | https://dummyjson.com/products | products, prices, categories | daily | ingestion_ts, source, batch_id |
| Returns CSV | File |  data/returns.csv (планируется)  | order_id, return_date, amount, reason | daily | ingestion_ts, source, batch_id |
