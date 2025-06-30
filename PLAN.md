# Plan for a Unified Data Catalog in LightRAG

This document outlines the plan to extend LightRAG's capabilities from a text-focused RAG system to a comprehensive, unified data catalog. The goal is to ingest, model, and create relationships between both unstructured data (like PDFs and text files) and structured data (like databases and Parquet files), enabling complex, cross-domain queries.

---

## 1. Unified Graph Schema Design

The foundation of the data catalog will be a new, more expressive graph schema. This schema will be designed to represent various data assets and their metadata in a connected way.

### 1.1. Node Definitions

We will introduce new node labels to represent structured data assets.

#### `DataSource`
- **Description:** Represents a source of data, such as a database server or a file directory.
- **Properties:**
    - `name`: (string, unique) e.g., `production_postgres_db`, `data_lake_s3_bucket`.
    - `type`: (string) e.g., `PostgreSQL`, `ParquetDirectory`, `S3`.
    - `uri`: (string) The connection string or path to the data source.
    - `description`: (string) A human-readable description of the data source.
    - `created_at`: (datetime) Timestamp of when the source was added.

#### `File`
- **Description:** Represents a single structured file.
- **Properties:**
    - `name`: (string) The name of the file, e.g., `q4_sales.parquet`.
    - `path`: (string, unique) The full path to the file.
    - `format`: (string) e.g., `Parquet`, `CSV`, `JSON`.
    - `size_bytes`: (integer) The size of the file in bytes.
    - `schema_definition`: (string) A JSON string representing the file's schema.
    - `description`: (string) A summary of the file's content.
    - `created_at`: (datetime) Timestamp of ingestion.

#### `Table`
- **Description:** Represents a table within a database.
- **Properties:**
    - `name`: (string) The name of the table, e.g., `users`.
    - `qualified_name`: (string, unique) A unique identifier, e.g., `prod_db.public.users`.
    - `description`: (string) A summary of the table's purpose, potentially auto-generated.
    - `row_count`: (integer) The number of rows in the table.
    - `created_at`: (datetime) Timestamp of ingestion.

#### `Column`
- **Description:** Represents a column within a `Table` or `File`. This is a critical node for detailed metadata.
- **Properties:**
    - `name`: (string) The name of the column, e.g., `email_address`.
    - `qualified_name`: (string, unique) A unique identifier, e.g., `prod_db.public.users.email_address`.
    - `data_type`: (string) The column's data type, e.g., `VARCHAR(255)`, `INTEGER`, `TIMESTAMP`.
    - `description`: (string) A description of the column's meaning.
    - `is_primary_key`: (boolean)
    - `is_foreign_key`: (boolean)
    - `is_nullable`: (boolean)
    - `sample_values`: (string) A JSON array of a few representative values, e.g., `["example1@test.com", "example2@test.com"]`.
    - `stats`: (string) A JSON object containing basic statistics, e.g., `{"min": 5, "max": 98, "average": 42.5, "null_fraction": 0.05, "distinct_values": 150}`.

#### `Document` & `Entity`
- These existing nodes will be leveraged. `Document` will represent unstructured text, and `Entity` will represent named entities (people, places, etc.) found in *any* data source.

### 1.2. Relationship Definitions

New relationships will connect the data catalog assets and link them to unstructured content.

- **`(DataSource) -[:HAS_TABLE]-> (Table)`**: Connects a database to its tables.
- **`(DataSource) -[:HAS_FILE]-> (File)`**: Connects a data source to its files.
- **`(Table) -[:HAS_COLUMN]-> (Column)`**: Connects a table to its columns.
- **`(File) -[:HAS_COLUMN]-> (Column)`**: Connects a file to its columns.
- **`(Column) -[:REFERENCES]-> (Column)`**: Represents a foreign key relationship between two columns.
- **`(Document) -[:MENTIONS]-> (Table|File|Column)`**: **Crucial link.** Connects a piece of unstructured text to a specific asset in the data catalog.
    - **Properties:**
        - `context_snippet`: (string) The sentence or paragraph where the mention occurred.
        - `confidence_score`: (float) A score indicating the confidence of the link.
- **`(Column) -[:CONTAINS_ENTITY]-> (Entity)`**: A semantic link indicating that a column's values correspond to a known entity type. For example, a `user_country` column would be linked to entities like `United States` and `Canada`.

---

## 2. Structured Data Ingestion Framework

A new, extensible framework will be built to handle structured data sources.

### 2.1. Parquet File Ingestion (`insert_parquet`)

1.  **Read Metadata:** Use `pyarrow` to read the Parquet file's schema without loading the entire file into memory.
2.  **Create Nodes:**
    - Create a `File` node with the file's path, format, size, and schema.
    - For each field in the schema, create a `Column` node.
3.  **Create Relationships:** Create `(File)-[:HAS_COLUMN]->(Column)` relationships.
4.  **Data Profiling & Sampling:**
    - Read the first N (e.g., 1,000) rows of the file.
    - For each column, compute basic statistics (min, max, null count, etc.) and store them in the `stats` property of the `Column` node.
    - For string-based columns, store the top K most frequent values in `sample_values`.
5.  **Entity Linking:** For columns with string data, attempt to match their sample values against existing `Entity` nodes in the graph. If matches are found, create `(Column)-[:CONTAINS_ENTITY]->(Entity)` relationships.

### 2.2. Database Ingestion (`insert_database`)

1.  **Connect & Inspect:** Connect to the target database using a provided connection string.
2.  **Create `DataSource`:** Create a `DataSource` node representing the database.
3.  **Query Information Schema:** Programmatically query the database's internal information schema (e.g., `information_schema` in PostgreSQL) to get a list of all tables, columns, data types, and constraints.
4.  **Create `Table` and `Column` Nodes:** For each table and column discovered, create the corresponding nodes in the graph.
5.  **Map Relationships:**
    - Create `(DataSource)-[:HAS_TABLE]->(Table)` and `(Table)-[:HAS_COLUMN]->(Column)` relationships.
    - Explicitly create `(Column)-[:REFERENCES]->(Column)` relationships for all foreign keys.
6.  **Data Profiling:** Similar to the Parquet process, run sampling queries (`SELECT ... LIMIT N`) on tables to populate the `stats` and `sample_values` properties on `Column` nodes.

---

## 3. Enhanced Unstructured Data Ingestion

The existing text ingestion pipeline will be made "catalog-aware".

1.  **Catalog Pre-computation:** Before processing a batch of documents, fetch a list of all `Table` and `Column` names from the graph to serve as a local dictionary.
2.  **Mention Pre-screening:** When processing a text chunk, perform a fast, exact-match search for the table and column names from the dictionary. For every match found, create a `MENTIONS` relationship in the graph.
3.  **LLM Prompt Augmentation:** Enhance the entity extraction prompt sent to the LLM. The prompt will now include the list of tables and columns that were pre-screened in the text.
    - **Example Prompt Snippet:** `"...The following data assets were mentioned in this text: Table 'quarterly_sales', Column 'revenue_usd'. When extracting entities and relationships, pay close attention to how they relate to these assets."`
4.  **LLM-based Relation Linking:** The LLM's output will be parsed not only for new entities but also for explicit links to the pre-identified data assets, creating more robust `MENTIONS` relationships.

---

## 4. Querying the Unified Catalog

The query engine will be updated to leverage the new, richer graph structure. This will enable powerful new query patterns.

- **Discovery Query:**
    - **User Question:** *"What data do we have on user activity?"*
    - **Execution Path:** Search for `Table`, `File`, or `Column` nodes with names or descriptions matching "user" and "activity". Follow relationships to show their data sources and schemas.

- **Direct Fact-Finding Query:**
    - **User Question:** *"What is the data type of the `last_login` column in the `users` table?"*
    - **Execution Path:** Find the `Table` node named `users`, traverse to the `Column` node named `last_login`, and return its `data_type` property.

- **Cross-Domain RAG Query:**
    - **User Question:** *"Based on the latest annual report, summarize our performance as it relates to the `regional_sales` table."*
    - **Execution Path:**
        1.  Identify the `Document` for the "latest annual report".
        2.  Find the `Table` node for `regional_sales`.
        3.  Find all `MENTIONS` relationships connecting the two.
        4.  Retrieve the `context_snippet` from those relationships and the associated text chunks.
        5.  Pass the retrieved text to the LLM with the prompt: "Summarize the following text which discusses the regional_sales table."
