"""Tests for workflow state machine transitions."""

import pytest
from src.orchestration.workflow import WorkflowStage, WorkflowStateMachine


class TestWorkflowStateMachine:
    """Test the workflow state machine."""

    def test_initialization(self):
        """Test that workflow initializes correctly."""
        workflow = WorkflowStateMachine()
        assert workflow.current_stage == WorkflowStage.INITIALIZATION

    def test_all_stages_have_transitions(self):
        """Verify that all stages (except terminal) have defined transitions."""
        workflow = WorkflowStateMachine()
        terminal_stages = {WorkflowStage.COMPLETED, WorkflowStage.FAILED}
        
        for stage in WorkflowStage:
            if stage not in terminal_stages:
                transitions = workflow.get_next_stages(stage)
                assert len(transitions) > 0, f"Stage {stage.value} has no transitions"

    def test_terminal_stages_have_no_transitions(self):
        """Verify terminal stages cannot transition."""
        workflow = WorkflowStateMachine()
        
        assert workflow.get_next_stages(WorkflowStage.COMPLETED) == []
        assert workflow.get_next_stages(WorkflowStage.FAILED) == []

    def test_completed_state_reachable(self):
        """Verify COMPLETED state is reachable through the workflow."""
        workflow = WorkflowStateMachine()
        
        # Define the expected happy path
        happy_path = [
            WorkflowStage.INITIALIZATION,
            WorkflowStage.PRD_GENERATION,
            WorkflowStage.WAITING_FOR_APPROVAL,
            WorkflowStage.PLAN_GENERATION,
            WorkflowStage.ARCHITECTURE_DESIGN,
            WorkflowStage.UIUX_DESIGN,
            WorkflowStage.DEVELOPMENT,
            WorkflowStage.QA_TESTING,
            WorkflowStage.SECURITY_REVIEW,
            WorkflowStage.PM_REVIEW,
            WorkflowStage.DELIVERY,
            WorkflowStage.COMPLETED
        ]
        
        # Verify each transition in the happy path is valid
        for i in range(len(happy_path) - 1):
            from_stage = happy_path[i]
            to_stage = happy_path[i + 1]
            assert workflow.can_transition(from_stage, to_stage), \
                f"Cannot transition from {from_stage.value} to {to_stage.value}"

    def test_failed_state_reachable_from_all_stages(self):
        """Verify FAILED state is reachable from all non-terminal stages."""
        workflow = WorkflowStateMachine()
        terminal_stages = {WorkflowStage.COMPLETED, WorkflowStage.FAILED}
        
        for stage in WorkflowStage:
            if stage not in terminal_stages:
                assert workflow.can_transition(stage, WorkflowStage.FAILED), \
                    f"Cannot transition from {stage.value} to FAILED"

    def test_invalid_transitions_rejected(self):
        """Verify invalid transitions are rejected."""
        workflow = WorkflowStateMachine()
        
        # Cannot skip stages
        assert not workflow.can_transition(
            WorkflowStage.PRD_GENERATION,
            WorkflowStage.PLAN_GENERATION
        )
        
        # Cannot go backwards
        assert not workflow.can_transition(
            WorkflowStage.DEVELOPMENT,
            WorkflowStage.ARCHITECTURE_DESIGN
        )
        
        # Cannot transition from terminal states
        assert not workflow.can_transition(
            WorkflowStage.COMPLETED,
            WorkflowStage.DELIVERY
        )

    def test_parallel_stages_identified(self):
        """Test that parallel stages are correctly identified."""
        workflow = WorkflowStateMachine()
        
        # Documentation and Support should be parallel stages
        assert workflow.is_parallel_stage(WorkflowStage.DOCUMENTATION)
        assert workflow.is_parallel_stage(WorkflowStage.SUPPORT_DOCS)
        
        # QA and Security are also parallel-capable
        assert workflow.is_parallel_stage(WorkflowStage.QA_TESTING)
        assert workflow.is_parallel_stage(WorkflowStage.SECURITY_REVIEW)

    def test_get_parallel_stages_after_development(self):
        """Test getting parallel stages after development."""
        workflow = WorkflowStateMachine()
        
        parallel_stages = workflow.get_parallel_stages_after(WorkflowStage.DEVELOPMENT)
        
        # Should include QA, Security, Documentation, and Support
        expected = [
            WorkflowStage.QA_TESTING,
            WorkflowStage.SECURITY_REVIEW,
            WorkflowStage.DOCUMENTATION,
            WorkflowStage.SUPPORT_DOCS
        ]
        
        assert set(parallel_stages) == set(expected)

    def test_all_stages_have_agents(self):
        """Verify all executable stages have assigned agents."""
        workflow = WorkflowStateMachine()
        
        # Stages that should have agents
        executable_stages = [
            WorkflowStage.PRD_GENERATION,
            WorkflowStage.PLAN_GENERATION,
            WorkflowStage.ARCHITECTURE_DESIGN,
            WorkflowStage.UIUX_DESIGN,
            WorkflowStage.DEVELOPMENT,
            WorkflowStage.QA_TESTING,
            WorkflowStage.SECURITY_REVIEW,
            WorkflowStage.DOCUMENTATION,
            WorkflowStage.SUPPORT_DOCS,
            WorkflowStage.PM_REVIEW,
            WorkflowStage.DELIVERY
        ]
        
        for stage in executable_stages:
            agent = workflow.get_agent_for_stage(stage)
            assert agent != "unknown", f"Stage {stage.value} has no assigned agent"

    def test_documentation_transition_to_pm_review(self):
        """Verify documentation stage can transition to PM review."""
        workflow = WorkflowStateMachine()
        
        assert workflow.can_transition(
            WorkflowStage.DOCUMENTATION,
            WorkflowStage.PM_REVIEW
        )

    def test_support_docs_transition_to_pm_review(self):
        """Verify support docs stage can transition to PM review."""
        workflow = WorkflowStateMachine()
        
        assert workflow.can_transition(
            WorkflowStage.SUPPORT_DOCS,
            WorkflowStage.PM_REVIEW
        )

    def test_delivery_transition_to_completed(self):
        """Verify delivery stage can transition to completed."""
        workflow = WorkflowStateMachine()
        
        assert workflow.can_transition(
            WorkflowStage.DELIVERY,
            WorkflowStage.COMPLETED
        )

    def test_complete_workflow_path(self):
        """Test a complete workflow path from start to finish."""
        workflow = WorkflowStateMachine()
        
        # Full sequential path
        path = [
            (WorkflowStage.INITIALIZATION, WorkflowStage.PRD_GENERATION),
            (WorkflowStage.PRD_GENERATION, WorkflowStage.WAITING_FOR_APPROVAL),
            (WorkflowStage.WAITING_FOR_APPROVAL, WorkflowStage.PLAN_GENERATION),
            (WorkflowStage.PLAN_GENERATION, WorkflowStage.ARCHITECTURE_DESIGN),
            (WorkflowStage.ARCHITECTURE_DESIGN, WorkflowStage.UIUX_DESIGN),
            (WorkflowStage.UIUX_DESIGN, WorkflowStage.DEVELOPMENT),
            (WorkflowStage.DEVELOPMENT, WorkflowStage.QA_TESTING),
            (WorkflowStage.QA_TESTING, WorkflowStage.SECURITY_REVIEW),
            (WorkflowStage.SECURITY_REVIEW, WorkflowStage.PM_REVIEW),
            (WorkflowStage.PM_REVIEW, WorkflowStage.DELIVERY),
            (WorkflowStage.DELIVERY, WorkflowStage.COMPLETED),
        ]
        
        for from_stage, to_stage in path:
            assert workflow.can_transition(from_stage, to_stage), \
                f"Transition {from_stage.value} → {to_stage.value} should be valid"

    def test_development_can_branch_to_multiple_stages(self):
        """Verify development can transition to multiple parallel stages."""
        workflow = WorkflowStateMachine()
        
        # Development can transition to QA, Security, Documentation, or Support
        valid_next = workflow.get_next_stages(WorkflowStage.DEVELOPMENT)
        
        assert WorkflowStage.QA_TESTING in valid_next
        assert WorkflowStage.SECURITY_REVIEW in valid_next
        assert WorkflowStage.DOCUMENTATION in valid_next
        assert WorkflowStage.SUPPORT_DOCS in valid_next
