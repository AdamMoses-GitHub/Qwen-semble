"""Threading utilities for non-blocking operations."""

import threading
import queue
from typing import Callable, Any, Optional
from dataclasses import dataclass


@dataclass
class ProgressUpdate:
    """Progress update data structure."""
    percentage: float
    message: str


class TTSWorker(threading.Thread):
    """Worker thread for TTS operations."""
    
    def __init__(
        self,
        task_func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        success_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None
    ):
        """Initialize TTS worker thread.
        
        Args:
            task_func: Function to execute in background
            args: Positional arguments for task_func
            kwargs: Keyword arguments for task_func
            success_callback: Called on successful completion with result
            error_callback: Called on error with exception
            progress_callback: Called with progress updates
        """
        super().__init__(daemon=True)
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs or {}
        self.success_callback = success_callback
        self.error_callback = error_callback
        self.progress_callback = progress_callback
        self.stop_flag = threading.Event()
        self.result = None
        self.error = None
    
    def run(self) -> None:
        """Execute the task in background thread."""
        try:
            # Pass progress callback if task supports it
            if 'progress_callback' in self.kwargs:
                self.kwargs['progress_callback'] = self._progress_wrapper
            
            self.result = self.task_func(*self.args, **self.kwargs)
            
            if not self.stop_flag.is_set() and self.success_callback:
                self.success_callback(self.result)
        except Exception as e:
            self.error = e
            if not self.stop_flag.is_set() and self.error_callback:
                self.error_callback(e)
    
    def _progress_wrapper(self, percentage: float, message: str) -> None:
        """Wrap progress callback to check stop flag.
        
        Args:
            percentage: Progress percentage (0-100)
            message: Progress message
        """
        if self.stop_flag.is_set():
            raise InterruptedError("Operation cancelled by user")
        
        if self.progress_callback:
            self.progress_callback(percentage, message)
    
    def stop(self) -> None:
        """Signal the worker to stop."""
        self.stop_flag.set()


class CancellableWorker(TTSWorker):
    """Worker thread with enhanced cancellation support."""
    
    def __init__(self, *args, cleanup_callback: Optional[Callable] = None, **kwargs):
        """Initialize cancellable worker.
        
        Args:
            cleanup_callback: Called when operation is cancelled
            *args, **kwargs: Passed to TTSWorker
        """
        super().__init__(*args, **kwargs)
        self.cleanup_callback = cleanup_callback
    
    def stop(self) -> None:
        """Stop the worker and perform cleanup."""
        super().stop()
        if self.cleanup_callback:
            try:
                self.cleanup_callback()
            except Exception as e:
                print(f"Error during cleanup: {e}")


class ProgressTracker:
    """Thread-safe progress tracker for GUI updates."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self.queue = queue.Queue()
        self.current_percentage = 0.0
        self.current_message = ""
    
    def set_progress(self, percentage: float, message: str) -> None:
        """Set progress update.
        
        Args:
            percentage: Progress percentage (0-100)
            message: Progress message
        """
        self.current_percentage = percentage
        self.current_message = message
        self.queue.put(ProgressUpdate(percentage, message))
    
    def get_update(self, block: bool = False, timeout: float = 0.1) -> Optional[ProgressUpdate]:
        """Get next progress update.
        
        Args:
            block: Whether to block waiting for update
            timeout: Timeout in seconds if blocking
            
        Returns:
            ProgressUpdate or None if queue is empty
        """
        try:
            return self.queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
    
    def complete(self) -> None:
        """Mark operation as complete."""
        self.set_progress(100.0, "Complete")
    
    def error(self, message: str) -> None:
        """Mark operation as failed.
        
        Args:
            message: Error message
        """
        self.set_progress(-1.0, f"Error: {message}")


def run_in_thread(
    root,
    task_func: Callable,
    on_success: Callable,
    on_error: Optional[Callable] = None,
    *args,
    **kwargs
) -> TTSWorker:
    """Convenience function to run a task in a background thread with GUI callbacks.
    
    Args:
        root: Tkinter root window for thread-safe GUI updates
        task_func: Function to run in background
        on_success: Called on main thread with result
        on_error: Called on main thread with exception
        *args, **kwargs: Passed to task_func
        
    Returns:
        TTSWorker instance
    """
    def success_wrapper(result):
        if root and on_success:
            root.after(0, lambda: on_success(result))
    
    def error_wrapper(error):
        if root and on_error:
            root.after(0, lambda: on_error(error))
    
    worker = TTSWorker(
        task_func,
        args=args,
        kwargs=kwargs,
        success_callback=success_wrapper,
        error_callback=error_wrapper
    )
    worker.start()
    return worker
