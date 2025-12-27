import time
from core.timer import Timer, WorkTimer, BreakTimer, TimerState

# Global flags for callbacks
tick_count = 0
completed = False
break_triggered = False
warning_triggered = False

def reset_flags():
    global tick_count, completed, break_triggered, warning_triggered
    tick_count = 0
    completed = False
    break_triggered = False
    warning_triggered = False

def on_tick(elapsed):
    global tick_count
    tick_count += 1
    print(f"Tick: {elapsed}s (total ticks: {tick_count})")

def on_complete():
    global completed
    completed = True
    print("Completed!")

def on_break_time(index):
    global break_triggered
    break_triggered = True
    print(f"Break time triggered at index {index}")

def on_warning(remaining):
    global warning_triggered
    warning_triggered = True
    print(f"Warning: {remaining}s remaining")

def test_basic_timer():
    print("\n=== Testing Basic Timer ===")
    reset_flags()
    
    # Test normal flow
    timer = Timer(0.1, on_tick=on_tick, on_complete=on_complete)  
    assert timer.state == TimerState.STOPPED
    assert timer.get_elapsed_seconds() == 0
    assert timer.get_progress_percentage() == 0.0
    
    timer.start()
    assert timer.is_running()
    time.sleep(2) 
    assert tick_count == 2
    
    timer.pause()
    assert timer.is_paused()
    elapsed_before = timer.get_elapsed_seconds()
    time.sleep(1)  # No ticks during pause
    assert tick_count == 2  
    assert timer.get_elapsed_seconds() == elapsed_before  # Elapsed doesn't advance
    
    timer.resume()
    assert timer.is_running()
    time.sleep(3)  
    time.sleep(2)  # Buffer for completion callback
    assert completed
    assert timer.is_completed()
    assert timer.get_elapsed_seconds() == 6
    assert timer.get_progress_percentage() == 100.0
    
    timer.reset()
    assert timer.state == TimerState.STOPPED
    assert timer.get_elapsed_seconds() == 0

def test_work_timer():
    print("\n=== Testing WorkTimer ===")
    reset_flags()
    
    # 10 minutes, breaks at 2 and 5 minutes
    timer = WorkTimer(10, [2, 5], on_tick=on_tick, on_complete=on_complete, on_break_time=on_break_time)
    timer.start()
    time.sleep(130)  # Wait ~2 minutes (120s) + 10s buffer to trigger break
    assert break_triggered  # Should trigger at 2min mark
    time.sleep(190)  # Wait another ~3 minutes to 5min mark + buffer
    timer.stop()

def test_break_timer():
    print("\n=== Testing BreakTimer ===")
    reset_flags()
    
    # 5 minutes break, warning at 60s remaining (triggers at 4min elapsed)
    timer = BreakTimer(5, on_tick=on_tick, on_complete=on_complete, on_warning=on_warning)
    timer.start()
    time.sleep(250)  # Run for ~4 minutes + 10s buffer, should trigger warning
    assert warning_triggered
    time.sleep(70)  # Wait for completion + buffer
    assert completed

def test_edge_cases():
    print("\n=== Testing Edge Cases ===")
    
    # Zero duration
    timer = Timer(0, on_complete=on_complete)
    timer.start()
    time.sleep(0.1)
    assert completed
    assert timer.get_progress_percentage() == 100.0
    
    # Multiple pauses
    reset_flags()
    timer = Timer(0.1, on_tick=on_tick)
    timer.start()
    time.sleep(1)
    timer.pause()
    time.sleep(0.5)
    timer.resume()
    time.sleep(1)
    timer.pause()
    time.sleep(0.5)
    timer.resume()
    time.sleep(4)  # Should complete
    time.sleep(1) 
    assert tick_count >= 5  # Approximate check

if __name__ == "__main__":
    test_basic_timer()
    test_work_timer()
    test_break_timer()
    test_edge_cases()
    print("\n=== All tests completed ===")