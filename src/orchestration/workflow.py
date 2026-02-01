"""Workflow state machine for managing job stages."""

from enum import Enum
from typing import Dict, List


class WorkflowStage(Enum):
    """Workflow stages for the SWE engineering pipeline."""

    INITIALIZATION = "initialization"
    PRD_GENERATION = "prd_generation"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    PLAN_GENERATION = "plan_generation"
    ARCHITECTURE_DESIGN = "architecture_design"
    UIUX_DESIGN = "uiux_design"
    DEVELOPMENT = "development"
    QA_TESTING = "qa_testing"
    SECURITY_REVIEW = "security_review"
    DOCUMENTATION = "documentation"
    SUPPORT_DOCS = "support_docs"
    PM_REVIEW = "pm_review"
    DELIVERY = "delivery"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStateMachine:
    """Manages job state transitions through the workflow."""

    # Define valid transitions between stages
    TRANSITIONS: Dict[WorkflowStage, List[WorkflowStage]] = {
        WorkflowStage.INITIALIZATION: [
            WorkflowStage.PRD_GENERATION,
            WorkflowStage.FAILED
        ],
        WorkflowStage.PRD_GENERATION: [
            WorkflowStage.WAITING_FOR_APPROVAL,
            WorkflowStage.FAILED
        ],
        WorkflowStage.WAITING_FOR_APPROVAL: [
            WorkflowStage.PLAN_GENERATION,
            WorkflowStage.FAILED
        ],
        WorkflowStage.PLAN_GENERATION: [
            WorkflowStage.ARCHITECTURE_DESIGN,
            WorkflowStage.FAILED
        ],
        WorkflowStage.ARCHITECTURE_DESIGN: [
            WorkflowStage.UIUX_DESIGN,
            WorkflowStage.FAILED
        ],
        WorkflowStage.UIUX_DESIGN: [
            WorkflowStage.DEVELOPMENT,
            WorkflowStage.FAILED
        ],
        WorkflowStage.DEVELOPMENT: [
            WorkflowStage.QA_TESTING,
            WorkflowStage.SECURITY_REVIEW,
            WorkflowStage.DOCUMENTATION,
            WorkflowStage.SUPPORT_DOCS,
            WorkflowStage.FAILED
        ],
        WorkflowStage.QA_TESTING: [
            WorkflowStage.SECURITY_REVIEW,
            WorkflowStage.FAILED
        ],
        WorkflowStage.SECURITY_REVIEW: [
            WorkflowStage.PM_REVIEW,
            WorkflowStage.FAILED
        ],
        WorkflowStage.DOCUMENTATION: [
            WorkflowStage.PM_REVIEW,
            WorkflowStage.FAILED
        ],
        WorkflowStage.SUPPORT_DOCS: [
            WorkflowStage.PM_REVIEW,
            WorkflowStage.FAILED
        ],
        WorkflowStage.PM_REVIEW: [
            WorkflowStage.DELIVERY,
            WorkflowStage.FAILED
        ],
        WorkflowStage.DELIVERY: [
            WorkflowStage.COMPLETED,
            WorkflowStage.FAILED
        ],
        WorkflowStage.COMPLETED: [],
        WorkflowStage.FAILED: []
    }

    # Map stages to required agents
    STAGE_AGENTS: Dict[WorkflowStage, str] = {
        WorkflowStage.PRD_GENERATION: "prd_agent",
        WorkflowStage.PLAN_GENERATION: "plan_agent",
        WorkflowStage.ARCHITECTURE_DESIGN: "architect_agent",
        WorkflowStage.UIUX_DESIGN: "uiux_agent",
        WorkflowStage.DEVELOPMENT: "developer_agent",
        WorkflowStage.QA_TESTING: "qa_agent",
        WorkflowStage.SECURITY_REVIEW: "security_agent",
        WorkflowStage.DOCUMENTATION: "tech_writer",
        WorkflowStage.SUPPORT_DOCS: "support_engineer",
        WorkflowStage.PM_REVIEW: "product_manager",
        WorkflowStage.DELIVERY: "delivery_agent",
    }

    # Stages that can run in parallel
    PARALLEL_STAGES = {
        WorkflowStage.QA_TESTING,
        WorkflowStage.SECURITY_REVIEW,
        WorkflowStage.DOCUMENTATION,
        WorkflowStage.SUPPORT_DOCS
    }

    def __init__(self):
        self.current_stage = WorkflowStage.INITIALIZATION

    def can_transition(self, from_stage: WorkflowStage, to_stage: WorkflowStage) -> bool:
        """
        Check if transition is valid.

        Args:
            from_stage: Current stage
            to_stage: Target stage

        Returns:
            True if transition is valid
        """
        return to_stage in self.TRANSITIONS.get(from_stage, [])

    def get_next_stages(self, current_stage: WorkflowStage) -> List[WorkflowStage]:
        """
        Get possible next stages.

        Args:
            current_stage: Current workflow stage

        Returns:
            List of possible next stages
        """
        return self.TRANSITIONS.get(current_stage, [])

    def get_agent_for_stage(self, stage: WorkflowStage) -> str:
        """
        Get the agent responsible for a stage.

        Args:
            stage: Workflow stage

        Returns:
            Agent ID
        """
        return self.STAGE_AGENTS.get(stage, "unknown")

    def is_parallel_stage(self, stage: WorkflowStage) -> bool:
        """
        Check if stage can run in parallel with others.

        Args:
            stage: Workflow stage

        Returns:
            True if stage can run in parallel
        """
        return stage in self.PARALLEL_STAGES

    def get_parallel_stages_after(self, stage: WorkflowStage) -> List[WorkflowStage]:
        """
        Get stages that should run in parallel after the given stage.

        Args:
            stage: Current workflow stage

        Returns:
            List of stages to run in parallel
        """
        if stage == WorkflowStage.DEVELOPMENT:
            return [
                WorkflowStage.QA_TESTING,
                WorkflowStage.SECURITY_REVIEW,
                WorkflowStage.DOCUMENTATION,
                WorkflowStage.SUPPORT_DOCS
            ]
        return []
