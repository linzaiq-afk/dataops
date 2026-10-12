```mermaid
flowchart TD
    A["Sources"] --> B["Ingestion"]
    B --> C["RAW"]
    C --> D["STAGING"]
    D --> E["CORE"]
    E --> F["MART"]
    F --> G["BI"]
```
