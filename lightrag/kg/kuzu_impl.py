
import kuzu
from lightrag.base import BaseGraphStorage
from lightrag.utils import logger

class KuzuGraphStorage(BaseGraphStorage):
    def __init__(self, namespace: str, global_config: dict, embedding_func, db_path: str):
        super().__init__(namespace=namespace,
                         global_config=global_config,
                         embedding_func=embedding_func)
        # Initialize Kùzu DB & async connection
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
    
    async def initialize(self):
        # Optionally create schema if not exists
        self.conn.execute("""
            CREATE NODE TABLE IF NOT EXISTS base(
                entity_id STRING PRIMARY KEY,
                properties MAP<STRING, STRING>,
                source_id STRING
            );
        """)
    
    async def upsert_node(self, node_id: str, node_data: dict[str, str]) -> None:
        props = ", ".join(f'"{k}": "{v}"' for k, v in node_data.items())
        self.conn.execute(f'''
            CREATE (n:base {{ entity_id: "{node_id}", properties: {{{props}}} }});
        ''')
    
    async def has_node(self, node_id: str) -> bool:
        result = self.conn.execute(f'''
          MATCH (n:base {{entity_id: "{node_id}"}}) RETURN COUNT(n) AS count;
        ''')
        return result.get_next()[0] > 0

    async def drop(self) -> dict[str, str]:
        self.conn.execute("DROP TABLE IF EXISTS base;")
        return {"status": "success", "message": "data dropped"}
    
    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        # Kuzu does not have a direct equivalent of UNWIND for this check, so we do it manually
        query = f"""
        MATCH (a:base {{entity_id: '{source_node_id}'}})-[r]->(b:base {{entity_id: '{target_node_id}'}})
        RETURN COUNT(r) > 0
        """
        result = self.conn.execute(query)
        return result.get_next()[0]

    async def node_degree(self, node_id: str) -> int:
        query = f"""
        MATCH (n:base {{entity_id: '{node_id}'}})-[r]-()
        RETURN COUNT(r)
        """
        result = self.conn.execute(query)
        return result.get_next()[0]

    async def edge_degree(self, src_id: str, tgt_id: str) -> int:
        # This is not an efficient way to do this, but it's a start
        src_degree = await self.node_degree(src_id)
        tgt_degree = await self.node_degree(tgt_id)
        return src_degree + tgt_degree

    async def get_node(self, node_id: str) -> dict[str, str] | None:
        query = f"""
        MATCH (n:base {{entity_id: '{node_id}'}})
        RETURN n.properties
        """
        result = self.conn.execute(query)
        if result.has_next():
            return result.get_next()[0]
        return None

    async def get_edge(
        self, source_node_id: str, target_node_id: str
    ) -> dict[str, str] | None:
        query = f"""
        MATCH (a:base {{entity_id: '{source_node_id}'}})-[r]->(b:base {{entity_id: '{target_node_id}'}})
        RETURN r.properties
        """
        result = self.conn.execute(query)
        if result.has_next():
            return result.get_next()[0]
        return None

    async def get_node_edges(self, source_node_id: str) -> list[tuple[str, str]] | None:
        query = f"""
        MATCH (a:base {{entity_id: '{source_node_id}'}})-[r]->(b:base)
        RETURN a.entity_id, b.entity_id
        """
        result = self.conn.execute(query)
        return [row for row in result.result_set] if result.has_next() else None

    async def get_nodes_by_chunk_ids(self, chunk_ids: list[str]) -> list[dict]:
        # Kuzu doesn't directly support UNWIND in the same way as Neo4j.
        # We can simulate this by iterating through the chunk_ids.
        nodes = []
        for chunk_id in chunk_ids:
            query = f"""
            MATCH (n:base)
            WHERE n.source_id = '{chunk_id}'
            RETURN n.properties
            """
            result = self.conn.execute(query)
            nodes.extend([row[0] for row in result.result_set])
        return nodes

    async def get_edges_by_chunk_ids(self, chunk_ids: list[str]) -> list[dict]:
        edges = []
        for chunk_id in chunk_ids:
            query = f"""
            MATCH ()-[r]->()
            WHERE r.source_id = '{chunk_id}'
            RETURN r.properties
            """
            result = self.conn.execute(query)
            edges.extend([row[0] for row in result.result_set])
        return edges

    async def upsert_edge(
        self, source_node_id: str, target_node_id: str, edge_data: dict[str, str]
    ) -> None:
        props = ", ".join(f'"{k}": "{v}"' for k, v in edge_data.items())
        query = f"""
        MATCH (a:base {{entity_id: '{source_node_id}'}}), (b:base {{entity_id: '{target_node_id}'}})
        CREATE (a)-[r:RELATION {{ {props} }}]->(b)
        """
        self.conn.execute(query)

    async def delete_node(self, node_id: str) -> None:
        query = f"""
        MATCH (n:base {{entity_id: '{node_id}'}})
        DETACH DELETE n
        """
        self.conn.execute(query)

    async def remove_nodes(self, nodes: list[str]):
        # Kuzu doesn't directly support UNWIND for deletions.
        for node_id in nodes:
            await self.delete_node(node_id)

    async def remove_edges(self, edges: list[tuple[str, str]]):
        for src, tgt in edges:
            query = f"""
            MATCH (a:base {{entity_id: '{src}'}})-[r]->(b:base {{entity_id: '{tgt}'}})
            DELETE r
            """
            self.conn.execute(query)

    async def get_all_labels(self) -> list[str]:
        query = "MATCH (n:base) RETURN DISTINCT n.entity_id"
        result = self.conn.execute(query)
        return [row[0] for row in result.result_set]

    async def get_knowledge_graph(
        self, node_label: str, max_depth: int = 3, max_nodes: int = 1000
    ) -> KnowledgeGraph:
        # This is a simplified implementation. A full implementation would require a more complex query.
        query = f"""
        MATCH (n:base {{entity_id: '{node_label}'}})-[r*1..{max_depth}]-(m:base)
        RETURN n, r, m
        LIMIT {max_nodes}
        """
        result = self.conn.execute(query)
        nodes = []
        edges = []
        for row in result.result_set:
            nodes.append(row[0])
            edges.append(row[1])
            nodes.append(row[2])
        return KnowledgeGraph(nodes=nodes, edges=edges)
    
    async def index_done_callback(self) -> None:
        """Commit the storage operations after indexing"""
        pass
