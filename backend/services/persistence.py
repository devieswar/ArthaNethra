"""
Persistence service for storing application state to disk
"""
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from models.document import Document
from models.entity import Entity


class PersistenceService:
    """
    Handles persistence of in-memory stores to disk.
    
    Stores data as JSON files in a persistent volume to survive restarts.
    """
    
    def __init__(self, data_dir: str = "/app/cache/state"):
        """
        Initialize persistence service
        
        Args:
            data_dir: Directory to store state files (mounted as volume)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.documents_file = self.data_dir / "documents.json"
        self.graphs_file = self.data_dir / "graphs.json"
        self.entities_file = self.data_dir / "entities.json"
        self.chat_sessions_file = self.data_dir / "chat_sessions.json"
        self.chat_messages_file = self.data_dir / "chat_messages.json"
        self.risks_file = self.data_dir / "risks.json"
        
        logger.info(f"Persistence service initialized at: {self.data_dir}")
    
    # ==================== SAVE OPERATIONS ====================
    
    def save_documents(self, documents_store: Dict[str, Document]) -> None:
        """Save documents store to disk"""
        try:
            data = {}
            for doc_id, doc in documents_store.items():
                data[doc_id] = {
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_path": doc.file_path,
                    "file_size": doc.file_size,
                    "mime_type": doc.mime_type,
                    "status": doc.status.value if hasattr(doc.status, 'value') else str(doc.status),
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    "metadata": doc.metadata,
                    "graph_id": doc.graph_id,
                    "entities_count": doc.entities_count,
                    "edges_count": doc.edges_count,
                    "ade_output": doc.ade_output,  # Save ADE output with markdown
                    "extraction_id": doc.extraction_id,
                    "total_pages": doc.total_pages,
                    "confidence_score": doc.confidence_score
                }
            
            with open(self.documents_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(data)} documents to disk")
        except Exception as e:
            logger.error(f"Failed to save documents: {e}")
    
    def save_graphs(self, graphs_store: Dict[str, Dict[str, Any]]) -> None:
        """Save graphs store to disk"""
        try:
            from models.edge import Edge
            
            data = {}
            for graph_id, graph in graphs_store.items():
                # Convert Entity objects to dicts
                entities = []
                for entity in graph.get("entities", []):
                    if isinstance(entity, Entity):
                        entities.append({
                            "id": entity.id,
                            "type": entity.type.value if hasattr(entity.type, 'value') else str(entity.type),
                            "name": entity.name,
                            "display_type": entity.display_type,
                            "original_type": entity.original_type,
                            "properties": entity.properties,
                            "document_id": entity.document_id,
                            "graph_id": entity.graph_id
                        })
                    else:
                        entities.append(entity)
                
                # Convert Edge objects to dicts
                edges = []
                for edge in graph.get("edges", []):
                    if isinstance(edge, Edge):
                        edges.append({
                            "id": edge.id,
                            "source": edge.source,
                            "target": edge.target,
                            "type": edge.type.value if hasattr(edge.type, 'value') else str(edge.type),
                            "properties": edge.properties,
                            "graph_id": edge.graph_id
                        })
                    else:
                        edges.append(edge)
                
                data[graph_id] = {
                    "graph_id": graph.get("graph_id"),
                    "document_id": graph.get("document_id"),
                    "entities": entities,
                    "edges": edges,
                    "metadata": graph.get("metadata", {})
                }
            
            with open(self.graphs_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(data)} graphs to disk")
        except Exception as e:
            logger.error(f"Failed to save graphs: {e}")
    
    def save_entities(self, entities_store: Dict[str, List[Entity]]) -> None:
        """Save entities store to disk"""
        try:
            data = {}
            for graph_id, entities in entities_store.items():
                data[graph_id] = []
                for entity in entities:
                    if isinstance(entity, Entity):
                        data[graph_id].append({
                            "id": entity.id,
                            "type": entity.type.value if hasattr(entity.type, 'value') else str(entity.type),
                            "name": entity.name,
                            "display_type": entity.display_type,
                            "original_type": entity.original_type,
                            "properties": entity.properties,
                            "document_id": entity.document_id,
                            "graph_id": entity.graph_id
                        })
                    else:
                        data[graph_id].append(entity)
            
            with open(self.entities_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved entities for {len(data)} graphs to disk")
        except Exception as e:
            logger.error(f"Failed to save entities: {e}")
    
    def save_chat_sessions(self, chat_sessions_store: Dict[str, Any]) -> None:
        """Save chat sessions to disk"""
        try:
            with open(self.chat_sessions_file, 'w') as f:
                json.dump(chat_sessions_store, f, indent=2)
            logger.debug(f"Saved {len(chat_sessions_store)} chat sessions to disk")
        except Exception as e:
            logger.error(f"Failed to save chat sessions: {e}")
    
    def save_chat_messages(self, chat_messages_store: Dict[str, List[Any]]) -> None:
        """Save chat messages to disk"""
        try:
            with open(self.chat_messages_file, 'w') as f:
                json.dump(chat_messages_store, f, indent=2)
            logger.debug(f"Saved chat messages for {len(chat_messages_store)} sessions to disk")
        except Exception as e:
            logger.error(f"Failed to save chat messages: {e}")
    
    def save_risks(self, risks_store: Dict[str, List[Any]]) -> None:
        """Save risks to disk"""
        try:
            # Convert Risk objects to dicts
            data = {}
            for graph_id, risks in risks_store.items():
                serialized_risks = []
                for risk in risks:
                    if hasattr(risk, "model_dump"):
                        risk_payload = risk.model_dump(mode="json")
                    else:
                        risk_payload = risk
                    serialized_risks.append(self._make_json_safe(risk_payload))
                data[graph_id] = serialized_risks
            
            with open(self.risks_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved risks for {len(data)} graphs to disk")
        except Exception as e:
            logger.error(f"Failed to save risks: {e}")
    
    def save_all(
        self,
        documents_store: Dict[str, Document],
        graphs_store: Dict[str, Dict[str, Any]],
        entities_store: Dict[str, List[Entity]],
        chat_sessions_store: Dict[str, Any] = None,
        chat_messages_store: Dict[str, List[Any]] = None,
        risks_store: Dict[str, List[Any]] = None
    ) -> None:
        """Save all stores to disk"""
        logger.info("Saving all state to disk...")
        self.save_documents(documents_store)
        self.save_graphs(graphs_store)
        self.save_entities(entities_store)
        if chat_sessions_store is not None:
            self.save_chat_sessions(chat_sessions_store)
        if chat_messages_store is not None:
            self.save_chat_messages(chat_messages_store)
        if risks_store is not None:
            self.save_risks(risks_store)
        logger.info("All state saved to disk")
    
    # ==================== LOAD OPERATIONS ====================
    
    def load_documents(self) -> Dict[str, Document]:
        """Load documents store from disk"""
        try:
            if not self.documents_file.exists():
                logger.debug("No documents file found, starting fresh")
                return {}
            
            with open(self.documents_file, 'r') as f:
                data = json.load(f)
            
            documents = {}
            for doc_id, doc_data in data.items():
                # Reconstruct Document object
                from models.document import DocumentStatus
                from datetime import datetime
                
                doc = Document(
                    id=doc_data["id"],
                    filename=doc_data["filename"],
                    file_path=doc_data["file_path"],
                    file_size=doc_data.get("file_size"),
                    mime_type=doc_data.get("mime_type"),
                    uploaded_at=datetime.fromisoformat(doc_data["uploaded_at"]) if doc_data.get("uploaded_at") else None,
                    metadata=doc_data.get("metadata", {})
                )
                doc.status = DocumentStatus(doc_data["status"]) if doc_data.get("status") else DocumentStatus.UPLOADED
                doc.graph_id = doc_data.get("graph_id")
                doc.entities_count = doc_data.get("entities_count", 0)
                doc.edges_count = doc_data.get("edges_count", 0)
                doc.ade_output = doc_data.get("ade_output")  # Restore ADE output
                doc.extraction_id = doc_data.get("extraction_id")
                doc.total_pages = doc_data.get("total_pages")
                doc.confidence_score = doc_data.get("confidence_score")
                documents[doc_id] = doc
            
            logger.info(f"Loaded {len(documents)} documents from disk")
            return documents
        except Exception as e:
            logger.error(f"Failed to load documents: {e}")
            return {}
    
    def load_graphs(self) -> Dict[str, Dict[str, Any]]:
        """Load graphs store from disk"""
        try:
            if not self.graphs_file.exists():
                logger.debug("No graphs file found, starting fresh")
                return {}
            
            with open(self.graphs_file, 'r') as f:
                data = json.load(f)
            
            graphs = {}
            for graph_id, graph_data in data.items():
                # Reconstruct Entity objects
                from models.entity import EntityType
                from models.edge import Edge, EdgeType
                
                entities = []
                for entity_data in graph_data.get("entities", []):
                    entity = Entity(
                        id=entity_data["id"],
                        type=EntityType(entity_data["type"]),
                        name=entity_data["name"],
                        display_type=entity_data.get("display_type"),
                        original_type=entity_data.get("original_type"),
                        properties=entity_data.get("properties", {}),
                        document_id=entity_data.get("document_id", graph_data.get("document_id", "")),
                        graph_id=entity_data.get("graph_id", graph_id)
                    )
                    entities.append(entity)
                
                # Reconstruct Edge objects
                edges = []
                for edge_data in graph_data.get("edges", []):
                    if isinstance(edge_data, dict):
                        edge = Edge(
                            id=edge_data["id"],
                            source=edge_data["source"],
                            target=edge_data["target"],
                            type=EdgeType(edge_data["type"]),
                            properties=edge_data.get("properties", {}),
                            graph_id=edge_data.get("graph_id", graph_id)
                        )
                        edges.append(edge)
                    else:
                        edges.append(edge_data)
                
                graphs[graph_id] = {
                    "graph_id": graph_data.get("graph_id"),
                    "document_id": graph_data.get("document_id"),
                    "entities": entities,
                    "edges": edges,
                    "metadata": graph_data.get("metadata", {})
                }
            
            logger.info(f"Loaded {len(graphs)} graphs from disk")
            return graphs
        except Exception as e:
            logger.error(f"Failed to load graphs: {e}")
            return {}
    
    def load_entities(self) -> Dict[str, List[Entity]]:
        """Load entities store from disk"""
        try:
            if not self.entities_file.exists():
                logger.debug("No entities file found, starting fresh")
                return {}
            
            with open(self.entities_file, 'r') as f:
                data = json.load(f)
            
            entities_store = {}
            from models.entity import EntityType
            
            for graph_id, entities_data in data.items():
                entities = []
                for entity_data in entities_data:
                    entity = Entity(
                        id=entity_data["id"],
                        type=EntityType(entity_data["type"]),
                        name=entity_data["name"],
                        display_type=entity_data.get("display_type"),
                        original_type=entity_data.get("original_type"),
                        properties=entity_data.get("properties", {}),
                        document_id=entity_data.get("document_id", ""),
                        graph_id=entity_data.get("graph_id", graph_id)
                    )
                    entities.append(entity)
                entities_store[graph_id] = entities
            
            logger.info(f"Loaded entities for {len(entities_store)} graphs from disk")
            return entities_store
        except Exception as e:
            logger.error(f"Failed to load entities: {e}")
            return {}
    
    def load_chat_sessions(self) -> Dict[str, Any]:
        """Load chat sessions from disk"""
        try:
            if not self.chat_sessions_file.exists():
                logger.debug("No chat sessions file found, starting fresh")
                return {}
            
            with open(self.chat_sessions_file, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Loaded {len(data)} chat sessions from disk")
            return data
        except Exception as e:
            logger.error(f"Failed to load chat sessions: {e}")
            return {}
    
    def load_chat_messages(self) -> Dict[str, List[Any]]:
        """Load chat messages from disk"""
        try:
            if not self.chat_messages_file.exists():
                logger.debug("No chat messages file found, starting fresh")
                return {}
            
            with open(self.chat_messages_file, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Loaded chat messages for {len(data)} sessions from disk")
            return data
        except Exception as e:
            logger.error(f"Failed to load chat messages: {e}")
            return {}
    
    def load_risks(self) -> Dict[str, List[Any]]:
        """Load risks from disk"""
        try:
            if not self.risks_file.exists():
                logger.debug("No risks file found, starting fresh")
                return {}
            
            with open(self.risks_file, 'r') as f:
                data = json.load(f)
            
            # Convert back to Risk objects
            from models.risk import Risk, RiskSeverity
            risks_store = {}
            for graph_id, risks_data in data.items():
                risks = []
                for risk_data in risks_data:
                    if isinstance(risk_data, dict) and "severity" in risk_data:
                        risk = Risk(
                            id=risk_data["id"],
                            type=risk_data.get("type", "Unknown Risk"),
                            severity=RiskSeverity(risk_data["severity"]),
                            description=risk_data["description"],
                            affected_entity_ids=risk_data.get("affected_entity_ids", []),
                            citations=risk_data.get("citations", []),
                            score=risk_data.get("score", 0.5),
                            threshold=risk_data.get("threshold", 0.0),
                            actual_value=risk_data.get("actual_value", 0.0),
                            recommendation=risk_data.get("recommendation", "Review this risk"),
                            document_id=risk_data.get("document_id", ""),
                            graph_id=risk_data.get("graph_id", graph_id)
                        )
                        risks.append(risk)
                    else:
                        risks.append(risk_data)
                risks_store[graph_id] = risks
            
            logger.info(f"Loaded risks for {len(risks_store)} graphs from disk")
            return risks_store
        except Exception as e:
            logger.error(f"Failed to load risks: {e}")
            return {}
    
    def load_all(self) -> tuple[Dict[str, Document], Dict[str, Dict[str, Any]], Dict[str, List[Entity]], Dict[str, Any], Dict[str, List[Any]], Dict[str, List[Any]]]:
        """Load all stores from disk"""
        logger.info("Loading all state from disk...")
        documents = self.load_documents()
        graphs = self.load_graphs()
        entities = self.load_entities()
        chat_sessions = self.load_chat_sessions()
        chat_messages = self.load_chat_messages()
        risks = self.load_risks()
        logger.info(f"Loaded state: {len(documents)} docs, {len(graphs)} graphs, {len(chat_sessions)} sessions, {len(risks)} risk graphs")
        return documents, graphs, entities, chat_sessions, chat_messages, risks
    
    # ==================== UTILITY OPERATIONS ====================
    
    def clear_all(self) -> None:
        """Clear all persisted state (use with caution!)"""
        try:
            if self.documents_file.exists():
                self.documents_file.unlink()
            if self.graphs_file.exists():
                self.graphs_file.unlink()
            if self.entities_file.exists():
                self.entities_file.unlink()
            if self.chat_sessions_file.exists():
                self.chat_sessions_file.unlink()
            if self.chat_messages_file.exists():
                self.chat_messages_file.unlink()
            if self.risks_file.exists():
                self.risks_file.unlink()
            logger.warning("All persisted state cleared")
        except Exception as e:
            logger.error(f"Failed to clear state: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about persisted data"""
        stats = {
            "documents_exists": self.documents_file.exists(),
            "graphs_exists": self.graphs_file.exists(),
            "entities_exists": self.entities_file.exists(),
            "documents_size": self.documents_file.stat().st_size if self.documents_file.exists() else 0,
            "graphs_size": self.graphs_file.stat().st_size if self.graphs_file.exists() else 0,
            "entities_size": self.entities_file.stat().st_size if self.entities_file.exists() else 0,
        }
        return stats

    def _make_json_safe(self, value: Any) -> Any:
        """Recursively convert values so they can be serialized to JSON."""
        if isinstance(value, dict):
            return {k: self._make_json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._make_json_safe(v) for v in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value

