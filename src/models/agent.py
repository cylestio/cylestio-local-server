"""
Agent model and related functionality.

This module defines the Agent model that represents a monitoring agent installed
on a system that reports telemetry data to the server.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.orm import relationship

from src.models.base import Base


class Agent(Base):
    """
    Agent model that represents a monitoring agent installed on a system.
    
    An agent is responsible for collecting and reporting telemetry data to the server.
    It has a unique identifier and can have many sessions, events, traces, and other
    telemetry data associated with it.
    """
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    
    system_info = Column(String)
    version = Column(String)
    
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    sessions = relationship("Session", back_populates="agent", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="agent")
    traces = relationship("Trace", back_populates="agent")
    
    def __repr__(self) -> str:
        return f"<Agent {self.id} ({self.agent_id})>"
    
    @classmethod
    def get_or_create(cls, db_session, agent_id: str, system_info: Optional[str] = None,
                     version: Optional[str] = None, name: Optional[str] = None) -> "Agent":
        """
        Get an existing agent or create a new one if it doesn't exist.
        
        Args:
            db_session: Database session
            agent_id: Unique identifier for the agent
            system_info: Optional system information
            version: Optional agent version
            name: Optional agent name
            
        Returns:
            Agent: The retrieved or created agent
        """
        agent = db_session.query(cls).filter(cls.agent_id == agent_id).first()
        
        current_time = datetime.utcnow()
        
        if agent:
            # Update the agent's last_seen time and other attributes if provided
            agent.last_seen = current_time
            
            if system_info and not agent.system_info:
                agent.system_info = system_info
                
            if version and agent.version != version:
                agent.version = version
                
            # Always ensure name matches agent_id for consistency
            if agent.name != agent_id:
                agent.name = agent_id
                
            db_session.add(agent)
            return agent
        
        # Create a new agent if it doesn't exist
        agent = cls(
            agent_id=agent_id,
            system_info=system_info,
            version=version,
            name=agent_id,  # Always use agent_id as the name for consistency
            first_seen=current_time,
            last_seen=current_time,
            is_active=True
        )
        
        db_session.add(agent)
        return agent
    
    @classmethod
    def generate_agent_id(cls) -> str:
        """
        Generate a unique agent ID.
        
        Returns:
            str: A unique agent ID
        """
        return str(uuid.uuid4())
    
    def update_last_seen(self, db_session) -> None:
        """
        Update the agent's last_seen timestamp.
        
        Args:
            db_session: Database session
        """
        self.last_seen = datetime.utcnow()
        db_session.add(self)
    
    def deactivate(self, db_session) -> None:
        """
        Deactivate the agent.
        
        Args:
            db_session: Database session
        """
        self.is_active = False
        db_session.add(self)
    
    def reactivate(self, db_session) -> None:
        """
        Reactivate the agent.
        
        Args:
            db_session: Database session
        """
        self.is_active = True
        self.update_last_seen(db_session)
    
    def get_active_session(self, db_session) -> Optional["Session"]:
        """
        Get the agent's active session, if any.
        
        Args:
            db_session: Database session
            
        Returns:
            Session or None: The active session, if any
        """
        from src.models.session import Session
        
        return db_session.query(Session).filter(
            Session.agent_id == self.agent_id,
            Session.end_timestamp.is_(None)
        ).order_by(Session.start_timestamp.desc()).first()
    
    def get_recent_events(self, db_session, limit: int = 100) -> List["Event"]:
        """
        Get the agent's most recent events.
        
        Args:
            db_session: Database session
            limit: Maximum number of events to return
            
        Returns:
            List[Event]: The agent's most recent events
        """
        from src.models.event import Event
        
        return db_session.query(Event).filter(
            Event.agent_id == self.agent_id
        ).order_by(Event.timestamp.desc()).limit(limit).all()
    
    def get_recent_traces(self, db_session, limit: int = 20) -> List["Trace"]:
        """
        Get the agent's most recent traces.
        
        Args:
            db_session: Database session
            limit: Maximum number of traces to return
            
        Returns:
            List[Trace]: The agent's most recent traces
        """
        from src.models.trace import Trace
        
        return db_session.query(Trace).filter(
            Trace.agent_id == self.agent_id
        ).order_by(Trace.start_timestamp.desc()).limit(limit).all()
    
    def get_statistics(self, db_session) -> Dict[str, Any]:
        """
        Get statistics about the agent's telemetry data.
        
        Args:
            db_session: Database session
            
        Returns:
            Dict: Statistics about the agent's telemetry data
        """
        from src.models.event import Event
        from src.models.trace import Trace
        from src.models.session import Session
        
        event_count = db_session.query(func.count(Event.id)).filter(
            Event.agent_id == self.agent_id
        ).scalar() or 0
        
        trace_count = db_session.query(func.count(Trace.trace_id)).filter(
            Trace.agent_id == self.agent_id
        ).scalar() or 0
        
        session_count = db_session.query(func.count(Session.id)).filter(
            Session.agent_id == self.agent_id
        ).scalar() or 0
        
        return {
            "event_count": event_count,
            "trace_count": trace_count,
            "session_count": session_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "is_active": self.is_active
        }
    
    def get_event_count(self, db_session) -> int:
        """
        Get the total number of events for this agent.
        
        Args:
            db_session: Database session
            
        Returns:
            int: Number of events
        """
        from src.models.event import Event
        return db_session.query(Event).filter(Event.agent_id == self.agent_id).count()
    
    def get_session_count(self, db_session) -> int:
        """
        Get the total number of sessions for this agent.
        
        Args:
            db_session: Database session
            
        Returns:
            int: Number of sessions
        """
        from src.models.session import Session
        return db_session.query(Session).filter(Session.agent_id == self.agent_id).count()
    
    def get_token_usage(self, db_session, start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get token usage metrics for this agent within a time range.
        
        Args:
            db_session: Database session
            start_time: Start of time range (optional)
            end_time: End of time range (optional)
            
        Returns:
            Dict containing token usage metrics by model
        """
        from src.models.event import Event
        from src.models.llm_interaction import LLMInteraction
        from sqlalchemy import func
        
        query = db_session.query(
            LLMInteraction.model,
            func.sum(LLMInteraction.input_tokens).label('total_input_tokens'),
            func.sum(LLMInteraction.output_tokens).label('total_output_tokens'),
            func.sum(LLMInteraction.total_tokens).label('total_tokens'),
            func.count(LLMInteraction.id).label('call_count')
        ).join(
            Event, LLMInteraction.event_id == Event.id
        ).filter(
            Event.agent_id == self.agent_id
        ).filter(
            LLMInteraction.interaction_type == 'finish'
        )
        
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
            
        query = query.group_by(LLMInteraction.model)
        
        return {
            row.model: {
                'input_tokens': row.total_input_tokens or 0,
                'output_tokens': row.total_output_tokens or 0,
                'total_tokens': row.total_tokens or 0,
                'call_count': row.call_count
            }
            for row in query.all()
        }
    
    def get_tool_usage(self, db_session, start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None) -> Dict[str, int]:
        """
        Get tool usage metrics for this agent within a time range.
        
        Args:
            db_session: Database session
            start_time: Start of time range (optional)
            end_time: End of time range (optional)
            
        Returns:
            Dict mapping tool names to usage counts
        """
        from src.models.event import Event
        from src.models.tool_interaction import ToolInteraction
        from sqlalchemy import func
        
        query = db_session.query(
            ToolInteraction.tool_name,
            func.count(ToolInteraction.id).label('usage_count')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        ).filter(
            Event.agent_id == self.agent_id
        ).filter(
            ToolInteraction.interaction_type == 'execution'
        )
        
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
            
        query = query.group_by(ToolInteraction.tool_name)
        
        return {row.tool_name: row.usage_count for row in query.all()}
    
    def get_security_alerts(self, db_session, start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> Dict[str, int]:
        """
        Get security alert counts for this agent within a time range.
        
        Args:
            db_session: Database session
            start_time: Start of time range (optional)
            end_time: End of time range (optional)
            
        Returns:
            Dict mapping alert levels to counts
        """
        from src.models.event import Event
        from src.models.security_alert import SecurityAlert
        from sqlalchemy import func
        
        query = db_session.query(
            SecurityAlert.alert_level,
            func.count(SecurityAlert.id).label('alert_count')
        ).join(
            Event, SecurityAlert.event_id == Event.id
        ).filter(
            Event.agent_id == self.agent_id
        )
        
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
            
        query = query.group_by(SecurityAlert.alert_level)
        
        return {row.alert_level: row.alert_count for row in query.all()} 