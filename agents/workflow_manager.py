"""
Smart Workflow Manager for ModuMentor
Enables intelligent chaining of multiple tools and actions
"""
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
from enum import Enum
import google.generativeai as genai
from config import config


class WorkflowStepType(Enum):
    """Types of workflow steps"""
    TOOL_EXECUTION = "tool_execution"
    DATA_PROCESSING = "data_processing"
    CONDITIONAL = "conditional"
    NOTIFICATION = "notification"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    step_id: str
    step_type: WorkflowStepType
    tool_name: str
    action: str
    parameters: Dict[str, Any]
    depends_on: List[str] = None
    condition: str = None
    output_variable: str = None


@dataclass
class WorkflowResult:
    """Result of workflow execution"""
    success: bool
    steps_completed: int
    total_steps: int
    results: Dict[str, Any]
    final_output: str
    execution_time: float
    errors: List[str] = None


class SmartWorkflowManager:
    """Manages intelligent workflow automation"""
    
    def __init__(self, tool_manager):
        self.tool_manager = tool_manager
        self.active_workflows: Dict[str, Dict] = {}
        
        # Configure Gemini for workflow planning
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        # Predefined workflow patterns
        self.workflow_patterns = {
            "weather_email": {
                "triggers": ["weather.*email", "check weather.*send", "weather.*notify"],
                "template": "weather_then_email"
            },
            "research_update": {
                "triggers": ["search.*update", "research.*spreadsheet", "find.*add to sheet"],
                "template": "search_then_update_sheet"
            },
            "data_analysis_report": {
                "triggers": ["analyze.*email", "sheet.*summary.*email", "data.*report"],
                "template": "analyze_data_then_email"
            },
            "meeting_prep": {
                "triggers": ["meeting.*weather.*email", "prepare.*meeting", "meeting prep"],
                "template": "meeting_preparation"
            }
        }
        
        logger.info("SmartWorkflowManager initialized")
    
    async def detect_workflow_intent(self, query: str) -> Optional[str]:
        """Detect if query requires a workflow and return workflow type"""
        query_lower = query.lower()
        
        # Check for workflow trigger patterns
        for workflow_name, pattern_info in self.workflow_patterns.items():
            for trigger in pattern_info["triggers"]:
                if re.search(trigger, query_lower):
                    logger.info(f"Detected workflow intent: {workflow_name}")
                    return workflow_name
        
        # Use AI to detect complex workflow patterns
        return await self._ai_workflow_detection(query)
    
    async def _ai_workflow_detection(self, query: str) -> Optional[str]:
        """Use AI to detect complex workflow patterns"""
        try:
            prompt = f"""
Analyze this user request and determine if it requires multiple sequential actions (a workflow):

Query: "{query}"

Available workflow types:
1. weather_email - Check weather then send email
2. research_update - Search/research then update spreadsheet
3. data_analysis_report - Analyze data then email summary
4. meeting_prep - Prepare for meeting (weather, emails, etc.)

If this requires multiple sequential actions, respond with the workflow type.
If it's a single action, respond with "none".

Response (just the workflow type or "none"):"""

            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            if response and response.text:
                result = response.text.strip().lower()
                if result in self.workflow_patterns:
                    return result
                    
        except Exception as e:
            logger.error(f"Error in AI workflow detection: {e}")
        
        return None
    
    async def create_workflow(self, workflow_type: str, query: str, user_context: Dict = None) -> List[WorkflowStep]:
        """Create a workflow based on type and query"""
        if workflow_type == "weather_email":
            return await self._create_weather_email_workflow(query, user_context)
        elif workflow_type == "research_update":
            return await self._create_research_update_workflow(query, user_context)
        elif workflow_type == "data_analysis_report":
            return await self._create_data_analysis_workflow(query, user_context)
        elif workflow_type == "meeting_prep":
            return await self._create_meeting_prep_workflow(query, user_context)
        else:
            return await self._create_custom_workflow(query, user_context)
    
    async def _create_weather_email_workflow(self, query: str, context: Dict = None) -> List[WorkflowStep]:
        """Create weather + email workflow"""
        # Extract location and email details from query
        location = self._extract_location(query) or "current location"
        email_context = self._extract_email_context(query)
        
        steps = [
            WorkflowStep(
                step_id="weather_check",
                step_type=WorkflowStepType.TOOL_EXECUTION,
                tool_name="Weather",
                action="get_weather",
                parameters={"location": location, "include_forecast": True},
                output_variable="weather_data"
            ),
            WorkflowStep(
                step_id="compose_email",
                step_type=WorkflowStepType.TOOL_EXECUTION,
                tool_name="Gmail",
                action="send_email",
                parameters={
                    "recipient": email_context.get("recipient", "team"),
                    "subject": f"Weather Update for {location}",
                    "context": "Include weather information from previous step",
                    "template": "weather_notification"
                },
                depends_on=["weather_check"]
            )
        ]
        
        return steps
    
    async def _create_research_update_workflow(self, query: str, context: Dict = None) -> List[WorkflowStep]:
        """Create research + spreadsheet update workflow"""
        search_topic = self._extract_search_topic(query)
        
        steps = [
            WorkflowStep(
                step_id="research",
                step_type=WorkflowStepType.TOOL_EXECUTION,
                tool_name="WebSearch",
                action="search",
                parameters={"query": search_topic, "max_results": 5},
                output_variable="research_data"
            ),
            WorkflowStep(
                step_id="update_sheet",
                step_type=WorkflowStepType.TOOL_EXECUTION,
                tool_name="GoogleSheets",
                action="add_data",
                parameters={
                    "data_source": "research_data",
                    "format": "structured"
                },
                depends_on=["research"]
            )
        ]
        
        return steps
    
    async def execute_workflow(self, steps: List[WorkflowStep], user_id: str = None) -> WorkflowResult:
        """Execute a workflow with intelligent step coordination"""
        import time
        start_time = time.time()
        
        results = {}
        errors = []
        completed_steps = 0
        
        try:
            # Execute steps in dependency order
            for step in self._sort_steps_by_dependencies(steps):
                try:
                    # Check dependencies
                    if step.depends_on:
                        missing_deps = [dep for dep in step.depends_on if dep not in results]
                        if missing_deps:
                            errors.append(f"Missing dependencies for step {step.step_id}: {missing_deps}")
                            continue
                    
                    # Execute step
                    step_result = await self._execute_step(step, results)
                    results[step.step_id] = step_result
                    
                    if step.output_variable:
                        results[step.output_variable] = step_result
                    
                    completed_steps += 1
                    logger.info(f"Completed workflow step: {step.step_id}")
                    
                except Exception as e:
                    error_msg = f"Error in step {step.step_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Generate final output
            final_output = await self._generate_workflow_summary(steps, results, errors)
            
            execution_time = time.time() - start_time
            
            return WorkflowResult(
                success=len(errors) == 0,
                steps_completed=completed_steps,
                total_steps=len(steps),
                results=results,
                final_output=final_output,
                execution_time=execution_time,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return WorkflowResult(
                success=False,
                steps_completed=completed_steps,
                total_steps=len(steps),
                results=results,
                final_output=f"Workflow failed: {str(e)}",
                execution_time=time.time() - start_time,
                errors=errors + [str(e)]
            )
    
    async def _execute_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Any:
        """Execute a single workflow step"""
        if step.step_type == WorkflowStepType.TOOL_EXECUTION:
            # Get the tool
            tool = None
            for t in self.tool_manager.tools:
                if t.name == step.tool_name:
                    tool = t
                    break
            
            if not tool:
                raise ValueError(f"Tool {step.tool_name} not found")
            
            # Prepare parameters with context substitution
            params = self._substitute_context_variables(step.parameters, context)
            
            # Execute tool
            if step.action == "send_email" and step.tool_name == "Gmail":
                return await self._execute_smart_email(params, context)
            else:
                # Build query from parameters
                query = self._build_query_from_params(step.action, params)
                return await tool.execute(query)
        
        return None
    
    def _extract_location(self, query: str) -> Optional[str]:
        """Extract location from query"""
        # Simple location extraction - can be enhanced
        location_patterns = [
            r'in ([A-Za-z\s]+?)(?:\s|$|,)',
            r'for ([A-Za-z\s]+?)(?:\s|$|,)',
            r'at ([A-Za-z\s]+?)(?:\s|$|,)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if len(location) > 2 and location.lower() not in ['the', 'our', 'my', 'his', 'her']:
                    return location
        
        return None
    
    def _extract_email_context(self, query: str) -> Dict[str, str]:
        """Extract email context from query"""
        context = {}
        
        # Extract recipient
        recipient_patterns = [
            r'email\s+(?:the\s+)?([A-Za-z\s]+?)(?:\s+about|\s+regarding|$)',
            r'send.*?to\s+([A-Za-z\s]+?)(?:\s+about|\s+regarding|$)',
            r'notify\s+([A-Za-z\s]+?)(?:\s+about|\s+regarding|$)'
        ]
        
        for pattern in recipient_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                context["recipient"] = match.group(1).strip()
                break
        
        return context
    
    def _extract_search_topic(self, query: str) -> str:
        """Extract search topic from query"""
        # Remove workflow-related words and extract the core topic
        topic_patterns = [
            r'search\s+(?:for\s+)?(.+?)(?:\s+then|\s+and|$)',
            r'research\s+(.+?)(?:\s+then|\s+and|$)',
            r'find\s+(.+?)(?:\s+then|\s+and|$)'
        ]
        
        for pattern in topic_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return query  # Fallback to full query

    def _sort_steps_by_dependencies(self, steps: List[WorkflowStep]) -> List[WorkflowStep]:
        """Sort steps by their dependencies"""
        sorted_steps = []
        remaining_steps = steps.copy()

        while remaining_steps:
            # Find steps with no unmet dependencies
            ready_steps = []
            for step in remaining_steps:
                if not step.depends_on or all(dep in [s.step_id for s in sorted_steps] for dep in step.depends_on):
                    ready_steps.append(step)

            if not ready_steps:
                # Circular dependency or missing dependency
                logger.warning("Circular dependency detected in workflow")
                sorted_steps.extend(remaining_steps)
                break

            # Add ready steps to sorted list
            sorted_steps.extend(ready_steps)
            for step in ready_steps:
                remaining_steps.remove(step)

        return sorted_steps

    def _substitute_context_variables(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute context variables in parameters"""
        substituted = {}

        for key, value in params.items():
            if isinstance(value, str):
                # Replace context variables like {weather_data}
                for var_name, var_value in context.items():
                    if f"{{{var_name}}}" in value:
                        value = value.replace(f"{{{var_name}}}", str(var_value))
                substituted[key] = value
            else:
                substituted[key] = value

        return substituted

    def _build_query_from_params(self, action: str, params: Dict[str, Any]) -> str:
        """Build a natural language query from action and parameters"""
        if action == "get_weather":
            location = params.get("location", "current location")
            return f"What's the weather in {location}?"
        elif action == "search":
            query = params.get("query", "")
            return f"Search for {query}"
        elif action == "add_data":
            return "Add the research data to the spreadsheet"
        else:
            return f"{action} with parameters: {params}"

    async def _execute_smart_email(self, params: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute smart email with context awareness"""
        # Get Gmail tool
        gmail_tool = None
        for tool in self.tool_manager.tools:
            if tool.name == "Gmail":
                gmail_tool = tool
                break

        if not gmail_tool:
            raise ValueError("Gmail tool not found")

        # Build email query with context
        recipient = params.get("recipient", "team")
        subject = params.get("subject", "Update")
        template = params.get("template", "general")

        # Include context data in email
        context_info = ""
        if "weather_data" in context:
            context_info += f"Weather information: {context['weather_data']}\n"
        if "research_data" in context:
            context_info += f"Research findings: {context['research_data']}\n"

        email_query = f"Send email to {recipient} about {subject}. Include this information: {context_info}"

        return await gmail_tool.execute(email_query)

    async def _generate_workflow_summary(self, steps: List[WorkflowStep], results: Dict[str, Any], errors: List[str]) -> str:
        """Generate a summary of workflow execution"""
        try:
            # Create summary prompt
            steps_info = "\n".join([f"- {step.step_id}: {step.action} using {step.tool_name}" for step in steps])
            results_info = "\n".join([f"- {key}: {str(value)[:100]}..." for key, value in results.items()])
            errors_info = "\n".join([f"- {error}" for error in errors]) if errors else "No errors"

            prompt = f"""
Create a concise summary of this workflow execution:

Steps executed:
{steps_info}

Results:
{results_info}

Errors:
{errors_info}

Provide a user-friendly summary of what was accomplished:"""

            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )

            if response and response.text:
                return response.text.strip()

        except Exception as e:
            logger.error(f"Error generating workflow summary: {e}")

        # Fallback summary
        success_count = len(results)
        total_steps = len(steps)

        if errors:
            return f"🔄 **Workflow Completed with Issues**\n\n✅ {success_count}/{total_steps} steps completed\n❌ {len(errors)} errors encountered\n\nSome tasks may need manual attention."
        else:
            return f"🎉 **Workflow Completed Successfully!**\n\n✅ All {total_steps} steps completed\n🚀 Your automated tasks have been executed successfully!"

    async def _create_custom_workflow(self, query: str, context: Dict = None) -> List[WorkflowStep]:
        """Create a custom workflow using AI analysis"""
        try:
            prompt = f"""
Analyze this user request and break it down into sequential workflow steps:

Request: "{query}"

Available tools:
- Weather: Get weather information
- WebSearch: Search the internet
- Gmail: Send emails
- GoogleSheets: Read/write spreadsheet data
- Dictionary: Get word definitions

Create a workflow with these steps (respond in this exact format):
STEP 1: [tool_name] - [action_description]
STEP 2: [tool_name] - [action_description]
...

Only include steps that are clearly needed. Maximum 4 steps."""

            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )

            if response and response.text:
                return self._parse_ai_workflow_response(response.text, query)

        except Exception as e:
            logger.error(f"Error creating custom workflow: {e}")

        # Fallback: single step workflow
        return [
            WorkflowStep(
                step_id="single_action",
                step_type=WorkflowStepType.TOOL_EXECUTION,
                tool_name="WebSearch",
                action="search",
                parameters={"query": query}
            )
        ]

    def _parse_ai_workflow_response(self, response: str, original_query: str) -> List[WorkflowStep]:
        """Parse AI-generated workflow response into WorkflowStep objects"""
        steps = []
        lines = response.strip().split('\n')

        for i, line in enumerate(lines):
            if line.strip().startswith('STEP'):
                try:
                    # Extract step info
                    parts = line.split(':', 1)[1].strip().split(' - ', 1)
                    if len(parts) == 2:
                        tool_name = parts[0].strip()
                        action_desc = parts[1].strip()

                        step = WorkflowStep(
                            step_id=f"step_{i+1}",
                            step_type=WorkflowStepType.TOOL_EXECUTION,
                            tool_name=tool_name,
                            action=action_desc,
                            parameters={"query": original_query},
                            depends_on=[f"step_{i}"] if i > 0 else None
                        )
                        steps.append(step)

                except Exception as e:
                    logger.warning(f"Error parsing workflow step: {line}, error: {e}")

        return steps if steps else [
            WorkflowStep(
                step_id="fallback",
                step_type=WorkflowStepType.TOOL_EXECUTION,
                tool_name="WebSearch",
                action="search",
                parameters={"query": original_query}
            )
        ]
