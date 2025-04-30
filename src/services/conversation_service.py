"""
Conversation service for LLM Explorer UI.

This module provides functions to retrieve and organize conversations for the LLM Explorer UI.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta

from sqlalchemy import func, and_, or_, desc, text, case, distinct, String
from sqlalchemy.orm import Session, joinedload

from src.models.event import Event
from src.models.llm_interaction import LLMInteraction
from src.models.agent import Agent
from src.models.trace import Trace
from src.api.schemas.metrics import (
    ConversationSummary, 
    ConversationMessage, 
    ConversationSearchParams,
    LLMRequestDetail
)
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    """Service for retrieving and organizing conversation data."""
    
    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db_session = db_session
    
    def get_conversations(self, search_params: ConversationSearchParams) -> Tuple[List[ConversationSummary], Dict[str, Any]]:
        """
        Get a list of conversations with pagination and filtering.
        
        Args:
            search_params: Search parameters including filters and pagination
            
        Returns:
            Tuple containing list of conversation summaries and pagination info
        """
        logger.info(f"Getting conversations with search params: {search_params}")
        
        # Start with a base query that joins events, llm_interactions, and agents
        base_query = (
            self.db_session.query(
                Event.trace_id,
                func.min(Event.timestamp).label('first_timestamp'),
                func.max(Event.timestamp).label('last_timestamp'),
                Event.agent_id,
                Agent.name.label('agent_name'),
                func.count(distinct(Event.id)).label('event_count'),
                func.count(distinct(LLMInteraction.id)).label('request_count'),
                func.sum(LLMInteraction.total_tokens).label('total_tokens'),
                func.sum(LLMInteraction.input_tokens).label('input_tokens'),
                func.sum(LLMInteraction.output_tokens).label('output_tokens'),
                func.sum(case((LLMInteraction.stop_reason == 'error', 1), else_=0)).label('error_count'),
                func.sum(LLMInteraction.duration_ms).label('total_duration'),
                # Most common model
                func.max(LLMInteraction.model).label('model'),
                func.sum(case((LLMInteraction.interaction_type == 'start', 1), else_=0)
                       ).label('user_messages'),
                func.sum(case((LLMInteraction.interaction_type == 'finish', 1), else_=0)
                       ).label('assistant_messages')
            )
            .join(LLMInteraction, Event.id == LLMInteraction.event_id)
            .join(Agent, Event.agent_id == Agent.agent_id, isouter=True)
            .filter(Event.trace_id.isnot(None))
            .group_by(Event.trace_id, Event.agent_id, Agent.name)
        )
        
        # Apply search filters
        query = self._apply_conversation_filters(base_query, search_params)
        
        # Count total before pagination
        total_count = query.count()
        
        # Apply pagination
        page = search_params.page
        page_size = search_params.page_size
        offset = (page - 1) * page_size
        
        # Order by most recent conversation first
        query = query.order_by(desc('last_timestamp')).offset(offset).limit(page_size)
        
        # Execute query
        results = query.all()
        
        # Process results into conversation summaries
        conversations = []
        
        for row in results:
            # Determine status based on error count
            status = "success"
            if row.error_count and row.error_count > 0:
                status = "error" if row.error_count == row.request_count else "mixed"
            
            # Calculate total tokens with fallback logic
            total_tokens = row.total_tokens
            if total_tokens is None or total_tokens == 0:
                # Try calculating from input and output
                if row.input_tokens or row.output_tokens:
                    total_tokens = (row.input_tokens or 0) + (row.output_tokens or 0)
                
                # If we still don't have tokens, estimate based on request count
                if (total_tokens is None or total_tokens == 0) and row.request_count:
                    # Rough estimate - 500 tokens per request on average
                    total_tokens = row.request_count * 500
            
            logger.debug(f"Conversation {row.trace_id}: total_tokens={total_tokens}, " +
                        f"input={row.input_tokens}, output={row.output_tokens}")
            
            conversation = ConversationSummary(
                trace_id=row.trace_id,
                first_timestamp=row.first_timestamp,
                last_timestamp=row.last_timestamp,
                agent_id=row.agent_id,
                agent_name=row.agent_name or f"Agent-{row.agent_id[:8]}",
                model=row.model,
                request_count=row.request_count,
                total_tokens=total_tokens or 0,
                status=status,
                duration_ms=row.total_duration or 0,
                user_messages=row.user_messages or 0,
                assistant_messages=row.assistant_messages or 0
            )
            conversations.append(conversation)
        
        # Create pagination info
        pagination = {
            "page": page,
            "page_size": page_size,
            "total": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
            "has_next": offset + page_size < total_count,
            "has_prev": page > 1
        }
        
        return conversations, pagination
    
    def get_conversation_messages(self, trace_id: str, page: int = 1, page_size: int = 50) -> Tuple[List[ConversationMessage], Dict[str, Any]]:
        """
        Get messages for a specific conversation.
        
        Args:
            trace_id: Trace ID for the conversation
            page: Page number
            page_size: Items per page
            
        Returns:
            Tuple containing list of conversation messages and pagination info
        """
        logger.info(f"Getting conversation messages for trace_id: {trace_id}")
        
        # Query for all events and LLM interactions in this trace
        query = (
            self.db_session.query(
                Event.id.label('event_id'),
                Event.timestamp,
                Event.trace_id,
                Event.span_id,
                Event.parent_span_id,
                Event.agent_id,
                Agent.name.label('agent_name'),
                LLMInteraction.id.label('interaction_id'),
                LLMInteraction.model,
                LLMInteraction.interaction_type,
                LLMInteraction.request_data,
                LLMInteraction.response_content,
                LLMInteraction.duration_ms,
                LLMInteraction.input_tokens,
                LLMInteraction.output_tokens,
                LLMInteraction.total_tokens,
                LLMInteraction.stop_reason,
                LLMInteraction.related_interaction_id
            )
            .join(LLMInteraction, Event.id == LLMInteraction.event_id)
            .join(Agent, Event.agent_id == Agent.agent_id, isouter=True)
            .filter(Event.trace_id == trace_id)
            .order_by(Event.timestamp.asc())
        )
        
        # Execute query
        results = query.all()
        
        # Group related interactions by span_id
        spans = {}
        for row in results:
            if row.span_id not in spans:
                spans[row.span_id] = []
            spans[row.span_id].append(row)
        
        # Create messages with clear indication of request vs response
        messages = []
        
        # Process all spans
        for span_id, span_rows in spans.items():
            # Sort by timestamp to ensure request comes before response
            span_rows.sort(key=lambda x: x.timestamp)
            
            # Find the start and finish interactions
            request_row = None
            response_row = None
            
            for row in span_rows:
                if row.interaction_type == 'finish':
                    if not response_row:  # Take the first finish as the response
                        response_row = row
                else:  # 'start' or other types
                    if not request_row:  # Take the first non-finish as the request
                        request_row = row
            
            # Create local variables for token information, don't modify the query results directly
            req_input_tokens = None
            resp_output_tokens = None
            
            # Share token information between request and response if available
            if request_row and response_row:
                # If request has no input tokens but response does, copy them
                if (request_row.input_tokens is None or request_row.input_tokens == 0) and response_row.input_tokens:
                    req_input_tokens = response_row.input_tokens
                else:
                    req_input_tokens = request_row.input_tokens
                    
                # If response has no output tokens but total tokens are available, calculate them
                if (response_row.output_tokens is None or response_row.output_tokens == 0) and response_row.total_tokens:
                    if response_row.input_tokens:
                        resp_output_tokens = response_row.total_tokens - response_row.input_tokens
                    else:
                        # Assume a typical ratio if we only have total tokens
                        resp_output_tokens = int(response_row.total_tokens * 0.4)  # 40% of total as output
                else:
                    resp_output_tokens = response_row.output_tokens
            
            # If we have a request row, create a request message
            if request_row:
                # Extract content from request data
                content = self._extract_message_content(request_row.request_data)
                
                # Skip if empty content and not the only message
                if not content and response_row:
                    content = "<Request data not available>"
                
                # Determine message type and role
                message_type = "request"
                role = self._determine_role(request_row.request_data, default="user")
                
                # Determine input tokens with multiple fallbacks
                input_tokens = req_input_tokens if req_input_tokens is not None else request_row.input_tokens
                
                # Try to get from total tokens
                if input_tokens is None and request_row.total_tokens:
                    input_tokens = request_row.total_tokens
                
                # Estimate from content as last resort
                if input_tokens is None and content:
                    input_tokens = self._estimate_token_count(content)
                
                # Default to non-null value
                if input_tokens is None:
                    input_tokens = 0
                
                # Create request message
                messages.append(ConversationMessage(
                    id=f"{request_row.event_id}_{request_row.interaction_id}",
                    timestamp=request_row.timestamp,
                    trace_id=request_row.trace_id,
                    span_id=request_row.span_id,
                    model=request_row.model,
                    role=role,
                    message_type=message_type,
                    status="pending" if response_row else "error",
                    duration_ms=request_row.duration_ms or 0,  # Set to 0 instead of null
                    input_tokens=input_tokens,  # Now this will never be null
                    output_tokens=0,  # Request has no output tokens
                    content=content,
                    parent_id=None,  # We'll set this later
                    agent_id=request_row.agent_id,
                    agent_name=request_row.agent_name or f"Agent-{request_row.agent_id[:8]}",
                    event_id=request_row.event_id  # Add the source event ID
                ))
            
            # If we have a response row, create a response message
            if response_row:
                # Extract content from response content
                content = self._extract_message_content(response_row.response_content)
                
                # Provide a placeholder if no content
                if not content:
                    content = "<Response data not available>"
                    
                # Determine message type and role
                message_type = "response"
                role = "assistant"
                
                # Determine status
                status = "success"
                if response_row.stop_reason and response_row.stop_reason != 'end_turn':
                    status = "error"
                
                # Determine output tokens with multiple fallbacks
                output_tokens = resp_output_tokens if resp_output_tokens is not None else response_row.output_tokens
                
                # Try to get from total tokens if we have input tokens
                if output_tokens is None and response_row.total_tokens:
                    if response_row.input_tokens:
                        output_tokens = response_row.total_tokens - response_row.input_tokens
                    else:
                        # Assume a typical ratio if we only have total tokens
                        output_tokens = int(response_row.total_tokens * 0.4)  # 40% of total as output
                
                # Estimate from content as last resort
                if output_tokens is None and content:
                    output_tokens = self._estimate_token_count(content)
                
                # Default to non-null value
                if output_tokens is None:
                    output_tokens = 0
                
                # Create response message with parent reference to request if it exists
                request_id = f"{request_row.event_id}_{request_row.interaction_id}" if request_row else None
                
                messages.append(ConversationMessage(
                    id=f"{response_row.event_id}_{response_row.interaction_id}",
                    timestamp=response_row.timestamp,
                    trace_id=response_row.trace_id,
                    span_id=response_row.span_id,
                    model=response_row.model,
                    role=role,
                    message_type=message_type,
                    status=status,
                    duration_ms=response_row.duration_ms or 0,  # Set to 0 instead of null
                    input_tokens=0,  # Response has no input tokens (they're on the request)
                    output_tokens=output_tokens,
                    content=content,
                    parent_id=request_id,
                    agent_id=response_row.agent_id,
                    agent_name=response_row.agent_name or f"Agent-{response_row.agent_id[:8]}",
                    event_id=response_row.event_id  # Add the source event ID
                ))
        
        # Ensure messages are sorted by timestamp
        messages.sort(key=lambda x: x.timestamp)
        
        # Now apply pagination
        total_messages = len(messages)
        offset = (page - 1) * page_size
        end_idx = min(offset + page_size, total_messages)
        
        # Check if we have a valid range
        if offset >= total_messages:
            paginated_messages = []
        else:
            paginated_messages = messages[offset:end_idx]
        
        # Create pagination info
        pagination = {
            "page": page,
            "page_size": page_size,
            "total": total_messages,
            "total_pages": (total_messages + page_size - 1) // page_size,
            "has_next": end_idx < total_messages,
            "has_prev": page > 1
        }
        
        return paginated_messages, pagination
    
    def get_llm_requests(self, 
                        agent_id: Optional[str] = None,
                        model: Optional[str] = None, 
                        from_time: Optional[datetime] = None,
                        to_time: Optional[datetime] = None,
                        page: int = 1, 
                        page_size: int = 20) -> Tuple[List[LLMRequestDetail], Dict[str, Any]]:
        """
        Get LLM requests with agent information included.
        
        Args:
            agent_id: Optional agent ID filter
            model: Optional model filter
            from_time: Optional start time
            to_time: Optional end time
            page: Page number
            page_size: Items per page
            
        Returns:
            Tuple containing list of LLM requests and pagination info
        """
        logger.info("Getting LLM requests with agent information")
        
        # Base query
        query = (
            self.db_session.query(
                Event.id.label('event_id'),
                Event.timestamp,
                Event.trace_id,
                Event.span_id,
                Event.agent_id,
                Agent.name.label('agent_name'),
                LLMInteraction.id.label('interaction_id'),
                LLMInteraction.model,
                LLMInteraction.duration_ms,
                LLMInteraction.input_tokens,
                LLMInteraction.output_tokens,
                LLMInteraction.total_tokens,
                LLMInteraction.stop_reason,
                LLMInteraction.request_data,
                LLMInteraction.response_content,
                LLMInteraction.related_interaction_id,
                LLMInteraction.interaction_type
            )
            .join(LLMInteraction, Event.id == LLMInteraction.event_id)
            .join(Agent, Event.agent_id == Agent.agent_id, isouter=True)
            .filter(LLMInteraction.interaction_type == 'finish')  # Only include finished interactions
        )
        
        # Apply filters
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
            
        if model:
            query = query.filter(LLMInteraction.model == model)
            
        if from_time and to_time:
            query = query.filter(Event.timestamp.between(from_time, to_time))
            
        # Count total before pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(Event.timestamp.desc()).offset(offset).limit(page_size)
        
        # Execute query
        results = query.all()
        
        # Process into request details
        requests = []
        
        for row in results:
            # Determine status
            status = "success"
            if row.stop_reason and row.stop_reason != 'end_turn':
                status = "error"
            
            # If this interaction has a related interaction, try to fetch it for the request data
            start_data = None
            if row.related_interaction_id:
                # Get the related start interaction
                try:
                    start_row = (
                        self.db_session.query(LLMInteraction.request_data)
                        .filter(LLMInteraction.id == row.related_interaction_id)
                        .first()
                    )
                    if start_row and start_row.request_data:
                        start_data = start_row.request_data
                except Exception as e:
                    logger.warning(f"Error fetching related interaction: {e}")
                
            # Use request data from either finish or start interaction
            request_data = row.request_data
            if (not request_data or request_data == '{}' or request_data == {}) and start_data:
                request_data = start_data
                
            # Extract content using our comprehensive extractor method
            request_content = self._extract_message_content(request_data)
            response_content = self._extract_message_content(row.response_content)
            
            # Add placeholders if content is empty
            if not request_content:
                request_content = "<Request data not available>"
                
            if not response_content:
                response_content = "<Response data not available>"
            
            # Create the request object
            request = LLMRequestDetail(
                id=f"{row.event_id}_{row.interaction_id}",
                timestamp=row.timestamp,
                trace_id=row.trace_id,
                span_id=row.span_id,
                model=row.model,
                status=status,
                duration_ms=row.duration_ms or 0,  # Ensure duration is never null
                input_tokens=row.input_tokens or 0,  # Ensure tokens are never null
                output_tokens=row.output_tokens or 0,
                agent_id=row.agent_id,
                agent_name=row.agent_name or f"Agent-{row.agent_id[:8]}",
                content=request_content,
                response=response_content
            )
            requests.append(request)
        
        # Create pagination info
        pagination = {
            "page": page,
            "page_size": page_size,
            "total": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
            "has_next": offset + page_size < total_count,
            "has_prev": page > 1
        }
        
        return requests, pagination
    
    def get_request_details(self, request_id: str) -> Optional[LLMRequestDetail]:
        """
        Get details for a specific LLM request.
        
        Args:
            request_id: Request ID in format "{event_id}_{interaction_id}"
            
        Returns:
            LLM request details or None if not found
        """
        logger.info(f"Getting LLM request details for request_id: {request_id}")
        
        try:
            # Parse event_id and interaction_id from request_id
            ids = request_id.split('_')
            if len(ids) != 2:
                raise ValueError(f"Invalid request_id format: {request_id}")
                
            event_id = int(ids[0])
            interaction_id = int(ids[1])
            
            # Query for this specific request and also for related start requests
            row = (
                self.db_session.query(
                    Event.id.label('event_id'),
                    Event.timestamp,
                    Event.trace_id,
                    Event.span_id,
                    Event.agent_id,
                    Agent.name.label('agent_name'),
                    LLMInteraction.id.label('interaction_id'),
                    LLMInteraction.model,
                    LLMInteraction.duration_ms,
                    LLMInteraction.input_tokens,
                    LLMInteraction.output_tokens,
                    LLMInteraction.total_tokens,
                    LLMInteraction.stop_reason,
                    LLMInteraction.request_data,
                    LLMInteraction.response_content,
                    LLMInteraction.related_interaction_id,
                    LLMInteraction.interaction_type
                )
                .join(LLMInteraction, Event.id == LLMInteraction.event_id)
                .join(Agent, Event.agent_id == Agent.agent_id, isouter=True)
                .filter(Event.id == event_id, LLMInteraction.id == interaction_id)
                .first()
            )
            
            if not row:
                return None
            
            # If this is a 'finish' interaction with empty request_data, try to find the related 'start' interaction
            start_data = None
            if (row.interaction_type == 'finish' and 
                (not row.request_data or row.request_data == '{}' or row.request_data == {})):
                if row.related_interaction_id:
                    # Get the related start interaction
                    start_row = (
                        self.db_session.query(LLMInteraction.request_data)
                        .filter(LLMInteraction.id == row.related_interaction_id)
                        .first()
                    )
                    if start_row and start_row.request_data:
                        start_data = start_row.request_data
                        logger.debug(f"Found related start interaction with request_data: {start_data}")
            
            # Debug log the actual data structures
            logger.debug(f"Request details data for interaction {row.interaction_id}:")
            logger.debug(f"Request data: {row.request_data}")
            logger.debug(f"Start data (if any): {start_data}")
            logger.debug(f"Response content: {row.response_content}")
            logger.debug(f"Tokens: input={row.input_tokens}, output={row.output_tokens}, total={row.total_tokens}")
            
            # Determine status
            status = "success"
            if row.stop_reason and row.stop_reason != 'end_turn':
                status = "error"
            
            # Use request data from either finish or start interaction
            request_data = row.request_data
            if (not request_data or request_data == '{}' or request_data == {}) and start_data:
                request_data = start_data
            
            # Extract content from request and response with multiple extraction strategies
            request_content = None
            response_content = None
            
            try:
                # Extract request content
                if request_data:
                    if isinstance(request_data, str):
                        request_content = request_data
                    elif isinstance(request_data, dict):
                        # Direct content field
                        if 'content' in request_data:
                            request_content = request_data['content']
                        
                        # Messages array - construct a readable format
                        elif 'messages' in request_data and isinstance(request_data['messages'], list):
                            messages = []
                            for msg in request_data['messages']:
                                if isinstance(msg, dict):
                                    role = msg.get('role', 'unknown')
                                    content = msg.get('content', '')
                                    if content:
                                        messages.append(f"{role}: {content}")
                            if messages:
                                request_content = "\n\n".join(messages)
                        
                        # Prompt field (common in some APIs)
                        elif 'prompt' in request_data:
                            request_content = request_data['prompt']
                        
                        # If nothing matches, show the structure
                        else:
                            request_content = f"<Structured data: {', '.join(request_data.keys())}>"
                
                # Extract response content
                if row.response_content:
                    if isinstance(row.response_content, str):
                        response_content = row.response_content
                    elif isinstance(row.response_content, dict):
                        # Handle various response formats
                        if 'content' in row.response_content:
                            response_content = row.response_content['content']
                        elif 'text' in row.response_content:
                            response_content = row.response_content['text']
                        elif 'message' in row.response_content:
                            if isinstance(row.response_content['message'], dict):
                                response_content = row.response_content['message'].get('content', '')
                            else:
                                response_content = str(row.response_content['message'])
                        elif 'choices' in row.response_content and isinstance(row.response_content['choices'], list):
                            if row.response_content['choices']:
                                choice = row.response_content['choices'][0]
                                if isinstance(choice, dict):
                                    if 'message' in choice and isinstance(choice['message'], dict):
                                        response_content = choice['message'].get('content', '')
                                    elif 'text' in choice:
                                        response_content = choice['text']
                        else:
                            response_content = f"<Structured data: {', '.join(row.response_content.keys())}>"
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Error extracting content from LLM interaction: {e}", exc_info=True)
                if not request_content:
                    request_content = f"<Error extracting request: {e}>"
                if not response_content:
                    response_content = f"<Error extracting response: {e}>"
            
            # Set token counts with fallbacks
            input_tokens = row.input_tokens
            output_tokens = row.output_tokens
            
            # If tokens are null but we have a total, split the total between input and output
            if row.total_tokens and (input_tokens is None or output_tokens is None):
                # Typical ratio is about 2/3 input, 1/3 output
                input_tokens = row.input_tokens or int(row.total_tokens * 0.67)
                output_tokens = row.output_tokens or (row.total_tokens - input_tokens)
            
            return LLMRequestDetail(
                id=request_id,
                timestamp=row.timestamp,
                trace_id=row.trace_id,
                span_id=row.span_id,
                model=row.model,
                status=status,
                duration_ms=row.duration_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                agent_id=row.agent_id,
                agent_name=row.agent_name or f"Agent-{row.agent_id[:8]}",
                content=request_content,
                response=response_content
            )
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing request_id: {e}")
            return None
    
    def _apply_conversation_filters(self, query, search_params: ConversationSearchParams):
        """Apply search filters to the conversation query."""
        
        if search_params.agent_id:
            query = query.filter(Event.agent_id == search_params.agent_id)
            
        if search_params.from_time and search_params.to_time:
            query = query.filter(Event.timestamp.between(search_params.from_time, search_params.to_time))
            
        if search_params.token_min is not None:
            query = query.having(func.sum(LLMInteraction.total_tokens) >= search_params.token_min)
            
        if search_params.token_max is not None:
            query = query.having(func.sum(LLMInteraction.total_tokens) <= search_params.token_max)
            
        if search_params.has_error is not None:
            if search_params.has_error:
                query = query.having(func.sum(case((LLMInteraction.stop_reason == 'error', 1), else_=0)) > 0)
            else:
                query = query.having(func.sum(case((LLMInteraction.stop_reason == 'error', 1), else_=0)) == 0)
                
        if search_params.status:
            if search_params.status == 'error':
                query = query.having(
                    func.sum(case((LLMInteraction.stop_reason == 'error', 1), else_=0)) > 0
                )
            elif search_params.status == 'success':
                query = query.having(
                    func.sum(case((LLMInteraction.stop_reason == 'error', 1), else_=0)) == 0
                )
                
        if search_params.query:
            # Full text search across conversation content
            # This is a simplified implementation - in production you'd want a proper full-text search
            like_pattern = f"%{search_params.query}%"
            content_subquery = (
                self.db_session.query(Event.trace_id)
                .join(LLMInteraction, Event.id == LLMInteraction.event_id)
                .filter(
                    or_(
                        func.json_extract(LLMInteraction.request_data, '$.content').cast(String).ilike(like_pattern),
                        func.cast(LLMInteraction.response_content, String).ilike(like_pattern)
                    )
                )
                .distinct()
                .subquery()
            )
            
            query = query.filter(Event.trace_id.in_(content_subquery))
            
        return query
    
    def _get_conversation_summary(self, trace_id: str) -> str:
        """Get a summary for a conversation, using the first user message as the summary."""
        
        # Find the first user message in this conversation
        first_message = (
            self.db_session.query(LLMInteraction.request_data, LLMInteraction.response_content)
            .join(Event, Event.id == LLMInteraction.event_id)
            .filter(
                Event.trace_id == trace_id,
                LLMInteraction.interaction_type == 'finish'
            )
            .order_by(Event.timestamp.asc())
            .first()
        )
        
        if first_message:
            # Try to extract content from request_data
            if first_message.request_data:
                # Try different possible structures
                if isinstance(first_message.request_data, dict):
                    # Direct content field
                    if 'content' in first_message.request_data:
                        content = first_message.request_data['content']
                        if content and len(content) > 0:
                            return self._truncate_summary(content)
                    
                    # Role-based content in messages array
                    if 'messages' in first_message.request_data:
                        # Look for the first user message in the messages array
                        for msg in first_message.request_data['messages']:
                            if isinstance(msg, dict) and 'content' in msg and msg.get('role') == 'user':
                                content = msg['content']
                                if content and len(content) > 0:
                                    return self._truncate_summary(content)
            
            # If nothing found in request_data, try response_content
            if first_message.response_content:
                if isinstance(first_message.response_content, str):
                    return self._truncate_summary(first_message.response_content)
                elif isinstance(first_message.response_content, dict) and 'content' in first_message.response_content:
                    return self._truncate_summary(first_message.response_content['content'])
            
        return "No summary available"

    def _truncate_summary(self, content: str) -> str:
        """Truncate summary if too long."""
        if not content:
            return "No summary available"
        
        if len(content) > 100:
            return content[:97] + "..."
        return content

    def _estimate_token_count(self, content: str) -> int:
        """Provide a rough estimation of token count based on content length.
        
        Approximation: 1 token ~= 4 characters for English text
        """
        if not content:
            return 0
            
        # For very short messages, minimum token count
        if len(content) < 10:
            return 5
            
        # Rough approximation: ~4 chars per token for English
        return max(1, len(content) // 4)
        
    def _extract_message_content(self, data) -> str:
        """Extract clean message content from various data structures."""
        if not data:
            return ""
        
        try:
            # If it's a string, use directly
            if isinstance(data, str):
                return data
            
            # If it's a list (array), look for objects with 'text' field
            if isinstance(data, list):
                texts = []
                for item in data:
                    if isinstance(item, dict):
                        if 'text' in item:
                            texts.append(item['text'])
                if texts:
                    return "\n".join(texts)
            
            # If it's a dict, try different common formats
            if isinstance(data, dict):
                # Direct content field
                if 'content' in data and data['content']:
                    return data['content']
                
                # Special case: messages stored as a string that represents a list
                if 'messages' in data and isinstance(data['messages'], str) and (data['messages'].startswith('[') or data['messages'].startswith("'")):
                    try:
                        # Try to extract content from the string representation of the messages list
                        # This handles cases like: {"messages": "[{'role': 'user', 'content': 'some text'}]"}
                        msg_str = data['messages']
                        
                        # Look for content directly in the string
                        import re
                        content_match = re.search(r"'content':\s*'([^']*)'", msg_str)
                        if content_match:
                            return content_match.group(1)
                        
                        # If regex fails, try safer approach - just return the raw content
                        if "content" in msg_str and len(msg_str) < 200:
                            return f"Input: {msg_str}"
                    except Exception as e:
                        logger.debug(f"Failed to parse string messages: {e}")
                        # Return something readable for this case
                        return "User input (formatted as string)"
                
                # Message array - extract the last user/assistant message
                if 'messages' in data and isinstance(data['messages'], list) and data['messages']:
                    # First look for non-system messages
                    for msg in reversed(data['messages']):
                        if isinstance(msg, dict) and 'content' in msg and msg['content'] and msg.get('role', '') != 'system':
                            return msg['content']
                        
                        # If no non-system messages, take any message with content
                        for msg in reversed(data['messages']):
                            if isinstance(msg, dict) and 'content' in msg and msg['content']:
                                return msg['content']
                
                # OpenAI choices format
                if 'choices' in data and isinstance(data['choices'], list) and data['choices']:
                    choice = data['choices'][0]
                    if isinstance(choice, dict):
                        if 'message' in choice and isinstance(choice['message'], dict) and 'content' in choice['message']:
                            return choice['message']['content']
                        if 'text' in choice:
                            return choice['text']
                        
                # Text field
                if 'text' in data and data['text']:
                    return data['text']
                
                # Message field
                if 'message' in data:
                    if isinstance(data['message'], dict) and 'content' in data['message']:
                        return data['message']['content']
                    return str(data['message'])
                
                # Prompt field
                if 'prompt' in data and data['prompt']:
                    return data['prompt']
                
                # If we have structured data with potential sensitive data, sanitize the output
                if 'messages' in data and 'model' in data:
                    # This is likely an LLM request with potential sensitive information
                    return "User input (content redacted for privacy)"
                
                # If we have structured data, give a hint
                if data:
                    return f"<Structured data with keys: {', '.join(data.keys())}>"
        except Exception as e:
            logger.warning(f"Error extracting message content: {e}", exc_info=True)
            return f"<Error extracting content: {str(e)[:50]}...>"
        
        return ""
    
    def _determine_role(self, data, default="system") -> str:
        """Determine the role from message data."""
        if not data:
            return default
        
        try:
            # Direct role field
            if isinstance(data, dict) and 'role' in data:
                return data['role']
            
            # Role in messages array
            if isinstance(data, dict) and 'messages' in data and isinstance(data['messages'], list) and data['messages']:
                # Take the last message's role
                last_msg = data['messages'][-1]
                if isinstance(last_msg, dict) and 'role' in last_msg:
                    return last_msg['role']
        except Exception:
            pass
        
        return default


# Initialize conversation service
def get_conversation_service(db_session: Session) -> ConversationService:
    """Get an instance of the conversation service with a database session."""
    return ConversationService(db_session) 