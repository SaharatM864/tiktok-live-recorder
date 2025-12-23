from abc import ABC, abstractmethod


class IRecorder(ABC):
    """Interface for recording implementations."""

    @abstractmethod
    async def start_recording(self, user: str, room_id: str, output_path: str) -> None:
        """Start recording a live stream."""
        pass

    @abstractmethod
    async def stop_recording(self) -> None:
        """Stop the current recording."""
        pass

    @abstractmethod
    def is_recording(self) -> bool:
        """Check if recording is in progress."""
        pass


class IUploader(ABC):
    """Interface for upload implementations."""

    @abstractmethod
    async def upload(self, file_path: str) -> bool:
        """Upload a file."""
        pass
