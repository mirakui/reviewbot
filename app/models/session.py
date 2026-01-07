"""Review session model."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from app.models.comment import ReviewComment  # noqa: TC001
from app.models.config import AgentConfig  # noqa: TC001
from app.models.file_diff import FileDiff  # noqa: TC001
from app.models.pull_request import PullRequest  # noqa: TC001


class ReviewState(str, Enum):
    """State of a review session."""

    PENDING = "pending"
    LOADING = "loading"
    REVIEWING = "reviewing"
    POSTING = "posting"
    COMPLETED = "completed"
    FAILED = "failed"


# Valid state transitions
VALID_TRANSITIONS: dict[ReviewState, set[ReviewState]] = {
    ReviewState.PENDING: {ReviewState.LOADING, ReviewState.FAILED},
    ReviewState.LOADING: {ReviewState.REVIEWING, ReviewState.FAILED},
    ReviewState.REVIEWING: {ReviewState.POSTING, ReviewState.FAILED},
    ReviewState.POSTING: {ReviewState.COMPLETED, ReviewState.FAILED},
    # Terminal states have no valid transitions
    ReviewState.COMPLETED: set(),
    ReviewState.FAILED: set(),
}


@dataclass
class ReviewSession:
    """Tracks the state of a review session.

    This is an in-memory state tracker - not persisted.
    """

    pull_request: PullRequest
    config: AgentConfig
    state: ReviewState = ReviewState.PENDING
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    files: list[FileDiff] = field(default_factory=list)
    comments: list[ReviewComment] = field(default_factory=list)
    error: str | None = None

    def transition_to(self, new_state: ReviewState) -> None:
        """Transition to a new state with validation.

        Args:
            new_state: The state to transition to.

        Raises:
            ValueError: If the transition is invalid.
        """
        valid_next_states = VALID_TRANSITIONS.get(self.state, set())

        if new_state not in valid_next_states:
            raise ValueError(
                f"Invalid transition: {self.state.value} -> {new_state.value}. "
                f"Valid transitions: {[s.value for s in valid_next_states]}"
            )

        self.state = new_state

        # Set completion time for terminal states
        if new_state in {ReviewState.COMPLETED, ReviewState.FAILED}:
            self.completed_at = datetime.now(UTC)

    def fail(self, error: str) -> None:
        """Transition to failed state with error message.

        Args:
            error: The error message.
        """
        self.error = error
        # Allow failing from any non-terminal state
        if self.state not in {ReviewState.COMPLETED, ReviewState.FAILED}:
            self.state = ReviewState.FAILED
            self.completed_at = datetime.now(UTC)

    @property
    def is_terminal(self) -> bool:
        """Check if session is in a terminal state."""
        return self.state in {ReviewState.COMPLETED, ReviewState.FAILED}

    @property
    def duration_seconds(self) -> float | None:
        """Get session duration in seconds, if completed."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def files_reviewed(self) -> int:
        """Get count of files reviewed."""
        return len(self.files)

    @property
    def comments_count(self) -> int:
        """Get total comment count."""
        return len(self.comments)
